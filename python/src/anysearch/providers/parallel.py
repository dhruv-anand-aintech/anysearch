"""Parallel (parallel.ai) — LLM-optimized web search returning ranked excerpts."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_MODE = {"fast": "basic", "balanced": "basic", "deep": "advanced"}


class ParallelProvider(BaseProvider):
    name = "parallel"
    env_keys = ("PARALLEL_API_KEY",)
    default_base_url = "https://api.parallel.ai"
    extra_package = "parallel-web"
    native_client = ("parallel", ("Parallel",))
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.COUNTRY,
            Capability.DATE,
            Capability.MODE,
            Capability.CONTENT,
            Capability.HIGHLIGHTS,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {
            "search_queries": [req.query],
            "objective": req.extra.pop("objective", req.query),
            "max_results": req.max_results,
        }
        if req.mode:
            body["mode"] = _MODE.get(req.mode, "advanced")

        advanced = {}
        source_policy = {}
        if req.include_domains:
            source_policy["include_domains"] = req.include_domains
        if req.exclude_domains:
            source_policy["exclude_domains"] = req.exclude_domains
        if req.start_published_date:
            source_policy["after_date"] = req.start_published_date
        if source_policy:
            advanced["source_policy"] = source_policy
        if req.country:
            advanced["location"] = req.country.lower()
        if advanced:
            body["advanced_settings"] = advanced

        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v1/search",
            headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
            json=body,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        data = response.json()
        results = []
        for item in data.get("results", []) or []:
            excerpts = item.get("excerpts") or []
            if isinstance(excerpts, str):
                excerpts = [excerpts]
            text = "\n\n".join(e for e in excerpts if e) or None
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=(excerpts[0] if excerpts else None),
                    text=text,
                    highlights=list(excerpts),
                    raw=item,
                )
            )
        return self._response(
            req, results, data, request_id=data.get("search_id"), elapsed_ms=elapsed_ms
        )
