"""anysearch — one interface for every web search API.

Quickstart::

    import anysearch

    # Auto-selects a provider from whatever API keys are set in the environment.
    resp = anysearch.search("who won the 2026 super bowl?", max_results=5)
    for r in resp:
        print(r.title, r.url)

    # Or target a specific provider with the same parameters.
    resp = anysearch.search("vector databases", provider="exa", include_content=True)
"""

from __future__ import annotations

from .client import (
    AnySearch,
    asearch,
    list_providers,
    native,
    provider_info,
    search,
)
from .exceptions import (
    AnySearchError,
    AuthenticationError,
    BadRequestError,
    ConfigurationError,
    MissingAPIKeyError,
    NoProviderAvailableError,
    ProviderConnectionError,
    ProviderError,
    ProviderNotFoundError,
    ProviderTimeoutError,
    RateLimitError,
    UnsupportedParameterError,
)
from .providers.base import Capability
from .types import SearchRequest, SearchResponse, SearchResult

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "AnySearch",
    "search",
    "asearch",
    "list_providers",
    "provider_info",
    "native",
    "Capability",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "AnySearchError",
    "ConfigurationError",
    "MissingAPIKeyError",
    "ProviderNotFoundError",
    "NoProviderAvailableError",
    "UnsupportedParameterError",
    "ProviderError",
    "AuthenticationError",
    "RateLimitError",
    "BadRequestError",
    "ProviderTimeoutError",
    "ProviderConnectionError",
]
