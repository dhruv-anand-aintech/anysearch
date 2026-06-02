/** Unified request and response types shared by every provider. */

export type SafeSearch = "off" | "moderate" | "strict";
export type Mode = "fast" | "balanced" | "deep";
export type SearchType = "web" | "news";

export type Capability =
  | "domains"
  | "country"
  | "language"
  | "date"
  | "safe_search"
  | "mode"
  | "engine"
  | "answer"
  | "content"
  | "summary"
  | "highlights"
  | "news";

export type Env = Record<string, string | undefined>;

/** Options accepted by `search()` and `AnySearch.search()`. */
export interface SearchParams {
  /** Provider name or alias. Omit to auto-select from configured keys. */
  provider?: string;
  maxResults?: number;
  searchType?: SearchType;
  /** SerpApi backend (google, bing, baidu, yandex, duckduckgo, …). */
  engine?: string;
  /** ISO 3166-1 alpha-2, e.g. "us". */
  country?: string;
  /** ISO 639-1, e.g. "en". */
  language?: string;
  includeDomains?: string[];
  excludeDomains?: string[];
  /** ISO 8601 / YYYY-MM-DD. */
  startPublishedDate?: string;
  endPublishedDate?: string;
  safeSearch?: SafeSearch;
  /** Depth/quality knob, mapped per provider. */
  mode?: Mode;
  /** Request a synthesized, cited answer where supported. */
  answer?: boolean;
  /** Return full page text where supported. */
  includeContent?: boolean;
  /** Return a per-result AI summary where supported. */
  includeSummary?: boolean;
  /** Return query-relevant excerpts where supported. */
  highlights?: boolean;
  /** Raw provider-specific params merged into the native request. */
  extra?: Record<string, unknown>;
  /** Per-provider passthrough params: { exa: {...}, tavily: {...} }. */
  providerParams?: Record<string, Record<string, unknown>>;
  /** Providers to try if the primary fails. */
  fallbacks?: string[];
  /** Override the API key for the named provider. */
  apiKey?: string;
  /** Override the base URL for the named provider. */
  baseUrl?: string;
  /** How to handle params the provider can't honor. Default "warn". */
  onUnsupported?: "ignore" | "warn" | "error";
  /** Request timeout in milliseconds. Default 30000. */
  timeoutMs?: number;
}

/** Fully-normalized request handed to a provider adapter. */
export interface SearchRequest {
  query: string;
  maxResults: number;
  searchType: SearchType;
  engine?: string;
  country?: string;
  language?: string;
  includeDomains: string[];
  excludeDomains: string[];
  startPublishedDate?: string;
  endPublishedDate?: string;
  safeSearch?: SafeSearch;
  mode?: Mode;
  answer: boolean;
  includeContent: boolean;
  includeSummary: boolean;
  highlights: boolean;
  extra: Record<string, unknown>;
}

export interface SearchResult {
  title?: string;
  url?: string;
  /** Short description, as returned by the engine. */
  snippet?: string;
  /** Full page content, if requested & supported. */
  text?: string;
  /** AI-generated summary, if requested & supported. */
  summary?: string;
  /** Query-relevant excerpts. */
  highlights: string[];
  /** Relevance score, if the provider exposes one. */
  score?: number;
  publishedDate?: string;
  author?: string;
  /** The result's domain/host. */
  source?: string;
  /** The provider's raw result object. */
  raw?: unknown;
}

export interface SearchResponse {
  provider: string;
  query: string;
  results: SearchResult[];
  answer?: string;
  totalResults?: number;
  latencyMs?: number;
  requestId?: string;
  raw?: unknown;
}

export function makeRequest(query: string, params: Partial<SearchRequest> = {}): SearchRequest {
  if (!query || !String(query).trim()) {
    throw new Error("`query` must be a non-empty string");
  }
  return {
    query,
    maxResults: params.maxResults ?? 10,
    searchType: params.searchType ?? "web",
    engine: params.engine,
    country: params.country,
    language: params.language,
    includeDomains: params.includeDomains ?? [],
    excludeDomains: params.excludeDomains ?? [],
    startPublishedDate: params.startPublishedDate,
    endPublishedDate: params.endPublishedDate,
    safeSearch: params.safeSearch,
    mode: params.mode,
    answer: params.answer ?? false,
    includeContent: params.includeContent ?? false,
    includeSummary: params.includeSummary ?? false,
    highlights: params.highlights ?? false,
    extra: params.extra ?? {},
  };
}
