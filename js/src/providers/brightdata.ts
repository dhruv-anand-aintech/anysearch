import type { HttpResponse } from "../http.js";
import type { Env, SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const ZONE_ENV = ["BRIGHTDATA_ZONE", "BRIGHT_DATA_ZONE", "BRIGHTDATA_SERP_ZONE"];

function zoneFromEnv(env: Env): string | undefined {
  for (const key of ZONE_ENV) if (env[key]) return env[key];
  return undefined;
}

function dateUs(value?: string): string | undefined {
  if (!value) return undefined;
  const [year, month, day] = value.slice(0, 10).split("-");
  if (!year || !month || !day) return value.slice(0, 10);
  return `${Number(month)}/${Number(day)}/${year}`;
}

function tbs(req: SearchRequest): string | undefined {
  if (!req.startPublishedDate && !req.endPublishedDate) return undefined;
  const pieces = ["cdr:1"];
  if (req.startPublishedDate) pieces.push(`cd_min:${dateUs(req.startPublishedDate)}`);
  if (req.endPublishedDate) pieces.push(`cd_max:${dateUs(req.endPublishedDate)}`);
  return pieces.join(",");
}

function query(req: SearchRequest): string {
  const parts = [req.query];
  for (const domain of req.includeDomains) parts.push(`site:${domain}`);
  for (const domain of req.excludeDomains) parts.push(`-site:${domain}`);
  return parts.filter(Boolean).join(" ").trim();
}

function targetUrl(req: SearchRequest): string {
  const engine = (req.engine ?? "google").trim().toLowerCase();
  const params = new URLSearchParams();
  params.set("q", query(req));
  if (engine === "bing") {
    params.set("count", String(Math.max(1, Math.min(req.maxResults, 50))));
    if (req.language) params.set("setlang", req.language.toLowerCase());
    if (req.country) params.set("cc", req.country.toUpperCase());
    if (req.safeSearch) {
      params.set("safeSearch", { off: "Off", moderate: "Moderate", strict: "Strict" }[req.safeSearch]);
    }
    if (req.searchType === "news") params.set("qft", 'sortbydate="1"');
    return `https://www.bing.com/search?${params.toString()}`;
  }
  params.set("num", String(Math.max(1, Math.min(req.maxResults, 100))));
  if (req.language) params.set("hl", req.language.toLowerCase());
  if (req.country) params.set("gl", req.country.toLowerCase());
  if (req.safeSearch) params.set("safe", req.safeSearch === "off" ? "off" : "active");
  if (req.searchType === "news") params.set("tbm", "nws");
  const range = tbs(req);
  if (range) params.set("tbs", range);
  return `https://www.google.com/search?${params.toString()}`;
}

export const brightdata: ProviderSpec = {
  name: "brightdata",
  aliases: ["bright_data"],
  envKeys: ["BRIGHTDATA_API_KEY", "BRIGHT_DATA_API_KEY", "BRIGHTDATA_ZONE"],
  defaultBaseUrl: "https://api.brightdata.com",
  capabilities: new Set(["domains", "country", "language", "date", "safe_search", "news", "engine"]),

  isConfigured(env: Env): boolean {
    const hasKey = Boolean(env.BRIGHTDATA_API_KEY || env.BRIGHT_DATA_API_KEY);
    return hasKey && Boolean(zoneFromEnv(env));
  },
  configHint() {
    return (
      "Set BRIGHTDATA_API_KEY and BRIGHTDATA_ZONE (a SERP API zone). " +
      'The adapter targets Google by default and Bing with engine="bing".'
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = {
      zone: (ctx.config.zone as string) ?? zoneFromEnv(ctx.env),
      url: targetUrl(req),
      format: "raw",
      data_format: "parsed",
    };
    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/request`,
      headers: {
        Authorization: `Bearer ${ctx.apiKey ?? ""}`,
        "Content-Type": "application/json",
      },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    let data = res.data;
    if (data && typeof data === "object" && typeof data.body === "string") {
      try {
        data = JSON.parse(data.body);
      } catch {
        /* keep the wrapper payload */
      }
    }
    const organic = data && typeof data === "object" ? data.organic ?? data.results ?? [] : [];
    const results = organic.map((item: any) =>
      result({
        title: item.title,
        url: item.link ?? item.url,
        snippet: item.description ?? item.snippet,
        publishedDate: item.date,
        score: item.global_rank ?? item.rank,
        source: item.source,
        raw: item,
      }),
    );
    return finalize(brightdata, req, results, data, {
      totalResults: results.length,
      elapsedMs,
    });
  },
};
