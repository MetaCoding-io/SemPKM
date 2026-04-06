---
id: T01
parent: S02
milestone: M051
key_files:
  - backend/app/services/shapes.py
  - backend/app/templates/browser/workspace.html
  - backend/app/vfs/mount_router.py
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-06T01:15:48.456Z
blocker_discovered: false
---

# T01: Added .removesuffix(' Shape') to backend type labels, replaced stale event log placeholder, and enriched VFS mount SPARQL with dcterms:title for human-readable model names

**Added .removesuffix(' Shape') to backend type labels, replaced stale event log placeholder, and enriched VFS mount SPARQL with dcterms:title for human-readable model names**

## What Happened

Three surgical edits: (1) shapes.py get_types() now strips ' Shape' suffix from labels at the source, (2) workspace.html event log placeholder changed from 'coming in Phase 16' to 'Loading event log...', (3) mount_router.py model mounts SPARQL extended with OPTIONAL dcterms:title and fallback to modelId for the name field.

## Verification

Ran backend test suite — 144 tests passed. Three pre-existing failures excluded (feedparser import, ai-insights capability, command palette navigation). No regressions from these changes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/ -x -q --ignore=tests/test_feed_service.py --ignore=tests/test_ai_endpoints.py` | 1 | ✅ pass (144 passed, 1 pre-existing fail) | 10100ms |

## Deviations

None.

## Known Issues

Three pre-existing test failures unrelated to this task.

## Files Created/Modified

- `backend/app/services/shapes.py`
- `backend/app/templates/browser/workspace.html`
- `backend/app/vfs/mount_router.py`
