---
estimated_steps: 3
estimated_files: 3
skills_used: []
---

# T03: E2E test for calendar view

**Slice:** S03 — Calendar View
**Milestone:** M033

## Description

Write a Playwright E2E test that verifies the full calendar view pipeline: opening from the sidebar, FullCalendar rendering, month/week/day view switching, and event click opening an object tab. Also update the E2E helpers to include `'calendar'` in the renderer union type and selector map.

## Steps

1. **Update `e2e/helpers/dockview.ts`**:
   - In the `openGenericViewTab` function signature, add `'calendar'` to the renderer union type: `renderer: 'table' | 'card' | 'graph' | 'kanban' | 'calendar'`

2. **Update `e2e/helpers/selectors.ts`**:
   - Add `calendar: '[data-testid="calendar-view"]'` to the `SEL.views` object (after `kanbanCard`)

3. **Write `e2e/tests/02-views/calendar-view.spec.ts`**:
   - Import `test, expect, BASE_URL` from auth fixture, `SEL` from selectors, `openGenericViewTab` from dockview, `waitForWorkspace` from wait-for helpers
   - Test: "calendar view renders with FullCalendar":
     - Navigate to `${BASE_URL}/browser/`
     - Wait for workspace
     - Call `openGenericViewTab(page, 'calendar', SEL.views.calendar)`
     - Wait for the `.fc` class (FullCalendar container) to appear inside the calendar panel
     - Assert `.fc` element is visible
   - Test: "calendar view shows empty state when no type selected":
     - Open calendar view
     - Assert `.view-empty-state` is visible OR the FullCalendar renders an empty month grid (both are acceptable — depends on whether the backend returns an error_message or renders the grid without data)
   - Test: "month/week/day view switching":
     - Open calendar view, select a type (use `bpkm:Event` if available, else any type)
     - Click the week button (`.fc-timeGridWeek-button`) → assert the week view renders (`.fc-timegrid` visible)
     - Click the day button (`.fc-timeGridDay-button`) → assert day view renders
     - Click the month button (`.fc-dayGridMonth-button`) → assert month grid returns (`.fc-daygrid` visible)

## Must-Haves

- [ ] `'calendar'` in dockview.ts renderer union type
- [ ] `calendar` selector in SEL.views
- [ ] E2E test verifies FullCalendar renders (`.fc` container present)
- [ ] E2E test verifies month/week/day switching

## Verification

- `npx playwright test e2e/tests/02-views/calendar-view.spec.ts` — all tests pass

## Inputs

- `e2e/helpers/dockview.ts` — existing helper with `openGenericViewTab` function
- `e2e/helpers/selectors.ts` — existing `SEL.views` object
- `e2e/tests/02-views/m031-views.spec.ts` — reference test pattern for view E2E tests
- `backend/app/templates/browser/calendar_view.html` — T02's template with `data-testid="calendar-view"`
- `frontend/static/js/workspace.js` — T02's `calendar` label registration

## Expected Output

- `e2e/helpers/dockview.ts` — modified with `'calendar'` in renderer type
- `e2e/helpers/selectors.ts` — modified with `calendar` selector
- `e2e/tests/02-views/calendar-view.spec.ts` — new E2E test file
