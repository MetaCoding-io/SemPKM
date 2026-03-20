# S01: Build Pipeline & Local Vendoring — UAT

**Milestone:** M029
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: Build pipeline correctness can be verified via file inspection, but full integration (htmx CRUD, Cytoscape, dockview) requires a running Docker stack

## Preconditions

- Node.js 20+ installed (for local build verification)
- Docker and Docker Compose available
- No running containers from previous tests (`docker compose down` first)
- Working directory is project root

## Smoke Test

Run `cd frontend && npm ci && node build.js` — should complete in <5s with `manifest.json` containing 37 entries.

## Test Cases

### 1. Build pipeline produces complete output

1. `cd frontend && rm -rf dist node_modules`
2. `npm ci`
3. `node build.js`
4. **Expected:** Exit code 0, stdout shows "37 entries" and "38 .gz files created"
5. `cat dist/manifest.json | python3 -m json.tool | wc -l` — **Expected:** ≥40 lines (37 entries + braces)
6. `ls dist/*.gz | wc -l` — **Expected:** 38
7. `ls dist/vendor-*.min.js` — **Expected:** exactly 1 file, ~1.5MB

### 2. Manifest maps all expected assets

1. `node -e "const m=require('./dist/manifest.json'); const keys=Object.keys(m); console.log(keys.length); console.log(keys.filter(k=>k.endsWith('.js')).length); console.log(keys.filter(k=>k.endsWith('.css')).length);"`
2. **Expected:** 37 total, ~26 JS entries, ~11 CSS entries
3. Verify key entries exist: `vendor.js`, `vendor.css`, `workspace-vendor.js`, `workspace-vendor.css`, `yasgui.js`, `yasgui.css`, `chartjs.js`, `hljs-github.css`, `hljs-github-dark.css`, `workspace.js`, `workspace.css`

### 3. Unit tests pass for template helpers

1. `cd backend && .venv/bin/python -m pytest tests/test_template_helpers.py -v`
2. **Expected:** 26/26 passed, 0 failed

### 4. CDN references are guarded in templates

1. `grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/`
2. **Expected:** All CDN URLs appear on lines that are preceded by `{% else %}` within a `{% if asset_manifest_available %}` block
3. No CDN URL should appear outside an else block — verify by checking that every hit has `{% else %}` or `{# Dev mode` context above it

### 5. Docker build produces working image

1. `docker compose build frontend`
2. **Expected:** Exit code 0, multi-stage build completes
3. `docker compose run --rm --no-deps frontend ls /build-assets/manifest.json`
4. **Expected:** File exists
5. `docker compose run --rm --no-deps frontend ls /build-assets/ | wc -l`
6. **Expected:** ≥70 files

### 6. Docker stack serves local assets

1. `docker compose up -d`
2. Wait for stack to be healthy (~10s)
3. `docker compose restart api` (ensures manifest is loaded from shared volume)
4. `curl -s http://localhost:3000/assets/manifest.json | python3 -m json.tool | head -5`
5. **Expected:** Valid JSON with vendor.js entry
6. `curl -s http://localhost:3000/browser/ | grep -c '/assets/'`
7. **Expected:** ≥3 (vendor.js, vendor.css, workspace.js minimum)

### 7. Zero CDN requests in production mode

1. Open browser to `http://localhost:3000/browser/`
2. Open Network tab, filter by domain
3. **Expected:** No requests to unpkg.com, jsdelivr.net, or cdnjs.cloudflare.com
4. All JS/CSS loaded from localhost /assets/ paths

### 8. Vendor libraries loaded correctly

1. Open browser console on workspace page
2. Check: `typeof htmx` — **Expected:** "object"
3. Check: `typeof cytoscape` — **Expected:** "function"
4. Check: `typeof marked` — **Expected:** "object"
5. Check: `typeof DOMPurify` — **Expected:** "object"
6. Check: `typeof hljs` — **Expected:** "object"
7. Check: `typeof Split` — **Expected:** "function"
8. Check: `window['dockview-core']` — **Expected:** truthy (object with DockviewComponent)

### 9. htmx CRUD works with vendored bundle

1. Navigate to workspace (`/browser/`)
2. Expand the OBJECTS section in explorer
3. Click any object to open it
4. **Expected:** Object tab opens, content renders (markdown body, properties panel)
5. No JS errors in console related to htmx or missing globals

### 10. Dev mode fallback works

1. Stop Docker stack: `docker compose down`
2. Remove the `ASSET_MANIFEST_PATH` env var if set (or set to `/nonexistent`)
3. Start the backend without Docker (or with volume mounts that mask built assets)
4. **Expected:** Templates render with CDN `<script>` tags (check view-source)
5. Application still works with CDN-loaded libraries

## Edge Cases

### Empty manifest.json

1. Create an empty file at the manifest path: `echo '{}' > /tmp/empty-manifest.json`
2. Set `ASSET_MANIFEST_PATH=/tmp/empty-manifest.json`
3. Start backend
4. **Expected:** `asset_manifest_available` is True but all `asset_url()` calls fall back to dev paths (missing key → dev path)

### Malformed manifest.json

1. Create invalid JSON: `echo 'not json' > /tmp/bad-manifest.json`
2. Set `ASSET_MANIFEST_PATH=/tmp/bad-manifest.json`
3. Start backend
4. **Expected:** Warning logged, `asset_manifest_available` is False, CDN fallback used

### Build from clean state

1. `cd frontend && rm -rf node_modules dist`
2. `npm ci && node build.js`
3. **Expected:** Identical manifest.json content (content hashes are deterministic given same input)

## Failure Signals

- JS console errors about undefined globals (htmx, cytoscape, marked, etc.) — vendor bundle didn't load or is incomplete
- `asset_manifest_available` is False in production Docker — manifest.json not accessible to API container
- Network requests to CDN domains in production — template conditional blocks are not rendering the production branch
- `docker compose logs api | grep 'Asset manifest not found'` — shared volume not populated or mount path wrong
- Build produces fewer than 37 manifest entries — a source file was added without updating build.js

## Requirements Proved By This UAT

- PERF-02 (local vendoring) — all CDN dependencies served locally
- PERF-03 (build pipeline) — esbuild build runs as part of docker compose build

## Not Proven By This UAT

- PERF-04 (gzip compression) — compression headers are S02 scope
- PERF-05 (HTTP caching) — cache headers are S02 scope
- PERF-06 (CSS code-splitting) — CSS splitting is S03 scope
- PERF-07 (Lighthouse ≥ 85) — Lighthouse measurement is S05 scope
- Yasgui SPARQL console rendering — requires navigating to admin SPARQL page with the admin model installed
- Chart.js sparkline rendering — requires admin model detail page with installed model data

## Notes for Tester

- After `docker compose build frontend`, the first `docker compose up -d` may require a `docker compose restart api` for the API to pick up the manifest from the shared volume. This is a known startup ordering issue.
- The dockview layout warning ("saved dockview layout incompatible, rebuilding") in the console is pre-existing and not a regression.
- The vendor.min.js is ~1.5MB uncompressed — this is expected for 18 bundled libraries. S02 will add gzip compression reducing transfer to ~427KB.
