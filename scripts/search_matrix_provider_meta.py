"""Official docs-backed metadata for the search capability matrix.

All `source_url` values must point at provider documentation (never the anysearch repo).
"""

from __future__ import annotations

# Primary docs + website per slug (overrides generator defaults where set).
LINKS: dict[str, dict[str, str]] = {
    "exa": {"docs": "https://exa.ai/docs/reference/search", "website": "https://exa.ai"},
    "parallel": {
        "docs": "https://docs.parallel.ai/search/modes",
        "website": "https://parallel.ai",
    },
    "tavily": {
        "docs": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
        "website": "https://tavily.com",
    },
    "brave": {
        "docs": "https://api-dashboard.search.brave.com/app/documentation/web-search/get-started",
        "website": "https://brave.com/search/api/",
    },
    "linkup": {
        "docs": "https://docs.linkup.so/pages/documentation/endpoints/search/overview",
        "website": "https://www.linkup.so",
    },
    "perplexity": {
        "docs": "https://docs.perplexity.ai/api-reference/search-post",
        "website": "https://www.perplexity.ai",
    },
    "serper": {"docs": "https://serper.dev/docs", "website": "https://serper.dev"},
    "serpapi": {"docs": "https://serpapi.com/search-api", "website": "https://serpapi.com"},
    "searchapi": {
        "docs": "https://www.searchapi.io/docs/google",
        "website": "https://www.searchapi.io",
    },
    "you": {
        "docs": "https://you.com/docs/search/overview",
        "website": "https://you.com",
    },
    "jina": {"docs": "https://jina.ai/reader/", "website": "https://jina.ai"},
    "kagi": {
        "docs": "https://help.kagi.com/kagi/api/search.html",
        "website": "https://kagi.com",
    },
    "firecrawl": {
        "docs": "https://docs.firecrawl.dev/api-reference/endpoint/search",
        "website": "https://www.firecrawl.dev",
    },
    "google_pse": {
        "docs": "https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list",
        "website": "https://programmablesearchengine.google.com",
    },
    "searxng": {
        "docs": "https://docs.searxng.org/dev/search_api.html",
        "website": "https://docs.searxng.org",
    },
    "duckduckgo": {
        "docs": "https://pypi.org/project/ddgs/",
        "website": "https://duckduckgo.com",
    },
}

# PyPI or provider install docs for optional native SDK extras (never anysearch repo).
EXTRA_SOURCES: dict[str, str] = {
    "exa": "https://pypi.org/project/exa-py/",
    "parallel": "https://pypi.org/project/parallel-web/",
    "tavily": "https://pypi.org/project/tavily-python/",
    "linkup": "https://docs.linkup.so/pages/sdk/python/python",
    "perplexity": "https://pypi.org/project/perplexityai/",
    "serpapi": "https://pypi.org/project/google-search-results/",
    "firecrawl": "https://pypi.org/project/firecrawl-py/",
    "duckduckgo": "https://pypi.org/project/ddgs/",
}

# Env var documentation (authentication / configuration).
ENV_SOURCES: dict[str, str] = {
    "exa": "https://exa.ai/docs/reference/quickstart",
    "parallel": "https://docs.parallel.ai/getting-started/overview",
    "tavily": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
    "brave": "https://api-dashboard.search.brave.com/app/documentation/web-search/get-started",
    "linkup": "https://docs.linkup.so/pages/documentation/endpoints/search/reference",
    "perplexity": "https://docs.perplexity.ai/docs/search/quickstart",
    "serper": "https://serper.dev/docs",
    "serpapi": "https://serpapi.com/search-api",
    "searchapi": "https://www.searchapi.io/docs/google",
    "you": "https://you.com/docs/api-reference/search/v1-search",
    "jina": "https://jina.ai/reader/",
    "kagi": "https://help.kagi.com/kagi/api/search.html",
    "firecrawl": "https://docs.firecrawl.dev/api-reference/endpoint/search",
    "google_pse": "https://developers.google.com/custom-search/v1/using_rest",
    "searxng": "https://docs.searxng.org/admin/settings/settings_search/",
    "duckduckgo": "https://pypi.org/project/ddgs/",
}

MODE_META: dict[str, dict] = {
    "exa": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://exa.ai/docs/reference/search-best-practices",
        "comment": (
            "Native `type` on /search: `fast` (~500ms), `auto` default (balanced), "
            "`deep` / `deep-lite` / `deep-reasoning` for multi-step research. "
            "anysearch maps fast→fast, balanced→auto, deep→deep."
        ),
    },
    "tavily": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://docs.tavily.com/documentation/best-practices/best-practices-search",
        "comment": (
            "Native `search_depth`: `ultra-fast`, `fast`, `basic` (balanced default), "
            "`advanced` (highest relevance, 2 credits). "
            "anysearch: fast→fast, balanced→basic, deep→advanced."
        ),
    },
    "parallel": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://docs.parallel.ai/search/modes",
        "comment": (
            "Native `mode`: `basic` (lower latency, 2–3 queries) vs `advanced` "
            "(default, higher-quality retrieval). "
            "anysearch: fast/balanced→basic, deep→advanced."
        ),
    },
    "linkup": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://docs.linkup.so/pages/documentation/endpoints/search/overview",
        "comment": (
            "Native `depth`: `fast` (<1s, keyword-only), `standard` (1–3s agentic), "
            "`deep` (5–30s multi-iteration). "
            "anysearch: fast→fast, balanced→standard, deep→deep."
        ),
    },
    "brave": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://api-dashboard.search.brave.com/app/documentation/web-search",
        "comment": (
            "No named depth tier; latency/richness via query params. "
            "`fast`/`balanced`: default web/news search (one description per result). "
            "`deep`: `extra_snippets=true` (up to 5 alternate excerpts per result; Pro plans)."
        ),
    },
    "jina": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://jina.ai/reader/",
        "comment": (
            "Reader Search (`s.jina.ai`): `fast` = header `X-Respond-With: no-content` "
            "(SERP metadata only). `balanced`/`deep` = fetch and return page markdown "
            "(default Reader pipeline; `deep` when full `include_content` is requested)."
        ),
    },
    "perplexity": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://docs.perplexity.ai/api-reference/search-post",
        "comment": (
            "Search API `snippet_mode`: `low`, `medium` (default), `high` (more extracted text). "
            "Tune with `max_tokens` / `max_tokens_per_page` for total content budget. "
            "anysearch sets `snippet_mode=high` when `include_content` is true (deep)."
        ),
    },
    "firecrawl": {
        "values": ["balanced", "deep"],
        "source": "https://docs.firecrawl.dev/features/search",
        "comment": (
            "No separate speed preset on /v2/search. "
            "`balanced`: results are title, URL, description only. "
            "`deep`: pass `scrapeOptions` (e.g. markdown) to scrape each hit inline."
        ),
    },
    "you": {
        "values": ["fast", "balanced", "deep"],
        "source": "https://you.com/docs/search/overview",
        "comment": (
            "No `mode` field; depth is implicit. "
            "`fast`/`balanced`: web/news snippets from /v1/search (no livecrawl). "
            "`deep`: `livecrawl` (`web`, `news`, or `all`) plus `livecrawl_formats` "
            "(`markdown` / `html`) to pull page bodies."
        ),
    },
    "kagi": {
        "values": ["balanced", "deep"],
        "source": "https://help.kagi.com/kagi/api/search.html",
        "comment": (
            "Search API has no request `mode`; snippet length is inherited from your "
            "Kagi account (Settings → Search → longer vs shorter snippets). "
            "Treat `deep` as longer snippets configured on the account."
        ),
    },
    "serper": {
        "values": ["balanced"],
        "source": "https://serper.dev/docs",
        "comment": (
            "Google SERP proxy: one ranked result style per call (no fast/deep API knob). "
            "Matrix `balanced` = standard /search or /news endpoint."
        ),
    },
    "serpapi": {
        "values": ["balanced"],
        "source": "https://serpapi.com/search-api",
        "comment": (
            "Aggregated Google engine API: no latency/depth parameter on the search call. "
            "Matrix `balanced` = default engine JSON response."
        ),
    },
    "searchapi": {
        "values": ["balanced"],
        "source": "https://www.searchapi.io/docs/google",
        "comment": (
            "Google engine wrapper: single SERP depth per request (no native fast/deep tier)."
        ),
    },
    "google_pse": {
        "values": ["balanced"],
        "source": "https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list",
        "comment": (
            "Custom Search JSON API: no search-depth or speed preset—only `num`, `sort`, "
            "and `siteSearch` filters. Matrix `balanced` = default `cse.list` behavior."
        ),
    },
    "searxng": {
        "values": ["balanced"],
        "source": "https://docs.searxng.org/dev/search_api.html",
        "comment": (
            "Meta-search JSON API: result richness depends on configured engines, not a "
            "global depth flag. Matrix `balanced` = default instance search."
        ),
    },
    "duckduckgo": {
        "values": ["balanced"],
        "source": "https://pypi.org/project/ddgs/",
        "comment": (
            "Keyless DDGS client: instant web results without a depth parameter. "
            "Matrix `balanced` = default `text()` search."
        ),
    },
}

# Per-feature support overrides (when code supports more/less than capabilities frozenset).
SUPPORT_OVERRIDE: dict[str, dict[str, str]] = {
    "google_pse": {
        "domains": "partial",
        "date": "partial",
    },
}

# Per-feature comments and doc anchors (slug → feature key → {source, comment}).
# Omitted keys fall back to generic labels from the generator.
FEATURE_META: dict[str, dict[str, dict[str, str]]] = {
    "exa": {
        "domains": {
            "source": "https://exa.ai/docs/reference/search",
            "comment": "`includeDomains` / `excludeDomains` on POST /search.",
        },
        "country": {
            "source": "https://exa.ai/docs/reference/search",
            "comment": "`userLocation` (ISO country code) biases results.",
        },
        "date": {
            "source": "https://exa.ai/docs/reference/search",
            "comment": "`startPublishedDate` / `endPublishedDate` (ISO dates).",
        },
        "safe_search": {
            "source": "https://exa.ai/docs/reference/search",
            "comment": "`moderation: true` enables content filtering.",
        },
        "content": {
            "source": "https://exa.ai/docs/reference/search",
            "comment": "`contents.text` (or highlights) in the request body.",
        },
        "summary": {
            "source": "https://exa.ai/docs/reference/search",
            "comment": "`contents.summary` returns an AI summary per result.",
        },
        "highlights": {
            "source": "https://exa.ai/docs/reference/search-best-practices",
            "comment": "`contents.highlights` — query-relevant excerpts (~10× fewer tokens than full text).",
        },
        "news": {
            "source": "https://exa.ai/docs/reference/search",
            "comment": "`category: news` or `type` tuned for news-style retrieval.",
        },
    },
    "tavily": {
        "domains": {
            "source": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
            "comment": "`include_domains` / `exclude_domains` (max 300 domains).",
        },
        "country": {
            "source": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
            "comment": "`country` (topic `general` only) — ISO country name.",
        },
        "date": {
            "source": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
            "comment": "`start_date` / `end_date` or `time_range` (`day`, `week`, `month`, `year`).",
        },
        "answer": {
            "source": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
            "comment": "`include_answer`: `basic` or `advanced` LLM answer from results.",
        },
        "content": {
            "source": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
            "comment": "`include_raw_content` returns raw page text per source.",
        },
        "news": {
            "source": "https://docs.tavily.com/documentation/api-reference/endpoint/search",
            "comment": "`topic`: `news` (or `general` with news-oriented query).",
        },
    },
    "parallel": {
        "domains": {
            "source": "https://docs.parallel.ai/search/advanced-search-settings",
            "comment": "`advanced_settings.source_policy.include_domains` / `exclude_domains` (use sparingly).",
        },
        "country": {
            "source": "https://docs.parallel.ai/search/advanced-search-settings",
            "comment": "`advanced_settings.location` — ISO 3166-1 alpha-2 (subset of countries).",
        },
        "date": {
            "source": "https://docs.parallel.ai/search/advanced-search-settings",
            "comment": "`source_policy.after_date` for freshness in advanced_settings.",
        },
        "content": {
            "source": "https://docs.parallel.ai/api-reference/search/search",
            "comment": "Excerpts are pre-compressed in search results (excerpt_settings optional).",
        },
        "highlights": {
            "source": "https://docs.parallel.ai/search/best-practices",
            "comment": "Ranked excerpts per URL are the default Search API payload.",
        },
    },
    "linkup": {
        "domains": {
            "source": "https://docs.linkup.so/pages/documentation/endpoints/search/reference",
            "comment": "`includeDomains` / `excludeDomains` arrays on POST /v1/search.",
        },
        "date": {
            "source": "https://docs.linkup.so/pages/documentation/endpoints/search/reference",
            "comment": "`fromDate` / `toDate` (YYYY-MM-DD) filter sources by publication date.",
        },
        "answer": {
            "source": "https://docs.linkup.so/pages/documentation/endpoints/search/overview",
            "comment": "`outputType`: `sourcedAnswer` returns a cited natural-language answer.",
        },
        "content": {
            "source": "https://docs.linkup.so/pages/documentation/endpoints/search/overview",
            "comment": "`outputType`: `searchResults` with page content in standard/deep depths.",
        },
    },
    "brave": {
        "country": {
            "source": "https://api-dashboard.search.brave.com/app/documentation/web-search/get-started",
            "comment": "`country` — filter by country (web and news).",
        },
        "language": {
            "source": "https://api-dashboard.search.brave.com/app/documentation/web-search/get-started",
            "comment": "`search_lang` and `ui_lang` for result and UI language.",
        },
        "date": {
            "source": "https://api-dashboard.search.brave.com/app/documentation/web-search/get-started",
            "comment": "`freshness` presets (`pd`, `pw`, `pm`, `py`) or custom `YYYY-MM-DDtoYYYY-MM-DD`.",
        },
        "safe_search": {
            "source": "https://api-dashboard.search.brave.com/app/documentation/web-search/get-started",
            "comment": "`safesearch`: `off`, `moderate`, `strict`.",
        },
        "highlights": {
            "source": "https://api-dashboard.search.brave.com/app/documentation/web-search",
            "comment": "`extra_snippets=true` — up to 5 alternate excerpts per web result (Pro).",
        },
        "news": {
            "source": "https://api-dashboard.search.brave.com/app/documentation/web-search/get-started",
            "comment": "Dedicated `/res/v1/news/search` endpoint.",
        },
    },
    "perplexity": {
        "domains": {
            "source": "https://docs.perplexity.ai/docs/search/quickstart",
            "comment": "`search_domain_filter` — allowlist entries or `-domain` denylist prefixes.",
        },
        "language": {
            "source": "https://docs.perplexity.ai/api-reference/search-post",
            "comment": "`search_language_filter` — array of ISO 639-1 language codes.",
        },
        "content": {
            "source": "https://docs.perplexity.ai/api-reference/search-post",
            "comment": "`snippet` field size via `snippet_mode`, `max_tokens`, `max_tokens_per_page`.",
        },
    },
    "you": {
        "domains": {
            "source": "https://you.com/docs/search/overview",
            "comment": "`include_domains`, `exclude_domains`, `boost_domains` (POST JSON arrays, up to 500).",
        },
        "country": {
            "source": "https://you.com/docs/search/overview",
            "comment": "`country` — ISO 3166-1 alpha-2 (e.g. US, GB).",
        },
        "highlights": {
            "source": "https://you.com/docs/api-reference/search/v1-search",
            "comment": "Multiple `snippets` strings per web result in the JSON response.",
        },
    },
    "jina": {
        "content": {
            "source": "https://jina.ai/reader/",
            "comment": "Search returns markdown page bodies unless `X-Respond-With: no-content` is set.",
        },
    },
    "kagi": {
        "snippet": {
            "source": "https://help.kagi.com/kagi/api/search.html",
            "comment": "Each result includes a `snippet`; length follows account Search settings.",
        },
    },
    "firecrawl": {
        "country": {
            "source": "https://docs.firecrawl.dev/api-reference/endpoint/search",
            "comment": "`country` — ISO country code on POST /v2/search.",
        },
        "content": {
            "source": "https://docs.firecrawl.dev/features/search",
            "comment": "`scrapeOptions.formats` (e.g. `markdown`) embeds full page text per hit.",
        },
        "news": {
            "source": "https://docs.firecrawl.dev/api-reference/endpoint/search",
            "comment": "`sources: [{\"type\": \"news\"}]` for news results.",
        },
    },
    "google_pse": {
        "domains": {
            "source": "https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list",
            "comment": "Single `siteSearch` + `siteSearchFilter` (`i` include / `e` exclude)—first domain only.",
        },
        "country": {
            "source": "https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list",
            "comment": "`gl` — geolocation of end user.",
        },
        "language": {
            "source": "https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list",
            "comment": "`hl` UI language and `lr` lang_restrict.",
        },
        "date": {
            "source": "https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list",
            "comment": "`sort=date:r:YYYYMMDD:YYYYMMDD` when both range ends are set.",
        },
        "safe_search": {
            "source": "https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list",
            "comment": "`safe`: `active` or `off`.",
        },
    },
    "searxng": {
        "language": {
            "source": "https://docs.searxng.org/dev/search_api.html",
            "comment": "`language` query parameter (instance default if omitted).",
        },
        "safe_search": {
            "source": "https://docs.searxng.org/dev/search_api.html",
            "comment": "`safesearch` 0=off, 1=moderate, 2=strict.",
        },
        "answer": {
            "source": "https://docs.searxng.org/dev/search_api.html",
            "comment": "Instant answers in the `answers` array when engines provide them.",
        },
    },
    "duckduckgo": {
        "country": {
            "source": "https://pypi.org/project/ddgs/",
            "comment": "DDGS `region` / locale parameters (see package docs).",
        },
        "safe_search": {
            "source": "https://pypi.org/project/ddgs/",
            "comment": "DDGS `safesearch` mapping for web search.",
        },
    },
    "serper": {
        "country": {
            "source": "https://serper.dev/docs",
            "comment": "`gl` — country code on POST /search and /news.",
        },
        "language": {
            "source": "https://serper.dev/docs",
            "comment": "`hl` — interface language.",
        },
        "answer": {
            "source": "https://serper.dev/docs",
            "comment": "Answer box / knowledge graph surfaced in JSON when Google returns them.",
        },
        "news": {
            "source": "https://serper.dev/docs",
            "comment": "POST /news for news SERP.",
        },
    },
    "serpapi": {
        "country": {
            "source": "https://serpapi.com/search-api",
            "comment": "`gl` — country code.",
        },
        "language": {
            "source": "https://serpapi.com/search-api",
            "comment": "`hl` — language code.",
        },
        "safe_search": {
            "source": "https://serpapi.com/search-api",
            "comment": "`safe` — active or off.",
        },
        "answer": {
            "source": "https://serpapi.com/search-api",
            "comment": "Answer box fields when present in the engine JSON.",
        },
        "news": {
            "source": "https://serpapi.com/search-api",
            "comment": "`engine=google_news` (or other news engines).",
        },
    },
    "searchapi": {
        "country": {
            "source": "https://www.searchapi.io/docs/google",
            "comment": "`gl` parameter on Google engine requests.",
        },
        "language": {
            "source": "https://www.searchapi.io/docs/google",
            "comment": "`hl` — language of the SERP.",
        },
        "answer": {
            "source": "https://www.searchapi.io/docs/google",
            "comment": "Featured snippets / answer box when returned by the engine.",
        },
        "news": {
            "source": "https://www.searchapi.io/docs/google-news",
            "comment": "Use the Google News engine for news results.",
        },
    },
}

PARTIAL_NOTES: dict[str, dict[str, str]] = {
    "serper": {
        "answer": "Answer only when the SERP includes an answer box (not explicitly requested).",
    },
    "serpapi": {
        "answer": "Answer only when the SERP includes an answer box (not explicitly requested).",
    },
    "searchapi": {
        "answer": "Answer only when the SERP includes an answer box (not explicitly requested).",
    },
    "google_pse": {
        "domains": "Single include or exclude domain via siteSearch (first list item).",
        "date": "Date range via sort=date:r:start:end (Custom Search JSON API).",
    },
    "searxng": {
        "answer": "Returns instant-answer text from the answers field when available.",
    },
}


def links_for(slug: str) -> dict[str, str]:
    return LINKS.get(slug, {})


def mode_for(slug: str, docs: str, website: str) -> dict:
    meta = MODE_META.get(slug)
    if meta:
        return {
            "values": meta["values"],
            "source_url": meta["source"],
            "comment": meta["comment"],
        }
    fallback = docs or website
    return {
        "values": ["balanced"],
        "source_url": fallback,
        "comment": "Standard search tier (no separate fast/deep API parameter documented).",
    }


def feature_entry(
    slug: str,
    key: str,
    support: str,
    docs: str,
    website: str,
    default_comment: str,
) -> dict:
    custom = FEATURE_META.get(slug, {}).get(key)
    if custom:
        return feat(support, custom["source"], custom["comment"])
    partial = PARTIAL_NOTES.get(slug, {}).get(key)
    comment = partial or default_comment
    return feat(support, docs or website, comment)


def feat(support: str, source_url: str, comment: str) -> dict:
    return {"support": support, "source_url": source_url, "comment": comment}


def string_val(value: str, source_url: str, comment: str) -> dict:
    return {"value": value, "source_url": source_url, "comment": comment}


def list_val(values: list[str], source_url: str, comment: str) -> dict:
    return {"values": values, "source_url": source_url, "comment": comment}
