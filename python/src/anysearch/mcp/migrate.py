"""Scan a codebase for direct search-API usage and map it onto anysearch.

This powers the ``migrate_codebase`` MCP tool. It is detection-only: it greps the
tree for known provider SDK imports, client constructors, and REST endpoints, then
returns precise call sites with a suggested unified ``anysearch`` replacement. The
calling agent (or a human) performs the actual edits using these findings.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Pattern, Tuple

# provider -> list of (compiled regex, kind) signatures.
_SIGNATURE_SOURCES: Dict[str, List[Tuple[str, str]]] = {
    "exa": [(r"\bfrom\s+exa_py\b|\bimport\s+exa_py\b", "sdk"), (r"\bExa\s*\(", "client"),
            (r"https?://api\.exa\.ai", "rest")],
    "tavily": [(r"\bfrom\s+tavily\b|\bimport\s+tavily\b|require\(['\"]@tavily", "sdk"),
               (r"\bTavilyClient\s*\(|\btavily\.search\b", "client"),
               (r"https?://api\.tavily\.com", "rest")],
    "parallel": [(r"\bfrom\s+parallel\s+import|require\(['\"]parallel-web", "sdk"),
                 (r"\bParallel\s*\(", "client"), (r"https?://api\.parallel\.ai", "rest")],
    "perplexity": [(r"\bfrom\s+perplexity\s+import|require\(['\"]@perplexity", "sdk"),
                   (r"https?://api\.perplexity\.ai/search", "rest")],
    "brave": [(r"https?://api\.search\.brave\.com", "rest"),
              (r"X-Subscription-Token", "header")],
    "serpapi": [(r"\bfrom\s+serpapi\b|require\(['\"]serpapi", "sdk"),
                (r"\bGoogleSearch\s*\(", "client"), (r"https?://serpapi\.com/search", "rest"),
                (r"google-search-results", "dep")],
    "serper": [(r"https?://google\.serper\.dev", "rest")],
    "you": [(r"https?://(api\.)?ydc-index\.io", "rest"), (r"\bYDC_API_KEY\b", "env")],
    "jina": [(r"https?://s\.jina\.ai", "rest")],
    "kagi": [(r"https?://kagi\.com/api", "rest"), (r"Authorization:\s*Bot\b", "header")],
    "linkup": [(r"\bfrom\s+linkup\b|require\(['\"]linkup", "sdk"),
               (r"\bLinkupClient\s*\(", "client"), (r"https?://api\.linkup\.so", "rest")],
    "firecrawl": [(r"\bfrom\s+firecrawl\b|require\(['\"]@mendable/firecrawl", "sdk"),
                  (r"\bFirecrawl(App)?\s*\(", "client"), (r"https?://api\.firecrawl\.dev", "rest")],
    "searchapi": [(r"https?://(www\.)?searchapi\.io", "rest")],
    "google_pse": [(r"https?://www\.googleapis\.com/customsearch|customsearch/v1", "rest")],
    "searxng": [(r"\bSEARXNG_BASE_URL\b|\bsearxng\b", "config")],
    "duckduckgo": [(r"\bfrom\s+ddgs\b|\bfrom\s+duckduckgo_search\b|require\(['\"]duck", "sdk"),
                   (r"\bDDGS\s*\(", "client"), (r"https?://(html\.|lite\.)?duckduckgo\.com", "rest")],
}

_COMPILED: Dict[str, List[Tuple[Pattern, str]]] = {
    provider: [(re.compile(pat, re.IGNORECASE), kind) for pat, kind in sigs]
    for provider, sigs in _SIGNATURE_SOURCES.items()
}

_CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".rb", ".go", ".java"}
_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "dist", "build", "__pycache__",
    ".next", ".turbo", ".cache", "vendor", "target", ".mypy_cache", ".ruff_cache",
}


def _suggestion(provider: str, language: str) -> str:
    if language == "python":
        return (
            f"anysearch.search(query, provider='{provider}', max_results=10)  "
            f"# unified replacement"
        )
    return (
        f"await search(query, {{ provider: '{provider}', maxResults: 10 }})  "
        f"// unified replacement"
    )


def _language_for(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".py":
        return "python"
    if ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        return "javascript"
    return "other"


def scan_codebase(
    root: str = ".",
    providers: Optional[List[str]] = None,
    max_files: int = 2000,
    max_findings: int = 1000,
) -> Dict:
    """Walk ``root`` and return structured findings of search-API usage."""
    root = os.path.abspath(os.path.expanduser(root))
    selected = set(providers) if providers else set(_COMPILED)
    findings: List[Dict] = []
    per_provider: Dict[str, int] = {}
    files_scanned = 0
    files_with_hits = 0

    if os.path.isfile(root):
        targets = [root]
        walk_root = os.path.dirname(root)
    else:
        targets = None
        walk_root = root

    def iter_files():
        if targets is not None:
            yield from targets
            return
        for dirpath, dirnames, filenames in os.walk(walk_root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for fn in filenames:
                if os.path.splitext(fn)[1].lower() in _CODE_EXTENSIONS:
                    yield os.path.join(dirpath, fn)

    for filepath in iter_files():
        if files_scanned >= max_files or len(findings) >= max_findings:
            break
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
        except (OSError, UnicodeError):
            continue
        files_scanned += 1
        language = _language_for(filepath)
        file_hit = False
        for lineno, line in enumerate(lines, start=1):
            for provider, sigs in _COMPILED.items():
                if provider not in selected:
                    continue
                for pattern, kind in sigs:
                    if pattern.search(line):
                        rel = os.path.relpath(filepath, walk_root) if targets is None else filepath
                        findings.append(
                            {
                                "file": rel,
                                "line": lineno,
                                "provider": provider,
                                "kind": kind,
                                "code": line.strip()[:200],
                                "suggestion": _suggestion(provider, language),
                            }
                        )
                        per_provider[provider] = per_provider.get(provider, 0) + 1
                        file_hit = True
                        break  # one finding per (line, provider)
            if len(findings) >= max_findings:
                break
        if file_hit:
            files_with_hits += 1

    return {
        "root": root,
        "files_scanned": files_scanned,
        "files_with_matches": files_with_hits,
        "total_findings": len(findings),
        "providers_detected": sorted(per_provider),
        "counts_by_provider": per_provider,
        "findings": findings,
        "next_steps": [
            "Install anysearch: pip install \"git+https://github.com/AI-Northstar-Tech/anysearch.git@main#subdirectory=python\"",
            "Replace each call site with anysearch.search(...) using the unified params.",
            "Keep the existing API key env vars — anysearch reads them automatically.",
            "Use provider='<name>' to pin a provider, or omit it to auto-select.",
        ],
    }
