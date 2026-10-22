"""xAI Responses API with the hosted `web_search` tool."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

DEFAULT_MODEL = "grok-4.7"


def _model_name(config: Dict[str, Any]) -> str:
    return str(config.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _answer(data: Dict[str, Any]) -> Optional[str]:
    texts = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                if content.get("text"):
                    texts.append(str(content["text"]))
    if texts:
        return "\n".join(texts)
    value = data.get("output_text")
    return str(value) if value else None


def _citations(data: Dict[str, Any]) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
    out: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []
    seen = set()
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text") or ""
            for annotation in content.get("annotations") or []:
                if not isinstance(annotation, dict):
                    continue
                url = annotation.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                start = annotation.get("start_index")
                end = annotation.get("end_index")
                snippet = None
                if isinstance(start, int) and isinstance(end, int) and text:
                    snippet = text[max(0, start - 100) : min(len(text), end + 100)].strip()
                out.append((url, annotation.get("title"), snippet))
    for citation in data.get("citations") or []:
        url = citation if isinstance(citation, str) else citation.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        title = None if isinstance(citation, str) else citation.get("title")
        out.append((url, title, None))
    return out


class XAIProvider(BaseProvider):
    name = "xai"
    aliases = ("grok", "x_ai")
    env_keys = ("XAI_API_KEY",)
    default_base_url = "https://api.x.ai"
    capabilities = frozenset({Capability.DOMAINS, Capability.ANSWER})

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set XAI_API_KEY. Uses POST /v1/responses with the hosted `web_search` tool; "
            f"default model `{DEFAULT_MODEL}` (override via provider_config xai.model)."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        config = {**self.config, **req.extra}
        tool: Dict[str, Any] = {"type": "web_search"}
        filters: Dict[str, Any] = {}
        if req.include_domains:
            filters["allowed_domains"] = req.include_domains
        if req.exclude_domains:
            filters["excluded_domains"] = req.exclude_domains
        if filters:
            tool["filters"] = filters
        body: Dict[str, Any] = {
            "model": _model_name(config),
            "input": req.query,
            "tools": [tool],
        }
        extra = {k: v for k, v in req.extra.items() if k != "model"}
        body.update(extra)
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/v1/responses",
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
        results = [
            self._result(title=title, url=url, snippet=snippet, raw={"url": url, "title": title})
            for url, title, snippet in _citations(data)[: req.max_results]
        ]
        return self._response(
            req,
            results,
            data,
            answer=_answer(data),
            request_id=data.get("id"),
            elapsed_ms=elapsed_ms,
        )
