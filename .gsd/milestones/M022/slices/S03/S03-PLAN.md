# S03: Push sync + section-based status moves

**Goal:** User edits task status/priority in SemPKM, triggers push, and changes appear in Asana via reverse field mapping — including section moves for section-based status configuration.
**Demo:** Change a task's status from "todo" to "in_progress" in SemPKM, push sync, and the corresponding Asana task either has its custom field enum updated or gets moved to the correct section (depending on the user's status_source configuration). Priority changes push as custom field PATCH. Settings UI shows sync direction, poll interval, Sync Now, and push result stats.

## Must-Haves

- Reverse status mapping supporting both custom_field and section-based modes
- Reverse priority mapping with enum option GID resolution via discovered_enum_fields
- `build_asana_patch()` that assembles the PATCH body for custom field updates
- `resolve_section_gid_for_status()` that maps bpkm status → section GID via discovered_sections
- `_find_changed_tasks()` SPARQL query detecting locally-changed Asana tasks
- `push_sync()` pipeline: auth check → direction check → find changed → reverse map → PATCH/section move → update lastSyncedAt → store result
- Settings UI: sync direction radios, poll interval dropdown, Sync Now button, push result stats
- sync_now route runs push after pull when bidirectional
- push_changes task handler calls push_sync()
- All existing 168 Asana tests continue passing (no regressions)

## Proof Level

- This slice proves: contract
- Real runtime required: no
- Human/UAT required: no

## Verification

- `uv run pytest backend/tests/test_asana_field_mapper.py backend/tests/test_asana_sync_engine.py -q` — 200+ tests pass (168 existing + ~30 reverse mapping + ~30 push sync)
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"` — syntax OK
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` — syntax OK
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — syntax OK
- Diagnostic surface: at least one test asserts `last_push_result` StateClient key has `pushed`, `errors`, `status` fields

## Observability / Diagnostics

- Runtime signals: `asana.sync.engine` logger — push_sync start/complete, per-task push errors, section move vs PATCH path taken
- Inspection surfaces: `last_push_result` StateClient key (JSON with status, pushed, skipped, errors), `sync_direction` and `poll_interval` StateClient keys
- Failure visibility: per-task error_details in push result (task IRI, task GID, error message), overall status (ok/partial/error/skipped)
- Redaction constraints: none (no secrets in push data)

## Integration Closure

- Upstream surfaces consumed: `field_mapper.build_task_properties()` (forward mapping patterns), `_read_field_config()` (StateClient config reading), `AsanaClient.patch_task()` and `AsanaClient.add_task_to_section()` (push APIs), `discovered_enum_fields` and `discovered_sections` StateClient keys (GID resolution data)
- New wiring introduced: `push_sync()` called from `push_changes` task handler and `sync_now` route; `sync-config` settings route; settings UI in connect_status.html
- What remains before the milestone is truly usable end-to-end: S04 — E2E tests, mock Asana server, user guide

## Tasks

- [x] **T01: Add reverse mapping functions to field_mapper.py** `est:30m`
  - Why: Push sync needs to convert bpkm properties back to Asana API format. This is pure-function work with no I/O — testable in isolation and prerequisite for the push pipeline.
  - Files: `apps/asana-sync/services/field_mapper.py`, `backend/tests/test_asana_field_mapper.py`
  - Do: Add `reverse_status_mapping()` (invert status_mapping dict, support both custom_field and section modes), `reverse_priority_mapping()` (invert priority_mapping dict), `build_asana_patch()` (assemble custom_fields PATCH body resolving enum option names → GIDs via discovered_enum_fields), `resolve_section_gid_for_status()` (map bpkm status → section GID via discovered_sections). Each function takes the field_config dict + discovered data as input. Add ~30 unit tests covering both push paths, unknown values, empty mappings.
  - Verify: `uv run pytest backend/tests/test_asana_field_mapper.py -q` — 120+ tests pass (92 existing + ~30 new)
  - Done when: All 4 reverse mapping functions exist, tests pass, ast.parse succeeds, existing 92 tests still green

- [x] **T02: Build push_sync pipeline in sync_engine.py** `est:40m`
  - Why: Orchestrates the full push flow: find changed tasks → reverse map → call Asana API → update lastSyncedAt. The two-path push (custom field PATCH vs section move) is the core novelty of this slice.
  - Files: `apps/asana-sync/services/sync_engine.py`, `backend/tests/test_asana_sync_engine.py`
  - Do: Add `_find_changed_tasks()` SPARQL (clone from Linear, filter by externalProvider="asana"), `push_sync()` pipeline (auth→direction→find changed→read field config + discovered data→for each: reverse map→PATCH and/or section move→update lastSyncedAt→store last_push_result). Per-task error isolation. Read `discovered_enum_fields` and `discovered_sections` from StateClient for GID resolution. Add ~30 push sync unit tests covering: guards (not connected, pull-only, no changed), custom field push, section-based push, mixed push, per-task errors, lastSyncedAt update, diagnostic result storage.
  - Verify: `uv run pytest backend/tests/test_asana_sync_engine.py -q` — 85+ tests pass (58 existing + ~30 new)
  - Done when: push_sync() handles both push paths, tests pass, ast.parse succeeds, existing 58 tests still green

- [x] **T03: Add settings UI + route wiring in app.py and template** `est:30m`
  - Why: Completes the slice — users need UI controls for sync direction/interval, Sync Now needs to be bidirectional, push_changes handler needs to call push_sync(), and the template needs push result stats.
  - Files: `apps/asana-sync/app.py`, `apps/asana-sync/frontend/templates/connect_status.html`
  - Do: (1) Add `/_fragments/settings/sync-config` POST route saving sync_direction and poll_interval to StateClient. (2) Update sync_now route to run push after pull when bidirectional. (3) Wire push_changes handler to call push_sync(). (4) Update _render_connect_status to pass sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result to template. (5) Add sync config section (direction radios, interval dropdown), Sync Now section, and push/pull stats sections to connect_status.html — clone pattern from Linear's template. All htmx URLs must use `/app/asana-sync/` prefix per KNOWLEDGE.md.
  - Verify: `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — syntax OK. Template contains sync-config form, Sync Now button, stat-group/stat-row elements for both pull and push results.
  - Done when: Settings route saves config, sync_now runs bidirectional, push_changes calls push_sync, template shows all controls and stats

## Files Likely Touched

- `apps/asana-sync/services/field_mapper.py`
- `apps/asana-sync/services/sync_engine.py`
- `apps/asana-sync/app.py`
- `apps/asana-sync/frontend/templates/connect_status.html`
- `backend/tests/test_asana_field_mapper.py`
- `backend/tests/test_asana_sync_engine.py`
