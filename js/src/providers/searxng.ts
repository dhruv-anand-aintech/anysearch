import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const SAFE: Record<string, number> = { off: 0, moderate: 1, strict: 2 };

export const searxng: ProviderSpec = {
  name: "searxng",
  aliases: ["searx"],
  envKeys: ["SEARXNG_API_KEY"],
  baseUrlEnv: ["SEARXNG_BASE_URL", "SEARXNG_URL"],
  requiresKey: false,
  requiresBaseUrl: true,
  capabilities: new Set(["language", "safe_search", "answer"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const params: Record<string, string | number | boolean | undefined> = {
      q: req.query,
      format: "json",
    };
    if (req.language) params.language = req.language;
    if (req.safeSearch !== undefined) params.safesearch = SAFE[req.safeSearch] ?? 1;
    if (req.searchType === "news") params.categories = "news";
    for (const [k, v] of Object.entries(req.extra)) params[k] = v as string;
    const headers: Record<string, string> = { Accept: "application/json" };
    if (ctx.apiKey) headers.Authorization = `Bearer ${ctx.apiKey}`;
    return { method: "GET", url: `${ctx.baseUrl}/search`, headers, params };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.results ?? []).map((item: any) =>
      result({
        title: item.title,
        url: item.url,
        snippet: item.content,
        score: item.score,
        publishedDate: item.publishedDate,
        source: item.engine,
        raw: item,
      }),
    );
    const answers: string[] = data.answers ?? [];
    const answer = answers.filter((a) => typeof a === "string").join("\n") || undefined;
    return finalize(searxng, req, results, data, {
      answer,
      totalResults: data.number_of_results,
      elapsedMs,
    });
  },
};
