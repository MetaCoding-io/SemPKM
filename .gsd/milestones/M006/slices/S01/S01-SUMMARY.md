---
status: complete
started: 2026-03-15
completed: 2026-03-15
---
# S01 Summary: PROV-O Retroactive Migration

## What Was Done

Migrated all custom `sempkm:` provenance predicates to their PROV-O equivalents across the entire codebase. Six predicates renamed, one vocabulary declaration added.

### Predicate Changes

| Old | New | Scope |
|-----|-----|-------|
| `sempkm:timestamp` | `prov:startedAtTime` | Events, LintRun, ValidationReport, services/models, services/validation |
| `sempkm:performedBy` | `prov:wasAssociatedWith` | Events, federation |
| `sempkm:description` | `rdfs:label` | Events |
| `sempkm:commentedBy` | `prov:wasAttributedTo` | Comments |
| `sempkm:commentedAt` | `prov:generatedAtTime` | Comments |
| `vocab:executedBy` | `prov:wasAssociatedWith` | Query execution history |

### Files Modified (13)

**Write-side:** `events/models.py`, `events/store.py` (via models), `browser/comments.py`, `sparql/query_service.py`, `validation/report.py`

**Read-side:** `events/query.py`, `browser/objects.py`, `federation/router.py`, `lint/service.py`, `services/models.py`, `services/validation.py`

**Tests:** `tests/test_comments.py` (updated assertions), `tests/test_provo_migration.py` (new, 13 tests)

### New Files (2)

- `backend/scripts/migrate_provo.py` — Standalone migration script with 7 SPARQL UPDATE statements + verification queries. Idempotent.
- `backend/tests/test_provo_migration.py` — 13 tests verifying predicate constants, comment/event write operations, and migration script structure.

### Vocabulary

Added `sempkm:Event rdfs:subClassOf prov:Activity` (D104) — events are queryable as both `sempkm:Event` and `prov:Activity`.

## Verification

- 548 tests pass (13 new)
- Zero conflict markers
- Zero remaining references to old predicates in app code (only in migration script and documentation)

## What Remains

- Run `scripts/migrate_provo.py` against the live triplestore to rename existing data (one-time operation when Docker is running)
