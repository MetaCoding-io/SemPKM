---
phase: 20-architecture-decision-commit
plan: 01
subsystem: planning
tags: [rdf4j, lucene, fts, vector-search, pgvector, sentence-transformers, architecture]

# Dependency graph
requires: []
provides:
  - Committed architectural decision: RDF4J LuceneSail for keyword FTS (Phase 20a)
  - Deferred decision: pgvector + sentence-transformers for semantic search (Phase 20b)
  - v2.2 Handoff section with concrete prerequisites and first implementation steps
affects: [phase-21-synthesis, phase-22-vfs, DEC-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Architecture decision documented inline in RESEARCH.md (Decision section + Handoff section)"

key-files:
  created: []
  modified:
    - .planning/research/phase-20-fts-vector/RESEARCH.md

key-decisions:
  - "LuceneSail chosen for FTS: zero new containers, zero sync infra, SPARQL-native integration, ships with RDF4J 5.0.1"
  - "OpenSearch/Jena/Oxigraph/GraphDB all explicitly ruled out with specific rationale"
  - "pgvector + sentence-transformers deferred to Phase 20b (blocked on PostgreSQL migration)"

patterns-established:
  - "Decision section at top of RESEARCH.md: one-sentence commitment + rationale + alternatives ruled out"
  - "v2.2 Handoff at bottom of RESEARCH.md: prerequisites + ordered first steps"

requirements-completed: [DEC-01]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 20 Plan 01: FTS/Vector Architecture Decision Summary

**RDF4J LuceneSail committed as keyword FTS approach for v2.2; pgvector semantic search deferred to Phase 20b pending PostgreSQL migration**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T02:28:45Z
- **Completed:** 2026-03-01T02:30:10Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added `## Decision` section at the top of RESEARCH.md with a binding one-sentence commitment to LuceneSail, five rationale bullet points, and five "Alternatives ruled out" entries covering OpenSearch, Jena, Oxigraph, GraphDB, and SQLite FTS5
- Added `## v2.2 Handoff` section at the bottom of RESEARCH.md with three validation prerequisites (JAR presence, Turtle config syntax, FROM clause scoping) and six ordered Phase 20a first steps
- RESEARCH.md is now a complete architectural commitment document: a reviewer reading only this file knows what was chosen, why, what was rejected, and exactly how to start implementation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Decision section to FTS/Vector RESEARCH.md** - `5349517` (feat)
2. **Task 2: Add v2.2 Handoff section to FTS/Vector RESEARCH.md** - `ce8755f` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `.planning/research/phase-20-fts-vector/RESEARCH.md` - Added Decision section (lines 1-20) and v2.2 Handoff section (lines 857-895); original 834 lines of research content unchanged

## Decisions Made
- LuceneSail is the committed FTS approach: wraps NativeStore at SAIL layer, zero new infrastructure, SPARQL-native, ships with RDF4J distribution; PKM-scale datasets are well within its ~100K object limit
- pgvector semantic search deliberately deferred to Phase 20b — blocked on PostgreSQL migration; asyncpg dependency already in pyproject.toml signals this migration is planned
- Three highest-priority implementation prerequisites documented: (1) verify LuceneSail JAR in Docker image, (2) validate Turtle config syntax for RDF4J 5.x unified namespace, (3) validate FROM clause graph scoping

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- DEC-01 requirement satisfied: FTS/vector decision committed with full rationale and implementation handoff
- Phase 21 (Research Synthesis) can now consume this decision for DECISIONS.md synthesis
- Phase 20a implementation can begin immediately with the three prerequisites checklist from the Handoff section
- No blockers for next plan in Phase 20

---
*Phase: 20-architecture-decision-commit*
*Completed: 2026-03-01*

## Self-Check: PASSED

- FOUND: `.planning/research/phase-20-fts-vector/RESEARCH.md`
- FOUND: `.planning/phases/20-architecture-decision-commit/20-01-SUMMARY.md`
- FOUND commit: `5349517` (feat: Decision section)
- FOUND commit: `ce8755f` (feat: v2.2 Handoff section)
