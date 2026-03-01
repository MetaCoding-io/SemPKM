---
gsd_state_version: 1.0
milestone: v2.3
milestone_name: Shell, Navigation & Views
status: roadmap_ready
last_updated: "2026-03-01T00:00:00.000Z"
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.
**Current focus:** v2.3 Shell, Navigation & Views — Phase 29 ready to plan

## Current Position

Phase: 29 of 34 (FTS Fuzzy Search)
Plan: —
Status: Ready to plan
Last activity: 2026-03-01 — v2.3 roadmap created (Phases 29-34)

Progress: [░░░░░░░░░░] 0% (0/6 phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (v2.3)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*

## Accumulated Context

### Key Decisions

Full decision log in PROJECT.md Key Decisions table. v2.3 decisions TBD.

- DEC-04: dockview-core 4.11.0 replaces Split.js for editor-pane area (Phase A only); CSS bridge file already in place from v2.2
- Research: LuceneSail `term~1` fuzzy syntax confirmed HIGH confidence; 5-char length threshold to avoid short-token noise

### Pending Todos

1. Add edit form helptext property to SHACL types (ui) — carried from v2.0

### Known Tech Debt

- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code
- E2E tests for SPARQL/FTS/VFS use test.skip() graceful degradation — resolved in Phase 34

### Blockers/Concerns

- Carousel bar + 3D flip toggle visual coexistence in object view header unresolved — prototype before committing VIEW-02 implementation (Phase 32)
- Named layout user preference storage in triplestore is a first-use pattern — validate SPARQL UPDATE design before LayoutService (Phase 33)

## Session Continuity

Last session: 2026-03-01
Stopped at: Roadmap created — ready to plan Phase 29 (FTS Fuzzy Search)
Resume file: None
