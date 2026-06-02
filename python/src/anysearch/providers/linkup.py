"""Linkup — agentic web search with optional cited answers."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_MODE = {"fast": "fast", "balanced": "standard", "deep": "deep"}


class LinkupProvider(BaseProvider):
    name = "linkup"
    env_keys = ("LINKUP_API_KEY",)
    default_base_url = "https://api.linkup.so"
    extra_package = "linkup-sdk"
    native_client = ("linkup", ("LinkupClient",))
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.DATE,
            Capability.MODE,
            Capability.ANSWER,
            Capability.CONTENT,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {
            "q": req.query,
            "depth": _MODE.get(req.mode, "standard"),
            "outputType": "sourcedAnswer" if req.answer else "searchResults",
        }
        if req.include_domains:
            body["includeDomains"] = req.include_domains
        if req.exclude_domains:
            body["excludeDomains"] = req.exclude_domains
        if req.start_published_date:
            body["fromDate"] = req.start_published_date[:10]
        if req.end_published_date:
            body["toDate"] = req.end_published_date[:10]
        if req.max_results:
            body["maxResults"] = req.max_results
        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v1/search",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        answer = data.get("answer")
        sources = data.get("results") or data.get("sources") or []
        results = []
        for item in sources:
            content = item.get("content") or item.get("snippet")
            results.append(
                self._result(
                    title=item.get("name") or item.get("title"),
                    url=item.get("url"),
                    snippet=content,
                    text=content,
                    raw=item,
                )
            )
        return self._response(req, results, data, answer=answer, elapsed_ms=elapsed_ms)
