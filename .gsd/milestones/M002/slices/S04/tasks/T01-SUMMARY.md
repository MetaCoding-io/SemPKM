---
id: T01
parent: S04
milestone: M002
provides:
  - shared _helpers.py module with _validate_iri, _format_date, _is_htmx_request, get_settings_service, get_icon_service, _MODELS_DIR
  - settings_router sub-router with 8 settings/LLM route handlers
  - validated include_router() pattern for remaining sub-router extractions
key_files:
  - backend/app/browser/_helpers.py
  - backend/app/browser/settings.py
  - backend/app/browser/router.py
  - backend/tests/test_iri_validation.py
key_decisions:
  - Sub-routers use NO prefix (paths match original since parent router already has /browser prefix)
  - settings_router includes 8 routes (not 7 as plan text said) — the plan listed all 8 paths including /llm/chat/stream
patterns_established:
  - Sub-router pattern: create APIRouter(tags=[...]) with NO prefix, define routes, import in router.py via include_router()
  - Shared helpers live in _helpers.py with explicit imports in each sub-router module
  - Type annotations (e.g. SettingsService, IconService) imported where used as function parameter types
observability_surfaces:
  - Import errors at module load time surface immediately
  - settings_router.routes inspectable at import time to verify route registration
duration: ~10 minutes
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Extract shared helpers and settings/LLM sub-router

**Created `_helpers.py` with 6 shared utilities and `settings.py` sub-router with 8 settings/LLM route handlers, reducing router.py by 311 lines.**

## What Happened

1. Created `backend/app/browser/_helpers.py` (69 lines) containing: `_validate_iri`, `_MODELS_DIR`, `get_settings_service`, `get_icon_service`, `_format_date`, `_is_htmx_request`. Each function carries its original docstring and logic unchanged.

2. Created `backend/app/browser/settings.py` (279 lines) with `settings_router = APIRouter(tags=["settings"])` (no prefix). Moved 8 route handlers: GET /settings, GET /settings/data, PUT /settings/{key:path}, DELETE /settings/{key:path}, PUT /llm/config, POST /llm/test, POST /llm/models, POST /llm/chat/stream. All inline imports (LLMConfigService, httpx, StreamingResponse) kept inside handler bodies.

3. Updated `backend/app/browser/router.py`: removed all moved code, added `from ._helpers import ...` and `from .settings import settings_router`, added `router.include_router(settings_router)`. Router reduced from 1956 to 1645 lines.

4. Updated `backend/tests/test_iri_validation.py` import from `app.browser.router` to `app.browser._helpers`.

## Verification

- `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` — 31/31 passed ✓
- `cd backend && .venv/bin/pytest tests/ -v` — 103/103 passed ✓
- `python -c "from app.browser.router import router; from app.browser.settings import settings_router; print('OK')"` — no import errors ✓
- `python -c "from app.browser._helpers import _validate_iri, _format_date, _is_htmx_request; print('OK')"` — helpers importable ✓
- Route count on main router: 33 (matches original) ✓
- settings_router.routes: 8 handlers verified ✓

### Slice-level checks (partial — intermediate task):
- `cd backend && .venv/bin/pytest tests/ -v` — all 103 unit tests pass ✓
- `python -c "from app.browser.router import router; print(len(router.routes))"` — 33 routes ✓
- `ls backend/app/browser/*.py | wc -l` — 4 files (will be 8 after all tasks complete)
- E2E tests — not run yet (appropriate for final task)

## Diagnostics

- Import the sub-router: `from app.browser.settings import settings_router; print(settings_router.routes)`
- Check route count: `from app.browser.router import router; print(len([r for r in router.routes if hasattr(r, 'methods')]))`
- Import errors surface at app startup time

## Deviations

- Plan said "7 route handlers" but listed 8 paths. Extracted all 8 (including `/llm/chat/stream`) since they're all in the settings/LLM domain.

## Known Issues

None.

## Files Created/Modified

- `backend/app/browser/_helpers.py` — **created** — shared utilities (69 lines): _validate_iri, _MODELS_DIR, get_settings_service, get_icon_service, _format_date, _is_htmx_request
- `backend/app/browser/settings.py` — **created** — settings/LLM sub-router (279 lines) with 8 route handlers
- `backend/app/browser/router.py` — **modified** — removed moved code, added sub-router include (1956→1645 lines)
- `backend/tests/test_iri_validation.py` — **modified** — import path updated to `app.browser._helpers`
