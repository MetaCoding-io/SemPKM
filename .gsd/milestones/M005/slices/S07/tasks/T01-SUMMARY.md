---
id: T01
parent: S07
milestone: M005
provides:
  - Views Rethink design document at .gsd/design/VIEWS-RETHINK.md
key_files:
  - .gsd/design/VIEWS-RETHINK.md
key_decisions:
  - Generic views registered in-memory at startup, not as RDF in a system graph
  - SHACL shapes via ShapesService as the column discovery source for generic views
  - Type filter pills (not dropdown or carousel) for cross-type generic views
  - sempkm:scopeQuery predicate for view-to-query scope binding (distinct from sempkm:fromQuery provenance)
  - 3-phase migration (additive-first) with Phase 1 as milestone deliverable
patterns_established:
  - Design doc format following PROV-O-ALIGNMENT.md structure (status header, current state audit, proposed changes, migration plan, recommendations)
observability_surfaces:
  - none (design document only, no runtime changes)
duration: 25m
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T01: Write Views Rethink Design Document

**Wrote complete design document proposing generic cross-type views with SHACL-driven columns, query-scoped view binding, and explorer tree consolidation from 31+ entries to ~7.**

## What Happened

Created `.gsd/design/VIEWS-RETHINK.md` following the PROV-O alignment doc format. The document covers:

1. **Current State** — audited ViewSpec scaling (12 basic-pkm + 19 ppv = 31 entries), documented the explorer tree structure in `views_explorer.html`, and identified what works well (ViewSpec data model, renderer execution, carousel tab bar).

2. **Proposed Data Model** — defined 3 generic system views (Table/Cards/Graph) with `sempkm:isGeneric` predicate, SHACL column discovery via `ShapesService._extract_node_shape()`, and query scope binding via `sempkm:scopeQuery`. Includes Turtle examples for all RDF vocabulary additions.

3. **Explorer Tree Redesign** — before/after structure showing consolidation from 31+ per-type folder entries to ~7 fixed entries + Saved Views folder. Type-specific model views become carousel tabs when a type is selected. Type filter pills replace carousel for cross-type generic views.

4. **Migration Plan** — 3 phases: Phase 1 (additive, generic views alongside existing tree), Phase 2 (consolidate explorer, merge MY VIEWS), Phase 3 (cleanup dead code, optimize queries). Backward compatibility ensured — model-declared ViewSpecs are never modified.

5. **Open Questions** — generic graph view performance limits, sparse SHACL fallback, query→view scope binding UX, duplicate route cleanup timing, type filter persistence scope.

6. **Recommendations** — Phase 1 as milestone deliverable, reuse existing mechanisms, clean up router duplicates first.

Also fixed pre-flight observability gaps: added Observability/Diagnostics section to S07-PLAN.md and Observability Impact section to T01-PLAN.md.

## Verification

- `test -f .gsd/design/VIEWS-RETHINK.md` — **PASS**
- `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` → 34 (≥6 required) — **PASS**
- ViewSpecService: 8 mentions, ShapesService: 8 mentions, carousel_tab_bar: 5 mentions, QueryService: 4 mentions — **PASS**
- Turtle examples present (20 lines with `@prefix`, `sempkm:isGeneric`, `sempkm:scopeQuery`) — **PASS**
- All referenced code paths verified in codebase: ViewSpecService (7 files), ShapesService (11 files), carousel_tab_bar (3 files), QueryService (10 files) — **PASS**
- Slice-level verification: all 3 checks pass (file exists, ≥6 H2 sections, real code path references) — this is the only task in S07, so all slice checks pass

## Diagnostics

No runtime diagnostics — this is a design document. Inspect with:
- `cat .gsd/design/VIEWS-RETHINK.md` — full document
- `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` — structural completeness
- `for term in ViewSpecService ShapesService carousel_tab_bar QueryService; do echo "$term: $(rg -l "$term" backend/ frontend/ | wc -l) files"; done` — code path validity

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `.gsd/design/VIEWS-RETHINK.md` — new: complete views rethink design document (~310 lines)
- `.gsd/milestones/M005/slices/S07/S07-PLAN.md` — added Observability/Diagnostics section, marked T01 done
- `.gsd/milestones/M005/slices/S07/tasks/T01-PLAN.md` — added Observability Impact section
