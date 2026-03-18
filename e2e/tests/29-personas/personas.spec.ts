/**
 * Persona E2E Tests
 *
 * Validates persona features (PERSONA-01 through PERSONA-05):
 * - REST API CRUD lifecycle (create, list, rename, get, delete)
 * - Default persona auto-creation on first workspace load
 * - Persona selector UI in the sidebar user popover
 * - Command palette persona entries
 * - Persona activation switching via API
 *
 * Uses the standard auth fixtures and wait helpers.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

test.describe('Personas', () => {
  test('persona CRUD via API', async ({ ownerRequest }) => {
    // --- Create ---
    const createResp = await ownerRequest.post(`${BASE_URL}/api/personas`, {
      data: { name: 'E2E Test Persona' },
    });
    expect(createResp.status()).toBe(201);
    const created = await createResp.json();
    expect(created.id).toBeTruthy();
    expect(created.name).toBe('E2E Test Persona');

    const personaId = created.id;

    try {
      // --- List (contains created persona) ---
      const listResp = await ownerRequest.get(`${BASE_URL}/api/personas`);
      expect(listResp.status()).toBe(200);
      const personas = await listResp.json();
      expect(Array.isArray(personas)).toBe(true);
      expect(personas.some((p: any) => p.id === personaId)).toBe(true);

      // --- Rename ---
      const renameResp = await ownerRequest.put(`${BASE_URL}/api/personas/${personaId}`, {
        data: { name: 'Renamed E2E Persona' },
      });
      expect(renameResp.status()).toBe(200);

      // --- Get (verify rename) ---
      const getResp = await ownerRequest.get(`${BASE_URL}/api/personas/${personaId}`);
      expect(getResp.status()).toBe(200);
      const fetched = await getResp.json();
      expect(fetched.name).toBe('Renamed E2E Persona');

      // --- Delete ---
      const deleteResp = await ownerRequest.delete(`${BASE_URL}/api/personas/${personaId}`);
      expect(deleteResp.status()).toBe(204);

      // --- Verify deleted ---
      const afterList = await ownerRequest.get(`${BASE_URL}/api/personas`);
      const afterPersonas = await afterList.json();
      expect(afterPersonas.some((p: any) => p.id === personaId)).toBe(false);
    } catch (e) {
      // Cleanup on failure
      await ownerRequest.delete(`${BASE_URL}/api/personas/${personaId}`);
      throw e;
    }
  });

  test('default persona auto-created on first workspace load', async ({
    ownerPage,
    ownerRequest,
  }) => {
    // Navigate to workspace — initPersonas() runs and auto-creates "Default" if none exist
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Give initPersonas time to complete its fetch + possible creation
    await ownerPage.waitForTimeout(2000);

    // Verify at least one persona exists via API
    const listResp = await ownerRequest.get(`${BASE_URL}/api/personas`);
    expect(listResp.status()).toBe(200);
    const personas = await listResp.json();
    expect(personas.length).toBeGreaterThanOrEqual(1);

    // At least one should be active
    const hasActive = personas.some((p: any) => p.is_active === true);
    expect(hasActive).toBe(true);
  });

  test('persona selector visible in sidebar user popover', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);
    await ownerPage.waitForTimeout(1000);

    // Click the user avatar/popover trigger in the sidebar
    await ownerPage.click('button[popovertarget="user-popover"]');

    // Wait for the persona selector partial to load (hx-get fires on popover open)
    await ownerPage.waitForSelector('.persona-selector', { state: 'visible', timeout: 10000 });

    // Assert the persona selector UI is visible
    const selector = ownerPage.locator('.persona-selector');
    await expect(selector).toBeVisible();

    // Verify the selector header is present
    await expect(ownerPage.locator('.persona-selector-title')).toHaveText('Personas');

    // Verify at least one persona item or the "Save Current" button is visible
    const hasItems = await ownerPage.locator('.persona-selector-item').count();
    const hasSaveBtn = await ownerPage.locator('.persona-selector-save').isVisible();
    expect(hasItems > 0 || hasSaveBtn).toBe(true);
  });

  test('command palette has persona commands', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open command palette
    await ownerPage.keyboard.press('Alt+k');
    await ownerPage.waitForTimeout(500);

    // Check that persona commands exist in the ninja-keys data
    const personaCommands = await ownerPage.evaluate(() => {
      const ninja = document.querySelector('ninja-keys') as any;
      if (!ninja || !ninja.data) return { switch: false, save: false, create: false };
      return {
        switch: ninja.data.some(
          (d: any) => d.id === 'persona-switch' && d.section === 'Persona',
        ),
        save: ninja.data.some(
          (d: any) => d.id === 'persona-save' && d.section === 'Persona',
        ),
        create: ninja.data.some(
          (d: any) => d.id === 'persona-create' && d.section === 'Persona',
        ),
      };
    });

    expect(personaCommands.switch).toBe(true);
    expect(personaCommands.save).toBe(true);
    expect(personaCommands.create).toBe(true);
  });

  test('persona activation via API switches active persona', async ({ ownerRequest }) => {
    // Ensure at least one persona exists by listing
    const initialList = await ownerRequest.get(`${BASE_URL}/api/personas`);
    const initialPersonas = await initialList.json();
    expect(initialPersonas.length).toBeGreaterThanOrEqual(1);

    // Create a second persona for activation testing
    const createResp = await ownerRequest.post(`${BASE_URL}/api/personas`, {
      data: { name: 'Second Persona E2E' },
    });
    expect(createResp.status()).toBe(201);
    const secondPersona = await createResp.json();
    const secondId = secondPersona.id;

    try {
      // Note: POST /api/personas auto-activates the new persona,
      // so secondPersona should already be active.
      // Let's verify by listing all.
      const afterCreate = await ownerRequest.get(`${BASE_URL}/api/personas`);
      const afterCreateList = await afterCreate.json();
      const secondInList = afterCreateList.find((p: any) => p.id === secondId);
      expect(secondInList.is_active).toBe(true);

      // Find a persona that is NOT the second one (should now be inactive)
      const otherPersona = afterCreateList.find((p: any) => p.id !== secondId);
      expect(otherPersona).toBeDefined();
      expect(otherPersona.is_active).toBe(false);

      // Activate the other persona explicitly
      const activateResp = await ownerRequest.post(
        `${BASE_URL}/api/personas/${otherPersona.id}/activate`,
      );
      expect(activateResp.status()).toBe(200);
      const activated = await activateResp.json();
      expect(activated.is_active).toBe(true);

      // Verify list: the other persona is active, second is not
      const finalList = await ownerRequest.get(`${BASE_URL}/api/personas`);
      const finalPersonas = await finalList.json();
      const secondFinal = finalPersonas.find((p: any) => p.id === secondId);
      const otherFinal = finalPersonas.find((p: any) => p.id === otherPersona.id);
      expect(secondFinal.is_active).toBe(false);
      expect(otherFinal.is_active).toBe(true);
    } finally {
      // Cleanup: delete the test persona
      await ownerRequest.delete(`${BASE_URL}/api/personas/${secondId}`);
    }
  });
});
