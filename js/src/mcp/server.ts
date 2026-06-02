#!/usr/bin/env node
/**
 * A dependency-free stdio MCP server that adapts to configured search providers.
 *
 * Run with `anysearch-mcp` (bin) or `node dist/mcp/server.js`. Implements MCP over
 * newline-delimited JSON-RPC on stdin/stdout (logs to stderr). The `provider` enum on
 * the `search` tool is derived from which API keys are present in the environment;
 * pass `--probe` (or set `ANYSEARCH_MCP_PROBE=1`) to verify each with a tiny live query.
 */

import { createInterface } from "node:readline";
import { AnySearch } from "../client.js";
import { AnySearchError } from "../errors.js";
import { getProviderSpec } from "../providers/index.js";
import { availableProviders, selectProvider } from "../router.js";
import type { Env, SearchParams } from "../types.js";
import { scanCodebase } from "./migrate.js";

const PROTOCOL_VERSION = "2025-06-18";
const SERVER_NAME = "anysearch";
const VERSION = "0.1.0";

const client = new AnySearch();
const env = process.env as Env;

function log(...args: unknown[]): void {
  console.error("[anysearch-mcp]", ...args);
}

async function probeProvider(name: string, timeoutMs = 8000): Promise<boolean> {
  try {
    await client.search("anysearch health check", {
      provider: name,
      maxResults: 1,
      onUnsupported: "ignore",
      timeoutMs,
    });
    return true;
  } catch (err) {
    log(`probe ${name}: not working (${(err as Error).message})`);
    return false;
  }
}

async function discoverProviders(probe: boolean): Promise<string[]> {
  const configured = availableProviders(env);
  if (!probe) return configured;
  const working: string[] = [];
  for (const name of configured) if (await probeProvider(name)) working.push(name);
  return working.length ? working : configured;
}

function searchSchema(providerEnum: string[]): Record<string, unknown> {
  const providerProp: Record<string, unknown> = {
    type: "string",
    description: "Search provider to use. Omit to auto-select from configured keys.",
  };
  if (providerEnum.length) providerProp.enum = providerEnum;
  return {
    type: "object",
    properties: {
      query: { type: "string", description: "The search query." },
      provider: providerProp,
      max_results: { type: "integer", default: 10, minimum: 1, maximum: 100 },
      search_type: { type: "string", enum: ["web", "news"], default: "web" },
      country: { type: "string", description: "ISO 3166-1 alpha-2, e.g. 'us'." },
      language: { type: "string", description: "ISO 639-1, e.g. 'en'." },
      include_domains: { type: "array", items: { type: "string" } },
      exclude_domains: { type: "array", items: { type: "string" } },
      start_published_date: { type: "string", description: "ISO 8601 / YYYY-MM-DD." },
      end_published_date: { type: "string", description: "ISO 8601 / YYYY-MM-DD." },
      safe_search: { type: "string", enum: ["off", "moderate", "strict"] },
      mode: { type: "string", enum: ["fast", "balanced", "deep"], description: "Depth/quality knob." },
      answer: { type: "boolean", description: "Request a synthesized answer where supported." },
      include_content: { type: "boolean", description: "Return full page text where supported." },
      include_summary: { type: "boolean", description: "Return per-result AI summary where supported." },
      highlights: { type: "boolean", description: "Return relevant excerpts where supported." },
      fallbacks: { type: "array", items: { type: "string" } },
      extra: { type: "object", description: "Raw provider-specific params (passthrough)." },
    },
    required: ["query"],
  };
}

function buildTools(providerEnum: string[]): Record<string, unknown>[] {
  return [
    {
      name: "search",
      description:
        "Run a web search through the unified anysearch adapter. Works across every " +
        "configured provider with one set of parameters; returns a common result shape " +
        "(title, url, snippet, text, summary, highlights, score, publishedDate). Omit " +
        "`provider` to auto-select from available API keys.",
      inputSchema: searchSchema(providerEnum),
    },
    {
      name: "list_providers",
      description:
        "List every known provider with capabilities and whether it is configured (its " +
        "API key is set). Shows the provider that auto-selection would pick.",
      inputSchema: {
        type: "object",
        properties: { configured_only: { type: "boolean", default: false } },
      },
    },
    {
      name: "check_providers",
      description:
        "Run a tiny live query against each configured provider and report which ones are " +
        "actually working right now (verifies keys + connectivity).",
      inputSchema: {
        type: "object",
        properties: { providers: { type: "array", items: { type: "string" } } },
      },
    },
    {
      name: "migrate_codebase",
      description:
        "Scan a codebase for direct search-API usage (SDK imports, client constructors, " +
        "REST endpoints for Exa, Tavily, Brave, SerpAPI, Serper, Perplexity, Linkup, " +
        "Firecrawl, Jina, Kagi, You, SearchApi, Google PSE, SearXNG, DuckDuckGo) and return " +
        "precise call sites with suggested unified anysearch replacements. Detection-only.",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string", default: ".", description: "Directory or file to scan." },
          providers: { type: "array", items: { type: "string" } },
          max_files: { type: "integer", default: 2000 },
        },
      },
    },
  ];
}

// --- tool implementations ---------------------------------------------------

const SNAKE_TO_CAMEL: Record<string, keyof SearchParams> = {
  max_results: "maxResults",
  search_type: "searchType",
  include_domains: "includeDomains",
  exclude_domains: "excludeDomains",
  start_published_date: "startPublishedDate",
  end_published_date: "endPublishedDate",
  safe_search: "safeSearch",
  include_content: "includeContent",
  include_summary: "includeSummary",
};

function toParams(args: Record<string, unknown>): SearchParams {
  const params: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(args)) {
    if (key === "query" || key === "api_key") continue;
    params[SNAKE_TO_CAMEL[key] ?? key] = value;
  }
  return params as SearchParams;
}

async function toolSearch(args: Record<string, unknown>): Promise<unknown> {
  const query = args.query as string;
  if (!query) throw new Error("`query` is required");
  const resp = await client.search(query, toParams(args));
  // Strip raw payloads to keep the response compact for the model.
  return {
    provider: resp.provider,
    query: resp.query,
    answer: resp.answer,
    total_results: resp.totalResults,
    latency_ms: resp.latencyMs,
    results: resp.results.map((r) => ({ ...r, raw: undefined })),
  };
}

function toolListProviders(args: Record<string, unknown>): unknown {
  let info = client.providerInfo();
  if (args.configured_only) info = info.filter((p) => p.configured);
  let def: string | null = null;
  try {
    def = selectProvider(env);
  } catch {
    def = null;
  }
  return {
    default_provider: def,
    configured: client.providerInfo().filter((p) => p.configured).map((p) => p.name),
    providers: info,
  };
}

async function toolCheckProviders(args: Record<string, unknown>): Promise<unknown> {
  const names = (args.providers as string[]) ?? availableProviders(env);
  const results: Record<string, { working: boolean; error?: string }> = {};
  for (const name of names) {
    try {
      getProviderSpec(name);
    } catch {
      results[name] = { working: false, error: "unknown provider" };
      continue;
    }
    results[name] = { working: await probeProvider(name) };
  }
  return {
    checked: Object.keys(results),
    results,
    working: Object.entries(results).filter(([, v]) => v.working).map(([n]) => n),
  };
}

function toolMigrate(args: Record<string, unknown>): unknown {
  return scanCodebase(
    (args.path as string) ?? ".",
    args.providers as string[] | undefined,
    Number(args.max_files ?? 2000),
  );
}

type ToolFn = (args: Record<string, unknown>) => unknown | Promise<unknown>;
const TOOLS: Record<string, ToolFn> = {
  search: toolSearch,
  list_providers: toolListProviders,
  check_providers: toolCheckProviders,
  migrate_codebase: toolMigrate,
};

// --- JSON-RPC plumbing ------------------------------------------------------

interface JsonRpcMessage {
  jsonrpc?: string;
  id?: unknown;
  method?: string;
  params?: Record<string, unknown>;
}

export class Server {
  providerEnum: string[];

  constructor(providerEnum: string[]) {
    this.providerEnum = providerEnum;
  }

  static async create(probe = false): Promise<Server> {
    const providers = await discoverProviders(probe);
    log(`v${VERSION} ready. usable providers: ${providers.join(", ") || "none"}`);
    return new Server(providers);
  }

  private result(id: unknown, result: unknown) {
    return { jsonrpc: "2.0", id, result };
  }

  private error(id: unknown, code: number, message: string) {
    return { jsonrpc: "2.0", id, error: { code, message } };
  }

  async handle(message: JsonRpcMessage): Promise<Record<string, unknown> | null> {
    const { method, id } = message;
    const isNotification = !("id" in message);
    try {
      switch (method) {
        case "initialize": {
          const clientVersion = (message.params?.protocolVersion as string) ?? PROTOCOL_VERSION;
          return this.result(id, {
            protocolVersion: clientVersion,
            capabilities: { tools: { listChanged: false } },
            serverInfo: { name: SERVER_NAME, version: VERSION },
          });
        }
        case "notifications/initialized":
        case "initialized":
        case "notifications/cancelled":
          return null;
        case "ping":
          return this.result(id, {});
        case "tools/list":
          return this.result(id, { tools: buildTools(this.providerEnum) });
        case "tools/call":
          return await this.handleToolCall(id, message.params ?? {});
        default:
          return isNotification ? null : this.error(id, -32601, `Method not found: ${method}`);
      }
    } catch (err) {
      log("handler error:", err);
      return isNotification ? null : this.error(id, -32603, `Internal error: ${(err as Error).message}`);
    }
  }

  private async handleToolCall(id: unknown, params: Record<string, unknown>) {
    const name = params.name as string;
    const args = (params.arguments as Record<string, unknown>) ?? {};
    const impl = TOOLS[name];
    if (!impl) return this.error(id, -32602, `Unknown tool: ${name}`);
    try {
      const payload = await impl({ ...args });
      return this.result(id, {
        content: [{ type: "text", text: JSON.stringify(payload, null, 2) }],
        structuredContent: payload && typeof payload === "object" ? payload : { result: payload },
        isError: false,
      });
    } catch (err) {
      const message =
        err instanceof AnySearchError ? `${err.name}: ${err.message}` : `Error: ${(err as Error).message}`;
      return this.result(id, { content: [{ type: "text", text: message }], isError: true });
    }
  }
}

export async function main(): Promise<void> {
  const probe =
    process.argv.includes("--probe") ||
    ["1", "true", "yes", "on"].includes((process.env.ANYSEARCH_MCP_PROBE ?? "").toLowerCase());
  const server = await Server.create(probe);

  const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    let message: JsonRpcMessage | JsonRpcMessage[];
    try {
      message = JSON.parse(trimmed);
    } catch {
      log("could not parse line as JSON; skipping");
      continue;
    }
    const messages = Array.isArray(message) ? message : [message];
    for (const msg of messages) {
      const response = await server.handle(msg);
      if (response !== null) process.stdout.write(JSON.stringify(response) + "\n");
    }
  }
}

const isMain =
  process.argv[1] != null &&
  (import.meta.url === `file://${process.argv[1]}` || import.meta.url.endsWith(process.argv[1]));
if (isMain) {
  main().catch((err) => {
    log("fatal:", err);
    process.exit(1);
  });
}
