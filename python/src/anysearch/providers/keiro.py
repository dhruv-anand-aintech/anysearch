"""KeiroLabs — v2 cited search and content search API."""

from __future__ import annotations

from typing import Any, List

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_MODE = {"fast": "light", "balanced": "ai", "deep": "deep"}


class KeiroProvider(BaseProvider):
    name = "keiro"
    aliases = ("keirolabs", "keiro_labs")
    env_keys = ("KEIRO_API_KEY", "KEIROLABS_API_KEY")
    base_url_env = ("KEIRO_BASE_URL", "KEIROLABS_BASE_URL")
    default_base_url = "https://kierolabs.space"
    extra_package = "keirolabs"
    native_client = ("keirolabs", ("Client",))
    capabilities = frozenset({Capability.MODE, Capability.CONTENT})

    def _endpoint(self, req: SearchRequest) -> str:
        endpoint = req.extra.get("endpoint")
        if isinstance(endpoint, str):
            return endpoint
        if req.include_content:
            return "/api/v2/search/content"
        if req.mode == "fast":
            return "/api/v2/search/flash"
        return "/api/v2/keiro"

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        endpoint = self._endpoint(req)
        extra = dict(req.extra)
        extra.pop("endpoint", None)
        body = {
            "query": req.query,
            "maxResults": req.max_results,
            "mode": _MODE.get(req.mode or "", "ai"),
        }
        body.update(extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}{endpoint if endpoint.startswith('/') else '/' + endpoint}",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=body,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        sources: List[Any] = data.get("results") or data.get("sources") or []
        results = []
        for item in sources:
            text = (
                item.get("full_text")
                or item.get("fullText")
                or item.get("text")
                or item.get("markdown")
            )
            snippet = item.get("snippet") or item.get("description") or text
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=snippet,
                    text=text,
                    score=item.get("score"),
                    published_date=item.get("published_date") or item.get("publishedDate"),
                    raw=item,
                )
            )
        return self._response(
            req,
            results,
            data,
            answer=data.get("answer") or data.get("summary"),
            total_results=data.get("total_results") or data.get("totalResults"),
            request_id=data.get("request_id") or data.get("requestId"),
            elapsed_ms=data.get("latency_ms") or data.get("latencyMs") or elapsed_ms,
        )
