import type { HttpResponse } from "../http.js";
import type { Env, SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const PASSWORD_ENV = ["DATAFORSEO_PASSWORD", "DATAFORSEO_API_PASSWORD"];

function passwordFromEnv(env: Env): string | undefined {
  for (const key of PASSWORD_ENV) if (env[key]) return env[key];
  return undefined;
}

function query(req: SearchRequest): string {
  const parts = [req.query];
  for (const domain of req.includeDomains) parts.push(`site:${domain}`);
  for (const domain of req.excludeDomains) parts.push(`-site:${domain}`);
  return parts.filter(Boolean).join(" ").trim();
}

function basic(login: string, password: string): string {
  return `Basic ${btoa(`${login}:${password}`)}`;
}

export const dataforseo: ProviderSpec = {
  name: "dataforseo",
  aliases: ["data_for_seo"],
  envKeys: ["DATAFORSEO_LOGIN", "DATAFORSEO_API_LOGIN", "DATAFORSEO_PASSWORD"],
  defaultBaseUrl: "https://api.dataforseo.com",
  capabilities: new Set(["domains", "language"]),

  isConfigured(env: Env): boolean {
    const hasLogin = Boolean(env.DATAFORSEO_LOGIN || env.DATAFORSEO_API_LOGIN);
    return hasLogin && Boolean(passwordFromEnv(env));
  },
  configHint() {
    return (
      "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD (HTTP Basic auth). " +
      "Optional DATAFORSEO_LOCATION_CODE defaults to 2840 (United States)."
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const password =
      (ctx.config.password as string) ?? passwordFromEnv(ctx.env) ?? "";
    const locationRaw =
      (ctx.config.locationCode as number | string | undefined) ??
      ctx.env.DATAFORSEO_LOCATION_CODE ??
      2840;
    const locationCode = Number(locationRaw) || 2840;
    const task: Record<string, unknown> = {
      keyword: query(req),
      location_code: locationCode,
      language_code: (req.language ?? "en").toLowerCase(),
      depth: Math.max(1, Math.min(req.maxResults, 200)),
    };
    Object.assign(task, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v3/serp/google/organic/live/advanced`,
      headers: {
        Authorization: basic(ctx.apiKey ?? "", password),
        "Content-Type": "application/json",
      },
      json: [task],
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const task = (data.tasks ?? [])[0] ?? {};
    const taskResult = (task.result ?? [])[0] ?? {};
    const results = (taskResult.items ?? [])
      .filter((item: any) => item?.type === "organic")
      .map((item: any) =>
        result({
          title: item.title,
          url: item.url,
          snippet: item.description,
          publishedDate: item.timestamp,
          score: item.rank_absolute ?? item.rank_group,
          raw: item,
        }),
      );
    return finalize(dataforseo, req, results, data, {
      totalResults: taskResult.se_results_count,
      elapsedMs,
    });
  },
};
