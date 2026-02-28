/**
 * Edit Object UI Regression Tests
 *
 * Regression coverage for bugs fixed during post-v2.0 live walkthrough sessions:
 *
 * Bug: Reference fields showed raw IRIs instead of labels in read view (7f13384)
 * Bug: object_read.html closest() TypeError in some click handlers (8bfdcf3)
 * Bug: toggleObjectMode set "Done" instead of "Cancel" on the mode toggle button (608b2fb)
 * Bug: Autocomplete dropdown used position:fixed causing off-screen rendering (608b2fb)
 * Bug: Multi-value reference fields only saved the first value (8bfdcf3, cdd9b2b)
 * Bug: objectSaved HX-Trigger handler did not update the tab bar label (608b2fb)
 *
 * Note: Tests use seed objects (installed by the Basic PKM Mental Model) rather than
 * objects created via the API commands endpoint. The commands API uses a base_namespace
 * type IRI that doesn't match SHACL sh:targetClass IRIs, so API-created objects would
 * show "No form schema available". Seed objects have the correct bpkm: type IRIs.
 */
import { test, expect } from '../../fixtures/auth';
import { SEED } from '../../fixtures/seed-data';
import { waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

/** Load an object into the active editor area via htmx (no tab bar entry). */
async function loadObjectInEditor(page: any, iri: string, mode: 'read' | 'edit' = 'read') {
  await page.evaluate(({ iri, mode }: { iri: string; mode: string }) => {
    const target = document.querySelector('#editor-area-group-1');
    if (target && (window as any).htmx) {
      (window as any).htmx.ajax(
        'GET',
        `/browser/object/${encodeURIComponent(iri)}?mode=${mode}`,
        { target },
      );
    }
  }, { iri, mode });
}

/** Open an object as a tab (adds to tab bar + loads content). */
async function openTab(page: any, iri: string, label: string, mode: 'read' | 'edit' = 'read') {
  await page.evaluate(
    ({ iri, label, mode }: { iri: string; label: string; mode: string }) => {
      if (typeof (window as any).openTab === 'function') {
        (window as any).openTab(iri, label, mode);
      }
    },
    { iri, label, mode },
  );
}

/** Trigger htmx form submit on #object-form (equivalent to Save button / Ctrl+S). */
async function submitObjectForm(page: any) {
  await page.evaluate(() => {
    const form = document.getElementById('object-form') as HTMLFormElement | null;
    if (form && (window as any).htmx) {
      (window as any).htmx.trigger(form, 'submit');
    }
  });
}

// ---------------------------------------------------------------------------

test.describe('Read View – Reference Field Regressions', () => {
  test('reference fields show human-readable labels, not raw IRIs', async ({ ownerPage }) => {
    // The architecture note is linked to the "Event Sourcing" concept.
    // Bug: ref-pills rendered the raw IRI (urn:sempkm:...) instead of the resolved label.
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await loadObjectInEditor(ownerPage, SEED.notes.architecture.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    const refPills = ownerPage.locator('.ref-pill');
    await expect(refPills.first()).toBeVisible({ timeout: 5000 });

    const count = await refPills.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i++) {
      const text = (await refPills.nth(i).textContent())?.trim() ?? '';
      // Raw IRIs start with "urn:" or "http(s)://" — labels should not
      expect(text).not.toMatch(/^(urn:|https?:\/\/)/);
      expect(text.length).toBeGreaterThan(0);
    }
  });

  test('known concept label appears as ref-pill in read view', async ({ ownerPage }) => {
    // Specifically verify "Event Sourcing" appears as a label pill on the architecture note.
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await loadObjectInEditor(ownerPage, SEED.notes.architecture.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // The architecture note has bpkm:isAbout → seed-concept-event-sourcing ("Event Sourcing")
    const eventSourcingPill = ownerPage.locator('.ref-pill', { hasText: 'Event Sourcing' });
    await expect(eventSourcingPill).toBeVisible({ timeout: 5000 });
  });

  test('no TypeError from closest() when clicking in read view', async ({ ownerPage }) => {
    // Bug: object_read.html used e.target.closest() without a typeof guard,
    // causing TypeError ("closest is not a function") in some click paths.
    const errors: string[] = [];
    ownerPage.on('pageerror', (err) => errors.push(err.message));

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await loadObjectInEditor(ownerPage, SEED.notes.architecture.iri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Click a ref-pill (the interaction that originally triggered the error)
    const refPill = ownerPage.locator('.ref-pill').first();
    if (await refPill.count() > 0) {
      await refPill.click({ force: true });
      await waitForIdle(ownerPage);
    }

    // Click inside the properties area
    const propsArea = ownerPage.locator('.object-read-properties, .object-properties').first();
    if (await propsArea.count() > 0) {
      await propsArea.click({ position: { x: 5, y: 5 }, force: true });
    }

    const typeErrors = errors.filter(
      (e) => e.toLowerCase().includes('typeerror') && e.toLowerCase().includes('closest'),
    );
    expect(typeErrors).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------

test.describe('Edit Mode – UI Regression Tests', () => {
  test('Cancel button text is "Cancel" when entering edit mode', async ({ ownerPage }) => {
    // Bug: toggleObjectMode was setting the mode-toggle button text to "Done"
    // instead of "Cancel" when switching from read to edit mode.
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // The mode toggle button is visible in read mode
    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await expect(toggleBtn).toBeVisible({ timeout: 5000 });

    // Click to enter edit mode
    await toggleBtn.click();
    await ownerPage.waitForSelector('[data-testid="object-form"]', { timeout: 10000 });

    // After entering edit mode the button must say "Cancel", not "Done" or anything else
    await expect(toggleBtn).toHaveText('Cancel');
  });

  test('autocomplete dropdown appears when typing in a reference search field', async ({ ownerPage }) => {
    // Bug: .suggestions-dropdown used position:fixed which rendered it off-screen.
    // Fix: changed to position:absolute, top:100% so it appears below the input.
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title, 'edit');
    await ownerPage.waitForSelector('[data-testid="object-form"]', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // "About Concepts" is a reference field in the Relationships group (open by default)
    const aboutField = ownerPage.locator('.form-field', { hasText: 'About Concepts' }).first();
    const searchInput = aboutField.locator('input[type="text"].reference-search').first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });

    // Type to trigger the htmx-powered autocomplete
    await searchInput.clear();
    await searchInput.pressSequentially('Event', { delay: 60 });

    // Dropdown should appear below the input with at least one suggestion
    const dropdown = aboutField.locator('.suggestions-dropdown').first();
    await expect(dropdown).toBeVisible({ timeout: 8000 });

    const suggestions = dropdown.locator('.suggestion-item');
    await expect(suggestions.first()).toBeVisible({ timeout: 5000 });

    // Verify dropdown is positioned within the visible viewport (not off-screen)
    const dropdownBox = await dropdown.boundingBox();
    expect(dropdownBox).not.toBeNull();
    const viewport = ownerPage.viewportSize()!;
    expect(dropdownBox!.y).toBeGreaterThanOrEqual(0);
    // Allow a small buffer for dropdowns near the bottom of the viewport
    expect(dropdownBox!.y).toBeLessThan(viewport.height + 50);
  });

  test('autocomplete: selecting a suggestion populates the hidden IRI input', async ({ ownerPage }) => {
    // Verify that clicking a suggestion correctly wires up the hidden input value
    // and clears the dropdown — the foundation for reference field saves to work.
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, SEED.notes.architecture.iri, SEED.notes.architecture.title, 'edit');
    await ownerPage.waitForSelector('[data-testid="object-form"]', { timeout: 10000 });
    await waitForIdle(ownerPage);

    const aboutField = ownerPage.locator('.form-field', { hasText: 'About Concepts' }).first();
    const firstItem = aboutField.locator('.multi-value-item').first();
    const searchInput = firstItem.locator('input[type="text"].reference-search');
    const hiddenInput = firstItem.locator('input[type="hidden"]');

    await searchInput.clear();
    await searchInput.pressSequentially('Knowledge', { delay: 60 });

    const dropdown = firstItem.locator('.suggestions-dropdown');
    await expect(dropdown).toBeVisible({ timeout: 8000 });

    // Click the Knowledge Management suggestion
    const kmSuggestion = dropdown.locator('.suggestion-item', { hasText: 'Knowledge Management' }).first();
    await kmSuggestion.click();
    await waitForIdle(ownerPage);

    // The visible input should show the label
    await expect(searchInput).toHaveValue('Knowledge Management');

    // The hidden input should hold the IRI (not empty, not the label)
    const hiddenValue = await hiddenInput.inputValue();
    expect(hiddenValue).toBe(SEED.concepts.km.iri);

    // Dropdown should be dismissed
    await expect(dropdown).toBeEmpty();
  });

  test('multi-value reference field: all values persist after save', async ({ ownerPage }) => {
    // Bug: save_object set properties[key] = values[0] instead of the full values list.
    // As a result, only the first reference was saved when multiple were submitted.
    // The SPARQL DELETE cross-join bug (one transaction_update per pattern) is also
    // exercised by this save path.
    //
    // Uses the "Graph Visualization" seed note which starts with no About Concepts
    // linked, giving a clean starting state. The test is idempotent — it checks that
    // BOTH target concepts are present after save, regardless of prior state.
    const noteIri = SEED.notes.graphViz.iri;

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, noteIri, SEED.notes.graphViz.title, 'edit');
    await ownerPage.waitForSelector('[data-testid="object-form"]', { timeout: 10000 });
    await waitForIdle(ownerPage);

    const aboutField = ownerPage.locator('.form-field', { hasText: 'About Concepts' }).first();

    // --- First concept: Knowledge Management (in first slot) ---
    const firstItem = aboutField.locator('.multi-value-item').first();
    const firstSearch = firstItem.locator('input[type="text"].reference-search');
    await firstSearch.clear();
    await firstSearch.pressSequentially('Knowledge', { delay: 60 });

    const firstDropdown = firstItem.locator('.suggestions-dropdown');
    await expect(firstDropdown).toBeVisible({ timeout: 8000 });
    await firstDropdown.locator('.suggestion-item', { hasText: 'Knowledge Management' }).first().click();
    await waitForIdle(ownerPage);

    // Verify first selection landed
    await expect(firstItem.locator('input[type="hidden"]')).toHaveValue(SEED.concepts.km.iri);

    // --- Add a second slot and pick Semantic Web ---
    const addBtn = aboutField.locator('.btn-add-value');
    await addBtn.click();

    const secondItem = aboutField.locator('.multi-value-item').nth(1);
    await expect(secondItem).toBeVisible({ timeout: 5000 });

    const secondSearch = secondItem.locator('input[type="text"].reference-search');
    await secondSearch.pressSequentially('Semantic', { delay: 60 });

    const secondDropdown = secondItem.locator('.suggestions-dropdown');
    await expect(secondDropdown).toBeVisible({ timeout: 8000 });
    await secondDropdown.locator('.suggestion-item', { hasText: 'Semantic Web' }).first().click();
    await waitForIdle(ownerPage);

    await expect(secondItem.locator('input[type="hidden"]')).toHaveValue(SEED.concepts.semanticWeb.iri);

    // --- Save ---
    await submitObjectForm(ownerPage);
    await ownerPage.waitForSelector('.form-success', { timeout: 10000 });
    await expect(ownerPage.locator('.form-success')).toContainText('saved');

    // --- Reload in read mode and verify both concepts appear as ref-pills ---
    await loadObjectInEditor(ownerPage, noteIri, 'read');
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    const pills = ownerPage.locator('.ref-pill');
    await expect(pills.first()).toBeVisible({ timeout: 5000 });

    const pillTexts = await pills.allTextContents();
    const normalized = pillTexts.map((t) => t.trim());

    expect(normalized.some((t) => t.includes('Knowledge Management'))).toBe(true);
    expect(normalized.some((t) => t.includes('Semantic Web'))).toBe(true);
  });

  test('title change updates the tab bar label after save', async ({ ownerPage }) => {
    // Bug: the objectSaved HX-Trigger handler did not update .tab-label in the tab bar
    // or .object-toolbar-title in the object toolbar when a new label was returned.
    //
    // Uses the kickoff seed note. After this test the note's title will be changed;
    // subsequent runs still verify the UPDATE behaviour (new title after save), so the
    // test remains valid on repeat runs without cleanup.
    const noteIri = SEED.notes.kickoff.iri;
    const updatedTitle = 'Kickoff Note – Title Updated By E2E';

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    // Open as a proper tab so the tab bar renders with an initial label
    await openTab(ownerPage, noteIri, SEED.notes.kickoff.title);
    await ownerPage.waitForSelector('.tab-label', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Switch to edit mode via the toolbar toggle
    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await toggleBtn.click();
    await ownerPage.waitForSelector('[data-testid="object-form"]', { timeout: 10000 });
    await waitForIdle(ownerPage);

    // Change the title (use the full dcterms:title IRI as the name attribute)
    const titleInput = ownerPage
      .locator('input[name="http://purl.org/dc/terms/title"]')
      .first();
    await expect(titleInput).toBeVisible({ timeout: 5000 });
    await titleInput.fill(updatedTitle);

    // Submit and wait for success
    await submitObjectForm(ownerPage);
    await ownerPage.waitForSelector('.form-success', { timeout: 10000 });

    // Wait for the objectSaved event to propagate and update the tab bar label
    await ownerPage.waitForFunction(
      (title: string) =>
        Array.from(document.querySelectorAll('.tab-label')).some((el) =>
          el.textContent?.includes(title),
        ),
      updatedTitle,
      { timeout: 5000 },
    );

    const tabBar = ownerPage.locator('.group-tab-bar');
    await expect(tabBar.locator('.tab-label', { hasText: updatedTitle })).toBeVisible();
  });

  test('title change updates the object toolbar title after save', async ({ ownerPage }) => {
    // Companion to the tab bar test: the .object-toolbar-title inside the object tab
    // should also update when objectSaved fires with a new label.
    const noteIri = SEED.notes.graphViz.iri;
    const updatedTitle = 'Graph Viz Note – Toolbar Title Updated By E2E';

    await ownerPage.goto(`${BASE_URL}/browser/`);
    await ownerPage.waitForSelector('[data-testid="workspace"]', { timeout: 15000 });

    await openTab(ownerPage, noteIri, SEED.notes.graphViz.title);
    await ownerPage.waitForSelector('.object-tab', { timeout: 10000 });
    await waitForIdle(ownerPage);

    const toggleBtn = ownerPage.locator('.mode-toggle').first();
    await toggleBtn.click();
    await ownerPage.waitForSelector('[data-testid="object-form"]', { timeout: 10000 });
    await waitForIdle(ownerPage);

    const titleInput = ownerPage
      .locator('input[name="http://purl.org/dc/terms/title"]')
      .first();
    await titleInput.fill(updatedTitle);

    await submitObjectForm(ownerPage);
    await ownerPage.waitForSelector('.form-success', { timeout: 10000 });

    // The object toolbar title (inside .object-tab) should reflect the new value
    const toolbarTitle = ownerPage.locator('.object-tab .object-toolbar-title');
    await expect(toolbarTitle).toHaveText(updatedTitle, { timeout: 5000 });
  });
});
