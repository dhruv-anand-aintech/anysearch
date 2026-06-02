"""Serper.dev — fast, low-cost Google SERP API."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


class SerperProvider(BaseProvider):
    name = "serper"
    env_keys = ("SERPER_API_KEY",)
    default_base_url = "https://google.serper.dev"
    capabilities = frozenset(
        {
            Capability.COUNTRY,
            Capability.LANGUAGE,
            Capability.NEWS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {"q": req.query, "num": req.max_results}
        if req.country:
            body["gl"] = req.country.lower()
        if req.language:
            body["hl"] = req.language
        body.update(req.extra)
        path = "/news" if req.search_type == "news" else "/search"
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}{path}",
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json=body,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        items = data.get("news", []) if req.search_type == "news" else data.get("organic", [])
        results = []
        for item in items or []:
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
        box = data.get("answerBox") or {}
        if isinstance(box, dict):
            answer = box.get("answer") or box.get("snippet")
        return self._response(req, results, data, answer=answer, elapsed_ms=elapsed_ms)
