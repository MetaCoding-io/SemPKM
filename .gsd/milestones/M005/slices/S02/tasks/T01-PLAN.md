---
estimated_steps: 6
estimated_files: 2
---

# T01: Build OperationsLogService with unit tests

**Slice:** S02 — Operations Log & PROV-O Foundation
**Milestone:** M005

## Description

Create the `OperationsLogService` as a standalone service module at `backend/app/services/ops_log.py`. This follows the `QueryService` pattern exactly: raw SPARQL strings (not rdflib graph objects), `_esc()` helper for safe literal inclusion, `_now_iso()` for timestamps, and direct `TriplestoreClient.update()`/`query()` calls. All data lives in a single `urn:sempkm:ops-log` named graph.

Unit tests validate SPARQL generation correctness without requiring a running triplestore — they mock `TriplestoreClient` and assert on the SPARQL strings passed to `update()` and `query()`.

## Steps

1. Create `backend/app/services/ops_log.py` with constants: `OPS_LOG_GRAPH = "urn:sempkm:ops-log"`, PROV-O and SEMPKM vocabulary IRIs, `_esc()`, `_now_iso()`, `_activity_iri()` helpers
2. Implement `log_activity()` — builds SPARQL INSERT DATA with `prov:Activity` type, `sempkm:activityType`, `rdfs:label`, `prov:startedAtTime`, `prov:endedAtTime`, `prov:wasAssociatedWith`, optional `prov:used` triples, optional `sempkm:status`/`sempkm:errorMessage` for failures. Defaults actor to `urn:sempkm:system` if None.
3. Implement `list_activities()` — SPARQL SELECT with ORDER BY DESC, cursor-based pagination via timestamp filter (FILTER(?startedAt < cursor)), LIMIT N+1 for next-page detection. Optional activity_type filter. Returns list of dicts + next cursor.
4. Implement `get_activity()` — single-resource SELECT by activity IRI, returns dict or None
5. Implement `count_activities()` — SELECT COUNT with optional type filter
6. Create `backend/tests/test_ops_log.py` — mock TriplestoreClient, test: INSERT DATA contains correct PROV-O triples, escaping of special characters in labels, system actor default, failed status triples, cursor filter construction, activity type filter, result parsing from SPARQL JSON bindings

## Must-Haves

- [ ] `OperationsLogService` with `log_activity()`, `list_activities()`, `get_activity()`, `count_activities()`
- [ ] PROV-O Starting Point terms used correctly (`prov:Activity`, `prov:startedAtTime`, `prov:endedAtTime`, `prov:wasAssociatedWith`)
- [ ] `sempkm:activityType` and `rdfs:label` on every entry
- [ ] `sempkm:status` and `sempkm:errorMessage` for failed activities
- [ ] `prov:used` for related resource IRIs
- [ ] All SPARQL strings properly escape user-provided text via `_esc()`
- [ ] Unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_ops_log.py -v` — all tests pass
- Manual inspection: `_esc()` handles backslash, single quote, newline, tab
- SPARQL INSERT DATA string contains `GRAPH <urn:sempkm:ops-log>` wrapper

## Inputs

- `backend/app/sparql/query_service.py` — reference pattern for raw SPARQL service style
- `backend/app/events/query.py` — reference pattern for cursor-based pagination
- `backend/app/events/models.py` — `SYSTEM_ACTOR_IRI` constant
- `backend/app/rdf/namespaces.py` — `PROV` namespace object (for reference, but service uses raw IRI strings)

## Observability Impact

- **New log signal:** `log_activity()` emits `logger.info("Logged ops activity: %s", activity_type)` on every successful write — grep for `"Logged ops activity"` in structured logs to confirm entries are being recorded.
- **Failure visibility:** Callers are expected to wrap `log_activity()` in try/except and log at WARNING — the service itself raises on triplestore errors so the caller controls fire-and-forget semantics.
- **Inspection surface:** All data in `urn:sempkm:ops-log` named graph. Direct SPARQL `SELECT * WHERE { GRAPH <urn:sempkm:ops-log> { ?s ?p ?o } }` via the SPARQL console returns all log entries.
- **No new endpoints yet** — the admin UI route and DI wiring come in T02/T03.

## Expected Output

- `backend/app/services/ops_log.py` — complete service module with all 4 methods
- `backend/tests/test_ops_log.py` — unit tests covering SPARQL generation, escaping, pagination, and result parsing
