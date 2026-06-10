"""Public API: the :class:`AnySearch` client plus module-level helpers."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .exceptions import MissingAPIKeyError, ProviderError
from .providers import BaseProvider, get_provider_class, list_provider_names
from .router import available_providers, enforce_capabilities, select_provider
from .types import SearchRequest, SearchResponse

# Unified request fields the client accepts as first-class keyword arguments.
_UNIFIED_FIELDS = (
    "max_results",
    "search_type",
    "engine",
    "country",
    "language",
    "include_domains",
    "exclude_domains",
    "start_published_date",
    "end_published_date",
    "safe_search",
    "mode",
    "answer",
    "include_content",
    "include_summary",
    "highlights",
)
_RECOVERABLE = (ProviderError, MissingAPIKeyError)


class AnySearch:
    """A configurable search client that adapts one interface to many providers."""

    def __init__(
        self,
        provider: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        fallbacks: Optional[List[str]] = None,
        on_unsupported: str = "warn",
        timeout: float = 30.0,
        priority: Optional[List[str]] = None,
        provider_config: Optional[Dict[str, Dict[str, Any]]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.fallbacks = fallbacks or []
        self.on_unsupported = on_unsupported
        self.timeout = timeout
        self.priority = priority
        self.provider_config = provider_config or {}
        self._env = env if env is not None else os.environ  # type: ignore[assignment]
        self._instances: Dict[str, BaseProvider] = {}

    # -- introspection -----------------------------------------------------

    def providers(self) -> List[str]:
        """Names of providers that are currently configured & ready to use."""
        return available_providers(self._env)

    @staticmethod
    def all_providers() -> List[str]:
        return list_provider_names()

    def provider_info(self) -> List[Dict[str, Any]]:
        """Capability + configuration metadata for every known provider."""
        info = []
        for name in list_provider_names():
            cls = get_provider_class(name)
            info.append(
                {
                    "name": name,
                    "aliases": list(cls.aliases),
                    "configured": cls.is_configured(self._env),
                    "requires_key": cls.requires_key,
                    "env_keys": list(cls.env_keys),
                    "capabilities": sorted(cls.capabilities),
                    "extra_package": cls.extra_package,
                    "config_hint": cls.config_hint(),
                }
            )
        return info

    def native(self, provider: Optional[str] = None) -> Any:
        """Return the provider's official SDK client (requires its extra installed)."""
        name = provider or self.provider or select_provider(self._env, self.priority)
        return self._provider(name).make_native()

    # -- provider instantiation -------------------------------------------

    def _provider(self, name: str) -> BaseProvider:
        cls = get_provider_class(name)
        canonical = cls.name
        if canonical not in self._instances:
            self._instances[canonical] = self._make_provider(cls, self.provider, self.api_key, self.base_url)
        return self._instances[canonical]

    def _make_provider(
        self,
        cls: type[BaseProvider],
        request_provider: Optional[str],
        api_key: Optional[str],
        base_url: Optional[str],
    ) -> BaseProvider:
        config = dict(self.provider_config.get(cls.name, {}))
        config.setdefault("env", self._env)
        is_named = request_provider is not None and get_provider_class(request_provider).name == cls.name
        if is_named:
            if api_key:
                config.setdefault("api_key", api_key)
            if base_url:
                config.setdefault("base_url", base_url)
        return cls(**config)

    def _provider_for_call(
        self,
        name: str,
        request_provider: Optional[str],
        api_key: Optional[str],
        base_url: Optional[str],
    ) -> BaseProvider:
        if not api_key and not base_url:
            return self._provider(name)
        cls = get_provider_class(name)
        return self._make_provider(cls, request_provider, api_key, base_url)

    # -- request building --------------------------------------------------

    def _build_request(self, name: str, query: str, params: Dict[str, Any]) -> SearchRequest:
        canonical = get_provider_class(name).name
        provider_params = params.get("provider_params") or {}
        extra = dict(params.get("extra") or {})
        for key, value in params.items():
            if key in _UNIFIED_FIELDS or key in ("extra", "provider_params"):
                continue
            extra[key] = value  # unknown kwargs pass through to the provider
        extra = {**provider_params.get(canonical, {}), **extra}

        field_kwargs = {f: params[f] for f in _UNIFIED_FIELDS if params.get(f) is not None}
        field_kwargs.setdefault("include_domains", params.get("include_domains") or [])
        field_kwargs.setdefault("exclude_domains", params.get("exclude_domains") or [])
        return SearchRequest(query=query, extra=extra, **field_kwargs)

    def _chain(self, primary: str, override_fallbacks: Optional[List[str]]) -> List[str]:
        fallbacks = override_fallbacks if override_fallbacks is not None else self.fallbacks
        seen = {get_provider_class(primary).name}
        chain = [primary]
        for fb in fallbacks:
            canonical = get_provider_class(fb).name
            if canonical not in seen:
                seen.add(canonical)
                chain.append(fb)
        return chain

    # -- search ------------------------------------------------------------

    def search(self, query: str, **params: Any) -> SearchResponse:
        provider = params.pop("provider", None) or self.provider
        override_fallbacks = params.pop("fallbacks", None)
        on_unsupported = params.pop("on_unsupported", None) or self.on_unsupported
        timeout = params.pop("timeout", None) or self.timeout
        api_key = params.pop("api_key", None)
        base_url = params.pop("base_url", None)

        primary = provider or select_provider(self._env, self.priority)
        chain = self._chain(primary, override_fallbacks)

        last_error: Optional[Exception] = None
        for name in chain:
            cls = get_provider_class(name)
            req = enforce_capabilities(cls, self._build_request(name, query, params), on_unsupported)
            try:
                return self._provider_for_call(name, provider, api_key, base_url).search(req, timeout=timeout)
            except _RECOVERABLE as exc:
                last_error = exc
                continue
        raise last_error  # type: ignore[misc]

    async def asearch(self, query: str, **params: Any) -> SearchResponse:
        provider = params.pop("provider", None) or self.provider
        override_fallbacks = params.pop("fallbacks", None)
        on_unsupported = params.pop("on_unsupported", None) or self.on_unsupported
        timeout = params.pop("timeout", None) or self.timeout
        api_key = params.pop("api_key", None)
        base_url = params.pop("base_url", None)

        primary = provider or select_provider(self._env, self.priority)
        chain = self._chain(primary, override_fallbacks)

        last_error: Optional[Exception] = None
        for name in chain:
            cls = get_provider_class(name)
            req = enforce_capabilities(cls, self._build_request(name, query, params), on_unsupported)
            try:
                return await self._provider_for_call(name, provider, api_key, base_url).asearch(req, timeout=timeout)
            except _RECOVERABLE as exc:
                last_error = exc
                continue
        raise last_error  # type: ignore[misc]


_default_client = AnySearch()


def search(query: str, **params: Any) -> SearchResponse:
    """Run a search with the default client. See :class:`AnySearch.search`."""
    return _default_client.search(query, **params)


async def asearch(query: str, **params: Any) -> SearchResponse:
    """Async variant of :func:`search`."""
    return await _default_client.asearch(query, **params)


def list_providers(configured_only: bool = False) -> List[str]:
    if configured_only:
        return available_providers()
    return list_provider_names()


def provider_info() -> List[Dict[str, Any]]:
    return _default_client.provider_info()


def native(provider: Optional[str] = None) -> Any:
    return _default_client.native(provider)
