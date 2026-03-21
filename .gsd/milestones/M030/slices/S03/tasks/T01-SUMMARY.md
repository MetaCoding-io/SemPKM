---
id: T01
parent: S03
milestone: M030
provides:
  - LintSuppression, LintDismissal, LintPreset SQLAlchemy ORM models
  - Alembic migration 015 creating 3 lint filter tables
  - LintFilterService with full async CRUD for suppressions, dismissals, presets
  - SuppressionData, DismissalData, PresetData dataclass read models
  - get_user_filters() convenience method for LintService integration
key_files:
  - backend/app/lint/filter_models.py
  - backend/app/lint/filter_service.py
  - backend/migrations/versions/015_lint_filters.py
  - backend/tests/test_lint_filter_service.py
key_decisions:
  - Duplicate suppressions/dismissals return existing record (idempotent) rather than raising
  - Duplicate preset names raise ValueError (names must be unique per user)
  - apply_preset does atomic delete-all + insert within single session (consistent state)
patterns_established:
  - LintFilterService follows PersonaService session_factory pattern exactly
  - filter_models follow UserFavorite pattern (UUID PK, user_id FK CASCADE, UniqueConstraint)
observability_surfaces:
  - INFO logs on all CRUD mutations (add/delete suppression, add/delete dismissal, create/update/delete/apply preset, clear operations)
  - get_user_filters(user_id) returns (set[str], set[tuple[str,str]]) for runtime inspection
duration: 12m
verification_result: passed
blocker_discovered: false
---

# T01: SQLAlchemy models, Alembic migration, and LintFilterService CRUD with unit tests

**Added 3 lint filter ORM models, Alembic migration 015, and LintFilterService with full CRUD — 30 unit tests passing**

## What Happened

Created the persistence layer for the lint filter system:

1. **ORM models** (`filter_models.py`): Three models following UserFavorite pattern — `LintSuppression` (user + rule IRI, unique pair), `LintDismissal` (user + object IRI + rule IRI, unique triple), `LintPreset` (user + name, stores JSON array of rule IRIs). All use UUID PK, user_id FK with CASCADE, DateTime with server_default.

2. **Alembic migration** (`015_lint_filters.py`): Creates `lint_suppressions`, `lint_dismissals`, `lint_presets` tables with correct constraints. Downgrade drops all three.

3. **LintFilterService** (`filter_service.py`): Full async CRUD following PersonaService pattern — 15 methods covering suppressions (add/list/delete/clear), dismissals (add/list/delete/clear), presets (create/list/update/delete/apply), and convenience `get_user_filters()`. Duplicate handling is idempotent for suppressions/dismissals, raises ValueError for preset names. `apply_preset` atomically replaces all user suppressions with preset rules per D280 additive model.

4. **Unit tests** (`test_lint_filter_service.py`): 30 tests in 5 test classes covering all CRUD operations, validation, duplicate handling, preset application, user isolation, and filter aggregation.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_lint_filter_service.py -v` — 30/30 tests passed in 1.65s
- `cd backend && .venv/bin/python -c "from app.lint.filter_models import LintSuppression, LintDismissal, LintPreset; print('OK')"` — imports OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_lint_filter_service.py -v` | 0 | ✅ pass | 1.65s |
| 2 | `python -c "from app.lint.filter_models import ..."` | 0 | ✅ pass | 0.3s |
| 3 | `python -m pytest tests/test_lint_filtering.py -v` | 4 | ⏳ expected (T03) | 0.01s |
| 4 | `python -m pytest tests/test_lint_filter_api.py -v` | 4 | ⏳ expected (T02) | 0.01s |

## Diagnostics

- **Tables:** Query `lint_suppressions`, `lint_dismissals`, `lint_presets` directly in SQLite
- **Service inspection:** Call `LintFilterService.get_user_filters(user_id)` to see current filter state as `(set[str], set[tuple[str,str]])`
- **Audit trail:** INFO-level logs on all mutations in `app.lint.filter_service` logger
- **Failure modes:** `ValueError` on empty IRI fields or duplicate preset names; `IntegrityError` caught internally for duplicate suppressions/dismissals

## Deviations

None — implemented exactly as planned.

## Known Issues

None.

## Files Created/Modified

- `backend/app/lint/filter_models.py` — 3 SQLAlchemy ORM models (LintSuppression, LintDismissal, LintPreset)
- `backend/app/lint/filter_service.py` — LintFilterService with 15 async CRUD methods + 3 dataclass read models
- `backend/migrations/versions/015_lint_filters.py` — Alembic migration 015 (create 3 tables)
- `backend/tests/test_lint_filter_service.py` — 30 unit tests across 5 test classes
- `.gsd/milestones/M030/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section
