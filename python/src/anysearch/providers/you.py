"""You.com (YDC) Search API — web results with rich snippets."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


class YouProvider(BaseProvider):
    name = "you"
    aliases = ("youcom", "ydc")
    env_keys = ("YDC_API_KEY", "YOU_API_KEY")
    default_base_url = "https://ydc-index.io"
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.COUNTRY,
            Capability.HIGHLIGHTS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {"query": req.query, "count": req.max_results}
        if req.include_domains:
            body["include_domains"] = req.include_domains
        if req.exclude_domains:
            body["exclude_domains"] = req.exclude_domains
        if req.country:
            body["country"] = req.country.lower()
        if req.safe_search:
            body["safesearch"] = req.safe_search
        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v1/search",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json=body,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        items = data.get("results") or data.get("hits") or []
        results = []
        for item in items:
            snippets = item.get("snippets") or []
            authors = item.get("authors") or []
            description = item.get("description")
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=description or (snippets[0] if snippets else None),
                    text="\n\n".join(snippets) if snippets else None,
                    highlights=list(snippets),
                    published_date=item.get("page_age"),
                    author=authors[0] if authors else None,
                    raw=item,
                )
            )
        return self._response(req, results, data, elapsed_ms=elapsed_ms)
