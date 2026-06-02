"""SearchApi.io — real-time SERP API (Google and other engines)."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


class SearchApiProvider(BaseProvider):
    name = "searchapi"
    env_keys = ("SEARCHAPI_API_KEY", "SEARCHAPI_KEY")
    default_base_url = "https://www.searchapi.io"
    capabilities = frozenset(
        {
            Capability.COUNTRY,
            Capability.LANGUAGE,
            Capability.NEWS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        params = {
            "engine": "google_news" if req.search_type == "news" else "google",
            "q": req.query,
            "num": req.max_results,
        }
        if req.country:
            params["gl"] = req.country.lower()
        if req.language:
            params["hl"] = req.language
        params.update(req.extra)
        return PreparedRequest(
            method="GET",
            url=f"{self.base_url}/api/v1/search",
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            params=params,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        items = data.get("organic_results") or data.get("news_results") or []
        results = []
        for item in items:
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("link"),
                    snippet=item.get("snippet"),
                    source=item.get("source"),
                    published_date=item.get("date"),
                    score=item.get("position"),
                    raw=item,
                )
            )
        answer = None
        box = data.get("answer_box") or {}
        if isinstance(box, dict):
            answer = box.get("answer") or box.get("snippet")
        total = (data.get("search_information") or {}).get("total_results")
        return self._response(
            req, results, data, answer=answer, total_results=total, elapsed_ms=elapsed_ms
        )
