---
id: T02
parent: S04
milestone: M010
provides:
  - commands_list() API enriches navigate commands with appId/pageId when path matches an app page
  - JS _loadAppCommandEntries() dispatches navigate commands with appId to openAppPageTab() (dockview tab)
key_files:
  - backend/app/browser/apps.py
  - frontend/static/js/workspace.js
  - backend/tests/test_app_views_commands.py
key_decisions:
  - Page matching uses exact equality (page.path == cmd.path) — no prefix/glob matching
patterns_established:
  - Navigate command enrichment: iterate manifest.ui.pages, match path, add appId+pageId to JSON
observability_surfaces:
  - /api/apps/commands JSON response includes appId and pageId fields for matching navigate commands (inspectable via DevTools or curl)
  - Browser console errors if openAppPageTab() fails at runtime
duration: 10m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Fix navigate action to open app pages as dockview tabs

**Enhanced commands_list() to include appId/pageId for navigate commands matching app pages, and updated JS handler to open dockview tabs instead of navigating away from the SPA.**

## What Happened

Two changes, backend and frontend:

1. **Backend (`commands_list()` in `apps.py`):** In the navigate branch, after setting `actionUrl = cmd.path`, added a loop over `manifest.ui.pages`. When `page.path == cmd.path`, the JSON entry gets `appId` (the app's ID) and `pageId` (the page's ID). Non-matching paths are unchanged (backwards compatible).

2. **Frontend (`_loadAppCommandEntries()` in `workspace.js`):** The navigate branch now checks `cmd.appId`. If truthy, calls `openAppPageTab(cmd.appId, cmd.pageId, cmd.title)` to open a dockview tab. Otherwise falls back to `window.location.href = cmd.actionUrl`.

3. **Tests:** Added 2 new tests to `test_app_views_commands.py`:
   - `test_navigate_command_with_matching_page_includes_app_and_page_ids` — verifies appId/pageId are present when path matches
   - `test_navigate_command_no_matching_page_excludes_ids` — verifies no appId/pageId when path doesn't match any page

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` — **15/15 passed** (13 existing + 2 new, zero regressions)
- `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` — syntax OK
- `rg "openAppPageTab" frontend/static/js/workspace.js` — 3 occurrences: definition (737), window export (755), new navigate dispatch (1819)

### Slice-level verification (partial — T02 is intermediate):
- ✅ `test_app_views_commands.py` — 15 passed
- ✅ `apps/rss-reader/app.py` syntax OK
- ✅ `apps/rss-reader/manifest.yaml` valid YAML
- ✅ Navigate command JSON includes `appId` and `pageId` when path matches an app page
- ⏳ `test_rss_reader_ui.py` — T03 will add S04-specific tests

## Diagnostics

- **Inspect navigate enrichment:** `curl localhost:8000/api/apps/commands | jq '.[] | select(.appId)'` shows commands with appId/pageId
- **Verify JS dispatch:** In browser DevTools, the `_loadAppCommandEntries` fetch handler logs at the `openAppPageTab` call; dockview panel creation is observable as a new tab appearing without URL change
- **Failure mode:** If page matching is wrong (e.g. path typo in manifest), the command falls through to `window.location.href` — observable as a full-page navigation instead of a dockview tab

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/apps.py` — Enhanced `commands_list()` navigate branch to add `appId`/`pageId` when path matches an app page
- `frontend/static/js/workspace.js` — Updated `_loadAppCommandEntries()` navigate handler to call `openAppPageTab()` when `appId` is present
- `backend/tests/test_app_views_commands.py` — Added `AppPage` import + 2 new tests for navigate command enrichment
- `.gsd/milestones/M010/slices/S04/tasks/T02-PLAN.md` — Added Observability Impact section
