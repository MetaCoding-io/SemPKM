# S02 UAT: Data-Driven Widget Types (stat-card, chart, heading)

## Preconditions

- Docker stack is running (`docker compose up -d`)
- At least one Mental Model installed with some objects (e.g., basic-pkm with a few Projects)
- User is logged in and can access the workspace

---

## Test 1: Stat-Card Block — Live SPARQL Metric

**Goal:** Verify stat-card renders a live number from a SPARQL count query.

1. Open the dashboard builder (create a new dashboard or edit an existing one)
2. In the block palette, locate **Stat Card** in the "Data" category — it should have a `hash` icon
3. Click to add a stat-card block to the canvas
4. In the config panel, enter:
   - **Query:** `SELECT (COUNT(?s) AS ?count) WHERE { ?s a ?type }`
   - **Label:** `Total Objects`
   - **Icon:** `database`
   - **Color:** `#4e79a7`
5. Save the dashboard
6. Open the dashboard page (viewer)

**Expected:**
- The stat-card shows a large number (the actual object count from the triplestore)
- Below the number, the label "Total Objects" appears in muted text
- A Lucide `database` icon appears alongside the metric
- The card has the configured color accent
- The card occupies roughly 3×2 grid cells (default dimensions)

---

## Test 2: Stat-Card Error Handling

**Goal:** Verify stat-card gracefully handles invalid SPARQL.

1. Edit the dashboard, add a stat-card with:
   - **Query:** `SELECT INVALID SPARQL`
   - **Label:** `Broken`
2. Save and view the dashboard

**Expected:**
- The stat-card shows "Query Error" text (not a blank block or server error page)
- The block has the `.dashboard-block-error` CSS class (inspect via browser DevTools)
- Backend logs show a `logger.warning` with the query text and error message

---

## Test 3: Chart Block — Bar Chart from SPARQL

**Goal:** Verify chart block renders a Chart.js bar chart from SPARQL results.

1. In the dashboard builder, locate **Chart** in the "Data" category — it should have a `bar-chart-2` icon
2. Add a chart block to the canvas
3. In the config panel, enter:
   - **Query:** `SELECT ?type (COUNT(?s) AS ?count) WHERE { ?s a ?type } GROUP BY ?type ORDER BY DESC(?count) LIMIT 10`
   - **Chart Type:** Bar
   - **Label Variable:** (leave blank — defaults to first SPARQL variable)
   - **Value Variable:** (leave blank — defaults to second SPARQL variable)
4. Save and view the dashboard

**Expected:**
- A Chart.js bar chart renders with type IRIs on the X-axis and counts on the Y-axis
- The chart uses the 10-color palette (blue, orange, red, teal, etc.)
- The chart is responsive — resizing the browser or the GridStack widget resizes the chart
- The chart occupies roughly 6×4 grid cells (default dimensions)
- Axis labels use theme-appropriate text colors (not hard-white or hard-black)

---

## Test 4: Chart Block — Pie Chart Variant

**Goal:** Verify pie/doughnut chart types work correctly.

1. Add a chart block, same query as Test 3
2. Set **Chart Type:** to `pie`
3. Save and view

**Expected:**
- A pie chart renders (not a bar chart)
- No axis scales are shown (pie/doughnut charts should omit x/y axes)
- Each slice has a different color from the palette

---

## Test 5: Chart Error Handling

**Goal:** Verify chart gracefully handles SPARQL failures.

1. Add a chart block with **Query:** `BROKEN QUERY`
2. Save and view

**Expected:**
- The chart block shows "Chart Error" text
- The block has `.dashboard-block-error` class
- Backend logs include a warning with dashboard_id and query text

---

## Test 6: Heading Block — Section Labels

**Goal:** Verify heading block renders styled text at configurable levels.

1. In the builder palette, locate **Heading** in the "Layout" category — `type` icon
2. Add a heading block
3. In the config panel, enter:
   - **Text:** `My Dashboard Section`
   - **Level:** h2
4. Save and view

**Expected:**
- An `<h2>` element renders with text "My Dashboard Section"
- The heading spans the full width (default 12×1 cells)
- Changing level to h1 produces a larger heading; h3/h4 produce smaller ones
- Text is HTML-escaped (entering `<script>alert(1)</script>` renders as literal text, not executed)

---

## Test 7: Builder Config Panels

**Goal:** Verify all 3 new block types have functional config panels in the builder.

1. Open dashboard builder
2. Add each new block type and verify its config panel:
   - **Stat-card:** query textarea, label input, icon input, color input
   - **Chart:** query textarea, chart_type select (bar/line/pie/doughnut), label_var input, value_var input
   - **Heading:** text input, level select (h1/h2/h3/h4)
3. For each: fill in config, save dashboard, reopen builder

**Expected:**
- Config values persist after save/reopen
- Query textarea shows SPARQL placeholder text
- Chart type select has exactly 4 options
- Heading level select has exactly 4 options (h1-h4)

---

## Test 8: Mixed Dashboard

**Goal:** Verify all block types coexist on a single dashboard.

1. Create a dashboard with:
   - 1 heading block ("Overview")
   - 1 stat-card block (object count query)
   - 1 chart block (type distribution query)
   - 1 markdown block (existing type from S01)
   - 1 view-embed block (existing type from S01)
2. Arrange blocks via drag-and-resize
3. Save and reopen

**Expected:**
- All 5 blocks render correctly
- Layout positions are preserved after save/reopen
- No block types interfere with each other's rendering
- GridStack drag-and-resize works on all blocks

---

## Test 9: Chart.js Global Availability

**Goal:** Verify Chart.js is loaded globally and available for chart blocks.

1. Open any page in the application
2. Open browser DevTools console
3. Type: `typeof Chart`

**Expected:**
- Returns `"function"` (not `"undefined"`)
- Chart.js is loaded from CDN in both dev and production modes

---

## Test 10: Theme Compatibility

**Goal:** Verify widgets look correct in both light and dark themes.

1. Create a dashboard with stat-card and chart blocks
2. View in light theme
3. Switch to dark theme

**Expected:**
- Stat-card text is readable in both themes (uses CSS color variables)
- Chart axis labels and grid lines adapt to theme (use CSS custom properties)
- Chart palette colors are visible against both light and dark backgrounds
- No hard-coded white/black colors that become invisible in one theme

---

## Edge Cases

- **Empty SPARQL results:** Stat-card with a query returning zero rows should show a value (possibly blank/0), not crash
- **Non-numeric chart values:** Chart block with non-numeric SPARQL results should coerce to 0 (float fallback)
- **Very long heading text:** Should not break layout — text should wrap or overflow gracefully
- **Missing config keys:** Blocks with partial config (e.g., stat-card with query but no label) should render without error
- **XSS in heading text:** `<img src=x onerror=alert(1)>` in heading text should be HTML-escaped, not rendered as HTML
