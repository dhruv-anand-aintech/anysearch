"""Firecrawl Search — web search that can scrape full page content inline."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


class FirecrawlProvider(BaseProvider):
    name = "firecrawl"
    env_keys = ("FIRECRAWL_API_KEY",)
    default_base_url = "https://api.firecrawl.dev"
    extra_package = "firecrawl-py"
    native_client = ("firecrawl", ("Firecrawl", "FirecrawlApp"))
    capabilities = frozenset(
        {
            Capability.COUNTRY,
            Capability.CONTENT,
            Capability.NEWS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        sources = [{"type": "news"}] if req.search_type == "news" else [{"type": "web"}]
        body = {"query": req.query, "limit": min(req.max_results, 100), "sources": sources}
        if req.country:
            body["country"] = req.country.upper()
        if req.include_content:
            body["scrapeOptions"] = {"formats": ["markdown"], "onlyMainContent": True}
        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v2/search",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        payload = data.get("data", data)
        items = []
        if isinstance(payload, dict):
            for key in ("web", "news", "images"):
                items.extend(payload.get(key) or [])
        elif isinstance(payload, list):
            items = payload
        results = []
        for item in items:
            metadata = item.get("metadata") or {}
            results.append(
                self._result(
                    title=item.get("title") or metadata.get("title"),
                    url=item.get("url"),
                    snippet=item.get("description") or metadata.get("description"),
                    text=item.get("markdown"),
                    published_date=item.get("date"),
                    raw=item,
                )
            )
        return self._response(req, results, data, elapsed_ms=elapsed_ms)
