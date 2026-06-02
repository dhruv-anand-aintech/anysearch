import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const MODE: Record<string, string> = { fast: "fast", balanced: "auto", deep: "deep" };

export const exa: ProviderSpec = {
  name: "exa",
  envKeys: ["EXA_API_KEY"],
  defaultBaseUrl: "https://api.exa.ai",
  extraPackage: "exa-js",
  nativeImport: { module: "exa-js", exports: ["Exa", "default"] },
  capabilities: new Set([
    "domains", "country", "date", "safe_search", "mode", "content", "summary", "highlights", "news",
  ]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = {
      query: req.query,
      numResults: req.maxResults,
      type: MODE[req.mode ?? ""] ?? "auto",
    };
    if (req.includeDomains.length) body.includeDomains = req.includeDomains;
    if (req.excludeDomains.length) body.excludeDomains = req.excludeDomains;
    if (req.startPublishedDate) body.startPublishedDate = req.startPublishedDate;
    if (req.endPublishedDate) body.endPublishedDate = req.endPublishedDate;
    if (req.country) body.userLocation = req.country.toUpperCase();
    if (req.safeSearch && req.safeSearch !== "off") body.moderation = true;
    if (req.searchType === "news") body.category = "news";

    const contents: Record<string, unknown> = {};
    if (req.includeContent) contents.text = true;
    if (req.highlights) contents.highlights = true;
    if (req.includeSummary) contents.summary = true;
    if (Object.keys(contents).length) body.contents = contents;

    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/search`,
      headers: { "x-api-key": ctx.apiKey ?? "", "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.results ?? []).map((item: any) => {
      const highlights = Array.isArray(item.highlights)
        ? item.highlights
        : item.highlights
          ? [item.highlights]
          : [];
      return result({
        title: item.title,
        url: item.url,
        snippet: item.summary ?? highlights[0],
        text: item.text,
        summary: item.summary,
        highlights,
        score: item.score,
        publishedDate: item.publishedDate,
        author: item.author,
        raw: item,
      });
    });
    const answer = data.output && typeof data.output.content === "string" ? data.output.content : undefined;
    return finalize(exa, req, results, data, { answer, requestId: data.requestId, elapsedMs });
  },
};
