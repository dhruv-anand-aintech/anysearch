import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

function formatDate(value?: string): string | undefined {
  return value ? value.slice(0, 10) : undefined;
}

export const tinyfish: ProviderSpec = {
  name: "tinyfish",
  envKeys: ["TINYFISH_API_KEY"],
  defaultBaseUrl: "https://api.search.tinyfish.ai",
  capabilities: new Set(["domains", "country", "language", "date", "news"]),

  configHint() {
    return (
      "Set TINYFISH_API_KEY. Search is GET https://api.search.tinyfish.ai with " +
      "domain_type=web|news|research_paper; page 0-10 and no result-count parameter."
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const params: Record<string, string | number | boolean | undefined> = {
      query: req.query,
    };
    if (req.country) params.location = req.country.toUpperCase();
    if (req.language) params.language = req.language.toLowerCase();
    if (req.includeDomains.length) params.include_domains = req.includeDomains.join(",");
    if (req.excludeDomains.length) params.exclude_domains = req.excludeDomains.join(",");
    if (req.startPublishedDate) params.after_date = formatDate(req.startPublishedDate);
    if (req.endPublishedDate) params.before_date = formatDate(req.endPublishedDate);
    if (req.searchType === "news") params.domain_type = "news";
    for (const [key, value] of Object.entries(req.extra)) {
      params[key] = value as string | number | boolean | undefined;
    }
    return {
      method: "GET",
      url: ctx.baseUrl,
      headers: { "X-API-Key": ctx.apiKey ?? "", Accept: "application/json" },
      params,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.results ?? []).map((item: any) => {
      const authors = Array.isArray(item.authors)
        ? item.authors.filter(Boolean).join(", ")
        : item.authors;
      return result({
        title: item.title,
        url: item.url,
        snippet: item.snippet,
        publishedDate: item.date,
        author: authors || undefined,
        source: item.site_name ?? item.publisher,
        raw: item,
      });
    });
    return finalize(tinyfish, req, results, data, {
      totalResults: data.total_results,
      elapsedMs,
    });
  },
};
