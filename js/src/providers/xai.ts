import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const DEFAULT_MODEL = "grok-4.7";

function answer(data: any): string | undefined {
  const texts: string[] = [];
  for (const item of data.output ?? []) {
    if (item?.type !== "message") continue;
    for (const content of item.content ?? []) {
      if (content?.type === "output_text" && content.text) texts.push(String(content.text));
    }
  }
  if (texts.length) return texts.join("\n");
  return data.output_text ? String(data.output_text) : undefined;
}

function citations(data: any): { url?: string; title?: string; snippet?: string }[] {
  const out: { url?: string; title?: string; snippet?: string }[] = [];
  const seen = new Set<string>();
  for (const item of data.output ?? []) {
    if (item?.type !== "message") continue;
    for (const content of item.content ?? []) {
      const body = String(content?.text ?? "");
      for (const annotation of content?.annotations ?? []) {
        const url = annotation?.url;
        if (!url || seen.has(url)) continue;
        seen.add(url);
        let snippet: string | undefined;
        if (Number.isInteger(annotation.start_index) && Number.isInteger(annotation.end_index) && body) {
          snippet = body
            .slice(Math.max(0, annotation.start_index - 100), Math.min(body.length, annotation.end_index + 100))
            .trim();
        }
        out.push({ url, title: annotation.title, snippet });
      }
    }
  }
  for (const citation of data.citations ?? []) {
    const url = typeof citation === "string" ? citation : citation?.url;
    if (!url || seen.has(url)) continue;
    seen.add(url);
    out.push({ url, title: typeof citation === "string" ? undefined : citation.title });
  }
  return out;
}

export const xai: ProviderSpec = {
  name: "xai",
  aliases: ["grok", "x_ai"],
  envKeys: ["XAI_API_KEY"],
  defaultBaseUrl: "https://api.x.ai",
  capabilities: new Set(["domains", "answer"]),

  configHint() {
    return (
      "Set XAI_API_KEY. Uses POST /v1/responses with the hosted web_search tool; " +
      `default model ${DEFAULT_MODEL} (override via providerConfig.xai.model).`
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const model = String((req.extra.model as string) ?? (ctx.config.model as string) ?? DEFAULT_MODEL);
    const tool: Record<string, unknown> = { type: "web_search" };
    const filters: Record<string, unknown> = {};
    if (req.includeDomains.length) filters.allowed_domains = req.includeDomains;
    if (req.excludeDomains.length) filters.excluded_domains = req.excludeDomains;
    if (Object.keys(filters).length) tool.filters = filters;
    const body: Record<string, unknown> = {
      model,
      input: req.query,
      tools: [tool],
    };
    for (const [key, value] of Object.entries(req.extra)) {
      if (key !== "model") body[key] = value;
    }
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1/responses`,
      headers: {
        Authorization: `Bearer ${ctx.apiKey ?? ""}`,
        "Content-Type": "application/json",
      },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const results = citations(data).slice(0, req.maxResults).map((citation) =>
      result({
        title: citation.title,
        url: citation.url,
        snippet: citation.snippet,
        raw: citation,
      }),
    );
    return finalize(xai, req, results, data, {
      answer: answer(data),
      requestId: data.id,
      elapsedMs,
    });
  },
};
