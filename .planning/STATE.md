---
gsd_state_version: 1.0
milestone: v2.2
milestone_name: Data Discovery
status: roadmap_ready
last_updated: "2026-02-28"
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.
**Current focus:** v2.2 Data Discovery — Phase 23: SPARQL Console (ready to plan)

## Current Position

Phase: 23 of 28 (SPARQL Console)
Plan: Not started
Status: Ready to plan
Last activity: 2026-02-28 — v2.2 roadmap created (Phases 23-28)

Progress: [░░░░░░░░░░] 0%

## v2.2 Phase Structure

| Phase | Name | Requirements | Depends On | Status |
|-------|------|--------------|------------|--------|
| 23 | SPARQL Console | SPARQL-01, SPARQL-02, SPARQL-03 | Nothing | Not started |
| 24 | FTS Keyword Search | FTS-01, FTS-02, FTS-03 | Nothing (JAR prereq) | Not started |
| 25 | CSS Token Expansion | — (v2.3 prep) | Nothing | Not started |
| 26 | VFS MVP Read-Only | VFS-01, VFS-02 | Nothing (self-contained) | Not started |
| 27 | VFS Write + Auth | VFS-03 | Phase 26 | Not started |
| 28 | UI Polish + Integration Testing | POLSH-01, POLSH-02, POLSH-03, POLSH-04 | Phases 23, 24, 26 | Not started |

## Accumulated Context

### Key Decisions

All v2.2 architectural decisions committed in v2.1. See .planning/DECISIONS.md for full rationale.

- DEC-01: RDF4J LuceneSail for FTS — zero new containers, SPARQL-native, ships with RDF4J 5.0.1
- DEC-02: @zazuko/yasgui v4.5.0 CDN for SPARQL Console — MIT, zero backend changes
- DEC-03: wsgidav + a2wsgi for VFS — HTTP-only, Docker-compatible, no SYS_ADMIN required
- DEC-04: dockview-core for UI shell — Phase A in v2.3; CSS token expansion (~40 to ~91) is v2.2 prep only

### Pending Todos

1. Add edit form helptext property to SHACL types (ui) — carried from v2.0
2. Verify LuceneSail JAR in Docker image before Phase 24 begins

### Known Tech Debt

- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- empty_shapes_loader dead code
- Bottom panel SPARQL tab is placeholder stub — Phase 23 replaces it

### Blockers/Concerns

- Phase 24 prerequisite: LuceneSail JAR must be verified in Docker image first; if absent, Dockerfile extension required before SearchService code
- Phase 27 prerequisite: API token auth design must be complete before write path work begins

## Session Continuity

Last session: 2026-02-28
Stopped at: v2.2 roadmap created — Phases 23-28 defined with full success criteria
Resume: Run /gsd:plan-phase 23 to begin SPARQL Console implementation
