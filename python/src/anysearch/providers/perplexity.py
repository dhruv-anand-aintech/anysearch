"""Perplexity Search API — ranked results with deep content extraction."""

from __future__ import annotations

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


class PerplexityProvider(BaseProvider):
    name = "perplexity"
    aliases = ("pplx",)
    env_keys = ("PERPLEXITY_API_KEY", "PPLX_API_KEY")
    default_base_url = "https://api.perplexity.ai"
    extra_package = "perplexityai"
    native_client = ("perplexity", ("Perplexity",))
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.LANGUAGE,
            Capability.CONTENT,
        }
    )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body = {"query": req.query, "max_results": min(req.max_results, 20)}
        domains = list(req.include_domains) + [f"-{d}" for d in req.exclude_domains]
        if domains:
            body["search_domain_filter"] = domains
        if req.language:
            body["search_language_filter"] = [req.language[:2]]
        if req.include_content:
            body["snippet_mode"] = "high"
            body.setdefault("max_tokens_per_page", 8192)
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
            snippet = item.get("snippet")
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=snippet,
                    text=snippet if req.include_content else None,
                    published_date=item.get("date") or item.get("last_updated"),
                    raw=item,
                )
            )
        return self._response(req, results, data, elapsed_ms=elapsed_ms)
