# S06: PROV-O Alignment Design

**Goal:** A design doc at `.gsd/design/PROV-O-ALIGNMENT.md` audits every custom `sempkm:` predicate with provenance semantics against PROV-O equivalents, proposes a phased migration plan, and recommends what provenance data to expose in the user-facing workspace vs. admin-only UI.

**Demo:** The design doc exists, covers all 13 provenance-related predicates from the research audit, presents a clear 4-phase migration plan (Phase 0 through Phase 3), and includes a UI exposure recommendation section.

## Must-Haves

- Complete audit table mapping every `sempkm:` provenance predicate to its PROV-O equivalent (or "keep custom")
- Phased migration plan: Phase 0 (ops log already aligned), Phase 1 (new features use PROV-O natively), Phase 2 (dual-write compatibility layer for EventStore), Phase 3 (read-side migration for existing events)
- Explicit statement that existing immutable event graphs retain `sempkm:` predicates forever
- Dual-predicate query strategy for the transition period (UNION/COALESCE patterns)
- UI exposure recommendation: what to show users vs. admin-only
- Recommendation to use PROV-O Starting Point terms only (no Qualified/Extended)

## Verification

- `test -f .gsd/design/PROV-O-ALIGNMENT.md` — file exists
- Doc contains sections: "Current State", "Predicate Audit", "Migration Plan", "UI Exposure", "Recommendations"
- Every predicate from S06-RESEARCH.md audit table appears in the doc
- `wc -l .gsd/design/PROV-O-ALIGNMENT.md` — substantive doc (100+ lines)

## Tasks

- [x] **T01: Write PROV-O alignment design doc** `est:45m`
  - Why: This is the entire deliverable for S06 — a design doc that audits current provenance predicates, maps them to PROV-O, and provides an actionable migration plan for future milestones.
  - Files: `.gsd/design/PROV-O-ALIGNMENT.md`
  - Do: Write the design doc with these sections:
    1. **Current State** — describe the two provenance systems (EventStore + ops log) and three provenance-adjacent subsystems (comments, validation, query history)
    2. **Predicate Audit** — table mapping all 13 `sempkm:` provenance predicates to PROV-O equivalents, migration risk, and recommendation (migrate/keep/N-A)
    3. **Migration Plan** — 4 phases: Phase 0 (complete — ops log uses PROV-O), Phase 1 (new features adopt PROV-O natively), Phase 2 (dual-write compatibility layer for EventStore), Phase 3 (read-side migration with UNION/COALESCE queries)
    4. **Dual-Predicate Query Strategy** — concrete SPARQL patterns for querying mixed-era data (old `sempkm:timestamp` + new `prov:startedAtTime`)
    5. **UI Exposure Recommendation** — what provenance data to surface in workspace (creation time, author attribution) vs. admin-only (full event graphs, ops log)
    6. **Recommendations** — Starting Point terms only, no Qualified/Extended; existing events are immutable; comments/validation low-priority alignment
  - Constraints: Research is complete in S06-RESEARCH.md — synthesize, don't re-investigate. Follow existing design doc format (see VFS-V2-DESIGN.md for convention). No code changes.
  - Verify: `test -f .gsd/design/PROV-O-ALIGNMENT.md && grep -c "##" .gsd/design/PROV-O-ALIGNMENT.md` shows file exists with multiple sections; `grep -c "sempkm:" .gsd/design/PROV-O-ALIGNMENT.md` shows all predicates covered
  - Done when: Design doc exists with all 6 sections, covers all 13 predicates from research, and a reader can determine for any given predicate whether to migrate it, when, and how.

## Observability / Diagnostics

This is a pure documentation slice — no runtime code changes. The design doc itself is the artifact.

- **Inspection surface:** `.gsd/design/PROV-O-ALIGNMENT.md` — the complete design doc; `grep` for any predicate, phase, or recommendation
- **Failure visibility:** Missing predicates or sections are detectable via the verification grep checks below
- **No runtime signals:** No services, endpoints, or logs are added or modified by this slice

## Verification

- `test -f .gsd/design/PROV-O-ALIGNMENT.md` — file exists
- Doc contains sections: "Current State", "Predicate Audit", "Migration Plan", "UI Exposure", "Recommendations"
- Every predicate from S06-RESEARCH.md audit table appears in the doc
- `wc -l .gsd/design/PROV-O-ALIGNMENT.md` — substantive doc (100+ lines)
- `grep -c "sempkm:" .gsd/design/PROV-O-ALIGNMENT.md` — all predicates referenced (10+ occurrences confirms coverage)

## Files Likely Touched

- `.gsd/design/PROV-O-ALIGNMENT.md`
