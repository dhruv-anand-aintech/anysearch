#!/usr/bin/env python3
"""Generate search_matrix/data/*.json from the anysearch Python provider registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_SRC = ROOT / "python" / "src"
sys.path.insert(0, str(PYTHON_SRC))

from anysearch.client import AnySearch  # noqa: E402

DATA_DIR = ROOT / "docs" / "tools" / "search_matrix" / "data"

# Official docs / marketing URLs per provider slug.
LINKS: dict[str, dict[str, str]] = {
    "exa": {
        "docs": "https://docs.exa.ai/reference/search",
        "website": "https://exa.ai",
    },
    "parallel": {
        "docs": "https://docs.parallel.ai/search/search-quickstart",
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
        "docs": "https://docs.linkup.so/pages/sdk/python/python",
        "website": "https://www.linkup.so",
    },
    "perplexity": {
        "docs": "https://docs.perplexity.ai/guides/search-quickstart",
        "website": "https://www.perplexity.ai",
    },
    "serper": {"docs": "https://serper.dev/docs", "website": "https://serper.dev"},
    "serpapi": {"docs": "https://serpapi.com/search-api", "website": "https://serpapi.com"},
    "searchapi": {
        "docs": "https://www.searchapi.io/docs/google",
        "website": "https://www.searchapi.io",
    },
    "you": {"docs": "https://documentation.you.com", "website": "https://you.com"},
    "jina": {"docs": "https://jina.ai/reader", "website": "https://jina.ai"},
    "kagi": {
        "docs": "https://help.kagi.com/kagi/api/search.html",
        "website": "https://kagi.com",
    },
    "firecrawl": {
        "docs": "https://docs.firecrawl.dev/features/search",
        "website": "https://www.firecrawl.dev",
    },
    "google_pse": {
        "docs": "https://developers.google.com/custom-search/v1/overview",
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

DISPLAY_NAMES = {
    "google_pse": "Google PSE",
    "duckduckgo": "DuckDuckGo",
    "searxng": "SearXNG",
    "serpapi": "SerpApi",
}

# Opportunistic / partial support notes.
PARTIAL: dict[str, dict[str, str]] = {
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
    },
    "searxng": {
        "answer": "Returns instant-answer text from the answers field when available.",
    },
}

MODE_MAP = {
    "exa": "fast → fast, balanced → auto, deep → deep",
    "tavily": "fast → fast, balanced → basic, deep → advanced",
    "parallel": "fast/balanced → basic, deep → advanced",
    "linkup": "fast → fast, balanced → standard, deep → deep",
}

FEATURE_KEYS = [
    "domains",
    "country",
    "language",
    "date",
    "safe_search",
    "mode",
    "answer",
    "content",
    "summary",
    "highlights",
    "news",
]

FEATURE_LABELS = {
    "domains": "Domain filters",
    "country": "Country (gl)",
    "language": "Language",
    "date": "Published date range",
    "safe_search": "Safe search",
    "mode": "Depth (fast/balanced/deep)",
    "answer": "Synthesized answer",
    "content": "Full page text",
    "summary": "AI per-result summary",
    "highlights": "Query highlights",
    "news": "News search type",
}


def feat(support: str, source_url: str, comment: str) -> dict:
    return {"support": support, "source_url": source_url, "comment": comment}


def string_val(value: str, source_url: str, comment: str) -> dict:
    return {"value": value, "source_url": source_url, "comment": comment}


def build_provider(row: dict) -> dict:
    name = row["name"]
    slug = name
    caps = set(row["capabilities"])
    links_meta = LINKS.get(slug, {})
    docs = links_meta.get("docs", row.get("config_hint", ""))
    website = links_meta.get("website", "")
    display = DISPLAY_NAMES.get(slug, name.replace("_", " ").title())

    partial_notes = PARTIAL.get(slug, {})

    def support_for(key: str) -> str:
        if key in caps:
            return "full"
        if key in partial_notes:
            return "partial"
        # Opportunistic answer on serper family
        if key == "answer" and slug in ("serper", "serpapi", "searchapi"):
            return "partial"
        if key == "domains" and slug == "google_pse":
            return "partial"
        if key == "answer" and slug == "searxng":
            return "partial"
        return "none"

    base_url = docs or website or f"https://github.com/AI-Northstar-Tech/anysearch"
    out: dict = {
        "name": display,
        "links": {
            "docs": docs,
            "github": "https://github.com/AI-Northstar-Tech/anysearch",
            "website": website,
            "slug": slug,
        },
        "env_keys": string_val(
            ", ".join(row["env_keys"]) if row["env_keys"] else "(none — keyless)",
            base_url,
            "Environment variables read by anysearch.",
        ),
        "python_extra": string_val(
            row["extra_package"] or "— (REST only)",
            "https://github.com/AI-Northstar-Tech/anysearch/tree/main/python#install",
            "Optional pip extra: pip install 'anysearch-sdk[<name>]'",
        ),
        "requires_key": feat(
            "none" if not row["requires_key"] else "full",
            base_url,
            "Keyless providers work without credentials.",
        ),
        "snippet": feat(
            "full",
            base_url,
            "Short description field; available on virtually all providers.",
        ),
    }

    for key in FEATURE_KEYS:
        sup = support_for(key)
        comment = FEATURE_LABELS.get(key, key)
        if key in partial_notes:
            comment = partial_notes[key]
        elif key == "mode" and slug in MODE_MAP:
            comment = f"Mapped: {MODE_MAP[slug]}"
        out[key] = feat(sup, docs or website or base_url, comment)

    if slug in MODE_MAP:
        out["mode_notes"] = string_val(MODE_MAP[slug], docs or base_url, "Unified mode knob mapping.")

    notes = []
    if not row["requires_key"]:
        notes.append("No API key required (keyless fallback).")
    if row.get("extra_package"):
        notes.append(f"Native SDK extra: {row['extra_package']}.")
    out["notes"] = " ".join(notes)

    return out


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for p in DATA_DIR.glob("*.json"):
        p.unlink()

    info = AnySearch().provider_info()
    for row in sorted(info, key=lambda r: r["name"]):
        payload = build_provider(row)
        path = DATA_DIR / f"{row['name']}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print("wrote", path.name)

    print(f"Generated {len(info)} provider files in {DATA_DIR}")


if __name__ == "__main__":
    main()
