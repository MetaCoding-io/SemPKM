/**
 * LLM Config E2E Tests
 *
 * Tests LLM configuration endpoints:
 * - PUT /browser/llm/config (save config)
 * - POST /browser/llm/test (test connection)
 * - POST /browser/llm/models (list available models)
 */
import { test, expect, BASE_URL } from '../../fixtures/auth';

test.describe('LLM Config', () => {
  test('save LLM config endpoint accepts configuration', async ({ ownerRequest }) => {
    const resp = await ownerRequest.put(`${BASE_URL}/browser/llm/config`, {
      data: {
        provider: 'openai',
        api_key: 'sk-test-not-real-key',
        model: 'gpt-4',
        base_url: '',
      },
    });
    // Should accept the config (200) or return validation error (422)
    expect([200, 422].includes(resp.status())).toBeTruthy();
  });

  test('test LLM connection endpoint responds', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/browser/llm/test`);
    // Without a real API key, this should return an error status but not 500
    expect(resp.status()).toBeLessThan(500);
  });

  test('list LLM models endpoint responds', async ({ ownerRequest }) => {
    const resp = await ownerRequest.post(`${BASE_URL}/browser/llm/models`);
    // May succeed with models list or fail gracefully without API key
    expect(resp.status()).toBeLessThan(500);
  });
});
