"""DuckDuckGo — keyless fallback provider (parses the HTML results endpoint).

This needs no API key, which makes it a useful zero-config default. It scrapes the
``html.duckduckgo.com`` endpoint, so it is best-effort and may break if DuckDuckGo
changes their markup. For production workloads prefer a keyed provider.
"""

from __future__ import annotations

import html
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from .._http import PreparedRequest
from ..types import SearchRequest, SearchResponse
from .base import BaseProvider, Capability

_SAFE = {"off": "-2", "moderate": "-1", "strict": "1"}
_RESULT_RE = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
    re.DOTALL,
)
_SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>(?P<snippet>.*?)</a>', re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text or "")).strip()


def _unwrap(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return unquote(uddg[0])
    return href


class DuckDuckGoProvider(BaseProvider):
    name = "duckduckgo"
    aliases = ("ddg",)
    requires_key = False
    default_base_url = "https://html.duckduckgo.com"
    extra_package = "ddgs"
    native_client = ("ddgs", ("DDGS",))
    capabilities = frozenset({Capability.COUNTRY, Capability.SAFE_SEARCH})

    def prepare(self, req: SearchRequest) -> PreparedRequest:
        data = {"q": req.query}
        if req.country:
            data["kl"] = f"{req.country.lower()}-en"
        if req.safe_search:
            data["kp"] = _SAFE.get(req.safe_search, "-1")
        return PreparedRequest(
            method="POST",
            url=f"{self.base_url}/html/",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html",
            },
            data=data,
        )

    def parse(self, response: httpx.Response, req: SearchRequest, elapsed_ms: float) -> SearchResponse:
        body = response.text
        snippets = [_clean(m.group("snippet")) for m in _SNIPPET_RE.finditer(body)]
        results = []
        for idx, match in enumerate(_RESULT_RE.finditer(body)):
            url = _unwrap(match.group("href"))
            results.append(
                self._result(
                    title=_clean(match.group("title")),
                    url=url,
                    snippet=snippets[idx] if idx < len(snippets) else None,
                    score=idx + 1,
                    raw={"href": match.group("href")},
                )
            )
        return self._response(req, results, {"html_results": len(results)}, elapsed_ms=elapsed_ms)
