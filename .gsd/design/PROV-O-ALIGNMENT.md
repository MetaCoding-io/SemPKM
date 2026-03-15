# PROV-O Alignment Design

> **Status:** Accepted  
> **Date:** 2026-03-14  
> **Scope:** Audit all custom `sempkm:` provenance predicates against PROV-O equivalents; propose a phased migration plan; recommend what provenance data to surface in the workspace vs. admin-only UI.

---

## Current State

SemPKM has **two primary provenance systems** and **three provenance-adjacent subsystems**, each with different levels of PROV-O alignment.

### Primary Provenance Systems

**1. EventStore** (`backend/app/events/`)

The immutable event log for data changes. Every mutation (object create, patch, edge create, body set) is recorded as a named graph (`urn:sempkm:event:{uuid}`) containing both the data triples and event metadata.

Uses **7 custom `sempkm:` predicates** defined in `events/models.py`:

| Predicate | Purpose |
|-----------|---------|
| `sempkm:Event` | rdf:type value for event metadata subjects |
| `sempkm:timestamp` | When the event occurred (xsd:dateTime) |
| `sempkm:operationType` | What kind of mutation (e.g. `object.create`, `edge.patch`) |
| `sempkm:affectedIRI` | Which resource(s) were changed |
| `sempkm:description` | Human-readable description of the change |
| `sempkm:performedBy` | User IRI who performed the action |
| `sempkm:performedByRole` | Role of the user (e.g. `owner`, `editor`) |

Consumed by: `events/query.py` (EventQueryService with SPARQL queries, cursor pagination), `federation/router.py` (patch export filtering), `browser/event_log.html` + `event_detail.html` (UI rendering).

**Critical constraint:** Event graphs are **immutable** named graphs — triples are written once and never updated. Retroactive migration would require rewriting thousands of named graphs, which contradicts the event-sourcing contract and could break federation sync.

**2. Operations Log** (`backend/app/services/ops_log.py`)

System activity logging for admin-visible operations (model install/remove, inference runs, validation runs). Stores `prov:Activity` instances in the `urn:sempkm:ops-log` named graph.

**Already uses PROV-O Starting Point terms correctly:**

| Term | Usage |
|------|-------|
| `prov:Activity` | rdf:type for log entries |
| `prov:startedAtTime` | Activity start timestamp |
| `prov:endedAtTime` | Activity end timestamp |
| `prov:wasAssociatedWith` | Actor who performed the activity |
| `prov:used` | Resources the activity consumed |

Custom extensions (appropriate — no PROV-O equivalents exist):
- `sempkm:activityType` — short classification string like `model.install`
- `sempkm:status` — `success` / `failed`
- `sempkm:errorMessage` — error detail for failed activities
- Uses `rdfs:label` for human-readable descriptions (matches PROV-O conventions)

**No migration needed** — the ops log is already aligned.

### Provenance-Adjacent Subsystems

**3. Comments** (`backend/app/browser/comments.py`)

- `sempkm:Comment` type with `sempkm:commentedBy` (author) and `sempkm:commentedAt` (timestamp)
- PROV-O equivalents exist: `prov:wasAttributedTo` + `prov:generatedAtTime`
- Low migration value — comments are a small, self-contained domain with no cross-module dependencies

**4. Validation Reports** (`backend/app/validation/report.py`)

- `sempkm:LintRun` type with `sempkm:timestamp`, `sempkm:triggerSource`, `sempkm:conforms`, severity counts
- `sempkm:ValidationReport` with `sempkm:forEvent`, `sempkm:timestamp`
- PROV-O equivalents: `prov:Activity` for LintRun, `prov:wasGeneratedBy` for `forEvent`
- SHACL already defines its own report vocabulary — adding PROV-O on top yields minimal value

**5. Query Execution History** (`backend/app/sparql/query_service.py`)

- `urn:sempkm:vocab:QueryExecution` type with `prov:startedAtTime` (already PROV-O!) and `urn:sempkm:vocab:executedBy` (custom)
- **Partially aligned** — timestamp uses PROV-O, but the actor predicate uses a custom term instead of `prov:wasAssociatedWith`

---

## Predicate Audit

Complete mapping of all 13 provenance-related `sempkm:` predicates to PROV-O equivalents.

| # | Predicate | Location | PROV-O Equivalent | Risk | Recommendation |
|---|-----------|----------|-------------------|------|----------------|
| 1 | `sempkm:Event` (type) | events/models.py | `prov:Activity` | **HIGH** | Keep custom for existing events. New features should type as `prov:Activity`. See note [A] below. |
| 2 | `sempkm:timestamp` | events/models.py | `prov:startedAtTime` | **HIGH** | Keep in existing event graphs (immutable). New event-like records should use `prov:startedAtTime`. |
| 3 | `sempkm:operationType` | events/models.py | None — keep custom | **N/A** | Keep as-is. PROV-O has no equivalent for mutation-type classification. The ops log uses `sempkm:activityType` for the same concept. |
| 4 | `sempkm:affectedIRI` | events/models.py | `prov:generated` or `prov:used` | **HIGH** | Keep custom. PROV-O's `prov:generated`/`prov:used` have specific semantics (output vs. input) that don't map cleanly to "which resource was changed." |
| 5 | `sempkm:description` | events/models.py | `rdfs:label` | **MEDIUM** | Low priority. The ops log already uses `rdfs:label` for descriptions. EventStore could adopt the same convention for new events, but existing events retain `sempkm:description`. |
| 6 | `sempkm:performedBy` | events/models.py | `prov:wasAssociatedWith` | **HIGH** | Keep in existing event graphs. Phase 2 dual-write would add `prov:wasAssociatedWith` alongside `sempkm:performedBy` for new events. |
| 7 | `sempkm:performedByRole` | events/models.py | `prov:qualifiedAssociation` + `prov:hadRole` | **LOW** | Keep custom. The Qualified PROV-O pattern (`prov:qualifiedAssociation` → blank node → `prov:hadRole`) adds significant triple count for minimal benefit. See Recommendation against Qualified terms. |
| 8 | `sempkm:syncSource` | events/store.py | None — federation-specific | **N/A** | Keep as-is. No PROV-O equivalent. This is federation wire-protocol metadata, not provenance. |
| 9 | `sempkm:graphTarget` | events/store.py | None — federation-specific | **N/A** | Keep as-is. No PROV-O equivalent. Part of the federation protocol. |
| 10 | `sempkm:commentedBy` | browser/comments.py | `prov:wasAttributedTo` | **LOW** | Low-priority alignment target. Comments are self-contained; migration can happen independently. |
| 11 | `sempkm:commentedAt` | browser/comments.py | `prov:generatedAtTime` | **LOW** | Low-priority alignment target. Same scope as `sempkm:commentedBy`. |
| 12 | `sempkm:LintRun` (type) | validation/report.py | `prov:Activity` | **MEDIUM** | Low-priority alignment target. SHACL already has its own report vocabulary; double-typing as `prov:Activity` is possible but adds complexity without clear benefit. |
| 13 | `sempkm:triggerSource` | validation/report.py | None — keep custom | **N/A** | Keep as-is. No PROV-O equivalent for "what triggered this validation run." |

**Note [A]: `sempkm:Event` vs. `prov:Activity`** — These overlap conceptually but serve different purposes. `sempkm:Event` represents an immutable data-change record (event-sourcing). `prov:Activity` represents "something that happened." For new provenance records that don't need immutable event-graph semantics, use `prov:Activity` directly (as the ops log already does). Existing EventStore events retain `sempkm:Event` typing forever.

### Predicates with No Migration Path (Keep Custom)

Four predicates have no PROV-O equivalent and should remain custom:
- `sempkm:operationType` / `sempkm:activityType` — mutation/activity classification
- `sempkm:syncSource` — federation loop prevention
- `sempkm:graphTarget` — federation graph routing
- `sempkm:triggerSource` — validation trigger origin

These are domain-specific extensions that PROV-O intentionally leaves to application vocabularies.

---

## Migration Plan

### Phase 0: Ops Log Already Aligned ✅ (Complete)

**Status:** Done (S02, M005)

The `OperationsLogService` uses PROV-O Starting Point terms correctly:
- `prov:Activity`, `prov:startedAtTime`, `prov:endedAtTime`, `prov:wasAssociatedWith`, `prov:used`
- Custom extensions (`sempkm:activityType`, `sempkm:status`, `sempkm:errorMessage`) are appropriate — no PROV-O equivalents exist for these concepts
- Uses `rdfs:label` for descriptions, consistent with PROV-O conventions

**No action required.** This is the reference implementation for how new provenance features should model data.

### Phase 1: New Features Adopt PROV-O Natively (Next Milestone)

**Scope:** Any new subsystem or feature that records provenance metadata should use PROV-O Starting Point terms from day one.

**Concrete actions:**
1. **Query Execution History** — complete its partial alignment by replacing `urn:sempkm:vocab:executedBy` with `prov:wasAssociatedWith`. This is a low-risk change affecting only `backend/app/sparql/query_service.py` (write + read in the same file).
2. **New features** — any future provenance-recording feature (e.g., export history, sharing activity) must follow the ops log pattern: `prov:Activity` + Starting Point terms + custom extensions only where no PROV-O term exists.
3. **Documentation** — update developer docs to reference the ops log service as the canonical pattern for provenance modeling.

**Boundary:** Phase 1 does NOT touch existing EventStore predicates. Existing events remain unchanged.

### Phase 2: Dual-Write Compatibility Layer for EventStore (Future)

**Scope:** When the EventStore writes new event graphs, it writes BOTH `sempkm:` and `prov:` predicates for the overlapping terms.

**Concrete actions:**
1. Modify `events/store.py` to emit additional triples alongside existing ones:
   - `sempkm:timestamp` → also write `prov:startedAtTime`
   - `sempkm:performedBy` → also write `prov:wasAssociatedWith`
   - `sempkm:description` → also write `rdfs:label`
   - `sempkm:Event` (type) → also type as `prov:Activity`
2. Keep `sempkm:affectedIRI`, `sempkm:operationType`, `sempkm:performedByRole` as-is (no clean PROV-O equivalents).
3. Keep `sempkm:syncSource` and `sempkm:graphTarget` as-is (federation-specific, no PROV-O equivalents).

**Boundary:** Phase 2 only changes write-side. All existing SPARQL queries continue to use `sempkm:` predicates and work exactly as before. New events are queryable by both predicate sets.

**Existing event graphs are immutable and retain only `sempkm:` predicates forever.** No retroactive migration of historical data is performed. The immutability guarantee is fundamental to the event-sourcing architecture and federation sync protocol.

### Phase 3: Read-Side Migration (Future)

**Scope:** Update SPARQL queries in `events/query.py` and downstream consumers to handle both old-era (`sempkm:` only) and new-era (dual-predicate) events transparently.

**Concrete actions:**
1. Update `EventQueryService` SPARQL queries to use UNION or COALESCE patterns (see Dual-Predicate Query Strategy below).
2. Update `federation/router.py` export queries to handle both predicate sets.
3. Update event log UI templates if they use predicate IRIs directly.

**Boundary:** Phase 3 is the highest-risk phase. It touches load-bearing SPARQL queries with cursor pagination, GROUP_CONCAT aggregation, and cross-graph JOINs. Should be preceded by comprehensive integration tests for the EventQueryService.

**Risk mitigation:**
- Phase 3 is optional if Phase 2 dual-write is sufficient (queries can just keep reading `sempkm:` predicates since dual-write ensures they're always present).
- An alternative is to eventually drop the `sempkm:` predicates from NEW events only after Phase 3 queries are verified — but this adds a "Phase 4" that may never be needed.

---

## Dual-Predicate Query Strategy

During the transition period (after Phase 2 begins, before Phase 3 completes), both old `sempkm:` and new `prov:` predicates coexist. The following SPARQL patterns handle mixed-era data.

### Pattern 1: Timestamp Query with COALESCE

For queries that need a single timestamp variable regardless of which predicate was used:

```sparql
PREFIX sempkm: <urn:sempkm:>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?event ?timestamp ?opType
WHERE {
  GRAPH ?event {
    ?event a sempkm:Event .
    ?event sempkm:operationType ?opType .

    # Handle both old and new timestamp predicates
    OPTIONAL { ?event sempkm:timestamp ?oldTs }
    OPTIONAL { ?event prov:startedAtTime ?newTs }
    BIND(COALESCE(?newTs, ?oldTs) AS ?timestamp)
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
}
ORDER BY DESC(?timestamp)
LIMIT 51
```

**When to use:** When events may have either or both predicates. COALESCE prefers the PROV-O predicate if both exist (dual-write era), falls back to `sempkm:` for old events.

### Pattern 2: Actor Query with UNION

For queries that filter by user across both predicate sets:

```sparql
PREFIX sempkm: <urn:sempkm:>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?event ?actor
WHERE {
  GRAPH ?event {
    ?event a sempkm:Event .
    {
      ?event sempkm:performedBy ?actor .
    } UNION {
      ?event prov:wasAssociatedWith ?actor .
    }
  }
  FILTER(?actor = <urn:sempkm:user:some-uuid>)
}
```

**When to use:** When you need to find events by actor and the actor predicate may be `sempkm:performedBy` (old) or `prov:wasAssociatedWith` (new/dual-write). UNION ensures both are searched.

### Pattern 3: Cursor Pagination with Dual Timestamps

The existing cursor pagination in EventQueryService uses `FILTER(?timestamp < cursor)`. With dual predicates:

```sparql
PREFIX sempkm: <urn:sempkm:>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?event ?timestamp ?opType
       (GROUP_CONCAT(STR(?affectedIRI); separator=",") AS ?affected)
       ?performedBy ?description
WHERE {
  GRAPH ?event {
    ?event a sempkm:Event ;
           sempkm:operationType ?opType ;
           sempkm:affectedIRI ?affectedIRI .

    # Dual-predicate timestamp
    OPTIONAL { ?event sempkm:timestamp ?oldTs }
    OPTIONAL { ?event prov:startedAtTime ?newTs }
    BIND(COALESCE(?newTs, ?oldTs) AS ?timestamp)

    # Dual-predicate actor
    OPTIONAL { ?event sempkm:performedBy ?oldActor }
    OPTIONAL { ?event prov:wasAssociatedWith ?newActor }
    BIND(COALESCE(?newActor, ?oldActor) AS ?performedBy)

    OPTIONAL { ?event sempkm:description ?description }
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
  FILTER(?timestamp < "2026-01-01T00:00:00Z"^^xsd:dateTime)
}
GROUP BY ?event ?timestamp ?opType ?performedBy ?description
ORDER BY DESC(?timestamp)
LIMIT 51
```

**When to use:** Full replacement for the current `list_events()` query once Phase 3 is active. The COALESCE approach keeps the GROUP BY and ORDER BY clean — only one `?timestamp` and `?performedBy` variable downstream.

### Why Not VALUES/BIND for Predicate Abstraction?

An alternative pattern is to use `VALUES ?tsPred { sempkm:timestamp prov:startedAtTime }` with `?event ?tsPred ?timestamp`. This is cleaner syntactically but:
1. Creates cross-products when multiple predicates match (dual-write events match twice)
2. Requires DISTINCT or deduplication logic
3. Performs worse on most triplestores than OPTIONAL + COALESCE

The OPTIONAL + COALESCE pattern is recommended as the standard approach.

---

## UI Exposure Recommendation

### Workspace Users (All Roles)

**Already exposed and should remain:**
- **Creation timestamp** — displayed on object cards and detail views (sourced from `dcterms:created`, not from event graphs directly)
- **Author attribution** — displayed as "Created by {user}" on object detail views

**Should NOT be exposed:**
- Full event graph details (operation types, affected IRIs, diff data) — these are developer/admin concerns
- Event timeline with cursor pagination — overwhelming for content users; the admin event log page exists for this
- PROV-O predicate details — internal vocabulary is not user-facing

### Admin / Debug Surfaces

**Currently exposed and should remain admin-only:**
- **Event Log** (`/browser/events/`) — full event timeline with operation types, user attribution, diffs
- **Event Detail** (`/browser/events/{id}`) — individual event with before/after data triples and body diffs
- **Operations Log** (`/admin/ops-log`) — system activity log with PROV-O Activity instances
- **SPARQL Console** (`/admin/sparql`) — raw query access to all provenance data

**Rationale:** Provenance metadata in SemPKM serves two purposes:
1. **User-facing:** "When was this created?" and "Who created it?" — already rendered from `dcterms:created` and user attribution, not from event provenance
2. **Admin/debug:** "What sequence of mutations led to this state?" and "What system operations ran?" — detailed event and ops log data stays admin-only

No changes to the current UI exposure are recommended. The existing split between workspace views (creation metadata) and admin views (full provenance) is correct.

---

## Recommendations

### 1. Use PROV-O Starting Point Terms Only

The PROV-O ontology has three tiers:
- **Starting Point** — `prov:Activity`, `prov:Entity`, `prov:Agent`, `prov:wasAssociatedWith`, `prov:startedAtTime`, `prov:endedAtTime`, `prov:used`, `prov:generated`, `prov:wasAttributedTo`, `prov:generatedAtTime`
- **Qualified** — `prov:qualifiedAssociation`, `prov:qualifiedGeneration`, `prov:hadRole`, `prov:hadPlan`, etc.
- **Extended** — `prov:hadMember`, `prov:alternateOf`, `prov:specializationOf`, etc.

**Recommendation:** Use Starting Point terms exclusively. Qualified terms add blank nodes and multi-triple patterns for marginal information gain. Extended terms address provenance patterns (bundle tracking, entity specialization) that SemPKM does not need.

The one place where Qualified terms *could* apply is `sempkm:performedByRole` → `prov:qualifiedAssociation` + `prov:hadRole`. However, the current single-predicate approach (`sempkm:performedByRole` stores the role string directly on the event) is simpler, more query-friendly, and adequate for SemPKM's single-user-per-event model. **Do not migrate to Qualified terms.**

### 2. Existing Event Graphs Are Immutable

**Existing event named graphs (`urn:sempkm:event:*`) retain their `sempkm:` predicates forever.** This is not a compromise — it is a design constraint:

- Event-sourcing requires immutable events. Rewriting triples in historical events violates the append-only contract.
- Federation sync transmits event graphs as serialized patches. Changing predicates in existing events would desynchronize federated instances.
- The dual-write + dual-read strategy (Phases 2-3) handles mixed-era data without retroactive changes.

### 3. Comments and Validation Are Low-Priority Alignment Targets

Comments (`sempkm:commentedBy/At`) and validation reports (`sempkm:LintRun`, `sempkm:triggerSource`) have PROV-O equivalents but:
- Are self-contained subsystems with no cross-module predicate dependencies
- Have low query complexity (no cursor pagination, no GROUP_CONCAT)
- Can be migrated independently, at any time, with minimal risk

**Recommendation:** Defer comment/validation alignment until a milestone specifically addresses those subsystems. Do not bundle them into the EventStore migration phases.

### 4. Phase 2 Dual-Write May Be Sufficient Long-Term

If Phase 2 (dual-write) is implemented but Phase 3 (read-side migration) is deferred indefinitely, the system still works correctly:
- Old events: queryable via `sempkm:` predicates (as today)
- New events: queryable via `sempkm:` predicates (dual-write ensures they're present) OR via `prov:` predicates
- External PROV-O consumers can query new events using standard PROV-O terms

Phase 3 is only required if we want to eventually DROP the `sempkm:` predicates from new event writes — which may never be necessary.

---

## Appendix: PROV Namespace Registration

The PROV namespace is already registered in the codebase:

```python
# app/rdf/namespaces.py
PROV = Namespace("http://www.w3.org/ns/prov#")

# COMMON_PREFIXES (available in all SPARQL queries)
"prov": str(PROV)
```

No namespace setup is required for any migration phase. PROV-O terms can be used in SPARQL queries immediately with the `prov:` prefix.
