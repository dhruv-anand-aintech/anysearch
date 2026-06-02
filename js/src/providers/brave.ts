import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const brave: ProviderSpec = {
  name: "brave",
  aliases: ["brave_search"],
  envKeys: ["BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY"],
  defaultBaseUrl: "https://api.search.brave.com",
  capabilities: new Set(["country", "language", "date", "safe_search", "highlights", "news"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const isNews = req.searchType === "news";
    const maxCount = isNews ? 50 : 20;
    const params: Record<string, string | number | boolean | undefined> = {
      q: req.query,
      count: Math.min(req.maxResults, maxCount),
    };
    if (req.country) params.country = req.country.toUpperCase();
    if (req.language) params.search_lang = req.language;
    if (req.safeSearch) params.safesearch = req.safeSearch;
    if (req.highlights) params.extra_snippets = "true";
    if (req.startPublishedDate || req.endPublishedDate) {
      const start = (req.startPublishedDate ?? "1970-01-01").slice(0, 10);
      const end = (req.endPublishedDate ?? new Date().toISOString()).slice(0, 10);
      params.freshness = `${start}to${end}`;
    }
    for (const [k, v] of Object.entries(req.extra)) params[k] = v as string;

    const path = isNews ? "/res/v1/news/search" : "/res/v1/web/search";
    return {
      method: "GET",
      url: `${ctx.baseUrl}${path}`,
      headers: { "X-Subscription-Token": ctx.apiKey ?? "", Accept: "application/json" },
      params,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const items = req.searchType === "news" ? data.results ?? [] : data.web?.results ?? [];
    const results = items.map((item: any) =>
      result({
        title: item.title,
        url: item.url,
        snippet: item.description,
        highlights: item.extra_snippets ?? [],
        publishedDate: item.page_age ?? item.age,
        raw: item,
      }),
    );
    return finalize(brave, req, results, data, { elapsedMs });
  },
};
