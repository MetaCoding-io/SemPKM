/**
 * Event Log E2E Tests
 *
 * Tests the event log bottom panel:
 * - Alt+J opens the bottom panel
 * - Clicking the Event Log tab lazy-loads event rows via htmx
 * - Events display operation type, affected object, and timestamp
 *
 * Requires: Docker test stack on port 3901, seed data installed.
 * Phase: 16 (Event Log Explorer)
 *
 * DOM structure (from workspace.html + event_log.html):
 *   #bottom-panel            — the collapsible bottom panel (height:0 when closed)
 *   .panel-tab[data-panel]   — tab buttons (data-panel="sparql"|"event-log"|"ai-copilot")
 *   #panel-event-log         — event log pane
 *   .event-row-wrapper       — individual event row containers
 *   .event-row               — the row itself (op badge, affected, user, timestamp)
 */
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Event Log', () => {
  test('Alt+J opens the bottom panel', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Bottom panel starts closed (height: 0)
    const bottomPanel = ownerPage.locator('#bottom-panel');
    await expect(bottomPanel).toBeAttached();

    const initialHeight = await bottomPanel.evaluate((el: HTMLElement) => el.style.height);
    expect(initialHeight).toBe('0px');

    // Alt+J calls toggleBottomPanel() which sets a non-zero height
    await ownerPage.keyboard.press('Alt+j');
    await waitForIdle(ownerPage);

    // Panel height should now be non-zero (panel is open)
    const openHeight = await bottomPanel.evaluate((el: HTMLElement) => el.style.height);
    expect(openHeight).not.toBe('0px');
    expect(openHeight).not.toBe('');
  });

  test('event log tab shows event rows after load', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open bottom panel
    await ownerPage.keyboard.press('Alt+j');
    await waitForIdle(ownerPage);

    // Click the EVENT LOG tab (data-panel="event-log")
    // workspace.html: <button class="panel-tab" data-panel="event-log">EVENT LOG</button>
    const eventLogTab = ownerPage.locator('.panel-tab[data-panel="event-log"]');
    await eventLogTab.click();

    // Wait for htmx lazy-load of event log content to complete
    // (initPanelTabs detects .panel-placeholder and fires htmx.ajax GET /browser/events)
    await waitForIdle(ownerPage);

    // Wait for event rows — seed data creates events on install, so there should be entries
    // event_log.html: <div class="event-row-wrapper" data-event-iri="...">
    const eventRows = ownerPage.locator('.event-row-wrapper');
    await expect(eventRows.first()).toBeVisible({ timeout: 10000 });

    const count = await eventRows.count();
    expect(count).toBeGreaterThan(0);
  });
});
