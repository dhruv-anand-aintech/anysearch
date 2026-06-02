import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";
import {
  applySerpapiLocale,
  applySerpapiSafeSearch,
  extractSerpapiAnswer,
  extractSerpapiResults,
  normalizeEngine,
  resolveSerpapiEngine,
  SERPAPI_WEB_ENGINES,
} from "./serpapiEngines.js";

export const serpapi: ProviderSpec = {
  name: "serpapi",
  aliases: ["serp"],
  envKeys: ["SERPAPI_API_KEY", "SERPAPI_KEY"],
  defaultBaseUrl: "https://serpapi.com",
  extraPackage: "serpapi",
  nativeImport: { module: "serpapi", exports: ["getJson", "GoogleSearch"] },
  capabilities: new Set(["country", "language", "safe_search", "news", "engine"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const defaultEngine = normalizeEngine(
      String(ctx.config?.engine ?? ctx.config?.defaultEngine ?? "google"),
    );
    const extra = { ...req.extra };
    const engine = resolveSerpapiEngine({
      engine: req.engine,
      defaultEngine,
      searchType: req.searchType,
      extra,
    });
    const params: Record<string, string | number | boolean | undefined> = {
      engine,
      q: req.query,
      num: req.maxResults,
      api_key: ctx.apiKey,
    };
    applySerpapiLocale(params, engine, req.country, req.language);
    applySerpapiSafeSearch(params, engine, req.safeSearch);
    for (const [k, v] of Object.entries(extra)) params[k] = v as string;
    return { method: "GET", url: `${ctx.baseUrl}/search`, headers: { Accept: "application/json" }, params };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = (res.data ?? {}) as Record<string, unknown>;
    const items = extractSerpapiResults(data, req.searchType);
    const results = items.map((item: any) =>
      result({
        title: item.title,
        url: item.link ?? item.url,
        snippet: item.snippet ?? item.description,
        source: item.source ?? item.displayed_link,
        publishedDate: item.date,
        score: item.position,
        raw: item,
      }),
    );
    const answer = extractSerpapiAnswer(data);
    const total = (data.search_information as { total_results?: number } | undefined)?.total_results;
    return finalize(serpapi, req, results, data, { answer, totalResults: total, elapsedMs });
  },
};

export { SERPAPI_WEB_ENGINES };
