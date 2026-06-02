"""SearXNG — self-hosted/open metasearch engine (configure your instance URL)."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_SAFE = {"off": 0, "moderate": 1, "strict": 2}


class SearxngProvider(BaseProvider):
    name = "searxng"
    aliases = ("searx",)
    env_keys = ("SEARXNG_API_KEY",)
    base_url_env = ("SEARXNG_BASE_URL", "SEARXNG_URL")
    requires_key = False
    requires_base_url = True
    capabilities = frozenset(
        {
            Capability.LANGUAGE,
            Capability.SAFE_SEARCH,
            Capability.ANSWER,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        params: dict = {"q": req.query, "format": "json"}
        if req.language:
            params["language"] = req.language
        if req.safe_search is not None:
            params["safesearch"] = _SAFE.get(req.safe_search, 1)
        if req.search_type == "news":
            params["categories"] = "news"
        params.update(req.extra)
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return PreparedRequest(
            method="GET", url=f"{self.base_url}/search", headers=headers, params=params
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        results = []
        for item in data.get("results", []) or []:
            content = item.get("content")
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=content,
                    score=item.get("score"),
                    published_date=item.get("publishedDate"),
                    source=item.get("engine"),
                    raw=item,
                )
            )
        answers = data.get("answers") or []
        answer = "\n".join(a for a in answers if isinstance(a, str)) or None
        total = data.get("number_of_results")
        return self._response(
            req, results, data, answer=answer, total_results=total, elapsed_ms=elapsed_ms
        )
