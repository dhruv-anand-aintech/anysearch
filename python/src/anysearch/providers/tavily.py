"""Tavily — search API purpose-built for LLMs, with answers and raw content."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_MODE = {"fast": "fast", "balanced": "basic", "deep": "advanced"}


class TavilyProvider(BaseProvider):
    name = "tavily"
    env_keys = ("TAVILY_API_KEY",)
    default_base_url = "https://api.tavily.com"
    extra_package = "tavily-python"
    native_client = ("tavily", ("TavilyClient",))
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.COUNTRY,
            Capability.DATE,
            Capability.MODE,
            Capability.ANSWER,
            Capability.CONTENT,
            Capability.NEWS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {
            "query": req.query,
            "max_results": min(req.max_results, 20),
            "search_depth": _MODE.get(req.mode, "basic"),
            "topic": "news" if req.search_type == "news" else "general",
        }
        if req.include_domains:
            body["include_domains"] = req.include_domains
        if req.exclude_domains:
            body["exclude_domains"] = req.exclude_domains
        if req.start_published_date:
            body["start_date"] = req.start_published_date[:10]
        if req.end_published_date:
            body["end_date"] = req.end_published_date[:10]
        if req.country:
            body["country"] = req.country.lower()
        if req.answer:
            body["include_answer"] = True
        if req.include_content:
            body["include_raw_content"] = True
        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/search",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
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
                    text=item.get("raw_content"),
                    highlights=[content] if content else [],
                    score=item.get("score"),
                    published_date=item.get("published_date"),
                    raw=item,
                )
            )
        return self._response(
            req,
            results,
            data,
            answer=data.get("answer"),
            request_id=data.get("request_id"),
            elapsed_ms=elapsed_ms,
        )
