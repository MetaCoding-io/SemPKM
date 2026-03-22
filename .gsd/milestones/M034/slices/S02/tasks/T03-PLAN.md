---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T03: E2E test proving timeline renders with bars and dependencies

**Slice:** S02 — Timeline / Gantt View
**Milestone:** M034

## Description

Write a Playwright E2E spec that proves the full pipeline: SPARQL → JSON → Frappe Gantt rendering. The test opens the timeline view via `openGenericViewTab('timeline')`, verifies task bars and dependency arrows render, and tests zoom level switching. This is the slice's integration proof — without it, visual rendering correctness is unverified.

## Steps

1. **Add timeline selectors to `e2e/helpers/selectors.ts`**:
   - Add to `SEL.views`: `timeline: '[data-testid="timeline-view"]'`, `timelineBar: '.bar-wrapper'`, `timelineArrow: '.arrow'`.

2. **Write `e2e/specs/timeline.spec.ts`**:
   - Import helpers: `SEL` from selectors, `openGenericViewTab` from `e2e/helpers/dockview.ts`, standard test fixtures.
   - **Test: "timeline view renders task bars"**
     - Navigate to workspace (`/browser/`).
     - Call `openGenericViewTab(page, 'timeline', '[data-testid="timeline-view"]')` — this opens an unscoped timeline. The type filter pills should show; the backend will prompt "Select a type" or show a default.
     - If a type select is needed, select `bpkm:Task` type from the type filter pills. The basic-pkm seed data includes tasks with `bpkm:dueDate` which `_detect_date_fields()` picks up.
     - Wait for `.gantt-container` to be visible (Frappe Gantt rendered).
     - Assert: at least one `.bar-wrapper` element exists (task bars).
   - **Test: "timeline shows dependency arrows"**
     - Same setup as above (timeline with bpkm:Task).
     - The seed data includes `bpkm:seed-task-write-guide` → `dependsOn` → `bpkm:seed-task-review-pr` (or similar). If both tasks appear on timeline, an arrow should connect them.
     - Assert: at least one `.arrow` SVG path element exists.
     - Note: If seed data doesn't have enough tasks with both dates AND dependencies visible, this test may need to create tasks first via the API. Check seed data carefully — `seed-task-fix-validation` has `dependsOn` but needs `dueDate`.
   - **Test: "zoom level changes"**
     - After timeline renders, find the view mode selector (Frappe Gantt adds a `select` or button group for view modes).
     - Change zoom to "Month" — the chart re-renders with wider columns.
     - Assert: the chart container is still visible (no crash on zoom change).
   - Use `test.describe('Timeline View')` to group all tests.
   - Each test should have proper cleanup / be independent (each uses its own page navigation).

3. **Run and iterate** — `cd e2e && npx playwright test specs/timeline.spec.ts --headed` to debug visually, then `npx playwright test specs/timeline.spec.ts` for CI mode. Fix any selector issues discovered during real browser testing.

## Must-Haves

- [ ] Timeline selectors added to `SEL.views`
- [ ] E2E test confirms task bars render in the Gantt chart
- [ ] E2E test confirms dependency arrows render
- [ ] E2E test confirms zoom level change doesn't crash

## Verification

- `cd e2e && npx playwright test specs/timeline.spec.ts` — all tests pass
- Tests are independent and don't rely on ordering

## Inputs

- `e2e/helpers/selectors.ts` — existing `SEL.views` object to extend
- `e2e/helpers/dockview.ts` — `openGenericViewTab()` helper function
- `backend/app/templates/browser/timeline_view.html` — T02 created this template with `data-testid="timeline-view"`
- `backend/app/views/router.py` — T01 registered the timeline renderer
- `models/basic-pkm/seed/basic-pkm.jsonld` — seed task data with `bpkm:dependsOn` and `bpkm:dueDate`

## Expected Output

- `e2e/specs/timeline.spec.ts` — Playwright E2E spec with 3 tests (bars, arrows, zoom)
- `e2e/helpers/selectors.ts` — timeline selectors added to `SEL.views`
