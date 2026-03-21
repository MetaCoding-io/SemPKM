---
estimated_steps: 8
estimated_files: 4
---

# T01: SQLAlchemy models, Alembic migration, and LintFilterService CRUD with unit tests

**Slice:** S03 — Lint Filter System (Suppress, Dismiss, Presets)
**Milestone:** M030

## Description

Create the persistence layer for lint filters: 3 SQLAlchemy ORM models (`LintSuppression`, `LintDismissal`, `LintPreset`), an Alembic migration to create the tables, and a `LintFilterService` with full async CRUD operations. This follows the established `PersonaService` + `UserFavorite` patterns exactly.

The key design decisions are:
- D279: Lint filter storage in SQLite with server-side Python filtering
- D280: Additive suppression model — presets store what to hide, not what to show

## Steps

1. Create `backend/app/lint/filter_models.py` with 3 SQLAlchemy ORM models:
   - `LintSuppression`: UUID PK, `user_id` FK to `users.id` with CASCADE, `rule_source_iri` String(2048), `created_at` DateTime(timezone=True) with server_default=func.now(), UniqueConstraint("user_id", "rule_source_iri")
   - `LintDismissal`: UUID PK, `user_id` FK to `users.id` with CASCADE, `object_iri` String(2048), `rule_source_iri` String(2048), `created_at` DateTime(timezone=True) with server_default=func.now(), UniqueConstraint("user_id", "object_iri", "rule_source_iri")
   - `LintPreset`: UUID PK, `user_id` FK to `users.id` with CASCADE, `name` String(255), `suppressed_rules_json` Text (JSON array of rule IRIs), `created_at` DateTime(timezone=True) with server_default=func.now(), `updated_at` DateTime(timezone=True) with server_default=func.now() onupdate=func.now(), UniqueConstraint("user_id", "name")
   - Follow `UserFavorite` pattern in `backend/app/favorites/models.py` exactly for style/imports
   - Import `Base` from `app.db.base`

2. Create `backend/migrations/versions/015_lint_filters.py` Alembic migration:
   - Revision ID: generate a random 12-char hex string
   - Down revision: `"014"` (match pattern of existing migrations — check `014_app_tables.py` for exact revision id)
   - Three `op.create_table()` calls matching the ORM models
   - `downgrade()` drops all 3 tables

3. Create `backend/app/lint/filter_service.py` with `LintFilterService` class:
   - Constructor takes `session_factory` (async context manager) — same pattern as `PersonaService.__init__`
   - Dataclass read models: `SuppressionData`, `DismissalData`, `PresetData`
   - Suppression methods: `add_suppression(user_id, rule_source_iri)` → returns SuppressionData (rejects empty rule_source_iri), `list_suppressions(user_id)` → list[SuppressionData], `delete_suppression(suppression_id, user_id)` → bool, `clear_suppressions(user_id)` → int (count deleted)
   - Dismissal methods: `add_dismissal(user_id, object_iri, rule_source_iri)` → DismissalData (rejects empty fields), `list_dismissals(user_id)` → list[DismissalData], `delete_dismissal(dismissal_id, user_id)` → bool, `clear_dismissals(user_id)` → int
   - Preset methods: `create_preset(user_id, name, suppressed_rules: list[str])` → PresetData, `list_presets(user_id)` → list[PresetData], `update_preset(preset_id, user_id, name=None, suppressed_rules=None)` → PresetData | None, `delete_preset(preset_id, user_id)` → bool, `apply_preset(preset_id, user_id)` → bool (replaces all user's suppressions with preset's rule list per D280)
   - `suppressed_rules_json` stored as JSON string via `json.dumps()`/`json.loads()`
   - All methods use `async with self._session_factory() as session:` pattern
   - Authorization by `user_id` match on all operations (following PersonaService)
   - Handle UniqueConstraint violations with try/except IntegrityError → return existing or raise ValueError
   - `get_user_filters(user_id)` → tuple[set[str], set[tuple[str,str]]] — convenience method returning (suppressed_rule_iris, dismissed_object_rule_pairs) for passing directly to LintService

4. Write `backend/tests/test_lint_filter_service.py`:
   - Use in-memory SQLite with `create_async_engine("sqlite+aiosqlite:///:memory:")` and `async_sessionmaker`
   - Create tables via `Base.metadata.create_all()` in async fixture
   - Insert a test user directly in the users table (UUID, email, role)
   - Tests: create suppression, list suppressions, duplicate suppression raises/returns existing, delete suppression, clear all suppressions (returns count), reject empty rule_source_iri
   - Tests: create dismissal, list dismissals, duplicate dismissal, delete dismissal, clear all dismissals
   - Tests: create preset, list presets, update preset name, update preset rules, delete preset, apply preset (verify it replaces suppressions)
   - Test `get_user_filters()` returns correct sets
   - Target: 18+ tests

## Must-Haves

- [ ] 3 SQLAlchemy models with correct FK constraints and UniqueConstraints
- [ ] Alembic migration 015 with upgrade + downgrade
- [ ] LintFilterService with all CRUD methods + apply_preset + get_user_filters
- [ ] Dataclass read models for API responses
- [ ] 18+ unit tests passing

## Verification

- `cd backend && python -m pytest tests/test_lint_filter_service.py -v` — all tests pass
- `python -c "from app.lint.filter_models import LintSuppression, LintDismissal, LintPreset; print('OK')"` — models import correctly

## Inputs

- `backend/app/favorites/models.py` — reference for SQLAlchemy ORM model pattern
- `backend/app/persona/service.py` — reference for async service CRUD pattern
- `backend/app/db/base.py` — `Base` import for ORM models
- `backend/migrations/versions/014_app_tables.py` — previous migration (for down_revision linkage)

## Observability Impact

- **New signals:** INFO-level logs in LintFilterService on all CRUD mutations (create/delete suppression, create/delete dismissal, create/update/delete/apply preset, clear operations) — following PersonaService logging pattern
- **Inspection surfaces:** `LintFilterService.get_user_filters(user_id)` returns current filter state as `(set[str], set[tuple[str,str]])` — usable for diagnostics without DB queries
- **Failure visibility:** `ValueError` raised on empty IRI fields, `IntegrityError` caught on duplicate entries — both produce deterministic error messages for debugging
- **How to inspect later:** Query `lint_suppressions`, `lint_dismissals`, `lint_presets` tables directly, or call service methods from a REPL; check INFO logs for CRUD operation audit trail

## Expected Output

- `backend/app/lint/filter_models.py` — 3 ORM model classes
- `backend/app/lint/filter_service.py` — LintFilterService with ~15 async methods
- `backend/migrations/versions/015_lint_filters.py` — Alembic migration
- `backend/tests/test_lint_filter_service.py` — 18+ passing unit tests
