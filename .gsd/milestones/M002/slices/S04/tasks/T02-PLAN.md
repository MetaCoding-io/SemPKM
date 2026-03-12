---
estimated_steps: 4
estimated_files: 2
---

# T02: Extract objects sub-router (CRUD, relations, edges, lint)

**Slice:** S04 — Browser Router Refactor
**Milestone:** M002

## Description

Extract the largest domain — object CRUD, relations, edges, and lint (13 routes, ~800 lines) — into `objects.py`. This is the highest-risk extraction because it contains the most code, complex template rendering with `request.app.state.templates`, and a latent `Operation` import bug that must be fixed during extraction.

## Steps

1. Read the current state of `router.py` (post-T01) to identify exact line ranges for the 13 object routes: `/object/{object_iri:path}` GET, `/tooltip/{object_iri:path}` GET, `/objects/{object_iri:path}/body` POST, `/relations/{object_iri:path}` GET, `/edge-provenance` GET, `/edge/delete` POST, `/objects/delete` POST, `/lint/{object_iri:path}` GET, `/types` GET, `/objects/new` GET, `/objects` POST, `/objects/{object_iri:path}/save` POST.
2. Create `backend/app/browser/objects.py` with `objects_router = APIRouter(tags=["objects"])` (NO prefix). Move all 13 route handlers and their helper code. Import shared utilities from `._helpers`. Keep all inline imports (`from app.commands.handlers.*`, `from app.config`, etc.) inside handler bodies. Add the missing `from app.events.store import Operation` to the top-level imports — this fixes the latent NameError bug in `delete_edge` and `bulk_delete_objects`.
3. Update `backend/app/browser/router.py`: remove the 13 extracted handlers. Add `from .objects import objects_router` and `router.include_router(objects_router)`. Ensure the include order matches original route registration order (objects routes come after workspace `"/"` and nav-tree routes in the original file, but the key constraint is that `/objects/new` and `/objects` POST must come after `/object/{object_iri:path}` — preserved by keeping them in the same sub-router in original order).
4. Verify: run `cd backend && .venv/bin/pytest tests/ -v` and confirm `python -c "from app.browser.objects import objects_router; print(len(objects_router.routes))"` shows 13 routes.

## Must-Haves

- [ ] `objects.py` has exactly 13 route handlers with NO prefix on the sub-router
- [ ] `from app.events.store import Operation` is a top-level import in `objects.py` (bug fix)
- [ ] Route order within `objects.py` matches original file order
- [ ] All inline imports preserved inside handler bodies
- [ ] All existing unit tests pass

## Verification

- `cd backend && .venv/bin/pytest tests/ -v` — all unit tests pass
- `cd backend && python -c "from app.browser.objects import objects_router; print(len(objects_router.routes))"` — prints 13 (or the correct count accounting for any auto-generated routes)
- `cd backend && python -c "from app.browser.router import router; print('OK')"` — coordinator imports cleanly

## Observability Impact

- Signals added/changed: Fixes latent `Operation` NameError — `delete_edge` and `bulk_delete_objects` will now work at runtime instead of crashing with NameError
- How a future agent inspects this: `objects_router.routes` shows all object routes; import `Operation` is verifiable at module load
- Failure state exposed: NameError on Operation is eliminated; any remaining import errors surface at startup

## Inputs

- `backend/app/browser/router.py` — post-T01 state (settings extracted, helpers extracted)
- `backend/app/browser/_helpers.py` — shared utilities (from T01)
- S04 research — route assignments and Operation bug location (lines 1232, 1325)

## Expected Output

- `backend/app/browser/objects.py` — ~800 lines with 13 object/CRUD route handlers and Operation import fix
- `backend/app/browser/router.py` — reduced by ~800 more lines, now includes settings + objects sub-routers
