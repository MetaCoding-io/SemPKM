# S02: Pull sync with configurable field transforms + subtask nesting

**Goal:** Asana tasks (including subtasks up to 5 levels, tags, assignees/followers) sync into SemPKM as bpkm:Task objects with status/priority mapped via the S01-configured field mapping.
**Demo:** User triggers sync and Asana tasks appear as correctly-mapped bpkm:Task objects — status comes from the configured source (completed_only, custom_field, or section), priority from custom enum field mapping, subtasks nested via dcterms:isPartOf edges, tags/followers/story points preserved.

## Must-Haves

- `field_mapper.py` with `build_task_properties()` that reads a `field_config` dict for configurable status/priority transforms — all three status modes (completed_only, custom_field, section) working
- `person_matcher.py` with SPARQL email lookup, create-on-miss, LRU cache (clone from Linear)
- `sync_engine.py` with `pull_sync(ctx)` implementing two-phase bulk create, subtask recursion bounded at 5 levels, per-task error isolation, incremental sync via `modified_since`
- `app.py` `poll_tasks` handler wired to call `pull_sync()`, `sync_now` route added
- 100+ tests across three test files, all passing with `--noconftest`
- Milestone detection: tasks with `resource_subtype: "milestone"` create `bpkm:Milestone` type
- HTML→Markdown conversion for `html_notes` via markdownify with plain `notes` fallback

## Proof Level

- This slice proves: contract (pure function tests + async mock tests prove all transform and orchestration paths)
- Real runtime required: no (all tests use mocks)
- Human/UAT required: no

## Verification

- `pytest backend/tests/test_asana_field_mapper.py -v --noconftest` — 50+ tests pass covering all 3 status modes, priority mapping, tag extraction, milestone detection, HTML→Markdown, date truncation, slug computation, follower extraction
- `pytest backend/tests/test_asana_person_matcher.py -v --noconftest` — 10+ tests pass covering email match, cache hit, person creation
- `pytest backend/tests/test_asana_sync_engine.py -v --noconftest` — 40+ tests pass covering auth guard, no-projects guard, new task creation, existing task update, loop prevention, trashed→cancelled, subtask recursion (1 level, 3 levels, max depth enforcement), per-task error isolation, incremental sync
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/person_matcher.py').read())"` — syntax valid
- Verify diagnostic surface: at least one test asserts `last_pull_result` state contains `created`, `errors`, `duration_ms` fields

## Observability / Diagnostics

- Runtime signals: `asana.sync.engine` logger — pull_sync start/complete, per-task errors, subtask recursion depth, rate limit retries
- Inspection surfaces: `last_pull_result` StateClient key (JSON with status, created, updated, errors, duration_ms, timestamp), `last_sync_at` cursor for incremental sync
- Failure visibility: per-task error isolation with `error_details` list (task_gid, project_gid, error message), overall status ("success"/"partial"/"error"/"skipped")
- Redaction constraints: none (no secrets in sync data)

## Integration Closure

- Upstream surfaces consumed: `apps/asana-sync/services/auth.py` (`get_connection_status`), `apps/asana-sync/services/asana_client.py` (`AsanaClient` with `get_tasks`, `get_subtasks`), StateClient keys from S01 (`selected_projects`, `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, `story_points_field_gid`)
- New wiring introduced in this slice: `poll_tasks` handler calls `pull_sync()`, `sync_now` route triggers pull on demand
- What remains before the milestone is truly usable end-to-end: S03 (push sync + section-based status moves), S04 (E2E tests + mock server + user guide)

## Tasks

- [x] **T01: Build field mapper and person matcher with tests** `est:2h`
  - Why: Pure transform layer — all field mapping logic must be proven before the sync engine can use it. The field mapper is the riskiest file because it handles the novel configurable transforms (three status modes from StateClient config). Person matcher is a trivial clone but must exist for T02.
  - Files: `apps/asana-sync/services/field_mapper.py`, `apps/asana-sync/services/person_matcher.py`, `backend/tests/test_asana_field_mapper.py`, `backend/tests/test_asana_person_matcher.py`
  - Do: Build field_mapper.py (~350-400 lines) with `build_task_properties(task, field_config, section_name)` that extracts all bpkm:Task properties from an Asana task dict using the field_config for configurable status/priority. Three status extraction paths: completed_only (map completed boolean), custom_field (match by GID in custom_fields array, lookup enum_value.name in status_mapping), section (lookup section_name in status_mapping). Priority via custom field GID + priority_mapping. Tag extraction from `tags[].name`. HTML→Markdown via markdownify for html_notes with notes fallback. Milestone detection via `resource_subtype: "milestone"`. Story points from number custom field. `compute_task_slug(task)`. Follower extraction to list of {email, name} dicts. Build person_matcher.py (~140 lines) cloned from `apps/linear-sync/services/person_matcher.py` with zero functional changes. Write 50+ field mapper tests and 10+ person matcher tests, all self-contained with mocks.
  - Verify: `pytest backend/tests/test_asana_field_mapper.py backend/tests/test_asana_person_matcher.py -v --noconftest` — all pass
  - Done when: 60+ tests pass, all three status modes proven, priority mapping proven, milestone detection proven, HTML→Markdown proven

- [x] **T02: Build sync engine, wire app.py poll handler, and add sync-now route** `est:2h`
  - Why: Orchestration layer — wires client, field mapper, and person matcher into the complete pull sync pipeline. Includes the novel subtask recursion bounded at 5 levels. Replaces the skeleton poll_tasks handler with real sync logic and adds a Sync Now trigger route.
  - Files: `apps/asana-sync/services/sync_engine.py`, `apps/asana-sync/app.py`, `backend/tests/test_asana_sync_engine.py`
  - Do: Build sync_engine.py (~400-450 lines) with `pull_sync(ctx)` following the Todoist/Linear two-phase bulk pattern. Steps: read field config from StateClient → iterate selected projects → get_tasks with opt_fields and modified_since → classify create/update via SPARQL lookup → build commands using field_mapper → Phase 1 bulk create → Phase 2 SPARQL discover IRIs + body.set + edge.create → update commands. Add `_fetch_subtasks_recursive(client, task_gid, opt_fields, depth, max_depth=5)` that fetches direct children and recurses with depth+1, collecting all subtask dicts with their parent_gid annotated. Subtask→parent linking via `dcterms:isPartOf` edge.create commands. Per-task error isolation with try/except around each task. Store `last_pull_result` and `last_sync_at` in StateClient. Wire `poll_tasks` in app.py to call `pull_sync(ctx)`. Add `sync_now` POST route handler. Write 40+ sync engine tests covering all guard paths, create/update flows, subtask recursion at multiple depths, max depth enforcement, loop prevention via lastSyncedAt, per-task error isolation, and incremental sync. Use `--noconftest` and bypass SDK IRI prefix via `ctx.commands._client`.
  - Verify: `pytest backend/tests/test_asana_sync_engine.py -v --noconftest` — all pass; `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — syntax valid
  - Done when: 40+ sync engine tests pass, poll_tasks calls pull_sync, sync_now route exists, subtask recursion proven at 1/3/5 levels with max depth enforcement

## Files Likely Touched

- `apps/asana-sync/services/field_mapper.py` (new)
- `apps/asana-sync/services/person_matcher.py` (new)
- `apps/asana-sync/services/sync_engine.py` (new)
- `apps/asana-sync/app.py` (modify — wire poll_tasks, add sync_now)
- `backend/tests/test_asana_field_mapper.py` (new)
- `backend/tests/test_asana_person_matcher.py` (new)
- `backend/tests/test_asana_sync_engine.py` (new)
