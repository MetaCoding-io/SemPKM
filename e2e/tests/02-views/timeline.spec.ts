/**
 * Timeline / Gantt View E2E Tests — S02, M034
 *
 * Validates the Frappe Gantt-based timeline view renderer:
 *   - Frappe Gantt renders task bars inside a dockview panel
 *   - Dependency arrows render between linked tasks
 *   - Zoom level switching (view mode change) works without crash
 *
 * The _detect_date_fields() method prefers scheduledStart > dueDate for
 * the start field, so test tasks use bpkm:scheduledStart to guarantee
 * they appear in the timeline SPARQL query results.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const TASK_TYPE = TYPES.Task;
const BPKM = 'urn:sempkm:model:basic-pkm:';

// The timeline date detection picks scheduledStart (priority 1) over dueDate
// (priority 3). Seed data uses dueDate only, so test-created tasks must use
// scheduledStart to appear in the timeline.
const SCHEDULED_START_PRED = `${BPKM}scheduledStart`;
const SCHEDULED_END_PRED = `${BPKM}scheduledEnd`;
const DEPENDS_ON_PRED = `${BPKM}dependsOn`;
const STATUS_PRED = `${BPKM}taskStatus`;
const PRIORITY_PRED = `${BPKM}priority`;
const TITLE_PRED = 'http://purl.org/dc/terms/title';

/**
 * Create a task via the command API with a scheduledStart date.
 * Returns the minted IRI.
 */
async function createTask(
  ownerRequest: any,
  title: string,
  scheduledStart: string,
  extraProps: Record<string, string> = {},
): Promise<string> {
  const resp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
    data: {
      command: 'object.create',
      params: {
        type: TASK_TYPE,
        properties: {
          [TITLE_PRED]: title,
          [SCHEDULED_START_PRED]: scheduledStart,
          ...extraProps,
        },
      },
    },
  });
  expect(resp.ok(), `Failed to create task "${title}": ${resp.status()}`).toBeTruthy();
  const body = await resp.json();
  // Command API returns { results: [{iri, event_iri, command}] }
  const iri = body.results?.[0]?.iri || body.iri || '';
  return iri;
}

/**
 * Create a bpkm:dependsOn edge between two tasks.
 */
async function createDependency(
  ownerRequest: any,
  sourceIri: string,
  targetIri: string,
): Promise<void> {
  const resp = await ownerRequest.post(`${BASE_URL}/api/commands`, {
    data: {
      command: 'edge.create',
      params: {
        source: sourceIri,
        target: targetIri,
        predicate: DEPENDS_ON_PRED,
      },
    },
  });
  expect(resp.ok(), `Failed to create dependency edge: ${resp.status()}`).toBeTruthy();
}

test.describe('Timeline View', () => {
  /**
   * Core rendering: create tasks with scheduledStart dates, open the
   * timeline view with Task type pre-selected, verify Frappe Gantt
   * renders with visible task bars.
   */
  test('timeline view renders task bars', async ({ ownerPage, ownerRequest }) => {
    // Create test tasks with scheduledStart so they appear in the timeline
    const taskIri = await createTask(ownerRequest, 'Timeline Bar Test', '2026-04-01', {
      [SCHEDULED_END_PRED]: '2026-04-05',
      [STATUS_PRED]: 'in-progress',
    });
    expect(taskIri).toBeTruthy();

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set the Task type so the timeline loads data immediately
    await ownerPage.evaluate((taskType) => {
      localStorage.setItem('sempkm_generic_type_timeline', taskType);
    }, TASK_TYPE);

    await openGenericViewTab(ownerPage, 'timeline', SEL.views.timeline, undefined, undefined, 20000, 'attached');

    // The timeline container should be in the DOM (may not be visible until Gantt CDN loads)
    await expect(ownerPage.locator(SEL.views.timeline)).toBeAttached({ timeout: 10000 });

    // Wait for Frappe Gantt to bootstrap — CDN load is async
    await ownerPage.waitForSelector('.gantt-container', { timeout: 30000 });
    await expect(ownerPage.locator('.gantt-container')).toBeVisible();

    // At least one task bar should be rendered
    await ownerPage.waitForSelector(SEL.views.timelineBar, { timeout: 10000 });
    const barCount = await ownerPage.locator(SEL.views.timelineBar).count();
    expect(barCount).toBeGreaterThan(0);
  });

  /**
   * Dependency arrows: create two tasks with a dependency edge, then
   * verify that Frappe Gantt renders an arrow between them.
   */
  test('timeline shows dependency arrows', async ({ ownerPage, ownerRequest }) => {
    // Create two test tasks with scheduledStart dates
    const taskAIri = await createTask(ownerRequest, 'Timeline Dep: Task A', '2026-04-10', {
      [SCHEDULED_END_PRED]: '2026-04-12',
      [STATUS_PRED]: 'in-progress',
      [PRIORITY_PRED]: 'high',
    });
    expect(taskAIri).toBeTruthy();

    const taskBIri = await createTask(ownerRequest, 'Timeline Dep: Task B', '2026-04-15', {
      [SCHEDULED_END_PRED]: '2026-04-18',
      [STATUS_PRED]: 'todo',
      [PRIORITY_PRED]: 'medium',
    });
    expect(taskBIri).toBeTruthy();

    // Create dependency: Task B depends on Task A
    await createDependency(ownerRequest, taskBIri, taskAIri);

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set Task type
    await ownerPage.evaluate((taskType) => {
      localStorage.setItem('sempkm_generic_type_timeline', taskType);
    }, TASK_TYPE);

    await openGenericViewTab(ownerPage, 'timeline', SEL.views.timeline, undefined, undefined, 20000, 'attached');

    // Wait for Gantt to render
    await ownerPage.waitForSelector('.gantt-container', { timeout: 30000 });
    await ownerPage.waitForSelector(SEL.views.timelineBar, { timeout: 10000 });

    // Frappe Gantt renders dependency arrows as SVG <g class="arrow">
    // elements. In SVG context, Playwright may report them as "hidden"
    // even when they render visually, so we check for DOM attachment
    // rather than visibility.
    await ownerPage.waitForSelector(SEL.views.timelineArrow, { state: 'attached', timeout: 10000 });
    const arrowCount = await ownerPage.locator(SEL.views.timelineArrow).count();
    expect(arrowCount).toBeGreaterThan(0);
  });

  /**
   * Zoom switching: change the Gantt view mode and verify the chart
   * doesn't crash — bars remain visible after the switch.
   */
  test('zoom level change does not crash', async ({ ownerPage, ownerRequest }) => {
    // Ensure at least one task exists with scheduledStart
    await createTask(ownerRequest, 'Timeline Zoom Test', '2026-04-20', {
      [SCHEDULED_END_PRED]: '2026-04-25',
    });

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set Task type
    await ownerPage.evaluate((taskType) => {
      localStorage.setItem('sempkm_generic_type_timeline', taskType);
    }, TASK_TYPE);

    await openGenericViewTab(ownerPage, 'timeline', SEL.views.timeline, undefined, undefined, 20000, 'attached');

    // Wait for Gantt to fully render
    await ownerPage.waitForSelector('.gantt-container', { timeout: 30000 });
    await ownerPage.waitForSelector(SEL.views.timelineBar, { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Frappe Gantt v1.2.2 with view_mode_select: true renders a <select>
    // element for view mode switching. Try multiple selector strategies.
    const viewModeSelect = ownerPage.locator('.gantt-container select, .viewmode-select, select.view-mode');
    const selectCount = await viewModeSelect.count();

    if (selectCount > 0) {
      // Select "Month" view mode from the dropdown
      await viewModeSelect.first().selectOption({ label: 'Month' });
    } else {
      // Frappe Gantt might use buttons — try button-based approach
      const monthBtn = ownerPage.locator('button:has-text("Month"), [data-view-mode="Month"]');
      const btnCount = await monthBtn.count();
      if (btnCount > 0) {
        await monthBtn.first().click();
      } else {
        // Fall back to programmatic view mode change via Gantt API
        await ownerPage.evaluate(() => {
          // Frappe Gantt stores the instance and exposes change_view_mode
          const containers = document.querySelectorAll('.gantt-container');
          containers.forEach((c) => {
            const svg = c.querySelector('svg.gantt');
            if (svg && (svg as any).__gantt) {
              (svg as any).__gantt.change_view_mode('Month');
            }
          });
        });
      }
    }

    // After zoom change, the gantt container should still be visible (no crash)
    await expect(ownerPage.locator('.gantt-container')).toBeVisible({ timeout: 5000 });

    // Task bars should still be present after the view mode change
    const barCount = await ownerPage.locator(SEL.views.timelineBar).count();
    expect(barCount).toBeGreaterThan(0);
  });
});
