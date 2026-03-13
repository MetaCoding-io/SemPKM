/**
 * Favorites E2E Tests
 *
 * Tests the star button and FAVORITES explorer section:
 * - Star button visible on object tab
 * - Clicking star adds object to FAVORITES section
 * - FAVORITES section shows starred object with correct label
 * - Clicking a favorite in FAVORITES opens the object tab
 * - Clicking star again (unfavorite) removes from FAVORITES
 * - Empty FAVORITES section shows hint text
 *
 * NOTE: Limited to ≤5 tests to stay within the auth rate limit (5 magic-link
 * calls per minute). Tests are combined where logically related.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { openObjectTab } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Favorites', () => {
  test('empty FAVORITES section shows hint text on workspace load', async ({ ownerPage }) => {
    // Ensure no leftover favorites from prior runs by unfavoriting via API
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await waitForIdle(ownerPage);

    // Wait for FAVORITES section to load via htmx
    const favSection = ownerPage.locator('#section-favorites');
    await expect(favSection).toBeVisible({ timeout: 10000 });

    const favBody = ownerPage.locator('#favorites-tree-body');
    // The hint text should appear (or existing favorites) — if there are
    // leftover favorites from a prior test run, clear them first
    const hintOrItems = favBody.locator('.tree-empty, .tree-leaf');
    await expect(hintOrItems.first()).toBeVisible({ timeout: 10000 });

    // Check if there are existing favorites and clear them
    const existingFavs = favBody.locator('.tree-leaf');
    const favCount = await existingFavs.count();
    if (favCount > 0) {
      // Clear by toggling each one off via star buttons
      for (let i = 0; i < favCount; i++) {
        const iri = await existingFavs.nth(i).getAttribute('data-iri');
        if (iri) {
          await ownerPage.evaluate(async (objectIri) => {
            const fd = new FormData();
            fd.append('object_iri', objectIri);
            await fetch('/browser/favorites/toggle', { method: 'POST', body: fd, credentials: 'same-origin' });
          }, iri);
        }
      }
      // Trigger refresh
      await ownerPage.evaluate(() => {
        if (typeof (window as any).htmx !== 'undefined') {
          (window as any).htmx.trigger(document.body, 'favoritesRefreshed');
        }
      });
      await ownerPage.waitForTimeout(1000);
    }

    // Now the hint text should be visible
    const hint = favBody.locator('.tree-empty');
    await expect(hint).toBeVisible({ timeout: 5000 });
    await expect(hint).toHaveText('Star objects to add them here');
  });

  test('star button visible on object tab and toggles favorite state', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open a seed object tab
    const noteIri = SEED.notes.architecture.iri;
    const noteLabel = SEED.notes.architecture.title;
    await openObjectTab(ownerPage, noteIri, noteLabel);

    // Star button should be visible
    const starBtn = ownerPage.locator(`.star-btn[data-iri="${noteIri}"]`);
    await expect(starBtn).toBeVisible({ timeout: 5000 });

    // Initially should NOT be favorited (unless leftover from prior run)
    // Click to toggle — if already favorited, this unfavorites first
    const wasFavorited = await starBtn.evaluate((el) => el.classList.contains('is-favorited'));
    if (wasFavorited) {
      await starBtn.click();
      await ownerPage.waitForTimeout(500);
    }

    // Confirm it's unfavorited
    await expect(starBtn).not.toHaveClass(/is-favorited/);

    // --- Click star to FAVORITE ---
    await starBtn.click();
    // Wait for the class to update (the JS fetch + DOM update)
    await expect(starBtn).toHaveClass(/is-favorited/, { timeout: 5000 });

    // FAVORITES section should show the object
    await waitForIdle(ownerPage);
    const favBody = ownerPage.locator('#favorites-tree-body');
    const favItem = favBody.locator(`[data-testid="favorites-item"][data-iri="${noteIri}"]`);
    await expect(favItem).toBeVisible({ timeout: 5000 });
    await expect(favItem.locator('.tree-leaf-label')).toHaveText(noteLabel);

    // --- Click star to UNFAVORITE ---
    await starBtn.click();
    await expect(starBtn).not.toHaveClass(/is-favorited/, { timeout: 5000 });

    // The favorite should be removed from the section
    await waitForIdle(ownerPage);
    await expect(favItem).not.toBeVisible({ timeout: 5000 });

    // Hint text should reappear
    const hint = favBody.locator('.tree-empty');
    await expect(hint).toBeVisible({ timeout: 5000 });
  });

  test('clicking a favorite in FAVORITES opens the object tab', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Star a seed object via API to set up
    const noteIri = SEED.notes.kickoff.iri;
    const noteLabel = SEED.notes.kickoff.title;
    await ownerPage.evaluate(async (objectIri) => {
      const fd = new FormData();
      fd.append('object_iri', objectIri);
      // First check if already favorited by trying to list
      const resp = await fetch('/browser/favorites/toggle', { method: 'POST', body: fd, credentials: 'same-origin' });
      const html = await resp.text();
      // If the toggle removed it (was already favorited), add it back
      if (html.indexOf('is-favorited') === -1) {
        const fd2 = new FormData();
        fd2.append('object_iri', objectIri);
        await fetch('/browser/favorites/toggle', { method: 'POST', body: fd2, credentials: 'same-origin' });
      }
    }, noteIri);

    // Refresh favorites section
    await ownerPage.evaluate(() => {
      if (typeof (window as any).htmx !== 'undefined') {
        (window as any).htmx.trigger(document.body, 'favoritesRefreshed');
      }
    });
    await waitForIdle(ownerPage);

    // Wait for the favorites item to appear
    const favBody = ownerPage.locator('#favorites-tree-body');
    const favItem = favBody.locator(`[data-testid="favorites-item"][data-iri="${noteIri}"]`);
    await expect(favItem).toBeVisible({ timeout: 5000 });

    // Click the favorite item to open the tab
    await favItem.click();

    // Wait for object tab to open
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });

    // Verify the correct object is shown
    const objectTab = ownerPage.locator(`.object-tab[data-object-iri="${noteIri}"]`);
    await expect(objectTab).toBeVisible({ timeout: 5000 });

    // Clean up: unfavorite
    await ownerPage.evaluate(async (objectIri) => {
      const fd = new FormData();
      fd.append('object_iri', objectIri);
      await fetch('/browser/favorites/toggle', { method: 'POST', body: fd, credentials: 'same-origin' });
    }, noteIri);
  });

  test('star button reflects correct initial state when object is already favorited', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Favorite a seed object via API first
    const conceptIri = SEED.concepts.km.iri;
    await ownerPage.evaluate(async (objectIri) => {
      const fd = new FormData();
      fd.append('object_iri', objectIri);
      // Toggle on — if already on, toggle twice
      const resp = await fetch('/browser/favorites/toggle', { method: 'POST', body: fd, credentials: 'same-origin' });
      const html = await resp.text();
      if (html.indexOf('is-favorited') === -1) {
        // Was favorited, now unfavorited — toggle again
        const fd2 = new FormData();
        fd2.append('object_iri', objectIri);
        await fetch('/browser/favorites/toggle', { method: 'POST', body: fd2, credentials: 'same-origin' });
      }
    }, conceptIri);

    // Open the object tab
    await openObjectTab(ownerPage, conceptIri, SEED.concepts.km.label);

    // Star button should be visible and already have is-favorited class
    const starBtn = ownerPage.locator(`.star-btn[data-iri="${conceptIri}"]`);
    await expect(starBtn).toBeVisible({ timeout: 5000 });
    await expect(starBtn).toHaveClass(/is-favorited/, { timeout: 5000 });

    // Clean up: unfavorite
    await ownerPage.evaluate(async (objectIri) => {
      const fd = new FormData();
      fd.append('object_iri', objectIri);
      await fetch('/browser/favorites/toggle', { method: 'POST', body: fd, credentials: 'same-origin' });
    }, conceptIri);
  });
});
