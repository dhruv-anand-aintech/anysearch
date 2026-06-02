"""SerpApi multi-engine request building."""

from __future__ import annotations

from anysearch.providers.serpapi import SerpApiProvider
from anysearch.providers.serpapi_engines import (
    resolve_serpapi_engine,
    normalize_engine,
)
from anysearch.types import SearchRequest


def test_normalize_engine_aliases():
    assert normalize_engine("DDG") == "duckduckgo"
    assert normalize_engine("goog") == "google"


def test_resolve_news_engine():
    assert (
        resolve_serpapi_engine(
            engine="bing",
            default_engine="google",
            search_type="news",
            extra={},
        )
        == "bing_news"
    )


def test_prepare_bing_web():
    p = SerpApiProvider(api_key="test-key", engine="bing")
    prep = p.prepare(SearchRequest(query="coffee"))
    assert prep.params["engine"] == "bing"
    assert prep.params["q"] == "coffee"
    assert "tbm" not in prep.params


def test_prepare_baidu_with_locale():
    p = SerpApiProvider(api_key="test-key")
    prep = p.prepare(
        SearchRequest(query="test", engine="baidu", country="cn", language="zh")
    )
    assert prep.params["engine"] == "baidu"


def test_prepare_yandex_news():
    p = SerpApiProvider(api_key="test-key", default_engine="yandex")
    prep = p.prepare(SearchRequest(query="news", search_type="news"))
    assert prep.params["engine"] == "yandex"


def test_prepare_google_news_uses_google_news_engine():
    p = SerpApiProvider(api_key="test-key")
    prep = p.prepare(SearchRequest(query="ai", search_type="news"))
    assert prep.params["engine"] == "google_news"
    assert "tbm" not in prep.params


def test_request_engine_overrides_default():
    p = SerpApiProvider(api_key="test-key", engine="google")
    prep = p.prepare(SearchRequest(query="x", engine="yandex"))
    assert prep.params["engine"] == "yandex"
