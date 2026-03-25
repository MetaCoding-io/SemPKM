/**
 * Recurring Tasks E2E Tests — S04, M034
 *
 * Validates RRULE expansion renders virtual calendar instances:
 *   - Creating a recurring task shows multiple events on the calendar
 *   - Virtual events have the .fc-event-recurring CSS class (dashed border + ↻)
 *   - Clicking a virtual event opens the master task
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

/** Task type IRI */
const TASK_TYPE = TYPES.Task;

/** Compute an ISO datetime string for a date relative to today */
function futureDate(daysFromNow: number, hours = 10): string {
  const d = new Date();
  d.setDate(d.getDate() + daysFromNow);
  d.setHours(hours, 0, 0, 0);
  return d.toISOString();
}

/**
 * Find the next occurrence of a specific weekday from today.
 * 0 = Sunday, 1 = Monday, ..., 6 = Saturday
 */
function nextWeekday(targetDay: number): Date {
  const d = new Date();
  d.setHours(10, 0, 0, 0);
  const currentDay = d.getDay();
  let daysUntil = targetDay - currentDay;
  if (daysUntil <= 0) daysUntil += 7;
  d.setDate(d.getDate() + daysUntil);
  return d;
}

test.describe('Recurring Tasks on Calendar', () => {

  test('recurring task shows virtual instances on calendar', async ({ ownerPage, ownerRequest }) => {
    // --- Arrange: create a recurring task via the API ---
    const startDate = nextWeekday(1); // next Monday
    const endDate = new Date(startDate.getTime() + 3600000); // 1 hour later
    const taskTitle = `E2E Recurring ${Date.now()}`;

    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TASK_TYPE,
          properties: {
            'http://purl.org/dc/terms/title': taskTitle,
            'urn:sempkm:model:basic-pkm:scheduledStart': startDate.toISOString(),
            'urn:sempkm:model:basic-pkm:scheduledEnd': endDate.toISOString(),
            'urn:sempkm:model:basic-pkm:recurrenceRule': 'FREQ=WEEKLY;COUNT=4',
          },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const masterIri = createData.results?.[0]?.iri;
    expect(masterIri).toBeTruthy();

    // --- Act: navigate to workspace and open calendar view ---
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Clear any type filter so calendar uses merged mode (Events + Tasks)
    // Merged mode bypasses _detect_date_fields and always renders the calendar
    await ownerPage.evaluate(() => {
      localStorage.removeItem('sempkm_generic_type_calendar');
    });

    await openGenericViewTab(ownerPage, 'calendar', SEL.views.calendar, undefined, undefined, 20000);

    // Wait for FullCalendar to render
    await ownerPage.waitForSelector('.fc', { timeout: 20000 });
    await waitForIdle(ownerPage);

    // Give RRULE expansion events time to render
    await ownerPage.waitForTimeout(2000);

    // --- Assert: multiple events with the recurring task title ---
    // The RRULE FREQ=WEEKLY;COUNT=4 should produce the master + 3 virtual
    // instances. On a monthly calendar view, at least 2 should be visible.
    const eventEls = ownerPage.locator(`.fc-event`).filter({ hasText: taskTitle });
    const eventCount = await eventEls.count();
    expect(eventCount).toBeGreaterThanOrEqual(2);

    // At least one event should have the recurring CSS class
    const recurringEls = ownerPage.locator('.fc-event-recurring');
    const recurringCount = await recurringEls.count();
    expect(recurringCount).toBeGreaterThanOrEqual(1);
  });

  test('clicking virtual event opens master task', async ({ ownerPage, ownerRequest }) => {
    // --- Arrange: create a recurring task ---
    const startDate = nextWeekday(2); // next Tuesday
    const endDate = new Date(startDate.getTime() + 3600000);
    const taskTitle = `E2E Click Virtual ${Date.now()}`;

    const createResp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TASK_TYPE,
          properties: {
            'http://purl.org/dc/terms/title': taskTitle,
            'urn:sempkm:model:basic-pkm:scheduledStart': startDate.toISOString(),
            'urn:sempkm:model:basic-pkm:scheduledEnd': endDate.toISOString(),
            'urn:sempkm:model:basic-pkm:recurrenceRule': 'FREQ=WEEKLY;COUNT=4',
          },
        },
      },
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const masterIri = createData.results?.[0]?.iri;
    expect(masterIri).toBeTruthy();

    // --- Act: open calendar and click a virtual instance ---
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await ownerPage.evaluate(() => {
      localStorage.removeItem('sempkm_generic_type_calendar');
    });

    await openGenericViewTab(ownerPage, 'calendar', SEL.views.calendar, undefined, undefined, 20000);
    await ownerPage.waitForSelector('.fc', { timeout: 20000 });
    await waitForIdle(ownerPage);
    await ownerPage.waitForTimeout(2000);

    // Intercept openTab to capture the IRI that would be opened
    await ownerPage.evaluate(() => {
      (window as any).__lastOpenTabIri = null;
      const originalOpenTab = (window as any).SemPKM.openTab;
      (window as any).SemPKM.openTab = function(iri: string, title: string) {
        (window as any).__lastOpenTabIri = iri;
        if (originalOpenTab) originalOpenTab(iri, title);
      };
    });

    // Find a virtual recurring event for THIS task and click it
    const recurringEvents = ownerPage.locator('.fc-event-recurring').filter({ hasText: taskTitle });
    const rcCount = await recurringEvents.count();
    expect(rcCount).toBeGreaterThanOrEqual(1);
    await recurringEvents.first().click();
    await ownerPage.waitForTimeout(1000);

    // --- Assert: openTab was called with the master IRI ---
    const openedIri = await ownerPage.evaluate(() => (window as any).__lastOpenTabIri);
    expect(openedIri).toBeTruthy();
    expect(openedIri).toBe(masterIri);
  });
});
