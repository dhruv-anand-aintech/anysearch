"""Thin HTTP layer that normalizes provider errors into anysearch exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

from .exceptions import (
    AuthenticationError,
    BadRequestError,
    ProviderConnectionError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)

DEFAULT_TIMEOUT = 30.0
USER_AGENT = "anysearch-python/0.1.0"


@dataclass
class PreparedRequest:
    """A provider-native HTTP request, ready to send."""

    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None
    data: Optional[Any] = None  # form-encoded body (e.g. DuckDuckGo HTML endpoint)


def _short(text: str, limit: int = 500) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + "…"


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except Exception:
        return _short(response.text)
    if isinstance(body, dict):
        for key in ("error", "message", "detail", "error_message", "Message"):
            val = body.get(key)
            if isinstance(val, dict):
                val = val.get("message") or val.get("detail") or str(val)
            if val:
                return _short(str(val))
    return _short(str(body))


def raise_for_status(provider: str, response: httpx.Response) -> None:
    """Map HTTP status codes onto the anysearch exception hierarchy."""
    code = response.status_code
    if code < 400:
        return
    message = _error_message(response)
    try:
        payload = response.json()
    except Exception:
        payload = response.text
    if code in (401, 403):
        raise AuthenticationError(message, provider=provider, status_code=code, response=payload)
    if code == 429:
        raise RateLimitError(message, provider=provider, status_code=code, response=payload)
    if code in (400, 422):
        raise BadRequestError(message, provider=provider, status_code=code, response=payload)
    raise ProviderError(message, provider=provider, status_code=code, response=payload)


def _merge_headers(headers: Dict[str, str]) -> Dict[str, str]:
    merged = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    merged.update(headers or {})
    return merged


def send(
    provider: str,
    prepared: PreparedRequest,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    client: Optional[httpx.Client] = None,
) -> httpx.Response:
    """Send a prepared request synchronously and validate the status."""
    headers = _merge_headers(prepared.headers)
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=timeout, follow_redirects=True)
    try:
        response = client.request(
            prepared.method,
            prepared.url,
            headers=headers,
            params=prepared.params,
            json=prepared.json,
            data=prepared.data,
        )
    except httpx.TimeoutException as exc:
        raise ProviderTimeoutError(str(exc), provider=provider) from exc
    except httpx.HTTPError as exc:
        raise ProviderConnectionError(str(exc), provider=provider) from exc
    finally:
        if own_client:
            client.close()
    raise_for_status(provider, response)
    return response


async def asend(
    provider: str,
    prepared: PreparedRequest,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    client: Optional[httpx.AsyncClient] = None,
) -> httpx.Response:
    """Send a prepared request asynchronously and validate the status."""
    headers = _merge_headers(prepared.headers)
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
    try:
        response = await client.request(
            prepared.method,
            prepared.url,
            headers=headers,
            params=prepared.params,
            json=prepared.json,
            data=prepared.data,
        )
    except httpx.TimeoutException as exc:
        raise ProviderTimeoutError(str(exc), provider=provider) from exc
    except httpx.HTTPError as exc:
        raise ProviderConnectionError(str(exc), provider=provider) from exc
    finally:
        if own_client:
            await client.aclose()
    raise_for_status(provider, response)
    return response
