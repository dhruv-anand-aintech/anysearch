"""SerpApi — Google, Bing, Baidu, Yandex, DuckDuckGo, and other SERP engines."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability
from .serpapi_engines import (
    SERPAPI_WEB_ENGINES,
    apply_serpapi_locale,
    apply_serpapi_safe_search,
    extract_serpapi_answer,
    extract_serpapi_results,
    normalize_engine,
    resolve_serpapi_engine,
)


class SerpApiProvider(BaseProvider):
    name = "serpapi"
    aliases = ("serp",)
    env_keys = ("SERPAPI_API_KEY", "SERPAPI_KEY")
    default_base_url = "https://serpapi.com"
    extra_package = "google-search-results"
    native_client = ("serpapi", ("Client", "GoogleSearch"))
    capabilities = frozenset(
        {
            Capability.COUNTRY,
            Capability.LANGUAGE,
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
        engine: Optional[str] = None,
        default_engine: Optional[str] = None,
        **config: Any,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, **config)
        raw = engine or default_engine or config.get("engine") or "google"
        self.default_engine = normalize_engine(str(raw))

    @classmethod
    def config_hint(cls) -> str:
        engines = ", ".join(sorted(SERPAPI_WEB_ENGINES))
        return (
            f"Set SERPAPI_API_KEY. Optional `engine` (e.g. bing, baidu, yandex) — "
            f"supported web engines include: {engines}."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        extra = dict(req.extra)
        engine = resolve_serpapi_engine(
            engine=req.engine,
            default_engine=self.default_engine,
            search_type=req.search_type,
            extra=extra,
        )
        params: Dict[str, Any] = {
            "engine": engine,
            "q": req.query,
            "num": req.max_results,
            "api_key": self.api_key,
        }
        apply_serpapi_locale(params, engine, req.country, req.language)
        apply_serpapi_safe_search(params, engine, req.safe_search)
        params.update(extra)
        return PreparedRequest(
            method="GET",
            url=f"{self.base_url}/search",
            headers={"Accept": "application/json"},
            params=params,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        items = extract_serpapi_results(data, req.search_type)
        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("link") or item.get("url"),
                    snippet=item.get("snippet") or item.get("description"),
                    source=item.get("source") or item.get("displayed_link"),
                    published_date=item.get("date"),
                    score=item.get("position"),
                    raw=item,
                )
            )
        answer = extract_serpapi_answer(data)
        total = (data.get("search_information") or {}).get("total_results")
        return self._response(
            req, results, data, answer=answer, total_results=total, elapsed_ms=elapsed_ms
        )
