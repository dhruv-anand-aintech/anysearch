# Search API provider matrix

Interactive capability matrix for [anysearch](https://github.com/AI-Northstar-Tech/anysearch),
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

Push to `main` (touches matrix paths) → GitHub Action runs `matrix:sync` and
(optionally) `wrangler deploy`. Requires repo secrets:

| Secret | Notes |
| --- | --- |
| `CLOUDFLARE_ACCOUNT_ID` | Set on this repo (same account as local Wrangler OAuth). |
| `CLOUDFLARE_API_TOKEN` | Copy from [dhruv-anand-aintech/agent-launch](https://github.com/dhruv-anand-aintech/agent-launch/settings/secrets/actions) → this repo’s Actions secrets. Without it, CI still validates/bundles matrix data but skips deploy. |

Manual:

```bash
npm run deploy:matrix
```
