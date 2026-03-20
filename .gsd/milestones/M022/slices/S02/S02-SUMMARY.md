---
id: S02
parent: M022
milestone: M022
provides:
  - Pull sync engine with two-phase bulk create for Asana tasks → bpkm:Task objects
  - Configurable field mapper with 3-mode status extraction (completed_only, custom_field, section)
  - Subtask recursion bounded at 5 levels with dcterms:isPartOf parent linking
  - Person matcher with SPARQL email lookup, create-on-miss, LRU cache
  - poll_tasks handler wired to pull_sync, sync_now POST route for on-demand sync
  - Milestone detection (resource_subtype: "milestone" → bpkm:Milestone type)
  - HTML→Markdown conversion for html_notes with plain notes fallback
requires:
  - slice: S01
    provides: OAuth/PAT auth, AsanaClient with opt_fields/pagination/rate-limit, persisted field mapping config (status_source, status_field_gid, status_mapping, priority_field_gid, priority_mapping, story_points_field_gid)
affects:
  - S03
key_files:
  - apps/asana-sync/services/field_mapper.py
  - apps/asana-sync/services/person_matcher.py
  - apps/asana-sync/services/sync_engine.py
  - apps/asana-sync/app.py
  - backend/tests/test_asana_field_mapper.py
  - backend/tests/test_asana_person_matcher.py
  - backend/tests/test_asana_sync_engine.py
key_decisions:
  - Tuple return (type_iri, properties) from build_task_properties — cleaner separation between type selection (milestone vs task) and property extraction for sync engine consumption
  - Slug format is asana-{gid} — Asana GIDs are already unique stable identifiers, no hashing needed
  - get_connection_status takes only state_client (no http_client) — simpler interface than originally planned
  - sync_now route returns HTML fragment (consistent with htmx pattern) while storing JSON in StateClient for programmatic access
patterns_established:
  - Configurable field extraction via field_config dict — status_source selects extraction mode, *_field_gid keys select custom fields by GID, *_mapping dicts provide value translation. Reusable for any provider with custom-field-based status/priority.
  - Subtask recursion via _fetch_subtasks_recursive with _parent_gid annotation on each subtask dict for edge creation in Phase 2
  - Phase 2 slug→IRI discovery for body.set + edge.create after bulk object.create commands
observability_surfaces:
  - asana.sync.engine logger — pull_sync start/complete, per-task error warnings, subtask recursion depth
  - last_pull_result StateClient key (JSON with status, created, updated, errors, duration_ms, timestamp)
  - last_sync_at cursor for incremental sync via modified_since parameter
  - Per-task error_details list (task_gid, project_gid, error message) with overall status (success/partial/error/skipped)
drill_down_paths:
  - .gsd/milestones/M022/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M022/slices/S02/tasks/T02-SUMMARY.md
duration: 50min
verification_result: passed
completed_at: 2026-03-19
---

# S02: Pull sync with configurable field transforms + subtask nesting

**Asana tasks sync into SemPKM as bpkm:Task objects with status/priority mapped via S01's configurable field mapping, subtasks nested up to 5 levels via dcterms:isPartOf, and 168 passing tests.**

## What Happened

T01 built the pure transform layer — field_mapper.py (~350 lines) with `build_task_properties()` that reads a `field_config` dict for configurable status/priority extraction. The core novelty is `extract_status()` which reads `field_config["status_source"]` to select between three modes: `completed_only` (boolean map), `custom_field` (enum field matched by GID in custom_fields array, lookup enum_value.name in status_mapping), and `section` (section name lookup in status_mapping). Each mode falls back to the completed boolean when no match is found. Priority and story points similarly extract from custom fields by GID. HTML→Markdown uses conditional markdownify import with regex fallback. person_matcher.py (~130 lines) is a direct clone from Linear — SPARQL email lookup, create-on-miss, case-insensitive LRU cache.

T02 built the sync engine (~450 lines) following the established Todoist/Linear two-phase bulk pattern. `pull_sync(ctx)` reads field config from StateClient, iterates selected projects, fetches tasks with opt_fields and modified_since, classifies create vs update via SPARQL lookup, builds commands using field_mapper, then executes Phase 1 (bulk create) and Phase 2 (slug→IRI discovery for body.set + edge.create). `_fetch_subtasks_recursive()` walks the Asana subtask tree up to `MAX_SUBTASK_DEPTH=5` levels, annotating each subtask with `_parent_gid` for `dcterms:isPartOf` edge creation. Tasks with `resource_subtype: "milestone"` create bpkm:Milestone objects. Per-task error isolation with try/except preserves partial progress. The poll_tasks handler was wired to call pull_sync, and a sync_now POST route was added for on-demand triggering.

## Verification

- **168 tests pass** in 0.14s: 92 field mapper + 18 person matcher + 58 sync engine
- All 4 source files pass `ast.parse()` syntax validation
- Diagnostic surface confirmed: `test_last_pull_result_stored` asserts `created`, `errors`, `duration_ms`, `timestamp` keys
- All 3 status modes tested (completed_only, custom_field, section)
- Subtask recursion tested at 1, 3, and 5 levels with max depth enforcement
- Per-task error isolation tested (one task fails, others continue)
- Incremental sync via modified_since tested (first sync sends None, subsequent sends cursor)
- Loop prevention via lastSyncedAt comparison tested

## Requirements Advanced

- ASANA-05 (pull sync) — pull_sync creates bpkm:Task objects with all mapped fields from Asana tasks
- ASANA-06 (subtask nesting) — subtasks up to 5 levels linked via dcterms:isPartOf
- ASANA-07 (tag mapping) — Asana tags extracted and mapped to SemPKM tags
- ASANA-08 (follower mapping) — followers extracted to person edge commands via person matcher

## Requirements Validated

None moved to validated — full validation requires E2E testing in S04.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- `get_connection_status` takes only `state_client` (not `state_client + http_client` as plan suggested) — adapted from actual S01 implementation.
- Test counts exceeded targets: 92 field mapper (plan: 50+), 18 person matcher (plan: 10+), 58 sync engine (plan: 40+).
- Person matcher tests initially used deprecated `asyncio.get_event_loop().run_until_complete()` — fixed to `asyncio.run()`.

## Known Limitations

- Pull sync only — no push capability yet (S03 scope).
- No section-based status push (S03 will implement section move API).
- No settings UI for sync direction/interval (S03 scope).
- sync_now route returns HTML fragment — no JSON API endpoint for programmatic triggering outside the workspace UI.

## Follow-ups

None — all planned work completed. S03 takes over with push sync and section-based status moves.

## Files Created/Modified

- `apps/asana-sync/services/field_mapper.py` — New. ~350 lines. Pure field mapping functions with 3-mode configurable status extraction, priority mapping, tag/follower extraction, HTML→Markdown, milestone detection, slug computation.
- `apps/asana-sync/services/person_matcher.py` — New. ~130 lines. SPARQL email lookup + create-on-miss + LRU cache, cloned from Linear.
- `apps/asana-sync/services/sync_engine.py` — New. ~450 lines. Pull sync pipeline with two-phase bulk create, subtask recursion bounded at 5 levels, incremental sync, per-task error isolation.
- `apps/asana-sync/app.py` — Modified. poll_tasks wired to pull_sync, sync_now route added.
- `backend/tests/test_asana_field_mapper.py` — New. 92 tests covering all extraction paths.
- `backend/tests/test_asana_person_matcher.py` — New. 18 tests covering email match, cache, creation.
- `backend/tests/test_asana_sync_engine.py` — New. 58 tests covering guards, create/update, subtasks, errors, incremental sync, diagnostics.

## Forward Intelligence

### What the next slice should know
- The field_mapper returns `(type_iri, properties_dict)` — the sync engine unpacks this to set the type on object.create and the properties separately. Push sync needs to reverse-map properties back to Asana fields using the same field_config dict.
- `_read_field_config(ctx)` in sync_engine.py reads all StateClient keys and builds the dict — push sync should reuse this function rather than reimplementing config reading.
- Section-based status push requires a different API call pattern (POST /sections/{gid}/addTask) vs custom field PATCH. The status_source in field_config tells you which path to take.
- The sync_now route is at `/_fragments/sync-now` — push sync should add a corresponding trigger mechanism.

### What's fragile
- Subtask recursion relies on Asana's `get_subtasks` endpoint returning complete data — if the API changes pagination behavior for subtask endpoints, the depth-bounded recursion may need adjustment.
- The `_parent_gid` annotation on subtask dicts is a convention (private key prefixed with underscore) — it's not a real Asana field. If field_mapper ever validates/strips unknown keys, this will break.

### Authoritative diagnostics
- `last_pull_result` StateClient key — JSON with full sync stats (status, created, updated, errors, error_details, duration_ms, timestamp). Most trustworthy signal for sync health.
- `asana.sync.engine` logger — per-task error warnings include task GID and project GID for debugging.

### What assumptions changed
- Plan assumed get_connection_status takes (state_client, http_client) — actual S01 implementation takes only state_client. No functional impact.
