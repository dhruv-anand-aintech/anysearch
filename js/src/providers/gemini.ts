import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const DEFAULT_MODEL = "gemini-2.5-flash";

function modelName(ctx: ProviderContext, extra: Record<string, unknown>): string {
  const raw = (extra.model as string) ?? (ctx.config?.model as string) ?? DEFAULT_MODEL;
  const m = String(raw).trim();
  return m || DEFAULT_MODEL;
}

function textFromCandidate(candidate: Record<string, unknown>): string | undefined {
  const content = (candidate.content as Record<string, unknown>) ?? {};
  const parts = (content.parts as unknown[]) ?? [];
  const texts = parts
    .filter((p): p is Record<string, unknown> => !!p && typeof p === "object")
    .map((p) => p.text as string | undefined)
    .filter(Boolean);
  return texts.length ? texts.join("\n") : undefined;
}

function groundingChunks(
  meta: Record<string, unknown>
): { uri?: string; title?: string }[] {
  const raw = (meta.groundingChunks ?? meta.grounding_chunks ?? []) as unknown[];
  const out: { uri?: string; title?: string }[] = [];
  const seen = new Set<string>();
  for (const chunk of raw) {
    if (!chunk || typeof chunk !== "object") continue;
    const web = ((chunk as Record<string, unknown>).web as Record<string, unknown>) ?? {};
    const uri = web.uri as string | undefined;
    const title = web.title as string | undefined;
    const key = uri ?? title ?? "";
    if (key && seen.has(key)) continue;
    if (key) seen.add(key);
    out.push({ uri, title });
  }
  return out;
}

export const gemini: ProviderSpec = {
  name: "gemini",
  aliases: ["google_gemini", "gemini_api"],
  envKeys: ["GEMINI_API_KEY", "GOOGLE_GEMINI_API_KEY"],
  defaultBaseUrl: "https://generativelanguage.googleapis.com",
  extraPackage: "google-genai",
  capabilities: new Set(["answer"]),

  configHint() {
    return (
      "Set GEMINI_API_KEY. Uses generateContent with the google_search tool " +
      `(default model ${DEFAULT_MODEL}; override via providerConfig.gemini.model).`
    );
  },

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const extra = { ...req.extra };
    const model = modelName(ctx, extra);
    delete extra.model;
    const body: Record<string, unknown> = {
      contents: [{ role: "user", parts: [{ text: req.query }] }],
      tools: [{ google_search: {} }],
    };
    if (extra.generationConfig !== undefined) {
      body.generationConfig = extra.generationConfig;
      delete extra.generationConfig;
    }
    Object.assign(body, extra);
    return {
      method: "POST",
      url: `${ctx.baseUrl}/v1beta/models/${model}:generateContent`,
      headers: {
        "x-goog-api-key": ctx.apiKey ?? "",
        "Content-Type": "application/json",
      },
      json: body,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const data = res.data ?? {};
    const candidates = (data.candidates as unknown[]) ?? [];
    const candidate = (candidates[0] as Record<string, unknown>) ?? {};
    const text = textFromCandidate(candidate);
    const meta =
      (candidate.groundingMetadata as Record<string, unknown>) ??
      (candidate.grounding_metadata as Record<string, unknown>) ??
      {};
    const results = groundingChunks(meta).slice(0, req.maxResults).map((ch) =>
      result({
        title: ch.title,
        url: ch.uri,
        snippet: ch.title,
        raw: ch,
      })
    );
    return finalize(gemini, req, results, data, {
      elapsedMs,
      answer: req.answer ? text : undefined,
      requestId: data.responseId as string | undefined,
    });
  },
};
