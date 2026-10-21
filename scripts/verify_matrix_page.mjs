#!/usr/bin/env node
/**
 * Predeploy smoke test for the search matrix HTML page.
 * Catches client-script ReferenceErrors (e.g. missing helpers) that break the table.
 */
import vm from "node:vm";
import assert from "node:assert/strict";
import { register } from "node:module";
import { pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

register(pathToFileURL(join(__dirname, "matrix_import_hooks.mjs")).href);

const REQUIRED_CLIENT_SYMBOLS = [
  "function faviconSlugForAgent",
  "function renderHeader",
  "function renderBody",
  "function favimg",
  "function showView",
  "function revealCell",
  "renderHeader(); renderBody();",
];

function extractClientScript(html) {
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  const client = blocks.find(
    (b) => b.includes("renderHeader") && b.includes("JSON.parse")
  );
  if (!client) throw new Error("Could not find matrix client script in rendered HTML");
  return client;
}

function runClientScriptSmoke(clientScript, payload, cookie = "", expectedPriceOrder = null) {
  const headerEl = { innerHTML: "" };
  const bodyEl = { innerHTML: "" };
  const pillEl = { textContent: "", dataset: { updatedAt: new Date().toISOString() } };
  const payloadJson = JSON.stringify(payload);

  const tableWrap = { clientWidth: 1200 };
  const events = {};
  const elements = Object.fromEntries(['matrixView','changelogView','compareTab','changelogTab'].map(id => [id, {hidden: id === 'changelogView', setAttribute(key,value) {this[key]=value;}}]));
  const document = {
    cookie,
    documentElement: { style: { setProperty() {} } },
    getElementById(id) {
      if (elements[id]) return elements[id];
      if (id === "headerRow") return headerEl;
      if (id === "tbody") return bodyEl;
      if (id === "updatedPill") return pillEl;
      if (id === "payload") {
        return { textContent: payloadJson };
      }
      return null;
    },
    querySelector(sel) {
      if (sel === ".table-wrap") return tableWrap;
      return null;
    },
    querySelectorAll() {
      return [];
    },
  };

  const window = {
    innerWidth: 1200,
    location: {hash: '', pathname: '/', search: ''},
    history: {pushState(_s,_t,url) { window.location.hash = url.startsWith('#') ? url : ''; }},
    addEventListener(name,fn) { events[name]=fn; },
    requestAnimationFrame(fn) {
      if (typeof fn === "function") fn();
      return 0;
    },
  };

  const sandbox = {
    document,
    window,
    requestAnimationFrame: window.requestAnimationFrame,
    console,
    setInterval() {},
    clearTimeout() {},
    setTimeout(fn) {
      if (typeof fn === "function") fn();
      return 0;
    },
    Intl: globalThis.Intl,
    Date: globalThis.Date,
    Math: globalThis.Math,
    JSON: globalThis.JSON,
    URL: globalThis.URL,
    encodeURIComponent: globalThis.encodeURIComponent,
  };

  vm.runInNewContext(clientScript, sandbox, { timeout: 10_000 });

  vm.runInNewContext("showView('changelog')", sandbox);
  if (elements.changelogView.hidden || !elements.matrixView.hidden) throw new Error('Changelog tab did not activate');
  vm.runInNewContext("showView('matrix')", sandbox);
  window.location.hash = '#changelog';
  if (!events.popstate || !events.hashchange) throw new Error('History/hash navigation handlers missing');
  events.popstate();
  if (elements.changelogView.hidden) throw new Error('Browser Back did not restore changelog');
  window.location.hash = ''; events.hashchange();
  if (elements.matrixView.hidden) throw new Error('Hash navigation did not restore matrix');

  for (const provider of payload.matrix.filter(row => row.comparison_only)) {
    for (const key of ['requires_key','snippet','domains','country','language','date','safe_search','answer','content','summary','highlights','news']) {
      const id = 'cell-' + provider.links.slug.replaceAll('_','-') + '-' + key.replaceAll('_','-');
      const row = bodyEl.innerHTML.match(new RegExp('<td id="' + id + '"[^>]*>([\\s\\S]*?)</td>'));
      assert.ok(row, 'Missing rendered native cell '+id);
      assert.ok(row[1].includes('support '+provider[key].support), 'Wrong rendered status '+id);
      assert.ok(!row[1].includes('class="dot">?</span>'), 'Placeholder remains '+id);
    }
  }
  vm.runInNewContext('colOrder = matrix.map((_,i)=>i); rowSort = []; cycleSort("pricing_per_1k");', sandbox);
  const ascending = Array.from(vm.runInNewContext('displayColOrder()', sandbox));
  vm.runInNewContext('cycleSort("pricing_per_1k")', sandbox);
  const descending = Array.from(vm.runInNewContext('displayColOrder()', sandbox));
  for (const [direction, order] of [['asc',ascending],['desc',descending]]) {
    let missing = false, previous = null;
    for (const index of order) {
      const value = payload.matrix[index].pricing_per_1k.primary_price?.amount_usd_per_1k;
      if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) { missing = true; continue; }
      assert.equal(missing, false, 'Unknown price must remain last in '+direction);
      if (previous !== null) assert.ok(direction === 'asc' ? value >= previous : value <= previous, 'Numeric order '+direction);
      previous = value;
    }
  }
  if (expectedPriceOrder) {
    assert.deepEqual(ascending, expectedPriceOrder.asc);
    assert.deepEqual(descending, expectedPriceOrder.desc);
  }
  vm.runInNewContext('cycleSort("pricing_per_1k")', sandbox);
  assert.equal(vm.runInNewContext('rowSort.length', sandbox), 0, 'Third click resets price sort');

  if (!headerEl.innerHTML.trim()) {
    throw new Error("renderHeader() produced empty #headerRow");
  }
  if (!bodyEl.innerHTML.trim()) {
    throw new Error("renderBody() produced empty #tbody");
  }
  if (!headerEl.innerHTML.includes("agent-col")) {
    throw new Error("Header row missing agent columns");
  }
  if (!bodyEl.innerHTML.includes("<tr")) {
    throw new Error("Table body missing rows");
  }
}

async function main() {
  const workerUrl = pathToFileURL(join(ROOT, "worker", "matrix.js")).href;
  const worker = await import(workerUrl);
  const res = await worker.default.fetch(new Request("https://matrix.test/"), {});
  if (!res.ok) throw new Error(`Matrix worker returned HTTP ${res.status}`);

  const html = await res.text();
  if (!html.includes('id="headerRow"') || !html.includes('id="tbody"')) {
    throw new Error("Rendered HTML missing table skeleton");
  }
  if (!html.includes('id="changelogView"') || !html.includes("changelog-cell-link")) {
    throw new Error("Rendered HTML missing changelog view or cell links");
  }

  for (const sym of REQUIRED_CLIENT_SYMBOLS) {
    if (!html.includes(sym)) {
      throw new Error(`Rendered HTML missing required client symbol: ${sym}`);
    }
  }

  const payloadMatch = html.match(
    /<script type="application\/json" id="payload">([\s\S]*?)<\/script>/
  );
  if (!payloadMatch) throw new Error("Rendered HTML missing #payload JSON");
  const payload = JSON.parse(payloadMatch[1]);
  const { matrix, columns } = payload;
  if (!Array.isArray(matrix) || matrix.length < 10) {
    throw new Error(`payload.matrix invalid: length ${matrix?.length}`);
  }
  if (!Array.isArray(columns) || !columns.length) {
    throw new Error("payload.columns missing or empty");
  }
  if (!columns.some((column) => column.key === "free_tier_limits")) {
    throw new Error("payload.columns missing free_tier_limits");
  }

  const slugify = (value) =>
    String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const cellTargets = new Set(
    matrix.flatMap((provider) =>
      columns.map((column) => {
        const providerSlug = provider.links?.slug || provider.name;
        return `cell-${slugify(providerSlug)}-${slugify(column.key)}`;
      })
    )
  );
  const changelogTargets = [
    ...html.matchAll(/data-target-id="(cell-[^"]+)"/g),
  ].map((match) => match[1]);
  if (!changelogTargets.length) {
    throw new Error("Changelog has no cell targets");
  }
  const missingTargets = changelogTargets.filter((target) => !cellTargets.has(target));
  if (missingTargets.length) {
    throw new Error(`Changelog targets missing cells: ${missingTargets.slice(0, 3).join(", ")}`);
  }

  const clientScript = extractClientScript(html);
  runClientScriptSmoke(clientScript, payload);
  const priceFixture = structuredClone(payload);
  priceFixture.matrix = [10, 0.75, 0, undefined, null, 1.5].map((amount,index) => {
    const row = structuredClone(payload.matrix[0]);
    row.name = 'Price fixture ' + index; row.links.slug = 'fixture-' + index;
    row.comparison_only = false;
    row.pricing_per_1k = {value: index === 1 ? '$10000; multiple tiers' : '$0.01 display text', primary_price:{amount_usd_per_1k:amount,billing_unit:'test requests',basis:'fixture'}};
    return row;
  });
  runClientScriptSmoke(clientScript, priceFixture, '', {asc:[2,1,5,0,3,4],desc:[0,5,1,2,3,4]});
  const compare = worker.comparePrimaryPriceCells;
  assert.ok(compare({primary_price:{amount_usd_per_1k:0}}, {primary_price:{amount_usd_per_1k:0.75}}) < 0);
  assert.ok(compare({}, {primary_price:{amount_usd_per_1k:0}}, 'desc') > 0);
  assert.equal(compare({}, {primary_price:{amount_usd_per_1k:null}}, 'desc'), 0);
  const corrupt = {cols: Array(matrix.length).fill(9999), rows: Array(columns.length - 1).fill('invalid')};
  runClientScriptSmoke(clientScript, payload, 'asmat_state=' + encodeURIComponent(JSON.stringify(corrupt)));
  for (const route of ['/bundle.json','/llms.txt','/changelog.json','/updated.json','/deployment-info','/api/deployment-info']) {
    const response = await worker.default.fetch(new Request('https://matrix.test'+route), {});
    if (!response.ok) throw new Error(route+' failed');
    if (route.endsWith('.json')) await response.json();
  }

  console.log(
    `matrix page verify: ok (${matrix.length} providers, header and body rendered)`
  );
}

main().catch((err) => {
  console.error("matrix page verify: FAILED");
  console.error(err.message || err);
  process.exit(1);
});
