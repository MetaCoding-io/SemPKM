# S01: PROV-O Retroactive Migration

**Goal:** Migrate all event graphs, comments, and query execution history to use PROV-O predicates instead of custom `sempkm:` predicates. Update write-side and read-side code. Zero old predicates remain.

**Demo:** Event log UI shows correct timestamps and actor names. SPARQL query `SELECT ?e ?t WHERE { GRAPH ?g { ?e prov:startedAtTime ?t } }` returns all events. `SELECT ?e WHERE { GRAPH ?g { ?e sempkm:timestamp ?t } }` returns zero results.

## Must-Haves

- Retroactive SPARQL UPDATE migration script that renames 3 event predicates + 2 comment predicates + 1 query history predicate
- `sempkm:Event rdfs:subClassOf prov:Activity` declaration
- Write-side code updated: `events/models.py`, `events/store.py`, `browser/comments.py`, `sparql/query_service.py`
- Read-side code updated: `events/query.py`, all SPARQL queries referencing old predicates
- Event log and comment UIs render correctly after migration
- Migration is idempotent (safe to re-run)
- All existing tests pass

## Proof Level

- This slice proves: integration (PROV-O predicates work end-to-end through write → store → query → UI)
- Real runtime required: yes (SPARQL UPDATE against real triplestore)
- Human/UAT required: no (test coverage + SPARQL verification)

## Verification

- `cd backend && python -m pytest tests/ -x -q` — all existing tests pass
- `cd backend && python -m pytest tests/test_provo_migration.py -x -q` — new migration tests pass
- SPARQL verification query: zero results for old predicates, non-zero for new
- Event log renders in browser (visual check via E2E or manual)

## Tasks

- [ ] **T01: Update predicate constants and write-side code** `est:30m`
  - Why: Foundation — all new events/comments must be written with PROV-O predicates
  - Files: `backend/app/events/models.py`, `backend/app/events/store.py`, `backend/app/browser/comments.py`, `backend/app/sparql/query_service.py`
  - Do:
    1. In `events/models.py`: change `EVENT_TIMESTAMP = SEMPKM.timestamp` → `PROV.startedAtTime`, `EVENT_PERFORMED_BY = SEMPKM.performedBy` → `PROV.wasAssociatedWith`, `EVENT_DESCRIPTION = SEMPKM.description` → `RDFS.label`. Add `from rdflib.namespace import RDFS` and `from app.rdf.namespaces import PROV`. Keep `EVENT_OPERATION`, `EVENT_AFFECTED`, `EVENT_PERFORMED_BY_ROLE` as custom.
    2. In `browser/comments.py`: change `SEMPKM.commentedBy` → `PROV.wasAttributedTo`, `SEMPKM.commentedAt` → `PROV.generatedAtTime`. Import `PROV` from namespaces.
    3. In `sparql/query_service.py`: change `PRED_EXECUTED_BY` from `VOCAB + "executedBy"` → `str(PROV.wasAssociatedWith)`. Import `PROV`.
    4. `events/store.py` already imports from `events/models.py` so gets the changes automatically.
  - Verify: `cd backend && python -m pytest tests/ -x -q`
  - Done when: all write-side code emits PROV-O predicates; existing tests pass

- [ ] **T02: Update read-side SPARQL queries** `est:45m`
  - Why: Queries must match the new predicates. The design doc confirms straight predicate swap — no COALESCE/UNION needed.
  - Files: `backend/app/events/query.py`, `backend/app/browser/comments.py` (read queries), `backend/app/sparql/query_service.py` (read queries)
  - Do:
    1. In `events/query.py`: replace all `sempkm:timestamp` → `prov:startedAtTime`, `sempkm:performedBy` → `prov:wasAssociatedWith`, `sempkm:description` → `rdfs:label` in SPARQL query strings (lines 126, 129, 130, 170, 173, 174, 218-219, 288, 515, 518, 519)
    2. In `browser/comments.py`: replace `sempkm:commentedAt` → `prov:generatedAtTime`, `sempkm:commentedBy` → `prov:wasAttributedTo` in SPARQL query strings (lines 269, 270, 443)
    3. In `sparql/query_service.py`: all `PRED_EXECUTED_BY` references already use the constant (updated in T01)
    4. Verify SPARQL prefix `prov:` is in COMMON_PREFIXES (it is — confirmed in namespaces.py)
  - Verify: `cd backend && python -m pytest tests/ -x -q`
  - Done when: all read-side queries use PROV-O predicates; all tests pass

- [ ] **T03: Add `sempkm:Event rdfs:subClassOf prov:Activity` and write migration script** `est:45m`
  - Why: The subclass declaration makes events queryable as both `sempkm:Event` and `prov:Activity`. The migration script renames predicates in existing data.
  - Files: `backend/app/events/store.py` (or vocabulary initialization), new file `backend/scripts/migrate_provo.py`
  - Do:
    1. Add the `rdfs:subClassOf` triple. Best location: insert it into the `urn:sempkm:vocab` graph during app initialization or as part of the migration script.
    2. Write `migrate_provo.py` — a standalone script that runs 6 SPARQL UPDATE queries against the triplestore:
       - 3 event predicate renames (`sempkm:timestamp` → `prov:startedAtTime`, `sempkm:performedBy` → `prov:wasAssociatedWith`, `sempkm:description` → `rdfs:label`)
       - 2 comment predicate renames (`sempkm:commentedBy` → `prov:wasAttributedTo`, `sempkm:commentedAt` → `prov:generatedAtTime`)
       - 1 query history rename (`executedBy` → `prov:wasAssociatedWith`)
    3. Make it idempotent: each UPDATE uses DELETE/INSERT WHERE pattern — safe to re-run (no-op when old predicates don't exist)
    4. Add verification queries at the end that assert zero old-predicate triples remain
  - Verify: run migration script against test triplestore, then verify with SPARQL SELECT
  - Done when: migration script exists, is idempotent, and includes self-verification

- [ ] **T04: Tests and verification** `est:30m`
  - Why: Prove the migration is correct and nothing is broken
  - Files: `backend/tests/test_provo_migration.py` (new)
  - Do:
    1. Write unit tests that verify:
       - Event metadata constants point to PROV-O URIs
       - EventStore writes events with `prov:startedAtTime`, `prov:wasAssociatedWith`, `rdfs:label`
       - Comment writes use `prov:wasAttributedTo`, `prov:generatedAtTime`
       - Query execution history uses `prov:wasAssociatedWith`
    2. Run full test suite to catch any regressions
    3. Verify migration script's self-check queries
  - Verify: `cd backend && python -m pytest tests/test_provo_migration.py tests/ -x -q`
  - Done when: new tests pass, full suite passes, zero regressions

## Files Likely Touched

- `backend/app/events/models.py`
- `backend/app/events/store.py`
- `backend/app/events/query.py`
- `backend/app/browser/comments.py`
- `backend/app/sparql/query_service.py`
- `backend/scripts/migrate_provo.py` (new)
- `backend/tests/test_provo_migration.py` (new)
