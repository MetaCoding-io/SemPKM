---
id: T01
parent: S03
milestone: M012
provides:
  - Persona SQLAlchemy model with 9 columns (UUID PK, user FK, name, layout_json, sidebar_positions_json, explorer_mode, is_active, timestamps)
  - Alembic migration 013 creating personas table
  - PersonaService with 8 async methods (create, list_for_user, get, update, delete, activate, get_active, save_state)
  - 20 unit tests covering all CRUD, activation, state save, and authorization paths
key_files:
  - backend/app/persona/models.py
  - backend/app/persona/service.py
  - backend/migrations/versions/013_personas.py
  - backend/tests/test_persona_service.py
key_decisions:
  - PersonaService follows DashboardService pattern exactly — async session factory, dataclass read models, user-scoped operations
patterns_established:
  - Persona module structure mirrors dashboard module (models.py, service.py, __init__.py) for consistency
  - Single-active-persona constraint enforced in activate() via bulk deactivate + targeted activate
  - delete() of active persona auto-activates first remaining (alphabetically) to avoid orphaned state
observability_surfaces:
  - logger.info on create/activate/delete with persona name and user_id
  - logger.warning on not-found/wrong-user access attempts in update/activate/save_state
  - All service methods return None/False for authorization failures (router translates to HTTP 404/403)
duration: 20m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Backend model, migration, service, and unit tests

**Added Persona model, migration 013, and PersonaService with full CRUD + single-active constraint + workspace state save, validated by 20 passing unit tests**

## What Happened

Created the `backend/app/persona/` module following the established `DashboardSpec`/`DashboardService` pattern. The Persona model has 9 columns covering workspace state (layout_json, sidebar_positions_json, explorer_mode) plus the is_active flag for the single-active constraint. Migration 013 creates the table with proper FK to users and index on user_id.

PersonaService implements 8 async methods. The key business rules: `activate()` deactivates all user personas then activates the target (single-active constraint), and `delete()` auto-activates the first remaining persona if the deleted one was active. All methods are user-scoped — operations check user_id ownership and return None/False on mismatch.

Wrote 20 tests (exceeding the 12+ requirement) organized into 6 test classes covering create, list, get, update, delete, activation, and state save — including authorization failure paths and edge cases like delete-active-activates-another and partial state saves.

## Verification

- `python -m pytest tests/test_persona_service.py -v` — 20/20 tests passed in 0.47s
- `grep -c "async def test_"` — returns 20 (exceeds 12+ requirement)
- Model has 9 `Mapped[]` columns confirmed
- Service has 8 public async methods confirmed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_persona_service.py -v` | 0 | ✅ pass | 0.47s |
| 2 | `grep -c "async def test_" backend/tests/test_persona_service.py` | 0 | ✅ pass (20 ≥ 12) | <1s |

### Slice-level verification (partial — T01 of 3)

| # | Check | Status |
|---|-------|--------|
| 1 | PersonaService unit tests pass | ✅ |
| 2 | Browser verification (persona selector, switching) | ⏳ T02/T03 |
| 3 | Failure-path diagnostic (404 on nonexistent) | ⏳ T02 |

## Diagnostics

- **Inspect model:** `sqlite3 backend/sempkm.db ".schema personas"` (after migration runs in Docker)
- **Run tests:** `cd backend && source .venv/bin/activate && python -m pytest tests/test_persona_service.py -v`
- **Check service methods:** `grep "async def " backend/app/persona/service.py`
- **Log output:** PersonaService logs at INFO (create/activate/delete) and WARNING (auth failures) via `logging.getLogger(__name__)`

## Deviations

- Added 5 extra tests beyond the 15 specified in the plan (test_create_persona_with_state, test_delete_nonexistent, test_delete_wrong_user, test_activate_wrong_user, test_save_state_wrong_user) to cover authorization edge cases more thoroughly. No deviation from the plan, just expanded coverage.

## Known Issues

None.

## Files Created/Modified

- `backend/app/persona/__init__.py` — empty module init
- `backend/app/persona/models.py` — Persona SQLAlchemy model (9 columns, users FK)
- `backend/app/persona/service.py` — PersonaService with 8 async CRUD/activation/state methods
- `backend/migrations/versions/013_personas.py` — Alembic migration creating personas table
- `backend/tests/test_persona_service.py` — 20 unit tests covering all service operations
