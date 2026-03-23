# S05 UAT: Cross-Model Integration, E2E Tests & Documentation

## Preconditions

- Docker test stack running (`docker compose -f docker-compose.test.yml up -d`)
- `business-planning` model installed via Admin > Mental Models
- `basic-pkm` and `ppv` models also installed (for cross-model edge targets)
- Browser open to SemPKM workspace

---

## Test 1: Cross-Model Edge Properties in SHACL Forms

**Goal:** Verify cross-model link pickers appear in object edit forms.

1. Navigate to workspace, create a new Eisenhower Item (bp:EisenhowerItem)
2. Open the item in edit mode
3. **Expected:** The SHACL form shows a "Cross Links" section (bp:CrossLinksGroup) with a "Related Task" field (bp:relatedTask) that accepts bpkm:Task references
4. Create a bpkm:Task object, then return to the Eisenhower Item edit form
5. Use the "Related Task" reference picker — search for the task
6. **Expected:** The task appears in search results and can be selected
7. Save the Eisenhower Item
8. **Expected:** The Relations panel shows an edge from the Eisenhower Item to the Task

**Edge case:** The `relatedProject` property is on bp:FrameworkItemShape targeting the abstract class. Verify whether it appears in the SHACL form for concrete types like BMCSection — it may not due to exact `sh:targetClass` matching. This is a known limitation.

---

## Test 2: OKR Objective → ppv:GoalOutcome Edge

**Goal:** Verify OKR Objectives can link to PPV GoalOutcome objects.

1. Create a ppv:GoalOutcome object (e.g., "Increase Revenue 20%")
2. Create a bp:Objective (e.g., "Q1 Revenue Growth")
3. Open the Objective in edit mode
4. **Expected:** The form shows a "Related Goal Outcome" field (bp:relatedGoalOutcome)
5. Link it to the GoalOutcome created in step 1
6. Save and verify the edge appears in the Relations panel
7. Run SPARQL: `SELECT ?obj ?goal WHERE { ?obj a <urn:sempkm:model:bp:Objective> ; <urn:sempkm:model:bp:relatedGoalOutcome> ?goal }`
8. **Expected:** Returns the Objective→GoalOutcome pair

---

## Test 3: E2E Test Suite Execution

**Goal:** Verify the Playwright E2E spec passes against a running Docker stack.

1. Ensure Docker test stack is running
2. Run: `cd e2e && npx playwright test tests/36-business-planning/ --reporter=list`
3. **Expected:** All test steps pass:
   - Model install via Admin UI
   - 11 objects created via batch Command API with @slot: references
   - Quadrant view tab opens and shows `.quadrant-board` container
   - BMC view tab opens and shows `.bmc-board` container
   - OKR view tab opens and shows `.okr-board` container
   - Decision Matrix view tab opens and shows `.dm-board` container
   - SPARQL query returns ≥2 EisenhowerItem results
   - Best-effort cleanup runs without crashing

**Edge case:** If the model was already installed from a previous run, the install step should handle "already installed" gracefully (the spec uses try/catch).

---

## Test 4: Quadrant Renderer with Cross-Model Data

**Goal:** Verify cross-model edges don't break quadrant rendering.

1. Create an Eisenhower Matrix with 2 items (one high/high, one low/low)
2. Link one item to a bpkm:Task via bp:relatedTask edge
3. Open the quadrant view for EisenhowerItem type
4. **Expected:** Both items render in their correct quadrants. The linked item shows normally — the cross-model edge doesn't interfere with quadrant placement logic.
5. Drag the linked item from Q4 (low/low) to Q1 (high/high)
6. **Expected:** The item's urgency and importance properties update. The cross-model edge to the Task is preserved.

---

## Test 5: User Guide Content Verification

**Goal:** Verify the user guide documents all frameworks accurately.

1. Open `docs/guide/39-mental-model-catalog.md` or navigate to the in-app guide at `/guide`
2. Find section "5. Business Planning"
3. **Expected:** Section exists with:
   - Model metadata (ID: business-planning, namespace: urn:sempkm:model:bp:)
   - 5 framework categories (Prioritization, Strategy, Business Design, Goal Tracking, Resource Management)
   - 15 framework sub-sections, each with container and item type reference tables
   - 4 custom renderer descriptions (quadrant, bmc, okr, decision-matrix)
   - Cross-model edges table listing relatedTask, relatedGoalOutcome, relatedProject
   - 3 SPARQL query examples
4. Scroll to the Model Comparison table at the bottom of the chapter
5. **Expected:** Business Planning row present showing 32 types

**Edge case:** The guide documents 15 frameworks (not 16). Eisenhower, Decision Matrix, SWOT, Porter, PESTLE, BCG, Ansoff, BMC, Lean Canvas, Value Chain, OKR, Balanced Scorecard, RACI, Stakeholder Map, Risk Matrix.

---

## Test 6: SPARQL Cross-Framework Queries

**Goal:** Verify SPARQL returns structured data across multiple framework types.

1. Create objects of different framework types (at least 2 Eisenhower Items and 1 Objective with a KeyResult)
2. Run SPARQL: `SELECT ?item ?urgency ?importance WHERE { ?item a <urn:sempkm:model:bp:EisenhowerItem> ; <urn:sempkm:model:bp:urgency> ?urgency ; <urn:sempkm:model:bp:importance> ?importance }`
3. **Expected:** Returns rows with urgency/importance values for each Eisenhower Item
4. Run SPARQL: `SELECT ?obj ?kr ?progress WHERE { ?obj a <urn:sempkm:model:bp:Objective> . ?kr <urn:sempkm:model:bp:forObjective> ?obj ; <urn:sempkm:model:bp:currentValue> ?progress }`
5. **Expected:** Returns KeyResult progress data linked to the Objective
6. Run a cross-model query: `SELECT ?item ?task WHERE { ?item a <urn:sempkm:model:bp:EisenhowerItem> ; <urn:sempkm:model:bp:relatedTask> ?task . ?task a <urn:sempkm:model:bpkm:Task> }`
7. **Expected:** Returns items linked to Tasks (if edges were created in Test 4)

---

## Test 7: TypeScript Type Safety

**Goal:** Verify E2E helpers compile cleanly after extensions.

1. Run: `cd e2e && npx tsc --noEmit 2>&1 | grep -E "36-business-planning|helpers/dockview|helpers/selectors"`
2. **Expected:** Zero output (no errors in our files)
3. Verify renderer type union: `rg "'quadrant' | 'bmc' | 'okr' | 'decision-matrix'" e2e/helpers/dockview.ts`
4. **Expected:** One match showing the extended union type
5. Verify selectors: `rg "quadrantBoard|bmcBoard|okrBoard|dmBoard" e2e/helpers/selectors.ts`
6. **Expected:** 4 matches, one for each custom renderer board selector
