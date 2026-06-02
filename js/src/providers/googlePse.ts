import type { HttpResponse } from "../http.js";
import type { Env, SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const KEY_ENV = ["GOOGLE_PSE_API_KEY", "GOOGLE_CSE_API_KEY", "GOOGLE_API_KEY"];
const CX_ENV = ["GOOGLE_PSE_CX", "GOOGLE_CSE_CX", "GOOGLE_PSE_ENGINE_ID"];

function cxFromEnv(env: Env): string | undefined {
  for (const k of CX_ENV) if (env[k]) return env[k];
  return undefined;
}

export const googlePse: ProviderSpec = {
  name: "google_pse",
  aliases: ["google", "google_cse"],
  envKeys: KEY_ENV,
  defaultBaseUrl: "https://www.googleapis.com",
  capabilities: new Set(["country", "language", "safe_search", "domains"]),

  isConfigured(env: Env): boolean {
    const hasKey = KEY_ENV.some((k) => env[k]);
    return Boolean(hasKey && cxFromEnv(env));
  },
  configHint(): string {
    return "Set GOOGLE_PSE_API_KEY and GOOGLE_PSE_CX (search engine id).";
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const cx = (ctx.config.cx as string) ?? cxFromEnv(ctx.env);
    const params: Record<string, string | number | boolean | undefined> = {
      key: ctx.apiKey,
      cx,
      q: req.query,
      num: Math.min(req.maxResults, 10),
    };
    if (req.country) params.gl = req.country.toLowerCase();
    if (req.language) {
      params.hl = req.language;
      params.lr = `lang_${req.language.slice(0, 2)}`;
    }
    if (req.safeSearch) params.safe = req.safeSearch === "off" ? "off" : "active";
    if (req.startPublishedDate && req.endPublishedDate) {
      const s = req.startPublishedDate.slice(0, 10).replace(/-/g, "");
      const e = req.endPublishedDate.slice(0, 10).replace(/-/g, "");
      params.sort = `date:r:${s}:${e}`;
    }
    if (req.includeDomains.length) {
      params.siteSearch = req.includeDomains[0];
      params.siteSearchFilter = "i";
    } else if (req.excludeDomains.length) {
      params.siteSearch = req.excludeDomains[0];
      params.siteSearchFilter = "e";
    }
    for (const [k, v] of Object.entries(req.extra)) params[k] = v as string;
    return {
      method: "GET",
      url: `${ctx.baseUrl}/customsearch/v1`,
      headers: { Accept: "application/json" },
      params,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.items ?? []).map((item: any) =>
      result({
        title: item.title,
        url: item.link,
        snippet: item.snippet,
        source: item.displayLink,
        raw: item,
      }),
    );
    const total = Number.parseInt(data.searchInformation?.totalResults ?? "", 10);
    return finalize(googlePse, req, results, data, {
      totalResults: Number.isNaN(total) ? undefined : total,
      elapsedMs,
    });
  },
};
