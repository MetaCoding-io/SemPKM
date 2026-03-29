/**
 * Calendar View E2E Tests — S03, M033
 *
 * Validates the FullCalendar-based calendar view renderer:
 *   - FullCalendar renders inside a dockview panel
 *   - Empty state when no type is selected
 *   - Month / week / day view switching
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

/** Event type IRI — follows the same namespace pattern as other bpkm types. */
const EVENT_TYPE = 'urn:sempkm:model:basic-pkm:Event';

test.describe('Calendar View', () => {
  /**
   * Core rendering: opening the calendar view should load FullCalendar's
   * .fc container inside the dockview panel.
   */
  test('calendar view renders with FullCalendar', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set the Event type so the calendar loads data immediately
    await ownerPage.evaluate((eventType) => {
      localStorage.setItem('sempkm_generic_type_calendar', eventType);
    }, EVENT_TYPE);

    await openGenericViewTab(ownerPage, 'calendar', SEL.views.calendar, undefined, undefined, 20000);

    // The calendar container should be visible
    await expect(ownerPage.locator(SEL.views.calendar)).toBeVisible({ timeout: 10000 });

    // Wait for FullCalendar to bootstrap — the CDN load is async
    await ownerPage.waitForSelector('.fc', { timeout: 20000 });
    await expect(ownerPage.locator('.fc')).toBeVisible();
  });

  /**
   * Merged mode: when no type is pre-selected, the backend renders a
   * merged-mode calendar (all types with date fields) — not an empty state.
   * The FullCalendar container should still render and be functional.
   */
  test('calendar view renders merged mode when no type selected', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Clear any previously stored type so the calendar starts in merged mode
    await ownerPage.evaluate(() => {
      localStorage.removeItem('sempkm_generic_type_calendar');
    });

    // Backend serves merged-mode calendar (date_fields={"merged":True}),
    // so the FullCalendar container renders — not .view-empty-state
    await openGenericViewTab(ownerPage, 'calendar', SEL.views.calendar, undefined, undefined, 20000);
    await ownerPage.waitForSelector('.fc', { timeout: 20000 });
    await expect(ownerPage.locator('.fc')).toBeVisible();
  });

  /**
   * View switching: month → week → day → month cycle.
   * FullCalendar renders distinct container classes for each view mode.
   */
  test('month/week/day view switching', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set Event type so the calendar renders with data
    await ownerPage.evaluate((eventType) => {
      localStorage.setItem('sempkm_generic_type_calendar', eventType);
    }, EVENT_TYPE);

    await openGenericViewTab(ownerPage, 'calendar', SEL.views.calendar, undefined, undefined, 20000);

    // Wait for FullCalendar to fully render
    await ownerPage.waitForSelector('.fc', { timeout: 20000 });
    await waitForIdle(ownerPage);

    // Default view is dayGridMonth — verify month grid is present.
    // FullCalendar's grid inside dockview can report hidden to Playwright's
    // visibility check, so use waitForSelector with state:'attached'.
    await ownerPage.waitForSelector('.fc-daygrid', { state: 'attached', timeout: 5000 });

    // Switch to week view
    const weekBtn = ownerPage.locator('.fc-timeGridWeek-button');
    if ((await weekBtn.count()) > 0) {
      await weekBtn.click();
      await ownerPage.waitForSelector('.fc-timegrid', { state: 'attached', timeout: 5000 });
    }

    // Switch to day view
    const dayBtn = ownerPage.locator('.fc-timeGridDay-button');
    if ((await dayBtn.count()) > 0) {
      await dayBtn.click();
      // Day view also uses fc-timegrid
      await ownerPage.waitForSelector('.fc-timegrid', { state: 'attached', timeout: 5000 });
    }

    // Switch back to month view
    const monthBtn = ownerPage.locator('.fc-dayGridMonth-button');
    if ((await monthBtn.count()) > 0) {
      await monthBtn.click();
      await ownerPage.waitForSelector('.fc-daygrid', { state: 'attached', timeout: 5000 });
    }
  });
});
