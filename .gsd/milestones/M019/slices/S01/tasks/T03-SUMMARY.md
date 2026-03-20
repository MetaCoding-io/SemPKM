---
id: T03
parent: S01
milestone: M019
provides:
  - PersonMatcher for Todoist assignee resolution (email + name lookup, LRU cache)
  - Sync engine with pull_sync() — two-phase bulk create, existing task detection, per-task error isolation
  - Route handlers for project selection, sync-now, and poll-tasks
  - connect_status.html with project checkboxes, sync button, and stats display
key_files:
  - apps/todoist-sync/services/person_matcher.py
  - apps/todoist-sync/services/sync_engine.py
  - apps/todoist-sync/app.py
  - apps/todoist-sync/frontend/templates/connect_status.html
  - apps/todoist-sync/frontend/templates/projects.html
  - backend/tests/test_todoist_person_matcher.py
  - backend/tests/test_todoist_sync_engine.py
key_decisions:
  - "Existing task detection uses bpkm:externalId + externalProvider='todoist' SPARQL lookup instead of slug-based STRENDS — more precise for Todoist's string IDs"
  - "Phase 2 IRI discovery uses STRENDS slug lookup on newly created tasks — same pattern as github-sync"
  - "todoist_client.py import changed from relative (.auth) to try/except pattern — matches github-sync convention and enables importlib test loading"
patterns_established:
  - "pull_sync follows github-sync pattern: auth check → fetch from API → classify create/update → two-phase bulk submit → store result"
  - "State keys: selected_projects (JSON array of project IDs), last_pull_result (JSON with status/counts/error_details)"
observability_surfaces:
  - "todoist.sync logger at INFO — pull sync complete with created/updated/unchanged/errors counts"
  - "todoist.sync.person logger at DEBUG — cache hits, person creation"
  - "last_pull_result state key — JSON with status, counts, error_details array, duration_ms"
duration: 35min
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: PersonMatcher + sync engine + pull routes

**Built pull sync engine with PersonMatcher, project selection routes, and sync-now handler — 168 tests pass across all S01 modules.**

## What Happened

Adapted github-sync's person_matcher.py for Todoist — uses name/email instead of login/email for assignee resolution, same SPARQL lookup pattern (foaf:mbox → crm:email → externalId → create new).

Built sync_engine.py with pull_sync() orchestrating: auth check → selected projects from state → fetch tasks per project → classify create/update via externalId SPARQL lookup → two-phase bulk command submission (Phase 1: object.create with X-Request-Id for idempotency, Phase 2: discover IRIs via STRENDS slug lookup, then body.set + edge.create for assignees). Per-task error isolation via try/except around each task's processing loop.

Wired four new route handlers in app.py: GET/POST /_fragments/projects (fetch + render project checkboxes, save selection to state), POST /_fragments/sync-now (trigger pull_sync, return updated status), and poll-tasks task handler (delegates to pull_sync). Updated connect_status.html with project selection section (htmx-loaded), Sync Now button with spinner, and sync stats display (created/updated/unchanged/errors). Created projects.html template for the checkbox form.

Fixed todoist_client.py import from relative (`.auth`) to try/except pattern matching github-sync convention — the relative import broke importlib-based test loading. Also fixed test_todoist_client.py module loading to match.

## Verification

- `cd backend && pytest tests/test_todoist_person_matcher.py tests/test_todoist_sync_engine.py -v` — 56 passed (18 person matcher + 38 sync engine)
- `cd backend && pytest tests/test_todoist_*.py -v` — 168 passed (all S01 tests)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_todoist_person_matcher.py tests/test_todoist_sync_engine.py -v` | 0 | ✅ pass | 0.08s |
| 2 | `pytest tests/test_todoist_*.py -v` | 0 | ✅ pass | 0.20s |

## Diagnostics

- **Sync health:** `ctx.state.get("last_pull_result")` returns JSON with `{status, created, updated, unchanged, errors, error_details, duration_ms, timestamp}`
- **Status values:** `"success"` (no errors), `"partial"` (some tasks synced, some failed), `"error"` (all failed), `"skipped"` (not connected or no projects selected — includes `reason`)
- **Error details:** `error_details` array with `{task_id, error}` or `{project_id, error}` per failure
- **Person matcher:** `todoist.sync.person` logger at DEBUG for cache hits and creation
- **Logger:** `todoist.sync` at INFO for sync completion summary

## Deviations

- Changed todoist_client.py from relative import (`.auth`) to try/except import pattern — necessary for importlib test loading, aligns with github-sync convention
- Fixed test_todoist_client.py module loading after import change — updated `_load_client()` and exception class references

## Known Issues

None.

## Files Created/Modified

- `apps/todoist-sync/services/person_matcher.py` — new: email/name SPARQL person resolution with LRU cache
- `apps/todoist-sync/services/sync_engine.py` — new: pull_sync engine with two-phase bulk create, error isolation
- `apps/todoist-sync/app.py` — updated: project selection routes, sync-now, poll-tasks wired to sync engine
- `apps/todoist-sync/services/todoist_client.py` — fixed: relative import → try/except pattern
- `apps/todoist-sync/frontend/templates/connect_status.html` — updated: project selection, sync button, stats
- `apps/todoist-sync/frontend/templates/projects.html` — new: project checkbox form
- `backend/tests/test_todoist_person_matcher.py` — new: 18 tests for person matching
- `backend/tests/test_todoist_sync_engine.py` — new: 38 tests for sync engine
- `backend/tests/test_todoist_client.py` — fixed: module loading for import change
