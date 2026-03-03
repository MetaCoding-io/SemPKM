---
phase: quick-21
plan: 01
subsystem: ui
tags: [obsidian, import-wizard, openrefine, htmx, sse, fuzzy-matching, shacl]

requires:
  - phase: none
    provides: standalone research document
provides:
  - "Complete UX/UI flow design for interactive Obsidian import wizard"
  - "Fuzzy matching algorithm spec for frontmatter-to-SHACL property mapping"
  - "SQLAlchemy data model for import jobs"
  - "API endpoint design for wizard backend"
affects: [obsidian-onboarding, import-wizard-implementation]

tech-stack:
  added: [jellyfish (recommended for Jaro-Winkler)]
  patterns: [OpenRefine-style reconciliation, SSE progress streaming, type-level property mapping]

key-files:
  created:
    - .planning/research/obsidian-import-wizard-ux.md

key-decisions:
  - "SQLAlchemy models over in-memory session for import job persistence (resumable, auditable)"
  - "Jaro-Winkler + token overlap for fuzzy property matching (better than Levenshtein for short strings)"
  - "Type-level property mappings (not per-file) following OpenRefine reconciliation pattern"
  - "SSE for import progress streaming (htmx sse extension compatible)"
  - "3-phase implementation priority: MVP wizard -> property/relationship mapping -> advanced features"

patterns-established:
  - "Import wizard: server-side state with htmx partial page loads per step"
  - "Fuzzy matching: multi-signal scoring (exact local name, Jaro-Winkler on label, Jaccard token overlap)"

requirements-completed: [QUICK-21]

duration: 5min
completed: 2026-03-03
---

# Quick Task 21: Obsidian Import Wizard UX Flow Design Summary

**OpenRefine-style interactive import wizard with 6-step flow, fuzzy property matching, and htmx-compatible UI design for replacing Chapter 24 external scripts**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T04:22:44Z
- **Completed:** 2026-03-03T04:28:00Z
- **Tasks:** 1
- **Files created:** 1

## Accomplishments
- Designed complete 6-step wizard flow: Scan, Type Mapping, Property Mapping, Relationship Mapping, Preview, Import
- Specified OpenRefine-style type reconciliation with folder-based bulk assign, glob patterns, and individual file assignment
- Designed fuzzy matching algorithm using Jaro-Winkler + token overlap for auto-suggesting SHACL property mappings
- Defined SQLAlchemy data model (ImportJob, ImportFileMapping, ImportPropertyMapping, ImportEdgeMapping)
- Mapped all wizard steps to existing backend services (ShapesService, Command API, SearchService)
- Created ASCII wireframes for all 6 wizard screens
- Specified htmx integration patterns (partial page loads, SSE progress streaming)
- Proposed 3-phase implementation priority (MVP -> full mapping -> advanced features)

## Task Commits

1. **Task 1: Design the interactive Obsidian import wizard UX flow** - `dbbaeb4` (docs)

## Files Created/Modified
- `.planning/research/obsidian-import-wizard-ux.md` - Complete UX/UI flow design document (1102 lines)

## Decisions Made
- SQLAlchemy models chosen over in-memory session state for import job persistence: enables resume-after-crash, import history, and future undo/rollback
- Jaro-Winkler similarity chosen over Levenshtein for fuzzy matching: better discrimination for short token strings (5-15 chars), prefix bonus helps with common property name patterns
- Type-level property mappings (not per-file): follows OpenRefine's column reconciliation pattern where mapping "status" to "bpkm:status" for Note type applies to all Note files
- Server-Sent Events for import progress: htmx has built-in SSE extension support, avoids WebSocket complexity
- 3-phase implementation: Phase 1 (scan, type mapping, preview, import) delivers value without property mapping complexity

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Research document complete and ready to serve as specification for future implementation milestone
- All backend integration points identified with specific service methods and API patterns
- Data model ready for Alembic migration generation when implementation begins

---
*Quick Task: 21-research-ux-ui-flow-for-interactive-obsi*
*Completed: 2026-03-03*
