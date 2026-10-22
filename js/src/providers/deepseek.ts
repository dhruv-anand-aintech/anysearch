import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

function date(value?: string): string | undefined {
  return value ? value.slice(0, 10) : undefined;
}

function queryWithOperators(req: SearchRequest): string {
  const parts: string[] = [req.query];
  if (req.includeDomains.length) {
    parts.push(req.includeDomains.map((domain) => `site:${domain}`).join(" OR "));
  }
  for (const domain of req.excludeDomains) parts.push(`-site:${domain}`);
  if (req.language) parts.push(`lang:${req.language.toLowerCase()}`);
  if (req.startPublishedDate) parts.push(`after:${date(req.startPublishedDate)}`);
  if (req.endPublishedDate) parts.push(`before:${date(req.endPublishedDate)}`);
  return parts.filter(Boolean).join(" ").trim();
}

export const deepseek: ProviderSpec = {
  name: "deepseek",
  envKeys: ["DEEPSEEK_API_KEY", "DEEPSEEK_SEARCH_API_KEY"],
  defaultBaseUrl: "https://api.deepseek.com",
  capabilities: new Set(["domains", "language", "date", "content", "summary"]),

  configHint() {
    return (
      "Set DEEPSEEK_API_KEY. POST /v1/tools/search takes count (1-50), " +
      "need_content, and query operators for site/lang/date filters."
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = {
      query: queryWithOperators(req),
      count: Math.max(1, Math.min(req.maxResults, 50)),
      need_content: Boolean(req.includeContent),
    };
    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1/tools/search`,
      headers: {
        Authorization: `Bearer ${ctx.apiKey ?? ""}`,
        "Content-Type": "application/json",
      },
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
        text: item.content || undefined,
        summary: item.summary,
        score: item.rerank_score,
        publishedDate: item.date,
        source: item.site_name,
        raw: item,
      }),
    );
    return finalize(deepseek, req, results, data, {
      totalResults: results.length,
      elapsedMs,
    });
  },
};
