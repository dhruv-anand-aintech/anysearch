import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import { AnySearch, getProviderSpec, listProviderNames } from "../src/index.js";
import { availableProviders, enforceCapabilities, selectProvider } from "../src/router.js";
import { UnsupportedParameterError } from "../src/errors.js";
import { makeRequest } from "../src/types.js";

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

test("all required providers registered", () => {
  const names = listProviderNames();
  for (const required of ["exa", "parallel", "serpapi", "brave", "keiro"]) {
    assert.ok(names.includes(required), `${required} missing`);
  }
  assert.ok(names.includes("gemini"));
  assert.ok(names.length >= 15);
});

test("aliases resolve to canonical providers", () => {
  assert.equal(getProviderSpec("serp").name, "serpapi");
  assert.equal(getProviderSpec("ddg").name, "duckduckgo");
  assert.equal(getProviderSpec("google").name, "google_pse");
  assert.equal(getProviderSpec("keirolabs").name, "keiro");
});

test("availability and selection from env", () => {
  assert.deepEqual(availableProviders({}), ["duckduckgo"]);
  assert.equal(selectProvider({}), "duckduckgo");
  const env = { EXA_API_KEY: "x", TAVILY_API_KEY: "y" };
  const avail = availableProviders(env);
  assert.ok(avail.includes("exa") && avail.includes("tavily"));
  assert.equal(selectProvider(env), "exa");
  assert.equal(selectProvider({ ANYSEARCH_PROVIDER: "tavily", EXA_API_KEY: "x" }), "tavily");
});

test("keiro default cited search normalizes response", async () => {
  let sentBody: any;
  let sentHeaders: Headers;
  mockFetch({
    "kierolabs.space/api/v2/keiro": (_url, init) => {
      sentBody = JSON.parse(String(init.body));
      sentHeaders = new Headers(init.headers);
      return {
        status: 200,
        body: {
          query: "q",
          total_results: 1,
          latency_ms: 123,
          results: [
            {
              title: "Keiro result",
              url: "https://k.example/a",
              snippet: "cited snippet",
              score: 0.82,
              published_date: "2026-05-27",
            },
          ],
        },
      };
    },
  });
  const client = new AnySearch({ provider: "keiro", apiKey: "keiro-test", env: {} });
  const resp = await client.search("q", { maxResults: 5 });
  assert.equal(sentHeaders!.get("authorization"), "Bearer keiro-test");
  assert.equal(sentBody.query, "q");
  assert.equal(sentBody.maxResults, 5);
  assert.equal(resp.provider, "keiro");
  assert.equal(resp.totalResults, 1);
  assert.equal(resp.latencyMs, 123);
  assert.equal(resp.results[0].snippet, "cited snippet");
  assert.equal(resp.results[0].publishedDate, "2026-05-27");
});

test("keiro content route returns full text", async () => {
  let sentBody: any;
  mockFetch({
    "kierolabs.space/api/v2/search/content": (_url, init) => {
      sentBody = JSON.parse(String(init.body));
      return {
        status: 200,
        body: {
          results: [
            {
              title: "Full text",
              url: "https://k.example/full",
              full_text: "markdown body",
              score: 0.9,
            },
          ],
        },
      };
    },
  });
  const client = new AnySearch({ provider: "keiro", apiKey: "keiro-test", env: {} });
  const resp = await client.search("q", { includeContent: true, mode: "deep" });
  assert.equal(sentBody.mode, "deep");
  assert.equal(resp.results[0].text, "markdown body");
  assert.equal(resp.results[0].snippet, "markdown body");
});

test("capability enforcement modes", () => {
  const serper = getProviderSpec("serper");
  const req = makeRequest("q", { includeDomains: ["a.com"], startPublishedDate: "2024-01-01" });
  assert.throws(() => enforceCapabilities(serper, req, "error"), UnsupportedParameterError);
  const safe = enforceCapabilities(serper, req, "ignore");
  assert.deepEqual(safe.includeDomains, []);
  assert.equal(safe.startPublishedDate, undefined);
});

test("exa search normalizes response", async () => {
  mockFetch({
    "api.exa.ai/search": () => ({
      status: 200,
      body: {
        requestId: "req-1",
        results: [
          {
            title: "Vector DBs",
            url: "https://example.com/a",
            text: "full text",
            summary: "a summary",
            highlights: ["hl one", "hl two"],
            score: 0.91,
            publishedDate: "2026-01-02",
            author: "Jane",
          },
        ],
      },
    }),
  });
  const client = new AnySearch({ provider: "exa", apiKey: "test-key", env: {} });
  const resp = await client.search("vector dbs", {
    includeContent: true,
    highlights: true,
    includeSummary: true,
  });
  assert.equal(resp.provider, "exa");
  assert.equal(resp.requestId, "req-1");
  assert.equal(resp.results.length, 1);
  const r = resp.results[0];
  assert.equal(r.title, "Vector DBs");
  assert.equal(r.text, "full text");
  assert.equal(r.summary, "a summary");
  assert.deepEqual(r.highlights, ["hl one", "hl two"]);
  assert.equal(r.source, "example.com");
});

test("per-call provider overrides set API key and base URL", async () => {
  let sentHeaders: Headers;
  mockFetch({
    "override.example/search": (_url, init) => {
      sentHeaders = new Headers(init.headers);
      return {
        status: 200,
        body: { results: [{ title: "Override", url: "https://override.example/r", text: "ok" }] },
      };
    },
  });
  const client = new AnySearch({ env: {} });
  const resp = await client.search("q", {
    provider: "exa",
    apiKey: "call-key",
    baseUrl: "https://override.example",
  });
  assert.equal(sentHeaders!.get("x-api-key"), "call-key");
  assert.equal(resp.provider, "exa");
  assert.equal(resp.results[0].title, "Override");
});

test("tavily answer and raw content", async () => {
  mockFetch({
    "api.tavily.com/search": () => ({
      status: 200,
      body: {
        answer: "the answer",
        results: [
          { title: "T", url: "https://t.example/x", content: "snippet", raw_content: "raw text", score: 0.5 },
        ],
      },
    }),
  });
  const client = new AnySearch({ provider: "tavily", apiKey: "tvly", env: {} });
  const resp = await client.search("q", { answer: true, includeContent: true });
  assert.equal(resp.answer, "the answer");
  assert.equal(resp.results[0].text, "raw text");
  assert.equal(resp.results[0].snippet, "snippet");
});

test("fallback on provider error", async () => {
  mockFetch({
    "api.exa.ai/search": () => ({ status: 500, body: { error: "boom" } }),
    "api.tavily.com/search": () => ({
      status: 200,
      body: { results: [{ title: "ok", url: "https://ok.example", content: "c" }] },
    }),
  });
  const client = new AnySearch({
    provider: "exa",
    apiKey: "exa-key",
    fallbacks: ["tavily"],
    env: { TAVILY_API_KEY: "tvly" },
  });
  const resp = await client.search("q");
  assert.equal(resp.provider, "tavily");
  assert.equal(resp.results[0].title, "ok");
});

test("provider error raised without fallback", async () => {
  mockFetch({ "api.exa.ai/search": () => ({ status: 401, body: { error: "bad key" } }) });
  const client = new AnySearch({ provider: "exa", apiKey: "bad", env: {} });
  await assert.rejects(() => client.search("q"), /HTTP 401/);
});

test("unknown options pass through to extra", () => {
  const client = new AnySearch({ provider: "exa", apiKey: "k", env: {} });
  // @ts-expect-error accessing private for test
  const req = client.buildRequest(getProviderSpec("exa"), "q", { extra: { foo: 1 } });
  assert.deepEqual(req.extra, { foo: 1 });
});
