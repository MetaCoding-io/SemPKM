/**
 * Crossfade Toggle, Inferred Display, and Clear & Reload E2E Tests
 *
 * Tests v2.4 features:
 * - Read/edit crossfade toggle (opacity, not 3D flip)
 * - Inferred badge on relations panel after inference run
 * - Clear & Reload button in user popover
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEED, TYPES } from '../../fixtures/seed-data';
import { waitForIdle, waitForWorkspace } from '../../helpers/wait-for';
import { openObjectTab } from '../../helpers/dockview';

test.describe('Read/Edit Crossfade Toggle', () => {
  test('crossfade toggle switches to edit mode', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openObjectTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await waitForIdle(ownerPage);

    // Click mode toggle (should say "Edit")
    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await expect(toggleBtn).toBeVisible({ timeout: 5000 });
    await toggleBtn.click();

    // Wait for flip-inner to have .flipped class (crossfade: edit face gets opacity:1)
    await ownerPage.waitForSelector('.object-flip-inner.flipped', { timeout: 10000 });

    // Toggle text should now be "Cancel"
    await expect(toggleBtn).toHaveText('Cancel');

    // Edit form should be present
    await expect(ownerPage.locator('[data-testid="object-form"]')).toBeAttached();
  });

  test('crossfade toggle returns to read mode', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openObjectTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await waitForIdle(ownerPage);

    // Enter edit mode
    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await expect(toggleBtn).toBeVisible({ timeout: 5000 });
    await toggleBtn.click();
    await ownerPage.waitForSelector('.object-flip-inner.flipped', { timeout: 10000 });

    // Click Cancel to return to read mode
    await toggleBtn.click();

    // Wait for flipped class to be removed (read face becomes visible via opacity)
    await ownerPage.waitForFunction(
      () => {
        const inner = document.querySelector('.object-flip-inner');
        return inner && !inner.classList.contains('flipped');
      },
      { timeout: 10000 },
    );

    // Toggle text should be "Edit" again
    await expect(toggleBtn).toHaveText('Edit');

    // Markdown body should be visible in read mode
    await expect(ownerPage.locator('.markdown-body').first()).toBeVisible({ timeout: 5000 });
  });

  test('crossfade uses opacity transition not 3D transform', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openObjectTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await waitForIdle(ownerPage);

    // Check that .object-flip-container does NOT use preserve-3d
    const transformStyle = await ownerPage.evaluate(() => {
      const container = document.querySelector('.object-flip-container');
      if (!container) return 'not-found';
      return getComputedStyle(container).transformStyle;
    });
    expect(transformStyle).not.toBe('preserve-3d');

    // Check that faces use opacity for transitions
    const usesOpacity = await ownerPage.evaluate(() => {
      const readFace = document.querySelector('.object-face-read');
      const editFace = document.querySelector('.object-face-edit');
      if (!readFace || !editFace) return false;
      const readTransition = getComputedStyle(readFace).transition;
      const editTransition = getComputedStyle(editFace).transition;
      return readTransition.includes('opacity') || editTransition.includes('opacity');
    });
    expect(usesOpacity).toBe(true);
  });
});

test.describe('Inferred Triple Display', () => {
  test('inferred badge appears on relations panel after inference', async ({
    ownerPage,
    ownerSessionToken,
  }) => {
    const api = ownerPage.context().request;
    const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

    // 1. Create fresh objects with a one-sided relationship
    const createResp = await api.post(`${BASE_URL}/api/commands`, {
      headers,
      data: [
        {
          command: 'object.create',
          params: {
            type: TYPES.Project,
            properties: { 'http://purl.org/dc/terms/title': 'Inferred Badge Test Project' },
          },
        },
        {
          command: 'object.create',
          params: {
            type: TYPES.Person,
            properties: { 'http://xmlns.com/foaf/0.1/name': 'Inferred Badge Test Person' },
          },
        },
      ],
    });
    expect(createResp.ok()).toBeTruthy();
    const createData = await createResp.json();
    const projectIri = createData.results[0].iri;
    const personIri = createData.results[1].iri;

    // 2. Add one-sided hasParticipant relationship
    const patchResp = await api.post(`${BASE_URL}/api/commands`, {
      headers,
      data: {
        command: 'object.patch',
        params: {
          iri: projectIri,
          properties: { 'urn:sempkm:model:basic-pkm:hasParticipant': personIri },
        },
      },
    });
    expect(patchResp.ok()).toBeTruthy();

    // 3. Run inference
    const inferResp = await api.post(`${BASE_URL}/api/inference/run`, { headers });
    expect(inferResp.ok()).toBeTruthy();
    const inferData = await inferResp.json();
    expect(inferData.total_inferred).toBeGreaterThan(0);

    // 4. Open the Person object in workspace and check relations panel
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openObjectTab(ownerPage, personIri, 'Inferred Badge Test Person');
    await waitForIdle(ownerPage);

    // Wait for the relations panel to load in the right pane
    const relationsPanel = ownerPage.locator('.relations-panel');
    await expect(relationsPanel).toBeVisible({ timeout: 15000 });

    // Look for the inferred badge
    const inferredBadge = relationsPanel.locator('.inferred-badge');
    await expect(inferredBadge.first()).toBeVisible({ timeout: 10000 });
    await expect(inferredBadge.first()).toContainText('inferred');
  });
});

test.describe('Clear & Reload Button', () => {
  test('clear and reload button exists in user popover', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // The popover content exists in the DOM (using HTML popover API).
    // Check the button is present in DOM without needing to open the popover.
    const clearBtn = ownerPage.locator('#user-popover .popover-item', {
      hasText: 'Clear',
    });
    await expect(clearBtn).toBeAttached({ timeout: 5000 });

    // Verify it contains "Clear & Reload" text
    await expect(clearBtn).toContainText('Reload');
  });
});
