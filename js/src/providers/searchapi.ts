import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const searchapi: ProviderSpec = {
  name: "searchapi",
  envKeys: ["SEARCHAPI_API_KEY", "SEARCHAPI_KEY"],
  defaultBaseUrl: "https://www.searchapi.io",
  capabilities: new Set(["country", "language", "news"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const params: Record<string, string | number | boolean | undefined> = {
      engine: req.searchType === "news" ? "google_news" : "google",
      q: req.query,
      num: req.maxResults,
    };
    if (req.country) params.gl = req.country.toLowerCase();
    if (req.language) params.hl = req.language;
    for (const [k, v] of Object.entries(req.extra)) params[k] = v as string;
    return {
      method: "GET",
      url: `${ctx.baseUrl}/api/v1/search`,
      headers: { Authorization: `Bearer ${ctx.apiKey ?? ""}`, Accept: "application/json" },
      params,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const items = data.organic_results ?? data.news_results ?? [];
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
    return finalize(searchapi, req, results, data, { answer, totalResults: total, elapsedMs });
  },
};
