---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M032

## Success Criteria Checklist

- [x] **A dashboard with a stat-card block shows a live SPARQL-derived count that updates on page load** — evidence: `_executeSparqlWidgets()` in workspace.js POSTs to `/api/sparql`, populates `[data-stat-target]` element. E2E test `stat-card renders live SPARQL count` passes. 28 backend render tests in test_data_widgets.py pass.
- [x] **A dashboard with a chart block renders a bar/line/pie Chart.js visualization from SPARQL query results** — evidence: `_initChartBlocks()` lazy-loads Chart.js from jsdelivr CDN, creates Chart instances with bar/line/pie support. E2E test `chart block renders Chart.js visualization` passes.
- [x] **The sparql-result block actually executes its configured query and displays a results table** — evidence: `_executeSparqlWidgets()` handles `[data-sparql-table]` elements, builds `<table>` from SPARQL bindings. Render test confirms `data-sparql-query` + `data-sparql-table` attributes emitted.
- [x] **The markdown block renders full markdown via marked.js** — evidence: `_renderMarkdownBlocks()` reads raw markdown from `<script type="text/plain" class="md-source">`, renders via `marked.parse()` + `DOMPurify.sanitize()`. Render tests confirm `data-md-block` attribute emitted.
- [x] **A heading block displays configurable title/subtitle text at the chosen heading level** — evidence: heading BlockTypeSpec registered (12×2), render_block emits heading HTML. E2E test `heading block renders configured text` passes.
- [x] **The dashboard builder palette lists all new block types with working config forms** — evidence: `getTypeConfigHTML()` in dashboard_builder.html has cases for `form-group`, `stat-card`, `chart`, `heading`. All 10 types registered in BLOCK_REGISTRY.
- [x] **A form-group block creates multiple linked objects in one submission, with slot-based IRI resolution** — evidence: `slot_map` accumulator in commands/router.py resolves `@slot:name` references. `_submitFormGroup()` in workspace.js collects sub-form data and POSTs batch payload. 28 form-group tests pass (15 unit + 8 render + 5 integration).
- [x] **Existing dashboards continue to render correctly with no migration required** — evidence: 27/27 test_dashboard.py tests pass. Guide notes backward-compatible CSS Grid layouts.

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Form-group block with slot IRI resolution, builder config, SHACL sub-forms | form-group type registered (7th), @slot:name resolution in batch commands, builder config UI with slot/edge management, template with htmx-loaded sub-forms, _submitFormGroup() JS. 28 tests pass. | pass |
| S02 | stat-card, chart, heading block types + markdown/sparql-result fixes, builder config, frontend JS | 3 new types registered (total 10), render_block handlers for all, _executeSparqlWidgets/_initChartBlocks/_renderMarkdownBlocks JS, Chart.js lazy CDN loading, builder config forms. 28 render tests + 38 registry tests pass. | pass |
| S03 | E2E Playwright spec + user guide chapter 28 | 4 E2E test cases (stat-card, chart, heading, multi-block), dashboard selectors in selectors.ts, openDashboardTab helper. Guide rewritten with all 10 block types, GridStack, data widgets, form groups. | pass |

## Cross-Slice Integration

**S01 → S03:** form-group block type available and registered. E2E spec does not test form-group submission (requires running triplestore with model data) — backend tests cover this path. Acceptable gap.

**S02 → S03:** All three new block types tested in E2E spec. `waitForStatCardValue()` and `waitForChartRendered()` correctly treat `data-*-loaded` as dedup guards rather than readiness signals, as documented in S02's forward intelligence.

**Boundary map alignment:** All produces/consumes match actuals. No mismatches found.

## Requirement Coverage

- **DASH-01** (Dashboard block types): Advanced from 6→10 types. All 10 registered and rendering.
- **BLK-01 through BLK-05, BLK-07** (individual block types): All delivered via S01/S02.
- **BLK-08** (Chart.js lazy load): Confirmed — `_ensureChartJs()` with singleton CDN loading.
- **BLK-10** (E2E tests): 4 test cases in `e2e/tests/45-dashboard-blocks/`.
- **BLK-11** (User guide): Chapter 28 rewritten with all 10 types documented.
- **BLK-06** (JSON Schema formalization): Explicitly left for later per roadmap.
- **BLK-09** (Viewer inline editing): Explicitly left for later per roadmap.

No unaddressed active requirements found for this milestone's scope.

## Known Issues (non-blocking)

1. **3 pre-existing test failures in test_dashboard_builder.py** — layout radio button assertions broken since prior GridStack migration. Not introduced by M032. Confirmed in both S01 and S02 summaries.
2. **E2E does not cover form-group submission** — requires triplestore with installed model for SHACL form rendering. Backend integration tests (5 tests in test_form_group.py) cover the batch submission + slot resolution path.
3. **Chart.js CDN dependency** — charts won't render offline. Acceptable for current deployment model.
4. **Multiple form-group blocks in builder** would have ID collisions (`#fg-slots-list`). Not a problem with current single-block-at-a-time editing UX.

## Verdict Rationale

All 8 success criteria are met with evidence from test results, code inspection, and E2E verification. All 3 slices delivered their claimed outputs. Cross-slice integration points align. 121 backend tests pass (28 form-group + 38 registry + 27 dashboard + 28 data-widgets). 4 E2E test cases cover the critical rendering paths. The 3 pre-existing builder test failures and the form-group E2E coverage gap are documented but do not represent M032 regressions.

Verdict: **needs-attention** — the milestone is complete and all success criteria are met. The pre-existing builder test failures (3) should be addressed in a future maintenance pass but do not block M032 completion.

## Remediation Plan

None required. The needs-attention items are pre-existing tech debt, not M032 gaps.
