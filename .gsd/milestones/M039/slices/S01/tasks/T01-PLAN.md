---
estimated_steps: 10
estimated_files: 10
skills_used: []
---

# T01: Add tags to all 10 untagged routers

**Slice:** S01 — Redoc API Tag Cleanup
**Milestone:** M039

## Description

Add `tags=["..."]` parameter to the `APIRouter()` constructor in each of the 10 router files that currently lack tags. This is purely OpenAPI metadata — zero behavior change to any route.

## Steps

1. Edit `backend/app/commands/router.py` — add `tags=["commands"]` to `APIRouter()`
2. Edit `backend/app/sparql/router.py` — add `tags=["sparql"]` to `APIRouter()`
3. Edit `backend/app/validation/router.py` — add `tags=["validation"]` to `APIRouter()`
4. Edit `backend/app/health/router.py` — add `tags=["health"]` to `APIRouter()`
5. Edit `backend/app/admin/router.py` — add `tags=["admin"]` to `APIRouter()`
6. Edit `backend/app/inference/router.py` — add `tags=["inference"]` to `APIRouter()`
7. Edit `backend/app/lint/router.py` — add `tags=["lint"]` to `APIRouter()`
8. Edit `backend/app/apps/admin_router.py` — add `tags=["app-management"]` to `APIRouter()`
9. Edit `backend/app/apps/router.py` — add `tags=["app-proxy"]` to `APIRouter()`
10. Edit `backend/app/shell/router.py` — add `tags=["shell"]` to `APIRouter()`

## Must-Haves

- [ ] All 10 routers have `tags=` parameter
- [ ] Existing parameters (prefix, etc.) are preserved
- [ ] No route paths, methods, or behavior changed

## Verification

- `rg 'tags=' backend/app/commands/router.py backend/app/sparql/router.py backend/app/validation/router.py backend/app/health/router.py backend/app/admin/router.py backend/app/inference/router.py backend/app/lint/router.py backend/app/apps/admin_router.py backend/app/apps/router.py backend/app/shell/router.py | wc -l` returns 10
- `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['backend/app/commands/router.py','backend/app/sparql/router.py','backend/app/validation/router.py','backend/app/health/router.py','backend/app/admin/router.py','backend/app/inference/router.py','backend/app/lint/router.py','backend/app/apps/admin_router.py','backend/app/apps/router.py','backend/app/shell/router.py']]"` — no SyntaxError

## Inputs

- `backend/app/commands/router.py` — existing router, needs tags
- `backend/app/sparql/router.py` — existing router, needs tags
- `backend/app/validation/router.py` — existing router, needs tags
- `backend/app/health/router.py` — existing router, needs tags
- `backend/app/admin/router.py` — existing router, needs tags
- `backend/app/inference/router.py` — existing router, needs tags
- `backend/app/lint/router.py` — existing router, needs tags
- `backend/app/apps/admin_router.py` — existing router, needs tags
- `backend/app/apps/router.py` — existing router, needs tags
- `backend/app/shell/router.py` — existing router, needs tags

## Expected Output

- `backend/app/commands/router.py` — `APIRouter(prefix="/api", tags=["commands"])`
- `backend/app/sparql/router.py` — `APIRouter(prefix="/api", tags=["sparql"])`
- `backend/app/validation/router.py` — `APIRouter(prefix="/api", tags=["validation"])`
- `backend/app/health/router.py` — `APIRouter(prefix="/api", tags=["health"])`
- `backend/app/admin/router.py` — `APIRouter(prefix="/admin", tags=["admin"])`
- `backend/app/inference/router.py` — `APIRouter(prefix="/api/inference", tags=["inference"])`
- `backend/app/lint/router.py` — `APIRouter(prefix="/api/lint", tags=["lint"])`
- `backend/app/apps/admin_router.py` — `APIRouter(tags=["app-management"])`
- `backend/app/apps/router.py` — `APIRouter(tags=["app-proxy"])`
- `backend/app/shell/router.py` — `APIRouter(tags=["shell"])`
