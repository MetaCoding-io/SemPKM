---
id: T01
parent: S05
milestone: M005
provides:
  - RefreshResult dataclass for model artifact refresh operations
  - ModelService.refresh_artifacts() method with transactional CLEAR+INSERT for 4 artifact graphs
key_files:
  - backend/app/services/models.py
  - backend/tests/test_model_refresh.py
key_decisions:
  - Refresh clears all 4 artifact graphs unconditionally (even if archive graph is empty) but only INSERT DATAs for non-empty graphs; this ensures stale triples from a removed artifact file are cleared
  - Model dir path hardcoded to /app/models/{model_id}/ matching the Docker volume mount pattern used by ensure_starter_model
patterns_established:
  - Transaction pattern for refresh: begin → CLEAR SILENT × 4 → INSERT DATA × N → commit, with rollback on any failure
observability_surfaces:
  - logger.info on successful refresh with list of refreshed graph names
  - logger.error on transaction failure
  - RefreshResult.errors list for structured error reporting to callers
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Implement ModelService.refresh_artifacts() with unit tests

**Added `RefreshResult` dataclass and `refresh_artifacts()` method that transactionally clears and reloads 4 artifact graphs (ontology, shapes, views, rules) from disk, explicitly excluding seed graph and registry.**

## What Happened

Added `RefreshResult` dataclass (fields: `success`, `model_id`, `graphs_refreshed`, `errors`) alongside the existing `InstallResult`/`RemoveResult` in `models.py`.

Implemented `refresh_artifacts(model_id)` on `ModelService` following the `install()` transaction pattern:
1. Verify model installed via `is_model_installed()`
2. Check model dir exists at `/app/models/{model_id}/`
3. Parse manifest + load archive from disk
4. Begin RDF4J transaction
5. CLEAR SILENT for exactly 4 graph IRIs (ontology, shapes, views, rules)
6. INSERT DATA for each non-empty artifact graph via `_build_insert_data_sparql()`
7. Commit — or rollback on any failure

Key design choice: all 4 graphs are always CLEARed (even if the archive file is empty/missing), but INSERT DATA is only issued for non-empty graphs. This ensures that if a model author removes an artifact file, stale triples from the old version are properly cleaned up.

Wrote 21 unit tests across 6 test classes covering happy path (success, 4 graphs refreshed, CLEAR/INSERT counts, transaction commit, empty/None rules handling), seed exclusion (seed IRI never in CLEAR or INSERT, registry graph never touched), error cases (model not installed, dir missing, manifest error, archive error), and transaction rollback (INSERT failure, CLEAR failure, rollback failure).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_model_refresh.py -v` — **21/21 tests passed**
- Seed graph IRI (`urn:sempkm:model:basic-pkm:seed`) verified via test assertions to never appear in any CLEAR or INSERT SPARQL call
- Registry graph (`urn:sempkm:models`) verified to never appear in any transaction SPARQL call

### Slice-level verification (partial — T01 is intermediate):
- ✅ `cd backend && python -m pytest tests/test_model_refresh.py -v` — all unit tests pass
- ⬜ Browser: admin models page Refresh button — not yet (T02 scope)

## Diagnostics

- `RefreshResult.errors` contains structured error messages for all failure modes
- Logger output: INFO on success, ERROR on transaction failure
- No persisted observability surface yet — ops log integration is T02 scope

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/services/models.py` — Added `RefreshResult` dataclass and `refresh_artifacts()` method to `ModelService`
- `backend/tests/test_model_refresh.py` — Created 21 unit tests for refresh_artifacts covering happy path, error cases, seed exclusion, and transaction rollback
- `.gsd/milestones/M005/slices/S05/tasks/T01-PLAN.md` — Added missing Observability Impact section
