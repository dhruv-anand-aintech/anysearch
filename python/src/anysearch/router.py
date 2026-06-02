"""Provider selection and cross-provider capability handling."""

from __future__ import annotations

import dataclasses
import os
import warnings
from typing import Dict, List, Optional, Type

from .exceptions import NoProviderAvailableError, UnsupportedParameterError
from .providers import DEFAULT_PRIORITY, BaseProvider, get_provider_class
from .providers.base import PARAM_CAPABILITY, _is_active
from .types import SearchRequest

ON_UNSUPPORTED_VALUES = ("ignore", "warn", "error")


def available_providers(env: Optional[Dict[str, str]] = None) -> List[str]:
    """Return the names of every provider that is currently configured."""
    if env is None:
        env = os.environ  # type: ignore[assignment]
    out = []
    for name in DEFAULT_PRIORITY:
        cls = get_provider_class(name)
        if cls.is_configured(env):
            out.append(name)
    return out


def select_provider(
    env: Optional[Dict[str, str]] = None,
    priority: Optional[List[str]] = None,
) -> str:
    """Pick the best configured provider, honoring env override then priority."""
    if env is None:
        env = os.environ  # type: ignore[assignment]
    override = env.get("ANYSEARCH_PROVIDER") or env.get("ANYSEARCH_SEARCH_PROVIDER")
    if override:
        return override.strip().lower()
    order = priority or DEFAULT_PRIORITY
    for name in order:
        if get_provider_class(name).is_configured(env):
            return name
    raise NoProviderAvailableError(
        "No search provider is configured. Set an API key (e.g. EXA_API_KEY, "
        "TAVILY_API_KEY, BRAVE_API_KEY) or point SEARXNG_BASE_URL at an instance. "
        "DuckDuckGo works with no key if reachable."
    )


def unsupported_params(provider_cls: Type[BaseProvider], req: SearchRequest) -> List[str]:
    """Names of unified fields the caller set that the provider cannot honor."""
    out = []
    for field, capability in PARAM_CAPABILITY.items():
        if _is_active(field, getattr(req, field)) and capability not in provider_cls.capabilities:
            out.append(field)
    # `search_type="news"` requires the NEWS capability.
    from .providers.base import Capability

    if req.search_type == "news" and Capability.NEWS not in provider_cls.capabilities:
        out.append("search_type=news")
    return out


def enforce_capabilities(
    provider_cls: Type[BaseProvider],
    req: SearchRequest,
    on_unsupported: str = "warn",
) -> SearchRequest:
    """Apply the on_unsupported policy, returning a request safe for the provider."""
    if on_unsupported not in ON_UNSUPPORTED_VALUES:
        raise ValueError(f"on_unsupported must be one of {ON_UNSUPPORTED_VALUES}")
    missing = unsupported_params(provider_cls, req)
    if not missing:
        return req
    if on_unsupported == "error":
        raise UnsupportedParameterError(provider_cls.name, missing)
    if on_unsupported == "warn":
        warnings.warn(
            f"Provider '{provider_cls.name}' does not support {missing}; ignoring "
            f"those parameter(s). Pass on_unsupported='ignore' to silence or 'error' to raise.",
            stacklevel=3,
        )
    # Reset unsupported fields to their dataclass defaults so build logic skips them.
    defaults = SearchRequest(query=req.query)
    resets = {}
    for field in missing:
        if field == "search_type=news":
            resets["search_type"] = "web"
        else:
            resets[field] = getattr(defaults, field)
    return dataclasses.replace(req, **resets)
