"""Base classes, capability flags, and shared helpers for providers."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import httpx

from .._http import PreparedRequest, asend, send
from ..types import SearchRequest, SearchResponse, SearchResult


class Capability:
    """Optional features a provider may support beyond the required ``query``."""

    DOMAINS = "domains"  # include_domains / exclude_domains
    COUNTRY = "country"
    LANGUAGE = "language"
    DATE = "date"  # start/end published date
    SAFE_SEARCH = "safe_search"
    MODE = "mode"  # fast | balanced | deep
    ANSWER = "answer"  # synthesized, cited answer
    CONTENT = "content"  # full page text
    SUMMARY = "summary"  # per-result AI summary
    HIGHLIGHTS = "highlights"  # query-relevant excerpts
    NEWS = "news"  # dedicated news search
    ENGINE = "engine"  # SerpApi-style backend selector (bing, baidu, yandex, …)


# Maps a unified request field to the capability it requires.
PARAM_CAPABILITY: Dict[str, str] = {
    "include_domains": Capability.DOMAINS,
    "exclude_domains": Capability.DOMAINS,
    "country": Capability.COUNTRY,
    "language": Capability.LANGUAGE,
    "start_published_date": Capability.DATE,
    "end_published_date": Capability.DATE,
    "safe_search": Capability.SAFE_SEARCH,
    "mode": Capability.MODE,
    "answer": Capability.ANSWER,
    "include_content": Capability.CONTENT,
    "include_summary": Capability.SUMMARY,
    "highlights": Capability.HIGHLIGHTS,
    "engine": Capability.ENGINE,
}


def _is_active(field: str, value: Any) -> bool:
    """True if a unified field was actually requested by the caller."""
    if value is None:
        return False
    if field in ("include_domains", "exclude_domains"):
        return bool(value)
    if field == "search_type":
        return value == "news"
    if isinstance(value, bool):
        return value
    return bool(value)


def domain_of(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        host = urlparse(url).netloc or urlparse("//" + url).netloc
    except Exception:
        return None
    return host[4:] if host.startswith("www.") else host or None


class BaseProvider:
    """Base class every provider adapter extends.

    Subclasses implement :meth:`prepare` (build a native HTTP request) and
    :meth:`parse` (normalize the response). The base class handles credential
    discovery, sync/async execution, and capability reporting.
    """

    name: str = ""
    aliases: Tuple[str, ...] = ()
    env_keys: Tuple[str, ...] = ()
    base_url_env: Tuple[str, ...] = ()
    default_base_url: str = ""
    requires_key: bool = True
    requires_base_url: bool = False
    capabilities: frozenset = frozenset()
    # PyPI extra that installs this provider's official SDK (None = REST only).
    extra_package: Optional[str] = None
    # (module, [candidate class names]) for the native() escape hatch.
    native_client: Optional[Tuple[str, Sequence[str]]] = None

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        **config: Any,
    ) -> None:
        self._env = env if env is not None else os.environ  # type: ignore[assignment]
        self.api_key = api_key or self.key_from_env(self._env)
        self.base_url = (
            base_url or self.base_url_from_env(self._env) or self.default_base_url
        ).rstrip("/")
        self.config = config

    # -- credential / configuration discovery ------------------------------

    @classmethod
    def key_from_env(cls, env: Optional[Dict[str, str]] = None) -> Optional[str]:
        if env is None:
            env = os.environ  # type: ignore[assignment]
        for key in cls.env_keys:
            val = env.get(key)
            if val:
                return val
        return None

    @classmethod
    def base_url_from_env(cls, env: Optional[Dict[str, str]] = None) -> Optional[str]:
        if env is None:
            env = os.environ  # type: ignore[assignment]
        for key in cls.base_url_env:
            val = env.get(key)
            if val:
                return val
        return None

    @classmethod
    def is_configured(cls, env: Optional[Dict[str, str]] = None) -> bool:
        """Whether the provider has everything it needs to make a request."""
        if env is None:
            env = os.environ  # type: ignore[assignment]
        if cls.requires_base_url and not cls.base_url_from_env(env) and not cls.default_base_url:
            return False
        if cls.requires_key:
            return bool(cls.key_from_env(env))
        return True

    @classmethod
    def config_hint(cls) -> str:
        parts = []
        if cls.requires_key and cls.env_keys:
            parts.append(f"Set {cls.env_keys[0]}.")
        if cls.requires_base_url and cls.base_url_env:
            parts.append(f"Set {cls.base_url_env[0]}.")
        if cls.extra_package:
            parts.append(
                "Optional native SDK: pip install "
                f"'anysearch-sdk[{cls.name}] @ git+https://github.com/dhruv-anand-aintech/anysearch.git@main#subdirectory=python'."
            )
        return " ".join(parts)

    # -- request execution -------------------------------------------------

    def prepare(self, req: SearchRequest) -> PreparedRequest:  # pragma: no cover
        raise NotImplementedError

    def parse(
        self, response: httpx.Response, req: SearchRequest, elapsed_ms: float
    ) -> SearchResponse:  # pragma: no cover
        raise NotImplementedError

    def _require_key(self) -> None:
        if self.requires_key and not self.api_key:
            from ..exceptions import MissingAPIKeyError

            raise MissingAPIKeyError(self.name, self.config_hint())
        if self.requires_base_url and not self.base_url:
            from ..exceptions import ConfigurationError

            raise ConfigurationError(f"Provider '{self.name}' requires a base URL. {self.config_hint()}")

    def search(
        self,
        req: SearchRequest,
        *,
        timeout: float = 30.0,
        client: Optional[httpx.Client] = None,
    ) -> SearchResponse:
        self._require_key()
        prepared = self.prepare(req)
        import time

        start = time.perf_counter()
        response = send(self.name, prepared, timeout=timeout, client=client)
        elapsed = (time.perf_counter() - start) * 1000
        return self.parse(response, req, elapsed)

    async def asearch(
        self,
        req: SearchRequest,
        *,
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> SearchResponse:
        self._require_key()
        prepared = self.prepare(req)
        import time

        start = time.perf_counter()
        response = await asend(self.name, prepared, timeout=timeout, client=client)
        elapsed = (time.perf_counter() - start) * 1000
        return self.parse(response, req, elapsed)

    # -- helpers for subclasses -------------------------------------------

    def _result(self, **kwargs: Any) -> SearchResult:
        if kwargs.get("source") is None:
            kwargs["source"] = domain_of(kwargs.get("url"))
        return SearchResult(**kwargs)

    def _response(
        self,
        req: SearchRequest,
        results: List[SearchResult],
        raw: Dict[str, Any],
        *,
        answer: Optional[str] = None,
        total_results: Optional[int] = None,
        request_id: Optional[str] = None,
        elapsed_ms: Optional[float] = None,
    ) -> SearchResponse:
        # Respect max_results uniformly, even for engines without a count param.
        if req.max_results and len(results) > req.max_results:
            results = results[: req.max_results]
        return SearchResponse(
            provider=self.name,
            query=req.query,
            results=results,
            answer=answer,
            total_results=total_results,
            latency_ms=round(elapsed_ms, 1) if elapsed_ms is not None else None,
            request_id=request_id,
            raw=raw,
        )

    def make_native(self) -> Any:
        """Return an instance of the provider's official SDK client (escape hatch)."""
        from ..exceptions import ConfigurationError

        if not self.native_client:
            raise ConfigurationError(
                f"Provider '{self.name}' has no official SDK; it is REST-only via anysearch."
            )
        module_name, class_names = self.native_client
        try:
            module = __import__(module_name, fromlist=list(class_names))
        except ImportError as exc:
            raise ConfigurationError(
                f"Native SDK for '{self.name}' is not installed. "
                "Install it with: pip install "
                f"'anysearch-sdk[{self.name}] @ "
                "git+https://github.com/dhruv-anand-aintech/anysearch.git@main#subdirectory=python'"
            ) from exc
        for cls_name in class_names:
            cls = getattr(module, cls_name, None)
            if cls is None:
                continue
            try:
                return cls(api_key=self.api_key)
            except TypeError:
                try:
                    return cls()
                except Exception:  # noqa: BLE001
                    continue
        raise ConfigurationError(
            f"Could not construct a native client for '{self.name}' from module '{module_name}'."
        )
