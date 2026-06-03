"""FastAPI proxy server for the anysearch SDK.

This is intentionally smaller than LiteLLM's production proxy, but carries over the
same useful gateway shape for search: central auth, OpenAI-style endpoints, provider
routing/fallbacks, health/model listing, and simple per-key request budgets.
"""

from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

try:  # Pydantic v2
    from pydantic import field_validator
except ImportError:  # pragma: no cover - exercised only with Pydantic v1
    from pydantic import validator as field_validator  # type: ignore[assignment]

from anysearch import AnySearch
from anysearch.exceptions import (
    AnySearchError,
    AuthenticationError,
    BadRequestError,
    ConfigurationError,
    ProviderError,
    RateLimitError,
    UnsupportedParameterError,
)
from anysearch.router import select_provider

APP_TITLE = "anysearch Proxy"
APP_VERSION = "0.1.0"

bearer_scheme = HTTPBearer(auto_error=False)


class ProxyConfig(BaseModel):
    """Runtime proxy configuration.

    Environment variables:
    - ``ANYSEARCH_PROXY_KEYS``: comma-separated accepted bearer tokens.
    - ``ANYSEARCH_PROXY_ADMIN_KEYS``: comma-separated tokens allowed on admin endpoints.
    - ``ANYSEARCH_PROXY_REQUIRE_AUTH``: set ``0``/``false`` to disable auth.
    - ``ANYSEARCH_PROXY_REQUEST_LIMIT``: per-key request count limit for this process.
    """

    api_keys: List[str] = Field(default_factory=list)
    admin_keys: List[str] = Field(default_factory=list)
    require_auth: bool = True
    request_limit: Optional[int] = None

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "ProxyConfig":
        source = env or os.environ
        require_auth = source.get("ANYSEARCH_PROXY_REQUIRE_AUTH", "1").lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        request_limit_raw = source.get("ANYSEARCH_PROXY_REQUEST_LIMIT")
        request_limit = int(request_limit_raw) if request_limit_raw else None
        return cls(
            api_keys=_split_csv(source.get("ANYSEARCH_PROXY_KEYS", "")),
            admin_keys=_split_csv(source.get("ANYSEARCH_PROXY_ADMIN_KEYS", "")),
            require_auth=require_auth,
            request_limit=request_limit,
        )


@dataclass
class KeyUsage:
    requests: int = 0
    last_request_at: Optional[float] = None


@dataclass
class ProxyState:
    client: AnySearch
    config: ProxyConfig
    usage: Dict[str, KeyUsage] = field(default_factory=dict)


class SearchBody(BaseModel):
    query: str
    provider: Optional[str] = None
    fallbacks: Optional[List[str]] = None
    max_results: Optional[int] = Field(default=None, ge=1)
    search_type: Optional[str] = None
    engine: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    include_domains: List[str] = Field(default_factory=list)
    exclude_domains: List[str] = Field(default_factory=list)
    start_published_date: Optional[str] = None
    end_published_date: Optional[str] = None
    safe_search: Optional[str] = None
    mode: Optional[str] = None
    answer: Optional[bool] = None
    include_content: Optional[bool] = None
    include_summary: Optional[bool] = None
    highlights: Optional[bool] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    provider_params: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    timeout: Optional[float] = Field(default=None, gt=0)
    on_unsupported: Optional[str] = None
    include_raw: bool = False

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must be a non-empty string")
        return value

    def to_search_params(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            data = self.model_dump(exclude={"query", "include_raw"}, exclude_none=True)
        else:  # pragma: no cover - exercised only with Pydantic v1
            data = self.dict(exclude={"query", "include_raw"}, exclude_none=True)
        return data


class OpenAISearchBody(SearchBody):
    model: Optional[str] = None

    def to_search_params(self) -> Dict[str, Any]:
        data = super().to_search_params()
        model = data.pop("model", None)
        data.setdefault("provider", model)
        return data


def create_app(
    *,
    client: Optional[AnySearch] = None,
    config: Optional[ProxyConfig] = None,
    env: Optional[Mapping[str, str]] = None,
) -> FastAPI:
    proxy_config = config or ProxyConfig.from_env(env)
    state = ProxyState(client=client or AnySearch(env=dict(env) if env is not None else None), config=proxy_config)

    app = FastAPI(title=APP_TITLE, version=APP_VERSION)
    app.state.anysearch_proxy = state

    @app.exception_handler(AnySearchError)
    async def anysearch_error_handler(_: Request, exc: AnySearchError) -> JSONResponse:
        return JSONResponse(status_code=_status_for_error(exc), content={"error": _error_payload(exc)})

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return _health_payload(state.client)

    @app.get("/v1/health")
    async def v1_health() -> Dict[str, Any]:
        return _health_payload(state.client)

    @app.get("/models", dependencies=[Depends(require_key)])
    async def models() -> Dict[str, Any]:
        return _models_payload(state.client)

    @app.get("/v1/models", dependencies=[Depends(require_key)])
    async def v1_models() -> Dict[str, Any]:
        return _openai_models_payload(state.client)

    @app.post("/search")
    async def search(body: SearchBody, _: str = Depends(require_key)) -> Dict[str, Any]:
        response = await state.client.asearch(body.query, **body.to_search_params())
        return response.to_dict(include_raw=body.include_raw)

    @app.post("/v1/search")
    async def v1_search(body: OpenAISearchBody, _: str = Depends(require_key)) -> Dict[str, Any]:
        response = await state.client.asearch(body.query, **body.to_search_params())
        payload = response.to_dict(include_raw=body.include_raw)
        payload["object"] = "search.response"
        return payload

    @app.get("/admin/usage")
    async def admin_usage(_: str = Depends(require_admin_key)) -> Dict[str, Any]:
        return {
            "request_limit": state.config.request_limit,
            "keys": {
                key: {"requests": usage.requests, "last_request_at": usage.last_request_at}
                for key, usage in state.usage.items()
            },
        }

    return app


async def require_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    state: ProxyState = request.app.state.anysearch_proxy
    if not state.config.require_auth:
        return "anonymous"
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if not _contains_secret(state.config.api_keys + state.config.admin_keys, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _record_usage(state, token)
    return token


async def require_admin_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    state: ProxyState = request.app.state.anysearch_proxy
    if not state.config.require_auth:
        return "anonymous"
    if not credentials or not _contains_secret(state.config.admin_keys, credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin bearer token required",
        )
    _record_usage(state, credentials.credentials)
    return credentials.credentials


def _record_usage(state: ProxyState, token: str) -> None:
    usage = state.usage.setdefault(token, KeyUsage())
    if state.config.request_limit is not None and usage.requests >= state.config.request_limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Request limit exceeded")
    usage.requests += 1
    usage.last_request_at = time.time()


def _health_payload(client: AnySearch) -> Dict[str, Any]:
    providers = client.provider_info()
    configured = [p["name"] for p in providers if p["configured"]]
    try:
        default_provider: Optional[str] = select_provider(client._env, client.priority)  # noqa: SLF001
    except ConfigurationError:
        default_provider = None
    return {
        "status": "ok",
        "version": APP_VERSION,
        "configured_providers": configured,
        "default_provider": default_provider,
    }


def _models_payload(client: AnySearch) -> Dict[str, Any]:
    providers = client.provider_info()
    return {"providers": providers}


def _openai_models_payload(client: AnySearch) -> Dict[str, Any]:
    providers = client.provider_info()
    return {
        "object": "list",
        "data": [
            {
                "id": provider["name"],
                "object": "model",
                "owned_by": "anysearch",
                "configured": provider["configured"],
                "capabilities": provider["capabilities"],
            }
            for provider in providers
        ],
    }


def _status_for_error(exc: AnySearchError) -> int:
    if isinstance(exc, (BadRequestError, UnsupportedParameterError)):
        return status.HTTP_400_BAD_REQUEST
    if isinstance(exc, AuthenticationError):
        return status.HTTP_401_UNAUTHORIZED
    if isinstance(exc, RateLimitError):
        return status.HTTP_429_TOO_MANY_REQUESTS
    if isinstance(exc, ConfigurationError):
        return status.HTTP_400_BAD_REQUEST
    if isinstance(exc, ProviderError) and exc.status_code:
        return exc.status_code
    return status.HTTP_502_BAD_GATEWAY


def _error_payload(exc: AnySearchError) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": str(exc), "type": exc.__class__.__name__}
    if isinstance(exc, ProviderError):
        payload.update({"provider": exc.provider, "status_code": exc.status_code})
    if isinstance(exc, UnsupportedParameterError):
        payload.update({"provider": exc.provider, "params": exc.params})
    return payload


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _contains_secret(candidates: List[str], token: str) -> bool:
    return any(secrets.compare_digest(candidate, token) for candidate in candidates)


app = create_app()
