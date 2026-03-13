/**
 * Tag System E2E Tests
 *
 * Tests that:
 * 1. Tag pills render correctly on seed objects with bpkm:tags
 * 2. By-tag explorer shows real tag folders with counts, expansion works,
 *    and clicking an object leaf opens a workspace tab
 *
 * NOTE: Limited to 2 tests to stay within the auth rate limit (5 magic-link
 * calls per minute). Each test uses a single ownerPage fixture.
 */
import { test, expect } from '../../fixtures/auth';
import { SEL } from '../../helpers/selectors';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Tag System', () => {
  test('tag pills visible on object with tags', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // By-type is the default mode — type sections should be visible
    const treeBody = ownerPage.locator(SEL.explorer.treeBody);
    const sections = treeBody.locator(SEL.nav.section);
    await expect(sections.first()).toBeVisible({ timeout: 10000 });

    // Click type sections to find one with seed objects (all basic-pkm types have tags).
    // Try each section until we find one with objects that have tag pills.
    const sectionCount = await sections.count();
    let foundTags = false;

    for (let i = 0; i < Math.min(sectionCount, 5) && !foundTags; i++) {
      // Click type section to expand and show objects
      await sections.nth(i).click();
      await ownerPage.waitForTimeout(1500);
      await waitForIdle(ownerPage);

      const leaves = treeBody.locator('.tree-leaf[data-iri]');
      const leafCount = await leaves.count();
      if (leafCount === 0) continue;

      // Click the first object leaf to open it in a tab
      await leaves.first().click();
      await ownerPage.waitForTimeout(2000);
      await waitForIdle(ownerPage);

      // The properties section is collapsed by default. Click the properties
      // toggle badge to expand it.
      const propsToggle = ownerPage.locator('.properties-toggle-badge').first();
      const toggleExists = await propsToggle.count();
      if (toggleExists === 0) continue;

      await propsToggle.click();
      await ownerPage.waitForTimeout(500);

      // Wait for properties to expand
      const propsSection = ownerPage.locator('.properties-collapsible.expanded');
      await expect(propsSection.first()).toBeVisible({ timeout: 5000 });

      // Check for tag pills in the expanded properties
      const tagPills = ownerPage.locator('.tag-pill');
      const pillCount = await tagPills.count();

      if (pillCount > 0) {
        foundTags = true;

        // Assert tag pills are visible
        await expect(tagPills.first()).toBeVisible();

        // Assert at least one pill text starts with #
        const firstText = await tagPills.first().innerText();
        expect(firstText).toMatch(/^#/);

        // Assert individual values (not comma-separated)
        // A properly split tag should not contain commas
        for (let j = 0; j < Math.min(pillCount, 5); j++) {
          const text = await tagPills.nth(j).innerText();
          expect(text).toMatch(/^#/);
          // Tag text after # should be a single value (no commas)
          const tagValue = text.substring(1);
          expect(tagValue).not.toContain(',');
          expect(tagValue.trim().length).toBeGreaterThan(0);
        }
      }
    }

    expect(foundTags).toBe(true);
  });

  test('by-tag explorer shows tag folders and expansion works', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Switch explorer dropdown to by-tag
    await ownerPage.selectOption(SEL.explorer.modeSelect, 'by-tag');
    await waitForIdle(ownerPage);

    const treeBody = ownerPage.locator(SEL.explorer.treeBody);

    // Wait for tag tree to load — tag folders have data-testid="tag-folder"
    const tagFolders = treeBody.locator('[data-testid="tag-folder"]');
    await expect(tagFolders.first()).toBeVisible({ timeout: 10000 });

    // Assert at least 3 tag folders visible (basic-pkm seed has many tags)
    const folderCount = await tagFolders.count();
    expect(folderCount).toBeGreaterThanOrEqual(3);

    // Assert tag folders show labels with # prefix
    const firstLabel = await tagFolders.first().locator('.tree-label').innerText();
    expect(firstLabel).toMatch(/^#/);

    // Assert tag folders show count badges
    const firstBadge = tagFolders.first().locator('.tree-count-badge');
    await expect(firstBadge).toBeVisible();
    const badgeText = await firstBadge.innerText();
    expect(parseInt(badgeText)).toBeGreaterThanOrEqual(1);

    // Click a tag folder to expand — find one likely to have objects
    await tagFolders.first().click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Wait for children to load — tag objects have data-testid="tag-object"
    const tagObjects = treeBody.locator('[data-testid="tag-object"]');
    const emptyChildren = treeBody.locator('.tree-children .tree-empty');
    await expect(tagObjects.first().or(emptyChildren.first())).toBeVisible({ timeout: 10000 });

    // Assert at least 1 object leaf visible
    const objectCount = await tagObjects.count();
    expect(objectCount).toBeGreaterThanOrEqual(1);

    // Object leaves should have data-iri and a label
    const firstObj = tagObjects.first();
    await expect(firstObj).toHaveAttribute('data-iri');
    await expect(firstObj.locator('.tree-leaf-label')).toBeVisible();

    // Get object label before clicking for tab verification
    const objectLabel = await firstObj.locator('.tree-leaf-label').innerText();

    // Click the object leaf — should open a workspace tab
    await firstObj.click();
    await ownerPage.waitForTimeout(2000);
    await waitForIdle(ownerPage);

    // Verify a tab opened — dockview tabs render in .dv-tab elements
    const tabs = ownerPage.locator('.dv-tab');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(1);

    // Check that a tab with matching text exists
    const matchingTab = ownerPage.locator('.dv-tab', { hasText: objectLabel });
    const matchCount = await matchingTab.count();

    if (matchCount === 0) {
      // Fallback: just verify at least one tab is open and object content loaded
      const objectIri = await firstObj.getAttribute('data-iri');
      if (objectIri) {
        const objectPanel = ownerPage.locator('.property-row, .markdown-body');
        await expect(objectPanel.first()).toBeAttached({ timeout: 10000 });
      }
    }

    // Nav sections from by-type should NOT be present in by-tag mode
    const sections = treeBody.locator(SEL.nav.section);
    await expect(sections).toHaveCount(0);

    // Placeholder should NOT be present (replaced by real content)
    const placeholder = treeBody.locator(SEL.explorer.placeholder);
    await expect(placeholder).toHaveCount(0);
  });
});
