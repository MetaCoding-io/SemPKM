# S05 Research: Cross-Model Integration, E2E Tests & Documentation

**Researched:** 2026-03-23
**Depth:** Light — well-understood work using established patterns from S01-S04 and existing E2E/docs infrastructure.

## Summary

S05 is the capstone slice: cross-model edge definitions in the ontology, E2E Playwright tests covering model install and all 4 custom renderers, and user guide documentation for all 16 business planning frameworks. All three deliverables follow well-proven patterns already in the codebase. No new technology, no risky integration, no novel architecture.

**Cross-model edges:** The edge system (`edge.create` command) already supports arbitrary object-to-object linking via predicate IRIs. "Cross-model edges" means defining OWL ObjectProperty declarations in the business-planning ontology that point to types in other models (bpkm:Task, ppv:GoalOutcome). This is a model archive edit — zero platform code changes.

**E2E tests:** The codebase has 30+ existing E2E specs. The `mental-model-expansion.spec.ts` (M011) already demonstrates the pattern: install model via Admin UI → create objects via Command API → verify in workspace → cleanup. View-specific E2E patterns exist for calendar, map, timeline, kanban. The 4 new renderers (quadrant, bmc, okr, decision-matrix) need the same treatment.

**Documentation:** Chapter 39 (`39-mental-model-catalog.md`) documents all installed models. Currently has 4 models (Basic PKM, CRM, Zettelkasten+, Research). Business Planning would be section 5, following the same field-reference table format. Per KNOWLEDGE entry, three files must stay in sync (README.md, index.html, guide.html) — but chapter 39 already exists in all three, so only the content within the file needs updating.

## Recommendation

Three natural tasks:

1. **T01 — Cross-model edge definitions** (ontology edit): Add OWL ObjectProperty declarations (`bp:relatedTask`, `bp:relatedGoalOutcome`, `bp:relatedProject`) to the business-planning ontology. Add SHACL PropertyShapes so the edge suggestions appear in the SHACL-generated forms. Verify ontology still parses.

2. **T02 — E2E Playwright tests**: One spec file (`e2e/tests/36-business-planning/business-planning.spec.ts`) covering: (a) model install via Admin UI, (b) object creation via Command API for Eisenhower, BMC, OKR, Decision Matrix, (c) quadrant view renders with `.quadrant-board`, (d) BMC view renders with `.bmc-board`, (e) OKR view renders with `.okr-board`, (f) Decision Matrix view renders with `.dm-board`, (g) cross-model SPARQL query returns structured results, (h) cleanup. Needs `openGenericViewTab` TypeScript type union updated to include `'quadrant' | 'bmc' | 'okr' | 'decision-matrix'`.

3. **T03 — User guide documentation**: Add section 5 ("Business Planning") to `docs/guide/39-mental-model-catalog.md` with type reference tables for all 16 frameworks, custom renderer descriptions, and cross-model edge documentation.

## Implementation Landscape

### Cross-Model Edges (T01)

**Where to edit:**
- `models/business-planning/ontology/business-planning.jsonld` — add 3 new OWL ObjectProperty entries with `rdfs:domain` and `rdfs:range` pointing to types in other models
- `models/business-planning/shapes/business-planning.jsonld` — add PropertyShapes on EisenhowerItem/Objective NodeShapes with `sh:class` pointing to cross-model types

**Target edge definitions:**
| Edge Property | Domain | Range | Purpose |
|---|---|---|---|
| `bp:relatedTask` | `bp:EisenhowerItem` | `bpkm:Task` | Link prioritized items to their task tracking |
| `bp:relatedGoalOutcome` | `bp:Objective` | `ppv:GoalOutcome` | Link OKR objectives to PPV goal outcomes |
| `bp:relatedProject` | `bp:FrameworkItem` | `bpkm:Project` | Generic link from any framework item to a project |

**Cross-model IRI references:**
- `bpkm:Task` = `urn:sempkm:model:basic-pkm:Task`
- `bpkm:Project` = `urn:sempkm:model:basic-pkm:Project`
- `ppv:GoalOutcome` = `urn:sempkm:model:ppv:GoalOutcome`

These IRIs are stable — they've been in their respective models since M001/M011.

**No platform code changes needed.** The edge system works with any predicate IRI. The SHACL form generator renders ObjectProperty fields with `sh:class` as reference pickers. The edge.create command accepts any source/target/predicate combination.

### E2E Tests (T02)

**File to create:** `e2e/tests/36-business-planning/business-planning.spec.ts`

**File to modify:** `e2e/helpers/dockview.ts` — add `'quadrant' | 'bmc' | 'okr' | 'decision-matrix'` to the `renderer` type union in `openGenericViewTab()`.

**Pattern to follow:** `e2e/tests/26-mental-models/mental-model-expansion.spec.ts` for model install flow. `e2e/tests/02-views/calendar-view.spec.ts` for view rendering verification.

**Test structure (single consolidated test to stay within rate limits):**
1. Navigate to Admin > Mental Models
2. Install `business-planning` model via UI form (path: `/app/models/business-planning`)
3. Verify model appears in model list
4. Create test objects via Command API (`ownerPage.request.post('/api/commands', ...)`)
   - 1 EisenhowerMatrix + 2 EisenhowerItems (high/high and low/low)
   - 1 BusinessModelCanvas + 1 BMCSection
   - 1 Objective + 1 KeyResult
   - 1 DecisionMatrix + 1 Criterion + 1 Alternative + 1 Score
5. Open quadrant view via `openGenericViewTab('quadrant', '.quadrant-board')` — verify `.quadrant-board` visible
6. Open BMC view via `openGenericViewTab('bmc', '.bmc-board')` — verify `.bmc-board` visible
7. Open OKR view via `openGenericViewTab('okr', '.okr-board')` — verify `.okr-board` visible
8. Open Decision Matrix view via `openGenericViewTab('decision-matrix', '.dm-board')` — verify `.dm-board` visible
9. SPARQL query: `SELECT ?item WHERE { ?item a <urn:sempkm:model:business-planning:EisenhowerItem> }` — verify returns ≥2 results
10. Best-effort cleanup (uninstall model via API)

**Key CSS selectors for view verification:**
| Renderer | Board selector | Item selector |
|---|---|---|
| quadrant | `.quadrant-board` | `.quadrant-cell` |
| bmc | `.bmc-board` | `.bmc-section` |
| okr | `.okr-board` | `.okr-objective-card` |
| decision-matrix | `.dm-board` | `.dm-row` |

**Pre-set type in localStorage before opening view tabs:**
```javascript
localStorage.setItem('sempkm_generic_type_quadrant', 'urn:sempkm:model:business-planning:EisenhowerItem');
localStorage.setItem('sempkm_generic_type_bmc', 'urn:sempkm:model:business-planning:BMCSection');
localStorage.setItem('sempkm_generic_type_okr', 'urn:sempkm:model:business-planning:KeyResult');
localStorage.setItem('sempkm_generic_type_decision-matrix', 'urn:sempkm:model:business-planning:Alternative');
```

**Imports needed:**
```typescript
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';
```

**Selectors to add to `SEL.views`:**
```typescript
quadrantBoard: '.quadrant-board',
quadrantCell: '.quadrant-cell',
bmcBoard: '.bmc-board',
bmcSection: '.bmc-section',
okrBoard: '.okr-board',
okrObjectiveCard: '.okr-objective-card',
dmBoard: '.dm-board',
dmRow: '.dm-row',
```

### Documentation (T03)

**File to edit:** `docs/guide/39-mental-model-catalog.md`

**Structure to add:** Section `## 5. Business Planning` after the existing section 4 (Research Workflow), following the same format:
- Model metadata (ID, version, namespace)
- Overview paragraph
- Sub-sections for each framework group:
  - Prioritization & Decision-Making (Eisenhower Matrix, Decision Matrix)
  - Strategy Analysis (SWOT, Porter's Five Forces, PESTLE, BCG, Ansoff)
  - Business Design (Business Model Canvas, Lean Canvas, Value Chain)
  - Goal Tracking (OKR, Balanced Scorecard)
  - Resource Management (RACI Matrix, Stakeholder Map, Risk Matrix)
- Type reference tables (fields, types, required, description)
- Custom renderer descriptions (quadrant, BMC, OKR, decision-matrix)
- Cross-model edges section
- SPARQL query examples

**Also update:** The Model Comparison table at the bottom of the file needs a Business Planning row.

**Three-file sync check:** Chapter 39 already exists in all three locations (README.md, index.html, guide.html). The content change is within the chapter, not a new chapter addition. No cross-file sync needed.

### Constraints and Risks

- **Docker stack required for E2E:** Tests need the Docker Compose test stack running. The model install path in the container is `/app/models/business-planning` (volume-mounted from `./models`).
- **Rate limiting:** The auth fixture has a magic-link rate limit of 5/minute. Use a single consolidated `test()` block like `mental-model-expansion.spec.ts` does.
- **E2E flakiness:** Custom renderer tabs load content via htmx with lazy-load JS boot. Use generous timeouts (15-20s) for view selectors. The `openGenericViewTab` helper already has a `timeoutMs` parameter.
- **View type pre-selection:** Renderers won't show data unless the type is pre-selected. Use `localStorage.setItem()` before opening the tab (pattern from calendar-view.spec.ts).
- **No drag E2E:** Testing actual HTML5 drag-drop in Playwright within dockview panels is unreliable (per existing cross-view-drag.spec.ts comments). Verify renderer rendering and data display, not drag interaction.

### Verification

- T01: `python3 -c "from rdflib import Graph; g = Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g))"` — count should increase by ~15 triples (3 properties × 5 triples each)
- T01: `rg "relatedTask\|relatedGoalOutcome\|relatedProject" models/business-planning/ontology/business-planning.jsonld` — 3 hits
- T02: `cd e2e && npx playwright test tests/36-business-planning/ --reporter=list` (requires Docker stack)
- T02: Without Docker: verify file compiles with `cd e2e && npx tsc --noEmit tests/36-business-planning/business-planning.spec.ts` (or full project type check)
- T03: `wc -l docs/guide/39-mental-model-catalog.md` — should increase by ~400-600 lines
- T03: `rg "Business Planning" docs/guide/39-mental-model-catalog.md` — at least 1 hit
