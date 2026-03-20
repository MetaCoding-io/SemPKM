---
id: S03
parent: M022
milestone: M022
provides:
  - reverse_status_mapping() — bpkm status → Asana enum option name / section name / completed bool (3 modes)
  - reverse_priority_mapping() — bpkm priority → Asana enum option name
  - build_asana_patch() — assembles PATCH body with GID-resolved enum values
  - resolve_section_gid_for_status() — bpkm status → section GID via discovered_sections
  - _find_changed_tasks() — SPARQL query detecting locally-changed Asana tasks (externalProvider="asana")
  - push_sync(ctx) — full push pipeline with two-path dispatch (custom field PATCH + section move)
  - sync-config POST route saving sync_direction and poll_interval
  - bidirectional sync_now (pull + conditional push)
  - push_changes task handler wired to push_sync()
  - settings UI with sync direction, poll interval, Sync Now button, pull/push stats
requires:
  - slice: S01
    provides: OAuth/PAT auth, AsanaClient (patch_task, add_task_to_section), field mapping config in StateClient
  - slice: S02
    provides: field_mapper.py (forward mapping patterns, _read_field_config), sync_engine.py (pull_sync, _submit_commands_batched), person_matcher
affects:
  - S04
key_files:
  - apps/asana-sync/services/field_mapper.py
  - apps/asana-sync/services/sync_engine.py
  - apps/asana-sync/app.py
  - apps/asana-sync/frontend/templates/connect_status.html
  - backend/tests/test_asana_field_mapper.py
  - backend/tests/test_asana_sync_engine.py
key_decisions:
  - Two-path push dispatch — build_asana_patch for custom fields/completed → patch_task; resolve_section_gid_for_status → add_task_to_section. Both can fire on the same task (section status + priority change).
  - Skip (not error) when a changed task produces no reverse-mappable fields — prevents false error noise
  - Reverse mapping returns structured dicts with "type" discriminator (custom_field/section/completed) so push engine dispatches correctly
patterns_established:
  - Reverse mapping pattern: invert {AsanaName: bpkmValue} → {bpkmValue: AsanaName}, then lookup by bpkm value, then resolve GID from discovered_enum_fields
  - Sync app settings pattern: sync-config route + bidirectional sync_now + stats display via stat-group/stat-row — identical in Linear and Asana apps
  - _PatchedPushSync context manager for isolated push tests — patches both AsanaClient and _find_changed_tasks
observability_surfaces:
  - StateClient keys: sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result
  - last_push_result schema: {status, pushed, skipped, errors, error_details}
  - Logger "asana.sync.engine" — push_sync start/complete, per-task push, section move, per-task errors
  - Template stat-group/stat-row blocks render pull/push results visually
drill_down_paths:
  - .gsd/milestones/M022/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M022/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M022/slices/S03/tasks/T03-SUMMARY.md
duration: 52m
verification_result: passed
completed_at: 2026-03-19
---

# S03: Push sync + section-based status moves

**Added bidirectional push sync to Asana with two-path dispatch (custom field PATCH + section move), reverse field mapping, settings UI, and 59 new tests bringing the total to 209.**

## What Happened

T01 added 5 reverse mapping functions to field_mapper.py — pure functions converting bpkm properties back to Asana API format. `reverse_status_mapping()` handles all 3 status_source modes (custom_field → enum option name, section → section name, completed_only → boolean). `reverse_priority_mapping()` inverts the priority dict. `build_asana_patch()` assembles the PATCH body resolving enum option names to GIDs via `_resolve_enum_option_gid()` scanning discovered_enum_fields. `resolve_section_gid_for_status()` maps bpkm status → section GID via discovered_sections. 33 tests across 5 test classes.

T02 built the push_sync pipeline in sync_engine.py. `_find_changed_tasks()` uses a SPARQL query filtering for `externalProvider="asana"` tasks modified since last sync. `push_sync()` orchestrates: auth check → direction guard → read field config + discovered data → find changed tasks → for each: build patch → PATCH custom fields + add_task_to_section → update lastSyncedAt → store last_push_result. The two-path dispatch is the core novelty: when status_source is "section" and status changed, the engine calls `add_task_to_section()` for the section move; when there's a priority change, it additionally calls `patch_task()`. Both paths can fire on the same task. Per-task error isolation. 26 tests.

T03 wired everything into the app surface. sync-config POST route saves sync_direction and poll_interval. sync_now runs pull then conditionally push when bidirectional. push_changes handler calls push_sync(). Template gained three new sections: sync configuration (direction radios + poll interval dropdown), manual sync (Sync Now button with htmx indicator), and sync stats (pull/push stat-group/stat-row displays). All htmx URLs use `/app/asana-sync/` prefix per KNOWLEDGE.md.

## Verification

- `uv run pytest tests/test_asana_field_mapper.py tests/test_asana_sync_engine.py -q` — **209 passed** (125 field mapper + 84 sync engine)
- `python3 -c "import ast; ast.parse(...)"` — syntax OK for all 3 source files (field_mapper.py, sync_engine.py, app.py)
- At least one test asserts `last_push_result` StateClient key has `pushed`, `errors`, `status` fields (diagnostic surface verified)
- Template contains 6 htmx POST URLs with `/app/asana-sync/` prefix, 12 stat-group/stat-row occurrences, 25 template variable references

## Requirements Advanced

- No formal ASANA requirements registered in REQUIREMENTS.md yet (pending S04/milestone completion). This slice delivers the push sync and settings UI capabilities that will satisfy ASANA-08 (push sync), ASANA-09 (section-based status moves), and ASANA-10 (settings UI) when formally registered.

## Requirements Validated

- None — ASANA requirements not yet registered in REQUIREMENTS.md

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None — all 3 tasks executed as planned.

## Known Limitations

- Push sync is tested via unit tests only — no E2E Playwright coverage yet (S04 scope)
- Settings UI not visually verified against running Docker stack (S04 E2E will cover this)
- No mock Asana REST API server for integration testing yet (S04 scope)

## Follow-ups

- S04: Mock Asana REST API server, Playwright E2E test, Chapter 40 user guide, README/glossary/nav-chain updates

## Files Created/Modified

- `apps/asana-sync/services/field_mapper.py` — Added ~95 lines: 4 public reverse mapping functions + 1 GID helper + 1 dict inversion helper
- `apps/asana-sync/services/sync_engine.py` — Added ~170 lines: _find_changed_tasks() SPARQL + push_sync() pipeline with two-path dispatch
- `apps/asana-sync/app.py` — Added sync-config route, bidirectional sync_now, push_changes wiring, extended _render_connect_status context (~50 new lines)
- `apps/asana-sync/frontend/templates/connect_status.html` — Added sync configuration, manual sync, and sync stats sections (~100 new lines)
- `backend/tests/test_asana_field_mapper.py` — Added ~250 lines: 33 new tests across 5 reverse mapping test classes
- `backend/tests/test_asana_sync_engine.py` — Added ~350 lines: 26 new push sync tests with mock infrastructure

## Forward Intelligence

### What the next slice should know
- The push sync pipeline follows the exact same pattern as Linear sync (M016/S03) — `_find_changed_tasks` SPARQL, `push_sync` orchestrator, `last_push_result` StateClient key. The mock Asana server should provide endpoints for PATCH /tasks/{gid} and POST /sections/{gid}/addTask.
- All htmx URLs in connect_status.html use `/app/asana-sync/` prefix — the mock server and E2E test must route through the app proxy.
- The settings UI clones Linear's stat-group/stat-row CSS pattern — no new CSS needed.

### What's fragile
- `_resolve_enum_option_gid()` scans discovered_enum_fields (a JSON blob from StateClient) looking for field GID match then option name match. If the discovered data structure changes shape, GID resolution silently returns None and the push skips the field update.

### Authoritative diagnostics
- `last_push_result` StateClient key — JSON with status/pushed/skipped/errors/error_details — is the single source of truth for push sync health
- Logger `asana.sync.engine` emits structured messages for every push phase

### What assumptions changed
- None — the slice executed exactly as planned. The two-path dispatch (PATCH + section move) pattern worked as designed.
