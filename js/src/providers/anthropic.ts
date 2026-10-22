import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const DEFAULT_MODEL = "claude-sonnet-4-5";
const DEFAULT_TOOL = "web_search_20250305";
const API_VERSION = "2023-06-01";

function text(data: any): string | undefined {
  const texts = (data.content ?? [])
    .filter((block: any) => block?.type === "text" && block.text)
    .map((block: any) => String(block.text));
  return texts.length ? texts.join("\n") : undefined;
}

function citations(data: any): { url?: string; title?: string; snippet?: string }[] {
  const out: { url?: string; title?: string; snippet?: string }[] = [];
  const seen = new Set<string>();
  for (const block of data.content ?? []) {
    if (block?.type === "web_search_tool_result" && Array.isArray(block.content)) {
      for (const item of block.content) {
        if (item?.type !== "web_search_result" || !item.url || seen.has(item.url)) continue;
        seen.add(item.url);
        out.push({ url: item.url, title: item.title, snippet: item.page_age });
      }
    }
    if (block?.type === "text") {
      const body = String(block.text ?? "");
      for (const citation of block.citations ?? []) {
        const url = citation?.url;
        if (!url || seen.has(url)) continue;
        seen.add(url);
        let snippet = citation.cited_text;
        if (!snippet && Number.isInteger(citation.start_char_index) && Number.isInteger(citation.end_char_index)) {
          snippet = body
            .slice(Math.max(0, citation.start_char_index - 100), Math.min(body.length, citation.end_char_index + 100))
            .trim();
        }
        out.push({ url, title: citation.title, snippet });
      }
    }
  }
  return out;
}

export const anthropic: ProviderSpec = {
  name: "anthropic",
  aliases: ["claude"],
  envKeys: ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
  defaultBaseUrl: "https://api.anthropic.com",
  capabilities: new Set(["domains", "answer"]),

  configHint() {
    return (
      "Set ANTHROPIC_API_KEY. Uses POST /v1/messages with the server-side " +
      `${DEFAULT_TOOL} web search tool; default model ${DEFAULT_MODEL}.`
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const model = String((req.extra.model as string) ?? (ctx.config.model as string) ?? DEFAULT_MODEL);
    const tool: Record<string, unknown> = {
      type: String((ctx.config.toolType as string) ?? DEFAULT_TOOL),
      name: "web_search",
    };
    if (req.includeDomains.length) tool.allowed_domains = req.includeDomains;
    if (req.excludeDomains.length) tool.blocked_domains = req.excludeDomains;
    const body: Record<string, unknown> = {
      model,
      max_tokens: Number(ctx.config.maxTokens ?? 4096),
      messages: [{ role: "user", content: req.query }],
      tools: [tool],
    };
    for (const [key, value] of Object.entries(req.extra)) {
      if (key !== "model") body[key] = value;
    }
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1/messages`,
      headers: {
        "x-api-key": ctx.apiKey ?? "",
        "anthropic-version": API_VERSION,
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
    return finalize(anthropic, req, results, data, {
      answer: text(data),
      requestId: data.id,
      elapsedMs,
    });
  },
};
