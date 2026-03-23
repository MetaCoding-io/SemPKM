# S05: Cross-Model Integration, E2E Tests & Documentation

**Goal:** Complete the business-planning milestone by adding cross-model edge definitions, E2E Playwright test coverage for all custom renderers, and user guide documentation for all 16 frameworks.
**Demo:** Eisenhower items can link to bpkm:Tasks via SHACL forms, OKR Objectives link to ppv:GoalOutcomes. E2E tests install the model, create objects, open all 4 custom view renderers, and verify structured SPARQL results. User guide chapter 39 documents all 16 business planning frameworks with field reference tables.

## Must-Haves

- 3 cross-model ObjectProperty declarations (bp:relatedTask, bp:relatedGoalOutcome, bp:relatedProject) in ontology with SHACL PropertyShapes
- E2E Playwright spec covering model install, object creation via Command API, and rendering verification for quadrant/bmc/okr/decision-matrix views
- `openGenericViewTab` type union in `e2e/helpers/dockview.ts` extended with 4 new renderer types
- View selectors added to `SEL.views` in `e2e/helpers/selectors.ts`
- User guide section "5. Business Planning" in `docs/guide/39-mental-model-catalog.md` with type reference tables for all 16 frameworks
- Model Comparison table updated with Business Planning row

## Verification

- `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); assert len([s for s,p,o in g if 'relatedTask' in str(s) or 'relatedGoalOutcome' in str(s) or 'relatedProject' in str(s)]) >= 3"` — cross-model properties exist
- `rg "relatedTask|relatedGoalOutcome|relatedProject" models/business-planning/shapes/business-planning.jsonld` — SHACL shapes reference cross-model properties
- `test -f e2e/tests/36-business-planning/business-planning.spec.ts` — E2E spec exists
- `cd e2e && npx tsc --noEmit` — E2E project type-checks cleanly (full test execution requires Docker stack)
- `rg "Business Planning" docs/guide/39-mental-model-catalog.md | wc -l` returns ≥ 5
- `rg "^## 5\. Business Planning" docs/guide/39-mental-model-catalog.md` — section exists

## Tasks

- [x] **T01: Add cross-model edge definitions to business-planning ontology and shapes** `est:25m`
  - Why: Enables linking framework items to objects in other installed models (bpkm:Task, ppv:GoalOutcome, bpkm:Project), completing the cross-model integration requirement.
  - Files: `models/business-planning/ontology/business-planning.jsonld`, `models/business-planning/shapes/business-planning.jsonld`
  - Do: Add 3 OWL ObjectProperty declarations (`bp:relatedTask`, `bp:relatedGoalOutcome`, `bp:relatedProject`) to the ontology with appropriate domain/range. Add SHACL PropertyShapes on the relevant NodeShapes (EisenhowerItem, FrameworkItem, Objective) with `sh:class` pointing to cross-model type IRIs. Add `bpkm:` and `ppv:` namespace prefixes to the `@context` blocks. Verify JSON-LD parses cleanly via rdflib.
  - Verify: `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g))"` — triple count increases; `rg "relatedTask" models/business-planning/ontology/business-planning.jsonld` returns results
  - Done when: 3 cross-model ObjectProperty declarations in ontology, 3 matching SHACL PropertyShapes in shapes, both files parse without error

- [x] **T02: E2E Playwright tests for business-planning model install and custom renderers** `est:45m`
  - Why: Proves the full vertical — model install, object creation, all 4 custom renderers — works end-to-end in a running Docker stack. Covers BIZ-09 (E2E tests).
  - Files: `e2e/tests/36-business-planning/business-planning.spec.ts`, `e2e/helpers/dockview.ts`, `e2e/helpers/selectors.ts`
  - Do: Extend `openGenericViewTab` renderer union with `'quadrant' | 'bmc' | 'okr' | 'decision-matrix'`. Add view selectors to `SEL.views`. Write single consolidated test: install model → create objects via Command API → set localStorage type preselection → open each of 4 custom view tabs → verify board selectors visible → run cross-model SPARQL query → best-effort cleanup. Follow `mental-model-expansion.spec.ts` patterns. Use generous timeouts (20s) for view rendering.
  - Verify: `cd e2e && npx tsc --noEmit` — type-checks cleanly. Full test: `cd e2e && npx playwright test tests/36-business-planning/ --reporter=list` (requires Docker stack)
  - Done when: Spec file exists, type-checks, and covers model install + 4 custom renderers + SPARQL query

- [x] **T03: User guide documentation for all business planning frameworks** `est:30m`
  - Why: Documents all 16 business planning frameworks with field reference tables, custom renderer descriptions, and cross-model edge documentation. Covers BIZ-10 (documentation).
  - Files: `docs/guide/39-mental-model-catalog.md`
  - Do: Add section `## 5. Business Planning` after existing section 4 (Research Workflow) and before `## Model Comparison`. Include: model metadata (ID, version, namespace), overview, sub-sections grouped by framework category (Prioritization, Strategy, Business Design, Goal Tracking, Resource Management), type reference tables for all 16 frameworks, custom renderer descriptions (quadrant, bmc, okr, decision-matrix), cross-model edges section, SPARQL query examples. Update the Model Comparison table with a Business Planning row.
  - Verify: `rg "^## 5\. Business Planning" docs/guide/39-mental-model-catalog.md` — section exists; `wc -l docs/guide/39-mental-model-catalog.md` ≥ 900 lines
  - Done when: Section 5 documents all 16 frameworks with field tables, the Model Comparison table includes Business Planning

## Files Likely Touched

- `models/business-planning/ontology/business-planning.jsonld`
- `models/business-planning/shapes/business-planning.jsonld`
- `e2e/tests/36-business-planning/business-planning.spec.ts`
- `e2e/helpers/dockview.ts`
- `e2e/helpers/selectors.ts`
- `docs/guide/39-mental-model-catalog.md`

## Observability / Diagnostics

- **Cross-model properties:** `rg "relatedTask|relatedGoalOutcome|relatedProject"` on ontology/shapes files confirms presence; rdflib triple count confirms parse integrity
- **E2E runtime:** Playwright test spec exercises model install, object creation, view rendering, and SPARQL queries in the Docker stack — failures report specific step and selector
- **User guide:** `rg "Business Planning"` with line count confirms section exists with sufficient content
- **Failure visibility:** JSON-LD parse errors surface as rdflib exceptions with line info; TypeScript compile errors from `tsc --noEmit` catch E2E type issues before runtime
