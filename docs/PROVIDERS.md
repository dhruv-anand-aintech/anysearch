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

| Provider | domains | country | language | date | safe_search | mode | answer | content | summary | highlights | news |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **exa** | ✅ | ✅ | — | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ |
| **parallel** | ✅ | ✅ | — | ✅ | — | ✅ | — | ✅ | — | ✅ | — |
| **tavily** | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | ✅ | — | — | ✅ |
| **brave** | — | ✅ | ✅ | ✅ | ✅ | — | — | — | — | ✅ | ✅ |
| **linkup** | ✅ | — | — | ✅ | — | ✅ | ✅ | ✅ | — | — | — |
| **perplexity** | ✅ | — | ✅ | — | — | — | — | ✅ | — | — | — |
| **serper** | — | ✅ | ✅ | — | — | — | ✅* | — | — | — | ✅ |
| **serpapi** | — | ✅ | ✅ | — | ✅ | — | ✅* | — | — | — | ✅ |
| **searchapi** | — | ✅ | ✅ | — | — | — | ✅* | — | — | — | ✅ |
| **you** | ✅ | ✅ | — | — | — | — | — | — | — | ✅ | — |
| **jina** | — | — | — | — | — | — | — | ✅ | — | — | — |
| **kagi** | — | — | — | — | — | — | — | — | — | — | — |
| **firecrawl** | — | ✅ | — | — | — | — | — | ✅ | — | — | ✅ |
| **google_pse** | ✅† | ✅ | ✅ | ✅ | ✅ | — | — | — | — | — | — |
| **searxng** | — | — | ✅ | — | ✅ | — | ✅‡ | — | — | — | — |
| **duckduckgo** | — | ✅ | — | — | ✅ | — | — | — | — | — | — |

\* Serper / SerpApi / SearchApi surface an answer only when the SERP includes an answer
box; it is not requested explicitly.
† Google PSE supports a single include **or** exclude domain (first one wins) via
`siteSearch`.
‡ SearXNG returns instant-answer text from its `answers` field when available.

## Notes on `mode`

The `mode` knob (`fast` / `balanced` / `deep`) is mapped to each provider's nearest
equivalent:

| Provider | fast | balanced | deep |
| --- | --- | --- | --- |
| exa | `fast` | `auto` | `deep` |
| tavily | `fast` | `basic` | `advanced` |
| parallel | `basic` | `basic` | `advanced` |
| linkup | `fast` | `standard` | `deep` |

For providers without a depth setting, `mode` is ignored.

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
