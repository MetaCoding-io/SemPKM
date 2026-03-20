# Project Knowledge

Append-only register of project-specific rules, patterns, and lessons learned.
Agents read this before every unit. Add entries when you discover something worth remembering.

## Rules

| # | Scope | Rule | Why | Added |
|---|-------|------|-----|-------|

## Patterns

| # | Pattern | Where | Notes |
|---|---------|-------|-------|
| 1 | SPARQL date comparison in rdflib: use `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)` instead of `xsd:date(NOW())` | `models/basic-pkm/rules/basic-pkm.ttl` | rdflib does not support `xsd:date()` cast — produces empty results. The STRDT+SUBSTR approach constructs a proper typed xsd:date literal that compares correctly with xsd:date values in FILTER. |
| 2 | MockResponse default data: use `data if data is not None else {}` not `data or {}` | `backend/tests/test_github_sync_engine.py` | Python `[] or {}` evaluates to `{}` because empty list is falsy. A mock returning `MockResponse(200, [])` silently becomes `{}` which gets iterated as a dict, producing cryptic KeyError failures. |

## Lessons Learned

| # | What Happened | Root Cause | Fix | Scope |
|---|--------------|------------|-----|-------|
| K001 | SHACL-AF stale-contact rule with `?today - "P90D"^^xsd:dayTimeDuration` doesn't work in rdflib's SPARQL engine | rdflib does not implement xsd:dayTimeDuration subtraction from xsd:date | Use `NOT EXISTS` for zero-interaction check in SHACL rules; use SavedQuery with direct date comparison for time-windowed checks | models/crm/rules, any SHACL-AF SPARQL using date arithmetic |
| K002 | Seed data `dcterms:created` with `xsd:dateTime` caused spurious `sh:Violation` when SHACL shape constrains that property to `xsd:date` | SHACL `sh:datatype xsd:date` is strict — `xsd:dateTime` values fail the check even though both represent temporal data | Match the seed data's `@type` to whatever the SHACL shape's `sh:datatype` declares for that property. Check shapes before authoring seed data. | Any model's seed data where shapes constrain date fields |

## E2E Test: SPARQL API Does Not Support UPDATE/DELETE

**Discovery date:** 2026-03-17  
**Context:** T02 E2E Playwright test for mental model expansion  

The `/api/sparql` endpoint (both GET and POST) only executes read queries (SELECT, ASK, CONSTRUCT, DESCRIBE). It does NOT support SPARQL UPDATE operations (INSERT, DELETE). Sending a DELETE query returns `400 Malformed SPARQL query`.

The triplestore client (`app.triplestore.client.TriplestoreClient`) has an `update()` method that works, but it's not exposed through any HTTP API endpoint.

**Impact:** E2E tests cannot clean up triplestore data (seed instances, created objects) via the API. Model uninstall is blocked when seed data exists because `check_user_data_exists()` queries `urn:sempkm:current` graph and finds instances.

**Workaround:** Make cleanup best-effort with skip-if-already-installed logic for idempotent reruns. For a proper fix, add a SPARQL UPDATE endpoint or a force-uninstall admin API.

## E2E Test: Docker Test Stack Volume Mounts From Worktree

**Discovery date:** 2026-03-17  
**Context:** T02 E2E Playwright test for mental model expansion  

The Docker test stack (docker-compose.test.yml) started from `.gsd/worktrees/M007/` mounts volumes from that worktree path, not from the main tree at `/home/james/Code/SemPKM/`. For example, `./models:/app/models:ro` resolves to `.gsd/worktrees/M007/models/`.

If model directories only exist in the main tree (e.g., after a T01 task copies them there), they must also be copied to the worktree's `models/` directory for the Docker container to see them.

**Check:** `docker inspect <container> --format '{{json .Mounts}}'` shows the resolved source paths.

## ninja-keys: Parent `children` Array Must List Child IDs

**Discovery date:** 2026-03-17  
**Context:** M012/S03/T03 — Command palette persona submenu

In ninja-keys, a parent command with `children: []` (empty array) does NOT auto-discover children by their `parent` property. The `children` array on the parent must contain the actual child IDs (e.g., `['persona-switch-abc123']`) for drill-down navigation to work. The `parent` property on children is only for breadcrumb display.

**Pattern:** When using `_refreshPersonaPaletteItems` or similar async population functions, always update both the child items' `parent` property AND the parent's `children` array with the child IDs.

## Cross-IIFE Guard Flags via window

**Discovery date:** 2026-03-17  
**Context:** M012/S03/T03 — workspace.js ↔ workspace-layout.js guard flag

`workspace.js` and `workspace-layout.js` are separate IIFEs. Variables declared inside one are not accessible from the other. To share a guard flag (like `_switchingPersona`), set it on `window` (e.g., `window._switchingPersona = true`) and check via `window._switchingPersona` in the other file.

## SPARQL API scopes to current state graph only

The `/api/sparql` endpoint (`backend/app/sparql/router.py`) calls `scope_to_current_graph()` which rewrites queries to only access `GRAPH <urn:sempkm:current>`. Event data lives in per-event named graphs (e.g. `urn:sempkm:event:abc123`) and is intentionally excluded to prevent data leakage.

**Consequence:** E2E tests cannot use the SPARQL API to query event metadata (operation types, affected IRIs). Use the event log UI or the event detail API endpoint (`/browser/events/{iri}/detail`) instead.

## Body save endpoint is POST not PUT

The save body endpoint is `POST /browser/objects/{encoded_iri}/body` with `Content-Type: text/plain` body. The task plan incorrectly specified PUT. The actual route is defined in `backend/app/browser/objects.py` as `@objects_router.post("/objects/{object_iri:path}/body")`.

## JSON API paths outside /api/ need _is_html_route exclusion

**Context:** `backend/app/main.py` has a `_is_html_route()` function that determines whether 401 errors should be returned as JSON or converted to 302 login redirects. It originally only excluded paths starting with `/api/`.

**Problem:** The `/.well-known/sempkm` discovery endpoint lives outside `/api/` but returns JSON. Without adding it to the exclusion list, unauthenticated requests got 302 redirects to `/login.html` instead of JSON `{"detail": "Not authenticated"}`.

**Rule:** Any new JSON API endpoint mounted outside the `/api/` prefix must also be excluded in `_is_html_route()`. Current exclusions: `/api/`, `/.well-known/`.

## SQLite naive datetimes vs timezone-aware Python datetimes

**Discovery date:** 2026-03-18
**Context:** M009/S07/T03 — App platform E2E test

SQLite stores datetimes without timezone info (naive). When Python code uses `datetime.now(timezone.utc)` to compute a timedelta against a SQLite-sourced value, it crashes with `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Fix:** Before subtracting, check `if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)`. Applied in `AppManager.get_status()` for `instance.started_at`.

## Workspace explorer sections start collapsed

**Discovery date:** 2026-03-18
**Context:** M009/S07/T03 — App platform E2E test

The workspace sidebar explorer sections (FAVORITES, OBJECTS, VIEWS, DASHBOARDS, APPS, etc.) use a custom CSS toggle — the section needs `.expanded` class to show its body. They are NOT `<details>` elements. The section header has `onclick="this.parentElement.classList.toggle('expanded')"`.

**Impact on E2E tests:** After navigating to `/browser/`, the APPS section body content loads via htmx `hx-trigger="load"` but is hidden because the section is collapsed. Tests must click the section header to expand it before asserting on child content.

## E2E tests: Docker stack must run from main tree for auth fixture

**Discovery date:** 2026-03-18
**Context:** M009/S07/T03 — App platform E2E test

The Playwright auth fixture (`e2e/fixtures/auth.ts`) reads the setup token via `docker compose -f docker-compose.test.yml exec -T api cat ...` with `cwd` set to `git rev-parse --show-toplevel` (the main tree). If the Docker stack is started from a worktree, the auth fixture can't find the container because Docker Compose uses project-name scoping based on the directory.

**Workaround:** Either (a) sync worktree code to main tree and run Docker from main tree, or (b) start Docker from worktree AND update the auth fixture to use the worktree's compose file path.

## Playwright extension tests: chrome.storage.sync unreliable in persistent context

**Discovery date:** 2026-03-18
**Context:** M014/S05/T02 — E2E extension tests

When using `chromium.launchPersistentContext()` with `--load-extension`, settings saved via `chrome.storage.sync` on the options page may not be visible when the popup page loads in a new tab. The popup sees the "unconfigured" state even though the options page saved successfully.

**Fix:** Inject settings directly into `chrome.storage.local` via `page.evaluate()` on an extension page before navigating to the popup. The extension's `storage.js` has fallback from sync to local, so this works reliably.

## Playwright extension tests: SHACL form required fields block native form validation

**Discovery date:** 2026-03-18
**Context:** M014/S05/T02 — E2E extension tests

The SHACL renderer sets `required` on input elements, including those inside collapsed sections (RELATIONSHIPS, METADATA). When the form is submitted via button click, native browser validation fires before the JS `handleSave()` runs, and fails with "An invalid form control with name='' is not focusable" because the required fields are hidden.

**Fix:** Set `form.noValidate = true` via `page.evaluate()` before clicking the Save button. The extension's `handleSave()` does its own validation.

## Playwright extension tests: persistent context hangs navigating non-extension pages

**Discovery date:** 2026-03-18
**Context:** M014/S05/T02 — E2E extension tests

Navigating to `http://localhost:3901/browser/` in a page opened within the extension's persistent context can hang indefinitely (even with `waitUntil: 'domcontentloaded'`). The workspace page has SSE/long-polling connections that may interact poorly with the persistent context. Use API-only verification (SPARQL query) instead of UI verification for objects created via the extension.

## App template htmx URLs must use proxy prefix

**Discovery date:** 2026-03-18
**Context:** M016/S04/T01 — Linear Sync E2E test

App templates rendered by the SDK's `render_template()` are loaded into the workspace page via the proxy chain at `/app/{app_id}/_fragments/{fragment}`. However, htmx attributes inside those templates (e.g. `hx-post="/_fragments/connect/api-key"`) use absolute paths that bypass the proxy — the browser sends them directly to the origin, where no platform route matches `/_fragments/*`.

**Fix:** All htmx URLs in app templates must be prefixed with `/app/{app_id}/` so requests route through the `app_proxy_router` catch-all at `/app/{app_id}/{path:path}`. Example: `hx-post="/app/linear-sync/_fragments/connect/api-key"`.

**Impact:** Any future app that uses htmx forms in its templates must follow this pattern. A better long-term fix would be to inject the prefix via a Jinja2 global or context variable from the SDK.

## User guide has THREE files that must stay in sync

**Discovery date:** 2026-03-19
**Context:** M024 — Monday.com Sync App

There are **three** places that list user guide chapters:

1. `docs/guide/README.md` — markdown table of contents (source of truth)
2. `docs/guide/index.html` — static HTML sidebar for the standalone docs site
3. `backend/app/templates/guide.html` — in-app Docs & Tutorials page served at `/guide`

When adding a new chapter (e.g., a sync app guide), all three files must be updated together. The in-app `guide.html` was missed for chapters 25–36 because it's a Jinja2 template with hardcoded `<button>` elements — not auto-generated from README.md.

**Rule:** Any milestone that adds a user-guide chapter must update all three files. The docs update task should be part of the final slice or a dedicated docs slice.

---

### FastAPI Depends() Executes Before Function Body (D249, M025/S01/T01)

**Problem:** If a dependency function uses `token: str = Depends(get_session_token)` and `get_session_token` raises 401 when no cookie is present, a `settings.demo_mode` check in the function body never runs — FastAPI resolves all `Depends()` arguments *before* entering the function.

**Solution:** Replace the dependency chain with an optional parameter: `sempkm_session: str | None = Cookie(None)`. Then check `settings.demo_mode` as the first line. If not in demo mode, manually check for None and raise 401.

**Rule:** When adding a bypass/override at the top of a dependency function, verify that no `Depends()` parameter can raise before the function body runs. If it can, inline the parameter extraction.

### Container-side scripts need sys.path fix for app imports (M025/S02/T02)

**Problem:** Python scripts mounted at `/app/scripts/` via Docker volume cannot import the `app` package because `/app` is not on `sys.path`. The default path only includes `/app/.venv/lib/...` and the script's own directory. Running `python /app/scripts/seed-demo-data.py` fails with `ModuleNotFoundError: No module named 'app'`.

**Fix:** Add this block before any `from app.* import ...` statements:
```python
_app_root = str(Path(__file__).resolve().parent.parent)
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)
```

**Rule:** Any new script under `scripts/` that imports from the `app` package must include this sys.path manipulation. FastAPI's uvicorn process doesn't need it because its working directory is `/app/`.
