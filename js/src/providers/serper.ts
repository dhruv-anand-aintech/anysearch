import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const serper: ProviderSpec = {
  name: "serper",
  envKeys: ["SERPER_API_KEY"],
  defaultBaseUrl: "https://google.serper.dev",
  capabilities: new Set(["country", "language", "news"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = { q: req.query, num: req.maxResults };
    if (req.country) body.gl = req.country.toLowerCase();
    if (req.language) body.hl = req.language;
    Object.assign(body, req.extra);
    const path = req.searchType === "news" ? "/news" : "/search";
    return {
      method: "POST",
      url: `${ctx.baseUrl}${path}`,
      headers: { "X-API-KEY": ctx.apiKey ?? "", "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const items = req.searchType === "news" ? data.news ?? [] : data.organic ?? [];
    const results = items.map((item: any) =>
      result({
        title: item.title,
        url: item.link,
        snippet: item.snippet,
        source: item.source,
        publishedDate: item.date,
        score: item.position,
        raw: item,
      }),
    );
    const box = data.answerBox ?? {};
    const answer = box.answer ?? box.snippet;
    return finalize(serper, req, results, data, { answer, elapsedMs });
  },
};
