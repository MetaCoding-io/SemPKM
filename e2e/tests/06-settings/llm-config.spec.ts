/**
 * LLM Config E2E Tests
 *
 * Tests LLM configuration endpoints (all owner-only):
 * - PUT /browser/llm/config (save config field)
 * - POST /browser/llm/test (test connection)
 * - POST /browser/llm/models (list available models)
 *
 * Consolidated into a single test() to stay within the
 * 5/minute magic-link rate limit.
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('LLM Config', () => {
  test('LLM config save, test, and models endpoints respond correctly', async ({ ownerRequest }) => {
    // 1. Save LLM config — PUT /browser/llm/config
    //    Sends a single field update (the actual API accepts {field, value})
    const saveResp = await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: {
        field: 'api_base_url',
        value: 'http://fake-llm-server:8080',
      },
    });
    expect(saveResp.ok()).toBeTruthy();
    const saveData = await saveResp.json();
    expect(saveData.ok).toBe(true);

    // Save another field — default_model
    const saveModelResp = await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: {
        field: 'default_model',
        value: 'gpt-4-test',
      },
    });
    expect(saveModelResp.ok()).toBeTruthy();

    // Save an API key (fake, for form mechanics verification)
    const saveKeyResp = await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: {
        field: 'api_key',
        value: 'sk-test-not-real-key-12345',
      },
    });
    expect(saveKeyResp.ok()).toBeTruthy();

    // 2. Test LLM connection — POST /browser/llm/test
    //    With the fake base_url, this should return an error HTML fragment
    //    (connection refused), but NOT a 500.
    const testResp = await ownerRequest.post(`${BASE_URL}/browser/llm/test`);
    expect(testResp.status()).toBeLessThan(500);
    const testHtml = await testResp.text();
    // Should return an HTML fragment (the test_result.html template)
    expect(testHtml.length).toBeGreaterThan(0);

    // 3. List LLM models — POST /browser/llm/models
    //    With the fake base_url, this should return HTML with an error
    //    message but not crash.
    const modelsResp = await ownerRequest.post(`${BASE_URL}/browser/llm/models`);
    expect(modelsResp.status()).toBeLessThan(500);
    const modelsHtml = await modelsResp.text();
    expect(modelsHtml.length).toBeGreaterThan(0);

    // 4. Clean up — reset to empty so other tests aren't affected
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'api_base_url', value: '' },
    });
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'api_key', value: '' },
    });
    await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: { field: 'default_model', value: '' },
    });
      data: {
        field: 'api_base_url',
        value: 'http://fake-llm-server:8080',
      },
    });
    expect(saveResp.ok()).toBeTruthy();
    const saveData = await saveResp.json();
    expect(saveData.ok).toBe(true);

    // Save another field — default_model
    const saveModelResp = await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: {
        field: 'default_model',
        value: 'gpt-4-test',
      },
    });
    expect(saveModelResp.ok()).toBeTruthy();

  test('list LLM models endpoint responds', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/browser/llm/models`);
    // May succeed with models list or fail gracefully without API key
    expect(resp.status()).toBeLessThan(500);
  });
});
