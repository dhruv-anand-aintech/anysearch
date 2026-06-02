"""Exa (exa.ai) — neural + keyword search with content, summaries, highlights."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_MODE = {"fast": "fast", "balanced": "auto", "deep": "deep"}


class ExaProvider(BaseProvider):
    name = "exa"
    env_keys = ("EXA_API_KEY",)
    default_base_url = "https://api.exa.ai"
    extra_package = "exa-py"
    native_client = ("exa_py", ("Exa",))
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.COUNTRY,
            Capability.DATE,
            Capability.SAFE_SEARCH,
            Capability.MODE,
            Capability.CONTENT,
            Capability.SUMMARY,
            Capability.HIGHLIGHTS,
            Capability.NEWS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {"query": req.query, "numResults": req.max_results, "type": _MODE.get(req.mode, "auto")}
        if req.include_domains:
            body["includeDomains"] = req.include_domains
        if req.exclude_domains:
            body["excludeDomains"] = req.exclude_domains
        if req.start_published_date:
            body["startPublishedDate"] = req.start_published_date
        if req.end_published_date:
            body["endPublishedDate"] = req.end_published_date
        if req.country:
            body["userLocation"] = req.country.upper()
        if req.safe_search and req.safe_search != "off":
            body["moderation"] = True
        if req.search_type == "news":
            body["category"] = "news"

        contents = {}
        if req.include_content:
            contents["text"] = True
        if req.highlights:
            contents["highlights"] = True
        if req.include_summary:
            contents["summary"] = True
        if contents:
            body["contents"] = contents

        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/search",
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
            json=body,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        results = []
        for item in data.get("results", []) or []:
            highlights = item.get("highlights") or []
            if isinstance(highlights, str):
                highlights = [highlights]
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=(item.get("summary") or (highlights[0] if highlights else None)),
                    text=item.get("text"),
                    summary=item.get("summary"),
                    highlights=list(highlights),
                    score=item.get("score"),
                    published_date=item.get("publishedDate"),
                    author=item.get("author"),
                    raw=item,
                )
            )
        answer = None
        output = data.get("output")
        if isinstance(output, dict):
            answer = output.get("content") if isinstance(output.get("content"), str) else None
        return self._response(
            req,
            results,
            data,
            answer=answer,
            request_id=data.get("requestId"),
            elapsed_ms=elapsed_ms,
        )
