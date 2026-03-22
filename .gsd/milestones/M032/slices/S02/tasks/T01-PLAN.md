---
estimated_steps: 4
estimated_files: 3
skills_used:
  - best-practices
  - test
---

# T01: Register stat-card, chart, heading block types with builder config panels and tests

**Slice:** S02 — Data-Driven Widget Types (stat-card, chart, heading)
**Milestone:** M032

## Description

Register three new block types in the `BLOCK_REGISTRY` singleton, add their config panels to the dashboard builder template, and update unit tests to cover the expanded registry. This is the data-model foundation — without these registrations, the renderer (T02) can't validate or render the new types.

The `BLOCK_REGISTRY` is in `backend/app/dashboard/registry.py`. It currently has 6 types registered in `_build_default_registry()`. Add 3 more `register()` calls at the end of that function.

The builder config panels live in `getTypeConfigHTML()` in `dashboard_builder.html` (line ~110). Add 3 new `case` branches in the `switch` statement. Each config panel uses `data-key` attributes on inputs — the existing builder save logic reads these generically.

The test file `backend/tests/test_block_registry.py` has `EXPECTED_TYPES` with 6 entries and tests that assert on that count.

## Steps

1. **Add 3 block type registrations in `registry.py`** at the end of `_build_default_registry()`, before `return registry`:
   - `stat-card`: label="Stat Card", icon="hash", category="data", config_schema={"query": str, "label": str, "icon": str, "color": str}, default_w=3, default_h=2
   - `chart`: label="Chart", icon="bar-chart-2", category="data", config_schema={"query": str, "chart_type": str, "label_var": str, "value_var": str}, default_w=6, default_h=4
   - `heading`: label="Heading", icon="type", category="layout", config_schema={"text": str, "level": str}, default_w=12, default_h=1

2. **Add 3 config panel cases to `getTypeConfigHTML()` in `dashboard_builder.html`**:
   - `stat-card`: SPARQL query textarea (`data-key="query"`, rows=3), label text input (`data-key="label"`), icon text input (`data-key="icon"`, placeholder="Lucide icon name"), color text input (`data-key="color"`, placeholder="#hex or CSS var")
   - `chart`: SPARQL query textarea (`data-key="query"`, rows=3), chart_type select (`data-key="chart_type"`) with options bar/line/pie/doughnut, label_var input (`data-key="label_var"`, placeholder="SPARQL variable for labels"), value_var input (`data-key="value_var"`, placeholder="SPARQL variable for values")
   - `heading`: text input (`data-key="text"`, placeholder="Heading text"), level select (`data-key="level"`) with options h1/h2/h3/h4 (h2 selected by default)

   All inputs must use `escapeAttr()` and `escapeHtml()` for pre-populating values from `config`. Follow the exact HTML patterns used by existing cases (e.g., `sparql-result` for textarea, `markdown` for simple textarea).

3. **Update `test_block_registry.py`**:
   - Change `EXPECTED_TYPES` set to include "stat-card", "chart", "heading" (9 total)
   - Change `test_all_six_types_registered` → `test_all_nine_types_registered` (rename + assert count)
   - Change `test_all_specs_returns_all` assertion from `len(specs) == 6` to `len(specs) == 9`
   - Add parameterized validation test cases for new types:
     - stat-card with valid config `{"query": "SELECT ...", "label": "Count"}` passes
     - chart with valid config `{"query": "SELECT ...", "chart_type": "bar"}` passes
     - heading with valid config `{"text": "Overview", "level": "h2"}` passes
   - Add negative test: stat-card with `{"query": 42}` → ValueError (wrong type)

4. **Run tests to verify**: `cd backend && python -m pytest tests/test_block_registry.py -v`

## Must-Haves

- [ ] `BLOCK_REGISTRY.all_types()` returns exactly 9 types: the original 6 plus stat-card, chart, heading
- [ ] stat-card is category="data", chart is category="data", heading is category="layout"
- [ ] `getTypeConfigHTML("stat-card", {...})` returns HTML with `data-key="query"`, `data-key="label"`, `data-key="icon"`, `data-key="color"` elements
- [ ] `getTypeConfigHTML("chart", {...})` returns HTML with `data-key="query"`, `data-key="chart_type"` (select), `data-key="label_var"`, `data-key="value_var"` elements
- [ ] `getTypeConfigHTML("heading", {...})` returns HTML with `data-key="text"`, `data-key="level"` (select) elements
- [ ] All unit tests pass with updated expected counts

## Verification

- `cd backend && python -m pytest tests/test_block_registry.py -v` — all tests pass
- `python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; types = BLOCK_REGISTRY.all_types(); assert len(types) == 9; assert 'stat-card' in types; assert 'chart' in types; assert 'heading' in types; print('OK')"` — run from `backend/` directory
- `grep -c "data-key" backend/app/templates/browser/dashboard_builder.html` — count increases by ~10 (4 stat-card + 4 chart + 2 heading keys)

## Inputs

- `backend/app/dashboard/registry.py` — existing registry with 6 block types to extend
- `backend/app/templates/browser/dashboard_builder.html` — existing builder template with `getTypeConfigHTML()` switch statement
- `backend/tests/test_block_registry.py` — existing test file with 6-type assertions

## Expected Output

- `backend/app/dashboard/registry.py` — 3 new `register()` calls added (9 total types)
- `backend/app/templates/browser/dashboard_builder.html` — 3 new `case` branches in `getTypeConfigHTML()`
- `backend/tests/test_block_registry.py` — updated expected counts and new test cases for 9 types

## Observability Impact

- **Signals changed:** `BLOCK_REGISTRY.all_types()` now returns 9 types (was 6). Any code iterating types or checking counts will see the expanded set.
- **Inspection:** `python3 -c "from app.dashboard.registry import BLOCK_REGISTRY; print(BLOCK_REGISTRY.all_types())"` from `backend/` shows all registered types.
- **Failure visibility:** `validate_block()` now rejects non-string config values for new types (stat-card query, chart chart_type, heading text) with descriptive `ValueError` messages.
- **Test surface:** 44 unit tests (was 30) covering all 9 types, including negative validation cases for new types.
