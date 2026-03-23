---
depends_on: [M034]
---

# M040: Cleanup — Documentation, UI Fixes & Bug Squashing

**Gathered:** 2026-03-23
**Status:** Queued

## Project Description

A catch-all milestone for accumulated documentation gaps, UI polish issues, and bugs discovered during review. Starts with the M034 user guide documentation gap — 7 user-visible features shipped without any guide chapters — and will grow as issues are identified during app review.

## Why This Milestone

M034 delivered 10 validated requirements across 5 slices with 99 unit tests and 8 E2E tests. The validation process flagged that zero user guide chapters were written for any of the new features. That gap was noted in the M034 summary's cross-slice verification table (❌ on "User guide docs for new features") but was never turned into a remediation slice or forward commitment. The observation died in a markdown table.

This is a process failure: validation findings that don't produce actionable follow-up are worse than not flagging at all — they create the illusion of rigor while debt accumulates silently. This milestone exists to close that loop and provide a home for similar cleanup items going forward.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Read documentation for all M034 planning features: editable calendar, timeline/Gantt, recurring tasks, task templates, review workflows, cross-view drag, composable planning
- Find these features in the existing guide chapter structure (chapter 7 expansion or new chapters)
- (Future slices) encounter fewer UI bugs and polish issues across the app

### Entry point / environment

- Docs: `docs/guide/` directory, served at the documentation site
- Environment: Standard dev environment for docs authoring

## Completion Class

- Contract complete means: every M034 user-visible feature has a corresponding guide section with usage instructions
- Integration complete means: new guide sections reference correct UI paths, keyboard shortcuts, and cross-link to related chapters
- Operational complete means: a new user can read the docs and successfully use calendar editing, timeline view, recurring tasks, templates, and review workflows without guessing

## Scope

### In Scope

- **S01:** User guide documentation for M034 features (calendar editing, timeline/Gantt, recurring tasks, task templates, review workflows, cross-view drag, composable planning)
- **Future slices:** UI issues, bugs, and polish items as discovered during app review

### Out of Scope / Non-Goals

- New feature development
- Architectural changes
- Performance optimization (unless it's a bug fix)

## Open Questions

- Should M034 features be added to chapter 7 (Browsing and Visualizing) or get their own dedicated chapters? Chapter 7 currently covers table/card/graph/kanban but not calendar or timeline. Task templates and review workflows may fit better in chapter 28 (Dashboards and Workflows) or new chapters.
