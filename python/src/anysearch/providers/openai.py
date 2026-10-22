"""OpenAI Responses API with the hosted `web_search` tool."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

DEFAULT_MODEL = "gpt-5.5"
_EFFORT = {"fast": "low", "balanced": "medium", "deep": "high"}
_CONTEXT = {"fast": "low", "balanced": "medium", "deep": "high"}


def _model_name(config: Dict[str, Any]) -> str:
    return str(config.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _query(req: SearchRequest) -> str:
    """OpenAI filters allow-lists; excluded domains become `-site:` operators."""
    parts = [req.query]
    for domain in req.exclude_domains:
        parts.append(f"-site:{domain}")
    return " ".join(part for part in parts if part).strip()


def _citations(data: Dict[str, Any]) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
    """Return (url, title, snippet) from message annotations, deduplicated by URL."""
    seen = set()
    out: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []
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
                if annotation.get("type") not in ("url_citation", None):
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
    return out


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


class OpenAIProvider(BaseProvider):
    name = "openai"
    env_keys = ("OPENAI_API_KEY",)
    default_base_url = "https://api.openai.com"
    capabilities = frozenset({Capability.DOMAINS, Capability.MODE, Capability.ANSWER})

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set OPENAI_API_KEY. Uses POST /v1/responses with the hosted `web_search` tool; "
            f"default model `{DEFAULT_MODEL}` (override via provider_config openai.model)."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        config = {**self.config, **req.extra}
        model = _model_name(config)
        tool: Dict[str, Any] = {"type": "web_search"}
        if req.include_domains:
            tool["filters"] = {"allowed_domains": req.include_domains}
        if req.mode:
            tool["search_context_size"] = _CONTEXT[req.mode]
        body: Dict[str, Any] = {
            "model": model,
            "input": _query(req),
            "tools": [tool],
        }
        if req.mode:
            body["reasoning"] = {"effort": _EFFORT[req.mode]}
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
            total_results=len(results),
            request_id=data.get("id"),
            elapsed_ms=elapsed_ms,
        )
