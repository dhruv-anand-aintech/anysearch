# Provider capability matrix

**Interactive matrix:** [compare-anysearch.ainorthstar.tech](https://compare-anysearch.ainorthstar.tech)
(drag columns, sort by capability, tooltips with docs links). This file is the static
reference; regenerate the site data with `npm run matrix:sync` from the repo root.

`anysearch` exposes one interface, but providers differ in what they support. The table
below shows which **unified parameters** each provider honors. Parameters a provider
can't honor are dropped (with a warning) by default, or you can pass
`on_unsupported="error"` / `onUnsupported: "error"` to fail loudly, or `"ignore"` to
drop silently.

Legend: ✅ supported · — not supported (the param is ignored for that provider).

| Provider | domains | country | language | date | safe_search | mode | engine | answer | content | summary | highlights | news |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **exa** | ✅ | ✅ | — | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ✅ | ✅ |
| **parallel** | ✅ | ✅ | — | ✅ | — | ✅ | — | — | ✅ | — | ✅ | — |
| **tavily** | ✅ | ✅ | — | ✅ | — | ✅ | — | ✅ | ✅ | — | — | ✅ |
| **brave** | — | ✅ | ✅ | ✅ | ✅ | — | — | — | — | — | ✅ | ✅ |
| **linkup** | ✅ | — | — | ✅ | — | ✅ | — | ✅ | ✅ | — | — | — |
| **perplexity** | ✅ | — | ✅ | — | — | — | — | — | ✅ | — | — | — |
| **serper** | — | ✅ | ✅ | — | — | — | — | ✅* | — | — | — | ✅ |
| **serpapi** | — | ✅ | ✅ | — | ✅ | — | ✅ | ✅* | — | — | — | ✅ |
| **searchapi** | — | ✅ | ✅ | — | — | — | — | ✅* | — | — | — | ✅ |
| **you** | ✅ | ✅ | — | — | — | — | — | — | — | — | ✅ | — |
| **jina** | — | — | — | — | — | — | — | — | ✅ | — | — | — |
| **kagi** | — | — | — | — | — | — | — | — | — | — | — | — |
| **firecrawl** | — | ✅ | — | — | — | — | — | — | ✅ | — | — | ✅ |
| **google_pse** | ✅‡ | ✅ | ✅ | ✅ | ✅ | — | — | — | — | — | — | — |
| **searxng** | — | — | ✅ | — | ✅ | — | — | ✅§ | — | — | — | — |
| **duckduckgo** | — | ✅ | — | — | ✅ | — | — | — | — | — | — | — |

\* Serper / SerpApi / SearchApi surface an answer only when the SERP includes an answer
box; it is not requested explicitly.
‡ Google PSE supports a single include **or** exclude domain (first one wins) via
`siteSearch`.
§ SearXNG returns instant-answer text from its `answers` field when available.

## SerpApi engines

Pass `engine` on `search()` (or set `AnySearch(provider="serpapi", provider_config={"serpapi": {"engine": "bing"}})`):

```python
client.search("query", provider="serpapi", engine="bing")
client.search("query", provider="serpapi", engine="baidu", country="cn")
client.search("headlines", provider="serpapi", engine="bing", search_type="news")
```

Common web engines: `google`, `bing`, `baidu`, `yandex`, `duckduckgo`, `yahoo`. See
[SerpApi Search API](https://serpapi.com/search-api) for the full catalog and engine-specific
parameters (pass via `extra`).

## Notes on `mode`

The matrix **Mode** row lists which of `fast`, `balanced`, and `deep` apply per API.
When anysearch maps `mode`, it uses the provider's nearest native knob:

| Provider | Matrix modes | Native / mapping |
| --- | --- | --- |
| exa | fast, balanced, deep | `type`: fast → fast, balanced → auto, deep → deep |
| tavily | fast, balanced, deep | `search_depth`: fast → fast, balanced → basic, deep → advanced |
| parallel | fast, balanced, deep | `mode`: fast/balanced → basic, deep → advanced |
| linkup | fast, balanced, deep | `depth`: fast → fast, balanced → standard, deep → deep |
| brave | fast, balanced, deep | Default search vs `extra_snippets=true` for richer excerpts |
| jina | fast, balanced, deep | `X-Respond-With: no-content` (fast) vs full Reader fetch |
| perplexity | fast, balanced, deep | `snippet_mode` low / medium / high (+ token budgets) |
| firecrawl | balanced, deep | Metadata-only search vs `scrapeOptions` inline scrape |
| you | fast, balanced, deep | Snippet search vs `livecrawl` + `livecrawl_formats` |
| kagi | balanced, deep | Snippet length from account Settings → Search |
| serper, serpapi, searchapi, google_pse, searxng, duckduckgo | balanced | No separate depth API; single SERP tier |

Providers with only `balanced` in the matrix have no documented fast/deep API parameter;
pass `mode` via `extra` if the vendor adds one later.

## Content fields, by intent

- **`snippet`** — the short description the engine returns. Available almost everywhere.
- **`text`** — full page content. Request with `include_content` (exa, tavily,
  parallel, linkup, perplexity, jina, firecrawl, you).
- **`summary`** — an AI-generated per-result summary. Request with `include_summary`
  (exa).
- **`highlights`** — query-relevant excerpts. Request with `highlights` (exa, brave,
  parallel, you).
- **`answer`** (top-level on the response) — a synthesized, often cited answer to the
  whole query. Request with `answer` (tavily, linkup; opportunistic on serper/serpapi/
  searchapi/searxng).

## Configuration reference

| Provider | Credentials | Optional |
| --- | --- | --- |
| exa | `EXA_API_KEY` | extra `exa` → `exa-py` |
| parallel | `PARALLEL_API_KEY` | extra `parallel` → `parallel-web` |
| tavily | `TAVILY_API_KEY` | extra `tavily` → `tavily-python` |
| brave | `BRAVE_API_KEY` | — |
| linkup | `LINKUP_API_KEY` | extra `linkup` → `linkup-sdk` |
| perplexity | `PERPLEXITY_API_KEY` | extra `perplexity` → `perplexityai` |
| serper | `SERPER_API_KEY` | — |
| serpapi | `SERPAPI_API_KEY` | extra `serpapi` → `google-search-results` |
| searchapi | `SEARCHAPI_API_KEY` | — |
| you | `YDC_API_KEY` | — |
| jina | `JINA_API_KEY` | — |
| kagi | `KAGI_API_KEY` | — |
| firecrawl | `FIRECRAWL_API_KEY` | extra `firecrawl` → `firecrawl-py` |
| google_pse | `GOOGLE_PSE_API_KEY` + `GOOGLE_PSE_CX` | — |
| searxng | `SEARXNG_BASE_URL` (no key; optional `SEARXNG_API_KEY`) | — |
| duckduckgo | none (keyless fallback) | extra `duckduckgo` → `ddgs` |

Override the API key or base URL per call/client with `api_key` / `base_url`
(`apiKey` / `baseUrl` in JS), or set `ANYSEARCH_PROVIDER` to pin a default provider.
