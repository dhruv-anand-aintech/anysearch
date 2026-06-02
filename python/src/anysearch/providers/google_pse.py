"""Google Programmable Search Engine (Custom Search JSON API)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_CX_ENV = ("GOOGLE_PSE_CX", "GOOGLE_CSE_CX", "GOOGLE_PSE_ENGINE_ID")


class GooglePSEProvider(BaseProvider):
    name = "google_pse"
    aliases = ("google", "google_cse")
    env_keys = ("GOOGLE_PSE_API_KEY", "GOOGLE_CSE_API_KEY", "GOOGLE_API_KEY")
    default_base_url = "https://www.googleapis.com"
    capabilities = frozenset(
        {
            Capability.COUNTRY,
            Capability.LANGUAGE,
            Capability.SAFE_SEARCH,
            Capability.DOMAINS,
        }
    )

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **config: Any):
        super().__init__(api_key=api_key, base_url=base_url, **config)
        self.cx = config.get("cx") or self._cx_from_env(self._env)

    @staticmethod
    def _cx_from_env(env: Optional[Dict[str, str]] = None) -> Optional[str]:
        if env is None:
            env = os.environ  # type: ignore[assignment]
        for key in _CX_ENV:
            if env.get(key):
                return env[key]
        return None

    @classmethod
    def is_configured(cls, env: Optional[Dict[str, str]] = None) -> bool:
        if env is None:
            env = os.environ  # type: ignore[assignment]
        return bool(cls.key_from_env(env)) and bool(cls._cx_from_env(env))

    @classmethod
    def config_hint(cls) -> str:
        return "Set GOOGLE_PSE_API_KEY and GOOGLE_PSE_CX (search engine id)."

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        params: Dict[str, Any] = {
            "key": self.api_key,
            "cx": self.cx,
            "q": req.query,
            "num": min(req.max_results, 10),
        }
        if req.country:
            params["gl"] = req.country.lower()
        if req.language:
            params["hl"] = req.language
            params["lr"] = f"lang_{req.language[:2]}"
        if req.safe_search:
            params["safe"] = "off" if req.safe_search == "off" else "active"
        if req.start_published_date or req.end_published_date:
            start = (req.start_published_date or "")[:10].replace("-", "")
            end = (req.end_published_date or "")[:10].replace("-", "")
            if start and end:
                params["sort"] = f"date:r:{start}:{end}"
        if req.include_domains:
            params["siteSearch"] = req.include_domains[0]
            params["siteSearchFilter"] = "i"
        elif req.exclude_domains:
            params["siteSearch"] = req.exclude_domains[0]
            params["siteSearchFilter"] = "e"
        params.update(req.extra)
        return PreparedRequest(
            method="GET",
            url=f"{self.base_url}/customsearch/v1",
            headers={"Accept": "application/json"},
            params=params,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        results = []
        for item in data.get("items", []) or []:
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("link"),
                    snippet=item.get("snippet"),
                    source=item.get("displayLink"),
                    raw=item,
                )
            )
        total = None
        info = data.get("searchInformation") or {}
        if info.get("totalResults") is not None:
            try:
                total = int(info["totalResults"])
            except (TypeError, ValueError):
                total = None
        return self._response(req, results, data, total_results=total, elapsed_ms=elapsed_ms)
