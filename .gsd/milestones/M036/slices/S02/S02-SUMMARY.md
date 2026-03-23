---
id: S02
parent: M036
milestone: M036
provides:
  - bp:BusinessModelCanvas and bp:BMCSection OWL classes in business-planning model
  - SHACL shapes with 9-value sh:in constraint on bp:sectionType (kebab-case enum)
  - 3 BMC ViewSpecs (2 table + 1 bmc renderer) and seed data (1 canvas + 9 sections)
  - bmc renderer type wired into _VALID_RENDERERS, RENDERER_REGISTRY, and generic_view elif chain
  - _detect_bmc_sections() service method — finds SHACL property with exactly 9 sh:in values
  - _build_bmc_select() SPARQL builder with OPTIONAL sectionContent and canvas path
  - execute_bmc_query() groups results into 9 section buckets keyed by sectionType
  - BMC_SECTION_TYPES class-level dict mapping 9 kebab-case values to display names
  - /browser/views/generic/bmc/data JSON endpoint for debugging BMC data
  - bmc_view.html Jinja2 template with 10-column CSS Grid and lazy-load JS boot
  - bmc.css (443 lines) — 10×3 CSS Grid poster layout with 9 color-coded sections and dark mode
  - bmc.js (157 lines) — inline editing with debounced object.patch saves and dockview isolation
  - 31 unit tests covering section detection, SPARQL building, and result grouping
requires:
  - S01 model archive structure, namespace urn:sempkm:model:business-planning:, shared ontology base
affects:
  - S05 (consumes BMC renderer for E2E tests + documentation)
key_files:
  - models/business-planning/ontology/business-planning.jsonld
  - models/business-planning/shapes/business-planning.jsonld
  - models/business-planning/views/business-planning.jsonld
  - models/business-planning/seed/business-planning.jsonld
  - models/business-planning/manifest.yaml
  - backend/app/views/router.py
  - backend/app/views/service.py
  - backend/app/views/registry.py
  - backend/app/templates/browser/bmc_view.html
  - frontend/static/js/bmc.js
  - frontend/static/css/bmc.css
  - backend/tests/test_bmc.py
key_decisions:
  - BMC section detection uses 9-value sh:in count (not hardcoded property IRI) — any type with exactly 9 enum values qualifies, with preference for "sectiontype" in path name
  - 10-column CSS Grid (not 5-column doubled) for precise section spanning — Key Partners and Value Propositions span 2 columns while Key Activities/Resources each get 2 columns in the middle stack
  - Each section gets a unique color identity (9 distinct hues) rather than grouping by category — more visually scannable
  - sectionContent IRI hardcoded in SPARQL builder as urn:sempkm:model:business-planning:sectionContent — acceptable coupling for a model-specific feature
patterns_established:
  - BMC follows exact same 4-layer wiring pattern as quadrant (registry → _VALID_RENDERERS → elif branch → service methods) confirming the pattern is repeatable for S03
  - BMC textarea inline editing uses debounce timer map keyed by IRI — cancels pending debounce on blur for immediate save
  - BMC_SECTION_TYPES dict centralises kebab-to-display mapping for use in both service grouping and template rendering
  - Dark mode tints use same rgba() approach as quadrant.css — 0.07 alpha light, 0.12 alpha dark, 0.25 border alpha dark
  - Test structure mirrors test_quadrant.py exactly — same _make_property/_make_form/_build_service helpers, adapted for 9-section pipeline
observability_surfaces:
  - logger.info("generic_view: renderer=bmc type=%s ...") in router
  - logger.info("execute_bmc_query: type=%s total=%d sections=%d") in service
  - /browser/views/generic/bmc/data?type=<iri> JSON endpoint for raw data debugging
  - Error template when type has no 9-value sh:in property
  - console.error("bmc: failed to patch section content for", iri, err) on save failure
  - .bmc-save-error (red flash) and .bmc-save-ok (green flash) CSS classes for visual feedback
drill_down_paths:
  - .gsd/milestones/M036/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M036/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M036/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M036/slices/S02/tasks/T04-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-23
---

# S02: Business Model Canvas — 9-Box Poster Renderer

**Shipped the complete BMC vertical: 2 new OWL classes in the business-planning model, a `bmc` renderer wired through all backend layers, a 10×3 CSS Grid poster layout with 9 color-coded sections, inline editing with debounced saves via object.patch, and 31 unit tests.**

## What Happened

**T01 — Model Archive Extension** added `bp:BusinessModelCanvas` (subClassOf `gist:Collection`) and `bp:BMCSection` (subClassOf `bp:FrameworkItem`) to the existing business-planning model. The `bp:sectionType` property has `sh:in` with exactly 9 kebab-case values (`key-partners`, `key-activities`, `value-propositions`, `customer-relationships`, `customer-segments`, `key-resources`, `channels`, `cost-structure`, `revenue-streams`). Three ViewSpecs added (2 table views + 1 bmc renderer). Seed data provides 1 canvas + 9 sections with realistic multi-line content. Manifest updated with 2 icon definitions. Total model now has 6 OWL classes, 72 ontology triples, 287 shape triples, 38 view triples, 113 seed triples.

**T02 — Backend Wiring** added `bmc` to `RENDERER_REGISTRY` and `_VALID_RENDERERS`, added elif branch in `generic_view()` with error handling (no-type, no-section-property, happy path), and added data endpoint in `generic_view_data()`. Three service methods on ViewSpecService: `_detect_bmc_sections()` finds SHACL property with exactly 9 `sh:in` values (preferring path containing "sectiontype"), also detects canvas link property by target_class. `_build_bmc_select()` builds SPARQL with OPTIONAL sectionContent/canvas and optional scope sub-select. `execute_bmc_query()` groups into 9 buckets via `BMC_SECTION_TYPES` dict. Template uses `section['items']` bracket notation (Jinja2 dict key access) and lazy-load JS boot pattern.

**T03 — Frontend** created `bmc.css` (443 lines): 10-column × 3-row CSS Grid with `[data-section-type]` attribute selectors positioning all 9 sections in the canonical BMC poster layout. Each section has a unique pastel tint (9 distinct hues). Full dark mode via `html[data-theme="dark"]`. Responsive single-column at < 800px. Created `bmc.js` (157 lines): IIFE with `initBMC(boardEl)`, debounced 500ms save on input, immediate save on blur, `object.patch` with `bp:sectionContent` property, `stopPropagation()` on drag events for dockview isolation, `sempkm:scope-changed` listener for re-fetch.

**T04 — Unit Tests** created 31 tests across 3 classes: `TestDetectBmcSections` (10 tests — happy path, keyword preference, rejection of ≠9 values, canvas detection), `TestBuildBmcSelect` (6 tests — structure, scope filter, canvas path, label alternatives), `TestExecuteBmcQuery` (15 tests — 9-bucket grouping, missing sections, empty results, dedup, error handling, canonical ordering, canvas field capture).

## Verification

All slice-level checks pass:

| Check | Result |
|-------|--------|
| `pytest tests/test_bmc.py -v` | 31 passed in 0.46s ✅ |
| All 5 JSON-LD model files parse via rdflib | ontology:72, shapes:287, views:38, seed:113 triples ✅ |
| `parse_manifest()` validates | Business Planning 1.0.0 ✅ |
| `bmc` in `_VALID_RENDERERS` | 7 mentions in router.py ✅ |
| `bmc` in `RENDERER_REGISTRY` | template: browser/bmc_view.html ✅ |
| `stopPropagation` in bmc.js | 2 occurrences ✅ |
| `data-theme="dark"` in bmc.css | 22 occurrences ✅ |
| `data-section-type` in bmc.css | 55 occurrences (9 sections) ✅ |
| bmc.css line count | 443 lines (≥ 200) ✅ |

## Requirements Advanced

- BIZ-03 (BMC renderer) — full BMC renderer vertical shipped from model types through CSS Grid frontend with inline editing

## Requirements Validated

- None yet — BIZ-03 needs live runtime integration testing (model install, BMC view rendering, inline save roundtrip) for validated status

## Deviations

None — all 4 tasks followed the quadrant patterns established in S01 exactly.

## Known Limitations

- Inline editing saves `bp:sectionContent` as a single text blob per section, not individual items. Users edit the full section content in one textarea.
- No drag-and-drop between sections (BMC sections are conceptually distinct; reordering doesn't apply the way quadrant reclassification does).
- Canvas-scoped filtering (`belongsToCanvas`) exists in the SPARQL builder but the frontend doesn't expose a canvas picker yet — all sections from all canvases appear in one view.
- No E2E Playwright tests — deferred to S05 per roadmap.

## Follow-ups

- S05 must add E2E tests for BMC view rendering and inline editing roundtrip
- S05 must document BMC in the user guide
- Future: canvas picker dropdown for filtering sections by parent canvas when users have multiple BMCs

## Forward Intelligence

### What the next slice should know
- The `bmc` renderer wiring confirms the pattern is fully repeatable: registry entry → `_VALID_RENDERERS` → elif branch → 3 service methods → template + JS + CSS. S03 (OKR + Decision Matrix) should follow the same structure.
- BMC detection uses 9-value `sh:in` count — this is specific to BMC. S03's OKR and Decision Matrix will need their own detection heuristics (e.g., detecting `bp:currentValue`/`bp:targetValue` for OKR progress).
- The `BMC_SECTION_TYPES` dict pattern (centralised kebab-to-display mapping) works well for any renderer that needs canonical category names.

### What's fragile
- `sectionContent` IRI is hardcoded in `_build_bmc_select()` — if the model property IRI changes, the SPARQL breaks silently (returns no content).
- Canvas detection relies on target_class containing "canvas" or "businessmodelcanvas" (case-insensitive) — non-standard naming would miss it.

### Authoritative diagnostics
- `/browser/views/generic/bmc/data?type=<iri>` — returns JSON with sections array, section_types dict, and total count. Check here first if the view looks wrong.
- `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v` — 31 tests pin the entire BMC pipeline.
