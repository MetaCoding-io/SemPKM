# S06 (PROV-O Alignment Design) — Research

**Date:** 2026-03-14  
**Status:** Complete

## Summary

SemPKM has two distinct provenance systems: the **EventStore** (immutable event graphs for data changes, using custom `sempkm:` predicates) and the **Operations Log** (system activity logging, using PROV-O Starting Point terms). Additionally, there are three other subsystems with provenance-adjacent metadata: comments (`sempkm:commentedBy/At`), validation reports (`sempkm:LintRun` with `sempkm:timestamp`), and federation (`sempkm:syncSource/graphTarget`).

The audit reveals a clean split. The ops log already uses correct PROV-O Starting Point terms (`prov:Activity`, `prov:startedAtTime`, `prov:endedAtTime`, `prov:wasAssociatedWith`, `prov:used`). The EventStore uses 7 custom `sempkm:` predicates that have direct PROV-O equivalents — but migrating them carries significant risk because they are load-bearing in 3+ modules and are serialized into immutable named graphs that cannot be retroactively altered. The design doc should recommend a phased approach: validate current ops log patterns, document the mapping from `sempkm:` to PROV-O for future alignment, and identify which new features should adopt PROV-O natively.

## Recommendation

**Produce a design doc with three sections:**

1. **Audit table** — Every `sempkm:` predicate with provenance semantics mapped to its PROV-O equivalent (or "no equivalent / keep custom")
2. **Migration plan** — Phased: Phase 0 (now): ops log is already aligned; Phase 1 (next milestone): new features use PROV-O natively; Phase 2 (future): dual-write compatibility layer for EventStore predicates; Phase 3 (future): read-side migration for existing event graphs
3. **UI exposure recommendation** — What provenance data to surface in the user-facing workspace vs. admin-only

The doc is purely descriptive — no code changes in this slice.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| PROV-O vocabulary | W3C PROV-O (https://www.w3.org/TR/prov-o/) | Standard ontology with Starting Point / Qualified / Extended tiers — use Starting Point only |
| RDF namespace for PROV | `app.rdf.namespaces.PROV` (already registered) | Namespace already in `COMMON_PREFIXES` with `prov:` prefix — available in all SPARQL queries |

## Existing Code and Patterns

### Two Provenance Systems

**1. EventStore (`backend/app/events/`)** — The immutable event log for data changes:
- `models.py` defines 7 custom predicates:
  - `sempkm:Event` (rdf:type value)
  - `sempkm:timestamp` → PROV-O equivalent: `prov:startedAtTime`
  - `sempkm:operationType` → No direct PROV-O equivalent (custom extension needed)
  - `sempkm:affectedIRI` → PROV-O equivalent: `prov:generated` or `prov:used`
  - `sempkm:description` → PROV-O equivalent: `rdfs:label` (already used by ops log)
  - `sempkm:performedBy` → PROV-O equivalent: `prov:wasAssociatedWith`
  - `sempkm:performedByRole` → PROV-O Qualified: `prov:qualifiedAssociation` + `prov:hadRole`
- `store.py` also uses `sempkm:syncSource` and `sempkm:graphTarget` for federation — no PROV-O equivalents (federation-specific metadata)
- **Consumed by:** `events/query.py` (EventQueryService with SPARQL queries), `federation/router.py` (patch export filtering), `browser/event_log.html` + `event_detail.html` (UI rendering)
- **Critical constraint:** Event graphs are immutable named graphs — triples are written once and never updated. Retroactive migration would require rewriting thousands of named graphs.

**2. OperationsLogService (`backend/app/services/ops_log.py`)** — System activity logging:
- Already uses PROV-O Starting Point terms correctly:
  - `prov:Activity` (rdf:type)
  - `prov:startedAtTime`, `prov:endedAtTime`
  - `prov:wasAssociatedWith` (actor)
  - `prov:used` (related resources)
- Custom extensions (appropriate — no PROV-O equivalents):
  - `sempkm:activityType` — short classification string like `model.install`
  - `sempkm:status` — `success` / `failed`
  - `sempkm:errorMessage` — error detail for failed activities
- Uses `rdfs:label` for human-readable descriptions (matches PROV-O convention)
- **4 instrumentation points:** model install/remove (admin/router.py), inference run (inference/router.py), validation run (validation/queue.py)

### Other Provenance-Adjacent Subsystems

**3. Comments (`backend/app/browser/comments.py`)**:
- `sempkm:Comment` type with `sempkm:commentedBy` (author) and `sempkm:commentedAt` (timestamp)
- PROV-O equivalents: `prov:wasAttributedTo` + `prov:generatedAtTime`
- Low migration value — comments are a small, self-contained domain

**4. Validation Reports (`backend/app/validation/report.py`)**:
- `sempkm:LintRun` with `sempkm:timestamp`, `sempkm:triggerSource`, `sempkm:conforms`, severity counts
- `sempkm:ValidationReport` with `sempkm:forEvent`, `sempkm:timestamp`
- PROV-O equivalents: `prov:Activity` for LintRun, `prov:wasGeneratedBy` for forEvent
- Medium migration value — validation runs are activities, but SHACL already defines its own report vocabulary

**5. Query Execution History (`backend/app/sparql/query_service.py`)**:
- `urn:sempkm:vocab:QueryExecution` with `prov:startedAtTime` (already using PROV-O!) and `urn:sempkm:vocab:executedBy`
- Partial alignment — timestamp uses PROV-O, but actor uses custom predicate

**6. Federation (`backend/app/events/store.py` + `federation/`)**:
- `sempkm:syncSource` — origin instance for loop prevention
- `sempkm:graphTarget` — which graph an event targets
- No PROV-O equivalents — these are federation protocol metadata, not provenance

### Complete Custom Predicate Inventory (Provenance-Related)

| Predicate | Location | PROV-O Equivalent | Migration Risk |
|-----------|----------|-------------------|----------------|
| `sempkm:Event` (type) | events/models.py | `prov:Activity` | **HIGH** — load-bearing in EventQueryService, federation export, event log UI |
| `sempkm:timestamp` | events/models.py | `prov:startedAtTime` | **HIGH** — queried by timestamp in EventQueryService, cursor pagination |
| `sempkm:operationType` | events/models.py | None (custom extension) | N/A — keep as-is |
| `sempkm:affectedIRI` | events/models.py | `prov:generated` | **HIGH** — GROUP_CONCAT in event queries, filter by object |
| `sempkm:description` | events/models.py | `rdfs:label` | MEDIUM — already used by ops log |
| `sempkm:performedBy` | events/models.py | `prov:wasAssociatedWith` | **HIGH** — user filter in EventQueryService |
| `sempkm:performedByRole` | events/models.py | `prov:qualifiedAssociation` + `prov:hadRole` | LOW — optional metadata, rarely queried |
| `sempkm:syncSource` | events/store.py | None | N/A — federation-specific |
| `sempkm:graphTarget` | events/store.py | None | N/A — federation-specific |
| `sempkm:commentedBy` | browser/comments.py | `prov:wasAttributedTo` | LOW — self-contained |
| `sempkm:commentedAt` | browser/comments.py | `prov:generatedAtTime` | LOW — self-contained |
| `sempkm:LintRun` (type) | validation/report.py | `prov:Activity` | MEDIUM — lint queries reference type |
| `sempkm:triggerSource` | validation/report.py | None (custom extension) | N/A — keep as-is |

## Constraints

- **Immutable event graphs** — Event named graphs (`urn:sempkm:event:{uuid}`) are append-only by design. Retroactive migration of existing triples would require rewriting every historical event graph, which contradicts the immutability guarantee and could break federation sync (events reference predicates by IRI in serialized patches).
- **EventQueryService SPARQL queries** — `events/query.py` has hardcoded SPARQL strings with `sempkm:` prefix references. Any predicate rename requires updating both write-side (`store.py`) and read-side (`query.py`) simultaneously.
- **Federation patch export** — `federation/router.py` queries event graphs by `sempkm:timestamp`, `sempkm:graphTarget`, and `sempkm:syncSource`. These predicates are part of the federation wire protocol — changing them would break cross-instance sync.
- **Ops log already aligned** — The operations log service already uses PROV-O correctly. No migration needed there.
- **PROV namespace registered** — `PROV = Namespace("http://www.w3.org/ns/prov#")` and `"prov": str(PROV)` in COMMON_PREFIXES means PROV-O terms can be used in any SPARQL query immediately.

## Common Pitfalls

- **Migrating immutable data** — Attempting to rewrite event named graphs would violate the event-sourcing contract. The design doc should explicitly state that existing events retain `sempkm:` predicates forever; alignment applies only to newly written data.
- **Over-qualifying provenance** — PROV-O Qualified terms (`prov:qualifiedAssociation`, `prov:hadPlan`, `prov:hadRole`) add significant triple count per entity. For SemPKM's use case, Starting Point terms cover 90%+ of the value. The design doc should explicitly recommend against Qualified terms except for `performedByRole` where the mapping is clean.
- **Breaking EventQueryService pagination** — EventQueryService cursor pagination uses `FILTER(?timestamp < cursor)` against `sempkm:timestamp`. If new events use `prov:startedAtTime` while old events use `sempkm:timestamp`, the query must handle both predicates or pagination breaks for mixed-era timelines.
- **Conflating Events with Activities** — `sempkm:Event` represents an immutable data-change record; `prov:Activity` represents something that happened. They overlap conceptually but serve different purposes. The design doc should clarify whether Events should become Activities or whether they remain a distinct concept that *links to* Activities.

## Open Risks

- **Dual-predicate query complexity** — If the migration path requires reading both old (`sempkm:timestamp`) and new (`prov:startedAtTime`) predicates, every SPARQL query touching events needs UNION or COALESCE patterns, increasing complexity and potentially affecting performance.
- **PROV-O Agent modeling** — PROV-O uses `prov:Agent` as a type for actors. SemPKM currently uses bare IRIs (`urn:sempkm:user:{uuid}`) without typing them as agents. If `prov:Agent` typing is added, it needs a separate graph or risks polluting the current state graph.
- **Design doc scope creep** — The doc could easily spiral into designing a full provenance framework. The slice scope is bounded: audit, map, recommend. No code changes.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| PROV-O | (none) | none found — PROV-O is a W3C standard, not a code library |
| RDF / SPARQL | (none) | none found — no relevant coding skills for RDF ontology alignment |

## Sources

- PROV-O vocabulary and term definitions (source: [W3C PROV-O Recommendation](https://www.w3.org/TR/prov-o/))
- S02 Forward Intelligence — PROV-O Starting Point terms sufficient, no need for Qualified/Extended
- Existing ops log service code in `backend/app/services/ops_log.py`
- EventStore and models in `backend/app/events/store.py` and `backend/app/events/models.py`
- EventQueryService SPARQL patterns in `backend/app/events/query.py`
- Query service partial PROV-O adoption in `backend/app/sparql/query_service.py` (uses `prov:startedAtTime`)
