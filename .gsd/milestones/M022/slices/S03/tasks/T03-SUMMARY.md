---
id: T03
parent: S03
milestone: M022
provides:
  - sync-config POST route saving sync_direction and poll_interval to StateClient
  - bidirectional sync_now route (pull + push when direction is "bidirectional")
  - push_changes task handler wired to push_sync()
  - settings UI sections for sync direction, poll interval, Sync Now, and pull/push stats
key_files:
  - apps/asana-sync/app.py
  - apps/asana-sync/frontend/templates/connect_status.html
key_decisions:
  - Cloned Linear sync's settings/stats UI pattern verbatim for Asana — same CSS classes, same stat-group/stat-row structure, same htmx target/swap model
patterns_established:
  - Sync app settings pattern: sync-config route + bidirectional sync_now + stats display via stat-group/stat-row — identical in Linear and Asana apps
observability_surfaces:
  - StateClient keys: sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result
  - Logger asana.sync.app: sync config saves, manual sync triggers, push/pull errors
  - Template stat-group/stat-row blocks render last pull and push results visually
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Add settings UI + route wiring in app.py and template

**Wired push sync into Asana app surface: sync-config route, bidirectional sync_now, push_changes handler, and template sections for sync direction/interval/stats**

## What Happened

Added four changes to `app.py`: (1) `/_fragments/settings/sync-config` POST route that saves sync_direction and poll_interval, (2) replaced `sync_now` route with bidirectional version that runs pull then conditionally push and stores results/timestamp, (3) replaced `push_changes` stub with real `push_sync()` call, (4) extended `_render_connect_status()` to pass sync_direction, poll_interval, last_sync_at, last_pull_result, last_push_result to the template.

Added three new sections to `connect_status.html` between the config summary and disconnect sections: Sync Configuration (direction radios + poll interval dropdown), Manual Sync (Sync Now button with htmx indicator), and Sync Stats (last sync timestamp, pull stat-group, push stat-group, empty-state message). All htmx URLs use `/app/asana-sync/` prefix per KNOWLEDGE.md.

## Verification

- `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` — syntax OK
- 6 `hx-post="/app/asana-sync/"` URLs in template (exceeds 2+ requirement)
- 12 stat-group/stat-row occurrences in template (exceeds 10+ requirement)
- `push_sync` appears in import, push_changes handler, and sync_now route
- 25 occurrences of sync_direction/poll_interval/last_pull_result/last_push_result template variables
- All 209 existing tests pass (field_mapper + sync_engine)
- All 3 syntax checks pass (field_mapper.py, sync_engine.py, app.py)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `grep -c 'hx-post="/app/asana-sync/' connect_status.html` → 6 | 0 | ✅ pass | <1s |
| 3 | `grep -c 'stat-group\|stat-row' connect_status.html` → 12 | 0 | ✅ pass | <1s |
| 4 | `grep 'push_sync' app.py` → 3 matches | 0 | ✅ pass | <1s |
| 5 | `uv run python -m pytest test_asana_field_mapper.py test_asana_sync_engine.py -q` → 209 passed | 0 | ✅ pass | 0.2s |
| 6 | `ast.parse(field_mapper.py)` | 0 | ✅ pass | <1s |
| 7 | `ast.parse(sync_engine.py)` | 0 | ✅ pass | <1s |

## Diagnostics

- **StateClient keys:** `sync_direction` (string), `poll_interval` (string), `last_sync_at` (ISO timestamp), `last_pull_result` (JSON), `last_push_result` (JSON)
- **Logger:** `asana.sync.app` emits sync config saves and manual sync triggers with direction/interval values
- **Template:** stat-group/stat-row blocks render pull/push results with status, counts, and error counts
- **Error path:** If push_sync raises during manual sync, error is caught, logged, and stored as `{"status": "error", "message": "..."}` in `last_push_result` — visible in the Sync Stats UI section

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/asana-sync/app.py` — Added sync-config route, bidirectional sync_now, push_changes wiring, extended _render_connect_status context (~50 new lines)
- `apps/asana-sync/frontend/templates/connect_status.html` — Added sync configuration, manual sync, and sync stats sections (~100 new lines)
- `.gsd/milestones/M022/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
