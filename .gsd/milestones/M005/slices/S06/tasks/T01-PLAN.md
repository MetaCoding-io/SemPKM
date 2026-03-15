---
estimated_steps: 6
estimated_files: 1
---

# T01: Write PROV-O alignment design doc

**Slice:** S06 — PROV-O Alignment Design
**Milestone:** M005

## Description

Write the PROV-O alignment design doc that audits all custom `sempkm:` provenance predicates against PROV-O equivalents, proposes a phased migration plan, and recommends what provenance data to expose in the user-facing workspace vs. admin-only UI. This is a pure documentation task — no code changes.

## Steps

1. Create `.gsd/design/PROV-O-ALIGNMENT.md` with status/date header following the VFS-V2-DESIGN.md convention
2. Write **Current State** section describing the two provenance systems (EventStore with 7 custom predicates, ops log with PROV-O Starting Point terms) and three provenance-adjacent subsystems (comments, validation reports, query execution history)
3. Write **Predicate Audit** table covering all 13 provenance-related predicates from S06-RESEARCH.md: for each, list location, PROV-O equivalent (or "none — keep custom"), migration risk (HIGH/MEDIUM/LOW/N-A), and recommendation
4. Write **Migration Plan** with 4 phases:
   - Phase 0 (Complete): ops log already uses PROV-O correctly
   - Phase 1 (Next milestone): new features adopt PROV-O natively; query execution history completes its partial alignment
   - Phase 2 (Future): dual-write compatibility layer for EventStore — new events use both `sempkm:` and `prov:` predicates
   - Phase 3 (Future): read-side migration — SPARQL queries handle both predicate sets via UNION/COALESCE
5. Write **Dual-Predicate Query Strategy** with concrete SPARQL examples showing how to query mixed-era data (e.g., timestamp across old `sempkm:timestamp` and new `prov:startedAtTime`)
6. Write **UI Exposure Recommendation** section: workspace users see creation timestamps and author attribution (already rendered); full event provenance stays admin/debug only; ops log stays admin-only. Write **Recommendations** summary: use Starting Point only, existing events immutable, comments/validation are low-priority alignment targets

## Must-Haves

- [ ] Complete audit table with all 13 predicates from S06-RESEARCH.md
- [ ] 4-phase migration plan with clear boundaries between phases
- [ ] Explicit statement that immutable event graphs retain `sempkm:` predicates forever
- [ ] Concrete SPARQL patterns for dual-predicate queries
- [ ] UI exposure recommendation distinguishing workspace vs. admin surfaces
- [ ] Recommendation against PROV-O Qualified/Extended terms

## Verification

- `test -f .gsd/design/PROV-O-ALIGNMENT.md` — file exists
- `grep -c "##" .gsd/design/PROV-O-ALIGNMENT.md` — has 6+ sections
- `grep -c "sempkm:" .gsd/design/PROV-O-ALIGNMENT.md` — covers all predicates (10+ occurrences)
- `grep "Phase 0\|Phase 1\|Phase 2\|Phase 3" .gsd/design/PROV-O-ALIGNMENT.md` — all 4 phases present
- `grep "immutable\|Immutable" .gsd/design/PROV-O-ALIGNMENT.md` — immutability constraint documented

## Inputs

- `.gsd/milestones/M005/slices/S06/S06-RESEARCH.md` — complete predicate inventory, migration risk assessment, constraints, pitfalls
- `.gsd/milestones/M005/slices/S02/S02-SUMMARY.md` — PROV-O usage patterns established in ops log, forward intelligence about what works
- `backend/app/services/ops_log.py` — reference implementation of correct PROV-O usage
- `backend/app/events/models.py` — EventStore predicate definitions
- `backend/app/events/query.py` — EventQueryService SPARQL patterns that would need dual-predicate support

## Observability Impact

This is a pure documentation task — no runtime signals change.

- **New artifact:** `.gsd/design/PROV-O-ALIGNMENT.md` — a future agent can `grep` this doc for any predicate name, migration phase, or UI exposure decision
- **No service/log/endpoint changes:** No code is modified; the design doc captures decisions that inform future code slices
- **Failure state:** If the doc is missing sections or predicates, verification grep checks will fail with counts below threshold

## Expected Output

- `.gsd/design/PROV-O-ALIGNMENT.md` — complete design doc with predicate audit, migration plan, query strategy, and UI exposure recommendation
