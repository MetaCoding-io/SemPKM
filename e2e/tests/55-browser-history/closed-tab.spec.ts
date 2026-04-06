/**
 * Closed Tab Recovery E2E Tests
 *
 * Verifies M055/S02: closing a tab pushes it to a recovery stack,
 * and Ctrl+Shift+T (or command palette) reopens it.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Open an object tab and wait for it to render */
async function openObject(page: import('@playwright/test').Page, iri: string, label: string) {
  await page.evaluate(
    ({ iri, label }) => {
      (window as any).SemPKM.openTab(iri, label);
    },
    { iri, label },
  );
  await page.waitForSelector('.object-tab', { timeout: 10000 });
  await waitForIdle(page);
  await page.waitForTimeout(300);
}

/** Close a tab by panel ID via dockview API */
async function closeTab(page: import('@playwright/test').Page, panelId: string) {
  await page.evaluate((id) => {
    const dv = (window as any).SemPKM._dockview;
    if (!dv) return;
    const panel = dv.panels.find((p: any) => p.id === id);
    if (panel) dv.removePanel(panel);
  }, panelId);
  await page.waitForTimeout(300);
  await waitForIdle(page);
}

/** Get all open panel IDs */
async function getPanelIds(page: import('@playwright/test').Page): Promise<string[]> {
  return page.evaluate(() => {
    const dv = (window as any).SemPKM._dockview;
    if (!dv) return [];
    return dv.panels.map((p: any) => p.id);
  });
}

/** Get the active panel ID */
async function getActivePanelId(page: import('@playwright/test').Page): Promise<string | null> {
  return page.evaluate(() => {
    const dv = (window as any).SemPKM?._dockview;
    return dv?.activePanel?.id || null;
  });
}

/** Press Ctrl+Shift+T to reopen the last closed tab */
async function pressReopenShortcut(page: import('@playwright/test').Page) {
  await page.keyboard.press('Control+Shift+t');
  await page.waitForTimeout(500);
  await waitForIdle(page);
}

test.describe('Closed Tab Recovery', () => {
  test('close a tab then Ctrl+Shift+T reopens it with same IRI', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iri = SEED.notes.architecture.iri;
    const label = 'Architecture Decision';

    // Open an object tab
    await openObject(ownerPage, iri, label);

    // Verify it's open
    let panels = await getPanelIds(ownerPage);
    expect(panels).toContain(iri);

    // Close it
    await closeTab(ownerPage, iri);

    // Verify it's closed
    panels = await getPanelIds(ownerPage);
    expect(panels).not.toContain(iri);

    // Press Ctrl+Shift+T to reopen
    await pressReopenShortcut(ownerPage);

    // Wait for the tab content to render
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });

    // Verify it reopened with the same IRI
    panels = await getPanelIds(ownerPage);
    expect(panels).toContain(iri);
    expect(await getActivePanelId(ownerPage)).toBe(iri);
  });

  test('close 3 tabs in sequence, reopenClosedTab reopens all three', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const tabs = [
      { iri: SEED.notes.architecture.iri, label: 'Architecture Decision' },
      { iri: SEED.people.alice.iri, label: 'Alice Chen' },
      { iri: SEED.people.bob.iri, label: 'Bob Martinez' },
    ];

    // Open all three tabs
    for (const t of tabs) {
      await openObject(ownerPage, t.iri, t.label);
    }

    // Verify all three are open
    let panels = await getPanelIds(ownerPage);
    for (const t of tabs) {
      expect(panels).toContain(t.iri);
    }

    // Close all three in open order: Architecture, Alice, Bob
    for (const t of tabs) {
      await closeTab(ownerPage, t.iri);
    }

    // Verify all are closed
    panels = await getPanelIds(ownerPage);
    for (const t of tabs) {
      expect(panels).not.toContain(t.iri);
    }

    // Reopen all 3 via reopenClosedTab() JS calls (more reliable than keyboard shortcut)
    for (let i = 0; i < 3; i++) {
      await ownerPage.evaluate(() => {
        (window as any).SemPKM.reopenClosedTab();
      });
      await ownerPage.waitForTimeout(500);
      await waitForIdle(ownerPage);
    }

    // Verify all three are now open
    panels = await getPanelIds(ownerPage);
    for (const t of tabs) {
      expect(panels).toContain(t.iri);
    }
  });

  test('Ctrl+Shift+T with no closed tabs does nothing and no error', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Capture console errors
    const errors: string[] = [];
    ownerPage.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    const panelsBefore = await getPanelIds(ownerPage);

    // Press Ctrl+Shift+T with an empty closed-tab stack
    await pressReopenShortcut(ownerPage);

    const panelsAfter = await getPanelIds(ownerPage);

    // Panel count should not change
    expect(panelsAfter.length).toBe(panelsBefore.length);

    // No JS errors should have been thrown
    const relevantErrors = errors.filter(
      (e) => e.includes('reopenClosedTab') || e.includes('_closedTabStack') || e.includes('Cannot read'),
    );
    expect(relevantErrors).toHaveLength(0);
  });

  test('close a tab, reopen it manually, then Ctrl+Shift+T skips already-open tab', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const iriA = SEED.notes.architecture.iri;
    const iriB = SEED.people.alice.iri;

    // Open both tabs
    await openObject(ownerPage, iriA, 'Architecture Decision');
    await openObject(ownerPage, iriB, 'Alice Chen');

    // Close both (B then A)
    await closeTab(ownerPage, iriB);
    await closeTab(ownerPage, iriA);

    // Verify both closed
    let panels = await getPanelIds(ownerPage);
    expect(panels).not.toContain(iriA);
    expect(panels).not.toContain(iriB);

    // Manually reopen A (not via Ctrl+Shift+T)
    await openObject(ownerPage, iriA, 'Architecture Decision');
    panels = await getPanelIds(ownerPage);
    expect(panels).toContain(iriA);

    // Now press Ctrl+Shift+T — the stack has [B, A].
    // A is the top of the stack (last closed), but it's already open.
    // Should skip A and activate it, then reopenClosedTab should try B.
    // Implementation: A is detected as already open, so setActive() is called on A,
    // then the while-loop continues and pops B, which IS closed, so it gets reopened.
    await pressReopenShortcut(ownerPage);
    await ownerPage.waitForTimeout(500);

    // B should have been reopened (A was skipped since already open)
    panels = await getPanelIds(ownerPage);
    expect(panels).toContain(iriB);
  });
});
