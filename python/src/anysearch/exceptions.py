"""Exception hierarchy for anysearch.

All errors raised by the SDK inherit from :class:`AnySearchError`, so callers can
catch a single base type. Provider HTTP failures are normalized into the
``Authentication``/``RateLimit``/``BadRequest``/``ProviderError`` family so that
behaviour is consistent regardless of which underlying API was used.
"""

from __future__ import annotations

from typing import Any, Optional


class AnySearchError(Exception):
    """Base class for every error raised by anysearch."""


class ConfigurationError(AnySearchError):
    """Raised when the SDK is misconfigured (bad arguments, etc.)."""


class MissingAPIKeyError(ConfigurationError):
    """Raised when a provider is selected but its credentials are not set."""

    def __init__(self, provider: str, hint: str = ""):
        self.provider = provider
        msg = f"No credentials configured for provider '{provider}'."
        if hint:
            msg += f" {hint}"
        super().__init__(msg)


class ProviderNotFoundError(ConfigurationError):
    """Raised when an unknown provider name is requested."""

    def __init__(self, provider: str, known: Optional[list] = None):
        self.provider = provider
        msg = f"Unknown search provider '{provider}'."
        if known:
            msg += f" Available: {', '.join(sorted(known))}."
        super().__init__(msg)


class NoProviderAvailableError(ConfigurationError):
    """Raised when auto-selection finds no configured provider."""


class UnsupportedParameterError(AnySearchError):
    """Raised when ``on_unsupported='error'`` and a param is not supported."""

    def __init__(self, provider: str, params: list):
        self.provider = provider
        self.params = params
        super().__init__(
            f"Provider '{provider}' does not support parameter(s): {', '.join(params)}."
        )


class ProviderError(AnySearchError):
    """A provider returned an error response."""

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        status_code: Optional[int] = None,
        response: Any = None,
    ):
        self.provider = provider
        self.status_code = status_code
        self.response = response
        prefix = f"[{provider}]"
        if status_code is not None:
            prefix += f" HTTP {status_code}"
        super().__init__(f"{prefix}: {message}")


class AuthenticationError(ProviderError):
    """401/403 from a provider — usually a bad or missing API key."""


class RateLimitError(ProviderError):
    """429 from a provider."""


class BadRequestError(ProviderError):
    """400/422 from a provider — usually invalid parameters."""


class ProviderTimeoutError(ProviderError):
    """The request to the provider timed out."""


class ProviderConnectionError(ProviderError):
    """A network-level error occurred talking to the provider."""
