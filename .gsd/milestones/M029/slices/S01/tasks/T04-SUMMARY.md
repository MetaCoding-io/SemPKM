---
id: T04
parent: S01
milestone: M029
provides:
  - Multi-stage Dockerfile building optimized assets in Node.js stage and serving via nginx
  - nginx /assets/ location block serving content-hashed built files
  - Docker shared volume (frontend_assets) making manifest.json accessible to API container
  - template_helpers.py multi-path manifest search supporting Docker shared volume
  - Complete T01-T04 integration — all CDN dependencies vendored and serving from /assets/
key_files:
  - frontend/Dockerfile
  - frontend/docker-entrypoint.sh
  - frontend/nginx.conf
  - docker-compose.yml
  - backend/app/template_helpers.py
  - backend/tests/test_template_helpers.py
  - frontend/static/js/theme.js
  - backend/app/main.py
  - backend/app/templates/base.html
  - backend/app/templates/base_embed.html
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/admin/sparql.html
  - backend/app/templates/admin/model_detail.html
  - backend/app/templates/errors/403.html
  - frontend/package.json
  - frontend/build.js
key_decisions:
  - Used /srv/built-assets/ as shared volume mount point to avoid conflict with bind-mount at /usr/share/nginx/html (which is :ro in dev)
  - Docker entrypoint script copies built assets from image to shared volume on each container start (avoids stale named volume problem)
  - nginx serves /assets/ via alias directive to shared volume path rather than root directive
  - template_helpers.py searches multiple paths in order — env override, Docker shared volume, in-container fallback
patterns_established:
  - Docker entrypoint script for populating shared volumes from image contents
  - Multi-path manifest search with env var override for tests
observability_surfaces:
  - INFO log at API startup showing manifest path and entry count (production) or "dev mode" message
  - docker compose exec frontend cat /srv/built-assets/manifest.json to inspect built assets
  - docker compose exec api python -c "from app.template_helpers import is_asset_manifest_available; print(is_asset_manifest_available())" to check mode
duration: ~25min
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T04: Multi-stage Dockerfile, nginx config, and Docker integration test

**Wired build pipeline into Docker with multi-stage Dockerfile, shared manifest volume, and zero-CDN production serving — all 18 vendor libraries load from /assets/**

## What Happened

This task was effectively the integration point for the entire S01 slice. Prior tasks (T01-T03) had created their code files but they were committed only to the M027 worktree branch, not the M029/main branch. Recovered all T01-T03 deliverables (build.js, package.json, template_helpers.py, template changes) from the M027 worktree, then built T04's Docker integration on top.

**Multi-stage Dockerfile:** Rewrote `frontend/Dockerfile` as a two-stage build. Stage 1 (node:20-alpine) runs `npm ci && node build.js` producing the dist/ directory. Stage 2 (nginx:stable-alpine) copies raw static files AND built assets. A pristine copy of built assets goes to `/build-assets/` (survives volume mounts).

**Manifest sharing problem:** The core challenge was getting manifest.json from the frontend container to the API container. The parent bind mount (`./frontend/static:/usr/share/nginx/html:ro`) is read-only, so a sub-volume at `/usr/share/nginx/html/assets` fails to mount. Solved by:
- Mounting a `frontend_assets` named volume at `/srv/built-assets/` in the frontend container
- An entrypoint script (`docker-entrypoint.sh`) copies `/build-assets/*` to `/srv/built-assets/` on every container start
- nginx serves `/assets/` via `alias /srv/built-assets/` directive
- API container mounts the same volume at `/app/frontend_assets:ro`

**template_helpers.py update:** Changed from a single `_MANIFEST_PATH` to a multi-path search: env var override → `/app/frontend_assets/manifest.json` (Docker shared volume) → `/usr/share/nginx/html/assets/manifest.json` (in-container fallback). Updated 26 unit tests to match.

**theme.js fix:** Discovered that `theme.js` had a hardcoded CDN base URL for hljs themes that overwrote the template's production `data-light-href`/`data-dark-href` attributes. Fixed to check data attributes first, falling back to CDN only in dev mode.

**Startup ordering:** The API container must restart after the frontend container has populated the shared volume. On first `docker compose up -d` after a build, the API loads before the volume is populated. `docker compose restart api` picks up the manifest. This is acceptable for a build-time operation.

## Verification

All task-plan and slice-level verification checks passed:

- `docker compose build frontend` — exit 0, Node.js stage builds 37 manifest entries + 38 .gz files
- `docker compose run --rm --no-deps frontend ls /build-assets/manifest.json` — exists
- `docker compose run --rm --no-deps frontend ls /build-assets/ | wc -l` — 76 files
- `curl -s http://localhost:3000/assets/manifest.json | python3 -m json.tool` — valid JSON
- Browser workspace: 18 scripts from /assets/, 0 CDN scripts; 10 stylesheets from /assets/, 0 CDN stylesheets
- All 7 core vendor libraries confirmed loaded: htmx 2.0.4, cytoscape, marked, DOMPurify, hljs, lucide, Split
- dockview-core loaded via `window['dockview-core'].DockviewComponent`
- htmx CRUD: opened Note object, markdown rendered correctly with no JS errors
- Unit tests: 26/26 passed for template_helpers.py
- CDN guard check: all CDN URLs in templates are inside `{% else %}` blocks

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose build frontend` | 0 | ✅ pass | 4s (cached) |
| 2 | `docker compose run --rm --no-deps frontend ls /build-assets/manifest.json` | 0 | ✅ pass | <1s |
| 3 | `docker compose run --rm --no-deps frontend ls /build-assets/ \| wc -l` (≥50) | 0 | ✅ pass (76) | <1s |
| 4 | `curl -s http://localhost:3000/assets/manifest.json \| python3 -m json.tool` | 0 | ✅ pass | <1s |
| 5 | `cd frontend && npm ci && node build.js` (slice check 1) | 0 | ✅ pass | 0.8s |
| 6 | `python -m pytest tests/test_template_helpers.py -v` (slice check 2) | 0 | ✅ pass (26/26) | 0.04s |
| 7 | CDN guard check (all CDN refs inside else blocks) | 0 | ✅ pass | <1s |
| 8 | Browser: asset script count = 18, CDN script count = 0 | - | ✅ pass | browser |
| 9 | Browser: vendor libs loaded (htmx, cytoscape, marked, DOMPurify, hljs, lucide, Split, dockview) | - | ✅ pass | browser |
| 10 | Browser: htmx tree expand + object open (no JS errors) | - | ✅ pass | browser |

### Slice-level checks:
| # | Check | Result |
|---|-------|--------|
| 1 | `cd frontend && npm ci && node build.js` produces dist/ with manifest.json | ✅ pass |
| 2 | `python -m pytest backend/tests/test_template_helpers.py -v` — 26/26 | ✅ pass |
| 3 | Zero unguarded CDN references in templates | ✅ pass |
| 4 | `docker compose build frontend` completes | ✅ pass |
| 5 | nginx serves /assets/ directory | ✅ pass |
| 6 | `curl -s .../browser/ \| grep -c '/assets/'` ≥ 3 | ✅ pass (29 total) |
| 7 | Docker workspace: htmx requests succeed | ✅ pass |
| 8 | Docker workspace: Cytoscape loaded | ✅ pass |
| 9 | Docker workspace: dockview panels render | ✅ pass |

## Diagnostics

- **Check build output:** `docker compose exec frontend cat /srv/built-assets/manifest.json | python3 -m json.tool`
- **Check API mode:** `docker compose exec api python -c "from app.template_helpers import is_asset_manifest_available; print(is_asset_manifest_available())"`
- **Check API logs:** `docker compose logs api 2>&1 | grep -i 'asset manifest'`
- **Rebuild assets:** `docker compose build frontend && docker compose up -d --force-recreate frontend && docker compose restart api`
- **Force dev mode:** Set `ASSET_MANIFEST_PATH=/nonexistent` in .env to force CDN fallback

## Deviations

- **Recovered T01-T03 from M027 worktree:** Prior task code existed in `.gsd/worktrees/M027/` but was not committed to the M029/main branch. Copied all files and incorporated them.
- **Shared volume at /srv/built-assets/ instead of /usr/share/nginx/html/assets/:** The plan assumed the named volume could be a sub-mount of the read-only bind mount. Docker rejects this (`read-only file system` error). Used a separate mount point with nginx `alias` directive.
- **Entrypoint script for volume population:** The plan didn't anticipate that Docker named volumes only get populated from image contents on first creation. The entrypoint copies on every start, so rebuilds take effect without `docker compose down -v`.
- **theme.js fix:** Found and fixed a hardcoded CDN URL for hljs theme switching that wasn't in the T03 scope but was necessary for zero-CDN production.
- **API restart required after first deployment:** The API container must restart after the frontend populates the shared volume. This is a one-time step per deployment, not ongoing.

## Known Issues

- **Startup ordering:** On fresh `docker compose up -d`, the API may start before the frontend entrypoint copies assets to the shared volume. A `docker compose restart api` is needed after the first deployment. This could be improved with a depends_on health check or init container pattern.
- **Dockview layout warning:** `saved dockview layout incompatible, rebuilding` appears in console — this is pre-existing (layout format changed between dockview versions) and the app recovers gracefully.

## Files Created/Modified

- `frontend/Dockerfile` — multi-stage build (node:20-alpine → nginx:stable-alpine)
- `frontend/docker-entrypoint.sh` — copies built assets from image to shared volume on each start
- `frontend/nginx.conf` — added /assets/ location block with alias directive
- `docker-compose.yml` — added frontend_assets named volume, build directive for frontend, volume mounts for sharing
- `backend/app/template_helpers.py` — multi-path manifest search (env override → Docker volume → in-container)
- `backend/tests/test_template_helpers.py` — 26 tests updated for multi-path search API
- `backend/app/main.py` — added init_template_helpers(app) call
- `frontend/static/js/theme.js` — hljs theme switcher uses data attributes in production, CDN fallback in dev
- `backend/app/templates/base.html` — conditional vendor/CDN blocks, all app assets use asset_url filter
- `backend/app/templates/base_embed.html` — conditional vendor/CDN blocks, app assets use asset_url
- `backend/app/templates/browser/workspace.html` — conditional dockview local/CDN blocks
- `backend/app/templates/admin/sparql.html` — conditional yasgui local/CDN blocks
- `backend/app/templates/admin/model_detail.html` — conditional chartjs local/CDN blocks
- `backend/app/templates/errors/403.html` — conditional lucide local/CDN blocks
- `frontend/package.json` — npm project with 18 CDN deps + esbuild (from T01)
- `frontend/build.js` — esbuild build script (from T01)
- `frontend/.gitignore` — ignores node_modules/ and dist/ (from T01)
- `frontend/package-lock.json` — lockfile (from T01)
