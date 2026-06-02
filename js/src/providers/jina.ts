import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const jina: ProviderSpec = {
  name: "jina",
  envKeys: ["JINA_API_KEY"],
  defaultBaseUrl: "https://s.jina.ai",
  capabilities: new Set(["content"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${ctx.apiKey ?? ""}`,
      Accept: "application/json",
    };
    if (!req.includeContent) headers["X-Respond-With"] = "no-content";
    const params: Record<string, string | number | boolean | undefined> = { q: req.query };
    for (const [k, v] of Object.entries(req.extra)) params[k] = v as string;
    return { method: "GET", url: `${ctx.baseUrl}/`, headers, params };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    let items = data.data ?? [];
    if (!Array.isArray(items)) items = [items];
    const results = items.map((item: any) => {
      const content: string | undefined = item.content;
      return result({
        title: item.title,
        url: item.url,
        snippet: item.description ?? (content ? content.slice(0, 300) : undefined),
        text: req.includeContent ? content : undefined,
        publishedDate: item.date ?? item.publishedTime,
        raw: item,
      });
    });
    return finalize(jina, req, results, data, { elapsedMs });
  },
};
