---
id: T03
parent: S04
milestone: M002
provides:
  - events_router sub-router with 3 event handlers (event log, detail, undo)
  - search_router sub-router with 1 search handler (reference search)
  - workspace_router sub-router with 5 workspace/nav handlers (layout, nav-tree, tree children, icons, my-views)
  - pages_router sub-router with 4 page handlers (docs, guide viewer, lint dashboard, canvas)
  - Thin coordinator router.py (~26 lines) assembling all 6 sub-routers
key_files:
  - backend/app/browser/events.py
  - backend/app/browser/search.py
  - backend/app/browser/workspace.py
  - backend/app/browser/pages.py
  - backend/app/browser/router.py
key_decisions:
  - "Include order: settings → objects → pages → workspace → events → search (matches original route registration order)"
  - "workspace_router groups all 5 workspace routes including /my-views which was originally separated from the other workspace routes by events and search — no routing ambiguity since paths are distinct"
patterns_established:
  - "Final coordinator pattern: ~26 lines, only imports and include_router() calls, no handler code"
observability_surfaces:
  - "Each sub-router independently importable for inspection: `from app.browser.<module> import <name>_router`"
  - "router.routes shows full assembled route table (33 routes)"
duration: 12m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Extract events, search, workspace, and pages sub-routers

**Extracted 4 remaining domain sub-routers (13 routes) and reduced router.py to a 26-line coordinator assembling all 6 sub-routers.**

## What Happened

Created the final 4 sub-router modules completing the browser router split:

1. **events.py** (3 routes): `/events` (event log timeline), `/events/{event_iri}/detail` (inline diff), `/events/{event_iri}/undo` (compensating event). Preserved all inline imports for EventQueryService, UserModel, uuid, etc.

2. **search.py** (1 route): `/search` (reference search for sh:class fields). Imports `_validate_iri` from `_helpers.py`.

3. **workspace.py** (5 routes): `/` (workspace layout), `/nav-tree` (nav tree partial), `/tree/{type_iri}` (tree children), `/icons` (icon map JSON), `/my-views` (promoted views). Imports `_is_htmx_request`, `_validate_iri`, and `get_icon_service` from `_helpers.py`.

4. **pages.py** (4 routes): `/docs` (docs hub), `/docs/guide/{filename}` (guide viewer), `/lint-dashboard` (lint dashboard), `/canvas` (spatial canvas).

Rewrote `router.py` to a 26-line thin coordinator that creates the `APIRouter(prefix="/browser")` and includes all 6 sub-routers in the original registration order.

## Verification

- `cd backend && .venv/bin/pytest tests/ -v` — **103 tests passed** (all unit tests including test_iri_validation.py)
- `python -c "from app.browser.router import router; print(len(router.routes))"` — **33 routes** (matches original)
- `wc -l backend/app/browser/router.py` — **26 lines** (under 50 threshold)
- `ls backend/app/browser/*.py | wc -l` — **9 files** (8 domain files + `__init__.py`)
- All 4 new sub-routers independently importable: `from app.browser.{events,search,workspace,pages} import *_router` — OK
- Per-router route counts: events=3, search=1, workspace=5, pages=4 — all match expected

### Slice-Level Verification (partial — T03 is not final task)

| Check | Status |
|-------|--------|
| `pytest tests/ -v` — all unit tests pass | ✅ pass |
| `python -c "from app.browser.router import router; print(len(router.routes))"` — 33 routes | ✅ pass |
| `ls backend/app/browser/*.py \| wc -l` — 8 files | ⚠️ 9 (includes `__init__.py` — plan counted only domain files) |
| `cd e2e && npx playwright test` — all 52 E2E tests | ⏳ deferred to T04 |

## Diagnostics

- Import check: `python -c "from app.browser.events import events_router; print(events_router.routes)"`
- Route audit: `python -c "from app.browser.router import router; [print(f'{r.path} {r.methods}') for r in router.routes]"`
- Import errors surface at app startup time

## Deviations

- File count is 9 (not 8) because `__init__.py` exists as a standard Python package marker. The plan's "8 files" counted only the domain files (coordinator + helpers + 6 sub-routers). Not a real issue — `__init__.py` predates this slice.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/events.py` — new: 3 event route handlers
- `backend/app/browser/search.py` — new: 1 search route handler
- `backend/app/browser/workspace.py` — new: 5 workspace/nav route handlers
- `backend/app/browser/pages.py` — new: 4 page route handlers
- `backend/app/browser/router.py` — rewritten: thin 26-line coordinator with 6 include_router() calls
