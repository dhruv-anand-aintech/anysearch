import assert from "node:assert/strict";
import test from "node:test";
import { getProviderSpec } from "../src/providers/index.js";
import { resolveSerpapiEngine } from "../src/providers/serpapiEngines.js";
import type { ProviderContext } from "../src/providers/base.js";
import { makeRequest } from "../src/types.js";

test("serpapi prepare uses bing engine", () => {
  const spec = getProviderSpec("serpapi");
  const req = makeRequest("coffee", { engine: "bing" });
  const ctx: ProviderContext = {
    apiKey: "key",
    baseUrl: "https://serpapi.com",
    env: {},
    config: {},
  };
  const prep = spec.prepare(ctx, req);
  assert.equal(prep.params?.engine, "bing");
});

test("resolveSerpapiEngine maps news for baidu", () => {
  assert.equal(
    resolveSerpapiEngine({
      engine: "baidu",
      defaultEngine: "google",
      searchType: "news",
      extra: {},
    }),
    "baidu_news",
  );
});
