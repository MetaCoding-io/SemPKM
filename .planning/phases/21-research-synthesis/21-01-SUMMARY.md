---
phase: 21-research-synthesis
plan: 01
subsystem: planning
tags: [architecture, decisions, planning, v2.2, LuceneSail, yasgui, wsgidav, dockview-core]

# Dependency graph
requires:
  - phase: 20-architecture-decision-commit
    provides: "4 RESEARCH.md files with committed decisions and v2.2 Handoff sections"
provides:
  - "DECISIONS.md: consolidated architectural decision record for all 4 v2.2/v2.3 decisions"
  - "v2.2 Phase Structure: 5 phases (23-27) with sequencing rationale"
  - "Cross-cutting concerns documented: auth scoping, SPARQL query patterns, CSS token usage, dependency footprint"
  - "Tech debt schedule: completed in v2.1, remaining items, deferred to v2.3+"
  - "Implementation readiness checklist for pre-v2.2 verification"
affects:
  - v2.2 implementation planning phases
  - Phase 23 SPARQL Console implementation
  - Phase 24 FTS Keyword Search implementation
  - Phase 25 CSS Token Expansion
  - Phase 26-27 VFS implementation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Consolidated ADR (Architectural Decision Record) pattern: single DECISIONS.md synthesizing multiple RESEARCH.md files"
    - "v2.2 phase sequencing based on prerequisite analysis across 4 independent decisions"

key-files:
  created:
    - ".planning/DECISIONS.md"
  modified: []

key-decisions:
  - "v2.2 Phase 23 (SPARQL Console) ships first — zero prerequisites, highest ROI/effort ratio"
  - "v2.2 Phase 24 (FTS/LuceneSail) requires infrastructure verification before code is written (JAR check, Turtle config validation)"
  - "v2.2 Phase 25 (CSS Token Expansion) is independent preparatory work for v2.3 Dockview migration"
  - "v2.2 Phases 26-27 (VFS) split read-only MVP (Phase 26) from auth+write (Phase 27) to bound risk"
  - "Dockview Phase A deferred to v2.3 Phase 1 — CSS token expansion is the only UI Shell work in v2.2"
  - "SyncTriplestoreClient (sync httpx.Client) is a required new component for wsgidav WSGI thread pool"
  - "API token auth (Basic auth with revocable token as password) must be designed before Phase 27 but not Phase 26"

requirements-completed:
  - SYN-01

# Metrics
duration: 3min
completed: 2026-02-28
---

# Phase 21 Plan 01: Research Synthesis Summary

**Consolidated DECISIONS.md synthesizing all 4 committed decisions (LuceneSail/yasgui/wsgidav/dockview-core) into a single v2.2 architectural reference with phase structure, cross-cutting concerns, and tech debt schedule**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-28T02:59:38Z
- **Completed:** 2026-02-28T03:02:38Z
- **Tasks:** 2 (both executed atomically in a single write)
- **Files modified:** 1

## Accomplishments

- Created `.planning/DECISIONS.md` (281 lines, 28KB) — the definitive v2.2 architecture reference
- Documented all 4 decisions with rationale, explicit rejections, prerequisites, and first implementation steps
- Identified 5 cross-cutting concerns that span the 4 decisions (auth scoping, SPARQL patterns, CSS tokens, dependency footprint, incremental delivery)
- Derived a concrete v2.2 phase structure (Phases 23-27) with per-phase sequencing rationale based on prerequisite analysis from the 4 Handoff sections
- Mapped all known tech debt items to target milestones (v2.1 completed, remaining, deferred to v2.3+)
- Produced an implementation readiness checklist (6 items) that must be verified before v2.2 development begins

## Task Commits

Each task was committed atomically:

1. **Task 1: Write DECISIONS.md — Decision Summary and Cross-Cutting Concerns** - `e33703d` (feat)
   - Task 2 content (v2.2 Phase Structure and Tech Debt Schedule) was included in the same write since both tasks produced a single coherent document; no separate commit needed

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `.planning/DECISIONS.md` — Consolidated architectural decision record: Decision Summary table, Decision Details for all 4 decisions, Cross-Cutting Concerns, v2.2 Phase Structure (Phases 23-27), Tech Debt Schedule, Implementation Readiness Checklist

## Decisions Made

- Phases 23-27 sequencing derived from prerequisite analysis: SPARQL Console first (no deps), FTS second (needs JAR verification), CSS tokens third (independent prep work), VFS read-only fourth (needs SyncTriplestoreClient), VFS auth+settings fifth (needs Phase 26 validated)
- Dockview Phase A explicitly deferred to v2.3 Phase 1; CSS token expansion is the only UI Shell work in v2.2
- SyncTriplestoreClient identified as a required new component — DAVProvider in WSGI thread pool cannot use async httpx client
- API token auth (Basic auth with revocable token) is a new auth mechanism that must be designed before VFS write support but not before read-only MVP

## Deviations from Plan

None - plan executed exactly as written. Both tasks were written in a single atomic operation since they produce a single document; the plan's "append" instruction for Task 2 was fulfilled by writing a complete document covering all required sections.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. DECISIONS.md is a planning artifact; no application changes were made.

## Next Phase Readiness

- Phase 21 complete — SYN-01 requirement satisfied
- DECISIONS.md is the v2.2 implementation reference; v2.2 planning can begin from this document
- Recommended next action: run `/gsd:plan-phase 22` (already complete per STATE.md) or begin v2.2 planning based on Phase 23-27 structure in DECISIONS.md
- Six implementation readiness checklist items should be verified before v2.2 development starts (LuceneSail JAR, Turtle config, Yasgui CDN, wsgidav PyPI, CSS token count, dockview-core bundle size)

## Self-Check: PASSED

- [x] `.planning/DECISIONS.md` exists (28,552 bytes, 281 lines)
- [x] Commit `e33703d` exists in git log
- [x] All must_haves verified: Decision Summary table, 4 decision detail sections, cross-cutting concerns, v2.2 phase structure, tech debt schedule, implementation readiness checklist
- [x] Key links verified: RESEARCH.md references present in Decision Summary table rows (5 RESEARCH.md references found)
- [x] SYN-01 requirement marked complete in REQUIREMENTS.md
- [x] Phase 21 marked complete in ROADMAP.md

---
*Phase: 21-research-synthesis*
*Completed: 2026-02-28*
