---
id: T03
parent: S02
milestone: M034
provides:
  - E2E Playwright spec (3 tests) proving timeline Gantt rendering, dependency arrows, and zoom switching
  - Timeline selectors in SEL.views for reuse by future tests
  - 'timeline' added to openGenericViewTab renderer type union
key_files:
  - e2e/tests/02-views/timeline.spec.ts
  - e2e/helpers/selectors.ts
  - e2e/helpers/dockview.ts
key_decisions:
  - Tests create tasks via command API with bpkm:scheduledStart (not bpkm:dueDate) because _detect_date_fields() picks scheduledStart first by priority
  - Arrow assertion uses state:'attached' instead of visibility check because Frappe Gantt SVG <g class="arrow"> elements are reported as hidden by Playwright despite rendering visually
  - Test file placed at e2e/tests/02-views/timeline.spec.ts following the existing view test directory convention, not e2e/specs/ as the plan suggested
patterns_established:
  - Timeline date field priority: scheduledStart > startDate > dueDate — test data must use the property that _detect_date_fields picks first for the type's shape
  - SVG sub-elements in Playwright should use state:'attached' not visibility assertions
observability_surfaces:
  - Playwright trace zips and screenshots in test-results/ on failure
  - Console log filtering via [timeline] prefix in headed mode for debugging
  - Run `cd e2e && npx playwright test tests/02-views/timeline.spec.ts --project chromium` for quick verification
duration: 25m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: E2E test proving timeline renders with bars and dependencies

**Added 3-test Playwright E2E spec verifying Frappe Gantt bar rendering, dependency arrows, and zoom level switching for the timeline view**

## What Happened

Created `e2e/tests/02-views/timeline.spec.ts` with three tests:

1. **"timeline view renders task bars"** — Creates a task with `scheduledStart`+`scheduledEnd` via command API, opens timeline with Task type pre-selected via localStorage, waits for Frappe Gantt CDN load and `.gantt-container`, asserts `.bar-wrapper` elements exist.

2. **"timeline shows dependency arrows"** — Creates two tasks with `scheduledStart` dates and a `bpkm:dependsOn` edge, opens timeline, asserts `.arrow` SVG group elements exist in DOM (using `state:'attached'` since Playwright reports SVG groups as hidden).

3. **"zoom level change does not crash"** — Creates a task, opens timeline, changes view mode via select dropdown/button/programmatic fallback, asserts gantt container and bars remain present.

Key discovery: `_detect_date_fields()` uses priority `["scheduledstart", "startdate", "duedate", ...]` and Task shape defines both `scheduledStart` (dateTime) and `dueDate` (date). Timeline SPARQL queries `bpkm:scheduledStart`, not `bpkm:dueDate`. Seed data only populates `dueDate`, so tests create their own tasks with `scheduledStart`.

Added `timeline`/`timelineBar`/`timelineArrow` selectors to `SEL.views` and `'timeline'` to `openGenericViewTab()` type union.

## Verification

- `cd e2e && npx playwright test tests/02-views/timeline.spec.ts --project chromium` — 3/3 passed
- `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` — 15/15 passed
- `curl timeline data endpoint` — returns `{"tasks": [], "dependency_count": 0}` (correct empty shape)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_timeline.py -v` | 0 | ✅ pass | 0.5s |
| 2 | `cd e2e && npx playwright test tests/02-views/timeline.spec.ts --project chromium` | 0 | ✅ pass | 21.1s |
| 3 | `curl -s http://localhost:3901/browser/views/generic/timeline/data \| python3 -c "..."` | 0 | ✅ pass | <1s |

## Diagnostics

- Run with `--headed` for visual debugging; filter DevTools with `[timeline]`
- Failed tests produce screenshots and trace zips in `e2e/test-results/`
- Tests are independent — each creates own tasks and navigates fresh

## Deviations

- **Test location:** Plan said `e2e/specs/timeline.spec.ts`; actual convention is `e2e/tests/02-views/`.
- **Date property:** Plan assumed `bpkm:dueDate`; reality is `bpkm:scheduledStart` (higher priority in detection).
- **Arrow assertion:** Changed from visibility to DOM attachment check for SVG compatibility.

## Known Issues

- Seed data tasks don't populate `scheduledStart`/`scheduledEnd`, so timeline shows empty for seed tasks unless users add those dates manually.

## Files Created/Modified

- `e2e/tests/02-views/timeline.spec.ts` — New Playwright E2E spec with 3 timeline view tests
- `e2e/helpers/selectors.ts` — Added timeline, timelineBar, timelineArrow selectors to SEL.views
- `e2e/helpers/dockview.ts` — Added 'timeline' to openGenericViewTab renderer type union
- `.gsd/milestones/M034/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section
