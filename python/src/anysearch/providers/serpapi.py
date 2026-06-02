"""SerpApi — real-time Google (and other engines) SERP scraping."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


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
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        params = {
            "engine": "google",
            "q": req.query,
            "num": req.max_results,
            "api_key": self.api_key,
        }
        if req.country:
            params["gl"] = req.country.lower()
        if req.language:
            params["hl"] = req.language
        if req.safe_search:
            params["safe"] = "off" if req.safe_search == "off" else "active"
        if req.search_type == "news":
            params["tbm"] = "nws"
        params.update(req.extra)
        return PreparedRequest(
            method="GET",
            url=f"{self.base_url}/search",
            headers={"Accept": "application/json"},
            params=params,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        if req.search_type == "news":
            items = data.get("news_results", []) or []
        else:
            items = data.get("organic_results", []) or []
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
