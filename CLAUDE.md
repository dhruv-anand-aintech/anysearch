# anysearch — agent notes

## Search capability matrix

After changing matrix metadata, generated data, or `worker/matrix.js`:

1. `npm run matrix:sync`
2. `npm run matrix:verify-page`
3. **Commit, push, and deploy** — do not leave matrix work only local.

```bash
npm run matrix:sync && npm run matrix:verify-page
git add docs/tools/search_matrix/ docs/PROVIDERS.md scripts/search_matrix_provider_meta.py scripts/generate_search_matrix_data.py worker/matrix.js
git commit -m "…"
git push origin HEAD
npm run deploy:matrix
```

`deploy:matrix` runs sync + verify + `wrangler deploy` for compare-anysearch.ainorthstar.tech.
