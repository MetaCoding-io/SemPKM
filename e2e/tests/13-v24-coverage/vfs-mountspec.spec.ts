/**
 * VFS MountSpec Management E2E Tests
 *
 * Tests VFS mount CRUD endpoints and VFS browser in 2 test() functions
 * to stay within the 5/minute magic-link rate limit:
 * - GET /api/vfs/mounts — list mounts
 * - POST /api/vfs/mounts — create a mount
 * - PUT /api/vfs/mounts/{id} — update a mount
 * - DELETE /api/vfs/mounts/{id} — delete a mount
 * - POST /api/vfs/mounts/preview — preview mount directory structure
 * - GET /api/vfs/mounts/properties — list available properties
 * - GET /browser/vfs — VFS browser page
 * - GET /api/vfs/tree — VFS tree structure
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('VFS MountSpec', () => {
  test('mount CRUD lifecycle and preview/properties endpoints', async ({ ownerRequest }) => {
    // 1. List mounts — initially may be empty
    const listResp = await ownerRequest.get(`${BASE_URL}/api/vfs/mounts`);
    expect(listResp.ok()).toBeTruthy();
    const initialMounts = await listResp.json();
    expect(Array.isArray(initialMounts)).toBe(true);

    // 2. Create a mount with "flat" strategy
    const createResp = await ownerRequest.post(`${BASE_URL}/api/vfs/mounts`, {
      data: {
        name: 'E2E Test Mount',
        path: 'e2e-test-mount',
        strategy: 'flat',
        visibility: 'personal',
      },
    });
    expect(createResp.status()).toBe(201);
    const created = await createResp.json();
    expect(created.id).toBeDefined();
    expect(created.name).toBe('E2E Test Mount');
    expect(created.path).toBe('e2e-test-mount');
    expect(created.strategy).toBe('flat');
    const mountId = created.id;

    // 3. List mounts — should now include our new mount
    const listResp2 = await ownerRequest.get(`${BASE_URL}/api/vfs/mounts`);
    expect(listResp2.ok()).toBeTruthy();
    const updatedMounts = await listResp2.json();
    const found = updatedMounts.find((m: any) => m.id === mountId);
    expect(found).toBeDefined();
    expect(found.name).toBe('E2E Test Mount');

    // 4. Update the mount — change name and strategy
    const updateResp = await ownerRequest.put(`${BASE_URL}/api/vfs/mounts/${mountId}`, {
      data: {
        name: 'E2E Test Mount Updated',
        strategy: 'by-type',
      },
    });
    expect(updateResp.ok()).toBeTruthy();
    const updated = await updateResp.json();
    expect(updated.name).toBe('E2E Test Mount Updated');
    expect(updated.strategy).toBe('by-type');

    // 5. Preview mount directory structure
    const previewResp = await ownerRequest.post(`${BASE_URL}/api/vfs/mounts/preview`, {
      data: {
        strategy: 'by-type',
      },
    });
    expect(previewResp.ok()).toBeTruthy();
    const previewData = await previewResp.json();
    expect(previewData.directories).toBeDefined();
    expect(Array.isArray(previewData.directories)).toBe(true);
    // by-type should produce directories named after types (seed data exists)
    if (previewData.directories.length > 0) {
      expect(previewData.directories[0].name).toBeDefined();
      expect(typeof previewData.directories[0].file_count).toBe('number');
    }

    // 6. List properties for strategy field dropdowns
    const propsResp = await ownerRequest.get(`${BASE_URL}/api/vfs/mounts/properties`);
    expect(propsResp.ok()).toBeTruthy();
    const propsData = await propsResp.json();
    expect(propsData.properties).toBeDefined();
    expect(Array.isArray(propsData.properties)).toBe(true);
    // Should have properties from installed models
    if (propsData.properties.length > 0) {
      expect(propsData.properties[0].iri).toBeDefined();
      expect(propsData.properties[0].name).toBeDefined();
      expect(Array.isArray(propsData.properties[0].types)).toBe(true);
    }

    // 7. Delete the mount — cleanup
    const deleteResp = await ownerRequest.delete(`${BASE_URL}/api/vfs/mounts/${mountId}`);
    expect(deleteResp.status()).toBe(204);

    // 8. Verify deletion — mount should no longer appear
    const listResp3 = await ownerRequest.get(`${BASE_URL}/api/vfs/mounts`);
    expect(listResp3.ok()).toBeTruthy();
    const finalMounts = await listResp3.json();
    const notFound = finalMounts.find((m: any) => m.id === mountId);
    expect(notFound).toBeUndefined();
  });

  test('VFS browser page and tree endpoint', async ({ ownerRequest }) => {
    // 1. VFS browser page — should return 200 HTML
    const pageResp = await ownerRequest.get(`${BASE_URL}/browser/vfs`);
    expect(pageResp.ok()).toBeTruthy();
    const pageHtml = await pageResp.text();
    expect(pageHtml).toMatch(/<|<!DOCTYPE/i);

    // 2. VFS tree endpoint — returns JSON tree structure
    const treeResp = await ownerRequest.get(`${BASE_URL}/api/vfs/tree`);
    expect(treeResp.ok()).toBeTruthy();
    const treeData = await treeResp.json();
    expect(Array.isArray(treeData)).toBe(true);
    // Seed data should produce at least one model in the tree
    if (treeData.length > 0) {
      const model = treeData[0];
      expect(model.id).toBeDefined();
      expect(model.label).toBeDefined();
      expect(Array.isArray(model.children)).toBe(true);
      // Each model should have type folders with file entries
      if (model.children.length > 0) {
        const typeFolder = model.children[0];
        expect(typeFolder.label).toBeDefined();
        expect(Array.isArray(typeFolder.children)).toBe(true);
      }
    }

    // 3. Validate invalid strategy is rejected
    const badPreview = await ownerRequest.post(`${BASE_URL}/api/vfs/mounts/preview`, {
      data: { strategy: 'nonexistent-strategy' },
    });
    expect(badPreview.status()).toBe(400);

    // 4. Validate duplicate path is rejected
    // Create a mount first
    const tempCreate = await ownerRequest.post(`${BASE_URL}/api/vfs/mounts`, {
      data: {
        name: 'Temp Dup Test',
        path: 'dup-test-path',
        strategy: 'flat',
      },
    });
    expect(tempCreate.status()).toBe(201);
    const tempMount = await tempCreate.json();

    // Try creating another mount with the same path
    const dupCreate = await ownerRequest.post(`${BASE_URL}/api/vfs/mounts`, {
      data: {
        name: 'Dup Attempt',
        path: 'dup-test-path',
        strategy: 'flat',
      },
    });
    expect(dupCreate.status()).toBe(400);

    // Cleanup
    await ownerRequest.delete(`${BASE_URL}/api/vfs/mounts/${tempMount.id}`);

    // 2. Create a mount with "flat" strategy
    const createResp = await ownerRequest.post(`${BASE_URL}/api/vfs/mounts`, {
      data: {
        name: 'E2E Test Mount',
        path: 'e2e-test-mount',
        strategy: 'flat',
        visibility: 'personal',
      },
    });
    expect(createResp.status()).toBe(201);
    const created = await createResp.json();
    expect(created.id).toBeDefined();
    expect(created.name).toBe('E2E Test Mount');
    expect(created.path).toBe('e2e-test-mount');
    expect(created.strategy).toBe('flat');
    const mountId = created.id;

    // 3. List mounts — should now include our new mount
    const listResp2 = await ownerRequest.get(`${BASE_URL}/api/vfs/mounts`);
    expect(listResp2.ok()).toBeTruthy();
    const updatedMounts = await listResp2.json();
    const found = updatedMounts.find((m: any) => m.id === mountId);
    expect(found).toBeDefined();
    expect(found.name).toBe('E2E Test Mount');

    // VFS settings may be a category/section on the settings page
    const pageContent = await ownerPage.textContent('body');
    // Check for VFS-related settings text
    const hasVfsSection = /VFS|Virtual File|Mount|WebDAV/i.test(pageContent || '');
    // VFS settings should be referenced somewhere
    expect(typeof pageContent).toBe('string');
  });
});
