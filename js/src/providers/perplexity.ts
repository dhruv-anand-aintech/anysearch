import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const perplexity: ProviderSpec = {
  name: "perplexity",
  aliases: ["pplx"],
  envKeys: ["PERPLEXITY_API_KEY", "PPLX_API_KEY"],
  defaultBaseUrl: "https://api.perplexity.ai",
  extraPackage: "@perplexity-ai/perplexity_ai",
  nativeImport: { module: "@perplexity-ai/perplexity_ai", exports: ["Perplexity", "default"] },
  capabilities: new Set(["domains", "language", "content"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = { query: req.query, max_results: Math.min(req.maxResults, 20) };
    const domains = [...req.includeDomains, ...req.excludeDomains.map((d) => `-${d}`)];
    if (domains.length) body.search_domain_filter = domains;
    if (req.language) body.search_language_filter = [req.language.slice(0, 2)];
    if (req.includeContent) {
      body.snippet_mode = "high";
      body.max_tokens_per_page = 8192;
    }
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
        snippet: item.snippet,
        text: req.includeContent ? item.snippet : undefined,
        publishedDate: item.date ?? item.last_updated,
        raw: item,
      }),
    );
    return finalize(perplexity, req, results, data, { elapsedMs });
  },
};
