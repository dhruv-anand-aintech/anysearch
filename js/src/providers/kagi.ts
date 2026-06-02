import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const kagi: ProviderSpec = {
  name: "kagi",
  envKeys: ["KAGI_API_KEY"],
  defaultBaseUrl: "https://kagi.com",
  capabilities: new Set([]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const params: Record<string, string | number | boolean | undefined> = {
      q: req.query,
      limit: req.maxResults,
    };
    for (const [k, v] of Object.entries(req.extra)) params[k] = v as string;
    return {
      method: "GET",
      url: `${ctx.baseUrl}/api/v0/search`,
      headers: { Authorization: `Bot ${ctx.apiKey ?? ""}`, Accept: "application/json" },
      params,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.data ?? [])
      .filter((item: any) => item.t === 0)
      .map((item: any) =>
        result({
          title: item.title,
          url: item.url,
          snippet: item.snippet,
          publishedDate: item.published,
          raw: item,
        }),
      );
    return finalize(kagi, req, results, data, { requestId: data.meta?.id, elapsedMs });
  },
};
