# S01: Eisenhower Matrix — Model Archive + Quadrant Renderer — UAT

**Milestone:** M036
**Written:** 2026-03-23

## UAT Type

- UAT mode: mixed (artifact-driven for model/backend verification, live-runtime for quadrant view and drag interaction)
- Why this mode is sufficient: The model archive and backend wiring can be validated offline via pytest and rdflib parsing. The quadrant view rendering and drag-to-reclassify interaction require a running Docker stack with triplestore.

## Preconditions

- Docker Compose stack running (`docker compose up -d`)
- `business-planning` model archive present at `models/business-planning/` (5 JSON-LD files + manifest.yaml)
- Backend unit tests passing: `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` → 28 passed
- Logged in as an authenticated user

## Smoke Test

1. Navigate to Admin > Mental Models
2. Click "Install" on `business-planning`
3. Navigate to workspace, open Views, select "Eisenhower Item Quadrant" view
4. **Expected:** 2×2 grid with 4 colored quadrants containing seed items

## Test Cases

### 1. Model Installation

1. Navigate to Admin > Mental Models
2. Locate `business-planning` in the available models list
3. Click "Install"
4. **Expected:** Model installs successfully. Status shows "Installed". Version is 1.0.0.
5. Navigate to the workspace object browser
6. **Expected:** "Eisenhower Matrix" and "Eisenhower Item" appear as available types

### 2. SHACL Form Generation for Eisenhower Item

1. Click "New Object" and select "Eisenhower Item" type
2. **Expected:** Form renders with 4 property groups: Basic Info, Classification, Relationships, Metadata
3. Locate the "Urgency" field
4. **Expected:** Dropdown/select with exactly two options: "high" and "low"
5. Locate the "Importance" field
6. **Expected:** Dropdown/select with exactly two options: "high" and "low"
7. Fill in title "Test Item", set urgency="high", importance="low", save
8. **Expected:** Object saves successfully

### 3. Quadrant View Renders Correctly

1. Open the Views section in the workspace sidebar
2. Open a generic view tab and select the "quadrant" renderer for Eisenhower Item type
3. **Expected:** 2×2 grid appears with 4 quadrant cells:
   - Top-left (green): "Do First" (high urgency + high importance) — 2 seed items
   - Top-right (blue): "Schedule" (low urgency + high importance) — 2 seed items
   - Bottom-left (amber): "Delegate" (high urgency + low importance) — 1 seed item
   - Bottom-right (red): "Eliminate" (low urgency + low importance) — 2 seed items
4. Each cell shows a count badge matching the number of items
5. Axis labels are visible: "Urgency →" along the bottom, "↑ Importance" along the left side

### 4. Quadrant Data Endpoint

1. In a terminal or browser: `curl -s http://localhost:3901/browser/views/generic/quadrant/data?type=urn:sempkm:model:business-planning:EisenhowerItem | python3 -m json.tool`
2. **Expected:** JSON response with:
   - `quadrants` array with 4 entries
   - Each quadrant has `x_value`, `y_value`, `label`, and `items` array
   - `axes` object with `x_predicate` containing "urgency" and `y_predicate` containing "importance"
   - `total` count matching sum of all items across quadrants

### 5. Drag-to-Reclassify Interaction

1. Open the quadrant view with Eisenhower items displayed
2. Grab a card from "Do First" (high/high) quadrant
3. Drag it to the "Eliminate" (low/low) quadrant
4. **Expected:** Card moves to the target quadrant immediately (optimistic update). Count badges update (source decrements, target increments).
5. Reload the page and re-open the quadrant view
6. **Expected:** The moved item remains in the "Eliminate" quadrant — the change persisted to RDF

### 6. Drag-to-Reclassify Does Not Interfere with Dockview

1. Open the quadrant view in a dockview tab
2. Start dragging a quadrant card
3. Move the mouse over the dockview tab bar or panel edges
4. **Expected:** Dockview does NOT attempt to detach the panel or show panel drop indicators. The drag stays within the quadrant grid.

### 7. Dark Mode Rendering

1. Toggle dark mode via the user menu theme toggle
2. Open the quadrant view
3. **Expected:** All 4 quadrant cells have distinct tinted backgrounds visible against the dark theme. Card text is clearly readable. Axis labels are visible.
4. Toggle back to light mode
5. **Expected:** Colors return to light-mode tints without flicker

### 8. SPARQL Queryability

1. Open the SPARQL console (Ctrl+J → SPARQL tab)
2. Run: `SELECT ?item ?urgency ?importance WHERE { ?item a <urn:sempkm:model:business-planning:EisenhowerItem> ; <urn:sempkm:model:business-planning:urgency> ?urgency ; <urn:sempkm:model:business-planning:importance> ?importance } ORDER BY ?urgency ?importance`
3. **Expected:** Returns all Eisenhower items with their urgency and importance values. Items dragged between quadrants reflect their updated values.

## Edge Cases

### Type with No Quadrant Axes

1. Open a generic view tab, select "quadrant" renderer, but choose a type that has no `sh:in` properties with exactly 2 values (e.g., a basic-pkm type like "Project")
2. **Expected:** Error message displayed in the view area: descriptive text explaining the type has no quadrant-axis properties. No crash, no blank view.

### Empty Quadrant

1. Create a new Eisenhower Matrix with no items
2. Open the quadrant view filtered to this matrix's items (if scope filtering is available)
3. **Expected:** 4 empty quadrant cells displayed. Each shows "Drag items here" hint text (via CSS :empty pseudo-element). Count badges show 0.

### Rapid Sequential Drags

1. Quickly drag 3 different cards to different quadrants in rapid succession
2. **Expected:** All 3 moves complete. No cards lost, no duplicated cards, count badges accurate after all moves settle.

### Drag Cancel (Drop Outside Grid)

1. Start dragging a card from a quadrant
2. Drop it outside the quadrant grid (e.g., on the toolbar or sidebar)
3. **Expected:** Card returns to its original quadrant. No API call fired. No error in console.

## Failure Signals

- Quadrant view shows blank white area instead of 4-cell grid → CSS not loaded (check `/css/quadrant.css` 404)
- All items in one quadrant / quadrants don't separate → `_detect_quadrant_axes()` failed to find urgency/importance axes (check data endpoint JSON)
- Drag moves card visually but reverts on reload → `object.patch` API call failed (check browser devtools console for "quadrant: failed to patch" error)
- Dockview panel detaches when dragging cards → `stopPropagation()` not firing on dragstart (check quadrant.js loaded)
- "Drag items here" text shows inside cells that have items → CSS `:empty` pseudo-element incorrectly applied (whitespace in cell body)

## Requirements Proved By This UAT

- BIZ-01 (model archive) — Test cases 1, 2, and 8 prove model installs, generates forms, and supports SPARQL queries
- BIZ-02 (quadrant renderer) — Test cases 3, 4, 5, 6, and 7 prove quadrant rendering, data endpoint, drag interaction, dockview isolation, and dark mode

## Not Proven By This UAT

- BIZ-03 through BIZ-10 — BMC renderer, OKR renderer, Decision Matrix renderer, extended frameworks, cross-model edges, E2E Playwright tests, and documentation are all S02-S05 scope
- Model persistence across Docker restart (requires restart test)
- `refresh_artifacts` correctness for business-planning model

## Notes for Tester

- The quadrant data endpoint (`/browser/views/generic/quadrant/data`) is the fastest way to debug data issues — it shows raw JSON with item grouping before the template renders.
- Seed data has 8 items total but some may have been moved by earlier test runs. If counts don't match expected, check the data endpoint for actual distribution.
- The "Test Item" created in test case 2 will appear in the quadrant view if urgency and importance are set.
- Dark mode test should check all 4 quadrant tints are visually distinguishable — the colors are subtle rgba tints, not solid blocks.
