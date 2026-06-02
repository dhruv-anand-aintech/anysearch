import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const MODE: Record<string, string> = { fast: "basic", balanced: "basic", deep: "advanced" };

export const parallel: ProviderSpec = {
  name: "parallel",
  envKeys: ["PARALLEL_API_KEY"],
  defaultBaseUrl: "https://api.parallel.ai",
  extraPackage: "parallel-web",
  nativeImport: { module: "parallel-web", exports: ["Parallel", "default"] },
  capabilities: new Set(["domains", "country", "date", "mode", "content", "highlights"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const extra = { ...req.extra };
    const objective = (extra.objective as string) ?? req.query;
    delete extra.objective;
    const body: Record<string, unknown> = {
      search_queries: [req.query],
      objective,
      max_results: req.maxResults,
    };
    if (req.mode) body.mode = MODE[req.mode] ?? "advanced";

    const sourcePolicy: Record<string, unknown> = {};
    if (req.includeDomains.length) sourcePolicy.include_domains = req.includeDomains;
    if (req.excludeDomains.length) sourcePolicy.exclude_domains = req.excludeDomains;
    if (req.startPublishedDate) sourcePolicy.after_date = req.startPublishedDate;
    const advanced: Record<string, unknown> = {};
    if (Object.keys(sourcePolicy).length) advanced.source_policy = sourcePolicy;
    if (req.country) advanced.location = req.country.toLowerCase();
    if (Object.keys(advanced).length) body.advanced_settings = advanced;

    Object.assign(body, extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1/search`,
      headers: { "x-api-key": ctx.apiKey ?? "", "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = (data.results ?? []).map((item: any) => {
      const excerpts: string[] = Array.isArray(item.excerpts)
        ? item.excerpts
        : item.excerpts
          ? [item.excerpts]
          : [];
      return result({
        title: item.title,
        url: item.url,
        snippet: excerpts[0],
        text: excerpts.filter(Boolean).join("\n\n") || undefined,
        highlights: excerpts,
        raw: item,
      });
    });
    return finalize(parallel, req, results, data, { requestId: data.search_id, elapsedMs });
  },
};
