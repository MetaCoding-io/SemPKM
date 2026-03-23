---
id: T01
parent: S01
milestone: M039
provides:
  - OpenAPI tags on all 10 previously-untagged APIRouter instances
key_files:
  - backend/app/commands/router.py
  - backend/app/sparql/router.py
  - backend/app/validation/router.py
  - backend/app/health/router.py
  - backend/app/admin/router.py
  - backend/app/inference/router.py
  - backend/app/lint/router.py
  - backend/app/apps/admin_router.py
  - backend/app/apps/router.py
  - backend/app/shell/router.py
key_decisions: []
patterns_established: []
observability_surfaces:
  - "GET /openapi.json — all routes now carry explicit tags; 'default' group should be empty"
duration: 3min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Add tags to all 10 untagged routers

**Added `tags=` parameter to all 10 APIRouter() constructors so every route appears under a descriptive group in OpenAPI/Redoc instead of "default"**

## What Happened

Each of the 10 router files had an `APIRouter()` call without a `tags=` parameter. Added the appropriate tag to each:

- `commands/router.py` → `tags=["commands"]`
- `sparql/router.py` → `tags=["sparql"]`
- `validation/router.py` → `tags=["validation"]`
- `health/router.py` → `tags=["health"]`
- `admin/router.py` → `tags=["admin"]`
- `inference/router.py` → `tags=["inference"]`
- `lint/router.py` → `tags=["lint"]`
- `apps/admin_router.py` → `tags=["app-management"]`
- `apps/router.py` → `tags=["app-proxy"]`
- `shell/router.py` → `tags=["shell"]`

After editing, confirmed zero `APIRouter()` calls remain without `tags=` anywhere in `backend/app/`.

## Verification

- `rg 'tags=' ... | wc -l` → 10 (all routers tagged)
- `python3 -c "import ast; ..."` → all 10 files parse without SyntaxError
- Slice check 1: `rg 'APIRouter(' ... | grep -c 'tags='` → 10
- Completeness: `rg 'APIRouter(' backend/app/ -g '*.py' | grep -v 'tags='` → empty (zero untagged routers)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'tags=' <10 files> \| wc -l` | 0 | ✅ pass (returned 10) | <1s |
| 2 | `python3 -c "import ast; ..."` (parse all 10) | 0 | ✅ pass | <1s |
| 3 | `rg 'APIRouter(' <10 files> \| grep -c 'tags='` | 0 | ✅ pass (returned 10) | <1s |
| 4 | `rg 'APIRouter(' backend/app/ -g '*.py' \| grep -v 'tags='` | 1 | ✅ pass (no untagged routers) | <1s |

## Diagnostics

After deployment, open `/redoc` or fetch `/openapi.json` to confirm routes are grouped by their tags. If any route appears under "default", check the corresponding router's `APIRouter()` for a missing `tags=` parameter.

## Deviations

None.

## Known Issues

- Slice verification check 2 (live `curl /openapi.json` "no default tag" assertion) requires a running server and will be validated in the final slice verification or manually.

## Files Created/Modified

- `backend/app/commands/router.py` — added `tags=["commands"]`
- `backend/app/sparql/router.py` — added `tags=["sparql"]`
- `backend/app/validation/router.py` — added `tags=["validation"]`
- `backend/app/health/router.py` — added `tags=["health"]`
- `backend/app/admin/router.py` — added `tags=["admin"]`
- `backend/app/inference/router.py` — added `tags=["inference"]`
- `backend/app/lint/router.py` — added `tags=["lint"]`
- `backend/app/apps/admin_router.py` — added `tags=["app-management"]`
- `backend/app/apps/router.py` — added `tags=["app-proxy"]`
- `backend/app/shell/router.py` — added `tags=["shell"]`
