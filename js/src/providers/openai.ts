import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const DEFAULT_MODEL = "gpt-5.5";
const EFFORT: Record<string, string> = { fast: "low", balanced: "medium", deep: "high" };
const CONTEXT: Record<string, string> = { fast: "low", balanced: "medium", deep: "high" };

function queryWithExcludes(req: SearchRequest): string {
  const parts = [req.query];
  for (const domain of req.excludeDomains) parts.push(`-site:${domain}`);
  return parts.filter(Boolean).join(" ").trim();
}

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
      const text = String(content?.text ?? "");
      for (const annotation of content?.annotations ?? []) {
        const url = annotation?.url;
        if (!url || seen.has(url)) continue;
        seen.add(url);
        const start = annotation.start_index;
        const end = annotation.end_index;
        const snippet =
          Number.isInteger(start) && Number.isInteger(end) && text
            ? text.slice(Math.max(0, start - 100), Math.min(text.length, end + 100)).trim()
            : undefined;
        out.push({ url, title: annotation.title, snippet });
      }
    }
  }
  return out;
}

export const openai: ProviderSpec = {
  name: "openai",
  envKeys: ["OPENAI_API_KEY"],
  defaultBaseUrl: "https://api.openai.com",
  capabilities: new Set(["domains", "mode", "answer"]),

  configHint() {
    return (
      "Set OPENAI_API_KEY. Uses POST /v1/responses with the hosted web_search tool; " +
      `default model ${DEFAULT_MODEL} (override via providerConfig.openai.model).`
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const model = String((req.extra.model as string) ?? (ctx.config.model as string) ?? DEFAULT_MODEL);
    const tool: Record<string, unknown> = { type: "web_search" };
    if (req.includeDomains.length) tool.filters = { allowed_domains: req.includeDomains };
    if (req.mode) tool.search_context_size = CONTEXT[req.mode];
    const body: Record<string, unknown> = {
      model,
      input: queryWithExcludes(req),
      tools: [tool],
    };
    if (req.mode) body.reasoning = { effort: EFFORT[req.mode] };
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
    return finalize(openai, req, results, data, {
      answer: answer(data),
      totalResults: results.length,
      requestId: data.id,
      elapsedMs,
    });
  },
};
