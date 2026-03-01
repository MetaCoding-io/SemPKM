---
gsd_state_version: 1.0
milestone: v2.3
milestone_name: Shell, Navigation & Views
status: defining_requirements
last_updated: "2026-03-01T00:00:00.000Z"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.
**Current focus:** v2.3 Shell, Navigation & Views — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-01 — Milestone v2.3 started

## Accumulated Context

### Key Decisions

v2.2 decisions archived to PROJECT.md Key Decisions table. v2.3 decisions TBD.

### Pending Todos

1. Add edit form helptext property to SHACL types (ui) — carried from v2.0

### Known Tech Debt

- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code
- E2E tests for SPARQL/FTS/VFS use test.skip() graceful degradation pending live service validation

### Blockers/Concerns

- None
