import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const MODE: Record<string, string> = { fast: "fast", balanced: "basic", deep: "advanced" };

export const tavily: ProviderSpec = {
  name: "tavily",
  envKeys: ["TAVILY_API_KEY"],
  defaultBaseUrl: "https://api.tavily.com",
  extraPackage: "@tavily/core",
  nativeImport: { module: "@tavily/core", exports: ["tavily", "TavilyClient"] },
  capabilities: new Set(["domains", "country", "date", "mode", "answer", "content", "news"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = {
      query: req.query,
      max_results: Math.min(req.maxResults, 20),
      search_depth: MODE[req.mode ?? ""] ?? "basic",
      topic: req.searchType === "news" ? "news" : "general",
    };
    if (req.includeDomains.length) body.include_domains = req.includeDomains;
    if (req.excludeDomains.length) body.exclude_domains = req.excludeDomains;
    if (req.startPublishedDate) body.start_date = req.startPublishedDate.slice(0, 10);
    if (req.endPublishedDate) body.end_date = req.endPublishedDate.slice(0, 10);
    if (req.country) body.country = req.country.toLowerCase();
    if (req.answer) body.include_answer = true;
    if (req.includeContent) body.include_raw_content = true;
    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/search`,
      headers: { Authorization: `Bearer ${ctx.apiKey ?? ""}`, "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.results ?? []).map((item: any) =>
      result({
        title: item.title,
        url: item.url,
        snippet: item.content,
        text: item.raw_content,
        highlights: item.content ? [item.content] : [],
        score: item.score,
        publishedDate: item.published_date,
        raw: item,
      }),
    );
    return finalize(tavily, req, results, data, {
      answer: data.answer,
      requestId: data.request_id,
      elapsedMs,
    });
  },
};
