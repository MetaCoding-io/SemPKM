---
phase: 20-architecture-decision-commit
plan: 04
subsystem: ui
tags: [dockview, split.js, css-tokens, panel-management, htmx, workspace]

# Dependency graph
requires:
  - phase: 20-architecture-decision-commit
    provides: Research completed for UI Shell panel management (Phase 23 RESEARCH.md)
provides:
  - Committed architectural decision: dockview-core over GoldenLayout for panel management
  - Incremental Split.js migration plan (Phase A/B/C) documented
  - CSS token expansion plan (40->91 tokens, two-tier architecture) committed
  - v2.2 Handoff section with prerequisites and Phase A implementation steps
affects: [21-research-synthesis, 23-ui-shell-implementation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Decision section pattern: ## Decision at top of RESEARCH.md, one-sentence choice + rationale + alternatives ruled out"
    - "v2.2 Handoff pattern: implementation prerequisites + phase steps + deferred work — binding commitment for next milestone"

key-files:
  created: []
  modified:
    - .planning/research/phase-23-ui-shell/RESEARCH.md

key-decisions:
  - "dockview-core chosen over GoldenLayout 2: DOM reparenting in GoldenLayout breaks htmx handlers; dockview-core has zero deps, vanilla TS support, CSS custom property theming"
  - "Incremental Split.js migration: Phase A (inner editor split) -> Phase B (full workspace) -> Phase C (floating panels) — Phase A in v2.3, B and C deferred"
  - "CSS token expansion (40->91 tokens) is v2.2-eligible preparatory work independent of Dockview migration"
  - "Bundle size measurement deferred as prerequisite: must check Bundlephobia before CDN vs vendor decision"

patterns-established:
  - "Decision annotation pattern: prepend ## Decision above existing H1 title with one-liner, rationale bullets, and alternatives ruled out"
  - "Handoff annotation pattern: append ## vX.Y Handoff with prerequisites, first steps, and deferred work sections"

requirements-completed: [DEC-04]

# Metrics
duration: 2min
completed: 2026-03-01
---

# Phase 20 Plan 04: UI Shell Architecture Decision Summary

**Committed dockview-core over GoldenLayout as panel manager, with incremental Split.js migration plan and CSS token expansion roadmap documented in RESEARCH.md**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-01T02:44:34Z
- **Completed:** 2026-03-01T02:46:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Prepended `## Decision` section to UI Shell RESEARCH.md committing dockview-core with full rationale and five alternatives ruled out (GoldenLayout, Lumino, FlexLayout-React, rc-dock, Keep Split.js)
- Appended `## v2.2 Handoff` section with 4 prerequisites before implementation, Phase A first steps, Phase B deferral, and CSS token expansion plan that can begin in v2.2
- File now self-contained: a reviewer reading only RESEARCH.md can determine chosen approach, rationale, rejections, and implementation starting point without reading any other file

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Decision section to UI Shell RESEARCH.md** - `02bd3d7` (docs)
2. **Task 2: Add v2.2 Handoff section to UI Shell RESEARCH.md** - `1202bd3` (docs)

**Plan metadata:** (included in final commit)

## Files Created/Modified
- `.planning/research/phase-23-ui-shell/RESEARCH.md` - Prepended Decision section + appended v2.2 Handoff section

## Decisions Made
- dockview-core chosen over GoldenLayout 2: primary rejection reason is DOM reparenting breaking htmx event handlers; secondary reasons are LESS-based themes (vs CSS custom properties), no floating panels, and sporadic maintenance
- Split.js migration is incremental (Phase A/B/C), not a single replacement — Phase A (inner editor-pane split) validates htmx integration before committing to full workspace migration
- CSS token expansion (from ~40 to ~91 tokens using two-tier primitive + semantic architecture) can proceed in v2.2 independently of Dockview migration
- Bundle size measurement is a prerequisite before deciding CDN vs vendor loading for dockview-core

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 4 DEC requirements (DEC-01 through DEC-04) are now committed across Phase 20 plans 01-04
- Phase 21 Research Synthesis (SYN-01) can now proceed — all four RESEARCH.md files have Decision sections
- Phase 21 will produce DECISIONS.md consolidating all four architectural commitments into v2.2 guidance

---
*Phase: 20-architecture-decision-commit*
*Completed: 2026-03-01*
