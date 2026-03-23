# Project Knowledge

Append-only register of project-specific rules, patterns, and lessons learned.
Agents read this before every unit. Add entries when you discover something worth remembering.

## Rules

| # | Scope | Rule | Why | Added |
|---|-------|------|-----|-------|
| R01 | git / GSD | **Never use worktree isolation mode.** Use `taskIsolation.mode: branch` or `none` in `.gsd/preferences.md`. | Worktree mode caused catastrophic data loss 3+ times: code was built in `.gsd/worktrees/<MID>/`, only `.gsd/` artifacts were committed to main, the worktree was cleaned up, and source code was permanently lost. M009-M010 lost the entire App Platform + RSS Reader. M019-M022 lost 4 sync apps. M027-M028 lost Notion Import + AI Features. ~115 files across 8 milestones were only recoverable from dangling git objects. | 2026-03-21 |
| R02 | git / GSD | **After every milestone or slice completion, verify source files exist on the integration branch.** Run: `git diff --stat HEAD~1` and confirm non-`.gsd/` files are present. If a commit only touches `.gsd/` files, the code was not merged. | The auto-commit mechanism commits `.gsd/` planning artifacts but does NOT commit source code from worktrees. This silent failure looks like a successful completion. | 2026-03-21 |
| R03 | git | **Never run `git gc` or `git prune` without first auditing dangling commits.** Run `git fsck --lost-found` and check for source files before allowing garbage collection. | Dangling commits are the last line of defense for unmerged worktree code. Once garbage-collected, the code is permanently gone. | 2026-03-21 |
| R04 | GSD / roadmap | **Roadmap `## Slices` section must use checkbox format, not heading format.** Correct: `- [ ] **S01: Title** \`risk:level\` \`depends:[]\``. Wrong: `### S01: Title` with bullet metadata. The auto-mode dispatcher parses checkbox lines to find eligible slices — heading-style slices are invisible to it, causing "No slice eligible" even when slices exist. | Blocked auto-mode dispatch for 5+ consecutive attempts on M033. The planner generated `### S01:` headings instead of `- [ ] **S01:**` checkboxes. | 2026-03-21 |
| R05 | git / GSD | **After every auto-mode commit, verify no source files were deleted.** Run: `git diff-tree --no-commit-id -r --diff-filter=D HEAD` and confirm zero non-`.gsd/` deletions. If the commit deleted source files, recover immediately from the parent commit. | Auto-mode commit 99e585b1 ("M030 E2E test suite") silently deleted 26 source files from 6 prior milestones (M010, M018-M022, M027, M028) including the entire rss-feeds model, 7 mock API servers, 8 E2E specs, the Notion import executor, and the AI router. The agent's `git add -A` captured a working tree state that was missing files from earlier recovery commits. The deletion was invisible — the commit message described only what was *added*, not what was removed. | 2026-03-21 |
| R06 | git / GSD | **Never use `git add -A` or `git add .` in auto-mode commits.** Use `git add <specific-files>` listing only the files the current task created or modified. | `git add -A` stages the entire working tree, including deletions of files the agent never touched. If the working tree is missing files (e.g., from a prior session's recovery that wasn't in the current checkout), they get silently deleted from the repository. This is how 99e585b1 destroyed 26 files — the agent added its 7 new test files but `git add -A` also staged the removal of 26 unrelated files. | 2026-03-21 |
| R07 | GSD / parallel | **Never use parallel auto-mode (`parallel.enabled: true`) with `git.isolation: "none"`.** Workers share the same `.gsd/` directory and can write artifacts for milestones they don't own. `GSD_MILESTONE_LOCK` only filters what `deriveState()` sees — it does NOT prevent file writes. A parallel worker can fabricate SUMMARY, VALIDATION, and slice/task summaries for another milestone, marking it "complete" when no real code was built. | The M033 worker created M032's entire completion artifact tree (SUMMARY, VALIDATION, S01-S03 summaries, T01-T03 summaries) in commit dc723e25, skipping M032 entirely. M032 had to be manually reopened. | 2026-03-22 |

## Patterns

| # | Pattern | Where | Notes |
|---|---------|-------|-------|
| 1 | SPARQL date comparison in rdflib: use `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)` instead of `xsd:date(NOW())` | `models/basic-pkm/rules/basic-pkm.ttl` | rdflib does not support `xsd:date()` cast — produces empty results. The STRDT+SUBSTR approach constructs a proper typed xsd:date literal that compares correctly with xsd:date values in FILTER. |
| 2 | MockResponse default data: use `data if data is not None else {}` not `data or {}` | `backend/tests/test_github_sync_engine.py` | Python `[] or {}` evaluates to `{}` because empty list is falsy. A mock returning `MockResponse(200, [])` silently becomes `{}` which gets iterated as a dict, producing cryptic KeyError failures. |
| 3 | Never embed N-Triples in SPARQL INSERT DATA for RDF4J — use `insert_graph()` with Graph Store protocol instead | `backend/app/services/validation.py`, `backend/app/triplestore/client.py` | rdflib N-Triples blank node IDs (e.g. `_:n333f21aad...`) cause RDF4J SPARQL parser to error with "Not a valid (absolute) IRI". The Graph Store protocol (POST with `Content-Type: text/turtle` to `/statements?context=<graph>`) bypasses SPARQL parsing entirely. |
| 4 | `_rdf_term_to_sparql` must handle `BNode` explicitly — rdflib `str(BNode())` returns the raw ID without `_:` prefix | `backend/app/services/validation.py` | BNode identifiers like `nf943a8d5...` look like relative IRIs when wrapped in `<...>`. Always check `isinstance(term, BNode)` and format as `_:{id}`. |
| 5 | Adding a new quadrant framework requires 6 coordinated edits | `backend/app/views/service.py`, `models/business-planning/` | (1) Add entry to `_QUADRANT_LABELS` dict keyed by framework id with 4 label tuples, (2) add keyword pair to `_AXIS_KEYWORD_PAIRS` for axis detection, (3) ontology classes (container + item), (4) SHACL shapes with exactly 2 `sh:in` properties of length 2, (5) ViewSpecs declaring `quadrant` renderer, (6) manifest icon entries. Missing any one causes silent failures (no labels, no axis detection, no view). |
| 6 | Adding a new custom renderer requires 4-layer wiring | `backend/app/views/{registry,router,service}.py`, templates, JS, CSS | (1) Add renderer name to `RENDERER_REGISTRY` dict in registry.py, (2) add to `_VALID_RENDERERS` set in router.py, (3) add elif branches in `generic_view()` and `generic_view_data()`, (4) add `_detect_*`, `_build_*_select`, `execute_*_query` methods to ViewSpecService, (5) create Jinja2 template + JS + CSS. Proven across 4 renderers (quadrant, bmc, okr, decision-matrix). The `register_renderer()` infrastructure exists but is dead code — activating it would eliminate steps 1-3. |

## Lessons Learned

| # | What Happened | Root Cause | Fix | Scope |
|---|--------------|------------|-----|-------|
| K001 | SHACL-AF stale-contact rule with `?today - "P90D"^^xsd:dayTimeDuration` doesn't work in rdflib's SPARQL engine | rdflib does not implement xsd:dayTimeDuration subtraction from xsd:date | Use `NOT EXISTS` for zero-interaction check in SHACL rules; use SavedQuery with direct date comparison for time-windowed checks | models/crm/rules, any SHACL-AF SPARQL using date arithmetic |
| K002 | Seed data `dcterms:created` with `xsd:dateTime` caused spurious `sh:Violation` when SHACL shape constrains that property to `xsd:date` | SHACL `sh:datatype xsd:date` is strict — `xsd:dateTime` values fail the check even though both represent temporal data | Match the seed data's `@type` to whatever the SHACL shape's `sh:datatype` declares for that property. Check shapes before authoring seed data. | Any model's seed data where shapes constrain date fields |
| K003 | Worktree isolation mode lost source code for 8 milestones (~115 files). Code was built in worktrees, only `.gsd/` artifacts committed to main, worktrees cleaned up. Files survived only as dangling git objects. | GSD auto-mode commits `.gsd/` state files to main but source code lives in the worktree on a `milestone/<MID>` branch. When the worktree is removed and the branch deleted, source code becomes unreachable (dangling). | (1) Set `taskIsolation.mode: none` in preferences. (2) Recovered all files from dangling commits via `git fsck --lost-found` + `git checkout <hash> -- <path>`. (3) Added Rules R01-R03 to prevent recurrence. | All milestones using worktree mode |
| K004 | Auto-mode dispatch stuck on "No slice eligible" for 5+ runs. All task code and summaries were correct but dispatch couldn't find any slice to execute. | The planner agent wrote the roadmap's `## Slices` section with `### S01: Title` markdown headings instead of the `- [ ] **S01: Title** \`risk:level\` \`depends:[]\`` checkbox format. The dispatcher regex only matches the checkbox format. | Rewrote the Slices section to use checkbox format. Added Rule R04 to KNOWLEDGE.md. The real fix is a validation step between planning output and dispatch — either the planner's system prompt enforces it harder, or a post-planning lint checks the roadmap format. | Any milestone roadmap planning |
| K005 | Auto-mode commit 99e585b1 silently deleted 26 source files from 6 prior milestones (M010, M018-M022, M027, M028). Deleted files included the rss-feeds Mental Model (4 files), 7 mock API servers, 8 E2E specs, the Notion import executor, AI router, and test fixtures. The deletion was only discovered weeks later during a planning audit. | The auto-mode agent used `git add -A` (or equivalent whole-tree staging) for its M030/S04 commit. The agent's working tree was missing files from earlier recovery sessions — likely because the agent's session started fresh and didn't have those files checked out. `git add -A` stages deletions for any tracked file absent from the working tree, so the commit silently removed 26 files the agent never intended to touch. | (1) Recovered all 26 files: 3 from commit a35c9e91 (M028 recovery), 6 from a35c9e91 (M027 recovery), 17 from ca981b55 (parent of destructive commit). (2) Added Rules R05-R06 to prevent recurrence. (3) Key insight: this is a *different* failure mode from K003 worktrees — these files were on main and were committed, then silently deleted by a later commit. The safeguard is never using `git add -A` in auto-mode. | All auto-mode commits; verification should check for unexpected deletions |
| K006 | Parallel auto-mode (M032+M033) caused M032 to be skipped. The M033 worker's "complete-milestone" unit committed fabricated M032 artifacts (SUMMARY, VALIDATION, all slice/task summaries) claiming M032 was done. Auto-mode then advanced to M033 tasks, researched M034, and only returned to M032 after manual intervention. | Workers with `git.isolation: "none"` share the `.gsd/` directory. `GSD_MILESTONE_LOCK` filters `deriveState()` visibility but doesn't restrict file writes. The completing-milestone prompt or the agent itself generated M032 planning artifacts and committed them alongside M033's own artifacts in a single `git add -A` commit (dc723e25). | (1) Disabled parallel mode (`parallel.enabled: false`). (2) Manually deleted fabricated M032 terminal artifacts (SUMMARY, VALIDATION, S02/S03 summaries). (3) Re-opened M032 S02+S03 in the roadmap. (4) Added Rule R07. Parallel mode needs filesystem-level write isolation per worker before it can be safely re-enabled. | Parallel mode with shared .gsd/ directory |

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

---

### pyshacl: `allow_warnings=True` means warnings don't affect `conforms`

**Discovered:** M030/S01/T02

When calling `pyshacl.validate(..., allow_warnings=True)`, the `conforms` return value stays `True` even when sh:Warning validation results are present. Warnings are captured in the results graph but don't cause non-conformance.

**Implication:** To detect if any warnings fired, you must inspect the results graph for `sh:ValidationResult` triples with `sh:resultSeverity sh:Warning`. Do NOT rely on `conforms is False`.

```python
# Correct: check results graph
for node in results_graph.subjects(RDF.type, SH.ValidationResult):
    severity = list(results_graph.objects(node, SH.resultSeverity))
    if any(str(s) == str(SH.Warning) for s in severity):
        # Warning found

# Wrong: conforms is True even with warnings
assert conforms is False  # FAILS when allow_warnings=True
```

---

### basic-pkm shapes are JSON-LD, not Turtle

**Discovered:** M030/S01/T02

The shapes file for basic-pkm is at `models/basic-pkm/shapes/basic-pkm.jsonld` (JSON-LD), not `.ttl`. The rules file IS Turtle at `models/basic-pkm/rules/basic-pkm.ttl`. When loading both into a combined graph:

```python
combined = Graph()
combined.parse("models/basic-pkm/shapes/basic-pkm.jsonld", format="json-ld")
combined.parse("models/basic-pkm/rules/basic-pkm.ttl", format="turtle")
```

---

### extract_scope_where_body() LIMIT clause edge case

**Discovered:** M031/S01/T03

`extract_scope_where_body()` uses an end-of-string regex (`\}\s*$`) to find the WHERE block's closing brace. Saved queries with `LIMIT`, `ORDER BY`, or other clauses after the closing brace return empty string — the regex doesn't match.

**Implication:** Callers should strip LIMIT/ORDER BY from the saved query text before passing to `extract_scope_where_body()`. The router's `_extract_where_body()` (brace-depth-counting version) handles these clauses correctly for query execution, but the scope injection utility does not.

```python
# Works: SELECT ?s WHERE { ?s a ex:Project }
extract_scope_where_body("SELECT ?s WHERE { ?s a ex:Project }")  # → "?s a ex:Project"

# Returns empty: SELECT ?s WHERE { ?s a ex:Project } LIMIT 10
extract_scope_where_body("SELECT ?s WHERE { ?s a ex:Project } LIMIT 10")  # → ""
```

---

### model_view_specs replaces all_specs in view templates

**Discovered:** M031/S01/T01

After carousel removal, view templates receive `model_view_specs` (only model-declared ViewSpecs for the active type) instead of the old `all_specs` (which merged generic + model-declared specs). The template guard is:

```jinja2
{% if model_view_specs is defined and model_view_specs | length > 0 %}
```

Dedicated view endpoints (`table_view()`, `cards_view()`, `graph_view()`) pass `model_view_specs: []` since they already serve a specific model-declared view. Only `generic_view()` populates this from `get_view_specs_for_type()`.

---

### PromotedViewData fields must use OPTIONAL SPARQL when listing

**Discovered:** M031/S02/T02

When extending `PromotedViewData` with new fields (`type_filter`, `scope_query_id`), the `list_promoted_views()` SPARQL must wrap all new predicates in OPTIONAL clauses. Without OPTIONAL, views saved without those fields (e.g., older query-based promoted views) are excluded from results entirely — the SPARQL pattern match fails if the triple doesn't exist.

This also applies to the original `fromQuery` predicate — making it OPTIONAL was necessary so generic saved views (which have no associated query) appear in the listing.

---

### Two-path pattern for saved views: generic vs. query-based

**Discovered:** M031/S02/T02

The Saved Views folder (`my_views.html`) needs two distinct code paths:
1. **Query-based promoted views** (created via "Pin as Saved View" on a saved query): use `openViewTab()` and `demoteView()` for unpin
2. **Generic saved views** (created via "Save View" toolbar button): use `openGenericViewTab(renderer, scopeQuery)` and `deleteSavedView()` for unpin

The distinguishing signal is whether the PromotedViewData has a `renderer_type` field — generic saves always have one; query-based promotions derive renderer from the ViewSpec.

---

### HTML5 drag-drop inside dockview panels needs stopPropagation()

**Discovered:** M031/S04/T02

dockview's panel drag system intercepts HTML5 drag events that bubble up from child elements. Any custom drag-drop UI within a dockview panel (kanban columns, sortable lists, etc.) must call `e.stopPropagation()` on `dragstart`, `dragover`, and `drop` handlers to prevent dockview from treating the drag as a panel detach/reorder operation. This is the same pattern as canvas resize handles (D127/CANVAS-01).

---

### dragLeave flicker prevention with contains(relatedTarget)

**Discovered:** M031/S04/T02

When implementing drag-over highlighting on a container element, the `dragleave` event fires when the cursor moves between child elements *within* the container — not just when it actually leaves. This causes the drag-over CSS class to flicker. Fix: check `e.currentTarget.contains(e.relatedTarget)` in the `dragleave` handler and only remove the highlight class when the cursor truly leaves the container.

```javascript
function onDragLeave(e) {
    if (e.currentTarget.contains(e.relatedTarget)) return; // still inside
    e.currentTarget.classList.remove('kanban-col-drag-over');
}
```

---

### Kanban status field detection uses SHACL sh:in, not hardcoded field names

**Discovered:** M031/S04/T01

`_detect_status_field()` scans all SHACL PropertyShapes for the type and finds the first with non-empty `sh:in` values, preferring properties with "status" in the path (case-insensitive). This is more general than the D286 planning decision which suggested hardcoding to `bpkm:taskStatus`. Any Mental Model type that adds `sh:in` enum constraints on a property will automatically work with the kanban view.

---

### Kanban test_kanban.py must run from backend/ directory

**Discovered:** M031/S04/T01

`pytest tests/test_kanban.py` must be run from the `backend/` directory (`cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v`), not from the project root. The root `.env` file contains `LINEAR_API_KEY` which is rejected as an extra field by the Pydantic Settings model, causing import failures.

### Views needing full-height must use .view-flex-column wrapper — not calc()

**Discovered:** M031/S05/T04

Graph and kanban views used fragile `height: calc(100% - 90px)` which breaks when toolbar height changes. The fix is a shared `.view-flex-column` class (flex column, height:100%) with `flex:1; min-height:0` on the expandable child. Table/cards views don't need this — they use natural scrolling. Any new view type that must fill its panel should use this wrapper.

### Popovers inside dockview panels must escape stacking context via document.body

**Discovered:** M031/S05/T04

Any popover rendered inside a dockview panel is trapped in the panel's stacking context (position:relative). Elevating z-index won't help because dockview chrome has its own stacking context. The only reliable fix is `document.body.appendChild(popover)` with `position:fixed` and `getBoundingClientRect()` for positioning. Always add cleanup to remove the popover from body when the parent view/graph is destroyed.

### SPARQL vocab prefix exclusion: use specific sub-namespace allow-list, not broad prefix

**Discovered:** M031/S05/T01

The `_VOCAB_PREFIXES` tuple in `sparql/router.py` and the matching `KNOWN_VOCAB_PREFIXES` in `sparql-console.js` must list specific internal namespaces (urn:sempkm:query:, urn:sempkm:user:, etc.), NOT the broad `urn:sempkm:`. The broad entry caused all model ontology IRIs to be treated as vocabulary, preventing pill rendering. When adding a new internal namespace, add it to both backend and frontend lists.

---

### Builder autocomplete pattern: reference-field with hidden data-key input

**Discovered:** M031/S06/T02

IRI fields in dashboard/workflow builders use a `.reference-field` wrapper containing three elements: (1) a visible search `<input>` for user typing, (2) a hidden `<input data-key="field_name">` that stores the actual IRI value, and (3) a `.suggestions-dropdown` div. A shared helper function (`_builderAutocomplete(inputEl, endpoint)`) handles 300ms debounce, fetch, rendering, click-to-select, and click-outside dismiss. The save collector (`querySelectorAll('[data-key]')`) picks up the hidden input automatically. When adding new IRI fields to builders, follow this pattern rather than using plain text inputs.

### Verification grep checks: beware CSS class substring matches

**Discovered:** M031/S06/T01

When slice verification uses `grep -c 'some-class'` to verify a class is absent, any new class containing that string as a substring will create a false positive. T01 hit this with `step-config-renderer-auto` matching the `step-config-renderer` absence check. Solution: name replacement classes to avoid the substring (e.g., `wf-auto-renderer` instead of `step-config-renderer-auto`).

---

### E2E view selectors belong in SEL.views, not inline

**Discovered:** M031/S07/T01

All view-related E2E selectors (kanbanBoard, kanbanColumn, kanbanCard, scopeSelect, variantSelect, saveViewBtn) are centralised in `SEL.views` in `e2e/helpers/selectors.ts`. Future view tests should add selectors here rather than inlining CSS class strings in test files. This avoids selector drift when CSS classes change — update one place instead of hunting through specs.

### E2E: use openGenericViewTab helper, not UI clicks, to open view tabs

**Discovered:** M031/S07/T01

Opening view tabs in E2E tests should use the `openGenericViewTab(page, renderer, waitSelector, ...)` helper in `e2e/helpers/dockview.ts`, which calls `window.openGenericViewTab()` via `page.evaluate()` then waits for a DOM selector. This is more reliable than clicking through the explorer sidebar (which involves loading htmx partials, waiting for dockview panel creation, etc.). Timeout failures from this helper directly indicate whether the JS API or DOM rendering is broken.

---

### Planning estimates can be safely exceeded when the cost is marginal

**Discovered:** M031/S04

D286 (planning) called for hardcoding `bpkm:taskStatus` as the kanban status field. D291 (implementation) upgraded to general SHACL `sh:in` scan for ~20 extra lines. The SHACL approach is strictly better — supports any model type automatically — for negligible extra cost. When the implementation reveals a low-cost generalization that the plan didn't envision, prefer the better approach. Document the divergence in the decision log (D291 references D286).

### Dockview stacking context escape: always append to document.body

**Discovered:** M031/S05/T04

Any popover, tooltip, or overlay rendered inside a dockview panel is trapped in that panel's stacking context. Elevating `z-index` within the panel cannot escape the panel boundary. The only reliable approach is appending the element to `document.body` with `position:fixed` and computing coordinates via `getBoundingClientRect()`. Always register cleanup (e.g., `registerCleanup` callback) to remove body-appended elements when the panel is destroyed. This applies to graph popovers (D293), and will apply to any future hover card, context menu, or overlay inside dockview.

### data-sparql-loaded / data-chart-loaded are dedup guards, not readiness signals

**Discovered:** M032/S03/T01

`_executeSparqlWidgets()` sets `data-sparql-loaded="1"` on the element *before* calling `fetch('/api/sparql', ...)`. Similarly, `_initChartBlocks()` sets `data-chart-loaded="1"` before the Chart.js CDN load and SPARQL fetch. These attributes prevent re-execution on htmx re-swaps, but they do NOT indicate the async work has completed.

**Impact on E2E tests:** Waiting for `[data-sparql-loaded]` or `[data-chart-loaded]` to appear does not guarantee the content is ready. For stat-cards, wait until `[data-stat-target]` text is no longer "…" (the loading placeholder). For charts, wait until `Chart.getChart(canvas)` returns truthy or the canvas `toDataURL()` exceeds ~500 chars (non-blank).

### @slot:name convention for cross-command IRI references in batch payloads

**Discovered:** M032/S01/T01

The batch command endpoint (`POST /api/commands`) supports `@slot:name` references for cross-command dependencies. An `object.create` command with a `slot` field registers its minted IRI in a `slot_map`. Subsequent commands (e.g., `edge.create`) can use `@slot:slotName` as a value — the router resolves it to the actual IRI before execution. Unresolved references return HTTP 400.

**Pattern:** Commands execute sequentially. The `slot_map` accumulates as commands succeed. Order matters — a command referencing `@slot:X` must appear after the command that defines slot `X`.

```python
# In commands/router.py
slot_map = {}
for cmd in batch:
    if cmd.type == "object.create" and cmd.params.slot:
        slot_map[cmd.params.slot] = minted_iri
    # Resolve @slot: references in subsequent commands
    if value.startswith("@slot:"):
        resolved = slot_map.get(value[6:])
```

**Use beyond form-groups:** The convention is generic — any batch payload can use it. Future features (templates, import wizards, automation) that need to create linked objects in one API call can use `@slot:name` references.

### Cytoscape CSS 3D transforms require coordinate correction monkey-patch

**Discovered:** M033/S02/T02

Applying CSS 3D transforms (e.g., `perspective(800px) rotateX(55deg) rotateZ(-45deg)`) to a Cytoscape container causes click events to land on wrong nodes — the browser reports mouse coordinates in transformed screen space but Cytoscape expects untransformed coordinates. This is Cytoscape issue #1756.

**Fix:** Monkey-patch `cy.renderer().findContainerClientCoords` to apply the inverse DOMMatrix transform before Cytoscape processes click positions. For popover positioning, apply the forward DOMMatrix transform to convert Cytoscape model coordinates back to screen coordinates.

**Fragile:** The monkey-patch must be reapplied after layout changes. The DOMMatrix positioning assumes the transform is on `#cy-wrapper` — if the DOM hierarchy changes, popovers will misposition.

### CDN lazy-loading pattern for heavy JS libraries in view templates

**Discovered:** M033/S03/T02, M033/S04/T02

View templates that depend on heavy third-party libraries (FullCalendar 6.1.17 = ~400KB, Leaflet 1.9.4 + MarkerCluster 1.5.3 = ~200KB) use CDN lazy-loading: the template includes `<script>` tags with pinned CDN URLs, and the library is only fetched when the view tab is opened. This avoids bloating the initial workspace load.

**Risk:** CDN outage breaks these views entirely. The M029 vendor pipeline could absorb these libraries to eliminate the CDN dependency. Versions are pinned in the HTML templates — update requires editing the template file.

**Files:** `backend/app/templates/browser/calendar_view.html`, `backend/app/templates/browser/map_view.html`

### SHACL field detection heuristic: sh:datatype + well-known path IRI

**Discovered:** M033/S03/T01, M033/S04/T01

`_detect_date_fields()` and `_detect_geo_fields()` in `ViewSpecService` use a dual heuristic: (1) check SHACL PropertyShape `sh:datatype` (e.g., `xsd:date`, `xsd:dateTime`) and (2) match the `sh:path` IRI against a well-known list (e.g., `dcterms:date`, `schema:startDate`, `wgs84:lat`). This catches types that declare date/geo fields but use non-standard IRIs, and types that use standard IRIs but don't specify `sh:datatype`.

**Pattern:** Any future field-type-dependent renderer (timeline, gantt, etc.) should follow the same dual heuristic. The detection functions are on `ViewSpecService` and return structured results (field path IRIs + detected labels).

### Timeline _detect_date_fields priority: scheduledStart beats dueDate

**Discovered:** M034/S02/T03

The `_START_DATE_PRIORITY` list in `_detect_date_fields()` is `["scheduledstart", "startdate", "duedate", "targetdate", "created"]`. For the basic-pkm Task shape, which defines both `bpkm:scheduledStart` (xsd:dateTime) and `bpkm:dueDate` (xsd:date), the timeline SPARQL uses `scheduledStart` as the start field. Seed data tasks only populate `dueDate`, so the timeline view appears empty for seed tasks.

**Impact on E2E tests:** Tests that need tasks visible in the timeline must create tasks with `bpkm:scheduledStart` values, not `bpkm:dueDate`. The `createTask()` helper in `e2e/tests/02-views/timeline.spec.ts` demonstrates this pattern.

### Playwright SVG element visibility: use state:'attached' not toBeVisible

**Discovered:** M034/S02/T03

Frappe Gantt renders dependency arrows as `<g class="arrow">` SVG group elements. Playwright's visibility check reports these as "hidden" (`locator resolved to hidden <g class="arrow"></g>`) even when the arrows render visually in the browser. SVG group elements don't have intrinsic dimensions that Playwright can measure.

**Fix:** Use `page.waitForSelector('.arrow', { state: 'attached' })` instead of the default `{ state: 'visible' }`. Then assert count > 0 via `.count()`. This applies to any SVG sub-element (groups, paths, etc.) inside third-party charting libraries.

### Jinja2 dict key access: use col['items'] not col.items

**Discovered:** M034/S03/T03

In Jinja2, `col.items` on a Python dict resolves to the dict's `.items()` method (attribute lookup), not the `items` key. This caused `kanban_view.html` to crash with `TypeError: object of type 'builtin_function_or_method' has no len()` when the template used `{{ col.items | length }}` and `{% for item in col.items %}`.

**Fix:** Use bracket notation `col['items']` for dict key access when the key name collides with a dict method (`items`, `keys`, `values`, `get`, `update`, etc.). This is a Jinja2-specific gotcha — Python code `col["items"]` and `col.items` (via __getattr__) behave differently in Jinja2's attribute resolution order.

**Affected file:** `backend/app/templates/browser/kanban_view.html`

### python-dateutil rruleset.between() requires consistent naive/aware datetimes

**Discovered:** M034/S04/T02

`dateutil.rrule.rruleset.between(start, end)` raises `TypeError: can't compare offset-naive and offset-aware datetimes` if `start`/`end` are timezone-aware but the `dtstart` used in the rule is naive (or vice versa). RDF date/dateTime values parsed via `fromisoformat()` may be naive or aware depending on whether they include a `Z` suffix.

**Fix:** In the RRULE expansion code, strip timezone info from all datetimes before passing to rruleset: `dt.replace(tzinfo=None)`. The expansion window is computed as `datetime.now(timezone.utc).replace(tzinfo=None)` — getting UTC then stripping the tzinfo. This keeps all comparisons in naive-datetime space.

**Affected file:** `backend/app/views/service.py` — `_expand_rrule()` and `execute_calendar_query()` RRULE expansion block.

### nginx serves /js/ and /css/ but NOT /static/ — template paths must match

**Discovered:** M034/S04/T04

The nginx config (`frontend/nginx.conf`) defines `location /js/` and `location /css/` with `root /usr/share/nginx/html`. There is NO `/static/` location. Requests to `/static/js/foo.js` fall through to the catch-all proxy → backend, which returns 404.

**Impact:** `calendar_view.html` used `<script src="/static/js/calendar.js">` which returned 404, silently breaking all calendar functionality. Same issue affected `_field.html` with `recurrence-editor.js`.

**Rule:** All JS references in templates must use `/js/filename.js`, not `/static/js/filename.js`. All CSS references must use `/css/filename.css`. The Docker volume mount maps `frontend/static/` → `/usr/share/nginx/html/`, so the file at `frontend/static/js/calendar.js` is served at `/js/calendar.js`.

### htmx swap of <script src> races with subsequent inline scripts

**Discovered:** M034/S04/T04

When htmx swaps HTML containing `<script src="/js/foo.js"></script>` followed by `<script>if (typeof foo === 'function') foo();</script>`, the external script loads asynchronously but the inline script executes immediately. The function from the external script is not yet defined when the inline script runs.

**Fix:** Use the lazy-load pattern instead:
```javascript
(function() {
    function _boot() { /* use the loaded function */ }
    if (typeof targetFn === 'function') { _boot(); }
    else {
        var s = document.createElement('script');
        s.src = '/js/foo.js';
        s.onload = _boot;
        document.head.appendChild(s);
    }
})();
```

This pattern is already used by `recurrence-editor.js` (T03) and now `calendar_view.html` (T04).
