# S01: Redoc API Tag Cleanup

**Goal:** All 85 API routes are organized under descriptive tags in OpenAPI/Redoc — zero routes under "default."
**Demo:** Open `/redoc` and see routes grouped by commands, sparql, validation, health, admin, inference, lint, app-management, app-proxy, shell.

## Must-Haves

- All 10 untagged routers have `tags=["..."]` on their `APIRouter()` constructor
- Zero routes appear under "default" in `/redoc`
- Zero behavior change to any endpoint — paths, methods, auth, and responses are identical

## Verification

- `rg 'APIRouter\(' backend/app/commands/router.py backend/app/sparql/router.py backend/app/validation/router.py backend/app/health/router.py backend/app/admin/router.py backend/app/inference/router.py backend/app/lint/router.py backend/app/apps/admin_router.py backend/app/apps/router.py backend/app/shell/router.py | grep -c 'tags='` returns 10
- `curl -s http://localhost:3000/openapi.json | python3 -c "import sys,json; d=json.load(sys.stdin); tags={t for p in d['paths'].values() for m in p.values() if isinstance(m,dict) for t in m.get('tags',['default'])}; assert 'default' not in tags, f'Found default tag'; print(f'Tags: {sorted(tags)}')"` passes

## Tasks

- [x] **T01: Add tags to all 10 untagged routers** `est:15m`
  - Why: The only task — adds the `tags=` parameter to each `APIRouter()` constructor
  - Files: `backend/app/commands/router.py`, `backend/app/sparql/router.py`, `backend/app/validation/router.py`, `backend/app/health/router.py`, `backend/app/admin/router.py`, `backend/app/inference/router.py`, `backend/app/lint/router.py`, `backend/app/apps/admin_router.py`, `backend/app/apps/router.py`, `backend/app/shell/router.py`
  - Do: For each router file, change `APIRouter(...)` to include `tags=["tag_name"]`. Use these tag names: commands, sparql, validation, health, admin, inference, lint, app-management, app-proxy, shell. Preserve all existing parameters (prefix, etc.).
  - Verify: `rg 'tags=' backend/app/commands/router.py backend/app/sparql/router.py backend/app/validation/router.py backend/app/health/router.py backend/app/admin/router.py backend/app/inference/router.py backend/app/lint/router.py backend/app/apps/admin_router.py backend/app/apps/router.py backend/app/shell/router.py | wc -l` returns 10
  - Done when: All 10 routers have tags, grep confirms 10 matches

## Files Likely Touched

- `backend/app/commands/router.py`
- `backend/app/sparql/router.py`
- `backend/app/validation/router.py`
- `backend/app/health/router.py`
- `backend/app/admin/router.py`
- `backend/app/inference/router.py`
- `backend/app/lint/router.py`
- `backend/app/apps/admin_router.py`
- `backend/app/apps/router.py`
- `backend/app/shell/router.py`
