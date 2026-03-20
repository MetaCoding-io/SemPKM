---
id: S02
parent: M023
milestone: M023
provides:
  - pull_sync(ctx) — complete Jira→bpkm:Task/Milestone pull pipeline with two-phase bulk create
  - push_sync(ctx) — stub returning skipped status (S03 implements real push)
  - app.py sync_now/poll-tasks/push-changes handlers wired to real sync functions
  - Epic→bpkm:Milestone creation with child task linking via parent.key and customfield_10014
  - ADF→Markdown description conversion integrated into pull pipeline
  - JQL construction with project keys, user JQL filter, and delta sync timestamp
  - Per-issue error isolation with structured result reporting
requires:
  - slice: S01
    provides: adf_converter (adf_to_markdown), field_mapper (build_task_properties, build_milestone_properties, compute_issue_slug), jira_client (JiraClient.search_all_issues), auth (get_connection_status), person_matcher (PersonMatcher.resolve), app scaffold (app.py with route handlers)
affects:
  - S03
key_files:
  - apps/jira-sync/services/sync_engine.py
  - apps/jira-sync/app.py
  - backend/tests/test_jira_sync_engine.py
key_decisions:
  - Result dict uses "success"/"partial"/"error" (not "ok") to match connect_status.html template's conditional rendering
  - Epic parent detection checks both next-gen parent.key and classic customfield_10014 (Epic Link custom field)
patterns_established:
  - Two-phase bulk create with Phase 3 epic→child linking (extends Linear/GCal two-phase pattern to three phases)
  - _build_jql() with project keys + user filter + ISO→JQL date conversion for delta sync
  - MockGraphClient with separate slug_map (Task) and milestone_slug_map (Milestone) for typed SPARQL routing in tests
  - MockSettingsClient separate from MockStateClient mirroring SDK ctx.settings vs ctx.state split
observability_surfaces:
  - ctx.state "last_pull_result" — JSON with status/created/updated/skipped/errors/failed_issues/duration_ms
  - ctx.state "last_push_result" — JSON with status/reason
  - Structured logging at INFO for all sync phases, WARNING for per-issue errors
drill_down_paths:
  - .gsd/milestones/M023/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M023/slices/S02/tasks/T02-SUMMARY.md
duration: 32m
verification_result: passed
completed_at: 2026-03-19
---

# S02: Pull sync + settings UI

**Jira pull sync engine creates bpkm:Task and bpkm:Milestone objects from Jira issues/epics with ADF→Markdown conversion, statusCategory-based status normalization, JQL-filtered delta sync, and per-issue error isolation — proven by 95 unit tests (332 total Jira tests)**

## What Happened

**T01** built `sync_engine.py` (~380 lines) implementing the full Jira→SemPKM pull pipeline. The engine follows the proven two-phase bulk create pattern from Linear/GCal sync apps, extended to three phases for Jira's Epic→child hierarchy:

- **Phase 1:** Create `object.create` commands for all tasks and milestones (platform mints IRIs)
- **Phase 2:** Re-query SPARQL to discover minted IRIs, submit `body.set` (ADF→Markdown converted descriptions) and `edge.create` (assignedTo) commands
- **Phase 3:** Link child tasks to parent Epics via `edge.create` with `bpkm:milestone` predicate, detecting parent via both next-gen `parent.key` and classic `customfield_10014` (Epic Link)

JQL construction handles multiple project keys (`project in (KEY1, KEY2)`), optional user-provided JQL filter (AND-appended), and delta sync via `updated >= "YYYY/MM/DD HH:mm"` from last sync timestamp. ISO→JQL date format conversion strips timezone and reformats for Jira's expected format.

Loop prevention skips issues where `updatedAt <= lastSyncedAt`. Per-issue error isolation via try/except ensures one bad issue doesn't kill the sync run. The result dict reports `status` (success/partial/error), counts, error details, and `failed_issues` list.

`push_sync(ctx)` is a stub returning `{status: "skipped", reason: "Push sync not yet implemented (S03)"}` — checks auth and sync_direction before returning.

App.py's three handlers (`sync_now`, `poll-tasks`, `push-changes`) were wired to real sync functions with lazy imports and try/except error handling. `sync_now` calls pull_sync and conditionally push_sync for bidirectional mode.

**T02** built 95 unit tests (2328 lines) across 13 test classes with full mock infrastructure — MockStateClient, MockSettingsClient, MockGraphClient, MockCommandClient, MockHttpClient, MockExternalHttpClient, MockAppContext. Tests cover SPARQL helpers, JQL construction (11 variants), command builders, pull sync happy path, Epic→Milestone creation and linking, delta sync with loop prevention, skip conditions (not connected, no projects, empty results), error isolation, push sync stub, app.py wiring, parent epic key extraction, batch submission, and edge cases.

## Verification

All 6 slice-level verification checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `pytest tests/test_jira_sync_engine.py -v` — 95 tests | ✅ 95 passed (0.12s) |
| 2 | `pytest tests/test_jira_*.py -v` — combined suite | ✅ 332 passed (0.38s) |
| 3 | `ast.parse(sync_engine.py)` — valid Python | ✅ VALID |
| 4 | `ast.parse(app.py)` — valid Python | ✅ VALID |
| 5 | `grep pull_sync\|push_sync app.py` — 7 occurrences | ✅ 7 (3 imports + 4 calls) |
| 6 | Failure-path signals in sync_engine.py | ✅ 10 matches (error/partial status, failed_issues, WARNING) |

## Requirements Advanced

- JIRA-03 (Pull sync: Jira issues → bpkm:Task) — pull_sync creates Task objects with correct field mapping via S01's build_task_properties, ADF→Markdown body conversion, assignee resolution via PersonMatcher. Proven by 95 unit tests with mocked clients.
- JIRA-04 (Epic → bpkm:Milestone mapping) — Epics detected via issuetype.name, converted to Milestone objects via build_milestone_properties, child tasks linked via Phase 3 edge creation. Proven by 8 dedicated unit tests.
- JIRA-05 (JQL-based filtered sync) — _build_jql() constructs JQL from project keys + user filter + delta timestamp. Proven by 11 JQL construction tests.
- JIRA-06 (Sprint as taskGroup, components/labels as tags) — Handled by S01's build_task_properties consuming fields.sprint.name, fields.labels, fields.components. Pull sync passes these through.
- JIRA-07 (Settings UI with project selection, JQL filter, sync direction, poll interval, Sync Now) — Settings UI built in S01 with project checkboxes, JQL input, direction radios, interval dropdown, Sync Now button. S02 wires Sync Now to real pull_sync.

## Requirements Validated

- none — full validation deferred to S04 E2E tests

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T02 produced 95 tests vs plan's 60+ target — additional coverage for _get_parent_epic_key (6 tests), _compute_status (5 tests), _submit_commands_batched (3 tests), MockResponse K002 compliance (6 tests), and edge cases (7 tests)
- pytest-asyncio required manual installation via `uv pip install pytest-asyncio` — was in pyproject.toml dev deps but not installed in worktree venv

## Known Limitations

- `push_sync` is a stub — real push implementation deferred to S03
- Issue link "blocks" → bpkm:dependsOn edges not yet implemented — deferred to S03
- pull_sync's empty-issues early return path does not store last_sync_at or last_pull_result in state (by design — no issues to sync means no sync timestamp update needed)
- No live Jira API testing — all verification is via mocked clients; E2E with mock Jira server deferred to S04

## Follow-ups

- S03 must implement real push_sync with SPARQL change detection, reverse field mapping, and issue update
- S03 must add issue link "blocks" → bpkm:dependsOn edge creation during pull sync
- S04 must build mock Jira REST API server and E2E test exercising full lifecycle

## Files Created/Modified

- `apps/jira-sync/services/sync_engine.py` — new, ~380 lines: pull_sync, push_sync stub, SPARQL helpers, command builders, JQL builder, batch submission
- `apps/jira-sync/app.py` — modified 3 handlers (sync_now, poll-tasks, push-changes) with lazy imports and real sync calls
- `backend/tests/test_jira_sync_engine.py` — new, 2328 lines, 95 unit tests for Jira sync engine

## Forward Intelligence

### What the next slice should know
- sync_engine.py uses `ctx.settings` for configuration (sync_direction, jql_filter, selected_projects) and `ctx.state` for runtime state (last_sync_at, last_pull_result, last_push_result) — S03's push_sync must follow this same split
- The three-phase bulk create pattern means Phase 3 (epic→child linking) runs after both milestones and tasks have been created and their IRIs discovered — push_sync doesn't need phases since it patches existing objects
- `_find_existing_task(graph, slug)` and `_find_existing_milestone(graph, slug)` use STRENDS on `bpkm:slug` with `externalProvider = "jira"` — push_sync should use similar SPARQL to find tasks that have changed
- Result dict must use `status: "success"` (not `"ok"`) to match connect_status.html template

### What's fragile
- The lazy import pattern in app.py (`from services.sync_engine import pull_sync`) runs at handler call time — if sync_engine.py has import-time errors, they surface as 500s on first sync attempt rather than at app startup
- MockGraphClient's dual slug_map pattern (slug_map for tasks, milestone_slug_map for milestones) requires tests to pre-populate the right map for the scenario being tested

### Authoritative diagnostics
- `pytest tests/test_jira_sync_engine.py -v` — 95 tests covering all sync paths, most trustworthy signal for sync engine correctness
- `ctx.state.get("last_pull_result")` — JSON with status/created/updated/skipped/errors/failed_issues/duration_ms, rendered in connect_status.html

### What assumptions changed
- Plan assumed settings UI needed work in S02 — it was already fully built in S01 (project selection, JQL filter, sync direction, poll interval, Sync Now button). S02 only needed to wire handlers to real sync logic.
- Plan estimated 60+ tests — actual coverage is 95 tests (58% more than planned) due to additional edge case and helper function coverage
