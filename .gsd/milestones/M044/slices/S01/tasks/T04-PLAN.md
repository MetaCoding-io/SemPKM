---
estimated_steps: 10
estimated_files: 4
skills_used: []
---

# T04: Full codebase verification sweep and cleanup

Final codebase-wide verification sweep to confirm zero remaining bare `fetch()` calls, then sanity-check a few key patterns to ensure the migration didn't break behavioral contracts.

**Verification steps:**
1. Run `rg '\\bfetch\\(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch' | grep -v vendor.js` — must return zero results
2. Run `rg '\\bfetch\\(' backend/app/templates/ -g '*.html' | grep -v apiFetch` — must return zero results
3. Count total `apiFetch(` calls across JS + HTML and confirm the number roughly matches the original 167
4. Verify `api-fetch.js` is loaded before any consumer: check script order in `base.html` (after posthog.js, before auth.js)
5. Verify toast CSS is in `theme.css` and removed from `workspace.css`
6. Spot-check the copilot SSE streaming path in `copilot.js` — confirm `.body.getReader()` chain is intact after apiFetch
7. Spot-check auth.js — confirm 401 handling still works correctly with apiFetch wrapper
8. If any bare `fetch(` calls remain, fix them or mark with `// raw-fetch` comment explaining why

## Inputs

- `frontend/static/js/api-fetch.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/sparql-console.js`
- `frontend/static/js/copilot.js`
- `frontend/static/js/canvas.js`
- `frontend/static/js/auth.js`
- `frontend/static/js/federation.js`
- `frontend/static/js/vfs-browser.js`

## Expected Output

- `frontend/static/js/api-fetch.js`

## Verification

total_js=$(rg '\\bfetch\\(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch' | grep -v vendor.js | wc -l) && total_html=$(rg '\\bfetch\\(' backend/app/templates/ -g '*.html' | grep -v apiFetch | wc -l) && echo "JS: $total_js, HTML: $total_html" && test "$total_js" -eq 0 && test "$total_html" -eq 0 && test -f frontend/static/js/api-fetch.js && rg 'sempkm-toast' frontend/static/css/theme.css -q && ! rg 'sempkm-toast' frontend/static/css/workspace.css -q
