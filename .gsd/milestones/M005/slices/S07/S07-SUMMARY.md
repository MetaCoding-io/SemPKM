---
id: S07
parent: M005
milestone: M005
provides:
  - Views Rethink design document at .gsd/design/VIEWS-RETHINK.md proposing generic cross-type views, SHACL-driven columns, query-scoped view binding, and explorer tree consolidation
requires:
  - slice: S01
    provides: Queries stored as RDF resources referenceable by IRI, enabling sempkm:scopeQuery view binding
affects:
  - Future implementation milestone for views rethink Phase 1
key_files:
  - .gsd/design/VIEWS-RETHINK.md
key_decisions:
  - D093: Generic views registered in-memory at startup, not as RDF in a system graph
  - D094: SHACL shapes via ShapesService as the column discovery source for generic views
  - D095: Type filter pills (not dropdown or carousel) for cross-type generic views
  - D096: sempkm:scopeQuery predicate for view-to-query scope binding (distinct from sempkm:fromQuery provenance)
  - D097: 3-phase migration (additive-first) with Phase 1 as milestone deliverable
patterns_established:
  - Design doc format following PROV-O-ALIGNMENT.md structure (status header, current state audit, proposed changes, migration plan, recommendations)
observability_surfaces:
  - none (design document only, no runtime changes)
drill_down_paths:
  - .gsd/milestones/M005/slices/S07/tasks/T01-SUMMARY.md
duration: 25m
verification_result: passed
completed_at: 2026-03-14
---

# S07: Views Rethink Design

**Design document proposing generic cross-type views with SHACL-driven columns, query-scoped view binding, and explorer tree consolidation from 31+ entries to ~7.**

## What Happened

Created `.gsd/design/VIEWS-RETHINK.md` — a comprehensive design document addressing the ViewSpec scaling problem (31+ explorer entries across 2 models, growing linearly with each new model). The document is grounded in existing codebase patterns, not hypothetical abstractions.

The design proposes a hybrid approach: 3 generic system-provided views (Table/Cards/Graph) that work across all types using SHACL shapes for dynamic column discovery, coexisting with model-declared ViewSpecs that remain accessible via carousel tabs when a type is selected. The explorer tree consolidates from 31+ per-type folder entries to ~7 fixed entries plus a Saved Views folder.

Key design elements:
- **Generic views** registered in `ViewSpecService` at startup with `sempkm:isGeneric` predicate — no new RDF system graph needed
- **SHACL column discovery** via `ShapesService._extract_node_shape()` — reuses existing `PropertyShape.path`, `.name`, `.order` for dynamic table columns
- **Type filter pills** for cross-type views — distinct from the carousel tab bar which assumes a single target class
- **Query scope binding** via `sempkm:scopeQuery` — extends the existing `sempkm:fromQuery` provenance pattern to support runtime result filtering
- **3-phase migration** — Phase 1 (additive, generic views alongside existing tree), Phase 2 (consolidate explorer), Phase 3 (cleanup). Phase 1 is the deliverable for a future milestone.

The document includes Turtle examples for all RDF vocabulary additions, before/after explorer tree diagrams, template and router change tables, and explicitly scoped open questions and deferred items.

## Verification

- `test -f .gsd/design/VIEWS-RETHINK.md` — **PASS** (file exists)
- `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` → 34 (≥6 required) — **PASS**
- Code path references validated in codebase:
  - ViewSpecService: 7 files — **PASS**
  - ShapesService: 11 files — **PASS**
  - carousel_tab_bar: 3 files — **PASS**
  - QueryService: 10 files — **PASS**
- 24 references to real code paths in the design doc — **PASS**

## Requirements Advanced

- VIEW-01 (views rethink — design only) — design doc produced as specified in M005 success criteria

## Requirements Validated

- None — this is a design document; implementation validation deferred to future milestone

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

None.

## Known Limitations

- This is a design document only — no runtime code changes, no new endpoints, no new templates
- Open questions on generic graph view performance limits and sparse SHACL fallback UX remain unresolved (documented in design doc for future implementation planning)
- Duplicate route definitions in `views/router.py` (identified in design doc) should be cleaned up before implementing Phase 1

## Follow-ups

- Implement Phase 1 (generic views alongside existing tree) in a future milestone
- Clean up duplicate route definitions in `views/router.py` before adding new endpoints
- Resolve open questions (graph view LIMIT strategy, sparse SHACL fallback hints, type filter persistence scope) during Phase 1 implementation planning

## Files Created/Modified

- `.gsd/design/VIEWS-RETHINK.md` — new: complete views rethink design document (~310 lines)
- `.gsd/milestones/M005/slices/S07/S07-PLAN.md` — added Observability/Diagnostics section, marked T01 done
- `.gsd/milestones/M005/slices/S07/tasks/T01-PLAN.md` — added Observability Impact section

## Forward Intelligence

### What the next slice should know
- S07 is a design-doc-only slice with no runtime changes. S08 (VFS v2 Design) and S09 (E2E Tests & Docs) have no dependency on S07's output.
- The views rethink design assumes queries are in RDF (S01 dependency) — this is already complete.

### What's fragile
- `views/router.py` has duplicate route definitions for `/explorer`, `/menu`, and `/available` — any new endpoint additions should clean these up first to avoid confusion about which route handles requests.

### Authoritative diagnostics
- `grep -c "^##" .gsd/design/VIEWS-RETHINK.md` — structural completeness of the design doc
- `for term in ViewSpecService ShapesService carousel_tab_bar QueryService; do echo "$term: $(rg -l "$term" backend/ frontend/ | wc -l) files"; done` — validates that all referenced code paths still exist in the codebase

### What assumptions changed
- No assumptions changed — the design doc was written after S01 (queries in RDF) and S06 (PROV-O alignment) were complete, so all prerequisites were stable.
