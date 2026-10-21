# Search API provider matrix

Interactive capability matrix for [anysearch](https://github.com/dhruv-anand-aintech/anysearch),
deployed at **https://compare-anysearch.ainorthstar.tech** (same UX pattern as
[compare.ainorthstar.tech](https://compare.ainorthstar.tech/) for coding agents).

## Data layout

| Path | Role |
| --- | --- |
| `schema.json` | Row definitions (groups, labels) |
| `data/*.json` | One file per provider |
| `bundle.json` | Generated array consumed by the Worker |
| `updated.json` | Last bundle timestamp |
| `llms.txt` | Text export for LLMs |

Provider JSON is **generated from the Python SDK** so capabilities stay in sync:

```bash
npm run matrix:generate   # scripts/generate_search_matrix_data.py
npm run matrix:validate
npm run matrix:bundle
npm run matrix:llms-txt
# or
npm run matrix:sync
npm run matrix:verify-page   # smoke-test HTML + client script (table must render)
```

After changing `python/src/anysearch/providers/*`, run `matrix:sync` and commit
`data/`, `bundle.json`, `updated.json`, and `llms.txt`.

## Local preview

```bash
npm install
npm run matrix:sync
npx wrangler dev --config wrangler.toml
```

Open the URL Wrangler prints (usually `http://localhost:8787`).

## Deploy

Push to `main` (touches matrix paths) → GitHub Action runs `matrix:sync`,
`matrix:verify-page` (catches broken client JS before deploy), and optionally
`wrangler deploy`. Requires repo secrets:

| Secret | Notes |
| --- | --- |
| `CLOUDFLARE_ACCOUNT_ID` | Set on this repo (same account as local Wrangler OAuth). |
| `CLOUDFLARE_API_TOKEN` | Copy from [dhruv-anand-aintech/agent-launch](https://github.com/dhruv-anand-aintech/agent-launch/settings/secrets/actions) → this repo’s Actions secrets. Without it, CI still validates/bundles matrix data but skips deploy. |

Manual:

```bash
npm run deploy:matrix
```

## Official-source review (2026-10-21)

`research.json` is the reviewed source of current commercial/product facts. It covers
26 provider families across 31 offerings (six SerpApi engine columns share one vendor).
`apply_search_research.py` applies that review after SDK metadata generation, so sync
cannot overwrite reviewed pricing with stale SDK-era notes. New comparison-only
entries explicitly have no anysearch adapter; the SDK parity tests still cover every
claimed adapter. Native product features and unified SDK mappings are separate.

Sources, review dates, effective dates where verified, conflicts and billing units
are retained in the research file and generated evidence objects. No paid provider
calls or new quality/latency benchmarks were run. July latency evidence is visibly
historical. DeepSeek's live October 21 guide specifies Search 100 QPS and Fetch 25 QPS;
an earlier indexed snapshot reported 5 QPS each and is superseded by the live guide.

The visible evidence date comes from source review dates, not the build clock.
`npm run matrix:research-check` rejects missing evidence or reviews older than 45 days.
Weekly CI validates the site and checks public source availability, uploading a report;
it does **not** autonomously research changed commercial claims, advance review dates,
or deploy scheduled builds. Review failures require a human/agent refresh of
`research.json`. A successful link check is not proof that a claim is still correct.

Changelog is comparison repository history, not a fabricated provider release timeline.
New files are included even before staging. `/changelog`, `/#changelog` and
`/changelog.json` expose navigation and machine-readable history. `/updated.json` and
`/deployment-info` expose evidence date and build identity. The release must run
`npm run matrix:sync`, `npm run matrix:research-check`, `npm run matrix:test`, then the
existing push/deploy process. After committing data, regenerate changelog and commit
its final Git provenance before deploying. Verify production bundle identity.

Diagnosis evidence: the previous task completed July 28, 2026; the production marker
was `tiered-latency-2026-07-28`. GitHub's latest recorded successful workflow was
https://github.com/dhruv-anand-aintech/anysearch/actions/runs/30362370718 . The workflow
had push/manual triggers, no schedule. No local search-matrix LaunchAgent or Codex
scheduled task was found in the inspected configuration. Direct tab clicks worked;
Back after Changelog → Compare left `#changelog` showing Compare. Missing popstate and
hashchange handling caused that reproducible navigation failure. A general current
homepage outage was not reproduced. Unknown JSON routes previously fell through to
HTML, and the old smoke test checked rendering without navigating tabs/history.

## New-column categorical evidence and price sorting

The follow-up audit found that all 84 feature cells in the seven new columns had
been set to unknown solely because there was no SDK adapter. That confused adapter
availability with provider capability. `categorical-research.json` now contains a
separate, dated native-API assessment for each feature plus Mode. The generated
`categorical-coverage-audit.md` lists all 91 prior/new values, exact official sources
and scope explanations. The visible Capability basis row distinguishes native
research for the new columns from existing SDK mappings for older columns.

Supported, limited/conditional, not exposed by the scoped contract, not applicable,
and specifically undocumented are distinct. N/A covers retired Bing and mismatched
model/raw-output abstractions; Undoc. retains specific documentation gaps after
review. This does not claim a missing SDK adapter or a silent doc page proves an API
capability unsupported. Anysearch adapter availability remains unchanged.

Pricing uses explicit `primary_price.amount_usd_per_1k`, never numbers parsed from
display text. Click Pricing / 1K to cycle ascending, descending and original order.
The primary price is the first documented priced offering shown in that column;
plan commitments, promotions, model-token charges and billing units remain visible.
For example, DataForSEO's $0.60 queued SERP page is not equivalent to a live request,
and hosted model tool fees exclude token charges. This is a numeric primary-price
ordering, not a normalized total-cost ranking. Credit-priced Firecrawl, token-priced
Jina, conflicting Keiro, retired Bing and closed-to-new-users Google PSE are unranked
and stay last in both directions. Zero software/library API fees sort as zero while
hosting, proxy and upstream costs remain explicit.
