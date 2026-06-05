import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const MODE: Record<string, string> = { fast: "light", balanced: "ai", deep: "deep" };

function pickEndpoint(req: SearchRequest): string {
  if (typeof req.extra.endpoint === "string") return req.extra.endpoint;
  if (req.includeContent) return "/api/v2/search/content";
  if (req.mode === "fast") return "/api/v2/search/flash";
  return "/api/v2/keiro";
}

function asArray(value: unknown): any[] {
  return Array.isArray(value) ? value : [];
}

export const keiro: ProviderSpec = {
  name: "keiro",
  aliases: ["keirolabs", "keiro_labs"],
  envKeys: ["KEIRO_API_KEY", "KEIROLABS_API_KEY"],
  baseUrlEnv: ["KEIRO_BASE_URL", "KEIROLABS_BASE_URL"],
  defaultBaseUrl: "https://kierolabs.space",
  extraPackage: "@keirolabs/sdk",
  nativeImport: { module: "@keirolabs/sdk", exports: ["KeiroLabs", "default"] },
  capabilities: new Set(["mode", "content"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const endpoint = pickEndpoint(req);
    const extra = { ...req.extra };
    delete extra.endpoint;
    const body: Record<string, unknown> = {
      query: req.query,
      maxResults: req.maxResults,
      mode: MODE[req.mode ?? ""] ?? "ai",
    };
    Object.assign(body, extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`,
      headers: { Authorization: `Bearer ${ctx.apiKey ?? ""}`, "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx: ProviderContext, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const sources = asArray(data.results ?? data.sources);
    const results = sources.map((item: any) => {
      const text = item.full_text ?? item.fullText ?? item.text ?? item.markdown;
      const snippet = item.snippet ?? item.description ?? text;
      return result({
        title: item.title,
        url: item.url,
        snippet,
        text,
        score: item.score,
        publishedDate: item.published_date ?? item.publishedDate,
        raw: item,
      });
    });
    return finalize(keiro, req, results, data, {
      answer: data.answer ?? data.summary,
      totalResults: data.total_results ?? data.totalResults,
      requestId: data.request_id ?? data.requestId,
      elapsedMs: data.latency_ms ?? data.latencyMs ?? elapsedMs,
    });
  },
};
