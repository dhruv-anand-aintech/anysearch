"""DataForSEO — live Google Organic SERP API with HTTP Basic authentication."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, Optional

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_PASSWORD_ENV = ("DATAFORSEO_PASSWORD", "DATAFORSEO_API_PASSWORD")
_LOCATION_ENV = ("DATAFORSEO_LOCATION_CODE",)


def _query(req: SearchRequest) -> str:
    parts = [req.query]
    for domain in req.include_domains:
        parts.append(f"site:{domain}")
    for domain in req.exclude_domains:
        parts.append(f"-site:{domain}")
    return " ".join(part for part in parts if part).strip()


class DataForSeoProvider(BaseProvider):
    name = "dataforseo"
    aliases = ("data_for_seo",)
    env_keys = ("DATAFORSEO_LOGIN", "DATAFORSEO_API_LOGIN", "DATAFORSEO_PASSWORD")
    default_base_url = "https://api.dataforseo.com"
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.LANGUAGE,
        }
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        *,
        password: Optional[str] = None,
        location_code: Optional[int] = None,
        **config: Any,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, **config)
        self.password = password or config.get("password") or self._env_value(_PASSWORD_ENV)
        raw_location = location_code or config.get("location_code")
        if raw_location is None:
            env_location = self._env_value(_LOCATION_ENV)
            raw_location = env_location
        try:
            self.location_code = int(raw_location) if raw_location is not None else 2840
        except (TypeError, ValueError):
            self.location_code = 2840

    def _env_value(self, keys: tuple) -> Optional[str]:
        for key in keys:
            value = self._env.get(key)
            if value:
                return value
        return None

    @classmethod
    def is_configured(cls, env: Optional[Dict[str, str]] = None) -> bool:
        if env is None:
            env = os.environ  # type: ignore[assignment]
        return bool(cls.key_from_env(env)) and any(env.get(k) for k in _PASSWORD_ENV)

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD (HTTP Basic auth). "
            "Optional DATAFORSEO_LOCATION_CODE defaults to 2840 (United States)."
        )

    def _require_key(self) -> None:
        super()._require_key()
        if not self.password:
            from ..exceptions import MissingAPIKeyError

            raise MissingAPIKeyError(self.name, self.config_hint())

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        task: Dict[str, Any] = {
            "keyword": _query(req),
            "location_code": self.location_code,
            "language_code": (req.language or "en").lower(),
            "depth": max(1, min(req.max_results, 200)),
        }
        if req.extra:
            task.update(req.extra)
        credentials = f"{self.api_key}:{self.password}".encode("utf-8")
        token = base64.b64encode(credentials).decode("ascii")
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v3/serp/google/organic/live/advanced",
            headers={
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
            },
            json=[task],
        )

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:
        data = response.json()
        tasks = data.get("tasks") or []
        task = tasks[0] if tasks else {}
        task_result = (task.get("result") or [{}])[0] if task.get("result") else {}
        items = task_result.get("items") or []
        results = []
        for item in items:
            if not isinstance(item, dict) or item.get("type") != "organic":
                continue
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=item.get("description"),
                    published_date=item.get("timestamp"),
                    score=item.get("rank_absolute") or item.get("rank_group"),
                    raw=item,
                )
            )
        return self._response(
            req,
            results,
            data,
            total_results=task_result.get("se_results_count"),
            elapsed_ms=elapsed_ms,
        )
