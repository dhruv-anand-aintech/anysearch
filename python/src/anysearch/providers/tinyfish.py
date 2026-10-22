"""TinyFish Search API — web, news, and research-paper results."""

from __future__ import annotations

from typing import Any, Dict

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


def _format_date(value: str) -> str:
    """TinyFish expects YYYY-MM-DD lower/upper bounds."""
    return (value or "")[:10]


class TinyFishProvider(BaseProvider):
    name = "tinyfish"
    env_keys = ("TINYFISH_API_KEY",)
    default_base_url = "https://api.search.tinyfish.ai"
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.COUNTRY,
            Capability.LANGUAGE,
            Capability.DATE,
            Capability.NEWS,
        }
    )

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set TINYFISH_API_KEY. Search is GET https://api.search.tinyfish.ai with "
            "`domain_type=web|news|research_paper`; page 0-10 and no result-count parameter."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        params: Dict[str, Any] = {"query": req.query}
        if req.country:
            params["location"] = req.country.upper()
        if req.language:
            params["language"] = req.language.lower()
        if req.include_domains:
            params["include_domains"] = ",".join(req.include_domains)
        if req.exclude_domains:
            params["exclude_domains"] = ",".join(req.exclude_domains)
        if req.start_published_date:
            params["after_date"] = _format_date(req.start_published_date)
        if req.end_published_date:
            params["before_date"] = _format_date(req.end_published_date)
        if req.search_type == "news":
            params["domain_type"] = "news"
        params.update(req.extra)
        return PreparedRequest(
            method="GET",
            url=self.base_url,
            headers={"X-API-Key": self.api_key, "Accept": "application/json"},
            params=params,
        )

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:
        data = response.json()
        results = []
        for item in data.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            authors = item.get("authors") or []
            if isinstance(authors, list):
                author = ", ".join(str(a) for a in authors if a) or None
            else:
                author = str(authors) or None
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=item.get("snippet"),
                    published_date=item.get("date"),
                    author=author,
                    source=item.get("site_name") or item.get("publisher"),
                    raw=item,
                )
            )
        return self._response(
            req,
            results,
            data,
            total_results=data.get("total_results"),
            elapsed_ms=elapsed_ms,
        )
