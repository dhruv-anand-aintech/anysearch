"""Google Gemini API with Google Search grounding — synthesized answers and web sources."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

DEFAULT_MODEL = "gemini-2.5-flash"


def _model_name(config: Dict[str, Any]) -> str:
    return str(config.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _text_from_candidate(candidate: Dict[str, Any]) -> Optional[str]:
    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
    joined = "\n".join(t for t in texts if t)
    return joined or None


def _grounding_chunks(meta: Dict[str, Any]) -> List[Tuple[Optional[str], Optional[str]]]:
    raw = meta.get("groundingChunks") or meta.get("grounding_chunks") or []
    out: List[Tuple[Optional[str], Optional[str]]] = []
    seen: set[str] = set()
    for chunk in raw:
        if not isinstance(chunk, dict):
            continue
        web = chunk.get("web") or {}
        uri = web.get("uri") if isinstance(web, dict) else None
        title = web.get("title") if isinstance(web, dict) else None
        key = uri or title or ""
        if key in seen:
            continue
        if key:
            seen.add(key)
        out.append((uri, title))
    return out


class GeminiProvider(BaseProvider):
    name = "gemini"
    aliases = ("google_gemini", "gemini_api")
    env_keys = ("GEMINI_API_KEY", "GOOGLE_GEMINI_API_KEY")
    default_base_url = "https://generativelanguage.googleapis.com"
    extra_package = "google-genai"
    native_client = ("google.genai", ("Client",))
    capabilities = frozenset({Capability.ANSWER})

    @classmethod
    def config_hint(cls) -> str:
        return (
            "Set GEMINI_API_KEY. Uses `generateContent` with the `google_search` tool "
            f"(default model `{DEFAULT_MODEL}`; override via provider_config gemini.model)."
        )

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        model = _model_name({**self.config, **req.extra})
        body: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": req.query}]}],
            "tools": [{"google_search": {}}],
        }
        extra = {k: v for k, v in req.extra.items() if k != "model"}
        if "generationConfig" in extra:
            body["generationConfig"] = extra.pop("generationConfig")
        body.update(extra)
        url = f"{self.base_url}/v1beta/models/{model}:generateContent"
        return PreparedRequest(
            method="POST",
            url=url,
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            json=body,
        )

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:
        data = response.json()
        candidates = data.get("candidates") or []
        candidate = candidates[0] if candidates else {}
        text = _text_from_candidate(candidate) if isinstance(candidate, dict) else None
        meta = (
            (candidate.get("groundingMetadata") or candidate.get("grounding_metadata") or {})
            if isinstance(candidate, dict)
            else {}
        )
        results = []
        for uri, title in _grounding_chunks(meta)[: req.max_results]:
            results.append(
                self._result(
                    title=title,
                    url=uri,
                    snippet=title,
                    raw={"uri": uri, "title": title},
                )
            )
        answer = text if req.answer else None
        return self._response(
            req,
            results,
            data,
            answer=answer,
            request_id=data.get("responseId"),
            elapsed_ms=elapsed_ms,
        )
