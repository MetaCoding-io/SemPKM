---
id: T02
parent: S04
milestone: M010
provides:
  - Navigate commands matching app pages include appId/pageId in JSON API response
  - JS handler dispatches navigate commands with appId to openAppPageTab() for SPA tab opening
key_files:
  - backend/app/browser/apps.py
  - frontend/static/js/workspace.js
  - backend/tests/test_app_views_commands.py
key_decisions:
  - Page matching done by iterating manifest.ui.pages and comparing page.path == cmd.path; no fuzzy/prefix matching
patterns_established:
  - Platform-wide pattern: commands_list() enriches navigate entries with appId/pageId when path matches an app page; JS handler branches on cmd.appId presence
observability_surfaces:
  - Navigate command JSON in /api/apps/commands includes appId and pageId fields when path matches an app page (inspectable via DevTools Network or curl | jq)
  - Browser console shows errors if openAppPageTab() fails; non-app-page navigates still use window.location.href
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Fix navigate action to open app pages as dockview tabs

**Enhanced commands_list() to include appId/pageId for navigate commands matching app pages, and updated JS handler to open them as dockview tabs instead of full-page navigations**

## What Happened

Two surgical edits — one backend, one frontend — fix the "Open RSS Reader" command (and all future app navigate commands) to stay within the workspace SPA.

In `commands_list()` (apps.py), after building the navigate command entry, the code now iterates `manifest.ui.pages` to check if `cmd.path` matches any page's `.path`. On match, `appId` and `pageId` are added to the JSON entry. Non-matching paths (external URLs, admin routes) are unchanged — backwards compatible.

In `_loadAppCommandEntries()` (workspace.js), the navigate branch now checks `cmd.appId`. If present, it calls `openAppPageTab(cmd.appId, cmd.pageId, cmd.title)` which opens a dockview tab. If absent, it falls through to the original `window.location.href` behavior.

Two new tests were added to `test_app_views_commands.py`: one verifying appId/pageId appear when the path matches an app page, and one verifying they're omitted when the path doesn't match. The `AppPage` import was added to the test file.

## Verification

- All 17 tests in `test_app_views_commands.py` pass (15 existing + 2 new)
- All 37 tests in `test_rss_reader_ui.py` pass (no regressions)
- Python syntax check on `apps.py` passes
- JS grep confirms `openAppPageTab` is wired in the navigate branch of `_loadAppCommandEntries`
- YAML and Python syntax checks for RSS Reader app files pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` | 0 | ✅ pass | 0.39s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` | 0 | ✅ pass | 0.30s |
| 3 | `python3 -c "import ast; ast.parse(open('backend/app/browser/apps.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `python3 -c "import yaml; yaml.safe_load(open('apps/rss-reader/manifest.yaml'))"` | 0 | ✅ pass | <1s |
| 6 | `grep "openAppPageTab" frontend/static/js/workspace.js` (in navigate branch) | 0 | ✅ pass | <1s |

## Diagnostics

- **API inspection:** `curl /api/apps/commands | jq '.[] | select(.actionType=="navigate")'` shows `appId` and `pageId` fields for app page navigates
- **Behavioral:** Navigate commands with `appId` create dockview panels (no URL change); those without still navigate the browser
- **Failure mode:** If `openAppPageTab()` is undefined or throws, browser console surfaces the error immediately

## Deviations

- Test file `test_app_views_commands.py` didn't exist in the worktree — copied from main repo and added 2 new tests (+ `AppPage` import). T03 will add more tests to this file.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/apps.py` — Enhanced `commands_list()` to add `appId`/`pageId` for navigate commands matching app pages
- `frontend/static/js/workspace.js` — Updated navigate handler in `_loadAppCommandEntries()` to call `openAppPageTab()` when `cmd.appId` present
- `backend/tests/test_app_views_commands.py` — Copied from main repo, added `AppPage` import and 2 new tests for navigate command enrichment
