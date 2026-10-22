"""Keenable — independent web index with pro and realtime search modes."""

from __future__ import annotations

from typing import Any, Dict

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_MODE = {"fast": "realtime", "balanced": "pro", "deep": "pro"}


class KeenableProvider(BaseProvider):
    name = "keenable"
    env_keys = ("KEENABLE_API_KEY",)
    default_base_url = "https://api.keenable.ai"
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.DATE,
            Capability.MODE,
            Capability.CONTENT,
            Capability.HIGHLIGHTS,
        }
    )

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set KEENABLE_API_KEY. `mode=fast` uses the realtime search SKU and "
            "`balanced`/`deep` use pro; override the body with provider_params or extra."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body: Dict[str, Any] = {
            "query": req.query,
            "mode": _MODE.get(req.mode or "", "pro"),
            "max_results": max(1, min(req.max_results, 50)),
        }
        if req.include_domains:
            body["site"] = req.include_domains[0]
        if req.start_published_date:
            body["published_after"] = req.start_published_date
        if req.end_published_date:
            body["published_before"] = req.end_published_date
        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v1/search",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json=body,
        )

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:
        data = response.json()
        results = []
        for item in data.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            snippet = item.get("snippet") or item.get("description")
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=snippet,
                    published_date=item.get("published_at"),
                    raw=item,
                )
            )
        return self._response(
            req,
            results,
            data,
            total_results=len(results),
            elapsed_ms=elapsed_ms,
        )
