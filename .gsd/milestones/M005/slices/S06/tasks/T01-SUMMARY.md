---
id: T01
parent: S06
milestone: M005
provides:
  - PROV-O alignment design doc with complete predicate audit, 4-phase migration plan, dual-predicate query strategy, and UI exposure recommendation
key_files:
  - .gsd/design/PROV-O-ALIGNMENT.md
key_decisions:
  - Use PROV-O Starting Point terms only — no Qualified or Extended terms
  - Existing immutable event graphs retain sempkm: predicates forever — no retroactive migration
  - Phase 2 dual-write may be sufficient long-term; Phase 3 read-side migration is optional
  - Comments and validation reports are low-priority alignment targets — defer to their own milestones
  - sempkm:affectedIRI has no clean PROV-O equivalent — keep custom
  - sempkm:performedByRole stays custom rather than adopting prov:qualifiedAssociation
patterns_established:
  - Design doc format: Status/Date header, Current State → Audit → Migration Plan → Query Strategy → UI Exposure → Recommendations
  - COALESCE pattern for dual-predicate SPARQL queries (preferred over UNION or VALUES)
observability_surfaces:
  - none
duration: 15m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Write PROV-O alignment design doc

**Complete design doc at `.gsd/design/PROV-O-ALIGNMENT.md` auditing all 13 `sempkm:` provenance predicates against PROV-O, with 4-phase migration plan and dual-predicate query patterns.**

## What Happened

Wrote the PROV-O Alignment Design doc synthesizing S06-RESEARCH.md findings, S02 ops log patterns, and code inspection of EventStore models/queries. The doc covers:

1. **Current State** — describes the two primary provenance systems (EventStore with 7 custom predicates, ops log with PROV-O Starting Point terms) and three provenance-adjacent subsystems (comments, validation, query execution history)
2. **Predicate Audit** — 13-row table mapping every provenance-related `sempkm:` predicate to its PROV-O equivalent, with location, migration risk (HIGH/MEDIUM/LOW/N-A), and recommendation
3. **Migration Plan** — 4 phases from Phase 0 (ops log complete) through Phase 3 (read-side migration), with clear scope boundaries between each phase
4. **Dual-Predicate Query Strategy** — 3 concrete SPARQL patterns (COALESCE for timestamps, UNION for actors, full cursor pagination replacement) with rationale for choosing COALESCE over VALUES
5. **UI Exposure Recommendation** — workspace users see creation timestamps and author attribution; full provenance stays admin/debug only
6. **Recommendations** — Starting Point only, immutable events, comments/validation deferred, Phase 2 may be sufficient long-term

Also applied pre-flight observability fixes to S06-PLAN.md (added Observability/Diagnostics section) and T01-PLAN.md (added Observability Impact section).

## Verification

- ✅ `test -f .gsd/design/PROV-O-ALIGNMENT.md` — file exists
- ✅ 24 `##` sections (requirement: 6+)
- ✅ All 5 required section names present: Current State, Predicate Audit, Migration Plan, UI Exposure, Recommendations
- ✅ 78 occurrences of `sempkm:` (requirement: 10+)
- ✅ All 4 phases present (Phase 0, Phase 1, Phase 2, Phase 3)
- ✅ 7 occurrences of "immutable/Immutable" — immutability constraint documented
- ✅ 360 lines (requirement: 100+)
- ✅ All 13 predicates from S06-RESEARCH.md audit table appear in the doc

Slice-level verification (final task — all must pass):
- ✅ File exists
- ✅ All required sections present
- ✅ Every predicate from research audit table appears
- ✅ Substantive doc (360 lines > 100)

## Diagnostics

None — this is a pure documentation task with no runtime components.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `.gsd/design/PROV-O-ALIGNMENT.md` — new; complete PROV-O alignment design doc (360 lines)
- `.gsd/milestones/M005/slices/S06/S06-PLAN.md` — added Observability/Diagnostics section; marked T01 done
- `.gsd/milestones/M005/slices/S06/tasks/T01-PLAN.md` — added Observability Impact section
