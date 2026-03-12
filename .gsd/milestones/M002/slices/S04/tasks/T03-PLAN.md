---
estimated_steps: 5
estimated_files: 5
---

# T03: Extract events, search, workspace, and pages sub-routers

**Slice:** S04 — Browser Router Refactor
**Milestone:** M002

## Description

Extract the remaining 4 domains into their own sub-router modules, completing the split. After this task, `router.py` becomes a thin ~30-line coordinator that creates the main `APIRouter(prefix="/browser")`, imports all 6 sub-routers, and assembles them via `include_router()`. This is the task that transforms the monolith into the final target structure.

## Steps

1. Read the current state of `router.py` (post-T02) to identify exact line ranges for the remaining routes: events (3 routes: `/events`, `/events/{event_iri:path}/detail`, `/events/{event_iri:path}/undo`), search (1 route: `/search`), workspace (5 routes: `/`, `/nav-tree`, `/tree/{type_iri:path}`, `/icons`, `/my-views`), pages (4 routes: `/docs`, `/docs/guide/{filename:path}`, `/lint-dashboard`, `/canvas`).
2. Create `backend/app/browser/events.py` with `events_router = APIRouter(tags=["events"])` (NO prefix). Move 3 event handlers. Keep inline imports (`from app.events.query import EventQueryService`, `from app.auth.models import User as UserModel`).
3. Create `backend/app/browser/search.py` with `search_router = APIRouter(tags=["search"])` (NO prefix). Move the single `/search` handler. Keep inline import (`from app.sparql.models import PromotedQueryView`).
4. Create `backend/app/browser/workspace.py` with `workspace_router = APIRouter(tags=["workspace"])` (NO prefix). Move 5 workspace/navigation handlers (`/`, `/nav-tree`, `/tree/{type_iri:path}`, `/icons`, `/my-views`). Keep inline imports (`from app.config import settings`).
5. Create `backend/app/browser/pages.py` with `pages_router = APIRouter(tags=["pages"])` (NO prefix). Move 4 page handlers (`/docs`, `/docs/guide/{filename:path}`, `/lint-dashboard`, `/canvas`). Rewrite `router.py` to its final thin coordinator form: create `APIRouter(prefix="/browser", tags=["browser"])`, import all 6 sub-routers, call `router.include_router()` for each in the original route registration order: settings → pages → workspace → objects → events → search (matching the original file's route order). Verify final line count is ~30 lines of real code.

## Must-Haves

- [ ] `events.py` has exactly 3 route handlers
- [ ] `search.py` has exactly 1 route handler
- [ ] `workspace.py` has exactly 5 route handlers
- [ ] `pages.py` has exactly 4 route handlers
- [ ] `router.py` is a thin coordinator (~30 lines) with only imports and `include_router()` calls
- [ ] Sub-router `include_router()` order matches original route registration order
- [ ] All inline imports preserved inside handler bodies
- [ ] All existing unit tests pass
- [ ] `ls backend/app/browser/*.py | wc -l` returns 8

## Verification

- `cd backend && .venv/bin/pytest tests/ -v` — all unit tests pass
- `cd backend && python -c "from app.browser.router import router; print(len(router.routes))"` — route count matches original
- `wc -l backend/app/browser/router.py` — under 50 lines
- `ls backend/app/browser/*.py | wc -l` — exactly 8 files
- `cd backend && python -c "from app.browser.events import events_router; from app.browser.search import search_router; from app.browser.workspace import workspace_router; from app.browser.pages import pages_router; print('OK')"` — all sub-routers importable

## Observability Impact

- Signals added/changed: None — pure structural move
- How a future agent inspects this: Each sub-router module is independently importable; `router.routes` shows the full assembled route table
- Failure state exposed: Import errors at startup; missing routes produce 404s caught by E2E tests

## Inputs

- `backend/app/browser/router.py` — post-T02 state (settings + objects extracted)
- `backend/app/browser/_helpers.py` — shared utilities (from T01)
- S04 research — route assignments, registration order constraints

## Expected Output

- `backend/app/browser/events.py` — ~150 lines with 3 event route handlers
- `backend/app/browser/search.py` — ~80 lines with 1 search route handler
- `backend/app/browser/workspace.py` — ~180 lines with 5 workspace/nav route handlers
- `backend/app/browser/pages.py` — ~80 lines with 4 page route handlers
- `backend/app/browser/router.py` — ~30 lines, thin coordinator importing and assembling all 6 sub-routers
