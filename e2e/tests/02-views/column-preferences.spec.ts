/**
 * Column Visibility Preferences E2E Tests
 *
<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> gsd/M003/S10
 * Tests that table column visibility preferences persist via localStorage
 * using the ColumnPrefs API (column-prefs.js). Storage key format:
 * "col-prefs:{typeIri}" with value [{col, visible, order}].
 *
 * Consolidated into 1 test() function (API + UI) to stay within the
 * 5/minute magic-link rate limit.
<<<<<<< HEAD
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Column Preferences', () => {
  test('column prefs persist in localStorage and survive page reload', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // 1. Verify ColumnPrefs API is available on window
    const hasApi = await ownerPage.evaluate(() => {
      return typeof (window as any).ColumnPrefs === 'object'
        && typeof (window as any).ColumnPrefs.saveColumnPrefs === 'function'
        && typeof (window as any).ColumnPrefs.getVisibleColumns === 'function';
    });
    expect(hasApi).toBe(true);

    // 2. Save column prefs via the ColumnPrefs API
    const testTypeIri = 'urn:sempkm:test:column-prefs-type';
    await ownerPage.evaluate((typeIri) => {
      const prefs = [
        { col: 'title', visible: true, order: 0 },
        { col: 'status', visible: false, order: 1 },
        { col: 'priority', visible: true, order: 2 },
      ];
      (window as any).ColumnPrefs.saveColumnPrefs(typeIri, prefs);
    }, testTypeIri);

    // 3. Read back via ColumnPrefs API
    const savedPrefs = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(savedPrefs).toBeDefined();
    expect(savedPrefs).toHaveLength(3);
    expect(savedPrefs[0].col).toBe('title');
    expect(savedPrefs[0].visible).toBe(true);
    expect(savedPrefs[1].col).toBe('status');
    expect(savedPrefs[1].visible).toBe(false);

    // 4. Verify raw localStorage key format
    const rawStored = await ownerPage.evaluate((typeIri) => {
      return localStorage.getItem('col-prefs:' + typeIri);
    }, testTypeIri);
    expect(rawStored).toBeTruthy();
    const parsed = JSON.parse(rawStored!);
    expect(parsed).toHaveLength(3);
    expect(parsed[1].visible).toBe(false);

    // 5. Reload and verify persistence
    await ownerPage.reload();
    await waitForWorkspace(ownerPage);

    const afterReload = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(afterReload).toBeDefined();
    expect(afterReload).toHaveLength(3);
    expect(afterReload[1].col).toBe('status');
    expect(afterReload[1].visible).toBe(false);

    // 6. Toggle a column visible and verify update persists
    await ownerPage.evaluate((typeIri) => {
      const prefs = (window as any).ColumnPrefs.getVisibleColumns(typeIri);
      prefs[1].visible = true;
      (window as any).ColumnPrefs.saveColumnPrefs(typeIri, prefs);
    }, testTypeIri);

    const updatedPrefs = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(updatedPrefs[1].visible).toBe(true);
=======
 * Tests that table column visibility preferences persist via localStorage.
 * Uses column-prefs.js which stores visibility state in localStorage.
=======
>>>>>>> gsd/M003/S10
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Column Preferences', () => {
  test('column prefs persist in localStorage and survive page reload', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // 1. Verify ColumnPrefs API is available on window
    const hasApi = await ownerPage.evaluate(() => {
      return typeof (window as any).ColumnPrefs === 'object'
        && typeof (window as any).ColumnPrefs.saveColumnPrefs === 'function'
        && typeof (window as any).ColumnPrefs.getVisibleColumns === 'function';
    });
    expect(hasApi).toBe(true);

    // 2. Save column prefs via the ColumnPrefs API
    const testTypeIri = 'urn:sempkm:test:column-prefs-type';
    await ownerPage.evaluate((typeIri) => {
      const prefs = [
        { col: 'title', visible: true, order: 0 },
        { col: 'status', visible: false, order: 1 },
        { col: 'priority', visible: true, order: 2 },
      ];
      (window as any).ColumnPrefs.saveColumnPrefs(typeIri, prefs);
    }, testTypeIri);

    // 3. Read back via ColumnPrefs API
    const savedPrefs = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(savedPrefs).toBeDefined();
    expect(savedPrefs).toHaveLength(3);
    expect(savedPrefs[0].col).toBe('title');
    expect(savedPrefs[0].visible).toBe(true);
    expect(savedPrefs[1].col).toBe('status');
    expect(savedPrefs[1].visible).toBe(false);

    // 4. Verify raw localStorage key format
    const rawStored = await ownerPage.evaluate((typeIri) => {
      return localStorage.getItem('col-prefs:' + typeIri);
    }, testTypeIri);
    expect(rawStored).toBeTruthy();
    const parsed = JSON.parse(rawStored!);
    expect(parsed).toHaveLength(3);
    expect(parsed[1].visible).toBe(false);

<<<<<<< HEAD
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(stored!);
    expect(parsed.hiddenColumns).toContain('col-1');
>>>>>>> gsd/M003/S03
=======
    // 5. Reload and verify persistence
    await ownerPage.reload();
    await waitForWorkspace(ownerPage);

    const afterReload = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(afterReload).toBeDefined();
    expect(afterReload).toHaveLength(3);
    expect(afterReload[1].col).toBe('status');
    expect(afterReload[1].visible).toBe(false);

    // 6. Toggle a column visible and verify update persists
    await ownerPage.evaluate((typeIri) => {
      const prefs = (window as any).ColumnPrefs.getVisibleColumns(typeIri);
      prefs[1].visible = true;
      (window as any).ColumnPrefs.saveColumnPrefs(typeIri, prefs);
    }, testTypeIri);

    const updatedPrefs = await ownerPage.evaluate((typeIri) => {
      return (window as any).ColumnPrefs.getVisibleColumns(typeIri);
    }, testTypeIri);
    expect(updatedPrefs[1].visible).toBe(true);
>>>>>>> gsd/M003/S10
  });
});
