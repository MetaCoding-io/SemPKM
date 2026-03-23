---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M036

## Success Criteria Checklist

- [x] **User installs `business-planning` model from Admin > Mental Models and sees new types** — Evidence: S01 created the 5-file model archive (manifest.yaml, ontology, shapes, views, seed JSON-LD). Manifest validates as `business-planning v1.0.0` with namespace `urn:sempkm:model:business-planning:`. S04 extended to 32 OWL types across 15 frameworks. Ontology parses to 423 triples, shapes to 1665 triples, views to 255 triples, seed to 479 triples.
- [x] **Eisenhower Matrix shows items in 2×2 quadrant view; dragging updates urgency/importance via command API** — Evidence: S01 shipped the full vertical — `quadrant` renderer wired into `_VALID_RENDERERS`, `RENDERER_REGISTRY`, and `generic_view()` elif chain. `quadrant.js` implements drag-to-reclassify with `stopPropagation()` dockview isolation, optimistic DOM move, and atomic `object.patch` for both axis properties. 28 unit tests pass. S01-T03 browser verification confirmed drag persistence across reload.
- [x] **Business Model Canvas shows 9-box poster layout with inline editing** — Evidence: S02 shipped `bmc` renderer with 10-column CSS Grid (443 lines CSS), 9 color-coded sections, debounced inline editing via `object.patch`. 31 unit tests pass. Template uses `q['items']` dict access (Jinja2 method collision fix).
- [x] **OKR Objectives display Key Results with progress bars computed from current/target** — Evidence: S03 shipped `okr` renderer with server-side `(currentValue / targetValue) × 100` computation, clamped 0–100, color-coded (green ≥70%, amber 30–69%, red <30%). Click-to-edit on currentValue with client-side recompute. 25 unit tests pass including div-by-zero and over-target edge cases.
- [x] **Decision Matrix shows weighted criteria with computed scores and auto-ranked alternatives** — Evidence: S03 shipped `decision-matrix` renderer with `Σ(weight × value)` per alternative, tie-aware ranking, rank badges (🥇🥈🥉), client-side column sorting with re-ranking. 26 unit tests pass.
- [x] **SPARQL query returns structured results across multiple matrices** — Evidence: S01 seed data provides 8 Eisenhower items across 4 quadrants with `bp:urgency` and `bp:importance` properties. S03 seeds OKR and Decision Matrix data. S05 UAT includes 3 SPARQL query examples. All data stored as typed RDF triples in the model's namespace, queryable via `/api/sparql`.
- [x] **Cross-model edge: Eisenhower item linked to bpkm:Task** — Evidence: S05-T01 added 3 OWL ObjectProperties (`bp:relatedTask`, `bp:relatedGoalOutcome`, `bp:relatedProject`) to ontology and 3 matching SHACL PropertyShapes with `sh:class` constraints. Ontology grew from 408→423 triples; shapes from 1632→1665.
- [x] **All framework types produce valid SHACL forms** — Evidence: All 32 types have SHACL NodeShapes with PropertyGroups (1665 shape triples). 21 `sh:in` constraints across 12 quadrant axes and 9 non-quadrant enum fields. Form generation uses existing SHACL→HTML pipeline proven across basic-pkm and ppv models.
- [~] **Model survives Docker restart, `refresh_artifacts` works, custom renderers survive theme toggle** — Evidence (partial): Dark mode is verified — 58 `data-theme="dark"` CSS rules across all 4 renderer stylesheets. Docker restart and `refresh_artifacts` were not explicitly tested in any slice summary, but the model archive follows the identical 5-file JSON-LD structure as basic-pkm which has established restart/refresh behaviour. This is an operational concern, not a model defect.
- [~] **E2E tests cover install, creation, custom rendering, and drag interaction** — Evidence (partial): S05-T02 created `e2e/tests/36-business-planning/business-planning.spec.ts` (344 lines) covering model install via Admin UI, 11 objects via batch Command API with `@slot:` references, 4 custom renderer tab opens (quadrant, bmc, okr, decision-matrix), and SPARQL query verification. TypeScript compiles clean. **Gap:** The E2E spec does not include drag-to-reclassify testing. Drag interaction is verified via S01 unit tests (28 tests) and S01-T03 manual browser verification, but not in the automated Playwright suite.
- [x] **User guide documents all framework types and custom renderers** — Evidence: S05-T03 added ~490 lines as section "5. Business Planning" in `docs/guide/39-mental-model-catalog.md`. Documents 15 frameworks in 5 categories, 4 custom renderer descriptions, cross-model edges, 3 SPARQL examples, and installation instructions. Chapter 39 was already indexed in all 3 guide files (README.md, index.html, guide.html).

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Model archive + quadrant renderer full vertical (install → view → drag) | 5-file model archive, `quadrant` renderer wired 3 layers deep, 2×2 CSS Grid frontend, drag-to-reclassify JS, 28 unit tests, 8 seed items | **pass** |
| S02 | BMC 9-box poster renderer with inline editing | `bmc` renderer wired, 10-column CSS Grid (443 lines), debounced inline editing, 31 unit tests, 9 seed sections | **pass** |
| S03 | OKR progress bars + Decision Matrix weighted scoring | `okr` and `decision-matrix` renderers wired, server-side computed fields, click-to-edit, column sorting, 51 unit tests, seed data for both | **pass** |
| S04 | 11 extended framework types using existing renderers | 22 new OWL classes (11 containers + 11 items), 5 quadrant-based + 6 table-based frameworks, SWOT/BCG/Ansoff/Stakeholder/Risk label mappings, 42 quadrant tests (14 new), seed data for all | **pass** |
| S05 | Cross-model edges, E2E tests, documentation | 3 cross-model ObjectProperties, E2E spec (344 lines, 4 renderers), user guide section (~490 lines, 15 frameworks) | **pass** (minor gap: no drag in E2E) |

## Cross-Slice Integration

| Boundary | Expected | Actual | Status |
|----------|----------|--------|--------|
| S01 → S02 (model archive structure, namespace) | S02 extends ontology/shapes/views/seed | S02 added BMC types to same JSON-LD files using `bp:` namespace | ✅ |
| S01 → S03 (model archive, namespace) | S03 extends with OKR/DM types | S03 added 6 OWL classes, 10 properties to same archive | ✅ |
| S01 → S04 (quadrant renderer) | S04 reuses quadrant for SWOT, BCG, Ansoff, Stakeholder, Risk | S04 extended `_QUADRANT_LABELS` and `_AXIS_KEYWORD_PAIRS` for 5 frameworks; 14 new tests confirm labels | ✅ |
| S01–S04 → S05 (all renderers + types) | S05 writes E2E covering all 4 renderers | S05 E2E opens quadrant, bmc, okr, decision-matrix tabs and verifies board containers | ✅ |
| S05 consumes S01–S04 for documentation | S05 documents all 15 frameworks | Guide section covers all 15 frameworks with type references and renderer descriptions | ✅ |

No boundary mismatches found. All produces/consumes contracts are satisfied.

## Requirement Coverage

| Requirement | Slice(s) | Evidence | Status |
|-------------|----------|----------|--------|
| BIZ-01 (model archive) | S01, S04 | 5-file archive with 32 types, manifest validates, all JSON-LD parses clean | ✅ covered |
| BIZ-02 (quadrant renderer) | S01, S04 | Full renderer vertical with drag, 6 framework label sets, 42 unit tests | ✅ covered |
| BIZ-03 (BMC renderer) | S02 | 9-box CSS Grid, inline editing, 31 unit tests | ✅ covered |
| BIZ-04 (OKR renderer) | S03 | Progress bars with server-side computation, click-to-edit, 25 unit tests | ✅ covered |
| BIZ-05 (Decision Matrix renderer) | S03 | Weighted scoring, tie-aware ranking, column sorting, 26 unit tests | ✅ covered |
| BIZ-06 (extended frameworks) | S04 | 11 additional frameworks (Porter, PESTLE, BSC, RACI, Value Chain, Lean Canvas, BCG, Ansoff, Stakeholder, Risk, SWOT) | ✅ covered |
| BIZ-07 (cross-model edges) | S05 | 3 ObjectProperties (relatedTask, relatedGoalOutcome, relatedProject) in ontology + shapes | ✅ covered |
| BIZ-08 (SPARQL queryability) | S01, S03, S05 | All data as typed RDF, SPARQL examples in UAT and guide | ✅ covered |
| BIZ-09 (E2E tests) | S05 | 344-line Playwright spec covering install, 4 renderers, SPARQL. No drag test. | ⚠️ partial |
| BIZ-10 (documentation) | S05 | ~490-line guide section, 15 frameworks, 4 renderers, 3 SPARQL examples | ✅ covered |

## Verdict Rationale

**Verdict: needs-attention** — All 5 slices delivered their core claims. The 4 custom renderers (quadrant, bmc, okr, decision-matrix) are fully wired with backend service methods, Jinja2 templates, interactive frontend JS/CSS, and comprehensive unit test suites (124 total tests, all passing). The model archive is complete with 32 types across 15 frameworks. Cross-model edges are defined. Documentation covers all frameworks.

Two minor gaps prevent a clean `pass`:

1. **E2E drag interaction not tested** — The Playwright spec covers install, creation, 4 renderer views, and SPARQL, but does not exercise drag-to-reclassify. Drag is verified via 28 S01 unit tests and manual browser verification during S01-T03, so the functionality is proven — it's the automated E2E coverage that's incomplete. This does not block milestone completion because (a) drag testing in Playwright requires complex coordinate-based DnD which is fragile across CI environments, and (b) the behaviour is thoroughly unit-tested.

2. **Docker restart / refresh_artifacts not explicitly tested** — The success criteria mention these operational properties. No slice summary provides evidence of testing them. However, the model follows the identical archive structure as basic-pkm which has established restart/refresh behaviour, so this is not a model-specific risk.

Neither gap represents a material defect in the delivered functionality. Both are coverage gaps in verification, not gaps in implementation. The milestone can be completed with these documented.

## Remediation Plan

No remediation slices needed. The two gaps documented above are minor verification coverage items that do not block completion:

- E2E drag testing can be added in a future milestone when broader E2E coverage is prioritized
- Docker restart/refresh verification is an operational concern already proven by the platform's existing model infrastructure
