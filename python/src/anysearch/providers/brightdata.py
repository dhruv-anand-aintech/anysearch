"""Bright Data SERP API — structured Google and Bing results through one request API."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_ZONE_ENV = ("BRIGHTDATA_ZONE", "BRIGHT_DATA_ZONE", "BRIGHTDATA_SERP_ZONE")


def _date_us(value: str) -> str:
    """Google `tbs` expects M/D/YYYY."""
    raw = (value or "")[:10]
    parts = raw.split("-")
    if len(parts) != 3:
        return raw
    return f"{int(parts[1])}/{int(parts[2])}/{parts[0]}"


def _tbs(req: SearchRequest) -> Optional[str]:
    if not (req.start_published_date or req.end_published_date):
        return None
    pieces = ["cdr:1"]
    if req.start_published_date:
        pieces.append(f"cd_min:{_date_us(req.start_published_date)}")
    if req.end_published_date:
        pieces.append(f"cd_max:{_date_us(req.end_published_date)}")
    return ",".join(pieces)


def _query(req: SearchRequest) -> str:
    parts = [req.query]
    for domain in req.include_domains:
        parts.append(f"site:{domain}")
    for domain in req.exclude_domains:
        parts.append(f"-site:{domain}")
    return " ".join(part for part in parts if part).strip()


class BrightDataProvider(BaseProvider):
    name = "brightdata"
    aliases = ("bright_data",)
    env_keys = ("BRIGHTDATA_API_KEY", "BRIGHT_DATA_API_KEY", "BRIGHTDATA_ZONE")
    default_base_url = "https://api.brightdata.com"
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.COUNTRY,
            Capability.LANGUAGE,
            Capability.DATE,
            Capability.SAFE_SEARCH,
            Capability.NEWS,
            Capability.ENGINE,
        }
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        *,
        zone: Optional[str] = None,
        **config: Any,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, **config)
        self.zone = zone or config.get("zone") or self._zone_from_env(self._env)

    @staticmethod
    def _zone_from_env(env: Optional[Dict[str, str]] = None) -> Optional[str]:
        if env is None:
            env = os.environ  # type: ignore[assignment]
        for key in _ZONE_ENV:
            if env.get(key):
                return env[key]
        return None

    @classmethod
    def is_configured(cls, env: Optional[Dict[str, str]] = None) -> bool:
        if env is None:
            env = os.environ  # type: ignore[assignment]
        return bool(cls.key_from_env(env)) and bool(cls._zone_from_env(env))

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set BRIGHTDATA_API_KEY and BRIGHTDATA_ZONE (a SERP API zone). "
            "The adapter targets Google by default and Bing with `engine=\"bing\"`."
        )

    def _target_url(self, req: SearchRequest) -> str:
        engine = (req.engine or "google").strip().lower()
        query = quote_plus(_query(req))
        date_filter = _tbs(req)
        if engine == "bing":
            params = [f"q={query}", f"count={max(1, min(req.max_results, 50))}"]
            if req.language:
                params.append(f"setlang={req.language.lower()}")
            if req.country:
                params.append(f"cc={req.country.upper()}")
            if req.safe_search:
                safe = {"off": "Off", "moderate": "Moderate", "strict": "Strict"}[
                    req.safe_search
                ]
                params.append(f"safeSearch={safe}")
            if req.search_type == "news":
                params.append("qft=sortbydate%3d%221%22")
            return "https://www.bing.com/search?" + "&".join(params)

        params = [f"q={query}", f"num={max(1, min(req.max_results, 100))}"]
        if req.language:
            params.append(f"hl={req.language.lower()}")
        if req.country:
            params.append(f"gl={req.country.lower()}")
        if req.safe_search:
            params.append(f"safe={'active' if req.safe_search != 'off' else 'off'}")
        if req.search_type == "news":
            params.append("tbm=nws")
        if date_filter:
            params.append(f"tbs={quote_plus(date_filter)}")
        return "https://www.google.com/search?" + "&".join(params)

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {
            "zone": self.zone,
            "url": self._target_url(req),
            "format": "raw",
            "data_format": "parsed",
        }
        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/request",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:
        data = response.json()
        if isinstance(data, dict) and isinstance(data.get("body"), str):
            try:
                data = json.loads(data["body"])
            except (TypeError, ValueError):
                pass
        organic = []
        if isinstance(data, dict):
            organic = data.get("organic") or data.get("results") or []
        results = []
        for item in organic:
            if not isinstance(item, dict):
                continue
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("link") or item.get("url"),
                    snippet=item.get("description") or item.get("snippet"),
                    published_date=item.get("date"),
                    score=item.get("global_rank") or item.get("rank"),
                    source=item.get("source"),
                    raw=item,
                )
            )
        return self._response(
            req,
            results,
            data if isinstance(data, dict) else {"body": data},
            total_results=len(results),
            elapsed_ms=elapsed_ms,
        )
