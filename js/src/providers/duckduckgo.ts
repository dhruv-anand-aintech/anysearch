import type { HttpResponse } from "../http.js";
import type { SearchRequest, SearchResponse } from "../types.js";
import { finalize, result, type ProviderContext, type ProviderSpec } from "./base.js";

const SAFE: Record<string, string> = { off: "-2", moderate: "-1", strict: "1" };
const RESULT_RE = /<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g;
const SNIPPET_RE = /class="result__snippet"[^>]*>([\s\S]*?)<\/a>/g;
const TAG_RE = /<[^>]+>/g;

function unescapeHtml(s: string): string {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

function clean(text: string): string {
  return unescapeHtml((text || "").replace(TAG_RE, "")).trim();
}

function unwrap(href: string): string {
  let h = href.startsWith("//") ? `https:${href}` : href;
  try {
    const u = new URL(h);
    if (u.hostname.includes("duckduckgo.com") && u.pathname.startsWith("/l/")) {
      const uddg = u.searchParams.get("uddg");
      if (uddg) return decodeURIComponent(uddg);
    }
  } catch {
    /* ignore */
  }
  return h;
}

export const duckduckgo: ProviderSpec = {
  name: "duckduckgo",
  aliases: ["ddg"],
  requiresKey: false,
  defaultBaseUrl: "https://html.duckduckgo.com",
  extraPackage: "duck-duck-scrape",
  capabilities: new Set(["country", "safe_search"]),

  prepare(ctx: ProviderContext, req: SearchRequest) {
    const form: Record<string, string> = { q: req.query };
    if (req.country) form.kl = `${req.country.toLowerCase()}-en`;
    if (req.safeSearch) form.kp = SAFE[req.safeSearch] ?? "-1";
    return {
      method: "POST",
      url: `${ctx.baseUrl}/html/`,
      headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "text/html" },
      form,
    };
  },

  parse(_ctx, res: HttpResponse, req: SearchRequest, elapsedMs: number): SearchResponse {
    const body = res.text;
    const snippets: string[] = [];
    for (const m of body.matchAll(SNIPPET_RE)) snippets.push(clean(m[1]));
    const results = [];
    let idx = 0;
    for (const m of body.matchAll(RESULT_RE)) {
      results.push(
        result({
          title: clean(m[2]),
          url: unwrap(m[1]),
          snippet: idx < snippets.length ? snippets[idx] : undefined,
          score: idx + 1,
          raw: { href: m[1] },
        }),
      );
      idx += 1;
    }
    return finalize(duckduckgo, req, results, { htmlResults: results.length }, { elapsedMs });
  },
};
