---
id: T03
parent: S03
milestone: M049
key_files:
  - backend/app/templates/browser/partials/inbox_panel.html
  - backend/app/templates/browser/partials/collaboration_panel.html
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-05T21:00:15.116Z
blocker_discovered: false
---

# T03: Changed inbox and collaboration panel htmx triggers from load to revealed so HTTP requests fire only when panels enter the viewport

**Changed inbox and collaboration panel htmx triggers from load to revealed so HTTP requests fire only when panels enter the viewport**

## What Happened

Straightforward two-line edit. Changed hx-trigger="load, every 60s" to hx-trigger="revealed, every 60s" in the inbox panel partial, and hx-trigger="load" to hx-trigger="revealed" in the collaboration panel partial. The htmx revealed trigger uses IntersectionObserver internally — the panel's GET request fires when the element first scrolls into view or is expanded, not on initial page load. The every 60s polling on inbox continues independently after the first reveal to keep notifications fresh.

## Verification

Verified both files show revealed trigger via grep. Confirmed no load triggers remain. Ran all 50 slice tests: 7 server-timing, 32 S01+S02 regression, 11 admin performance — all pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep 'revealed' inbox_panel.html && grep 'revealed' collaboration_panel.html` | 0 | ✅ pass | 100ms |
| 2 | `! grep 'hx-trigger="load' inbox_panel.html && ! grep 'hx-trigger="load' collaboration_panel.html` | 0 | ✅ pass | 100ms |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_server_timing.py -v` | 0 | ✅ pass | 380ms |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_shapes_cache.py tests/test_object_query_opt.py tests/test_object_parallel.py tests/test_tracing.py -v` | 0 | ✅ pass | 1440ms |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_admin_performance.py -v` | 0 | ✅ pass | 790ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/browser/partials/inbox_panel.html`
- `backend/app/templates/browser/partials/collaboration_panel.html`
