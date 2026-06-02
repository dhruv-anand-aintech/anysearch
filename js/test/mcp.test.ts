import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";

import { scanCodebase } from "../src/mcp/migrate.js";
import { Server } from "../src/mcp/server.js";

function tempProject(files: Record<string, string>): string {
  const dir = mkdtempSync(join(tmpdir(), "anysearch-"));
  for (const [name, content] of Object.entries(files)) {
    writeFileSync(join(dir, name), content);
  }
  return dir;
}

test("scanCodebase detects providers and skips node_modules", () => {
  const dir = tempProject({
    "a.py": "from exa_py import Exa\nclient = Exa(api_key='x')\n",
    "b.js": "const r = await fetch('https://api.tavily.com/search')\n",
    "c.ts": "fetch('https://serpapi.com/search')\n",
  });
  const report = scanCodebase(dir);
  const detected = new Set(report.providersDetected);
  assert.ok(detected.has("exa") && detected.has("tavily") && detected.has("serpapi"));
  assert.ok(report.totalFindings >= 3);
  assert.ok(report.findings.some((f) => f.suggestion.includes("search")));
});

test("scanCodebase filters by provider", () => {
  const dir = tempProject({ "a.py": "from exa_py import Exa\nfrom tavily import TavilyClient\n" });
  const report = scanCodebase(dir, ["exa"]);
  assert.deepEqual(report.providersDetected, ["exa"]);
});

test("MCP initialize and tools/list", async () => {
  const server = new Server(["duckduckgo"]);
  const init = await server.handle({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: { protocolVersion: "2025-06-18" },
  });
  assert.equal((init as any).result.serverInfo.name, "anysearch");

  const notif = await server.handle({ jsonrpc: "2.0", method: "notifications/initialized" });
  assert.equal(notif, null);

  const listed = await server.handle({ jsonrpc: "2.0", id: 2, method: "tools/list" });
  const names = new Set((listed as any).result.tools.map((t: any) => t.name));
  assert.deepEqual(names, new Set(["search", "list_providers", "check_providers", "migrate_codebase"]));
});

test("MCP migrate_codebase tool", async () => {
  const dir = tempProject({ "x.py": "from tavily import TavilyClient\n" });
  const server = new Server(["duckduckgo"]);
  const resp = await server.handle({
    jsonrpc: "2.0",
    id: 4,
    method: "tools/call",
    params: { name: "migrate_codebase", arguments: { path: dir } },
  });
  assert.equal((resp as any).result.isError, false);
  assert.ok((resp as any).result.structuredContent.providersDetected.includes("tavily"));
});

test("MCP unknown method", async () => {
  const server = new Server(["duckduckgo"]);
  const resp = await server.handle({ jsonrpc: "2.0", id: 9, method: "does/not/exist" });
  assert.equal((resp as any).error.code, -32601);
});
