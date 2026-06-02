"""Brave Search API — independent index with web + news search."""

from __future__ import annotations

from datetime import date

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


class BraveProvider(BaseProvider):
    name = "brave"
    aliases = ("brave_search",)
    env_keys = ("BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY")
    default_base_url = "https://api.search.brave.com"
    capabilities = frozenset(
        {
            Capability.COUNTRY,
            Capability.LANGUAGE,
            Capability.DATE,
            Capability.SAFE_SEARCH,
            Capability.HIGHLIGHTS,
            Capability.NEWS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        is_news = req.search_type == "news"
        max_count = 50 if is_news else 20
        params = {
            "q": req.query,
            "count": min(req.max_results, max_count),
        }
        if req.country:
            params["country"] = req.country.upper()
        if req.language:
            params["search_lang"] = req.language
        if req.safe_search:
            params["safesearch"] = req.safe_search
        if req.highlights:
            params["extra_snippets"] = "true"
        if req.start_published_date or req.end_published_date:
            start = req.start_published_date or "1970-01-01"
            end = req.end_published_date or date.today().isoformat()
            params["freshness"] = f"{start[:10]}to{end[:10]}"
        params.update(req.extra)

        path = "/res/v1/news/search" if is_news else "/res/v1/web/search"
        return PreparedRequest(
            method="GET",
            url=f"{self.base_url}{path}",
            headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
            params=params,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        if req.search_type == "news":
            items = (data.get("results") or [])
        else:
            items = (data.get("web") or {}).get("results", []) or []
        results = []
        for item in items:
            extra_snippets = item.get("extra_snippets") or []
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=item.get("description"),
                    highlights=list(extra_snippets),
                    published_date=item.get("page_age") or item.get("age"),
                    raw=item,
                )
            )
        return self._response(req, results, data, elapsed_ms=elapsed_ms)
