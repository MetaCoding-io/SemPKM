---
estimated_steps: 7
estimated_files: 1
---

# T01: Write Views Rethink Design Document

**Slice:** S07 — Views Rethink Design
**Milestone:** M005

## Description

Write the views rethink design document at `.gsd/design/VIEWS-RETHINK.md`. This doc proposes a concrete, implementable-in-one-milestone redesign of how views are accessed and organized — shifting from 31+ per-type explorer entries to generic cross-type views with SHACL-driven columns, query-scoped view binding, and carousel-based type-specific rendering.

The document follows the PROV-O alignment doc format: status header, current state audit, proposed changes, migration plan, recommendations. All proposals must reference real code extension points identified in S07-RESEARCH.md.

## Steps

1. Write the status header and summary (same format as PROV-O-ALIGNMENT.md: Status, Date, Scope)
2. Write Current State section: audit ViewSpec scaling (31 entries from 2 models, 3 renderers × N types), show how views_explorer.html groups them, reference basic-pkm.jsonld (12 specs) and ppv.jsonld (19 specs). Include the existing VIEWS / MY VIEWS sidebar split.
3. Write Proposed Data Model section: define generic system-provided views (Table/Cards/Graph with `sempkm:isGeneric true`), SHACL column discovery via ShapesService._extract_node_shape(), `sempkm:scopeQuery` predicate linking views to saved queries by IRI. Include RDF vocabulary additions as Turtle examples.
4. Write Explorer Tree Redesign section: propose the consolidated tree (~7 fixed entries + Saved Views folder), show how type-specific model views move to carousel tabs when a type is selected within a generic view. Reference carousel_tab_bar.html + switchCarouselView() as the existing mechanism. Describe type filter pills for generic views (replacing carousel which assumes single target_class).
5. Write Migration Plan section: phase 1 (generic views as new explorer entries alongside existing per-type tree), phase 2 (consolidate explorer tree, move per-type entries to carousel), phase 3 (cleanup). Emphasize backward compatibility — no breaking existing views.
6. Write Open Questions / Deferred Scope section: generic graph view performance limits, user-created types with sparse SHACL, UX for query→view scope binding, duplicate route cleanup in views/router.py.
7. Write Recommendations section: summarize key decisions, reference the hybrid approach (D020-style existing patterns + new generic layer), note what's implementable in one milestone vs. deferred.

## Must-Haves

- [ ] File exists at `.gsd/design/VIEWS-RETHINK.md`
- [ ] Current state audit with concrete ViewSpec counts (12 basic-pkm + 19 ppv = 31)
- [ ] Generic views proposal with SHACL column discovery mechanism
- [ ] Explorer tree redesign showing before/after structure
- [ ] Query scope binding via `sempkm:scopeQuery` predicate
- [ ] Phased migration plan (no big-bang)
- [ ] Open questions section
- [ ] References real code paths: ViewSpecService, ShapesService, carousel_tab_bar.html, QueryService

## Verification

- `test -f .gsd/design/VIEWS-RETHINK.md` succeeds
- `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` returns ≥ 6
- Document mentions ViewSpecService, ShapesService, carousel_tab_bar.html, and QueryService by name
- Document includes Turtle examples for proposed RDF vocabulary

## Inputs

- `.gsd/milestones/M005/slices/S07/S07-RESEARCH.md` — full codebase analysis, constraints, data model notes, proposed explorer tree structure
- `.gsd/design/PROV-O-ALIGNMENT.md` — format reference (status header, sections with tables, code examples, recommendations)
- `.gsd/milestones/M005/slices/S01/S01-SUMMARY.md` — QueryService API, query IRI patterns, `sempkm:source` for model queries
- `.gsd/DECISIONS.md` — relevant decisions (D010 ViewSpec query, D020 explorer mode switching, etc.)

## Observability Impact

This task produces a design document only — no runtime code changes. Observable signals:

- **Artifact presence:** `test -f .gsd/design/VIEWS-RETHINK.md`
- **Structural completeness:** `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` ≥ 6
- **Code path validity:** All referenced code paths (ViewSpecService, ShapesService, carousel_tab_bar.html, QueryService) must exist in the codebase at time of writing. Verify with `rg -l <term> backend/ frontend/`.
- **Failure mode:** If future refactoring renames referenced services, the design doc becomes stale. The diagnostic check in S07-PLAN.md's verification section catches this.

## Expected Output

- `.gsd/design/VIEWS-RETHINK.md` — complete design document (~200-350 lines) covering all must-haves, ready for review and implementation planning in a future milestone
