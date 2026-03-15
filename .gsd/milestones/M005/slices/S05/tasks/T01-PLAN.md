---
estimated_steps: 5
estimated_files: 2
---

# T01: Implement ModelService.refresh_artifacts() with unit tests

**Slice:** S05 — Model Schema Refresh
**Milestone:** M005

## Description

Add `RefreshResult` dataclass and `refresh_artifacts()` method to `ModelService`. The method clears and reloads the 4 artifact graphs (ontology, shapes, views, rules) from disk in a single RDF4J transaction, explicitly excluding the seed graph and registry entry. Write comprehensive unit tests with mock triplestore.

## Steps

1. Add `RefreshResult` dataclass to `backend/app/services/models.py` (fields: `success`, `model_id`, `graphs_refreshed`, `errors`)
2. Add `async def refresh_artifacts(self, model_id: str) -> RefreshResult` to `ModelService`:
   - Verify model is installed via `is_model_installed()`
   - Locate model dir at `/app/models/{model_id}/` (use same path pattern as `ensure_starter_model`)
   - Parse manifest via `parse_manifest()`, load archive via `load_archive()`
   - Begin transaction
   - CLEAR SILENT the 4 artifact graphs (ontology, shapes, views, rules) — NOT seed
   - INSERT DATA for each non-empty graph via `_build_insert_data_sparql()`
   - Commit transaction
   - On failure: rollback transaction, return error
3. Write `backend/tests/test_model_refresh.py` with tests:
   - Happy path: model installed, dir exists → 4 graphs cleared and reloaded, RefreshResult.success=True
   - Model not installed → RefreshResult.success=False with error message
   - Model dir not on disk → RefreshResult.success=False with FileNotFoundError message
   - Transaction rollback on INSERT failure → old graphs preserved, RefreshResult.success=False
   - Verify seed graph IRI never appears in any CLEAR or INSERT call

## Must-Haves

- [ ] `RefreshResult` dataclass with success, model_id, graphs_refreshed, errors fields
- [ ] `refresh_artifacts()` clears exactly 4 graph IRIs (ontology, shapes, views, rules) — NOT seed
- [ ] Transaction used: begin → CLEAR × 4 → INSERT DATA × N → commit
- [ ] Transaction rollback on any failure
- [ ] Error handling for model-not-installed and model-dir-missing
- [ ] Unit tests pass with mock triplestore

## Verification

- `cd backend && python -m pytest tests/test_model_refresh.py -v` — all tests pass
- Confirm via test assertions that seed graph IRI (`urn:sempkm:model:{id}:seed`) never appears in CLEAR or INSERT calls

## Inputs

- `backend/app/services/models.py` — `ModelService.install()` as reference pattern for transaction pipeline
- `backend/app/models/registry.py` — `ModelGraphs` for graph IRIs, `is_model_installed()`, `clear_model_graphs()` as anti-pattern (clears all 5 — refresh must clear only 4)
- `backend/app/models/loader.py` — `load_archive()` returns `ModelArchive` with `.seed` field to ignore
- `backend/tests/test_ops_log.py` — reference for mock patterns in this codebase

## Expected Output

- `backend/app/services/models.py` — `RefreshResult` dataclass and `refresh_artifacts()` method added
- `backend/tests/test_model_refresh.py` — unit tests for refresh_artifacts covering happy path, error cases, and seed exclusion

## Observability Impact

- **New signal:** `refresh_artifacts()` logs at INFO level on success (`"Model '{id}' artifacts refreshed: ontology, shapes, views, rules"`) and at ERROR level on transaction failure via `logger.error()`.
- **Inspection:** No new persisted observability surface in this task. Downstream T02 will add ops log entries (`activity_type="model.refresh"`) for runtime visibility.
- **Failure state:** `RefreshResult.errors` list contains structured error messages for all failure modes (not installed, dir missing, manifest error, archive error, transaction error). Callers can inspect these for diagnostics.
