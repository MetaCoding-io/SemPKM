---
id: S06
parent: M005
milestone: M005
provides:
  - PROV-O alignment design doc with complete predicate audit, 4-phase migration plan, dual-predicate query strategy, and UI exposure recommendation
requires:
  - slice: S02
    provides: Working PROV-O usage in operations log (concrete reference for design doc audit)
affects:
  - none (design doc only — no downstream code dependencies)
key_files:
  - .gsd/design/PROV-O-ALIGNMENT.md
key_decisions:
  - "D090: Use PROV-O Starting Point terms only — no Qualified or Extended terms"
  - "D091: Existing immutable event graphs retain sempkm: predicates forever — no retroactive migration"
  - "D092: COALESCE pattern for dual-predicate SPARQL queries (over UNION or VALUES)"
  - "Phase 2 dual-write may be sufficient long-term; Phase 3 read-side migration is optional"
  - "Comments and validation reports are low-priority alignment targets — defer to their own milestones"
  - "sempkm:affectedIRI has no clean PROV-O equivalent — keep custom"
  - "sempkm:performedByRole stays custom rather than adopting prov:qualifiedAssociation"
patterns_established:
  - "Design doc format: Status/Date header, Current State → Audit → Migration Plan → Query Strategy → UI Exposure → Recommendations"
  - "COALESCE pattern for dual-predicate SPARQL queries (preferred over UNION or VALUES)"
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M005/slices/S06/tasks/T01-SUMMARY.md
duration: 15m
verification_result: passed
completed_at: 2026-03-14
---

# S06: PROV-O Alignment Design

**Complete design doc auditing all 13 `sempkm:` provenance predicates against PROV-O equivalents, with a 4-phase migration plan and concrete dual-predicate SPARQL query patterns.**

## What Happened

Wrote the PROV-O Alignment Design doc (`.gsd/design/PROV-O-ALIGNMENT.md`, 360 lines) synthesizing the S06-RESEARCH.md findings, the S02 ops log PROV-O patterns, and code inspection of EventStore models/queries.

The doc covers six sections:

1. **Current State** — describes the two primary provenance systems (EventStore with 7 custom predicates, ops log with PROV-O Starting Point terms) and three provenance-adjacent subsystems (comments, validation, query execution history)
2. **Predicate Audit** — 13-row table mapping every provenance-related `sempkm:` predicate to its PROV-O equivalent, with location, migration risk (HIGH/MEDIUM/LOW/N-A), and recommendation (migrate/keep/defer)
3. **Migration Plan** — 4 phases from Phase 0 (ops log already complete) through Phase 3 (read-side migration with COALESCE queries), with clear scope boundaries and risk mitigation
4. **Dual-Predicate Query Strategy** — 3 concrete SPARQL patterns (COALESCE for timestamps, UNION for actors, full cursor pagination replacement) with rationale for choosing COALESCE over VALUES
5. **UI Exposure Recommendation** — workspace users see creation timestamps and author attribution; full provenance stays admin/debug only; no changes recommended
6. **Recommendations** — Starting Point only, immutable events, comments/validation deferred, Phase 2 may be sufficient long-term

Key insight: The existing split between workspace views (creation metadata from `dcterms:created`) and admin views (full event provenance) is already correct. No UI changes needed.

## Verification

- ✅ `test -f .gsd/design/PROV-O-ALIGNMENT.md` — file exists
- ✅ 24 `##` sections (requirement: 6+)
- ✅ All 5 required section names present: Current State, Predicate Audit, Migration Plan, UI Exposure, Recommendations
- ✅ 78 occurrences of `sempkm:` (requirement: 10+)
- ✅ All 4 phases present (Phase 0, Phase 1, Phase 2, Phase 3)
- ✅ 7 occurrences of "immutable/Immutable" — immutability constraint documented
- ✅ 360 lines (requirement: 100+)
- ✅ All 13 predicates from S06-RESEARCH.md audit table appear in the doc

## Requirements Advanced

- none — this is a design doc; no requirements advanced (implementation deferred to future milestones)

## Requirements Validated

- none — design docs don't validate implementation requirements

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None. Single-task slice completed as planned.

## Known Limitations

- The design doc proposes migration phases but does not implement any of them — implementation is deferred to future milestones
- Phase 3 (read-side migration) touches load-bearing SPARQL queries with cursor pagination and GROUP_CONCAT — comprehensive integration tests needed before attempting
- Query Execution History partial alignment (`urn:sempkm:vocab:executedBy` → `prov:wasAssociatedWith`) identified but not executed — deferred to Phase 1

## Follow-ups

- Phase 1 implementation (new features adopt PROV-O natively) should be planned when a milestone touches the Query Execution History or adds new provenance features
- Phase 2 (dual-write) should be planned when EventStore is next modified for other reasons — piggyback on existing changes

## Files Created/Modified

- `.gsd/design/PROV-O-ALIGNMENT.md` — new; complete PROV-O alignment design doc (360 lines)
- `.gsd/milestones/M005/slices/S06/S06-PLAN.md` — added Observability/Diagnostics section; marked T01 done
- `.gsd/milestones/M005/slices/S06/tasks/T01-PLAN.md` — added Observability Impact section

## Forward Intelligence

### What the next slice should know
- The PROV-O alignment design doc is a reference document, not an implementation plan. No code changes were made. S07 and S08 (design docs) can reference it for provenance modeling conventions.
- The ops log (S02) is the canonical reference implementation for PROV-O usage — any new provenance feature should follow its patterns.

### What's fragile
- Nothing — this is a pure documentation slice with no runtime components.

### Authoritative diagnostics
- `.gsd/design/PROV-O-ALIGNMENT.md` predicate audit table — definitive mapping of all 13 provenance predicates. Consult this before touching any `sempkm:` predicate in EventStore code.

### What assumptions changed
- No assumptions changed. The research (S06-RESEARCH.md) findings were confirmed and synthesized without surprises.
