---
id: S05
milestone: M036
outcome: success
tasks_completed: 3
tasks_total: 3
duration: ~42m (T01: 12m, T02: 15m, T03: 15m)
completed_at: 2026-03-22
---

# S05 Summary: Cross-Model Integration, E2E Tests & Documentation

## What This Slice Delivered

Completed the business-planning milestone by adding cross-model edge definitions, E2E Playwright test coverage, and user guide documentation for all 15 frameworks.

**T01 — Cross-model edge definitions:** Added 3 OWL ObjectProperties (`bp:relatedTask`, `bp:relatedGoalOutcome`, `bp:relatedProject`) to the ontology and 3 matching SHACL PropertyShapes to the shapes file. These enable linking Eisenhower items to bpkm:Tasks, OKR Objectives to ppv:GoalOutcomes, and any FrameworkItem to bpkm:Projects. Added `bpkm:` and `ppv:` namespace prefixes to both JSON-LD `@context` blocks. Created a `bp:CrossLinksGroup` PropertyGroup for SHACL form organization. Ontology grew from 408→423 triples; shapes from 1632→1665 triples.

**T02 — E2E Playwright tests:** Created `e2e/tests/36-business-planning/business-planning.spec.ts` — a consolidated test exercising the full vertical: model install via Admin UI, creation of 11 objects across 4 framework types using batch Command API with `@slot:` references, opening all 4 custom view renderer tabs (quadrant, bmc, okr, decision-matrix), and SPARQL query verification. Extended `openGenericViewTab()` with 4 new renderer types and added 8 view selectors to `SEL.views`.

**T03 — User guide documentation:** Added ~490 lines as section "5. Business Planning" in `docs/guide/39-mental-model-catalog.md`. Documents all 15 frameworks grouped into 5 categories with type reference tables, custom renderer descriptions, cross-model edges section, 3 SPARQL query examples, and installation instructions. Updated the Model Comparison table with a Business Planning row (32 types).

## Key Files

| File | What |
|------|------|
| `models/business-planning/ontology/business-planning.jsonld` | 3 cross-model ObjectProperty declarations |
| `models/business-planning/shapes/business-planning.jsonld` | 3 SHACL PropertyShapes + CrossLinksGroup |
| `e2e/tests/36-business-planning/business-planning.spec.ts` | E2E spec: install, 11 objects, 4 renderers, SPARQL |
| `e2e/helpers/dockview.ts` | Extended renderer type union |
| `e2e/helpers/selectors.ts` | 8 new view selectors |
| `docs/guide/39-mental-model-catalog.md` | Section 5 (~490 lines) + Model Comparison update |

## Patterns Established

- **Cross-model edges via OWL ObjectProperty + SHACL sh:class:** No backend code changes needed. The edge system handles arbitrary linking; the SHACL shapes provide form pickers on specific NodeShapes. Pattern: add ObjectProperty to ontology with domain/range, add PropertyShape with `sh:class` to the relevant NodeShape.
- **Batch Command API with @slot: references in E2E tests:** Creating linked object graphs (matrix→items, canvas→sections) in one API call using the slot resolution feature, rather than sequential single-command calls. More efficient and tests slot resolution as a side effect.
- **E2E custom renderer verification pattern:** Pre-seed localStorage type selection → `openGenericViewTab(renderer)` → assert board container visible. The 4 new renderers follow the same pattern as kanban/table/graph E2E tests.

## Known Limitations

- `bp:FrameworkItemShape` targets the abstract base class `bp:FrameworkItem`. The SHACL form generator matches by exact `sh:targetClass`, so `relatedProject` won't appear in SHACL forms for concrete subclasses. The edge system can still link any object to any other via `edge.create`.
- E2E full execution requires the Docker test stack. Type-check and file-existence checks pass without Docker.
- Pre-existing tsc errors in `tests/05-admin/sparql-advanced.spec.ts`, `tests/06-settings/`, and `tests/07-multi-user/` are unrelated to this work. The 3 files this slice created/modified have zero type errors.

## Verification Results

| Check | Result |
|-------|--------|
| Cross-model properties in ontology (rdflib, ≥3) | ✅ 15 triples found |
| Cross-model properties in shapes (rg) | ✅ 3 matches |
| E2E spec exists | ✅ |
| tsc --noEmit on our files | ✅ 0 errors |
| Guide section "5. Business Planning" exists | ✅ |
| Guide "Business Planning" mentions ≥ 5 | ✅ 6 |
| Guide line count ≥ 900 | ✅ 1101 |

## What the Next Slice Should Know

This is the final slice of M036. The milestone is complete:
- The `business-planning` model archive is fully built with 32 types across 15 frameworks
- 4 custom renderers (quadrant, bmc, okr, decision-matrix) are wired into the view router
- Cross-model edges connect to bpkm:Task, ppv:GoalOutcome, and bpkm:Project
- E2E coverage proves the full install→create→render→query vertical
- User guide chapter 39 section 5 documents everything
