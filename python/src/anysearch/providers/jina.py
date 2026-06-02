"""Jina Reader Search (s.jina.ai) — search that returns clean page content."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


class JinaProvider(BaseProvider):
    name = "jina"
    env_keys = ("JINA_API_KEY",)
    default_base_url = "https://s.jina.ai"
    capabilities = frozenset({Capability.CONTENT})

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        # Ask for links only when full content was not requested (faster, cheaper).
        if not req.include_content:
            headers["X-Respond-With"] = "no-content"
        params = {"q": req.query}
        params.update(req.extra)
        return PreparedRequest(
            method="GET",
            url=f"{self.base_url}/",
            headers=headers,
            params=params,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        items = data.get("data") or []
        if isinstance(items, dict):
            items = [items]
        results = []
        for item in items:
            content = item.get("content")
            description = item.get("description")
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=description or (content[:300] if content else None),
                    text=content if req.include_content else None,
                    published_date=item.get("date") or item.get("publishedTime"),
                    raw=item,
                )
            )
        return self._response(req, results, data, elapsed_ms=elapsed_ms)
