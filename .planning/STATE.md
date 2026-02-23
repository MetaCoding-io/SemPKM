# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations -- no blank-page syndrome, no schema setup.
**Current focus:** v2.0 Tighten Web UI -- Phase 10: Bug Fixes and Cleanup Architecture

## Current Position

Phase: 10 of 18 (Bug Fixes and Cleanup Architecture)
Plan: 2 of 3 in current phase
Status: Executing
Last activity: 2026-02-23 -- Completed 10-02 (autocomplete dropdown and views explorer fixes)

Progress: [░░░░░░░░░░] 0% (v2.0)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 26
- Total execution time: across 9 phases
- v2.0 estimated plans: ~23

**v2.0 tracking starts on first plan execution.**

## Accumulated Context

### Key Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table.

v2.0 roadmap decisions:
- Phase 10 includes editor group data model DESIGN (not implementation) to prevent Split.js pitfall (Pitfall 1 from research)
- Driver.js replaces Shepherd.js (MIT vs AGPL-3.0 licensing issue)
- WORK-06 (rounded tabs) grouped with Phase 13 (dark mode/visual polish) since both are CSS styling
- ERR-01 (styled 403) grouped with Phase 13 (visual polish) since it is a template/styling task
- Settings system (Phase 15) placed after dark mode (Phase 13) -- dark mode uses CSS-only approach first, migrates to settings consumer later
- (10-02) position: fixed + getBoundingClientRect for dropdown overflow escape rather than removing overflow-y: auto from form sections

### Pending Todos

None yet.

### Known Tech Debt (from v1.0)

- Cookie secure=False (needs production config)
- SMTP deferred (magic link tokens logged to console)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code

### Blockers/Concerns

- Split.js has no dynamic pane API -- editor group data model must be designed before read-only view changes `#editor-area` targeting (addressed: Phase 10 plan 10-03 designs the model, Phase 14 implements)
- Shepherd.js v14 is AGPL-3.0 -- using Driver.js (MIT) instead (addressed in REQUIREMENTS.md)

## Session Continuity

Last session: 2026-02-23
Stopped at: Completed 10-02-PLAN.md
Resume: `/gsd:execute-phase 10` (plan 03 next)
