/** Provider selection and cross-provider capability handling. */

import { NoProviderAvailableError, UnsupportedParameterError } from "./errors.js";
import { DEFAULT_PRIORITY, getProviderSpec, PROVIDER_SPECS } from "./providers/index.js";
import { isActive, isConfigured, PARAM_CAPABILITY, type ProviderSpec } from "./providers/base.js";
import type { Env, SearchRequest } from "./types.js";

export function availableProviders(env: Env): string[] {
  return PROVIDER_SPECS.filter((spec) => isConfigured(spec, env)).map((s) => s.name);
}

export function selectProvider(env: Env, priority?: string[]): string {
  const override = env.ANYSEARCH_PROVIDER || env.ANYSEARCH_SEARCH_PROVIDER;
  if (override) return override.trim().toLowerCase();
  for (const name of priority ?? DEFAULT_PRIORITY) {
    if (isConfigured(getProviderSpec(name), env)) return name;
  }
  throw new NoProviderAvailableError(
    "No search provider is configured. Set an API key (e.g. EXA_API_KEY, TAVILY_API_KEY, " +
      "BRAVE_API_KEY) or point SEARXNG_BASE_URL at an instance. DuckDuckGo works with no key.",
  );
}

export function unsupportedParams(spec: ProviderSpec, req: SearchRequest): string[] {
  const out: string[] = [];
  for (const [field, capability] of Object.entries(PARAM_CAPABILITY)) {
    if (isActive(field, req) && !spec.capabilities.has(capability)) out.push(field);
  }
  if (req.searchType === "news" && !spec.capabilities.has("news")) out.push("searchType=news");
  return out;
}

export function enforceCapabilities(
  spec: ProviderSpec,
  req: SearchRequest,
  onUnsupported: "ignore" | "warn" | "error" = "warn",
): SearchRequest {
  const missing = unsupportedParams(spec, req);
  if (missing.length === 0) return req;
  if (onUnsupported === "error") throw new UnsupportedParameterError(spec.name, missing);
  if (onUnsupported === "warn") {
    console.warn(
      `[anysearch] provider '${spec.name}' does not support ${JSON.stringify(missing)}; ` +
        `ignoring. Pass onUnsupported: 'ignore' to silence or 'error' to raise.`,
    );
  }
  const next = { ...req } as unknown as Record<string, unknown>;
  for (const field of missing) {
    switch (field) {
      case "searchType=news":
        next.searchType = "web";
        break;
      case "includeDomains":
        next.includeDomains = [];
        break;
      case "excludeDomains":
        next.excludeDomains = [];
        break;
      case "answer":
      case "includeContent":
      case "includeSummary":
      case "highlights":
        next[field] = false;
        break;
      default:
        next[field] = undefined;
    }
  }
  return next as unknown as SearchRequest;
}
