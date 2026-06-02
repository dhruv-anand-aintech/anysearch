"""Unified request and response types shared by every provider."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterator, List, Optional

# Cross-provider "lowest common denominator" enums.
SAFE_SEARCH_VALUES = ("off", "moderate", "strict")
MODE_VALUES = ("fast", "balanced", "deep")
SEARCH_TYPE_VALUES = ("web", "news")


@dataclass
class SearchRequest:
    """Normalized, provider-agnostic search request.

    Only ``query`` is required. Every other field is a "lowest common denominator"
    parameter that anysearch translates into each provider's native parameter where
    the provider supports it. Provider-specific knobs that are not part of the common
    set are passed through verbatim via :attr:`extra`.
    """

    query: str
    max_results: int = 10
    search_type: str = "web"  # "web" | "news"
    country: Optional[str] = None  # ISO 3166-1 alpha-2, e.g. "us"
    language: Optional[str] = None  # ISO 639-1, e.g. "en"
    include_domains: List[str] = field(default_factory=list)
    exclude_domains: List[str] = field(default_factory=list)
    start_published_date: Optional[str] = None  # ISO 8601 / YYYY-MM-DD
    end_published_date: Optional[str] = None  # ISO 8601 / YYYY-MM-DD
    safe_search: Optional[str] = None  # off | moderate | strict

    # Unified "extra param modes" — optional capabilities mapped per provider.
    mode: Optional[str] = None  # fast | balanced | deep  (depth/quality knob)
    answer: bool = False  # request a synthesized, cited answer where supported
    include_content: bool = False  # return full page text where supported
    include_summary: bool = False  # return a per-result AI summary where supported
    highlights: bool = False  # return query-relevant excerpts where supported

    # Raw provider-specific passthrough (merged into the native request).
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.query or not str(self.query).strip():
            raise ValueError("`query` must be a non-empty string")
        if self.safe_search is not None and self.safe_search not in SAFE_SEARCH_VALUES:
            raise ValueError(f"safe_search must be one of {SAFE_SEARCH_VALUES}")
        if self.mode is not None and self.mode not in MODE_VALUES:
            raise ValueError(f"mode must be one of {MODE_VALUES}")
        if self.search_type not in SEARCH_TYPE_VALUES:
            raise ValueError(f"search_type must be one of {SEARCH_TYPE_VALUES}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """A single normalized search result."""

    title: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None  # short description, as returned by the engine
    text: Optional[str] = None  # full page content, if requested & supported
    summary: Optional[str] = None  # AI-generated summary, if requested & supported
    highlights: List[str] = field(default_factory=list)  # relevant excerpts
    score: Optional[float] = None  # relevance score, if the provider exposes one
    published_date: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None  # the result's domain/host
    raw: Dict[str, Any] = field(default_factory=dict)  # the provider's raw result

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResponse:
    """A normalized response wrapping a list of :class:`SearchResult`."""

    provider: str
    query: str
    results: List[SearchResult] = field(default_factory=list)
    answer: Optional[str] = None  # synthesized answer, if requested & supported
    total_results: Optional[int] = None
    latency_ms: Optional[float] = None
    request_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)  # full provider payload

    def __iter__(self) -> Iterator[SearchResult]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, index: int) -> SearchResult:
        return self.results[index]

    @property
    def urls(self) -> List[str]:
        return [r.url for r in self.results if r.url]

    def to_dict(self, *, include_raw: bool = False) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "provider": self.provider,
            "query": self.query,
            "answer": self.answer,
            "total_results": self.total_results,
            "latency_ms": self.latency_ms,
            "request_id": self.request_id,
            "results": [r.to_dict() for r in self.results],
        }
        if not include_raw:
            for r in data["results"]:
                r.pop("raw", None)
        else:
            data["raw"] = self.raw
        return data
