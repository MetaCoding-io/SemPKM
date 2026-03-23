# M036: Business Planning Mental Models & Custom Renderers

**Vision:** A library of business planning frameworks as typed RDF data with custom visual renderers — matrices, canvases, progress bars — that an AI copilot can query across frameworks for structured strategic analysis.

## Success Criteria

- User installs `business-planning` model from Admin > Mental Models and sees new types (Eisenhower Matrix, SWOT, BMC, OKR, etc.) in the object browser
- Creating an Eisenhower Matrix shows items in a 2×2 quadrant view; dragging an item between quadrants updates its urgency/importance properties via the command API
- Creating a Business Model Canvas shows the 9-box poster layout with inline editing per section
- OKR Objectives display Key Results with progress bars computed from current/target values
- Decision Matrix shows weighted criteria with computed scores and auto-ranked alternatives
- SPARQL query `SELECT ?item WHERE { ?item a bp:EisenhowerItem ; bp:urgency "high" ; bp:importance "high" }` returns structured results across multiple matrices
- Cross-model edge: an Eisenhower item linked to a bpkm:Task appears in both framework view and task table
- All framework types produce valid SHACL forms via the existing form generator
- Model survives Docker restart, `refresh_artifacts` works, custom renderers survive theme toggle (dark/light)

## Key Risks / Unknowns

- **Custom renderer dispatch** — The view router dispatches renderers via hardcoded elif branches (1486 lines). New renderer types need new branches, endpoints, and templates. The `register_renderer()` infrastructure exists but is dead code. Risk: extending the elif pattern is ugly but safe; wiring the registry is cleaner but higher scope.
- **Drag-to-reclassify in dockview** — Dragging items between quadrants must use stopPropagation to avoid dockview panel interference. Proven pattern (kanban M031, canvas M008) but each new drag context needs its own wiring.
- **BMC 9-box CSS Grid** — The Business Model Canvas poster layout has non-uniform row/column spans. Needs careful responsive design and dark mode support.
- **Computed values** — OKR progress (current/target) and Decision Matrix weighted scores (Σ weight × score) need server-side computation for SPARQL queryability.

## Proof Strategy

- Custom renderer dispatch → retire in S01 by shipping Eisenhower quadrant view as a new renderer type through the full vertical (model install → type creation → custom view rendering → drag interaction)
- BMC layout complexity → retire in S02 by shipping the 9-box CSS Grid layout with inline editing
- Computed values → retire in S03 by shipping OKR progress bars and Decision Matrix auto-ranking with server-side computation

## Verification Classes

- Contract verification: pytest unit tests for model manifest validation, SHACL shape generation, SPARQL query execution, computed field logic
- Integration verification: Docker Compose stack — model install, object creation, custom renderer rendering, drag-to-update roundtrip, cross-model edges
- Operational verification: Docker restart persistence, refresh_artifacts, theme toggle
- UAT / human verification: visual inspection of quadrant layout, BMC poster, progress bars, dark mode styling

## Milestone Definition of Done

This milestone is complete only when all are true:

- `business-planning` model installs cleanly via Admin UI and passes manifest validation
- All 5 core framework types (Eisenhower, SWOT, BMC, OKR, Decision Matrix) have custom renderers that display correctly
- Drag-to-reclassify works in quadrant views (Eisenhower, SWOT) with RDF property updates
- OKR progress bars and Decision Matrix rankings compute from real data
- Extended framework types (Porter, Value Chain, PESTLE, BCG, etc.) work with existing renderers (table/kanban)
- Cross-model edges connect framework items to basic-pkm/ppv types
- SPARQL queries return structured framework data across multiple instances
- All renderers work in both light and dark modes
- E2E tests cover install, creation, custom rendering, and drag interaction
- User guide documents all framework types and custom renderers

## Requirement Coverage

- Covers: BIZ-01 (model archive), BIZ-02 (quadrant renderer), BIZ-03 (BMC renderer), BIZ-04 (OKR renderer), BIZ-05 (Decision Matrix renderer), BIZ-06 (extended frameworks), BIZ-07 (cross-model edges), BIZ-08 (SPARQL queryability), BIZ-09 (E2E tests), BIZ-10 (documentation)
- Partially covers: none
- Leaves for later: AI auto-population (M035 scope), export to PDF/PowerPoint, import from Miro/Lucidchart, user-created custom renderers
- Orphan risks: none

## Slices

- [x] **S01: Eisenhower Matrix — Model Archive + Quadrant Renderer** `risk:high` `depends:[]`
  > After this: User installs business-planning model, creates an Eisenhower Matrix, sees items in a 2×2 quadrant view, and drags items between quadrants with RDF property updates.
- [x] **S02: Business Model Canvas — 9-Box Poster Renderer** `risk:high` `depends:[S01]`
  > After this: User creates a Business Model Canvas and fills the 9 standard sections (Key Partners, Key Activities, Value Propositions, etc.) in a poster-style grid layout with inline editing.
- [x] **S03: OKR Progress + Decision Matrix Weighted Scoring** `risk:medium` `depends:[S01]`
  > After this: User creates OKR Objectives with Key Results showing progress bars, and Decision Matrices with weighted criteria showing auto-ranked alternatives.
- [x] **S04: Extended Framework Library** `risk:low` `depends:[S01]`
  > After this: User creates Porter's Five Forces, PESTLE, Balanced Scorecard, RACI, Value Chain, Lean Canvas, BCG/Ansoff/Stakeholder/Risk matrices, all browsable via table, kanban, and existing renderers. SWOT uses the quadrant renderer from S01.
- [x] **S05: Cross-Model Integration, E2E Tests & Documentation** `risk:low` `depends:[S01,S02,S03,S04]`
  > After this: Eisenhower items link to bpkm:Tasks, OKR Objectives link to ppv:GoalOutcomes. SPARQL queries return structured data across all frameworks. E2E Playwright tests cover model install, custom renderers, and drag interactions. User guide documents all frameworks.

## Boundary Map

### S01 → S02, S03, S04, S05

Produces:
- `business-planning` model archive structure: manifest.yaml, namespace `urn:sempkm:model:bp:`, shared base ontology classes (bp:FrameworkItem, bp:QuadrantItem)
- Quadrant renderer: `browser/quadrant_view.html` template + `frontend/static/js/quadrant.js` + `frontend/static/css/quadrant.css`
- New renderer type `quadrant` added to `_VALID_RENDERERS` and view router elif branch
- Data endpoint pattern: `/browser/views/generic/quadrant/data` returning JSON for quadrant placement
- Drag-to-reclassify API contract: PATCH via `object.patch` command to update quadrant axis properties
- Eisenhower types: bp:EisenhowerMatrix, bp:EisenhowerItem with bp:urgency (sh:in ["high","low"]) and bp:importance (sh:in ["high","low"])
- SHACL shapes for all S01 types passing form generation
- ViewSpecs declaring `sempkm:rendererType: "quadrant"` for Eisenhower

Consumes:
- nothing (first slice)

### S02

Produces:
- BMC renderer: `browser/bmc_view.html` template + `frontend/static/js/bmc.js` + `frontend/static/css/bmc.css`
- New renderer type `bmc` added to router
- BMC types: bp:BusinessModelCanvas, bp:BMCSection with bp:sectionType (sh:in 9 standard sections)
- Data endpoint: `/browser/views/generic/bmc/data`

Consumes:
- S01 model archive structure, namespace, shared ontology base

### S03

Produces:
- OKR renderer: `browser/okr_view.html` template + `frontend/static/js/okr.js` + `frontend/static/css/okr.css`
- Decision Matrix renderer: `browser/decision_matrix_view.html` + JS + CSS
- New renderer types `okr` and `decision-matrix` in router
- Server-side computed fields: OKR progress percentage, Decision Matrix weighted scores
- OKR types: bp:Objective, bp:KeyResult with bp:currentValue, bp:targetValue, bp:unit
- Decision Matrix types: bp:DecisionMatrix, bp:Alternative, bp:Criterion with bp:weight, bp:Score with bp:value

Consumes:
- S01 model archive structure, namespace, shared ontology base

### S04

Produces:
- Extended framework ontology types (Porter, PESTLE, Balanced Scorecard, RACI, Value Chain, Lean Canvas, BCG, Ansoff, Stakeholder Map, Risk Matrix)
- SHACL shapes + ViewSpecs for each type (using existing renderers: table, kanban, quadrant)
- SWOT type using S01's quadrant renderer
- Seed data for each framework type

Consumes:
- S01 model archive, quadrant renderer (for SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix)

### S05

Produces:
- Cross-model edge definitions in ontology (bp:EisenhowerItem → bpkm:Task, bp:Objective → ppv:GoalOutcome)
- E2E Playwright test suite covering model install, type creation, custom renderer display, drag interaction
- User guide chapter covering all business planning frameworks and custom renderers

Consumes:
- S01 quadrant renderer, S02 BMC renderer, S03 OKR/Decision Matrix renderers, S04 extended frameworks
