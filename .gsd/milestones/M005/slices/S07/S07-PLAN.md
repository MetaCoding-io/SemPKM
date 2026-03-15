# S07: Views Rethink Design

**Goal:** Produce a design document at `.gsd/design/VIEWS-RETHINK.md` that proposes a concrete, implementable-in-one-milestone plan for generic cross-type views, query-scoped view binding, and explorer tree consolidation — grounded in existing code patterns and informed by the S01 query-as-RDF foundation.

**Demo:** `.gsd/design/VIEWS-RETHINK.md` exists with current state audit, proposed data model, explorer tree redesign, type-scoped carousel integration, migration path, and phased implementation plan.

## Must-Haves

- Current state audit showing the scaling problem (31+ ViewSpecs across 2 models, per-type explorer tree explosion)
- Proposed data model for generic system-provided views (Table/Cards/Graph) with SHACL-driven column discovery
- Explorer tree redesign: from 31+ entries → ~7 fixed + Saved Views folder
- Type-specific model views presented via carousel tabs (existing mechanism), not separate explorer entries
- Saved query → view scope binding design using `sempkm:scopeQuery` linking
- Migration path: phased, backward-compatible, no big-bang switchover
- Open questions and deferred scope clearly called out

## Verification

- `test -f .gsd/design/VIEWS-RETHINK.md` — file exists
- `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` returns ≥ 6 (Current State, Proposed Data Model, Explorer Tree Redesign, Migration Plan, UI Exposure, Recommendations/Open Questions)
- Document references real code paths (ViewSpecService, ShapesService, carousel_tab_bar.html) not hypothetical abstractions

## Tasks

- [x] **T01: Write Views Rethink design document** `est:1h`
  - Why: This is the sole deliverable of S07 — a design doc following the PROV-O alignment doc format, grounded in S07-RESEARCH.md findings and existing codebase patterns
  - Files: `.gsd/design/VIEWS-RETHINK.md`
  - Do: Write the design doc covering: (1) current state audit of ViewSpec scaling problem with concrete numbers, (2) proposed generic views data model using SHACL column discovery, (3) explorer tree redesign from 31+ entries to ~7, (4) type-scoped model views via existing carousel tab bar, (5) saved query scope binding via sempkm:scopeQuery, (6) phased migration plan, (7) open questions. Follow the PROV-O alignment doc format (status header, sections with tables, code examples, recommendations). Reference real files and extension points from S07-RESEARCH.md.
  - Verify: File exists with ≥6 H2 sections; references ViewSpecService, ShapesService, carousel_tab_bar.html, and QueryService
  - Done when: Design doc is complete, internally consistent, and covers all must-haves

## Observability / Diagnostics

This is a design-document-only slice — no runtime code changes. Observability is limited to artifact inspection:

- **Design doc exists and is well-formed:** `test -f .gsd/design/VIEWS-RETHINK.md && grep -c "^##" .gsd/design/VIEWS-RETHINK.md`
- **Code path references are valid:** `grep -c "ViewSpecService\|ShapesService\|carousel_tab_bar\|QueryService" .gsd/design/VIEWS-RETHINK.md` returns ≥ 4
- **Failure state:** If the design doc references code paths that no longer exist (e.g., after refactoring), `grep` against the actual codebase will reveal stale references: `for term in ViewSpecService ShapesService carousel_tab_bar QueryService; do echo "$term: $(rg -l "$term" backend/ frontend/ | wc -l) files"; done`

## Verification

- `test -f .gsd/design/VIEWS-RETHINK.md` — file exists
- `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` returns ≥ 6 (Current State, Proposed Data Model, Explorer Tree Redesign, Migration Plan, UI Exposure, Recommendations/Open Questions)
- Document references real code paths (ViewSpecService, ShapesService, carousel_tab_bar.html) not hypothetical abstractions
- **Diagnostic check:** `for term in ViewSpecService ShapesService carousel_tab_bar QueryService; do echo "$term: $(rg -l "$term" backend/ frontend/ | wc -l) files"; done` — all terms found in ≥1 file (confirms references are to real code, not hypothetical)

## Files Likely Touched

- `.gsd/design/VIEWS-RETHINK.md`
