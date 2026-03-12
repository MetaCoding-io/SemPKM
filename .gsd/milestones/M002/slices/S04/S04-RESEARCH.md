# S04: Browser Router Refactor — Research

**Date:** 2026-03-12

## Summary

The browser router at `backend/app/browser/router.py` is a 1956-line monolith with 33 route handlers spanning 6 distinct domains: settings/LLM, objects/CRUD, events, search, workspace/navigation, and pages (docs, canvas, lint-dashboard). All routes live under `/browser/` prefix on a single `APIRouter`. The refactor must split these into focused sub-router modules while preserving every URL path exactly, keeping all 52 E2E tests and 61+ htmx template references working.

The recommended approach is: create domain sub-router modules inside `backend/app/browser/`, extract route handlers and their helpers into them, then reassemble them in the existing `router.py` using `router.include_router()`. This keeps `main.py` unchanged (it still imports `router` from `app.browser.router`), preserves all URL paths, and allows the split to be validated by the existing E2E suite. A latent `Operation` import bug exists in two handlers (`delete_edge`, `bulk_delete_objects`) that should be fixed as part of the refactor.

## Recommendation

**Split into 6 sub-router modules inside `backend/app/browser/`**, each with its own `APIRouter(tags=[...])` but NO prefix (the parent router already has `prefix="/browser"`). The parent `router.py` becomes a thin coordinator that creates the main `APIRouter(prefix="/browser")`, imports each sub-router, and calls `router.include_router(sub_router)` for each.

**Why this approach:**
1. `main.py` only imports `from app.browser.router import router as browser_router` — no change needed there
2. Each sub-router gets no prefix (the parent provides `/browser/`), so all URL paths are preserved exactly
3. FastAPI's `include_router` merges path operations at registration time — no runtime cost, no URL changes
4. Shared utilities (`_validate_iri`, `_format_date`, `_is_htmx_request`, dependency factories) move to a `_shared.py` or `_helpers.py` module importable by all sub-routers
5. The existing `app/views/router.py` (at `/browser/views`) and `app/obsidian/router.py` (at `/browser/import`) are already separate — this just completes the pattern for the remaining routes

**Proposed file structure:**
```
backend/app/browser/
├── __init__.py          (unchanged)
├── router.py            (thin coordinator — imports & includes sub-routers)
├── _helpers.py          (shared: _validate_iri, _format_date, _is_htmx_request, dependency factories)
├── settings.py          (settings + LLM config: 7 routes)
├── objects.py           (object CRUD + relations + lint + edges: 13 routes)
├── events.py            (event log + detail + undo: 3 routes)
├── search.py            (reference search: 1 route)
├── workspace.py         (workspace, nav-tree, tree children, icons, types, my-views: 7 routes)
└── pages.py             (docs, lint-dashboard, canvas: 4 routes — standalone page partials)
```

**Route assignment:**

| Sub-router | Routes | Line count (approx) |
|------------|--------|---------------------|
| settings.py | `/settings`, `/settings/data`, `/settings/{key}` (PUT/DELETE), `/llm/config`, `/llm/test`, `/llm/models`, `/llm/chat/stream` | ~270 |
| objects.py | `/object/{iri}`, `/tooltip/{iri}`, `/objects/{iri}/body`, `/relations/{iri}`, `/edge-provenance`, `/edge/delete`, `/objects/delete`, `/lint/{iri}`, `/objects/new`, `/objects` (POST), `/objects/{iri}/save`, `/types` | ~800 |
| events.py | `/events`, `/events/{iri}/detail`, `/events/{iri}/undo` | ~150 |
| search.py | `/search` | ~80 |
| workspace.py | `/`, `/nav-tree`, `/tree/{type_iri}`, `/icons`, `/my-views` | ~180 |
| pages.py | `/docs`, `/docs/guide/{filename}`, `/lint-dashboard`, `/canvas` | ~80 |
| _helpers.py | `_validate_iri`, `_format_date`, `_is_htmx_request`, `get_settings_service`, `get_icon_service`, `_MODELS_DIR` | ~60 |
| router.py (coordinator) | imports + `include_router` calls | ~30 |

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Sub-router mounting | FastAPI `router.include_router(sub_router)` | Built-in, zero-overhead, preserves all path operations exactly |
| Shared dependencies across sub-routers | Python module import (`from ._helpers import ...`) | Standard pattern, no framework magic needed |

## Existing Code and Patterns

- `backend/app/browser/router.py` — the 1956-line monolith to split. Contains 33 `@router.*` decorators, 7 utility functions/classes, and 40 total function definitions.
- `backend/app/views/router.py` — already a separate router at `prefix="/browser/views"` (601 lines, 9 routes). Mounted directly in `main.py`. This is the reference pattern for a browser sub-domain router.
- `backend/app/obsidian/router.py` — already separate at `prefix="/browser/import"`. Another reference.
- `backend/app/main.py:471` — `app.include_router(browser_router)` — the single integration point. Must NOT change.
- `backend/tests/test_iri_validation.py` — imports `from app.browser.router import _validate_iri`. After refactor, this import path must still work (either keep re-export in router.py or update test import to `from app.browser._helpers import _validate_iri`).
- `backend/app/events/store.py:35` — `class Operation` dataclass. Used in `delete_edge` and `bulk_delete_objects` handlers but never imported (latent NameError bug).

## Constraints

- **Zero URL changes.** All 33 routes must keep exact same paths under `/browser/`. The 52 E2E tests and 61+ htmx template references are the verification.
- **`main.py` import unchanged.** Only `from app.browser.router import router as browser_router` — the coordinator must export `router`.
- **S03 test imports.** `backend/tests/test_iri_validation.py` imports `from app.browser.router import _validate_iri`. Must either keep that import path working (via re-export) or update the test file.
- **Template paths unchanged.** All `TemplateResponse` calls reference `browser/*.html` and `forms/*.html` templates — these are template file paths, not URL paths, so they're unaffected by router restructuring.
- **No behavior changes.** This is structure-only. No request/response changes, no auth changes, no new features.
- **`request.app.state` access.** 25 uses of `request.app.state` (22x `templates`, plus `auth_service`, `triplestore_client`, `async_session_factory`). All work identically in sub-routers since `request.app` always refers to the same FastAPI app instance.

## Common Pitfalls

- **Sub-router prefix stacking.** If a sub-router has `prefix="/settings"` AND the parent has `prefix="/browser"`, the final path becomes `/browser/settings` — correct. But if you accidentally set `prefix="/browser/settings"` on the sub-router, it becomes `/browser/browser/settings`. **Solution:** sub-routers get NO prefix; they define routes with their full sub-path (e.g., `@settings_router.get("/settings")`). The parent provides `/browser/`.
- **Missing `Operation` import.** `delete_edge` (L1178) and `bulk_delete_objects` (L1250) use `Operation(...)` without importing it from `app.events.store`. This is a latent NameError that crashes at runtime. **Must fix during extraction** by adding `from app.events.store import Operation` to `objects.py`.
- **Inline imports scattered through handlers.** Multiple handlers use inline `from app.commands.handlers.*`, `from app.services.llm`, `from app.events.query`, `from app.config`, etc. These must move with their handlers. Keep them inline (they're inline for a reason — lazy loading or avoiding circular imports).
- **`_validate_iri` reachability from tests.** S03 tests import it from `app.browser.router`. After move to `_helpers.py`, either: (a) update test imports, or (b) re-export from `router.py`. Option (a) is cleaner.
- **Dependency function scope.** `get_settings_service()` and `get_icon_service()` are plain functions used in `Depends()`. They reference module-level `_MODELS_DIR`. Moving them to `_helpers.py` means `_MODELS_DIR` moves too — straightforward.

## Open Risks

- **Circular import risk:** Sub-router modules importing from `_helpers.py` while `router.py` imports from sub-routers. This is safe as long as `_helpers.py` doesn't import from `router.py` or any sub-router module. Verified: `_helpers.py` will only contain pure utilities and dependency factories with no router imports.
- **Route registration order:** FastAPI matches routes in registration order. If `include_router` calls change the order relative to the original file, a route like `/object/{object_iri:path}` could shadow `/objects/new`. **Mitigation:** Register sub-routers in the same order as routes appeared in the original file. The path parameter patterns (`{object_iri:path}` vs `/objects/new`) don't actually conflict because the HTTP methods and path prefixes differ (`/object/` vs `/objects/`).
- **htmx `HX-Trigger` headers.** `create_object` and `save_object` set custom `HX-Trigger` response headers with JSON payloads. These are response-level, not routing-level, so they're unaffected by the split.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | wshobson/agents@fastapi-templates (6.1K installs) | available — not needed for this refactor (straightforward APIRouter split) |

## Sources

- FastAPI docs: "Bigger Applications - Multiple Files" — `APIRouter` + `include_router()` pattern (source: [FastAPI GitHub](https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/bigger-applications.md))
- Codebase analysis: `backend/app/browser/router.py` (1956 lines, 33 routes, 40 functions)
- Codebase pattern: `backend/app/views/router.py` — existing sub-router at `/browser/views` prefix
- Codebase pattern: `backend/app/obsidian/router.py` — existing sub-router at `/browser/import` prefix
- S03 test dependency: `backend/tests/test_iri_validation.py` imports `_validate_iri` from `app.browser.router`
