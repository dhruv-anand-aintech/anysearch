/** Scan a codebase for direct search-API usage and map it onto anysearch. */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join, relative } from "node:path";

interface Signature {
  pattern: RegExp;
  kind: string;
}

const SIGNATURES: Record<string, Signature[]> = {
  exa: [
    { pattern: /\bfrom\s+exa_py\b|\bimport\s+exa_py\b|require\(['"]exa-js|from\s+['"]exa-js/, kind: "sdk" },
    { pattern: /\bExa\s*\(|new\s+Exa\b/, kind: "client" },
    { pattern: /https?:\/\/api\.exa\.ai/, kind: "rest" },
  ],
  tavily: [
    { pattern: /\bfrom\s+tavily\b|require\(['"]@tavily|from\s+['"]@tavily/, kind: "sdk" },
    { pattern: /\bTavilyClient\s*\(|\btavily\.search\b/, kind: "client" },
    { pattern: /https?:\/\/api\.tavily\.com/, kind: "rest" },
  ],
  parallel: [
    { pattern: /\bfrom\s+parallel\s+import|require\(['"]parallel-web|from\s+['"]parallel-web/, kind: "sdk" },
    { pattern: /\bParallel\s*\(|new\s+Parallel\b/, kind: "client" },
    { pattern: /https?:\/\/api\.parallel\.ai/, kind: "rest" },
  ],
  perplexity: [
    { pattern: /\bfrom\s+perplexity\s+import|@perplexity-ai/, kind: "sdk" },
    { pattern: /https?:\/\/api\.perplexity\.ai\/search/, kind: "rest" },
  ],
  brave: [
    { pattern: /https?:\/\/api\.search\.brave\.com/, kind: "rest" },
    { pattern: /X-Subscription-Token/, kind: "header" },
  ],
  serpapi: [
    { pattern: /\bfrom\s+serpapi\b|require\(['"]serpapi|from\s+['"]serpapi/, kind: "sdk" },
    { pattern: /\bGoogleSearch\s*\(|getJson\s*\(/, kind: "client" },
    { pattern: /https?:\/\/serpapi\.com\/search/, kind: "rest" },
  ],
  serper: [{ pattern: /https?:\/\/google\.serper\.dev/, kind: "rest" }],
  you: [
    { pattern: /https?:\/\/(api\.)?ydc-index\.io/, kind: "rest" },
    { pattern: /\bYDC_API_KEY\b/, kind: "env" },
  ],
  jina: [{ pattern: /https?:\/\/s\.jina\.ai/, kind: "rest" }],
  kagi: [
    { pattern: /https?:\/\/kagi\.com\/api/, kind: "rest" },
    { pattern: /Authorization:\s*Bot\b/, kind: "header" },
  ],
  linkup: [
    { pattern: /\bfrom\s+linkup\b|require\(['"]linkup|from\s+['"]linkup/, kind: "sdk" },
    { pattern: /\bLinkupClient\s*\(/, kind: "client" },
    { pattern: /https?:\/\/api\.linkup\.so/, kind: "rest" },
  ],
  firecrawl: [
    { pattern: /\bfrom\s+firecrawl\b|@mendable\/firecrawl/, kind: "sdk" },
    { pattern: /\bFirecrawl(App)?\s*\(|new\s+Firecrawl\b/, kind: "client" },
    { pattern: /https?:\/\/api\.firecrawl\.dev/, kind: "rest" },
  ],
  searchapi: [{ pattern: /https?:\/\/(www\.)?searchapi\.io/, kind: "rest" }],
  google_pse: [{ pattern: /https?:\/\/www\.googleapis\.com\/customsearch|customsearch\/v1/, kind: "rest" }],
  searxng: [{ pattern: /\bSEARXNG_BASE_URL\b|\bsearxng\b/i, kind: "config" }],
  duckduckgo: [
    { pattern: /\bfrom\s+ddgs\b|\bfrom\s+duckduckgo_search\b|duck-duck-scrape/, kind: "sdk" },
    { pattern: /\bDDGS\s*\(/, kind: "client" },
    { pattern: /https?:\/\/(html\.|lite\.)?duckduckgo\.com/, kind: "rest" },
  ],
};

const CODE_EXTENSIONS = new Set([".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".rb", ".go", ".java"]);
const SKIP_DIRS = new Set([
  ".git", "node_modules", ".venv", "venv", "env", "dist", "build", "__pycache__",
  ".next", ".turbo", ".cache", "vendor", "target", ".mypy_cache", ".ruff_cache",
]);

export interface Finding {
  file: string;
  line: number;
  provider: string;
  kind: string;
  code: string;
  suggestion: string;
}

export interface MigrationReport {
  root: string;
  filesScanned: number;
  filesWithMatches: number;
  totalFindings: number;
  providersDetected: string[];
  countsByProvider: Record<string, number>;
  findings: Finding[];
  nextSteps: string[];
}

function languageFor(path: string): "python" | "javascript" | "other" {
  const ext = extname(path).toLowerCase();
  if (ext === ".py") return "python";
  if ([".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"].includes(ext)) return "javascript";
  return "other";
}

function suggestion(provider: string, language: string): string {
  return language === "python"
    ? `anysearch.search(query, provider='${provider}', max_results=10)  # unified replacement`
    : `await search(query, { provider: '${provider}', maxResults: 10 })  // unified replacement`;
}

function* walk(dir: string): Generator<string> {
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch {
    return;
  }
  for (const entry of entries) {
    if (SKIP_DIRS.has(entry) || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) {
      yield* walk(full);
    } else if (CODE_EXTENSIONS.has(extname(full).toLowerCase())) {
      yield full;
    }
  }
}

export function scanCodebase(
  root = ".",
  providers?: string[],
  maxFiles = 2000,
  maxFindings = 1000,
): MigrationReport {
  const selected = new Set(providers && providers.length ? providers : Object.keys(SIGNATURES));
  const findings: Finding[] = [];
  const counts: Record<string, number> = {};
  let filesScanned = 0;
  let filesWithMatches = 0;

  let isFile = false;
  try {
    isFile = statSync(root).isFile();
  } catch {
    isFile = false;
  }
  const walkRoot = isFile ? "." : root;
  const files = isFile ? [root] : walk(root);

  for (const file of files) {
    if (filesScanned >= maxFiles || findings.length >= maxFindings) break;
    let content: string;
    try {
      content = readFileSync(file, "utf8");
    } catch {
      continue;
    }
    filesScanned += 1;
    const language = languageFor(file);
    const lines = content.split(/\r?\n/);
    let fileHit = false;
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      for (const provider of Object.keys(SIGNATURES)) {
        if (!selected.has(provider)) continue;
        for (const sig of SIGNATURES[provider]) {
          if (sig.pattern.test(line)) {
            findings.push({
              file: isFile ? file : relative(walkRoot, file),
              line: i + 1,
              provider,
              kind: sig.kind,
              code: line.trim().slice(0, 200),
              suggestion: suggestion(provider, language),
            });
            counts[provider] = (counts[provider] ?? 0) + 1;
            fileHit = true;
            break;
          }
        }
      }
      if (findings.length >= maxFindings) break;
    }
    if (fileHit) filesWithMatches += 1;
  }

  return {
    root,
    filesScanned,
    filesWithMatches,
    totalFindings: findings.length,
    providersDetected: Object.keys(counts).sort(),
    countsByProvider: counts,
    findings,
    nextSteps: [
      "Install anysearch: npm install github:dhruv-anand-aintech/anysearch#main:js",
      "Replace each call site with anysearch search(...) using the unified params.",
      "Keep the existing API key env vars — anysearch reads them automatically.",
      "Use { provider: '<name>' } to pin a provider, or omit it to auto-select.",
    ],
  };
}
