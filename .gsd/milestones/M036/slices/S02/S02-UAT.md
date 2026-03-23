# S02: Business Model Canvas — UAT Script

## Preconditions

- Docker stack running (`docker compose up -d`)
- `business-planning` model installed via Admin > Mental Models
- At least one Business Model Canvas with sections exists (seed data provides "SemPKM Business Model" with 9 sections)
- User authenticated in the workspace

---

## Test Case 1: BMC View Renders 9-Box Poster Layout

**Steps:**

1. Navigate to the workspace at `/browser/`
2. Open the explorer sidebar — expand the OBJECTS section
3. Select type "BMC Section" from the type browser (or use the object browser's type filter)
4. Open a view tab for BMC Sections — select the "bmc" renderer from the renderer dropdown (or if auto-detected, it opens directly)
5. Verify the view renders a poster-style grid with 9 labeled sections:
   - **Top row (left to right):** Key Partners, Key Activities, Value Propositions, Customer Relationships, Customer Segments
   - **Middle row:** Key Resources and Channels should be positioned under Key Activities and Customer Relationships respectively
   - **Bottom row:** Cost Structure (left half), Revenue Streams (right half)
6. Each section should have a colored header with the section name and item count badge
7. Each section should contain a textarea with the seed content (3-4 bullet points)

**Expected:** 9-box grid visible with correct section names, color-coded headers, and populated textareas.

---

## Test Case 2: Inline Editing Saves via Command API

**Steps:**

1. With the BMC view open, click into the textarea for the "Value Propositions" section
2. Add a new line: "- Automated SHACL validation"
3. Wait 500ms (debounce timer) or click outside the textarea (blur triggers immediate save)
4. Observe the brief green flash on the section (`.bmc-save-ok` class)
5. Open browser DevTools Network tab — verify a `POST /api/commands` request was sent with:
   - `type: "object.patch"`
   - Property: `urn:sempkm:model:business-planning:sectionContent`
   - Updated content including the new line
6. Reload the page and reopen the BMC view
7. Verify the "Value Propositions" section still contains the added line

**Expected:** Content persists across page reload. Green flash confirms save. Network request shows object.patch command.

---

## Test Case 3: Dark Mode Support

**Steps:**

1. With the BMC view open, toggle to dark mode (Settings or theme toggle)
2. Verify all 9 sections have readable text on dark backgrounds
3. Section headers should have visible accent colors (not washed out)
4. Textareas should have light text on dark backgrounds with visible borders on focus
5. The overall grid background should match the workspace dark theme
6. Toggle back to light mode — verify colors return to pastel tints

**Expected:** All sections readable in dark mode. No white-on-white or dark-on-dark text. Color tints adjust appropriately.

---

## Test Case 4: Empty Section State

**Steps:**

1. Create a new Business Model Canvas via "New Object" with type `bp:BusinessModelCanvas`
2. Create a BMC Section linked to this canvas with `sectionType` = "key-partners" but leave `sectionContent` empty
3. Open the BMC view
4. Verify the "Key Partners" section shows an empty-state hint (italic "No items yet" or similar CSS `:empty` styling)
5. Click into the textarea and type content
6. Verify the section updates and the empty hint disappears

**Expected:** Empty sections are visually distinct. Typing content transitions cleanly from empty to populated state.

---

## Test Case 5: BMC Data Debug Endpoint

**Steps:**

1. In a browser or curl, request: `GET /browser/views/generic/bmc/data?type=urn:sempkm:model:business-planning:BMCSection`
2. Verify the JSON response contains:
   - `sections`: array of 9 objects, each with `type` (kebab-case), `name` (display name), and `items` array
   - `section_types`: dict mapping kebab-case to display names (9 entries)
   - `total`: integer count of all items across sections
3. Verify section ordering follows BMC canonical order: key-partners, key-activities, value-propositions, customer-relationships, customer-segments, key-resources, channels, cost-structure, revenue-streams

**Expected:** JSON endpoint returns structured data matching the 9-section BMC layout.

---

## Test Case 6: Error State — Type Without 9-Value sh:in

**Steps:**

1. Try to open the BMC renderer for a type that is NOT a BMC Section (e.g., a regular bpkm:Project type)
2. The view should display an error message indicating the type doesn't have the required section-type property
3. Verify no JavaScript errors in the console

**Expected:** Graceful error message, not a crash or blank view.

---

## Test Case 7: Dockview Drag Isolation

**Steps:**

1. Open the BMC view in a dockview tab alongside other tabs
2. Click and drag within a BMC section textarea (text selection)
3. Verify the drag does NOT trigger dockview panel detach or reorder
4. Try dragging from a section header area
5. Verify dockview panel behaviour is unaffected by BMC drag events

**Expected:** Text selection and any drag interactions within the BMC view are contained — they do not bubble up to dockview's panel drag system.

---

## Test Case 8: Unit Tests Pass

**Steps:**

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_bmc.py -v`
2. Verify all 31 tests pass
3. Verify test coverage includes:
   - Section detection (10 tests): happy path, keyword preference, rejection, canvas detection
   - SPARQL building (6 tests): structure, scope filter, canvas path
   - Result grouping (15 tests): 9-bucket grouping, ordering, edge cases

**Expected:** 31 passed, 0 failed, 0 errors.

---

## Test Case 9: Model File Integrity

**Steps:**

1. Parse all model files:
   ```
   cd backend && .venv/bin/python -c "
   from rdflib import Graph
   for f in ['ontology', 'shapes', 'views', 'seed']:
       g = Graph()
       g.parse(f'../models/business-planning/{f}/business-planning.jsonld', format='json-ld')
       print(f'{f}: {len(g)} triples')
   "
   ```
2. Verify: ontology ≥ 72 triples, shapes ≥ 287, views ≥ 38, seed ≥ 113
3. Validate manifest: `from app.models.manifest import parse_manifest; parse_manifest(Path('../models/business-planning'))` returns name="Business Planning", version="1.0.0"
4. Verify `sh:in` constraint on `sectionType` has exactly 9 values

**Expected:** All files parse cleanly. Triple counts match. Manifest validates.

---

## Edge Cases

- **Multiple canvases:** If two Business Model Canvases exist, the BMC view should show sections from both (no canvas-scoped filtering in the current UI). Verify items from both canvases appear.
- **Long content:** Enter 20+ lines of text in a section textarea. Verify the textarea expands and the grid layout doesn't break.
- **Concurrent edits:** Open two browser tabs showing the same BMC view. Edit the same section in both. Verify last-write-wins without errors.
- **Responsive layout:** Resize the browser window to < 800px width. Verify the grid collapses to a single-column layout with all 9 sections stacked vertically.
