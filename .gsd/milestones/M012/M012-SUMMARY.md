---
id: M012
provides:
  - Event log predicate labels resolved to human-readable text via ShapesService batch resolution
  - Helptext tooltips on event log predicates from SHACL sh:name / sempkm:editHelpText / sh:description
  - Three autocomplete suggestion endpoints for event log filter fields (types, predicates, objects)
  - body.diff operation type storing incremental unified diffs instead of full body replacements
  - Event log rendering for both body.set (full text) and body.diff (green/red diff highlighting)
  - body.diff undo support via build_compensation() reconstructing old body from stored diff
  - Persona SQLAlchemy model with Alembic migration 013
  - PersonaService with CRUD, activation, and state save (8 async methods)
  - REST API (7 endpoints) + browser route for persona selector partial
  - Persona selector in sidebar user popover with active indicator
  - Command palette entries for persona switching (Switch To, Save Current, Create New)
  - Frontend persona lifecycle (init, save, switch, create, beforeunload auto-save)
  - Default persona auto-created on first workspace load
  - 12 Playwright E2E tests across 3 spec files
  - User guide Chapter 15 updated (4 new sections) + Chapter 30 created (personas, 7 sections)
  - RATE_LIMIT_ENABLED config toggle for E2E test environments
key_decisions:
  - D155 — Layout-only personas for v1 (no settings overrides)
  - D156 — Dedicated personas table following DashboardSpec model pattern
  - D157 — Explicit save only (no auto-save on every layout change)
  - D158 — RATE_LIMIT_ENABLED env var to disable slowapi in E2E test stack
  - D161 — Iterate both rdf:type sh:PropertyShape subjects AND sh:property objects for inline blank-node property shapes
patterns_established:
  - SHACL property shape iteration for predicate metadata — handles both typed and inline blank-node PropertyShapes via dual-path iteration
  - htmx autocomplete pattern — text input + hx-trigger → suggestion template fragment → JS click handler applies filter via htmx.ajax
  - body.diff handler mirrors body.set but adds sempkm:bodyDiff data triple for stored diff alongside full body
  - save_body() three-way branching — body.diff for changes, body.set for first body, no-op for unchanged
  - Persona module mirrors dashboard module structure (models.py, service.py, router.py)
  - Single-active-per-user constraint via bulk-deactivate + targeted-activate
  - Cross-IIFE guard flags via window.* for workspace.js ↔ workspace-layout.js communication
  - navigator.sendBeacon on beforeunload for fire-and-forget state persistence
observability_surfaces:
  - logger.warning on shapes graph query failure in get_labels_for_predicates() and get_helptext_for_predicates()
  - logger.warning in each suggestion endpoint on SPARQL query failure
  - HTML title attribute on .diff-pred-label shows helptext or full IRI for debugging
  - body.diff events visible in event log with operation type body.diff
  - Stored diff text queryable via SPARQL — SELECT ?diff WHERE { GRAPH <event_iri> { ?s <urn:sempkm:bodyDiff> ?diff } }
  - GET /api/personas returns persona list with is_active indicator
  - Console logs on persona init, save, switch, create with persona name
  - Toast notifications for all persona operations
  - logger.info on persona create/activate/delete
requirement_outcomes:
  - id: EVTLOG-01
    from_status: active
    to_status: validated
    proof: ShapesService label resolution + 20 unit tests (test_event_log_labels.py) + E2E test (event-log-polish.spec.ts) + docs (Ch 15 §Predicate Labels)
  - id: EVTLOG-02
    from_status: active
    to_status: validated
    proof: ShapesService helptext extraction + 20 unit tests (test_event_log_labels.py) + E2E test (event-log-polish.spec.ts) + docs (Ch 15 §Helptext Tooltips)
  - id: EVTLOG-03
    from_status: active
    to_status: validated
    proof: 3 suggestion endpoints + 17 unit tests (test_event_suggestions.py) + E2E tests (event-log-polish.spec.ts) + docs (Ch 15 §Autocomplete Filters)
  - id: BDIFF-01
    from_status: active
    to_status: validated
    proof: body.diff handler + save_body() branching + 34 unit tests (test_body_diff.py) + E2E test (body-diff.spec.ts) + docs (Ch 15 §Body Diff Events)
  - id: BDIFF-02
    from_status: active
    to_status: validated
    proof: _parse_stored_diff() rendering + event_detail.html extension + 34 unit tests + E2E test proves green/red highlighting
  - id: BDIFF-03
    from_status: active
    to_status: validated
    proof: save_body() three-way branch emits body.set for first body + E2E test 3 proves body.set creation + backward compat unit tests
  - id: PERSONA-01
    from_status: active
    to_status: validated
    proof: PersonaService 8 methods + 20 unit tests (test_persona_service.py) + 7 API endpoints + E2E test (personas.spec.ts) + docs (Ch 30)
  - id: PERSONA-02
    from_status: active
    to_status: validated
    proof: switchPersona() restores layout/positions/mode + dv.fromJSON() try/catch + _switchingPersona guard + browser verified + E2E test
  - id: PERSONA-03
    from_status: active
    to_status: validated
    proof: _persona_selector.html partial in sidebar popover + browser screenshot + E2E test proves selector visible
  - id: PERSONA-04
    from_status: active
    to_status: validated
    proof: 3 command palette entries with _refreshPersonaPaletteItems() + browser screenshot + E2E test proves commands exist
  - id: PERSONA-05
    from_status: active
    to_status: validated
    proof: initPersonas() auto-creates Default when no personas exist + browser console verified + E2E test proves auto-creation
duration: ~5h (S01: 2h30m, S02: 52m, S03: 80m, S04: 57m)
verification_result: passed
completed_at: 2026-03-17
---

# M012: Workspace & Event Log Polish

**Three independent UX improvements shipped: event log fields now show human-readable labels with helptext and autocomplete, body edits store incremental diffs with green/red highlighting, and a persona system lets users switch between named workspace configurations**

## What Happened

M012 delivered three independent feature sets across four slices, with no cross-slice dependencies between the first three features — enabling parallel development with a trailing E2E + docs slice.

**Event Log Polish (S01)** enriched the event log detail view with SHACL-derived metadata. Two new methods on ShapesService — `get_labels_for_predicates()` and `get_helptext_for_predicates()` — iterate both typed `sh:PropertyShape` nodes and inline blank nodes linked via `sh:property` to resolve predicate IRIs to human-readable labels and helptext. The event detail route now injects these as template context, rendering labels like "Title" instead of raw "dcterms:title" with dotted-underline tooltips showing SHACL descriptions. Three suggestion endpoints (`suggest-types`, `suggest-predicates`, `suggest-objects`) query real event data via SPARQL and return HTML fragments through a shared `_event_suggestions.html` template. The event log filter area was upgraded from a static dropdown to three text inputs with htmx-driven autocomplete. A critical discovery during implementation: installed model shapes use inline blank nodes via `sh:property` without explicit `rdf:type sh:PropertyShape` — requiring dual-path iteration (D161).

**Body.Diff (S02)** introduced incremental storage for body edits. A new `body.diff` operation type stores both the full new body and a unified diff as `sempkm:bodyDiff` data triples. The `save_body()` endpoint now queries `urn:sempkm:current` for existing content and branches three ways: body.diff for changes, body.set for first body, no-op for unchanged. The event log viewer renders both operation types with the same diff highlighting CSS. Undo support via `build_compensation()` reconstructs the old body from the stored diff by reverse-applying it. A diff normalization fix was needed — `difflib.unified_diff` with `lineterm=""` produces header lines without trailing newlines, which broke both parsing and reverse application.

**Workspace Personas (S03)** added a complete persona system. The Persona SQLAlchemy model (9 columns, Alembic migration 013) stores dockview layout JSON, sidebar panel positions, and explorer mode per named configuration. PersonaService enforces single-active-per-user via bulk-deactivate + targeted-activate, with auto-activation of the first remaining persona on delete. The sidebar user popover gained a persona selector section between Layouts and the theme row, loaded eagerly via htmx. Three command palette entries ("Switch To...", "Save Current", "Create New...") with dynamic submenu populate via `_refreshPersonaPaletteItems()`. The frontend lifecycle handles init (auto-creating "Default" on first load), save (capturing current workspace state), switch (with `_switchingPersona` guard flag bridged via `window.*` to prevent localStorage corruption during `dv.fromJSON()`), and beforeunload (via `navigator.sendBeacon` for reliable state persistence).

**E2E Tests & User Guide (S04)** unified all features with 12 Playwright tests across three spec files and comprehensive documentation. A rate limiting issue was discovered and fixed — auth fixture failures from slowapi required a `RATE_LIMIT_ENABLED` config toggle (D158), disabled in the test stack. A template bug was also fixed: `event_log.html` only enabled Diff/Undo buttons for body.set, missing body.diff. Chapter 15 gained 4 new sections (predicate labels, helptext tooltips, autocomplete filters, body diff events). Chapter 30 was created for personas with 7 sections. Glossary entries for "Body Diff" and "Persona" were added.

## Cross-Slice Verification

All 10 success criteria from the roadmap verified:

| # | Success Criterion | Evidence |
|---|-------------------|----------|
| 1 | Predicate labels show human-readable text (e.g., "Title" not "dcterms:title") | S01 browser verification + S04 E2E test `event-log-polish.spec.ts` test 1 |
| 2 | Helptext tooltip on predicate hover from SHACL annotations | S01 HTML title attributes + S04 E2E test `event-log-polish.spec.ts` test 2 |
| 3 | Autocomplete for operation types, predicates, and objects | S01 browser verification (3 filters, 9 operation types) + S04 E2E tests 3-4 |
| 4 | Body edit shows diff view with changed paragraph in green/red | S02 unified diff rendering + S04 E2E test `body-diff.spec.ts` test 2 |
| 5 | First-time body set uses body.set with full text display | S02 three-way branching logic + S04 E2E test `body-diff.spec.ts` test 3 |
| 6 | Two named personas with different layouts, switching restores correctly | S03 switchPersona() with layout/positions/mode restore + S04 E2E `personas.spec.ts` test 5 |
| 7 | Persona selector in user popover menu | S03 browser screenshot + S04 E2E `personas.spec.ts` test 3 |
| 8 | Personas via Ctrl+K command palette | S03 browser screenshot + S04 E2E `personas.spec.ts` test 4 |
| 9 | Default persona auto-created on first use | S03 console log verification + S04 E2E `personas.spec.ts` test 2 |
| 10 | Personas persist across Docker restarts (SQLite) | Alembic migration 013 creates personas table; PersonaService reads/writes via SQLAlchemy |

**Definition of Done verification:**

- ✅ All 4 slices marked `[x]` complete
- ✅ All 4 slice summaries exist with verification_result: passed
- ✅ 12 Playwright E2E tests pass (4 event log + 3 body.diff + 5 personas)
- ✅ 946 backend unit tests pass (including 37 event log + 34 body.diff + 20 persona)
- ✅ User guide docs updated: Chapter 15 (4 new sections) + Chapter 30 (new, 7 sections) + glossary
- ✅ All 11 requirements validated with unit tests, E2E tests, and documentation

## Requirement Changes

- EVTLOG-01: active → validated — Unit tests (20) + E2E test + docs (Ch 15 §Predicate Labels)
- EVTLOG-02: active → validated — Unit tests (20) + E2E test + docs (Ch 15 §Helptext Tooltips)
- EVTLOG-03: active → validated — Unit tests (17) + E2E tests + docs (Ch 15 §Autocomplete Filters)
- BDIFF-01: active → validated — Unit tests (34) + E2E test + docs (Ch 15 §Body Diff Events)
- BDIFF-02: active → validated — Unit tests (34) + E2E test + docs (Ch 15 §Body Diff Events)
- BDIFF-03: active → validated — E2E test (body.set creation for first body) + docs
- PERSONA-01: active → validated — Unit tests (20) + 7 API endpoints + E2E test + docs (Ch 30)
- PERSONA-02: active → validated — switchPersona() + browser verified + E2E test + docs (Ch 30 §Switching)
- PERSONA-03: active → validated — sidebar selector UI + browser screenshot + E2E test + docs
- PERSONA-04: active → validated — 3 command palette entries + E2E test + docs (Ch 30 §Switching)
- PERSONA-05: active → validated — initPersonas() auto-create + E2E test + docs (Ch 30 §Default Persona)

## Forward Intelligence

### What the next milestone should know
- **ShapesService dual-path iteration** is the canonical pattern for resolving predicate-level metadata from SHACL shapes. It handles both typed `sh:PropertyShape` nodes and inline blank nodes linked via `sh:property`. Any future code needing predicate labels or helptext should use `get_labels_for_predicates()` / `get_helptext_for_predicates()`, not re-query shapes directly.
- **body.diff is stored, not recomputed.** The `sempkm:bodyDiff` predicate in event graph data triples holds the raw unified diff. Old `body.set` events still compute diffs on-the-fly from before/after states. Both render through the same template path.
- **Persona API is at `/api/personas`** with standard CRUD. List returns metadata only (no layout_json). GET by ID returns full payload. The selector partial at `/browser/personas/selector` loads eagerly in the sidebar popover.
- **RATE_LIMIT_ENABLED pattern** is established for test environments. Future E2E test stacks should keep `RATE_LIMIT_ENABLED=false` in docker-compose.test.yml.
- **htmx autocomplete pattern** is established and reusable: text input → hx-trigger → shared `_event_suggestions.html` fragment → JS click handler. The template accepts `suggestions` (list of dicts with `value`, `label`, `filter_param` keys).

### What's fragile
- **ShapesService shapes graph caching** — `_fetch_shapes_graph()` is called per-request for label/helptext resolution. Under high event log traffic, this could become a bottleneck. The shapes graph changes only on model install/refresh.
- **Suggestion SPARQL scans all event graphs** — `SELECT DISTINCT` across all event named graphs. On repositories with thousands of events, these queries may become slow.
- **dv.fromJSON() reliability** — Layout restore is wrapped in try/catch with toast fallback, but if panel types change between save and restore, some panels may not restore. This is a known dockview limitation.
- **beforeunload sendBeacon** — Browser may not send the beacon in all cases (process kill, crash). localStorage continues as independent crash recovery.
- **Diff normalization** — The `save_body()` normalization loop is the only thing preventing malformed stored diffs. If someone stores a diff through a different code path without normalization, parsing will produce wrong content.
- **Pre-existing E2E syntax errors** — ~15-20 older spec files from earlier merge conflicts have syntax errors in directories 00-07, 18-19. Only targeted test directories (27-29) should be trusted for M012 verification.

### Authoritative diagnostics
- `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff tests/29-personas --project=chromium` — the definitive M012 E2E check (12 tests)
- `python -m pytest tests/test_event_log_labels.py tests/test_event_suggestions.py tests/test_body_diff.py tests/test_persona_service.py -v` — 91 unit tests covering all M012 service-layer contracts
- Browser: hover any `.diff-pred-label` element — the `title` attribute shows either SHACL helptext or the full predicate IRI
- `GET /api/personas` — shows all personas for current user with active indicator
- Backend logs: `"Failed to resolve predicate labels from shapes graph"` or `"Failed to resolve predicate helptext from shapes graph"` warnings indicate shapes service issues

### What assumptions changed
- **Assumption:** `rdf:type sh:PropertyShape` iteration finds all property shapes → **Reality:** Installed models use inline blank nodes via `sh:property` without explicit type triples. Both iteration paths required (D161).
- **Assumption:** `difflib.unified_diff` with `lineterm=""` produces clean output → **Reality:** Header lines lack trailing newlines, requiring per-line normalization before storage.
- **Assumption:** ninja-keys children auto-discover by parent property → **Reality:** Parent's `children` array must contain child IDs explicitly for drill-down navigation.
- **Assumption:** SPARQL API can query event data → **Reality:** It scopes to `urn:sempkm:current` only. Event verification requires event log UI or event detail API endpoint.
- **Assumption:** body.diff template was ready → **Reality:** Diff/Undo buttons needed body.diff added to their enabled operation type lists.

## Files Created/Modified

- `backend/app/services/shapes.py` — added `get_labels_for_predicates()` and `get_helptext_for_predicates()` with dual-path PropertyShape iteration
- `backend/app/browser/events.py` — ShapesService/LabelService deps, 3 suggestion endpoints, predicate filter with chip
- `backend/app/events/query.py` — `predicate_iri` filter, `_parse_stored_diff()`, `_reverse_apply_diff()`, body.diff in `get_event_detail()` and `build_compensation()`
- `backend/app/commands/handlers/body_diff.py` — new handler for body.diff operations
- `backend/app/commands/schemas.py` — BodyDiffParams, BodyDiffCommand, updated Command union
- `backend/app/commands/dispatcher.py` — registered body.diff handler
- `backend/app/commands/router.py` — body.diff webhook event mapping
- `backend/app/browser/objects.py` — save_body() three-way branching + diff normalization
- `backend/app/persona/__init__.py` — persona module init
- `backend/app/persona/models.py` — Persona SQLAlchemy model (9 columns)
- `backend/app/persona/service.py` — PersonaService with 8 async methods
- `backend/app/persona/router.py` — REST API (7 endpoints) + browser selector route
- `backend/migrations/versions/013_personas.py` — Alembic migration creating personas table
- `backend/app/main.py` — PersonaService instantiation + router registration
- `backend/app/config.py` — RATE_LIMIT_ENABLED setting
- `backend/app/auth/rate_limit.py` — pass enabled flag to slowapi Limiter
- `backend/app/templates/browser/event_detail.html` — label/helptext rendering + body.diff support
- `backend/app/templates/browser/event_log.html` — autocomplete inputs + body.diff Diff/Undo buttons
- `backend/app/templates/browser/_event_suggestions.html` — shared suggestion dropdown fragment
- `backend/app/templates/components/_persona_selector.html` — persona selector partial
- `backend/app/templates/components/_sidebar.html` — persona selector container in user popover
- `frontend/static/js/workspace.js` — persona lifecycle (init, save, switch, create, command palette, beforeunload)
- `frontend/static/js/workspace-layout.js` — _switchingPersona guard in onDidLayoutChange
- `frontend/static/css/workspace.css` — autocomplete dropdown + persona selector styling
- `backend/tests/test_event_log_labels.py` — 20 unit tests for label/helptext resolution
- `backend/tests/test_event_suggestions.py` — 17 unit tests for suggestion endpoints
- `backend/tests/test_body_diff.py` — 34 unit tests for body.diff handler/rendering/undo
- `backend/tests/test_persona_service.py` — 20 unit tests for persona service
- `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — 4 E2E tests
- `e2e/tests/28-body-diff/body-diff.spec.ts` — 3 E2E tests
- `e2e/tests/29-personas/personas.spec.ts` — 5 E2E tests
- `docs/guide/15-event-log.md` — 4 new sections (predicate labels, helptext, autocomplete, body diff)
- `docs/guide/30-personas.md` — new chapter (7 sections)
- `docs/guide/README.md` — Chapter 30 in TOC
- `docs/guide/29-mental-model-catalog.md` — navigation footer → Chapter 30
- `docs/guide/appendix-d-glossary.md` — Body Diff and Persona entries
- `docker-compose.test.yml` — RATE_LIMIT_ENABLED: false
