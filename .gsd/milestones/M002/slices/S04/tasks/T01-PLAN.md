---
estimated_steps: 5
estimated_files: 4
---

# T01: Extract shared helpers and settings/LLM sub-router

**Slice:** S04 — Browser Router Refactor
**Milestone:** M002

## Description

Create the `_helpers.py` module containing shared utilities that all sub-routers will import, then extract the first domain — settings and LLM configuration (7 routes) — into `settings.py`. This validates the `include_router()` pattern works correctly before extracting larger domains. Also update the S03 test import path for `_validate_iri`.

## Steps

1. Read the full `backend/app/browser/router.py` to identify exact line ranges for helpers (lines 48–92) and settings/LLM routes (lines 94–423).
2. Create `backend/app/browser/_helpers.py` with: `_validate_iri()` (lines 48–79), `_MODELS_DIR` (line 81), `get_settings_service()` (lines 84–87), `get_icon_service()` (lines 89–92), `_format_date()` (lines 439–446), `_is_htmx_request()` (lines 448–451). Include only the imports these functions need.
3. Create `backend/app/browser/settings.py` with its own `settings_router = APIRouter(tags=["settings"])` (NO prefix). Move 7 route handlers: `/settings`, `/settings/data`, `/settings/{key:path}` PUT, `/settings/{key:path}` DELETE, `/llm/config`, `/llm/test`, `/llm/models`, `/llm/chat/stream`. Import shared utilities from `._helpers`. Keep all inline imports (e.g., `from app.services.llm import LLMConfigService`) inside handler bodies.
4. Update `backend/app/browser/router.py`: remove the moved helpers and 7 settings/LLM handlers. Add `from .settings import settings_router` and `router.include_router(settings_router)` at the position matching original route order (before docs routes). Keep all remaining routes in `router.py` for now. Import helpers from `._helpers` where still needed by remaining routes.
5. Update `backend/tests/test_iri_validation.py` line 11: change `from app.browser.router import _validate_iri` to `from app.browser._helpers import _validate_iri`.

## Must-Haves

- [ ] `_helpers.py` exports `_validate_iri`, `_format_date`, `_is_htmx_request`, `get_settings_service`, `get_icon_service`, `_MODELS_DIR`
- [ ] `settings.py` has exactly 7 route handlers with NO prefix on the sub-router
- [ ] `router.py` includes settings sub-router via `router.include_router(settings_router)`
- [ ] `test_iri_validation.py` import updated to `from app.browser._helpers import _validate_iri`
- [ ] All existing unit tests pass

## Verification

- `cd backend && .venv/bin/pytest tests/test_iri_validation.py -v` — passes with updated import
- `cd backend && .venv/bin/pytest tests/ -v` — all unit tests pass
- `cd backend && python -c "from app.browser.router import router; from app.browser.settings import settings_router; print('OK')"` — no import errors
- `cd backend && python -c "from app.browser._helpers import _validate_iri, _format_date, _is_htmx_request; print('OK')"` — helpers importable

## Observability Impact

- Signals added/changed: None — pure structural move
- How a future agent inspects this: Import the sub-router module and check `settings_router.routes`
- Failure state exposed: Import errors at module load time; missing routes produce 404s

## Inputs

- `backend/app/browser/router.py` — the 1956-line monolith (source of all code to extract)
- `backend/tests/test_iri_validation.py` — S03 test that imports `_validate_iri` (import path must update)
- S04 research — route assignments, line ranges, constraint notes

## Expected Output

- `backend/app/browser/_helpers.py` — ~60 lines of shared utility functions
- `backend/app/browser/settings.py` — ~270 lines with 7 settings/LLM route handlers
- `backend/app/browser/router.py` — reduced by ~330 lines, now imports and includes settings sub-router
- `backend/tests/test_iri_validation.py` — import path updated (1 line change)
