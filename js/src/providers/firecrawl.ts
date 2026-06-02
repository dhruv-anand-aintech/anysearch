import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const firecrawl: ProviderSpec = {
  name: "firecrawl",
  envKeys: ["FIRECRAWL_API_KEY"],
  defaultBaseUrl: "https://api.firecrawl.dev",
  extraPackage: "@mendable/firecrawl-js",
  nativeImport: { module: "@mendable/firecrawl-js", exports: ["Firecrawl", "default", "FirecrawlApp"] },
  capabilities: new Set(["country", "content", "news"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const sources = req.searchType === "news" ? [{ type: "news" }] : [{ type: "web" }];
    const body: Record<string, unknown> = {
      query: req.query,
      limit: Math.min(req.maxResults, 100),
      sources,
    };
    if (req.country) body.country = req.country.toUpperCase();
    if (req.includeContent) body.scrapeOptions = { formats: ["markdown"], onlyMainContent: true };
    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v2/search`,
      headers: { Authorization: `Bearer ${ctx.apiKey ?? ""}`, "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const payload = data.data ?? data;
    let items: any[] = [];
    if (Array.isArray(payload)) {
      items = payload;
    } else if (payload && typeof payload === "object") {
      for (const key of ["web", "news", "images"]) items = items.concat(payload[key] ?? []);
    }
    const results = items.map((item: any) =>
      result({
        title: item.title ?? item.metadata?.title,
        url: item.url,
        snippet: item.description ?? item.metadata?.description,
        text: item.markdown,
        publishedDate: item.date,
        raw: item,
      }),
    );
    return finalize(firecrawl, req, results, data, { elapsedMs });
  },
};
