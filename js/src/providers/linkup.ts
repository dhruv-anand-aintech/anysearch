import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const MODE: Record<string, string> = { fast: "fast", balanced: "standard", deep: "deep" };

export const linkup: ProviderSpec = {
  name: "linkup",
  envKeys: ["LINKUP_API_KEY"],
  defaultBaseUrl: "https://api.linkup.so",
  extraPackage: "linkup-sdk",
  nativeImport: { module: "linkup-sdk", exports: ["LinkupClient", "default"] },
  capabilities: new Set(["domains", "date", "mode", "answer", "content"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = {
      q: req.query,
      depth: MODE[req.mode ?? ""] ?? "standard",
      outputType: req.answer ? "sourcedAnswer" : "searchResults",
    };
    if (req.includeDomains.length) body.includeDomains = req.includeDomains;
    if (req.excludeDomains.length) body.excludeDomains = req.excludeDomains;
    if (req.startPublishedDate) body.fromDate = req.startPublishedDate.slice(0, 10);
    if (req.endPublishedDate) body.toDate = req.endPublishedDate.slice(0, 10);
    if (req.maxResults) body.maxResults = req.maxResults;
    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1/search`,
      headers: { Authorization: `Bearer ${ctx.apiKey ?? ""}`, "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const sources = data.results ?? data.sources ?? [];
    const results = sources.map((item: any) => {
      const content = item.content ?? item.snippet;
      return result({
        title: item.name ?? item.title,
        url: item.url,
        snippet: content,
        text: content,
        raw: item,
      });
    });
    return finalize(linkup, req, results, data, { answer: data.answer, elapsedMs });
  },
};
