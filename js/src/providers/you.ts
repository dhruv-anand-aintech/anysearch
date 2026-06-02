import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

export const you: ProviderSpec = {
  name: "you",
  aliases: ["youcom", "ydc"],
  envKeys: ["YDC_API_KEY", "YOU_API_KEY"],
  defaultBaseUrl: "https://ydc-index.io",
  capabilities: new Set(["domains", "country", "highlights"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const body: Record<string, unknown> = { query: req.query, count: req.maxResults };
    if (req.includeDomains.length) body.include_domains = req.includeDomains;
    if (req.excludeDomains.length) body.exclude_domains = req.excludeDomains;
    if (req.country) body.country = req.country.toLowerCase();
    if (req.safeSearch) body.safesearch = req.safeSearch;
    Object.assign(body, req.extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1/search`,
      headers: { "X-API-Key": ctx.apiKey ?? "", "Content-Type": "application/json" },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const items = data.results ?? data.hits ?? [];
    const results = items.map((item: any) => {
      const snippets: string[] = item.snippets ?? [];
      const authors: string[] = item.authors ?? [];
      return result({
        title: item.title,
        url: item.url,
        snippet: item.description ?? snippets[0],
        text: snippets.length ? snippets.join("\n\n") : undefined,
        highlights: snippets,
        publishedDate: item.page_age,
        author: authors[0],
        raw: item,
      });
    });
    return finalize(you, req, results, data, { elapsedMs });
  },
};
