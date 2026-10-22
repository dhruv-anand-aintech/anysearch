"""Anthropic Claude Messages API with the server-side web search tool."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_TOOL = "web_search_20250305"
API_VERSION = "2023-06-01"


def _model_name(config: Dict[str, Any]) -> str:
    return str(config.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _tool(config: Dict[str, Any], req: SearchRequest) -> Dict[str, Any]:
    tool: Dict[str, Any] = {
        "type": str(config.get("tool_type") or DEFAULT_TOOL),
        "name": "web_search",
    }
    if req.include_domains:
        tool["allowed_domains"] = req.include_domains
    if req.exclude_domains:
        tool["blocked_domains"] = req.exclude_domains
    return tool


def _text(data: Dict[str, Any]) -> Optional[str]:
    texts = [
        str(block.get("text"))
        for block in data.get("content") or []
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
    ]
    return "\n".join(texts) if texts else None


def _citations(data: Dict[str, Any]) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
    """Collect web_search_tool_result entries and inline url citations."""
    out: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []
    seen = set()
    for block in data.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "web_search_tool_result":
            content = block.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "web_search_result":
                    continue
                url = item.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                out.append((url, item.get("title"), item.get("page_age")))
        if block.get("type") == "text":
            text = block.get("text") or ""
            for citation in block.get("citations") or []:
                if not isinstance(citation, dict):
                    continue
                url = citation.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                snippet = citation.get("cited_text")
                if not snippet:
                    start = citation.get("start_char_index")
                    end = citation.get("end_char_index")
                    if isinstance(start, int) and isinstance(end, int) and text:
                        snippet = text[max(0, start - 100) : min(len(text), end + 100)]
                out.append((url, citation.get("title"), snippet))
    return out


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    aliases = ("claude",)
    env_keys = ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")
    default_base_url = "https://api.anthropic.com"
    capabilities = frozenset({Capability.DOMAINS, Capability.ANSWER})

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set ANTHROPIC_API_KEY. Uses POST /v1/messages with the server-side "
            f"`{DEFAULT_TOOL}` web search tool; default model `{DEFAULT_MODEL}`."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        config = {**self.config, **req.extra}
        body: Dict[str, Any] = {
            "model": _model_name(config),
            "max_tokens": int(config.get("max_tokens") or 4096),
            "messages": [{"role": "user", "content": req.query}],
            "tools": [_tool(config, req)],
        }
        extra = {k: v for k, v in req.extra.items() if k != "model"}
        body.update(extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": API_VERSION,
                "Content-Type": "application/json",
            },
            json=body,
        )

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:
        data = response.json()
        results = [
            self._result(title=title, url=url, snippet=snippet, raw={"url": url, "title": title})
            for url, title, snippet in _citations(data)[: req.max_results]
        ]
        return self._response(
            req,
            results,
            data,
            answer=_text(data),
            request_id=data.get("id"),
            elapsed_ms=elapsed_ms,
        )
