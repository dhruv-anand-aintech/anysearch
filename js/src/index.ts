/**
 * anysearch — one interface for every web search API.
 *
 * ```ts
 * import { search } from "anysearch";
 *
 * // Auto-selects a provider from whatever API keys are set in the environment.
 * const resp = await search("who won the 2026 super bowl?", { maxResults: 5 });
 * for (const r of resp.results) console.log(r.title, r.url);
 *
 * // Or target a specific provider with the same parameters.
 * const exa = await search("vector databases", { provider: "exa", includeContent: true });
 * ```
 */

export { AnySearch, search, listProviders, providerInfo, native } from "./client.js";
export type { AnySearchOptions, ProviderInfo } from "./client.js";
export {
  availableProviders,
  selectProvider,
  enforceCapabilities,
  unsupportedParams,
} from "./router.js";
export { getProviderSpec, listProviderNames, PROVIDER_SPECS, DEFAULT_PRIORITY } from "./providers/index.js";
export type { ProviderSpec, ProviderContext } from "./providers/base.js";
export * from "./errors.js";
export type {
  Capability,
  Env,
  Mode,
  SafeSearch,
  SearchParams,
  SearchRequest,
  SearchResponse,
  SearchResult,
  SearchType,
} from "./types.js";

export const VERSION = "0.1.0";
