"""SerpApi multi-engine helpers — https://serpapi.com/search-api."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Web search engines available via SerpApi's `engine` parameter (not exhaustive).
SERPAPI_WEB_ENGINES: frozenset[str] = frozenset(
    {
        "google",
        "bing",
        "baidu",
        "yandex",
        "duckduckgo",
        "yahoo",
        "ebay",
        "naver",
        "amazon",
        "apple_app_store",
        "walmart",
        "yelp",
        "youtube",
    }
)

# Web engine → dedicated SerpApi news engine name.
SERPAPI_NEWS_ENGINES: Dict[str, str] = {
    "google": "google_news",
    "bing": "bing_news",
    "baidu": "baidu_news",
    "duckduckgo": "duckduckgo_news",
    "yahoo": "yahoo",
}

ENGINE_ALIASES: Dict[str, str] = {
    "ddg": "duckduckgo",
    "goog": "google",
}


def normalize_engine(name: str) -> str:
    key = name.strip().lower().replace("-", "_")
    return ENGINE_ALIASES.get(key, key)


def resolve_serpapi_engine(
    *,
    engine: Optional[str],
    default_engine: str,
    search_type: str,
    extra: Dict[str, Any],
) -> str:
    """Pick the SerpApi `engine` query value for this request."""
    raw = engine if engine is not None else extra.pop("engine", None)
    base = normalize_engine(str(raw or default_engine))
    if search_type == "news":
        if base in SERPAPI_NEWS_ENGINES:
            return SERPAPI_NEWS_ENGINES[base]
        if base.endswith("_news"):
            return base
    return base


def apply_serpapi_locale(
    params: Dict[str, Any],
    engine: str,
    country: Optional[str],
    language: Optional[str],
) -> None:
    if not country and not language:
        return
    root = engine.removesuffix("_news")
    if root == "google":
        if country:
            params["gl"] = country.lower()
        if language:
            params["hl"] = language
    elif root == "bing":
        if country:
            params["cc"] = country.lower()
        if language:
            params["setlang"] = language.lower()
    elif root == "duckduckgo":
        cc = (country or "us").lower()
        lang = (language or "en").lower()
        params["kl"] = f"{cc}-{lang}"


def apply_serpapi_safe_search(
    params: Dict[str, Any],
    engine: str,
    safe_search: Optional[str],
) -> None:
    if not safe_search:
        return
    root = engine.removesuffix("_news")
    if root == "google":
        params["safe"] = "off" if safe_search == "off" else "active"
    elif root in ("bing", "duckduckgo", "yahoo"):
        params["safe_search"] = safe_search


def extract_serpapi_results(data: Dict[str, Any], search_type: str) -> List[Dict[str, Any]]:
    keys = (
        ("news_results", "organic_results")
        if search_type == "news"
        else ("organic_results", "organic", "results")
    )
    for key in keys:
        items = data.get(key)
        if isinstance(items, list) and items:
            return items
    return []


def extract_serpapi_answer(data: Dict[str, Any]) -> Optional[str]:
    box = data.get("answer_box")
    if isinstance(box, dict):
        answer = box.get("answer") or box.get("snippet") or box.get("result")
        if answer:
            return str(answer)
    featured = data.get("answer")
    if isinstance(featured, str):
        return featured
    if isinstance(featured, dict):
        return featured.get("answer") or featured.get("snippet")
    return None
