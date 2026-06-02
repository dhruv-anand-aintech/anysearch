"""Kagi Search API (v0) — premium, ad-free search index."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider


class KagiProvider(BaseProvider):
    name = "kagi"
    env_keys = ("KAGI_API_KEY",)
    default_base_url = "https://kagi.com"
    capabilities = frozenset(set())

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        params = {"q": req.query, "limit": req.max_results}
        params.update(req.extra)
        return PreparedRequest(
            method="GET",
            url=f"{self.base_url}/api/v0/search",
            headers={"Authorization": f"Bot {self.api_key}", "Accept": "application/json"},
            params=params,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        results = []
        for item in data.get("data", []) or []:
            # t == 0 is a search result; t == 1 is "related searches".
            if item.get("t") != 0:
                continue
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=item.get("snippet"),
                    published_date=item.get("published"),
                    raw=item,
                )
            )
        meta = data.get("meta") or {}
        return self._response(req, results, data, request_id=meta.get("id"), elapsed_ms=elapsed_ms)
