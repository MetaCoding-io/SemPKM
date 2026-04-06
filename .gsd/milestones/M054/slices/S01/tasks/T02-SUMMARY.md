---
id: T02
parent: S01
milestone: M054
key_files:
  - backend/app/templates/browser/explorer_config_tree.html
  - backend/app/templates/browser/explorer_config_children.html
  - backend/app/browser/workspace.py
  - backend/tests/test_explorer_config.py
key_decisions:
  - Config-children filters in Python after full query rather than separate group-scoped SPARQL — avoids duplicating query composition logic
  - Config params forwarded to children endpoint via assembled URL query string in template variable
duration: 
verification_result: passed
completed_at: 2026-04-06T04:26:04.008Z
blocker_discovered: false
---

# T02: Added config-tree and config-children endpoints that render grouped/sorted explorer HTML from ExplorerConfig query composition

**Added config-tree and config-children endpoints that render grouped/sorted explorer HTML from ExplorerConfig query composition**

## What Happened

Created two HTML templates (explorer_config_tree.html for grouped folders or flat objects, explorer_config_children.html for sorted leaf nodes within a group) and two workspace endpoints (GET /explorer/config-tree and GET /explorer/config-children). The config-tree endpoint builds ExplorerConfig from query params, runs group-folders or explorer query, and renders the tree. The config-children endpoint runs the full explorer query and filters to the requested group_value. Both templates follow existing tree_children.html/mount_tree.html patterns. Added 6 endpoint tests using mock FastAPI app with mocked triplestore client.

## Verification

All 26 tests pass (20 from T01 + 6 new endpoint tests): cd backend && ./.venv/bin/python -m pytest tests/test_explorer_config.py -v → 26 passed in 0.76s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && ./.venv/bin/python -m pytest tests/test_explorer_config.py -v` | 0 | ✅ pass | 760ms |

## Deviations

Config-children endpoint filters in Python after running the full explorer query rather than composing a separate group-scoped SPARQL query — simpler and reuses existing query builder. Verification command uses ./.venv/bin/python instead of .venv/bin/python due to PATH resolution.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/explorer_config_tree.html`
- `backend/app/templates/browser/explorer_config_children.html`
- `backend/app/browser/workspace.py`
- `backend/tests/test_explorer_config.py`
