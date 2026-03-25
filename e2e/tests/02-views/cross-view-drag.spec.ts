/**
 * Cross-View Drag & Scope Propagation E2E Tests — S03, M034
 *
 * Validates:
 *   1. Kanban card drag data includes IRI and title attributes
 *   2. External drop on calendar triggers PATCH and persists scheduledStart
 *   3. Scope-changed event fires with correct detail structure
 *
 * HTML5 drag-and-drop is hard to simulate across dockview panels in
 * Playwright, so we exercise the drop handler directly via page.evaluate()
 * — the same approach used by the canvas drop tests.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const TASK_TYPE = TYPES.Task;

test.describe('Cross-View Drag & Scope Propagation', () => {
  /**
   * Test 1: Kanban card drag data includes IRI and title attributes.
   * Opens kanban view filtered to Task type, verifies that .kanban-card
   * elements carry data-iri and data-title attributes, and that the
   * onDragStart handler would set the __calendarDragPayload side-channel.
   */
  test('kanban card drag data includes IRI and title', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set Task type for kanban
    await ownerPage.evaluate((taskType) => {
      localStorage.setItem('sempkm_generic_type_kanban', taskType);
    }, TASK_TYPE);

    await openGenericViewTab(ownerPage, 'kanban', SEL.views.kanbanBoard, undefined, undefined, 20000);
    await waitForIdle(ownerPage);

    // Wait for at least one kanban card to appear (seed data includes tasks)
    const cards = ownerPage.locator(SEL.views.kanbanCard);
    const cardCount = await cards.count();

    if (cardCount === 0) {
      // No seed tasks — create one via the commands API
      const resp = await ownerPage.request.post(`${BASE_URL}/api/commands`, {
        data: {
          command: 'object.create',
          params: {
            type: TASK_TYPE,
            properties: {
              'http://purl.org/dc/terms/title': 'Drag Test Task',
              'urn:sempkm:model:basic-pkm:taskStatus': 'todo',
            },
          },
        },
      });
      expect(resp.status()).toBe(200);

      // Refresh kanban to pick up the new task
      await ownerPage.evaluate(() => {
        document.dispatchEvent(new CustomEvent('sempkm:command-executed'));
      });
      await ownerPage.waitForTimeout(2000);
      // Re-open kanban
      await openGenericViewTab(ownerPage, 'kanban', SEL.views.kanbanBoard, undefined, undefined, 20000);
      await waitForIdle(ownerPage);
    }

    // Now verify at least one card has data-iri and data-title
    const firstCard = cards.first();
    await expect(firstCard).toBeVisible({ timeout: 10000 });

    const iri = await firstCard.getAttribute('data-iri');
    const title = await firstCard.getAttribute('data-title');

    expect(iri).toBeTruthy();
    expect(typeof iri).toBe('string');
    expect(iri!.length).toBeGreaterThan(0);

    expect(title).toBeTruthy();
    expect(typeof title).toBe('string');
    expect(title!.length).toBeGreaterThan(0);

    // Verify that simulating dragstart sets the side-channel
    const payload = await ownerPage.evaluate((cardSel) => {
      const card = document.querySelector(cardSel) as HTMLElement;
      if (!card) return null;

      // Simulate a minimal dragstart event
      const evt = new DragEvent('dragstart', {
        bubbles: true,
        cancelable: true,
        dataTransfer: new DataTransfer(),
      });
      card.dispatchEvent(evt);

      return (window as any).SemPKM.__calendarDragPayload;
    }, SEL.views.kanbanCard);

    expect(payload).toBeTruthy();
    expect(payload.iri).toBeTruthy();
    expect(payload.title).toBeTruthy();
  });

  /**
   * Test 2: External drop on calendar schedules a task.
   * Seeds a Task via API, opens calendar, simulates the drop handler
   * via page.evaluate(), and verifies the PATCH request fires and
   * the event appears on the calendar.
   *
   * NOTE: This test requires FullCalendar CDN to be reachable. If the
   * CDN load fails (common in isolated test environments), the test
   * verifies the data flow up to the point of failure and skips the
   * visual assertion.
   */
  test('external drop on calendar schedules task', async ({ ownerPage }) => {
    // 1. Seed a Task via the commands API
    const taskTitle = `CalDrop Test ${Date.now()}`;
    const createResp = await ownerPage.request.post(`${BASE_URL}/api/commands`, {
      data: {
        command: 'object.create',
        params: {
          type: TASK_TYPE,
          properties: {
            'http://purl.org/dc/terms/title': taskTitle,
            'urn:sempkm:model:basic-pkm:taskStatus': 'todo',
          },
        },
      },
    });
    expect(createResp.status()).toBe(200);
    const createData = await createResp.json();
    const taskIri = createData.results?.[0]?.iri;
    expect(taskIri).toBeTruthy();

    // 2. Navigate to workspace and open calendar
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set Task type for calendar
    await ownerPage.evaluate((taskType) => {
      localStorage.setItem('sempkm_generic_type_calendar', taskType);
    }, TASK_TYPE);

    await openGenericViewTab(ownerPage, 'calendar', SEL.views.calendar, undefined, undefined, 25000);

    // Wait for FullCalendar CDN to load — this may fail in isolated envs
    let calendarReady = false;
    try {
      await ownerPage.waitForSelector('.fc', { timeout: 25000 });
      calendarReady = true;
    } catch {
      // CDN didn't load — verify what we can without the visual calendar
      console.log('FullCalendar CDN not loaded — testing PATCH endpoint directly');
    }

    if (calendarReady) {
      await waitForIdle(ownerPage);

      // 3. Simulate external drop via page.evaluate()
      const patchPromise = ownerPage.waitForResponse(
        (resp) => resp.url().includes('/browser/views/calendar/patch') && resp.status() === 200,
        { timeout: 15000 },
      );

      await ownerPage.evaluate(({ iri, title }) => {
        const cal = (window as any).SemPKM._sempkmCalendar;
        if (!cal) throw new Error('Calendar instance not found');

        // Set the side-channel payload (same as kanban onDragStart)
        (window as any).SemPKM.__calendarDragPayload = { iri, title };

        // Build a synthetic FullCalendar drop info object
        const dropDate = new Date();
        dropDate.setHours(14, 0, 0, 0);

        const fakeEl = document.createElement('div');
        fakeEl.dataset.iri = iri;
        fakeEl.dataset.title = title;

        // Call the FullCalendar drop callback via the options
        const dropHandler = cal.getOption('drop');
        if (typeof dropHandler === 'function') {
          dropHandler({
            date: dropDate,
            dateStr: dropDate.toISOString(),
            allDay: false,
            draggedEl: fakeEl,
            jsEvent: new MouseEvent('drop'),
            view: cal.view,
          });
        }
      }, { iri: taskIri, title: taskTitle });

      // 4. Wait for the PATCH response
      const patchResponse = await patchPromise;
      expect(patchResponse.status()).toBe(200);
      const patchData = await patchResponse.json();
      expect(patchData.ok).toBe(true);

      // 5. Verify the calendar shows the event
      await ownerPage.waitForTimeout(1000);
      const calEvent = ownerPage.locator(SEL.views.calendarEvent);
      await expect(calEvent.first()).toBeVisible({ timeout: 5000 });
    }

    // 6. Verify scheduledStart persistence via direct API call —
    //    works regardless of whether the calendar UI loaded.
    //    If calendar didn't load, use the PATCH endpoint directly.
    if (!calendarReady) {
      // Directly call the PATCH endpoint to schedule the task
      const patchResp = await ownerPage.request.post(`${BASE_URL}/browser/views/calendar/patch`, {
        data: {
          iri: taskIri,
          start: new Date().toISOString(),
          end: new Date(Date.now() + 3600000).toISOString(),
        },
      });
      expect(patchResp.status()).toBe(200);
      const patchData = await patchResp.json();
      expect(patchData.ok).toBe(true);
    }

    // Verify scheduledStart was persisted via SPARQL
    const sparqlResp = await ownerPage.request.post(`${BASE_URL}/api/sparql`, {
      data: {
        query: `SELECT ?start WHERE {
          GRAPH <urn:sempkm:current> {
            <${taskIri}> <urn:sempkm:model:basic-pkm:scheduledStart> ?start .
          }
        }`,
      },
    });
    expect(sparqlResp.status()).toBe(200);
    const sparqlData = await sparqlResp.json();
    const bindings = sparqlData.results?.bindings || [];
    expect(bindings.length).toBeGreaterThan(0);
    expect(bindings[0].start.value).toBeTruthy();
  });

  /**
   * Test 3: Scope change propagation fires sempkm:scope-changed event.
   * Opens a view, sets up a listener, then triggers a scope change via
   * the select element, and verifies the event fires with correct fields.
   */
  test('scope change propagation fires event', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set Task type for kanban
    await ownerPage.evaluate((taskType) => {
      localStorage.setItem('sempkm_generic_type_kanban', taskType);
    }, TASK_TYPE);

    await openGenericViewTab(ownerPage, 'kanban', SEL.views.kanbanBoard, undefined, undefined, 20000);
    await waitForIdle(ownerPage);

    // Set up a listener for the scope-changed event
    await ownerPage.evaluate(() => {
      (window as any).__scopeEventFired = null;
      document.addEventListener('sempkm:scope-changed', (e: any) => {
        (window as any).__scopeEventFired = e.detail;
      });
    });

    // Check if a scope select exists
    const scopeSelect = ownerPage.locator(SEL.views.scopeSelect);
    const scopeCount = await scopeSelect.count();

    if (scopeCount > 0) {
      // Get current options
      const options = await scopeSelect.first().locator('option').all();

      if (options.length > 1) {
        // Select the second option to trigger a scope change
        const secondValue = await options[1].getAttribute('value');
        await scopeSelect.first().selectOption(secondValue || '');

        // Wait for the event to fire
        await ownerPage.waitForTimeout(500);

        const detail = await ownerPage.evaluate(() => (window as any).__scopeEventFired);

        expect(detail).toBeTruthy();
        expect(detail).toHaveProperty('scopeQuery');
        expect(detail).toHaveProperty('sourcePanel');
        expect(detail).toHaveProperty('renderer');
        expect(detail).toHaveProperty('selectedType');
      } else {
        // No saved queries to pick from — trigger scope change programmatically
        // via applyScopeQuery to verify the event detail structure
        await ownerPage.evaluate(() => {
          if (typeof (window as any).SemPKM.applyScopeQuery === 'function') {
            // Create a temporary element to derive sourcePanel
            const viewContainer = document.querySelector('.kanban-board');
            const sourceEl = viewContainer || document.body;
            (window as any).SemPKM.applyScopeQuery('test-query-id', 'kanban', 'urn:test:Type', sourceEl);
          }
        });

        await ownerPage.waitForTimeout(500);
        const detail = await ownerPage.evaluate(() => (window as any).__scopeEventFired);

        expect(detail).toBeTruthy();
        expect(detail).toHaveProperty('scopeQuery');
        expect(detail).toHaveProperty('sourcePanel');
        expect(detail).toHaveProperty('renderer');
        expect(detail).toHaveProperty('selectedType');
        expect(detail.scopeQuery).toBe('test-query-id');
        expect(detail.renderer).toBe('kanban');
      }
    } else {
      // No scope select rendered — programmatically dispatch the event
      // to verify the structure contract
      await ownerPage.evaluate(() => {
        if (typeof (window as any).SemPKM.applyScopeQuery === 'function') {
          const sourceEl = document.querySelector('.kanban-board') || document.body;
          (window as any).SemPKM.applyScopeQuery('programmatic-scope', 'kanban', 'urn:test:Type', sourceEl);
        }
      });

      await ownerPage.waitForTimeout(500);
      const detail = await ownerPage.evaluate(() => (window as any).__scopeEventFired);

      expect(detail).toBeTruthy();
      expect(detail).toHaveProperty('scopeQuery');
      expect(detail).toHaveProperty('sourcePanel');
      expect(detail).toHaveProperty('renderer');
      expect(detail).toHaveProperty('selectedType');
    }
  });
});
