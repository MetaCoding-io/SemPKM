# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-23)

**Core value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations -- no blank-page syndrome, no schema setup.
**Current focus:** v2.0 Tighten Web UI -- Phase 12: Sidebar and Navigation

## Current Position

Phase: 12 of 18 (Sidebar and Navigation)
Plan: Not yet planned
Status: Phase 11 complete, ready for Phase 12
Last activity: 2026-02-23 -- Completed Phase 11 (read-only object view with mode toggle, body unification, polish)

Progress: [###░░░░░░░] 26% (v2.0) -- 11-02 complete (5/23 plans)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 26
- Total execution time: across 9 phases
- v2.0 estimated plans: ~23

**v2.0 Metrics:**

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 10    | 01   | 2min     | 2     | 3     |
| 10    | 03   | 2min     | 2     | 6     |
| 11    | 01   | 4min     | 2     | 7     |
| 11    | 02   | session  | 15    | 12    |

## Accumulated Context

### Key Decisions

All v1.0 decisions logged in PROJECT.md Key Decisions table.

v2.0 roadmap decisions:
- Phase 10 includes editor group data model DESIGN (not implementation) to prevent Split.js pitfall (Pitfall 1 from research)
- Driver.js replaces Shepherd.js (MIT vs AGPL-3.0 licensing issue)
- WORK-06 (rounded tabs) grouped with Phase 13 (dark mode/visual polish) since both are CSS styling
- ERR-01 (styled 403) grouped with Phase 13 (visual polish) since it is a template/styling task
- Settings system (Phase 15) placed after dark mode (Phase 13) -- dark mode uses CSS-only approach first, migrates to settings consumer later
- (10-01) Promise.race with 3s timeout replaces setInterval polling for editor loading -- deterministic failure time
- (10-01) Skeleton loading uses CSS-only shimmer animation (no JS animation dependency)
- (10-02) position: fixed + getBoundingClientRect for dropdown overflow escape rather than removing overflow-y: auto from form sections
- (10-03) Cleanup registry uses element IDs as keys with arrays of teardown functions; htmx:beforeCleanupElement walks descendants
- (10-03) Split.js instances tracked globally in window._sempkmSplits with destroy-before-recreate guard
- (11-01) Multi-valued properties stored as dict[str, list[str]] -- backward compatible with existing edit form templates
- (11-01) Edit mode initialization deferred via _initEditMode_ function to prevent CodeMirror/Split.js waste on read-only views
- (11-01) CDN-loaded marked.js + highlight.js + DOMPurify for client-side Markdown rendering (no server-side dependency)
- (11-01) Reference tooltips show "TypeLabel: ObjectLabel" format derived from SHACL sh:class target_class
- (11-02) JS setTimeout at animation midpoint for face visibility swap (CSS backface-visibility unreliable in complex DOM)
- (11-02) Body predicate unification: detect SHACL Body property by name, use model-specific path for save
- (11-02) dcterms:created/modified excluded from edit form, modified auto-updated on save
- (11-02) Lazy-loaded ref-pill popovers reuse graph-popover CSS for visual consistency

### Pending Todos

1. Add edit form helptext property to SHACL types (ui)

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
Stopped at: Completed Phase 11 (all plans verified and committed)
Resume: Plan and execute Phase 12 (Sidebar and Navigation)
