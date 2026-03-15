/**
 * Tag Hierarchy & Autocomplete E2E Tests
 *
 * Tests that:
 * 1. Hierarchical `/`-delimited tags render as nested folder nodes
 *    in the By Tag explorer, and expanding a folder shows sub-folders
 * 2. Tag folders show `.tree-count-badge` elements with correct counts,
 *    including on sub-folders after expansion
 * 3. Tag autocomplete input shows suggestion items when typing slowly
 *
 * Uses `ownerPage` fixture only (no `memberPage`) to stay within
 * the 5/min magic-link rate limit.
 *
 * Seed data has no hierarchical tags, so a setup step creates
 * objects with `/`-delimited tags via the command API.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

/**
 * Unique prefix to avoid collisions with other test data.
 * Creates a two-level hierarchy: e2ehier/alpha, e2ehier/beta
 */
const TAG_PREFIX = 'e2ehier';
const TAG_CHILD_A = `${TAG_PREFIX}/alpha`;
const TAG_CHILD_B = `${TAG_PREFIX}/beta`;
const TAGS_PREDICATE = 'urn:sempkm:model:basic-pkm:tags';

/**
 * Create test objects with hierarchical tags via the API.
 * Uses the ownerPage's request context so we share the auth session.
 * Idempotent: creates on best-effort, silently proceeds if already present.
 */
async function ensureHierarchicalTestData(ownerPage: import('@playwright/test').Page) {
  const cookies = await ownerPage.context().cookies();
  const sessionCookie = cookies.find((c) => c.name === 'sempkm_session');
  if (!sessionCookie) throw new Error('No session cookie on ownerPage');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Cookie: `sempkm_session=${sessionCookie.value}`,
  };

  const objects = [
    { title: 'Hierarchy Alpha Note 1', tag: TAG_CHILD_A },
    { title: 'Hierarchy Alpha Note 2', tag: TAG_CHILD_A },
    { title: 'Hierarchy Beta Note', tag: TAG_CHILD_B },
  ];

  for (const obj of objects) {
    try {
      await ownerPage.request.post(`${BASE_URL}/api/commands`, {
        headers,
        data: {
          command: 'object.create',
          params: {
            type: 'Note',
            properties: {
              'dcterms:title': obj.title,
              [TAGS_PREDICATE]: obj.tag,
            },
          },
        },
      });
    } catch {
      // Best-effort: data may already exist from a prior run
    }
  }
}

test.describe('Tag Hierarchy & Autocomplete', () => {

  test('hierarchical tag folders expand to show nested sub-folders', async ({ ownerPage }) => {
    // Create test data with hierarchical tags
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await ensureHierarchicalTestData(ownerPage);

    // Switch explorer to by-tag mode
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'by-tag');
    await waitForIdle(ownerPage);

    const treeBody = ownerPage.locator(SEL.explorer.treeBody);

    // Wait for tag folders to appear
    const tagFolders = treeBody.locator(SEL.tagHierarchy.folder);
    await expect(tagFolders.first()).toBeVisible({ timeout: 10000 });

    // Find the "e2ehier" root folder — it should be a folder node
    // (has_children=true) because it has children alpha and beta.
    // Folder nodes render without # prefix; leaf nodes render with #.
    const hierFolder = treeBody.locator(SEL.tagHierarchy.folder, {
      has: ownerPage.locator(SEL.tagHierarchy.treeLabel, { hasText: TAG_PREFIX }),
    });
    await expect(hierFolder).toBeVisible({ timeout: 10000 });

    // Click the folder to expand — htmx lazy-loads sub-folders
    await hierFolder.click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // After expansion, sub-folder nodes should appear inside the
    // .tree-children container that follows the folder node.
    // Look for sub-folders with labels "alpha" and "beta"
    const subFolders = treeBody.locator(
      `${SEL.tagHierarchy.treeChildren} ${SEL.tagHierarchy.folder}`,
    );
    await expect(subFolders.first()).toBeVisible({ timeout: 10000 });

    const subFolderCount = await subFolders.count();
    expect(subFolderCount).toBeGreaterThanOrEqual(2);

    // Verify "alpha" and "beta" labels are present in sub-folders
    const alphaFolder = treeBody.locator(SEL.tagHierarchy.folder, {
      has: ownerPage.locator(SEL.tagHierarchy.treeLabel, { hasText: 'alpha' }),
    });
    const betaFolder = treeBody.locator(SEL.tagHierarchy.folder, {
      has: ownerPage.locator(SEL.tagHierarchy.treeLabel, { hasText: 'beta' }),
    });
    await expect(alphaFolder).toBeVisible();
    await expect(betaFolder).toBeVisible();
  });

  test('tag folders show count badges with correct totals', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Switch to by-tag mode
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'by-tag');
    await waitForIdle(ownerPage);

    const treeBody = ownerPage.locator(SEL.explorer.treeBody);
    const tagFolders = treeBody.locator(SEL.tagHierarchy.folder);
    await expect(tagFolders.first()).toBeVisible({ timeout: 10000 });

    // Find the "e2ehier" root folder
    const hierFolder = treeBody.locator(SEL.tagHierarchy.folder, {
      has: ownerPage.locator(SEL.tagHierarchy.treeLabel, { hasText: TAG_PREFIX }),
    });
    await expect(hierFolder).toBeVisible({ timeout: 10000 });

    // Verify root folder badge — total should be >= 3 (2 alpha + 1 beta)
    const rootBadge = hierFolder.locator(SEL.tagHierarchy.countBadge);
    await expect(rootBadge).toBeVisible();
    const rootCount = parseInt(await rootBadge.innerText());
    expect(rootCount).toBeGreaterThanOrEqual(3);

    // Expand the folder
    await hierFolder.click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify sub-folder badges
    const alphaFolder = treeBody.locator(SEL.tagHierarchy.folder, {
      has: ownerPage.locator(SEL.tagHierarchy.treeLabel, { hasText: 'alpha' }),
    });
    await expect(alphaFolder).toBeVisible({ timeout: 10000 });

    const alphaBadge = alphaFolder.locator(SEL.tagHierarchy.countBadge);
    await expect(alphaBadge).toBeVisible();
    const alphaCount = parseInt(await alphaBadge.innerText());
    expect(alphaCount).toBeGreaterThanOrEqual(2);

    const betaFolder = treeBody.locator(SEL.tagHierarchy.folder, {
      has: ownerPage.locator(SEL.tagHierarchy.treeLabel, { hasText: 'beta' }),
    });
    await expect(betaFolder).toBeVisible();

    const betaBadge = betaFolder.locator(SEL.tagHierarchy.countBadge);
    await expect(betaBadge).toBeVisible();
    const betaCount = parseInt(await betaBadge.innerText());
    expect(betaCount).toBeGreaterThanOrEqual(1);
  });

  test('tag autocomplete shows suggestions when typing in edit form', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    const treeBody = ownerPage.locator(SEL.explorer.treeBody);

    // By-type is default — expand a type section to find an object
    const sections = treeBody.locator(SEL.nav.section);
    await expect(sections.first()).toBeVisible({ timeout: 10000 });

    // Click through type sections to find one with objects
    const sectionCount = await sections.count();
    let objectOpened = false;

    for (let i = 0; i < Math.min(sectionCount, 5) && !objectOpened; i++) {
      await sections.nth(i).click();
      await ownerPage.waitForTimeout(1500);
      await waitForIdle(ownerPage);

      const leaves = treeBody.locator('.tree-leaf[data-iri]');
      const leafCount = await leaves.count();
      if (leafCount === 0) continue;

      // Click the first object to open it in a tab
      await leaves.first().click();
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);
      objectOpened = true;
    }

    expect(objectOpened).toBe(true);

    // Switch to edit mode — click the "Edit" button (.mode-toggle)
    const editBtn = ownerPage.locator('button.mode-toggle').first();
    await expect(editBtn).toBeVisible({ timeout: 5000 });
    await editBtn.click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // The edit face is now visible. Properties may be collapsed.
    // Look for properties toggle badge and expand if collapsed.
    const propsToggle = ownerPage.locator('.properties-toggle-badge').first();
    const propsToggleExists = await propsToggle.count();
    if (propsToggleExists > 0) {
      // Check if the edit properties section is expanded
      const editProps = ownerPage.locator('.object-face-edit .properties-collapsible');
      const isExpanded = await editProps.evaluate(
        (el) => el.classList.contains('expanded'),
      ).catch(() => false);

      if (!isExpanded) {
        await propsToggle.click();
        await ownerPage.waitForTimeout(500);
      }
    }

    // Find the tag autocomplete input
    const tagInput = ownerPage.locator(SEL.tagHierarchy.autocompleteInput).first();
    await expect(tagInput).toBeVisible({ timeout: 10000 });

    // Clear any existing value first, then type slowly to trigger the
    // debounced htmx fetch (delay:200ms).
    // Use a search term that matches existing tags (e.g. "arch" -> "architecture").
    await tagInput.click();
    await tagInput.fill('');
    await ownerPage.waitForTimeout(300);

    // Now type slowly character-by-character
    await tagInput.pressSequentially('arch', { delay: 150 });

    // Wait for the filtered suggestions to appear — the htmx fetch has a
    // 200ms debounce plus network time, so allow generous timeout.
    // We need to wait for a suggestion matching "arch", not just any suggestion
    // (because the focus event may have loaded unfiltered results first).
    const matchingSuggestion = ownerPage.locator(
      `${SEL.tagHierarchy.suggestionItem}:has-text("arch")`,
    );
    await expect(matchingSuggestion.first()).toBeVisible({ timeout: 8000 });

    // Assert at least one suggestion containing "arch" is visible
    const suggestionCount = await matchingSuggestion.count();
    expect(suggestionCount).toBeGreaterThanOrEqual(1);

    // The suggestion should contain the typed text (case-insensitive match)
    const firstText = await matchingSuggestion.first().innerText();
    expect(firstText.toLowerCase()).toContain('arch');
  });

});
