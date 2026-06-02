"""A dependency-free stdio MCP server that adapts to configured search providers.

Run it with ``anysearch-mcp`` (console script) or ``python -m anysearch.mcp.server``.

The server implements the Model Context Protocol over newline-delimited JSON-RPC on
stdin/stdout (logs go to stderr only). The set of usable providers — and the ``provider``
enum on the ``search`` tool — is derived from which API keys are present in the
environment. Pass ``--probe`` (or set ``ANYSEARCH_MCP_PROBE=1``) to additionally run a
tiny live query per provider at startup and expose only the ones that actually work.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional

from .. import __version__
from ..client import AnySearch
from ..exceptions import AnySearchError
from ..providers import get_provider_class
from ..router import available_providers, select_provider
from .migrate import scan_codebase

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "anysearch"

_client = AnySearch()


def log(*args: Any) -> None:
    print("[anysearch-mcp]", *args, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------
# Provider discovery
# --------------------------------------------------------------------------

def probe_provider(name: str, timeout: float = 8.0) -> bool:
    try:
        resp = _client.search("anysearch health check", provider=name, max_results=1,
                              on_unsupported="ignore", timeout=timeout)
        return resp is not None
    except Exception as exc:  # noqa: BLE001
        log(f"probe {name}: not working ({type(exc).__name__}: {exc})")
        return False


def discover_providers(probe: bool = False) -> List[str]:
    configured = available_providers()
    if not probe:
        return configured
    working = [name for name in configured if probe_provider(name)]
    return working or configured


# --------------------------------------------------------------------------
# Tool definitions
# --------------------------------------------------------------------------

def _search_schema(provider_enum: List[str]) -> Dict[str, Any]:
    provider_prop: Dict[str, Any] = {
        "type": "string",
        "description": "Search provider to use. Omit to auto-select from configured keys.",
    }
    if provider_enum:
        provider_prop["enum"] = provider_enum
    return {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "provider": provider_prop,
            "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 100},
            "search_type": {"type": "string", "enum": ["web", "news"], "default": "web"},
            "engine": {
                "type": "string",
                "description": (
                    "SerpApi search backend when provider is serpapi: google (default), "
                    "bing, baidu, yandex, duckduckgo, yahoo, and others documented at "
                    "https://serpapi.com/search-api"
                ),
            },
            "country": {"type": "string", "description": "ISO 3166-1 alpha-2, e.g. 'us'."},
            "language": {"type": "string", "description": "ISO 639-1, e.g. 'en'."},
            "include_domains": {"type": "array", "items": {"type": "string"}},
            "exclude_domains": {"type": "array", "items": {"type": "string"}},
            "start_published_date": {"type": "string", "description": "ISO 8601 / YYYY-MM-DD."},
            "end_published_date": {"type": "string", "description": "ISO 8601 / YYYY-MM-DD."},
            "safe_search": {"type": "string", "enum": ["off", "moderate", "strict"]},
            "mode": {"type": "string", "enum": ["fast", "balanced", "deep"],
                     "description": "Depth/quality knob, mapped per provider."},
            "answer": {"type": "boolean", "description": "Request a synthesized answer where supported."},
            "include_content": {"type": "boolean", "description": "Return full page text where supported."},
            "include_summary": {"type": "boolean", "description": "Return per-result AI summary where supported."},
            "highlights": {"type": "boolean", "description": "Return relevant excerpts where supported."},
            "fallbacks": {"type": "array", "items": {"type": "string"},
                          "description": "Providers to try if the primary fails."},
            "extra": {"type": "object", "description": "Raw provider-specific params (passthrough)."},
        },
        "required": ["query"],
    }


def build_tools(provider_enum: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            "name": "search",
            "description": (
                "Run a web search through the unified anysearch adapter. Works across "
                "every configured provider with one set of parameters; returns a common "
                "result shape (title, url, snippet, text, summary, highlights, score, "
                "published_date). Omit `provider` to auto-select from available API keys."
            ),
            "inputSchema": _search_schema(provider_enum),
        },
        {
            "name": "list_providers",
            "description": (
                "List every known provider with capabilities and whether it is configured "
                "(its API key is set). Shows the provider that auto-selection would pick."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "configured_only": {"type": "boolean", "default": False},
                },
            },
        },
        {
            "name": "check_providers",
            "description": (
                "Run a tiny live query against each configured provider and report which "
                "ones are actually working right now (verifies keys + connectivity)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "providers": {"type": "array", "items": {"type": "string"},
                                  "description": "Limit the check to these providers."},
                },
            },
        },
        {
            "name": "migrate_codebase",
            "description": (
                "Scan a codebase for direct search-API usage (SDK imports, client "
                "constructors, REST endpoints for Exa, Tavily, Brave, SerpAPI, Serper, "
                "Perplexity, Linkup, Firecrawl, Jina, Kagi, You, SearchApi, Google PSE, "
                "SearXNG, DuckDuckGo) and return precise call sites with suggested unified "
                "anysearch replacements. Detection-only: use the findings to perform edits."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": ".",
                             "description": "Directory or file to scan."},
                    "providers": {"type": "array", "items": {"type": "string"},
                                  "description": "Limit detection to these providers."},
                    "max_files": {"type": "integer", "default": 2000},
                },
            },
        },
    ]


# --------------------------------------------------------------------------
# Tool implementations
# --------------------------------------------------------------------------

def tool_search(args: Dict[str, Any]) -> Dict[str, Any]:
    query = args.pop("query", None)
    if not query:
        raise ValueError("`query` is required")
    args.pop("api_key", None)  # never accept secrets over the wire
    resp = _client.search(query, **args)
    return resp.to_dict(include_raw=False)


def tool_list_providers(args: Dict[str, Any]) -> Dict[str, Any]:
    info = _client.provider_info()
    if args.get("configured_only"):
        info = [p for p in info if p["configured"]]
    try:
        default = select_provider()
    except AnySearchError:
        default = None
    return {
        "default_provider": default,
        "configured": [p["name"] for p in info if p["configured"]],
        "providers": info,
    }


def tool_check_providers(args: Dict[str, Any]) -> Dict[str, Any]:
    names = args.get("providers") or available_providers()
    results = {}
    for name in names:
        try:
            get_provider_class(name)
        except AnySearchError:
            results[name] = {"working": False, "error": "unknown provider"}
            continue
        ok = probe_provider(name)
        results[name] = {"working": ok}
    return {"checked": list(results), "results": results,
            "working": [n for n, v in results.items() if v.get("working")]}


def tool_migrate(args: Dict[str, Any]) -> Dict[str, Any]:
    return scan_codebase(
        root=args.get("path", "."),
        providers=args.get("providers"),
        max_files=int(args.get("max_files", 2000)),
    )


_TOOLS = {
    "search": tool_search,
    "list_providers": tool_list_providers,
    "check_providers": tool_check_providers,
    "migrate_codebase": tool_migrate,
}


# --------------------------------------------------------------------------
# JSON-RPC plumbing
# --------------------------------------------------------------------------

def _result(req_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


class Server:
    def __init__(self, probe: bool = False) -> None:
        self.provider_enum = discover_providers(probe=probe)
        log(f"v{__version__} ready. usable providers: {', '.join(self.provider_enum) or 'none'}")

    def handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = message.get("method")
        req_id = message.get("id")
        is_notification = "id" not in message
        try:
            if method == "initialize":
                client_version = (message.get("params") or {}).get("protocolVersion")
                return _result(req_id, {
                    "protocolVersion": client_version or PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": __version__},
                })
            if method in ("notifications/initialized", "initialized", "notifications/cancelled"):
                return None
            if method == "ping":
                return _result(req_id, {})
            if method == "tools/list":
                return _result(req_id, {"tools": build_tools(self.provider_enum)})
            if method == "tools/call":
                return self._handle_tool_call(req_id, message.get("params") or {})
            if is_notification:
                return None
            return _error(req_id, -32601, f"Method not found: {method}")
        except Exception as exc:  # noqa: BLE001
            log("handler error:", traceback.format_exc())
            if is_notification:
                return None
            return _error(req_id, -32603, f"Internal error: {exc}")

    def _handle_tool_call(self, req_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        impl = _TOOLS.get(name)
        if impl is None:
            return _error(req_id, -32602, f"Unknown tool: {name}")
        try:
            payload = impl(dict(arguments))
            text = json.dumps(payload, indent=2, default=str)
            return _result(req_id, {
                "content": [{"type": "text", "text": text}],
                "structuredContent": payload if isinstance(payload, dict) else {"result": payload},
                "isError": False,
            })
        except AnySearchError as exc:
            return _result(req_id, {
                "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
                "isError": True,
            })
        except Exception as exc:  # noqa: BLE001
            log("tool error:", traceback.format_exc())
            return _result(req_id, {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            })


def main() -> None:
    probe = "--probe" in sys.argv or os.environ.get("ANYSEARCH_MCP_PROBE", "").lower() in (
        "1", "true", "yes", "on",
    )
    server = Server(probe=probe)
    stdout = sys.stdout

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            log("could not parse line as JSON; skipping")
            continue

        messages = message if isinstance(message, list) else [message]
        for msg in messages:
            response = server.handle(msg)
            if response is not None:
                stdout.write(json.dumps(response, default=str) + "\n")
                stdout.flush()


if __name__ == "__main__":
    main()
