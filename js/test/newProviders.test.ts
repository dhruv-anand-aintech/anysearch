import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { AnySearch, getProviderSpec } from "../src/index.js";

type Route = (url: string, init: RequestInit) => { status: number; body: unknown };

const realFetch = globalThis.fetch;

function mockFetch(routes: Record<string, Route>): void {
  globalThis.fetch = (async (input: string | URL | Request, init: RequestInit = {}) => {
    const url = typeof input === "string" ? input : input.toString();
    for (const [needle, handler] of Object.entries(routes)) {
      if (url.includes(needle)) {
        const { status, body } = handler(url, init);
        return new Response(JSON.stringify(body), {
          status,
          headers: { "content-type": "application/json" },
        });
      }
    }
    throw new Error(`No mock route for ${url}`);
  }) as typeof fetch;
}

afterEach(() => {
  globalThis.fetch = realFetch;
});

test("keenable maps mode, site, dates and normalizes results", async () => {
  let body: any;
  mockFetch({
    "api.keenable.ai/v1/search": (_url, init) => {
      body = JSON.parse(String(init.body));
      return {
        status: 200,
        body: {
          query: "ai news",
          mode: "realtime",
          results: [
            {
              title: "AI news",
              url: "https://example.com/ai",
              description: "A short description",
              snippet: "The query-relevant snippet",
              published_at: "2026-10-20T10:00:00Z",
            },
          ],
        },
      };
    },
  });
  const client = new AnySearch({ provider: "keenable", apiKey: "keen-test", env: {} });
  const response = await client.search("ai news", {
    maxResults: 5,
    mode: "fast",
    includeDomains: ["example.com"],
    startPublishedDate: "2026-10-01",
    endPublishedDate: "2026-10-22",
  });
  assert.deepEqual(body, {
    query: "ai news",
    mode: "realtime",
    max_results: 5,
    site: "example.com",
    published_after: "2026-10-01",
    published_before: "2026-10-22",
  });
  assert.equal(response.results[0].snippet, "The query-relevant snippet");
  assert.equal(response.results[0].publishedDate, "2026-10-20T10:00:00Z");
});

test("tinyfish maps locale, domains, news and normalizes results", async () => {
  let url = "";
  mockFetch({
    "api.search.tinyfish.ai": (input) => {
      url = input;
      return {
        status: 200,
        body: {
          query: "ai",
          results: [
            {
              site_name: "Example",
              title: "Example result",
              snippet: "Snippet text",
              url: "https://example.com/a",
              date: "2026-10-20",
              publisher: "Example News",
            },
          ],
          total_results: 1,
        },
      };
    },
  });
  const client = new AnySearch({ provider: "tinyfish", apiKey: "tf-test", env: {} });
  const response = await client.search("ai", {
    searchType: "news",
    country: "GB",
    language: "en",
    includeDomains: ["example.com"],
    excludeDomains: ["spam.example"],
    startPublishedDate: "2026-10-01",
  });
  const params = new URL(url).searchParams;
  assert.equal(params.get("location"), "GB");
  assert.equal(params.get("language"), "en");
  assert.equal(params.get("include_domains"), "example.com");
  assert.equal(params.get("exclude_domains"), "spam.example");
  assert.equal(params.get("domain_type"), "news");
  assert.equal(params.get("after_date"), "2026-10-01");
  assert.equal(response.results[0].source, "Example");
});

test("deepseek builds query operators and returns content and summary", async () => {
  let body: any;
  mockFetch({
    "api.deepseek.com/v1/tools/search": (_url, init) => {
      body = JSON.parse(String(init.body));
      return {
        status: 200,
        body: {
          results: [
            {
              rerank_score: 2.4,
              title: "DeepSeek result",
              url: "https://example.com/ds",
              snippet: "Short",
              summary: "Long model-readable summary",
              content: "# Page body",
              site_name: "Example",
              date: "2026-06-01T00:00:00+00:00",
            },
          ],
        },
      };
    },
  });
  const client = new AnySearch({ provider: "deepseek", apiKey: "ds-test", env: {} });
  const response = await client.search("agents", {
    maxResults: 3,
    includeContent: true,
    includeDomains: ["example.com", "docs.example"],
    excludeDomains: ["spam.example"],
    language: "en",
    startPublishedDate: "2026-01-01",
    endPublishedDate: "2026-06-01",
  });
  assert.equal(body.count, 3);
  assert.equal(body.need_content, true);
  assert.equal(
    body.query,
    "agents site:example.com OR site:docs.example -site:spam.example lang:en after:2026-01-01 before:2026-06-01",
  );
  assert.equal(response.results[0].text, "# Page body");
  assert.equal(response.results[0].summary, "Long model-readable summary");
  assert.equal(response.results[0].score, 2.4);
});

test("brightdata posts a parsed Google SERP request and reads organic results", async () => {
  let body: any;
  mockFetch({
    "api.brightdata.com/request": (_url, init) => {
      body = JSON.parse(String(init.body));
      return {
        status: 200,
        body: {
          organic: [
            {
              global_rank: 1,
              title: "Bright result",
              link: "https://example.com/b",
              description: "Result description",
            },
          ],
        },
      };
    },
  });
  const client = new AnySearch({
    provider: "brightdata",
    apiKey: "bd-test",
    env: { BRIGHTDATA_ZONE: "serp_zone" },
  });
  const response = await client.search("pizza", {
    country: "US",
    language: "en",
    includeDomains: ["example.com"],
    safeSearch: "strict",
  });
  assert.equal(body.zone, "serp_zone");
  assert.equal(body.data_format, "parsed");
  assert.match(body.url, /q=pizza\+site%3Aexample\.com/);
  assert.match(body.url, /gl=us/);
  assert.match(body.url, /hl=en/);
  assert.match(body.url, /safe=active/);
  assert.equal(response.results[0].url, "https://example.com/b");
  assert.equal(response.results[0].score, 1);
});

test("brightdata and dataforseo configuration require both credentials", () => {
  assert.equal(getProviderSpec("brightdata").isConfigured?.({ BRIGHTDATA_API_KEY: "x" }), false);
  assert.equal(
    getProviderSpec("brightdata").isConfigured?.({
      BRIGHTDATA_API_KEY: "x",
      BRIGHTDATA_ZONE: "zone",
    }),
    true,
  );
  assert.equal(getProviderSpec("dataforseo").isConfigured?.({ DATAFORSEO_LOGIN: "login" }), false);
  assert.equal(
    getProviderSpec("dataforseo").isConfigured?.({
      DATAFORSEO_LOGIN: "login",
      DATAFORSEO_PASSWORD: "password",
    }),
    true,
  );
});

test("dataforseo uses basic auth and reads live organic items", async () => {
  let body: any;
  let auth = "";
  mockFetch({
    "api.dataforseo.com/v3/serp/google/organic/live/advanced": (_url, init) => {
      body = JSON.parse(String(init.body));
      auth = new Headers(init.headers).get("authorization") ?? "";
      return {
        status: 200,
        body: {
          tasks: [
            {
              result: [
                {
                  se_results_count: 1000,
                  items: [
                    {
                      type: "organic",
                      rank_absolute: 1,
                      title: "SEO result",
                      url: "https://example.com/seo",
                      description: "Description",
                    },
                    { type: "people_also_ask", title: "Skip me" },
                  ],
                },
              ],
            },
          ],
        },
      };
    },
  });
  const client = new AnySearch({
    provider: "dataforseo",
    env: { DATAFORSEO_LOGIN: "login", DATAFORSEO_PASSWORD: "password" },
  });
  const response = await client.search("seo", { maxResults: 5, language: "en" });
  assert.equal(auth, `Basic ${btoa("login:password")}`);
  assert.equal(body[0].keyword, "seo");
  assert.equal(body[0].depth, 5);
  assert.equal(body[0].language_code, "en");
  assert.equal(body[0].location_code, 2840);
  assert.equal(response.results.length, 1);
});

test("openai web search returns the answer and citation results", async () => {
  let body: any;
  mockFetch({
    "api.openai.com/v1/responses": (_url, init) => {
      body = JSON.parse(String(init.body));
      return {
        status: 200,
        body: {
          id: "resp_1",
          output: [
            {
              type: "message",
              content: [
                {
                  type: "output_text",
                  text: "A cited answer about AI news.",
                  annotations: [
                    {
                      type: "url_citation",
                      url: "https://example.com/openai",
                      title: "OpenAI source",
                      start_index: 0,
                      end_index: 10,
                    },
                  ],
                },
              ],
            },
          ],
        },
      };
    },
  });
  const client = new AnySearch({ provider: "openai", apiKey: "oa-test", env: {} });
  const response = await client.search("ai news", {
    mode: "deep",
    includeDomains: ["example.com"],
    excludeDomains: ["spam.example"],
  });
  assert.equal(body.tools[0].type, "web_search");
  assert.deepEqual(body.tools[0].filters, { allowed_domains: ["example.com"] });
  assert.equal(body.tools[0].search_context_size, "high");
  assert.deepEqual(body.reasoning, { effort: "high" });
  assert.equal(body.input, "ai news -site:spam.example");
  assert.equal(response.answer, "A cited answer about AI news.");
  assert.equal(response.results[0].title, "OpenAI source");
  assert.equal(response.requestId, "resp_1");
});

test("anthropic web search returns the answer and result blocks", async () => {
  let body: any;
  let version = "";
  mockFetch({
    "api.anthropic.com/v1/messages": (_url, init) => {
      body = JSON.parse(String(init.body));
      version = new Headers(init.headers).get("anthropic-version") ?? "";
      return {
        status: 200,
        body: {
          id: "msg_1",
          content: [
            {
              type: "web_search_tool_result",
              content: [
                {
                  type: "web_search_result",
                  url: "https://example.com/claude",
                  title: "Claude source",
                  page_age: "2026-10-20",
                },
              ],
            },
            { type: "text", text: "A cited Claude answer." },
          ],
        },
      };
    },
  });
  const client = new AnySearch({ provider: "anthropic", apiKey: "an-test", env: {} });
  const response = await client.search("ai news", {
    includeDomains: ["example.com"],
    excludeDomains: ["spam.example"],
  });
  assert.equal(version, "2023-06-01");
  assert.equal(body.tools[0].type, "web_search_20250305");
  assert.deepEqual(body.tools[0].allowed_domains, ["example.com"]);
  assert.deepEqual(body.tools[0].blocked_domains, ["spam.example"]);
  assert.equal(response.answer, "A cited Claude answer.");
  assert.equal(response.results[0].url, "https://example.com/claude");
  assert.equal(response.requestId, "msg_1");
});

test("xai web search returns the answer and both citation shapes", async () => {
  let body: any;
  mockFetch({
    "api.x.ai/v1/responses": (_url, init) => {
      body = JSON.parse(String(init.body));
      return {
        status: 200,
        body: {
          id: "xai_1",
          output: [
            {
              type: "message",
              content: [
                {
                  type: "output_text",
                  text: "A cited Grok answer.",
                  annotations: [
                    {
                      type: "url_citation",
                      url: "https://example.com/grok",
                      title: "Grok source",
                      start_index: 0,
                      end_index: 8,
                    },
                  ],
                },
              ],
            },
          ],
          citations: ["https://example.com/second"],
        },
      };
    },
  });
  const client = new AnySearch({ provider: "xai", apiKey: "xai-test", env: {} });
  const response = await client.search("ai news", {
    includeDomains: ["example.com"],
    excludeDomains: ["spam.example"],
  });
  assert.deepEqual(body.tools[0].filters, {
    allowed_domains: ["example.com"],
    excluded_domains: ["spam.example"],
  });
  assert.equal(response.answer, "A cited Grok answer.");
  assert.deepEqual(
    response.results.map((item) => item.url),
    ["https://example.com/grok", "https://example.com/second"],
  );
});
