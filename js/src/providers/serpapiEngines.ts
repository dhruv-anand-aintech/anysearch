/** SerpApi multi-engine helpers — https://serpapi.com/search-api */

export const SERPAPI_WEB_ENGINES = [
  "google",
  "bing",
  "baidu",
  "yandex",
  "duckduckgo",
  "yahoo",
  "ebay",
  "naver",
  "amazon",
  "apple_app_store",
  "walmart",
  "yelp",
  "youtube",
] as const;

export const SERPAPI_NEWS_ENGINES: Record<string, string> = {
  google: "google_news",
  bing: "bing_news",
  baidu: "baidu_news",
  duckduckgo: "duckduckgo_news",
  yahoo: "yahoo",
};

const ENGINE_ALIASES: Record<string, string> = {
  ddg: "duckduckgo",
  goog: "google",
};

export function normalizeEngine(name: string): string {
  const key = name.trim().toLowerCase().replace(/-/g, "_");
  return ENGINE_ALIASES[key] ?? key;
}

export function resolveSerpapiEngine(opts: {
  engine?: string;
  defaultEngine: string;
  searchType: string;
  extra: Record<string, unknown>;
}): string {
  const extra = { ...opts.extra };
  const raw = opts.engine ?? (extra.engine as string | undefined);
  if (raw !== undefined) delete extra.engine;
  const base = normalizeEngine(String(raw ?? opts.defaultEngine));
  if (opts.searchType === "news") {
    if (base in SERPAPI_NEWS_ENGINES) return SERPAPI_NEWS_ENGINES[base]!;
    if (base.endsWith("_news")) return base;
  }
  return base;
}

export function applySerpapiLocale(
  params: Record<string, string | number | boolean | undefined>,
  engine: string,
  country?: string,
  language?: string,
): void {
  if (!country && !language) return;
  const root = engine.replace(/_news$/, "");
  if (root === "google") {
    if (country) params.gl = country.toLowerCase();
    if (language) params.hl = language;
  } else if (root === "bing") {
    if (country) params.cc = country.toLowerCase();
    if (language) params.setlang = language.toLowerCase();
  } else if (root === "duckduckgo") {
    const cc = (country ?? "us").toLowerCase();
    const lang = (language ?? "en").toLowerCase();
    params.kl = `${cc}-${lang}`;
  }
}

export function applySerpapiSafeSearch(
  params: Record<string, string | number | boolean | undefined>,
  engine: string,
  safeSearch?: string,
): void {
  if (!safeSearch) return;
  const root = engine.replace(/_news$/, "");
  if (root === "google") {
    params.safe = safeSearch === "off" ? "off" : "active";
  } else if (root === "bing" || root === "duckduckgo" || root === "yahoo") {
    params.safe_search = safeSearch;
  }
}

export function extractSerpapiResults(data: Record<string, unknown>, searchType: string): unknown[] {
  const keys =
    searchType === "news"
      ? (["news_results", "organic_results"] as const)
      : (["organic_results", "organic", "results"] as const);
  for (const key of keys) {
    const items = data[key];
    if (Array.isArray(items) && items.length) return items;
  }
  return [];
}

export function extractSerpapiAnswer(data: Record<string, unknown>): string | undefined {
  const box = data.answer_box;
  if (box && typeof box === "object") {
    const b = box as Record<string, unknown>;
    const answer = b.answer ?? b.snippet ?? b.result;
    if (answer != null) return String(answer);
  }
  const featured = data.answer;
  if (typeof featured === "string") return featured;
  if (featured && typeof featured === "object") {
    const f = featured as Record<string, unknown>;
    return (f.answer ?? f.snippet) as string | undefined;
  }
  return undefined;
}
