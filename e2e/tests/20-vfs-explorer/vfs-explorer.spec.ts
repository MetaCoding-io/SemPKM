/**
 * VFS Explorer Mode E2E Tests
 *
 * Tests that VFS mounts appear in the explorer dropdown, folders expand,
 * and object click-through opens workspace tabs.
 *
 * Setup: creates a by-type VFS mount via the API. Teardown: deletes it.
 * Limited to ≤5 tests to stay within auth magic-link rate limit.
 *
 * Mount creation/deletion uses the ownerRequest fixture passed to the
 * first/last test instead of beforeAll/afterAll to avoid extra magic-link
 * consumption. A shared module-level mountId coordinates between tests.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

let mountId: string;
const MOUNT_NAME = 'E2E Type Mount';
// Random suffix to avoid path collisions across test runs
const MOUNT_PATH = `e2e-mount-${Math.random().toString(36).slice(2, 8)}`;

/**
 * Ensure the test mount exists. Creates it if not already created.
 * Safe to call from any test — idempotent via module-level mountId guard.
 */
async function ensureMount(ownerRequest: import('@playwright/test').APIRequestContext) {
  if (mountId) return; // Already created

  // Clean up any stale E2E mounts from prior aborted runs
  const listResp = await ownerRequest.get(`${BASE_URL}/api/vfs/mounts`);
  if (listResp.ok()) {
    const mounts = await listResp.json();
    for (const m of mounts) {
      if (m.name === MOUNT_NAME) {
        await ownerRequest.delete(`${BASE_URL}/api/vfs/mounts/${m.id}`);
      }
    }
  }

  const resp = await ownerRequest.post(`${BASE_URL}/api/vfs/mounts`, {
    data: {
      name: MOUNT_NAME,
      path: MOUNT_PATH,
      strategy: 'by-type',
      sparql_scope: 'all',
      visibility: 'shared',
    },
  });
  expect(resp.status()).toBe(201);
  const body = await resp.json();
  mountId = body.id;
  expect(mountId).toBeTruthy();
}

/**
 * Select the mount mode in the explorer dropdown and wait for tree content.
 * Common setup for tests that need the mount tree loaded.
 */
async function selectMountMode(ownerPage: import('@playwright/test').Page) {
  await ownerPage.goto(`${BASE_URL}/browser/`);
  await waitForWorkspace(ownerPage);

  // Wait for async mount injection
  const dropdown = ownerPage.locator(SEL.explorer.modeSelect);
  await expect(dropdown.locator(SEL.explorer.mountOption).first()).toBeAttached({ timeout: 10000 });

  // Select the mount mode
  await ownerPage.selectOption(SEL.explorer.modeSelect, `mount:${mountId}`);
  await waitForIdle(ownerPage);

  const treeBody = ownerPage.locator(SEL.explorer.treeBody);
  const folders = treeBody.locator(SEL.explorer.mountFolderNode);
  const emptyState = treeBody.locator('.tree-empty');

  // Wait for content to appear (htmx swap)
  await expect(folders.first().or(emptyState.first())).toBeVisible({ timeout: 10000 });

  return { treeBody, folders, emptyState };
}

test.describe('VFS Explorer Modes', () => {
  test('mount option appears in explorer dropdown after page load', async ({ ownerPage, ownerRequest }) => {
    await ensureMount(ownerRequest);

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Wait for async mount injection (initExplorerMountOptions fetches /api/vfs/mounts).
    // <option> elements inside a <select> are never "visible" in Playwright —
    // they're part of the native dropdown widget. Use toBeAttached() instead.
    const dropdown = ownerPage.locator(SEL.explorer.modeSelect);
    const mountOptions = dropdown.locator(SEL.explorer.mountOption);
    await expect(mountOptions.first()).toBeAttached({ timeout: 10000 });

    // Verify our test mount appears by value
    const ourMount = dropdown.locator(`option[value="mount:${mountId}"]`);
    await expect(ourMount).toHaveCount(1);

    // Option text includes strategy suffix: "E2E Type Mount (by-type)"
    await expect(ourMount.first()).toHaveText(`${MOUNT_NAME} (by-type)`);

    // Verify mount is inside a VFS Mounts optgroup
    const optgroup = dropdown.locator('optgroup[label="VFS Mounts"]');
    await expect(optgroup).toHaveCount(1);
  });

  test('selecting mount mode loads tree with folder nodes', async ({ ownerPage, ownerRequest }) => {
    await ensureMount(ownerRequest);

    const { treeBody, folders } = await selectMountMode(ownerPage);

    const folderCount = await folders.count();
    const emptyState = treeBody.locator('.tree-empty');
    const emptyCount = await emptyState.count();

    // At least one of the two should be present
    expect(folderCount + emptyCount).toBeGreaterThanOrEqual(1);

    // If folders exist, they should have the tree-node structure
    if (folderCount > 0) {
      await expect(folders.first().locator('.tree-label')).toBeVisible();
    }

    // Built-in nav sections should NOT be present
    const navSections = treeBody.locator(SEL.nav.section);
    await expect(navSections).toHaveCount(0);
  });

  test('expanding a folder shows object leaves', async ({ ownerPage, ownerRequest }) => {
    await ensureMount(ownerRequest);

    const { treeBody, folders } = await selectMountMode(ownerPage);

    const folderCount = await folders.count();
    if (folderCount === 0) {
      test.skip(true, 'No mount folders available for expansion test');
      return;
    }

    // Click the first folder to trigger htmx lazy expansion
    await folders.first().click();
    await ownerPage.waitForTimeout(1500);
    await waitForIdle(ownerPage);

    // After expansion, look for object leaves or sub-empty state
    const objects = treeBody.locator(SEL.explorer.mountObjectLeaf);
    const childEmpty = treeBody.locator('.tree-children .tree-empty');

    // Wait for children to appear
    await expect(objects.first().or(childEmpty.first())).toBeVisible({ timeout: 10000 });

    const objectCount = await objects.count();
    if (objectCount > 0) {
      // Object leaves should have data-iri attribute and tree-leaf-label
      const firstObj = objects.first();
      await expect(firstObj).toHaveAttribute('data-iri');
      await expect(firstObj.locator('.tree-leaf-label')).toBeVisible();
    }
  });

  test('clicking an object leaf opens object tab (EXP-05)', async ({ ownerPage, ownerRequest }) => {
    await ensureMount(ownerRequest);

    const { treeBody, folders } = await selectMountMode(ownerPage);

    const folderCount = await folders.count();
    if (folderCount === 0) {
      test.skip(true, 'No mount folders — cannot test object click-through');
      return;
    }

    // Expand first folder
    await folders.first().click();
    await ownerPage.waitForTimeout(1500);
    await waitForIdle(ownerPage);

    const objects = treeBody.locator(SEL.explorer.mountObjectLeaf);
    const childEmpty = treeBody.locator('.tree-children .tree-empty');
    await expect(objects.first().or(childEmpty.first())).toBeVisible({ timeout: 10000 });

    const objectCount = await objects.count();
    if (objectCount === 0) {
      test.skip(true, 'No objects in mount folder — cannot test click-through');
      return;
    }

    // Get the object's label before clicking
    const firstObj = objects.first();
    const objectLabel = await firstObj.locator('.tree-leaf-label').innerText();
    const objectIri = await firstObj.getAttribute('data-iri');

    // Click the object leaf — should open a workspace tab
    await firstObj.click();
    await ownerPage.waitForTimeout(1500);
    await waitForIdle(ownerPage);

    // Verify a dockview tab opened — look for the tab by label or IRI.
    // dockview tabs render in .dv-tab elements with the object label.
    const tabs = ownerPage.locator('.dv-tab');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(1);

    // Check that a tab with matching text exists
    const matchingTab = ownerPage.locator('.dv-tab', { hasText: objectLabel });
    const matchCount = await matchingTab.count();

    if (matchCount === 0 && objectIri) {
      // Fallback: check that the object content area loaded
      const objectPanel = ownerPage.locator(`[data-iri="${objectIri}"]`);
      const panelExists = await objectPanel.count();
      expect(panelExists).toBeGreaterThanOrEqual(1);
    }
  });

  test('switching back to by-type restores normal tree', async ({ ownerPage, ownerRequest }) => {
    await ensureMount(ownerRequest);

    const { treeBody } = await selectMountMode(ownerPage);

    // Nav sections should NOT be present in mount mode
    const navSections = treeBody.locator(SEL.nav.section);
    await expect(navSections).toHaveCount(0);

    // Switch back to by-type
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'by-type');
    await waitForIdle(ownerPage);

    // Wait for nav sections to reappear
    await expect(navSections.first()).toBeVisible({ timeout: 10000 });
    const sectionCount = await navSections.count();
    expect(sectionCount).toBeGreaterThanOrEqual(1);

    // Mount-specific elements should be gone
    const mountFolders = treeBody.locator(SEL.explorer.mountFolderNode);
    await expect(mountFolders).toHaveCount(0);

    // Cleanup: delete the test mount after the last test
    if (mountId) {
      const resp = await ownerRequest.delete(`${BASE_URL}/api/vfs/mounts/${mountId}`);
      // Accept 204 (deleted) or 404 (already gone)
      expect([204, 404]).toContain(resp.status());
    }
  });
});
