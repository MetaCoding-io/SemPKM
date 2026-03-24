---
id: T02
parent: S05
milestone: M038
provides:
  - Async lifecycle hooks wiring context_service into app startup/shutdown
  - POST /_fragments/entry/{entry_iri}/status route for entry status mutations
  - GET /_fragments/current-suggestion/json endpoint for mobile app consumption
  - Today view action buttons (complete/skip/save) with htmx wiring
  - 29 new tests covering all new routes, lifecycle, and template assertions
key_files:
  - apps/media-scheduler/app.py
  - apps/media-scheduler/frontend/templates/today.html
  - apps/media-scheduler/frontend/static/styles.css
  - backend/tests/test_media_scheduler.py
key_decisions:
  - Used JSONResponse from starlette instead of manual json.dumps for the JSON endpoint — cleaner content-type handling
  - Entry status route returns a minimal HTML fragment (status badge + done class) for htmx outerHTML swap rather than re-rendering the full entry card
patterns_established:
  - _make_request() test helper for building mock Starlette Request objects with path_params, form_data, and wired ctx
observability_surfaces:
  - entry_status.updated log (INFO) with IRI and status on successful patch
  - entry_status.patch_failed log (WARNING) on object.patch failure
  - JSON endpoint returns {"status": "none", "error": "..."} on SPARQL failure
  - on_startup/on_shutdown log context listener spawn/cancel
duration: 18m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: App wiring — lifecycle hooks, entry status route, JSON suggestion endpoint, today UI buttons

**Wired context_service into app lifecycle, added entry status mutation route and JSON suggestion endpoint, added complete/skip/save action buttons to today view — 29 new tests all passing (395 total).**

## What Happened

1. **Context service import + lifecycle hooks** — Added importlib fallback block for `context_service` (matching the pattern of podcast_service, plan_service, etc.). Changed `on_startup` and `on_shutdown` from sync to async, calling `start_context_listener(ctx)` and `stop_context_listener()` respectively.

2. **Entry status route** (`POST /_fragments/entry/{entry_iri}/status`) — Validates status is one of `completed`, `skipped`, `saved` (returns 400 otherwise). Calls `ctx.commands.execute("object.patch", ...)` to update `entryStatus`. Returns a minimal HTML fragment with the status badge and `ms-entry-done` class for htmx `outerHTML` swap.

3. **JSON suggestion endpoint** (`GET /_fragments/current-suggestion/json`) — Reuses the same `TODAY_PLAN_SPARQL` query, extracts `sourceType`, `enclosureUrl`, `duration`, `sourceTitle` from the linked mediaItem. Returns `{title, slot_start, slot_end, status, source_type, source_title, enclosure_url, duration_seconds}`. Returns `{"status": "none"}` when no current/next entry exists.

4. **Today view action buttons** — Added `.ms-entry-actions` div with three buttons (✓ Complete, → Skip, ♡ Save) per entry. Buttons use `hx-post` to the entry status route with the `/app/media-scheduler/` proxy prefix. Entries with terminal status (`completed`, `skipped`, `saved`) show a done badge instead of action buttons. Updated both `today_fragment()` and `plan_generate_fragment()` to pass `entry_iri` from the SPARQL `?entry` binding.

5. **CSS** — Added `.ms-entry-actions`, `.ms-action-btn`, and per-action hover color styles. Added `.ms-entry-done` for terminal-status display. Added `.ms-status-saved` badge style.

6. **Tests** — 29 new tests across 4 test classes: `TestEntryStatusRoute` (8), `TestSuggestionJSON` (8), `TestLifecycleContext` (4), `TestTodayTemplateActions` (9).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` — **395 passed** in 1.21s
- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -k "TestEntryStatusRoute or TestSuggestionJSON or TestLifecycleContext or TestTodayTemplateActions" -v` — **29 passed**
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — clean parse
- `grep -q "/_fragments/current-suggestion/json" apps/media-scheduler/app.py` — present
- `grep -q "/_fragments/entry/" apps/media-scheduler/app.py` — present
- `grep -q "ms-entry-actions" apps/media-scheduler/frontend/templates/today.html` — present

### Slice-level checks (T02 scope):
- 395 tests pass (≥380 required) ✅
- `grep -c "def test_"` returns 395 (≥380 required) ✅
- app.py clean parse ✅
- context_service.py clean parse ✅
- JSON endpoint exists ✅
- Entry status route exists ✅
- Mobile checks (getMediaSuggestion, MediaSuggestion component) — T03 scope, not yet applicable

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -v` | 0 | ✅ pass | 1.21s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` | 0 | ✅ pass | <0.1s |
| 3 | `grep -q "/_fragments/current-suggestion/json" apps/media-scheduler/app.py` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "/_fragments/entry/" apps/media-scheduler/app.py` | 0 | ✅ pass | <0.1s |
| 5 | `grep -q "ms-entry-actions" apps/media-scheduler/frontend/templates/today.html` | 0 | ✅ pass | <0.1s |
| 6 | `grep -c "def test_" backend/tests/test_media_scheduler.py` → 395 | 0 | ✅ pass | <0.1s |

## Diagnostics

- **Entry status changes:** `grep "entry_status" <log>` — shows updated/failed status changes with IRIs
- **JSON endpoint failures:** `grep "current-suggestion-json SPARQL" <log>` — SPARQL query failures
- **Lifecycle wiring:** `grep "context listener" <log>` — confirms spawn on startup, cancel on shutdown
- **Runtime inspection:** `get_context_subscription_status()` returns `{connected, last_event_at, debounce_pending, reconnect_count}` — confirms SSE listener is running

## Deviations

- Added `json` import and `JSONResponse` from starlette instead of manually constructing response with `json.dumps()` — cleaner and handles content-type automatically.
- Added `unquote` from `urllib.parse` for proper URL-decoded entry IRI handling in the status route.
- Added `_make_request()` helper function in tests to reduce boilerplate across the 4 new test classes.
- 29 tests instead of planned 25 — template assertions were naturally more granular.

## Known Issues

None.

## Files Created/Modified

- `apps/media-scheduler/app.py` — Added context_service import block, async lifecycle hooks, entry status route, JSON suggestion endpoint, entry_iri in today/plan template data (~110 lines added)
- `apps/media-scheduler/frontend/templates/today.html` — Added action buttons (complete/skip/save) per entry with htmx wiring and conditional done-state display
- `apps/media-scheduler/frontend/static/styles.css` — Added `.ms-entry-actions`, `.ms-action-btn`, per-action hover colors, `.ms-entry-done`, `.ms-status-saved`
- `backend/tests/test_media_scheduler.py` — Added 29 test functions across 4 new test classes, added new symbol imports from _app_mod
- `.gsd/milestones/M038/slices/S05/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
