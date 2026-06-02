import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const serpapi: ProviderSpec = {
  name: "serpapi",
  aliases: ["serp"],
  envKeys: ["SERPAPI_API_KEY", "SERPAPI_KEY"],
  defaultBaseUrl: "https://serpapi.com",
  extraPackage: "serpapi",
  nativeImport: { module: "serpapi", exports: ["getJson", "GoogleSearch"] },
  capabilities: new Set(["country", "language", "safe_search", "news"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const params: Record<string, string | number | boolean | undefined> = {
      engine: "google",
      q: req.query,
      num: req.maxResults,
      api_key: ctx.apiKey,
    };
    if (req.country) params.gl = req.country.toLowerCase();
    if (req.language) params.hl = req.language;
    if (req.safeSearch) params.safe = req.safeSearch === "off" ? "off" : "active";
    if (req.searchType === "news") params.tbm = "nws";
    for (const [k, v] of Object.entries(req.extra)) params[k] = v as string;
    return { method: "GET", url: `${ctx.baseUrl}/search`, headers: { Accept: "application/json" }, params };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const items = req.searchType === "news" ? data.news_results ?? [] : data.organic_results ?? [];
    const results = items.map((item: any) =>
      result({
        title: item.title,
        url: item.link,
        snippet: item.snippet,
        source: item.source,
        publishedDate: item.date,
        score: item.position,
        raw: item,
      }),
    );
    const box = data.answer_box ?? {};
    const answer = box.answer ?? box.snippet;
    const total = data.search_information?.total_results;
    return finalize(serpapi, req, results, data, { answer, totalResults: total, elapsedMs });
  },
};
