import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const MODE: Record<string, string> = { fast: "realtime", balanced: "pro", deep: "pro" };

export const keenable: ProviderSpec = {
  name: "keenable",
  envKeys: ["KEENABLE_API_KEY"],
  defaultBaseUrl: "https://api.keenable.ai",
  capabilities: new Set(["domains", "date", "mode", "content", "highlights"]),

  configHint() {
    return (
      "Set KEENABLE_API_KEY. mode=fast uses the realtime search SKU and " +
      "balanced/deep use pro; override the body with providerParams or extra."
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = {
      query: req.query,
      mode: MODE[req.mode ?? ""] ?? "pro",
      max_results: Math.max(1, Math.min(req.maxResults, 50)),
    };
    if (req.includeDomains.length) body.site = req.includeDomains[0];
    if (req.startPublishedDate) body.published_after = req.startPublishedDate;
    if (req.endPublishedDate) body.published_before = req.endPublishedDate;
    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1/search`,
      headers: { "X-API-Key": ctx.apiKey ?? "", "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.results ?? []).map((item: any) =>
      result({
        title: item.title,
        url: item.url,
        snippet: item.snippet ?? item.description,
        publishedDate: item.published_at,
        raw: item,
      }),
    );
    return finalize(keenable, req, results, data, {
      totalResults: results.length,
      elapsedMs,
    });
  },
};
