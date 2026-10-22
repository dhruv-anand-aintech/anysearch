"""Provider-specific tests for the adapters added with the full matrix coverage."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from anysearch import AnySearch
from anysearch.providers import get_provider_class


@respx.mock
def test_keenable_search_maps_mode_site_dates_and_normalizes_results():
    route = respx.post("https://api.keenable.ai/v1/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "query": "ai news",
                "mode": "realtime",
                "results": [
                    {
                        "title": "AI news",
                        "url": "https://example.com/ai",
                        "description": "A short description",
                        "snippet": "The query-relevant snippet",
                        "published_at": "2026-10-20T10:00:00Z",
                        "acquired_at": "2026-10-21T00:00:00Z",
                    }
                ],
            },
        )
    )
    client = AnySearch(provider="keenable", api_key="keen-test", env={})
    response = client.search(
        "ai news",
        max_results=5,
        mode="fast",
        include_domains=["example.com"],
        start_published_date="2026-10-01",
        end_published_date="2026-10-22",
    )
    payload = json.loads(route.calls.last.request.content)
    assert route.calls.last.request.headers["x-api-key"] == "keen-test"
    assert payload == {
        "query": "ai news",
        "mode": "realtime",
        "max_results": 5,
        "site": "example.com",
        "published_after": "2026-10-01",
        "published_before": "2026-10-22",
    }
    assert response.results[0].snippet == "The query-relevant snippet"
    assert response.results[0].published_date == "2026-10-20T10:00:00Z"


def test_keenable_balanced_and_deep_use_pro():
    provider = get_provider_class("keenable")(api_key="keen-test", env={})
    from anysearch.types import SearchRequest

    balanced = provider.prepare(SearchRequest(query="q", mode="balanced"))
    deep = provider.prepare(SearchRequest(query="q", mode="deep"))
    assert balanced.json["mode"] == "pro"
    assert deep.json["mode"] == "pro"


@respx.mock
def test_tinyfish_maps_locale_domains_news_and_normalizes_results():
    route = respx.get("https://api.search.tinyfish.ai").mock(
        return_value=httpx.Response(
            200,
            json={
                "query": "ai",
                "results": [
                    {
                        "position": 1,
                        "site_name": "Example",
                        "title": "Example result",
                        "snippet": "Snippet text",
                        "url": "https://example.com/a",
                        "date": "2026-10-20",
                        "publisher": "Example News",
                    }
                ],
                "total_results": 1,
                "page": 0,
            },
        )
    )
    client = AnySearch(provider="tinyfish", api_key="tf-test", env={})
    response = client.search(
        "ai",
        search_type="news",
        country="GB",
        language="en",
        include_domains=["example.com"],
        exclude_domains=["spam.example"],
        start_published_date="2026-10-01",
    )
    params = route.calls.last.request.url.params
    assert route.calls.last.request.headers["x-api-key"] == "tf-test"
    assert params["location"] == "GB"
    assert params["language"] == "en"
    assert params["include_domains"] == "example.com"
    assert params["exclude_domains"] == "spam.example"
    assert params["domain_type"] == "news"
    assert params["after_date"] == "2026-10-01"
    assert response.results[0].source == "Example"
    assert response.results[0].published_date == "2026-10-20"


@respx.mock
def test_deepseek_builds_query_operators_and_returns_content_summary():
    route = respx.post("https://api.deepseek.com/v1/tools/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "rerank_score": 2.4,
                        "title": "DeepSeek result",
                        "url": "https://example.com/ds",
                        "snippet": "Short",
                        "summary": "Long model-readable summary",
                        "content": "# Page body",
                        "site_name": "Example",
                        "date": "2026-06-01T00:00:00+00:00",
                    }
                ]
            },
        )
    )
    client = AnySearch(provider="deepseek", api_key="ds-test", env={})
    response = client.search(
        "agents",
        max_results=3,
        include_content=True,
        include_domains=["example.com", "docs.example"],
        exclude_domains=["spam.example"],
        language="en",
        start_published_date="2026-01-01",
        end_published_date="2026-06-01",
    )
    payload = json.loads(route.calls.last.request.content)
    assert route.calls.last.request.headers["authorization"] == "Bearer ds-test"
    assert payload["count"] == 3
    assert payload["need_content"] is True
    assert payload["query"] == (
        "agents site:example.com OR site:docs.example -site:spam.example "
        "lang:en after:2026-01-01 before:2026-06-01"
    )
    assert response.results[0].text == "# Page body"
    assert response.results[0].summary == "Long model-readable summary"
    assert response.results[0].score == 2.4


@respx.mock
def test_brightdata_posts_a_google_serp_request_and_parses_organic_items():
    route = respx.post("https://api.brightdata.com/request").mock(
        return_value=httpx.Response(
            200,
            json={
                "organic": [
                    {
                        "global_rank": 1,
                        "title": "Bright result",
                        "link": "https://example.com/b",
                        "description": "Result description",
                    }
                ]
            },
        )
    )
    client = AnySearch(
        provider="brightdata",
        api_key="bd-test",
        env={"BRIGHTDATA_ZONE": "serp_zone"},
    )
    response = client.search(
        "pizza",
        country="US",
        language="en",
        include_domains=["example.com"],
        safe_search="strict",
    )
    payload = json.loads(route.calls.last.request.content)
    assert payload["zone"] == "serp_zone"
    assert payload["data_format"] == "parsed"
    assert "q=pizza+site%3Aexample.com" in payload["url"]
    assert "gl=us" in payload["url"]
    assert "hl=en" in payload["url"]
    assert "safe=active" in payload["url"]
    assert response.results[0].url == "https://example.com/b"
    assert response.results[0].score == 1


def test_brightdata_requires_zone_for_configuration():
    assert not get_provider_class("brightdata").is_configured(
        {"BRIGHTDATA_API_KEY": "x"}
    )
    assert get_provider_class("brightdata").is_configured(
        {"BRIGHTDATA_API_KEY": "x", "BRIGHTDATA_ZONE": "zone"}
    )


@respx.mock
def test_dataforseo_uses_basic_auth_and_reads_live_organic_items():
    route = respx.post(
        "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "tasks": [
                    {
                        "result": [
                            {
                                "se_results_count": 1000,
                                "items": [
                                    {
                                        "type": "organic",
                                        "rank_absolute": 1,
                                        "title": "SEO result",
                                        "url": "https://example.com/seo",
                                        "description": "Description",
                                        "timestamp": "2026-10-20 10:00:00 +00:00",
                                    },
                                    {"type": "people_also_ask", "title": "Skip me"},
                                ],
                            }
                        ]
                    }
                ]
            },
        )
    )
    client = AnySearch(
        provider="dataforseo",
        env={
            "DATAFORSEO_LOGIN": "login",
            "DATAFORSEO_PASSWORD": "password",
        },
    )
    response = client.search("seo", max_results=5, language="en")
    request = route.calls.last.request
    token = request.headers["authorization"].removeprefix("Basic ")
    assert base64.b64decode(token).decode() == "login:password"
    payload = json.loads(request.content)
    assert payload[0]["keyword"] == "seo"
    assert payload[0]["depth"] == 5
    assert payload[0]["language_code"] == "en"
    assert payload[0]["location_code"] == 2840
    assert len(response.results) == 1
    assert response.results[0].score == 1


def test_dataforseo_requires_login_and_password():
    assert not get_provider_class("dataforseo").is_configured(
        {"DATAFORSEO_LOGIN": "login"}
    )
    assert get_provider_class("dataforseo").is_configured(
        {"DATAFORSEO_LOGIN": "login", "DATAFORSEO_PASSWORD": "password"}
    )


@respx.mock
def test_openai_web_search_returns_answer_and_citations():
    route = respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "resp_1",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "A cited answer about AI news.",
                                "annotations": [
                                    {
                                        "type": "url_citation",
                                        "url": "https://example.com/openai",
                                        "title": "OpenAI source",
                                        "start_index": 0,
                                        "end_index": 10,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        )
    )
    client = AnySearch(provider="openai", api_key="oa-test", env={})
    response = client.search(
        "ai news",
        mode="deep",
        include_domains=["example.com"],
        exclude_domains=["spam.example"],
    )
    payload = json.loads(route.calls.last.request.content)
    assert payload["tools"][0]["type"] == "web_search"
    assert payload["tools"][0]["filters"] == {"allowed_domains": ["example.com"]}
    assert payload["tools"][0]["search_context_size"] == "high"
    assert payload["reasoning"] == {"effort": "high"}
    assert payload["input"] == "ai news -site:spam.example"
    assert response.answer == "A cited answer about AI news."
    assert response.results[0].title == "OpenAI source"
    assert response.request_id == "resp_1"


@respx.mock
def test_anthropic_web_search_returns_answer_and_result_blocks():
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_1",
                "content": [
                    {
                        "type": "web_search_tool_result",
                        "content": [
                            {
                                "type": "web_search_result",
                                "url": "https://example.com/claude",
                                "title": "Claude source",
                                "page_age": "2026-10-20",
                            }
                        ],
                    },
                    {"type": "text", "text": "A cited Claude answer."},
                ],
            },
        )
    )
    client = AnySearch(provider="anthropic", api_key="an-test", env={})
    response = client.search(
        "ai news",
        include_domains=["example.com"],
        exclude_domains=["spam.example"],
    )
    payload = json.loads(route.calls.last.request.content)
    assert route.calls.last.request.headers["anthropic-version"] == "2023-06-01"
    assert payload["tools"][0]["type"] == "web_search_20250305"
    assert payload["tools"][0]["allowed_domains"] == ["example.com"]
    assert payload["tools"][0]["blocked_domains"] == ["spam.example"]
    assert response.answer == "A cited Claude answer."
    assert response.results[0].url == "https://example.com/claude"
    assert response.request_id == "msg_1"


@respx.mock
def test_xai_web_search_returns_answer_and_citations():
    route = respx.post("https://api.x.ai/v1/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "xai_1",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "A cited Grok answer.",
                                "annotations": [
                                    {
                                        "type": "url_citation",
                                        "url": "https://example.com/grok",
                                        "title": "Grok source",
                                        "start_index": 0,
                                        "end_index": 8,
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "citations": ["https://example.com/second"],
            },
        )
    )
    client = AnySearch(provider="xai", api_key="xai-test", env={})
    response = client.search(
        "ai news",
        include_domains=["example.com"],
        exclude_domains=["spam.example"],
    )
    payload = json.loads(route.calls.last.request.content)
    assert payload["tools"][0]["filters"] == {
        "allowed_domains": ["example.com"],
        "excluded_domains": ["spam.example"],
    }
    assert response.answer == "A cited Grok answer."
    assert [r.url for r in response.results] == [
        "https://example.com/grok",
        "https://example.com/second",
    ]
