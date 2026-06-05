# Repository Guidelines

## Project Structure & Module Organization

This repo contains a dual SDK plus a hosted search capability matrix.

- `js/src/` contains the TypeScript SDK, provider adapters, router, HTTP helpers, and MCP server code. JS tests live in `js/test/`.
- `python/src/anysearch/` mirrors the SDK in Python, including providers and MCP support. Python tests live in `python/tests/`.
- `docs/tools/search_matrix/` stores matrix source data, schema, generated bundle, and `llms.txt`.
- `scripts/` contains matrix generation, import hooks, verification, and provider metadata helpers.
- `worker/matrix.js` and `wrangler.toml` define the Cloudflare Worker used to serve the matrix page.

## Build, Test, and Development Commands

- Root matrix sync: `npm run matrix:sync` regenerates, validates, bundles, and updates `llms.txt`.
- Matrix page check: `npm run matrix:verify-page` verifies the generated Worker page.
- Matrix deploy: `npm run deploy:matrix` runs sync, page verification, then `wrangler deploy`.
- JS SDK: from `js/`, run `npm run build`, `npm run typecheck`, and `npm test`.
- Python SDK: from `python/`, use `uv` where possible, then run `uv pip install -e '.[dev]'` and `pytest`.

## Coding Style & Naming Conventions

Use TypeScript ES modules in `js/`; keep provider files camelCase where already established, such as `googlePse.ts`, and export through `js/src/providers/index.ts`. Use Python package naming with snake_case modules, such as `google_pse.py`. Keep provider behavior aligned across JS and Python unless a platform-specific difference is intentional. Python style is Ruff-compatible with a 100-character line length and Python 3.9 target.

## Testing Guidelines

Tests must not make real provider API calls. Mock HTTP and external services, especially paid search APIs. Add or update matching tests in both SDKs when changing shared routing, provider normalization, MCP behavior, or error handling. Use names like `test_core.py` and `core.test.ts` for parallel coverage.

## Commit & Pull Request Guidelines

Git history uses short conventional-style subjects, for example `chore(matrix): ...`, `refactor(matrix): ...`, and `docs: ...`. Keep commits focused; split matrix regeneration from implementation changes when practical. PRs should describe the behavioral change, list verification commands run, link related issues, and include screenshots or URLs for Worker/matrix UI changes.

## Security & Configuration Tips

Look for `.env` files in this directory and parent directories before assuming configuration. Never commit secrets, API keys, or generated credentials. For Cloudflare custom domains, use `custom_domain = true` in `wrangler.toml`; deploy only after `npm run matrix:sync && npm run matrix:verify-page` passes.
