# S02: Push Sync + Settings UI — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

Straightforward slice — all three components (push sync, settings controls, settings UI) follow the github-sync pattern exactly. S01 already delivered the TodoistClient with `close_task()`, `reopen_task()`, `create_task()`, `update_task()` methods (all tested), the reverse field mapper `build_todoist_task_data()`, and a placeholder `push_changes` task handler in `app.py`. The only novel piece is the close/reopen branching for status changes — Todoist uses separate `POST /tasks/{id}/close` and `POST /tasks/{id}/reopen` endpoints instead of PATCH for completion state, unlike GitHub/Linear which use a single mutation. The `_find_changed_tasks` SPARQL, sync-direction gating, loop prevention via `lastSyncedAt`, and settings form patterns are identical to github-sync.

## Recommendation

Clone the github-sync push_sync pattern with one adaptation: after detecting a status change, branch on direction — if the bpkm status maps to `is_completed=True`, call `close_task()`; if `False`, call `reopen_task()`. Non-status field changes (title, priority, labels, due date) go through `update_task()` with the reverse-mapped body from `build_todoist_task_data()`. Settings UI adds sync direction radios, poll interval dropdown, and push result stats to the existing `connect_status.html` template.

## Implementation Landscape

### Key Files

**Modify:**
- `apps/todoist-sync/services/sync_engine.py` — Add `push_sync()`, `_find_changed_tasks()`. Currently only has `pull_sync()`. The `_find_changed_tasks` SPARQL is identical to github-sync except `externalProvider = "todoist"`.
- `apps/todoist-sync/app.py` — Replace the `push_changes` placeholder with real `push_sync()` call. Add `sync-now` to also call push when bidirectional. Add `/_fragments/settings/sync-config` POST route. Update `_render_connect_status` to read/pass `sync_direction`, `poll_interval`, `last_push_result`.
- `apps/todoist-sync/frontend/templates/connect_status.html` — Add sync config section (direction radios, poll interval dropdown), push result stats section. Pattern: copy from `apps/github-sync/frontend/templates/connect_status.html`.

**Reference (read-only):**
- `apps/github-sync/services/sync_engine.py` — `push_sync()` (~120 lines), `_find_changed_tasks()` (~40 lines). Direct template.
- `apps/github-sync/app.py` — `sync_config` route, `sync_now` bidirectional logic, `_render_connect_status` with all template vars.
- `apps/github-sync/frontend/templates/connect_status.html` — Settings section HTML (direction radios, poll interval, push stats).

**Create:**
- `backend/tests/test_todoist_push_sync.py` — Push sync unit tests (~50+ tests). Covers: `_find_changed_tasks` SPARQL, push_sync pipeline (close/reopen branching, field update, lastSyncedAt update), loop prevention in pull_sync, settings route, template context, push_changes task handler.

### Build Order

1. **push_sync() + close/reopen branching** — This is the only novel piece. Add `_find_changed_tasks()` (SPARQL for todoist tasks with `modified > lastSyncedAt`), then `push_sync()` orchestrating: auth check → direction check → find changed → for each: detect status change direction → close/reopen or update → lastSyncedAt update → store result. Unit test the status branching thoroughly.

2. **Settings route + app.py updates** — Wire `/_fragments/settings/sync-config` POST route, update `_render_connect_status` to pass `sync_direction`, `poll_interval`, `last_push_result`. Update `sync_now` to call push after pull when bidirectional. Replace `push_changes` placeholder with real implementation. Unit test route and template context.

3. **Settings UI template** — Add sync config form and push stats to `connect_status.html`. Copy structure from github-sync template. All htmx URLs must use `/app/todoist-sync/` prefix (knowledge base rule).

### Verification Approach

- `pytest backend/tests/test_todoist_push_sync.py -v` — 50+ tests covering push pipeline, close/reopen branching, settings route, template context
- `pytest backend/tests/test_todoist_*.py -v` — All Todoist tests (168 existing + 50+ new ≈ 218+) pass together
- `rg "hx-" apps/todoist-sync/frontend/templates/ | grep -v "/app/todoist-sync/"` — must return empty (htmx URL prefix check)

## Constraints

- `close_task()` and `reopen_task()` are separate POST endpoints — cannot batch status changes with field updates in a single Todoist API call. Push must sequence: first close/reopen if status changed, then update_task for other field changes.
- `ctx.settings` (not `ctx.state`) is used for sync_direction and poll_interval — follows the github-sync pattern. Settings are user-configurable; state is internal sync bookkeeping.

## Common Pitfalls

- **Close/reopen vs update ordering** — If both status and fields changed, close/reopen must happen first. If update_task sends `priority: 3` to a just-closed task, it might silently fail or reopen it. Sequence: status change → field update.
- **Loop prevention** — pull_sync must skip tasks whose `lastSyncedAt` is recent (set by push_sync). The github-sync pattern uses `STR(?modified) > STR(?lastSynced)` FILTER in `_find_changed_tasks`. Same pattern applies.
- **MockResponse `data or {}` trap** — Per KNOWLEDGE.md pattern #2, use `data if data is not None else {}` in test mocks to avoid empty list → empty dict coercion.
