# M041: Code Quality Audit — Recommendations Report

**Date:** 2026-03-23
**Scope:** Full-stack quality audit of SemPKM — backend (Python/FastAPI), frontend (JS/CSS/Jinja2), cross-cutting dimensions
**Methodology:** Pattern-based detection using `rg`, `fd`, `ast-grep`, Python AST analysis, and manual code inspection. No runtime profiling or dynamic analysis.

## Codebase Metrics Summary

| Dimension | Files | LOC | Largest File |
|-----------|-------|-----|-------------|
| Backend Python (`backend/app/`) | 233 | 60,069 | `views/service.py` (3,663) |
| Frontend JS (`frontend/static/js/`) | 28 | 18,587 | `workspace.js` (5,409) |
| Frontend CSS (`frontend/static/css/`) | 16 | 20,495 | `workspace.css` (9,203) |
| Jinja2 Templates (`backend/app/templates/`) | 165 | 18,323 | `dashboard_builder.html` (749) |
| **Total** | **442** | **117,474** | |

---

## Top 10 Highest-Impact Recommendations

Ranked by: runtime risk → correctness → maintainability → style.

### 1. Add SPARQL Parameterization and Input Escaping

- **Category:** SPARQL Construction (SQ-01, SQ-02, SQ-04)
- **Severity:** Critical
- **Effort:** High (architectural — build utility, migrate 131 sites)
- **Rationale:** 131 f-string SPARQL construction sites across 25 files with zero IRI or literal escaping. `scope_filter` is injected raw into WHERE clauses at 11 sites in `views/service.py`. A user-supplied description containing `"` produces malformed SPARQL. While mitigated by authentication, this is the single largest correctness risk in the codebase.
- **Files:** `backend/app/views/service.py` (30 sites), `backend/app/sparql/query_service.py` (12), `backend/app/services/models.py` (15), `backend/app/ontology/service.py` (14), `backend/app/sparql/utils.py` (missing escaping utilities)
- **Action:** Create `sparql/builder.py` with `escape_iri()`, `escape_literal()`, `escape_sparql_string()` utilities. Add `scope_filter` brace-balance validation. Migrate highest-risk sites (user-facing search, saved query injection) first.

### 2. Eliminate 26 Silent `except Exception: pass` Blocks

- **Category:** Error Handling (EH-02)
- **Severity:** Critical
- **Effort:** Low (add `logger.debug(..., exc_info=True)` to each)
- **Rationale:** 26 exception handlers silently swallow all errors with no logging. 7 are in model installation (`services/models.py`), inference configuration (`inference/service.py`), and model registry (`models/registry.py`) — core paths where silent failures mask real bugs. The `admin/router.py` `_query_entailment_examples()` has 7 sequential silent catches that make entailment diagnostics invisible.
- **Files:** `backend/app/admin/router.py` (7), `backend/app/services/models.py` (4), `backend/app/events/query.py` (2), `backend/app/events/store.py` (2), `backend/app/canvas/router.py` (2), `backend/app/canvas/service.py` (2), `backend/app/inference/service.py` (1), `backend/app/models/registry.py` (1), `backend/app/monitoring/middleware.py` (1), `backend/app/ontology/service.py` (1), `backend/app/services/icons.py` (1), `backend/app/services/settings.py` (1), `backend/app/task_templates/router.py` (1)
- **Action:** Add at minimum `logger.debug(...)` to each. For the 7 dangerous ones in core paths, upgrade to `logger.warning()`.

### 3. Add Test Coverage for Auth, Commands, and Triplestore Modules

- **Category:** Test Coverage Gaps (Cross-Cutting)
- **Severity:** Critical
- **Effort:** High (auth: 2-3 sessions, commands: 2 sessions, triplestore: 1 session)
- **Rationale:** 7/7 auth modules, 9/10 command handler modules, and 3/3 triplestore modules have zero test files. Auth handles session tokens, password hashing, and user injection — the entire authentication surface is untested. Commands handle IRI minting, RDF object creation, and batch slot resolution — the primary write path for the app. The triplestore client wraps all RDF4J HTTP communication.
- **Files:** `backend/app/auth/{dependencies,service,router,tokens,rate_limit,models,schemas}.py`, `backend/app/commands/{router,dispatcher,handlers/*.py}`, `backend/app/triplestore/{client,sync_client,setup}.py`
- **Action:** Start with auth (highest blast radius), then commands (most complex), then triplestore. Use the existing test patterns from `backend/tests/` — in-memory SQLite for auth DB tests, mock triplestore for command handler tests.

### 4. Fix 67 Unhandled fetch() Calls in Frontend JavaScript

- **Category:** DOM & Event Patterns (DOM-03)
- **Severity:** High
- **Effort:** Medium (mechanical fix per call site, ~2 sessions)
- **Rationale:** 67 of 131 fetch() calls (51%) lack `.catch()` handlers, `response.ok` checks, or both. Network failures silently fail, leaving the UI in an inconsistent state. `copilot.js` has 100% unhandled fetches (13/13). `workspace.js` has 30 unhandled fetches out of 49 total.
- **Files:** `frontend/static/js/workspace.js` (30), `frontend/static/js/copilot.js` (13), `frontend/static/js/sparql-console.js` (5), `frontend/static/js/canvas.js` (4), `frontend/static/js/settings.js` (3), `frontend/static/js/calendar.js` (3), `frontend/static/js/federation.js` (3), `frontend/static/js/vfs-browser.js` (3), `frontend/static/js/graph.js` (2), `frontend/static/js/markdown-render.js` (1)
- **Action:** Create a shared `apiFetch()` wrapper that enforces `.catch()` and `resp.ok` checking. Migrate highest-traffic call sites first (workspace.js object loading, copilot.js chat).

### 5. Decompose `views/service.py` God Module (3,663 LOC)

- **Category:** Module Structure (MS-01)
- **Severity:** Critical
- **Effort:** High (multi-session refactor)
- **Rationale:** `ViewSpecService` is a single class with 56 functions handling 12 renderer types. Every new renderer adds ~200 lines. The `register_renderer()` infrastructure already exists but is dead code. Extracting into `views/renderers/{table,cards,graph,calendar,map,kanban,...}.py` reduces the class to a ~300 LOC dispatcher and makes each renderer independently testable.
- **Files:** `backend/app/views/service.py` (3,663 LOC), `backend/app/views/registry.py` (dead `register_renderer()`)
- **Action:** Extract renderer modules one at a time, starting with the most self-contained (kanban, map, quadrant). Pairs with the `generic_view()` 1,020-line function decomposition in `views/router.py` (MS-03).

### 6. Add Loggers to 26 Substantial Modules Missing Logging

- **Category:** Logging (LG-01)
- **Severity:** High
- **Effort:** Low-Medium (add `logger = logging.getLogger(__name__)` + relevant log calls)
- **Rationale:** 26 modules over 100 LOC have no logger. Critical gaps: `auth/service.py` (authentication with zero logging), `sparql/client.py` (SPARQL communication), `triplestore/client.py` (RDF4J wrapper), `vfs/mount_service.py` (597 LOC, largest unlogged module). `canvas/service.py` has 4 silent exceptions with no logger to add to.
- **Files:** `backend/app/auth/service.py`, `backend/app/sparql/client.py`, `backend/app/triplestore/client.py`, `backend/app/vfs/mount_service.py`, `backend/app/canvas/service.py`, `backend/app/services/settings.py` + 20 others
- **Action:** Add loggers to the 6 critical modules first. Then sweep the remaining 20 as a batch.

### 7. Add Return Type Annotations to Router Layer (17% → 80%+)

- **Category:** Type Safety (TS-01, TS-02)
- **Severity:** High
- **Effort:** Medium (incremental, file-by-file)
- **Rationale:** Router layer has only 17% return type annotation coverage (62/368 functions). FastAPI uses return annotations for `response_model` inference — without them, 83% of routes have no response schema in OpenAPI docs and no automatic response validation. Only 45 of ~260 route decorators specify `response_model`.
- **Files:** All 35 router modules under `backend/app/`, especially zero-coverage ones: `lint/router.py` (0/18), `rdf_import/router.py` (0/8), `sparql/mirror_router.py` (0/6)
- **Action:** Add `response_model` to JSON-returning endpoints first. Use `response_class=HTMLResponse` for HTML-returning routes. Annotate return types on all async route handlers.

### 8. Clean Up 188 Unmatched Event Listeners

- **Category:** DOM & Event Patterns (DOM-01)
- **Severity:** High
- **Effort:** Medium (per-file audit)
- **Rationale:** 208 `addEventListener` calls vs. 20 `removeEventListener` calls. Not all are bugs — page-level listeners are intentionally permanent — but listeners on dockview panel content (graph nodes, editor instances, kanban cards) leak when panels are destroyed. `workspace.js` has 34 unmatched, `copilot.js` has 24.
- **Files:** `frontend/static/js/workspace.js` (34 imbalance), `frontend/static/js/copilot.js` (24), `frontend/static/js/sparql-console.js` (23), `frontend/static/js/recurrence-editor.js` (16), `frontend/static/js/canvas.js` (16), `frontend/static/js/vfs-browser.js` (15)
- **Action:** Audit each file: classify listeners as page-level (OK) or panel-scoped (needs cleanup). For panel-scoped listeners, add cleanup to `registerCleanup()` callbacks or `MutationObserver` teardown.

### 9. Extract PersonMatcher and Shared Utilities from 9 Sync Apps

- **Category:** Code Duplication (Cross-Cutting)
- **Severity:** Medium
- **Effort:** Large (extract to SDK, update 9 apps)
- **Rationale:** 9 sync apps have near-identical `person_matcher.py` files — the single largest duplication in the codebase. Additionally: ISO 8601 Z-replacement (8 instances), `datetime.now(timezone.utc)` (46 sites), label resolution SPARQL (4+ copies), and `FROM <urn:sempkm:current>` hard-coding (20+ instances).
- **Files:** `apps/{asana,caldav,github,google-calendar,jira,linear,monday,outlook-calendar,todoist}-sync/services/person_matcher.py`, `backend/app/federation/router.py`, `backend/app/admin/router.py`, `backend/app/views/service.py`, `backend/app/services/models.py`
- **Action:** Extract `parse_iso_datetime()` utility first (quick win, 8 sites). Then `PersonMatcher` to SDK (larger effort). Centralize graph URI constant.

### 10. Migrate Hardcoded Colors to CSS Custom Properties

- **Category:** CSS Architecture & Theming (CSS-01, CSS-02)
- **Severity:** Medium
- **Effort:** Medium (84 hex + 202 rgba values)
- **Rationale:** 84 standalone hardcoded hex colors and 202 hardcoded `rgba()` values bypass the theme system. These will not respond to theme changes (dark mode). The theme system is mature (89.7% tokenized) — the remaining 286 values are the long tail.
- **Files:** `frontend/static/css/workspace.css` (133 hardcoded), `frontend/static/css/bmc.css` (61 rgba), `frontend/static/css/decision-matrix.css` (26 rgba), `frontend/static/css/views.css` (37), `frontend/static/css/import.css` (11 hex)
- **Action:** Start with the most-shared colors (`#fff`, `#ef4444`, `#3b82f6`, `#22c55e`) that appear in 4+ files. Use `color-mix()` for rgba replacements.

---

## Backend Findings

### Module Structure

#### MS-01: `views/service.py` is the #1 god module (3,663 LOC, 56 functions, 2 classes)

- **Severity:** Critical
- **Effort:** High (multi-session refactor)
- **Location:** `backend/app/views/service.py:91-3495`
- **Detection:** `wc -l backend/app/views/service.py`

`ViewSpecService` spans 3,400+ lines with 46 methods handling 12 distinct renderer types. Each new renderer adds ~200 lines. Decompose into `views/renderers/{table,cards,graph,calendar,map,kanban,quadrant,bmc,okr,decision_matrix,timeline}.py`, reducing the class to a ~300 LOC dispatcher. The `register_renderer()` infrastructure already exists but is dead code.

#### MS-02: `ontology/service.py` is a god module (2,181 LOC, 42 functions)

- **Severity:** High
- **Effort:** Medium
- **Location:** `backend/app/ontology/service.py:184-2181`

Three distinct responsibility clusters: gist ontology management, read queries, and CRUD mutations. Split into `OntologyQueryService`, `OntologyMutationService`, and `GistService`.

#### MS-03: `views/router.py` contains a 1,020-line function

- **Severity:** Critical
- **Effort:** High
- **Location:** `backend/app/views/router.py:212` — `generic_view()` is 1,020 lines

A massive if/elif chain dispatching to renderer-specific code paths. Each branch (~80-120 lines) should be a separate handler function. Pairs with MS-01 renderer extraction.

#### MS-04: `admin/router.py` is monolithic (1,400 LOC, 31 functions)

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `backend/app/admin/router.py`

Single flat router covering models CRUD, API keys, webhooks, federation, SPARQL console, ops log, and entailment. Split into sub-routers by admin section.

#### MS-05: `browser/objects.py` and `browser/workspace.py` are oversized (1,349 and 1,344 LOC)

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `backend/app/browser/objects.py`, `backend/app/browser/workspace.py`

Large but less urgent than MS-01–03 — fewer functions with clearer single-entity responsibility.

#### MS-06: 9 modules exceed 1,000 LOC

- **Severity:** High
- **Effort:** High (aggregate)
- **Location:** `views/service.py` (3,663), `ontology/service.py` (2,181), `views/router.py` (1,930), `admin/router.py` (1,400), `browser/objects.py` (1,349), `browser/workspace.py` (1,344), `services/models.py` (1,256), `api/ai.py` (1,119), `federation/service.py` (1,090)

#### MS-07: `main.py` `lifespan()` is 415 lines

- **Severity:** Medium
- **Effort:** Low
- **Location:** `backend/app/main.py:102`

Extract initialization into per-subsystem functions: `_init_database()`, `_init_triplestore()`, `_init_services()`, `_init_background_tasks()`.

#### MS-08: 280 functions exceed 50 lines, 63 exceed 100 lines, 13 exceed 200 lines

- **Severity:** High
- **Effort:** High (aggregate)
- **Location:** Spread across 63 modules

Top offenders: `generic_view()` (1,020), `lifespan()` (415), `copilot_chat()` (399), `execute_cards_query()` (342), `execute()` in notion (323) and obsidian (267).

### Readability & Naming

#### RN-01: Naming conventions are consistently followed (positive)

- **Severity:** None
- All functions `snake_case`, all classes `PascalCase`, private methods use `_` prefix.

#### RN-02: Docstring coverage is excellent for public APIs (98%+) (positive)

- **Severity:** None
- 10 sampled modules show 100% docstring coverage (except `main.py` at 50%).

#### RN-03: `main.py` missing docstrings on 2 public functions

- **Severity:** Low
- **Effort:** Trivial
- **Location:** `backend/app/main.py:225` (`shapes_loader`), `backend/app/main.py:237` (`on_validation_complete`)

#### RN-04: `api/copilot.py` `copilot_chat()` mixes 5 concerns in 399 lines

- **Severity:** High
- **Effort:** Medium
- **Location:** `backend/app/api/copilot.py:314`

SSE formatting, SPARQL extraction, streaming, error handling, and conversation persistence interleaved.

#### RN-05: Import executors have monolithic `execute()` functions (323 and 267 lines)

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `backend/app/notion/executor.py:68`, `backend/app/obsidian/executor.py:75`

### Error Handling

#### EH-01: 312 `except Exception` handlers — 70% catch-and-degrade, 8% silent

- **Severity:** High
- **Effort:** High (aggregate)
- **Location:** 50+ modules

218 log + return default (graceful degradation), 24 silent `pass`, 19 silent `return`, 15 log + re-raise, 36 mixed.

#### EH-02: 26 `except Exception: pass` blocks — completely silent failure

- **Severity:** Critical
- **Effort:** Low
- **Location:** `admin/router.py` (7), `services/models.py` (4), `events/query.py` (2), `events/store.py` (2), `canvas/router.py` (2), `canvas/service.py` (2), `inference/service.py` (1), `models/registry.py` (1), `monitoring/middleware.py` (1), `ontology/service.py` (1), `services/icons.py` (1), `services/settings.py` (1), `task_templates/router.py` (1)

#### EH-03: 19 `except Exception: return <default>` with no logging

- **Severity:** High
- **Effort:** Low
- **Location:** `views/service.py:3211,3236,3464,3489` + others

Return empty defaults (`[]`, `{}`, `None`) without trace. Caller sees empty result indistinguishable from genuine empty dataset.

#### EH-04: `views/service.py` has 37 broad `except Exception` — 33 logged, 4 silent

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `backend/app/views/service.py`

Deliberate graceful degradation pattern but no user/admin visibility into failures. Consider failure counters or `warnings` field in response.

#### EH-05: `admin/router.py` entailment examples — 7 sequential silent catches

- **Severity:** Medium
- **Effort:** Trivial
- **Location:** `backend/app/admin/router.py:770-923`

If triplestore is down, admin page renders with zero entailment examples and no error indicator.

#### EH-06: `inference/service.py` logs triplestore errors at `debug` level

- **Severity:** Medium
- **Effort:** Trivial
- **Location:** `backend/app/inference/service.py:485,585`

Real operational errors (CLEAR GRAPH, DELETE failures) logged at debug — should be warning.

### Logging

#### LG-01: 26 substantial modules (>100 LOC) lack logging

- **Severity:** High
- **Effort:** Medium
- **Location:** Critical gaps: `auth/service.py` (333 LOC), `sparql/client.py` (242 LOC), `triplestore/client.py` (151 LOC), `vfs/mount_service.py` (597 LOC), `canvas/service.py` (250 LOC, 4 silent exceptions)

#### LG-02: Zero f-string logging — %-style used consistently (positive)

- **Severity:** None
- All 743 logger calls use %-style deferred formatting.

#### LG-03: Zero `extra={}` structured logging

- **Severity:** Medium
- **Effort:** Medium (incremental)
- **Location:** All 743 logger calls

No structured logging anywhere. All context embedded in format strings. Makes log aggregation harder.

#### LG-04: 105 `exc_info=True` usages — good exception chain preservation (positive)

- **Severity:** None

#### LG-05: `federation/signatures.py` logs signature verification failure at `info`

- **Severity:** Low
- **Effort:** Trivial
- **Location:** `backend/app/federation/signatures.py:260`

Security-relevant event at insufficient log level.

#### LG-06: `indieauth/service.py` logs client fetch failure at `debug`

- **Severity:** Low
- **Effort:** Trivial
- **Location:** `backend/app/indieauth/service.py:142`

### Type Safety

#### TS-01: 74% return type annotation overall — routers at 17%

- **Severity:** High
- **Effort:** Medium
- **Location:** 35 router modules

Services at 67%, utilities at ~70%, routers at 17%. Zero-coverage: `lint/router.py` (0/18), `rdf_import/router.py` (0/8), `sparql/mirror_router.py` (0/6).

#### TS-02: Only 45 of ~260 route decorators specify `response_model`

- **Severity:** Medium
- **Effort:** Medium
- **Location:** All router modules

215 routes return untyped responses. No response validation, empty OpenAPI schemas.

#### TS-03: 158 Pydantic models — zero deprecated `.dict()` usage (positive)

- **Severity:** None
- All serialization uses v2 `model_dump()`.

### SPARQL Construction

#### SQ-01: 131 f-string SPARQL construction sites — no parameterized builder

- **Severity:** High
- **Effort:** High (architectural)
- **Location:** 25 files, heaviest: `views/service.py` (~30), `services/models.py` (~15), `ontology/service.py` (~14), `sparql/query_service.py` (~12)

No escaping for IRIs, literals, or user-supplied values.

#### SQ-02: `scope_filter` injected raw into SPARQL WHERE clauses at 11 sites

- **Severity:** High
- **Effort:** Medium
- **Location:** `backend/app/views/service.py:346,380,409,1320,1708,1881,2140,2399,2615,2873,3063`

Raw SPARQL WHERE body from saved queries interpolated directly. Mitigated by auth but fragile.

#### SQ-03: IRI validation duplicated across 3 implementations

- **Severity:** Medium
- **Effort:** Low
- **Location:** `browser/_helpers.py:13`, `canvas/router.py:40`, `models/validator.py:55`

#### SQ-04: Only regex escaping exists — no IRI or literal escaping

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `backend/app/sparql/utils.py` — single function `escape_sparql_regex()`

### Async Patterns

#### AP-01: 6 blocking `open()` calls in async router modules

- **Severity:** Medium
- **Effort:** Low
- **Location:** `admin/router.py:917`, `apps/admin_router.py:110`, `browser/apps.py:356`, `notion/router.py:145`, `obsidian/router.py:117`, `services/icons.py:72`

Synchronous file I/O in async handlers. Low risk for small files, problematic for upload zip writes.

#### AP-02: Zero `time.sleep()` calls (positive)

- **Severity:** None

#### AP-03: 3 sync helper functions in async modules — appropriate usage (positive)

- **Severity:** Low
- Pure data transformation and DI factories — sync is correct.

#### AP-04: 254 `request.app.state` accesses — mixed DI pattern

- **Severity:** Medium
- **Effort:** High (widespread refactor)
- **Location:** 35+ router and utility modules

Two parallel DI patterns: `Depends()` (9 factories) and direct `request.app.state.X` (254 accesses). Inconsistency hinders testability.

### FastAPI Patterns

#### FP-01: Router prefix conventions inconsistent

- **Severity:** Low
- **Effort:** Low
- 18 routers define prefix inline, 12 rely on `include_router()`.

#### FP-02: 83% of routes lack response schema (cross-ref TS-02)

- **Severity:** Medium
- **Effort:** Medium

#### FP-03: `dependencies.py` covers only 9 of ~20+ `app.state` services

- **Severity:** Medium
- **Effort:** Low
- Missing: `templates`, `template_service`, `view_spec_service`, `workflow_service`, `event_store`, `ops_log_service`, `icon_service`, `settings_service`

#### FP-04: No middleware ordering documentation — 5 layers with implicit ordering

- **Severity:** Low
- **Effort:** Trivial

---

## Frontend Findings

### JS Structure & Global State

#### JS-01: workspace.js is a 5,409-line monolith with 170 functions

- **Severity:** High
- **Effort:** Large (multi-sprint decomposition)
- **Location:** `frontend/static/js/workspace.js`

Handles 12+ concerns: tab management, object CRUD, editor wiring, persona switching, command palette, VFS mounts, lint dashboard, favorites, SPARQL widgets, chart rendering, relation panels, event undo.

#### JS-02: 124 global state assignments on window object in workspace.js

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `frontend/static/js/workspace.js` (124), total across all JS: ~222

Cross-IIFE communication via `window` is a documented pattern, but scale creates collision risk.

#### JS-03: Inconsistent module patterns — 25 IIFE vs 3 ESM files

- **Severity:** Low
- **Effort:** Large (would need bundler)

Documented architectural choice. ESM used for newer features (copilot, editor, sparql-console).

#### JS-04: 126 console.log/error calls in production code

- **Severity:** Low
- **Effort:** Small
- **Location:** `workspace.js` (45), `copilot.js` (23), `calendar.js` (13), `graph.js` (9)

Keep `console.error` in catch blocks, remove `console.log` from production paths.

### DOM & Event Patterns

#### DOM-01: 188 unmatched addEventListener calls (208 add vs 20 remove)

- **Severity:** High
- **Effort:** Medium
- **Location:** `workspace.js` (34 imbalance), `copilot.js` (24), `sparql-console.js` (23), `recurrence-editor.js` (16), `canvas.js` (16), `vfs-browser.js` (15)

Page-level listeners are OK. Panel-scoped listeners on dynamically created elements inside dockview panels leak when panels are destroyed.

#### DOM-02: 48 setTimeout with only 9 clearTimeout — plus 1 undeduplicated setInterval

- **Severity:** Medium
- **Effort:** Small
- **Location:** `federation.js:62` — `setInterval(updateInboxBadge, 60000)` runs forever, no dedup guard

Most timeouts are fire-and-forget animations (safe). Debounce timers are properly tracked.

#### DOM-03: 67 of 131 fetch() calls (51%) have incomplete error handling

- **Severity:** High
- **Effort:** Medium
- **Location:** `workspace.js` (30 unhandled), `copilot.js` (13, 100%), `sparql-console.js` (5), `canvas.js` (4), `settings.js` (3), `calendar.js` (3), `federation.js` (3), `vfs-browser.js` (3), `graph.js` (2), `markdown-render.js` (1)

Missing `.catch()` (51 calls) and `response.ok` check (32 calls). Network failures silently fail.

#### DOM-04: No centralized fetch wrapper — error handling duplicated ad hoc

- **Severity:** Medium
- **Effort:** Small to create, large to migrate
- **Location:** All JS files using `fetch()`

No shared `apiFetch()` utility that enforces consistent error handling, auth redirect, or AbortController.

### CSS Architecture & Theming

#### CSS-01: 84 standalone hardcoded hex colors bypass the theme system

- **Severity:** Medium
- **Effort:** Small-Medium
- **Location:** `workspace.css` (32), `views.css` (12), `import.css` (11), `vfs-browser.css` (9), `okr.css` (6)

Most-shared: `#fff` (10 files), `#1e1e1e` (5 files), `#ef4444` (4 files), `#3b82f6` (4 files), `#22c55e` (4 files). Map to existing `--color-*` variables.

#### CSS-02: 202 standalone hardcoded rgba() values bypass theme

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `workspace.css` (101), `bmc.css` (61), `decision-matrix.css` (26), `quadrant.css` (25), `okr.css` (16)

Modern `color-mix(in srgb, var(--color-x) 15%, transparent)` is already used in places — adopt consistently.

#### CSS-03: 61 `!important` declarations — 30 necessary vendor overrides, 31 avoidable

- **Severity:** Low
- **Effort:** Medium
- 30 are driver.js (guided tour) overrides — necessary. 31 are avoidable via higher specificity.

#### CSS-04: Inconsistent responsive breakpoints — 4 different values, no tokens

- **Severity:** Low
- **Effort:** Small
- 600px (5 uses), 640px (3 uses), 768px (3 uses), 800px (1 use). Document standard set.

#### CSS-05: Repeated property patterns suggest missing utility classes

- **Severity:** Low
- **Effort:** Medium
- `display: flex` (165×), `align-items: center` (134×), `flex-shrink: 0` (134×), `cursor: pointer` (101×) in workspace.css alone.

### Jinja2 Template Hygiene

#### TPL-01: 23 templates >200 LOC with zero partial extraction

- **Severity:** Medium
- **Effort:** Medium
- Worst: `dashboard_builder.html` (749), `guide.html` (578), `admin/model_detail.html` (481), `workflow_builder.html` (477)

#### TPL-02: Computation logic in templates via namespace() and .append()

- **Severity:** High
- **Effort:** Medium
- 7 templates use `namespace()`, 10 use `.append()`. Property filtering, path comparison, and state detection belong in view functions, not templates.
- **Location:** `object_read.html:44,69`, `object_form.html:81,110`, `object_tab.html:24`, `object_embed.html:22`, `dashboard_builder.html:59`, `saved_queries_explorer.html:9,11`, `_context_rules.html:49`

#### TPL-03: Notion/Obsidian importer templates are near-duplicates (9 matching files)

- **Severity:** Medium
- **Effort:** Medium
- Similarity ranges from 55% to 95%. Shared base templates with importer-specific blocks would eliminate ~800 LOC.

#### TPL-04: Zero url_for() usage — all 349 URLs are hardcoded strings

- **Severity:** Medium
- **Effort:** Large
- 349 hardcoded route references (212 hx-get, 59 href, 49 hx-post, 19 action, 10 hx-delete). Renaming any backend route requires updating every referencing template.

### htmx Consistency

#### HTMX-01: 88% of hx-swap is innerHTML — undocumented convention

- **Severity:** Low
- **Effort:** Small
- 242 interactions rely on htmx's default behavior without explicit attribute.

#### HTMX-02: 14 unique hx-trigger patterns — debounce inconsistency

- **Severity:** Medium
- **Effort:** Small-Medium
- `_field.html` uses `delay:200ms` while all others use `delay:300ms`. `revealed` vs `intersect once` overlap. Custom event names are ad hoc.

#### HTMX-03: guide.html and docs_page.html have 81 near-identical button blocks

- **Severity:** Low
- **Effort:** Small
- Could be generated from a Jinja2 loop, reducing 550+ lines to ~15.

#### HTMX-04: No hx-put or hx-patch — all mutations via hx-post

- **Severity:** Low
- **Effort:** N/A (informational)
- 49 hx-post mutations, 10 hx-delete (correct). No hx-put/hx-patch usage.

---

## Cross-Cutting Findings

### Dead Code & Markers

#### DC-01: Zero TODO/FIXME/HACK/XXX markers in codebase

- **Severity:** Low (informational)
- **Effort:** N/A
- Good hygiene, but means accumulated debt is undocumented inline — lives only in KNOWLEDGE.md.

#### DC-02: No genuine commented-out code blocks

- **Severity:** Low
- **Effort:** N/A
- All 3+ consecutive comment runs are documentation.

#### DC-03: 3 unused imports found in 10-module sample

- **Severity:** Low
- **Effort:** Trivial (5 min per fix)
- **Location:** `main.py:562` (`init_template_helpers`), `browser/workspace.py:1333` (`AsyncSession`), `services/validation.py:15` (`XSD`)
- A full `ruff` run would surface all unused imports across 193 modules.

#### DC-04: `register_renderer()` is dead code

- **Severity:** Medium
- **Effort:** Small
- **Location:** `backend/app/views/registry.py:55`
- Defined but never called. Creates confusion about the intended renderer extension pattern.

### Code Duplication

#### DUP-01: PersonMatcher across 9 sync apps (largest duplication)

- **Severity:** Medium
- **Effort:** Large
- **Location:** `apps/{asana,caldav-calendar,github,google-calendar,jira,linear,monday,outlook-calendar,todoist}-sync/services/person_matcher.py`

#### DUP-02: ISO 8601 Z-replacement (8 instances in 4 files)

- **Severity:** Medium
- **Effort:** Small (30 min)
- **Location:** `federation/router.py` (2), `admin/router.py` (3), `views/service.py` (2), `services/models.py` (1)
- Extract `parse_iso_datetime()` utility.

#### DUP-03: `datetime.now(timezone.utc)` proliferation (46 call sites)

- **Severity:** Low
- **Effort:** Small
- Extract `utc_now_iso()` utility.

#### DUP-04: Label resolution SPARQL (4+ inlined copies)

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `services/labels.py:85-87` (canonical), `vfs/collections.py:248-250`, `vfs/router.py:132-134,222-224`, `events/query.py:138,184`
- VFS and events inline their own fragments instead of using `LabelService`.

#### DUP-05: `FROM <urn:sempkm:current>` hard-coded (20+ instances)

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `vfs/strategies.py` (12), `vfs/mount_router.py` (2), `vfs/mount_resource.py` (2), `inference/service.py` (5+)
- Should use `scope_to_current_graph()` or a central constant.

#### DUP-06: IRI pill rendering (3 frontend implementations)

- **Severity:** Low-Medium
- **Effort:** Small
- **Location:** `sparql-console.js:1013-1044`, `copilot.js:749-758`, `copilot.js:1706`

#### DUP-07: escapeHtml (2 independent definitions)

- **Severity:** Low
- **Effort:** Small
- **Location:** `workspace.js:2269`, `context-indicator.js:72`

### Test Coverage Gaps

#### TEST-01: 165 of 193 backend modules have no dedicated test file (85.5%)

- **Severity:** High
- **Effort:** Very High (aggregate)

#### TEST-02: Authentication — 7/7 modules completely untested

- **Severity:** Critical
- **Effort:** High
- **Location:** `backend/app/auth/{dependencies,service,router,tokens,rate_limit,models,schemas}.py`

#### TEST-03: Commands — 9/10 modules completely untested

- **Severity:** Critical
- **Effort:** High
- **Location:** `backend/app/commands/{router,dispatcher,handlers/*.py}`
- Only `body_diff` has a test file.

#### TEST-04: Triplestore — 3/3 modules completely untested

- **Severity:** Critical
- **Effort:** Medium
- **Location:** `backend/app/triplestore/{client,sync_client,setup}.py`

#### TEST-05: Views core — 3/3 modules untested (service, router, registry)

- **Severity:** High
- **Effort:** High
- Individual renderer tests exist but don't cover core dispatch logic.

#### TEST-06: Copilot — 6/7 modules untested

- **Severity:** High
- **Effort:** Medium
- **Location:** `backend/app/copilot/{service,personas,conversation,context,models,schemas}.py`

#### TEST-07: VFS subsystem — 13 modules with only 2 test files

- **Severity:** High
- **Effort:** High
- **Location:** `backend/app/vfs/` — 13 modules covering virtual filesystem

### Tech Debt

#### TD-01: K001 — rdflib `xsd:dayTimeDuration` workaround still present

- **Severity:** Low
- **Effort:** Small
- **Location:** `models/crm/rules/crm.ttl`

#### TD-02: K002 — Seed data dateTime vs date type mismatch still present

- **Severity:** Low
- **Effort:** Small
- **Location:** `models/basic-pkm/seed/basic-pkm.jsonld`

#### TD-03: `extract_scope_where_body()` LIMIT clause bug still present

- **Severity:** Medium
- **Effort:** Small
- **Location:** `backend/app/views/service.py:3505`
- Regex fails on queries with trailing LIMIT/ORDER BY.

#### TD-04: SPARQL API lacks UPDATE endpoint

- **Severity:** Medium
- **Effort:** Medium
- **Location:** `backend/app/sparql/router.py`
- Only SELECT/ASK/CONSTRUCT/DESCRIBE supported. No INSERT/DELETE via HTTP API.

#### TD-05: Accumulated debt not in KNOWLEDGE.md

- **Severity:** Varies
- Auth zero-test-coverage (Critical), Commands zero-test-coverage (Critical), Triplestore zero-test-coverage (Critical), `datetime.now(timezone.utc)` proliferation (Medium), `FROM <urn:sempkm:current>` hard-coding (Medium), Frontend `escapeHtml` duplication (Low).

---

## Linting Tool Recommendations

### Python: ruff

**Recommended tool:** [ruff](https://docs.astral.sh/ruff/) — extremely fast Python linter and formatter (Rust-based, replaces flake8 + isort + pyflakes + many plugins)

**Suggested rule sets:**

```toml
# pyproject.toml
[tool.ruff]
target-version = "py310"
line-length = 120

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # pyflakes (unused imports, undefined names)
    "I",     # isort (import ordering)
    "UP",    # pyupgrade (Python version upgrades, e.g. Z-replacement)
    "B",     # flake8-bugbear (common bugs)
    "SIM",   # flake8-simplify (simplifiable code)
    "RUF",   # ruff-specific rules
    "ASYNC", # flake8-async (async anti-patterns like blocking I/O)
    "T20",   # flake8-print (print statements)
    "C4",    # flake8-comprehensions
]
ignore = [
    "E501",  # line length (handled by formatter)
]

[tool.ruff.lint.per-file-ignores]
"backend/app/views/service.py" = ["C901"]  # too complex — known, tracked as MS-01
"backend/app/views/router.py" = ["C901"]   # too complex — known, tracked as MS-03
```

**Immediate wins from ruff:**
- `F401` — Catches all unused imports across 193 modules (DC-03 found 3 in a 10-module sample)
- `UP036` — Auto-fixes `"Z", "+00:00"` replacement with `fromisoformat()` on Python 3.11+ (DUP-02)
- `ASYNC100/ASYNC101` — Flags blocking `open()` calls in async functions (AP-01)
- `B001` — Catches bare `except:` handlers
- `T201` — Flags `print()` statements that should be `logger.info()`

**Setup effort:** Small (30 min). Add `pyproject.toml` config, run `ruff check backend/app/` to see initial violations, fix auto-fixable ones with `ruff check --fix`.

### JavaScript: ESLint

**Recommended tool:** [ESLint](https://eslint.org/) v9 with flat config

**Suggested configuration:**

```javascript
// eslint.config.js
export default [
    {
        files: ["frontend/static/js/**/*.js"],
        rules: {
            "no-unused-vars": "warn",
            "no-undef": "off",           // IIFE pattern uses window globals
            "eqeqeq": ["error", "always"],
            "no-implicit-globals": "error",
            "no-console": ["warn", { allow: ["error", "warn"] }],
            "no-empty": ["error", { allowEmptyCatch: false }],
            "curly": "error",
            "no-throw-literal": "error",
            "prefer-const": "warn",
        },
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "script",     // IIFE files are scripts, not modules
            globals: {
                window: "readonly",
                document: "readonly",
                fetch: "readonly",
                htmx: "readonly",
                lucide: "readonly",
                dockview: "readonly",
                AbortController: "readonly",
            }
        }
    },
    {
        files: ["frontend/static/js/copilot.js", "frontend/static/js/editor.js", "frontend/static/js/sparql-console.js"],
        languageOptions: {
            sourceType: "module",     // ESM files
        }
    }
];
```

**Immediate wins from ESLint:**
- `no-console` — Flags 126 console calls (JS-04), keeping only `console.error` and `console.warn`
- `no-empty` — Catches empty catch blocks in JS (equivalent to EH-02 for frontend)
- `eqeqeq` — Prevents subtle type coercion bugs from `==`
- `no-implicit-globals` — Prevents accidental global scope pollution beyond explicit `window.*`

**Setup effort:** Small (45 min). No bundler needed — ESLint runs standalone on JS files.

### CSS: Stylelint

**Recommended tool:** [Stylelint](https://stylelint.io/) with `stylelint-config-standard`

**Suggested configuration:**

```json
{
    "extends": "stylelint-config-standard",
    "rules": {
        "color-no-hex": null,
        "custom-property-pattern": "^(color|_|font|space|radius|shadow|bp)-",
        "declaration-no-important": true,
        "no-duplicate-selectors": true,
        "shorthand-property-no-redundant-values": true,
        "color-named": "never",
        "max-nesting-depth": 4,
        "selector-max-specificity": "0,4,1",
        "declaration-block-no-redundant-longhand-properties": true
    },
    "overrides": [
        {
            "files": ["frontend/static/css/workspace.css"],
            "rules": {
                "declaration-no-important": [true, {
                    "severity": "warning"
                }]
            }
        }
    ]
}
```

**Immediate wins from Stylelint:**
- `declaration-no-important` — Flags 31 avoidable `!important` declarations (CSS-03)
- `no-duplicate-selectors` — Catches repeated selectors that could be consolidated
- `color-named` — Ensures consistent use of hex/variable notation

**Setup effort:** Small (30 min). Run `npx stylelint "frontend/static/css/*.css"`.

### Combined Setup Estimate

| Tool | Setup Time | Auto-fixable Issues | Manual Issues |
|------|-----------|--------------------:|-------------:|
| ruff | 30 min | ~50 (imports, style) | ~80 (logic, async) |
| ESLint | 45 min | ~30 (style) | ~60 (error handling) |
| Stylelint | 30 min | ~20 (formatting) | ~40 (specificity, !important) |
| **Total** | **~2 hours** | **~100** | **~180** |

**Recommended adoption order:** ruff first (most impactful, fastest to run, auto-fixes the most), then ESLint, then Stylelint.

---

## Appendix: Detection Commands

### Module Structure

```bash
# LOC per file
fd -e py . backend/app/ | xargs wc -l | sort -rn | head -20

# Functions per file
python3 -c "import ast,os; [(print(f'{fp}: {sum(1 for n in ast.walk(ast.parse(open(fp).read())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)))} functions')) for fp in (os.path.join(r,f) for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py'))]" 2>/dev/null | sort -t: -k2 -rn | head -20

# Functions >100 lines
python3 -c "import ast,os; [print(f'{n.end_lineno-n.lineno+1:4d} lines  {fp}:{n.lineno}  {n.name}') for fp in (os.path.join(r,f) for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py')) for n in ast.walk(ast.parse(open(fp).read())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and getattr(n,'end_lineno',0)-n.lineno>99]" 2>/dev/null | sort -rn

# Modules >1000 LOC
fd -e py . backend/app/ | xargs wc -l | sort -rn | awk '$1 > 1000 && $2 != "total"'
```

### Error Handling

```bash
# All except Exception handlers
python3 -c "import ast,os; total=0; [total:=total+1 for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py') for n in ast.walk(ast.parse(open(os.path.join(r,f)).read())) if isinstance(n,ast.ExceptHandler) and n.type and isinstance(n.type,ast.Name) and n.type.id=='Exception']; print(total)"

# Silent except Exception: pass
python3 -c "import ast,os; [(print(f'{os.path.join(r,f)}:{n.lineno}')) for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py') for n in ast.walk(ast.parse(open(os.path.join(r,f)).read())) if isinstance(n,ast.ExceptHandler) and n.type and isinstance(n.type,ast.Name) and n.type.id=='Exception' and len(n.body)==1 and isinstance(n.body[0],ast.Pass)]"

# Silent except Exception: return
python3 -c "import ast,os; [(print(f'{os.path.join(r,f)}:{n.lineno}')) for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py') for n in ast.walk(ast.parse(open(os.path.join(r,f)).read())) if isinstance(n,ast.ExceptHandler) and n.type and isinstance(n.type,ast.Name) and n.type.id=='Exception' and len(n.body)==1 and isinstance(n.body[0],ast.Return)]"
```

### Logging

```bash
# Modules with loggers
rg "logger\s*=\s*|logging\.getLogger" -l backend/app/ | wc -l

# Modules without loggers (>100 LOC)
comm -23 <(fd -e py . backend/app/ | sort) <(rg "logger\s*=\s*|logging\.getLogger" -l backend/app/ 2>/dev/null | sort) | grep -v "__init__\.py" | grep -v "models\.py" | grep -v "schemas\.py" | xargs -I{} sh -c 'lines=$(wc -l < "{}"); [ "$lines" -gt 100 ] && echo "$lines {}"' | sort -rn

# Structured logging usage
rg "extra\s*=" backend/app/ | grep "logger\."
```

### Type Safety

```bash
# Return annotation coverage
rg "^\s*(async )?def " backend/app/ -n | wc -l     # total functions
rg "^\s*(async )?def " backend/app/ -n | rg "\->" | wc -l  # annotated

# response_model coverage
rg "response_model=" backend/app/ | wc -l
```

### SPARQL Construction

```bash
# f-string SPARQL sites
{ rg -n 'f"[^"]*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)' backend/app/ --no-heading; rg -n "f'[^']*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)" backend/app/ --no-heading; rg -n 'f"""[^"]*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)' backend/app/ --no-heading; } | sort -u | wc -l

# scope_filter injection points
rg "scope_filter" backend/app/views/service.py -n

# IRI validation implementations
rg "def.*iri.*valid|def.*valid.*iri|def.*is_valid_iri" backend/app/ -n -i
```

### Frontend JS

```bash
# File sizes
wc -l frontend/static/js/*.js | sort -rn

# Function counts
grep -cE "function\s+\w+\(|=\s*function\s*\(|=>\s*\{" frontend/static/js/*.js | sort -t: -k2 -rn

# window.* global assignments
rg "window\.\w+ =" frontend/static/js/ -n --count

# addEventListener vs removeEventListener
rg "addEventListener" frontend/static/js/ -n --count
rg "removeEventListener" frontend/static/js/ -n --count

# fetch() call sites
rg "fetch\(" frontend/static/js/ -n --count

# console.* calls
rg "console\." frontend/static/js/ --count
```

### Frontend CSS

```bash
# Hardcoded hex (non-fallback, non-theme)
rg "#[0-9a-fA-F]{3,8}\b" frontend/static/css/ -n | grep -v "var(--" | grep -v "theme.css"

# Hardcoded rgba
rg "rgba\(" frontend/static/css/ -n | grep -v "var(--" | grep -v "theme.css" | wc -l

# !important declarations
rg "!important" frontend/static/css/ -n --count | sort -t: -k2 -rn

# var() reference count
rg "var\(--" frontend/static/css/ | wc -l

# Responsive breakpoints
rg "@media" frontend/static/css/ -n
```

### Jinja2 Templates

```bash
# Template sizes
fd -e html . backend/app/templates/ -x wc -l {} | sort -rn | head -20

# Logic density ({% if/for/set/macro %})
rg "\{%\s*(if|for|set|macro)" backend/app/templates/ | wc -l

# Partial reuse ({% include %})
rg "\{%\s*include" backend/app/templates/ | wc -l

# namespace() usage
rg "namespace\(" backend/app/templates/ -n

# .append() side-effects
rg "\.append\(" backend/app/templates/ -n

# url_for() vs hardcoded URLs
rg "url_for" backend/app/templates/ --count
rg '(href|action|hx-get|hx-post|hx-put|hx-delete|hx-patch)="/' backend/app/templates/ --count
```

### Cross-Cutting

```bash
# Dead code markers
rg -i "todo|fixme|hack\b|xxx\b" backend/app/ frontend/static/ --type py --type js --type css

# Unused imports (full run via ruff)
# ruff check backend/app/ --select F401

# Test coverage gaps
comm -23 <(fd -e py . backend/app/ --exclude '__pycache__' -x basename {} .py | sort -u) <(fd -e py . backend/tests/ --exclude '__pycache__' -x basename {} .py | sed 's/^test_//' | sort -u)

# Z-replacement duplication
rg '\.replace\("Z", "\+00:00"\)' backend/app/ -n

# datetime.now proliferation
rg 'datetime\.now\(timezone\.utc\)' backend/app/ -c

# FROM graph hard-coding
rg 'FROM <urn:sempkm:current>' backend/app/ -c

# PersonMatcher duplication
fd "person_matcher" apps/

# register_renderer dead code
rg "register_renderer" backend/app/views/ -n
```
