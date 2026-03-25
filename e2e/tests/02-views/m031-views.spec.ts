/**
 * M031 View Features E2E Tests
 *
 * Validates all major view changes from Milestone 031:
 *   - Carousel removal (S01): tab bar and carousel artifacts are absent
 *   - Generic view tabs (S02): openGenericViewTab opens table/card/graph/kanban
 *   - Kanban renderer (S03): board renders with status columns and cards
 *   - Scope binding (S04): scope dropdown present on generic views
 *   - Saved views (S05): save button present on generic views
 *   - Multiple instances (S06): same view type can open multiple tabs
 *
 * Uses the openGenericViewTab helper which wraps the workspace.js API.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { TYPES } from '../../fixtures/seed-data';
import { SEL } from '../../helpers/selectors';
import { openGenericViewTab, getTabCount } from '../../helpers/dockview';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('M031 View Features', () => {
  /**
   * S01 — Carousel Removal
   * The carousel tab bar (.carousel-tab-bar, .carousel-tab) was removed.
   * Generic views must not contain any carousel artifacts.
   */
  test('carousel tab bar is absent from generic views', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open a generic table view via the M031 API
    await openGenericViewTab(ownerPage, 'table', SEL.views.table, undefined, undefined, 15000);

    // Assert no carousel artifacts exist in the DOM
    const carouselBarCount = await ownerPage.locator('.carousel-tab-bar').count();
    expect(carouselBarCount).toBe(0);

    const carouselTabCount = await ownerPage.locator('.carousel-tab').count();
    expect(carouselTabCount).toBe(0);
  });

  /**
   * S02 — Generic View Tab Opening
   * openGenericViewTab('table') should create a dockview panel with a
   * table view rendered inside. The [data-testid="table-view"] element
   * should be visible.
   */
  test('generic view tab opens from explorer sidebar click', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open table view using the generic view tab helper
    await openGenericViewTab(ownerPage, 'table', SEL.views.table, undefined, undefined, 15000);

    // The table view data-testid should be visible
    await expect(ownerPage.locator(SEL.views.table)).toBeVisible({ timeout: 10000 });
  });

  /**
   * S03 — Kanban Renderer
   * Opening a kanban view for the Task type should render a board with
   * status columns. The basic-pkm seed data includes Tasks with
   * bpkm:taskStatus values that produce at least 2 columns.
   */
  test('kanban view renders board with status columns', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Pre-set the Task type in localStorage so the kanban view loads Task objects
    await ownerPage.evaluate((taskType) => {
      localStorage.setItem('sempkm_generic_type_kanban', taskType);
    }, TYPES.Task);

    // Open kanban view — wait for the .kanban-board container
    await openGenericViewTab(ownerPage, 'kanban', SEL.views.kanbanBoard, undefined, undefined, 15000);

    // Board should be visible
    await expect(ownerPage.locator(SEL.views.kanbanBoard)).toBeVisible({ timeout: 10000 });

    // Should have at least 2 status columns (e.g. "To Do", "In Progress", "Done")
    const columnCount = await ownerPage.locator(SEL.views.kanbanColumn).count();
    expect(columnCount).toBeGreaterThanOrEqual(2);

    // At least 1 card should be rendered (seed data has 4 Tasks)
    const cardCount = await ownerPage.locator(SEL.views.kanbanCard).count();
    expect(cardCount).toBeGreaterThanOrEqual(1);
  });

  /**
   * S04 — Scope Binding
   * Generic views include a view-scope-select dropdown that binds to saved
   * SPARQL queries. Even if no saved queries exist, the <select> element
   * should be present in the DOM.
   */
  test('view scope dropdown is present on generic views', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openGenericViewTab(ownerPage, 'table', SEL.views.table, undefined, undefined, 15000);
    await waitForIdle(ownerPage);

    // The scope select should be attached to the DOM (may be hidden if no saved queries)
    const scopeSelectCount = await ownerPage.locator(SEL.views.scopeSelect).count();
    expect(scopeSelectCount).toBeGreaterThanOrEqual(1);
  });

  /**
   * S05 — Saved Views CRUD
   * The save-view button is present on the view toolbar for all generic views.
   * Clicking it would invoke saveCurrentView(), but here we just check presence.
   */
  test('save view button is present on generic views', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    await openGenericViewTab(ownerPage, 'table', SEL.views.table, undefined, undefined, 15000);
    await waitForIdle(ownerPage);

    // The save-view button should be present in the toolbar
    const saveBtn = ownerPage.locator(SEL.views.saveViewBtn);
    const saveBtnCount = await saveBtn.count();
    expect(saveBtnCount).toBeGreaterThanOrEqual(1);
  });

  /**
   * S06 — Multiple View Instances
   * Opening the same renderer type twice (without a scope) should create
   * two separate dockview panels, incrementing the tab count.
   */
  test('multiple instances of same view type create separate tabs', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Wait for dockview to be available
    await ownerPage.waitForFunction(
      () => (window as any).SemPKM._dockview != null,
      { timeout: 10000 },
    );

    // Record initial tab count
    const initialCount = await getTabCount(ownerPage);

    // Open first table view
    await openGenericViewTab(ownerPage, 'table', SEL.views.table, undefined, undefined, 15000);
    const afterFirst = await getTabCount(ownerPage);
    expect(afterFirst).toBeGreaterThan(initialCount);

    // Open second table view — unscoped calls use timestamp IDs so they always create new tabs
    await openGenericViewTab(ownerPage, 'table', SEL.views.table, undefined, undefined, 15000);
    const afterSecond = await getTabCount(ownerPage);
    expect(afterSecond).toBeGreaterThan(afterFirst);
  });
});
