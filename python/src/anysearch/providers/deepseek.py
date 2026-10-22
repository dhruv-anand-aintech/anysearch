"""DeepSeek Search & Fetch — raw JSON search over DeepSeek's own web index."""

from __future__ import annotations

from typing import Any, Dict, List

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability


def _date(value: str) -> str:
    return (value or "")[:10]


def _query_with_operators(req: SearchRequest) -> str:
    """DeepSeek keeps the search syntax in the query, using site:/lang:/after:/before:."""
    parts = [req.query]
    if req.include_domains:
        parts.append(" OR ".join(f"site:{d}" for d in req.include_domains))
    for domain in req.exclude_domains:
        parts.append(f"-site:{domain}")
    if req.language:
        parts.append(f"lang:{req.language.lower()}")
    if req.start_published_date:
        parts.append(f"after:{_date(req.start_published_date)}")
    if req.end_published_date:
        parts.append(f"before:{_date(req.end_published_date)}")
    return " ".join(part for part in parts if part).strip()


class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    env_keys = ("DEEPSEEK_API_KEY", "DEEPSEEK_SEARCH_API_KEY")
    default_base_url = "https://api.deepseek.com"
    capabilities = frozenset(
        {
            Capability.DOMAINS,
            Capability.LANGUAGE,
            Capability.DATE,
            Capability.CONTENT,
            Capability.SUMMARY,
        }
    )

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set DEEPSEEK_API_KEY. POST /v1/tools/search takes `count` (1-50), "
            "`need_content`, and query operators for site/lang/date filters."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        body: Dict[str, Any] = {
            "query": _query_with_operators(req),
            "count": max(1, min(req.max_results, 50)),
            "need_content": bool(req.include_content),
        }
        body.update(req.extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v1/tools/search",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:
        data = response.json()
        results: List[Any] = []
        for item in data.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            results.append(
                self._result(
                    title=item.get("title"),
                    url=item.get("url"),
                    snippet=item.get("snippet"),
                    text=item.get("content") or None,
                    summary=item.get("summary"),
                    score=item.get("rerank_score"),
                    published_date=item.get("date"),
                    source=item.get("site_name"),
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


__all__ = ["DeepSeekProvider"]
