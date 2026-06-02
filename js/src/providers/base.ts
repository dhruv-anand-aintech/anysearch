/** Provider adapter contract, capability flags, and shared helpers. */

import type { HttpResponse, PreparedRequest } from "../http.js";
import type {
  Capability,
  Env,
  SearchRequest,
  SearchResponse,
  SearchResult,
} from "../types.js";

export interface ProviderContext {
  apiKey?: string;
  baseUrl: string;
  env: Env;
  /** Extra per-provider config (e.g. Google PSE `cx`). */
  config: Record<string, unknown>;
}

export interface ProviderSpec {
  name: string;
  aliases?: string[];
  envKeys?: string[];
  baseUrlEnv?: string[];
  defaultBaseUrl?: string;
  requiresKey?: boolean; // default true
  requiresBaseUrl?: boolean; // default false
  capabilities: Set<Capability>;
  /** npm package that provides this provider's official SDK (optional escape hatch). */
  extraPackage?: string;
  nativeImport?: { module: string; exports: string[] };

  prepare(ctx: ProviderContext, req: SearchRequest): PreparedRequest;
  parse(ctx: ProviderContext, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse;

  /** Override for providers needing more than a single key (Google PSE) or no key (SearXNG). */
  isConfigured?(env: Env): boolean;
  configHint?(): string;
}

/** Maps a unified request field to the capability it requires. */
export const PARAM_CAPABILITY: Record<string, Capability> = {
  includeDomains: "domains",
  excludeDomains: "domains",
  country: "country",
  language: "language",
  startPublishedDate: "date",
  endPublishedDate: "date",
  safeSearch: "safe_search",
  mode: "mode",
  engine: "engine",
  answer: "answer",
  includeContent: "content",
  includeSummary: "summary",
  highlights: "highlights",
};

export function isActive(field: string, req: SearchRequest): boolean {
  const value = (req as unknown as Record<string, unknown>)[field];
  if (value === undefined || value === null) return false;
  if (field === "includeDomains" || field === "excludeDomains") return (value as unknown[]).length > 0;
  if (typeof value === "boolean") return value;
  return Boolean(value);
}

export function domainOf(url?: string): string | undefined {
  if (!url) return undefined;
  try {
    const host = new URL(url.includes("://") ? url : `https://${url}`).hostname;
    return host.startsWith("www.") ? host.slice(4) : host || undefined;
  } catch {
    return undefined;
  }
}

export function result(partial: Partial<SearchResult>): SearchResult {
  return {
    ...partial,
    highlights: partial.highlights ?? [],
    source: partial.source ?? domainOf(partial.url),
  };
}

export function finalize(
  spec: ProviderSpec,
  req: SearchRequest,
  results: SearchResult[],
  raw: unknown,
  extras: { answer?: string; totalResults?: number; requestId?: string; elapsedMs?: number } = {},
): SearchResponse {
  let trimmed = results;
  if (req.maxResults && results.length > req.maxResults) {
    trimmed = results.slice(0, req.maxResults);
  }
  return {
    provider: spec.name,
    query: req.query,
    results: trimmed,
    answer: extras.answer,
    totalResults: extras.totalResults,
    latencyMs: extras.elapsedMs != null ? Math.round(extras.elapsedMs * 10) / 10 : undefined,
    requestId: extras.requestId,
    raw,
  };
}

// --- credential helpers -----------------------------------------------------

export function keyFromEnv(spec: ProviderSpec, env: Env): string | undefined {
  for (const k of spec.envKeys ?? []) {
    if (env[k]) return env[k];
  }
  return undefined;
}

export function baseUrlFromEnv(spec: ProviderSpec, env: Env): string | undefined {
  for (const k of spec.baseUrlEnv ?? []) {
    if (env[k]) return env[k];
  }
  return undefined;
}

export function isConfigured(spec: ProviderSpec, env: Env): boolean {
  if (spec.isConfigured) return spec.isConfigured(env);
  if (spec.requiresBaseUrl && !baseUrlFromEnv(spec, env) && !spec.defaultBaseUrl) return false;
  if (spec.requiresKey === false) return true;
  return Boolean(keyFromEnv(spec, env));
}

export function configHint(spec: ProviderSpec): string {
  if (spec.configHint) return spec.configHint();
  const parts: string[] = [];
  if (spec.requiresKey !== false && spec.envKeys?.length) parts.push(`Set ${spec.envKeys[0]}.`);
  if (spec.requiresBaseUrl && spec.baseUrlEnv?.length) parts.push(`Set ${spec.baseUrlEnv[0]}.`);
  return parts.join(" ");
}
