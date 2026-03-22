---
estimated_steps: 5
estimated_files: 4
skills_used:
  - best-practices
  - test
---

# T01: Register stat-card, chart, heading blocks and fix markdown/sparql-result render handlers

**Slice:** S02 — Data-Driven Widgets (stat-card, chart, heading) + Block Fixes
**Milestone:** M032

## Description

Add three new block types to the BlockRegistry (stat-card, chart, heading) and fix two existing render_block handlers (markdown, sparql-result). This is the backend foundation — all new types need registry entries so they appear in the builder palette and pass validation, and the render_block function needs to emit HTML with correct `data-*` attributes for frontend JS pickup in T02.

The markdown block currently uses `html.escape()` + paragraph splitting — no real markdown rendering. The fix: emit raw content inside a `<script type="text/plain">` tag for client-side `marked.js` parsing.

The sparql-result block currently emits `data-query` but no JS executes it. The fix: change to `data-sparql-query` (unified attribute name) and add `data-sparql-table` for the frontend to distinguish table rendering from scalar stat rendering.

## Steps

1. **Register 3 new block types in `backend/app/dashboard/registry.py`:**
   - `stat-card`: category="data", icon="hash", config_schema={"query": str, "label": str, "icon": str, "color": str}, default_w=3, default_h=2
   - `chart`: category="data", icon="bar-chart-3", config_schema={"query": str, "chart_type": str, "label": str}, default_w=6, default_h=4
   - `heading`: category="content", icon="heading", config_schema={"text": str, "level": str, "subtitle": str, "align": str}, default_w=12, default_h=2
   - Add them inside `_build_default_registry()`, before the `return` statement. Update the docstring from "7 built-in" to "10 built-in".

2. **Add render_block handlers in `backend/app/dashboard/router.py`:**
   - `stat-card`: Return `<div class="dashboard-block dashboard-block-stat-card" data-sparql-query="ESCAPED_QUERY">` containing: `.stat-card-label` span, `.stat-card-icon` span with `<i data-lucide="ICON">`, `.stat-card-value[data-stat-target]` span showing "…" placeholder. HTML-escape the query via `html.escape(query, quote=True)`. Apply optional inline color style on the value span if `config.color` is set.
   - `chart`: Return `<div class="dashboard-block dashboard-block-chart" data-chart-query="ESCAPED_QUERY" data-chart-type="TYPE">` containing `<canvas class="chart-canvas"></canvas>` and a `.chart-label` span if label is set. Default chart_type to "bar".
   - `heading`: Return `<div class="dashboard-block dashboard-block-heading" style="text-align:ALIGN">` containing `<hN>TEXT</hN>` (N from config.level, default "2", clamped to 1-4) and optional `<p class="heading-subtitle">SUBTITLE</p>`. HTML-escape text and subtitle.

3. **Fix markdown render_block handler:**
   - Replace the current `html.escape()` + paragraph-split logic with: emit `<div class="dashboard-block dashboard-block-markdown" data-md-block>` containing `<script type="text/plain" class="md-source">CONTENT</script>` and a `<div class="md-rendered">Loading…</div>`. The raw markdown content goes inside the script tag — browsers don't execute `type="text/plain"` scripts, and the content doesn't need HTML escaping inside a script tag.

4. **Fix sparql-result render_block handler:**
   - Change `data-query` to `data-sparql-query` (unified attribute for frontend JS). Add `data-sparql-table` attribute to flag table rendering mode. Keep the label span. Emit a `<div class="sparql-table-container">` placeholder for the table. HTML-escape the query via `html.escape(query, quote=True)`.

5. **Update `backend/tests/test_block_registry.py`:**
   - Add "stat-card", "chart", "heading" to `EXPECTED_TYPES` set.
   - Update `test_all_seven_types_registered` → rename to `test_all_ten_types_registered` (or just update the set — the name is cosmetic).
   - Update `test_all_specs_returns_all` assertion from `len(specs) == 7` to `len(specs) == 10`.
   - Add parametrized tests for new types: verify category, icon, config_schema keys, default_w, default_h.

6. **Create `backend/tests/test_data_widgets.py`:**
   - Test render_block output for each of the 5 block types (stat-card, chart, heading, fixed markdown, fixed sparql-result).
   - For each: create a mock dashboard with one block, call the render_block endpoint, assert response contains expected HTML attributes and structure.
   - Use the existing test patterns from `test_dashboard.py` (TestClient, mock data, etc.).
   - Key assertions: stat-card has `data-sparql-query` and `data-stat-target`, chart has `data-chart-query` and `data-chart-type` and `<canvas>`, heading has the right `<h2>` tag, markdown has `<script type="text/plain"` and `data-md-block`, sparql-result has `data-sparql-query` and `data-sparql-table`.

## Must-Haves

- [ ] stat-card, chart, heading registered in BLOCK_REGISTRY with correct config schemas
- [ ] render_block returns HTML with data-sparql-query for stat-card
- [ ] render_block returns HTML with data-chart-query, data-chart-type, canvas for chart
- [ ] render_block returns HTML with configurable heading level (h1-h4) for heading
- [ ] markdown render_block uses script type="text/plain" + data-md-block (not html.escape)
- [ ] sparql-result render_block uses data-sparql-query + data-sparql-table (not data-query)
- [ ] All SPARQL query text in data attributes is HTML-escaped via html.escape(query, quote=True)
- [ ] test_block_registry.py passes with 10 types
- [ ] test_data_widgets.py passes with render output assertions
- [ ] Existing test_dashboard.py and test_dashboard_builder.py pass unchanged

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_block_registry.py -v` — all pass, 10 types
- `cd backend && .venv/bin/python -m pytest tests/test_data_widgets.py -v` — all pass
- `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py tests/test_dashboard_builder.py -v` — existing tests pass (regression guard)

## Inputs

- `backend/app/dashboard/registry.py` — existing BlockRegistry with 7 types, add 3 new
- `backend/app/dashboard/router.py` — existing render_block with 7 branches, add 3 new + fix 2
- `backend/tests/test_block_registry.py` — existing registry tests, update counts and add new type checks
- `backend/tests/test_dashboard.py` — existing 27 dashboard tests (regression guard, do not modify)
- `backend/tests/test_dashboard_builder.py` — existing 9 builder tests (regression guard, do not modify)

## Expected Output

- `backend/app/dashboard/registry.py` — 10 block types registered
- `backend/app/dashboard/router.py` — render_block handles stat-card, chart, heading; markdown and sparql-result fixed
- `backend/tests/test_block_registry.py` — updated for 10 types
- `backend/tests/test_data_widgets.py` — new test file with render output assertions for 5 block types
