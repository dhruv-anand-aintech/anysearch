"""Tests for the FastAPI proxy server."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi.testclient import TestClient

from anysearch.proxy.server import ProxyConfig, create_app
from anysearch.types import SearchResponse, SearchResult


class FakeAnySearch:
    priority = None
    _env: Dict[str, str] = {"EXA_API_KEY": "x"}

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def provider_info(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "exa",
                "aliases": [],
                "configured": True,
                "requires_key": True,
                "env_keys": ["EXA_API_KEY"],
                "capabilities": ["content", "domains"],
                "extra_package": "exa-py",
                "config_hint": "Set EXA_API_KEY.",
            },
            {
                "name": "duckduckgo",
                "aliases": ["ddg"],
                "configured": True,
                "requires_key": False,
                "env_keys": [],
                "capabilities": [],
                "extra_package": "ddgs",
                "config_hint": "No key required.",
            },
        ]

    async def asearch(self, query: str, **params: Any) -> SearchResponse:
        self.calls.append({"query": query, "params": params})
        return SearchResponse(
            provider=params.get("provider") or "exa",
            query=query,
            answer="answer",
            results=[
                SearchResult(
                    title="T",
                    url="https://example.com",
                    snippet="snippet",
                    score=0.9,
                )
            ],
        )


def make_client(fake: FakeAnySearch, **config: Any) -> TestClient:
    app = create_app(client=fake, config=ProxyConfig(api_keys=["user-key"], admin_keys=["admin-key"], **config))
    return TestClient(app)


def test_health_and_models_are_openai_shaped():
    fake = FakeAnySearch()
    client = make_client(fake)

    assert client.get("/health").json()["configured_providers"] == ["exa", "duckduckgo"]
    resp = client.get("/v1/models", headers={"Authorization": "Bearer user-key"})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["object"] == "list"
    assert payload["data"][0]["id"] == "exa"


def test_search_forwards_unified_params():
    fake = FakeAnySearch()
    client = make_client(fake)

    resp = client.post(
        "/search",
        headers={"Authorization": "Bearer user-key"},
        json={
            "query": "vector dbs",
            "provider": "exa",
            "fallbacks": ["tavily"],
            "include_content": True,
            "max_results": 3,
        },
    )

    assert resp.status_code == 200
    assert resp.json()["results"][0]["url"] == "https://example.com"
    assert fake.calls == [
        {
            "query": "vector dbs",
            "params": {
                "provider": "exa",
                "fallbacks": ["tavily"],
                "max_results": 3,
                "include_domains": [],
                "exclude_domains": [],
                "include_content": True,
                "extra": {},
                "provider_params": {},
            },
        }
    ]


def test_v1_search_uses_model_as_provider():
    fake = FakeAnySearch()
    client = make_client(fake)

    resp = client.post(
        "/v1/search",
        headers={"Authorization": "Bearer user-key"},
        json={"query": "q", "model": "duckduckgo"},
    )

    assert resp.status_code == 200
    assert resp.json()["object"] == "search.response"
    assert fake.calls[0]["params"]["provider"] == "duckduckgo"


def test_auth_and_request_limit():
    fake = FakeAnySearch()
    client = make_client(fake, request_limit=1)

    assert client.post("/search", json={"query": "q"}).status_code == 401
    assert client.post("/search", headers={"Authorization": "Bearer user-key"}, json={"query": "q"}).status_code == 200
    assert client.post("/search", headers={"Authorization": "Bearer user-key"}, json={"query": "q"}).status_code == 429


def test_admin_usage_requires_admin_key():
    fake = FakeAnySearch()
    client = make_client(fake)

    assert client.get("/admin/usage", headers={"Authorization": "Bearer user-key"}).status_code == 403
    assert client.get("/admin/usage", headers={"Authorization": "Bearer admin-key"}).status_code == 200
