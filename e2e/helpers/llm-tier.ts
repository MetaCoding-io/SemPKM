/**
 * LLM test tier auto-selection and configuration.
 *
 * Three tiers:
 *   - mock:   Mock LLM server (default, CI, fast, deterministic)
 *   - ollama: Local Ollama instance (real inference, no API key needed)
 *   - cloud:  OpenAI-compatible cloud API (real inference, costs money)
 *
 * Tier selection priority:
 *   1. LLM_TEST_TIER env var (explicit override)
 *   2. OPENAI_API_KEY set → cloud
 *   3. OLLAMA_API_URL set → ollama
 *   4. Default → mock
 *
 * Usage in tests:
 *   import { configureLlmForTier } from '../helpers/llm-tier';
 *   const tier = await configureLlmForTier(request, baseURL);
 *   // tier is 'mock' | 'ollama' | 'cloud'
 */
import { APIRequestContext } from '@playwright/test';

export type LlmTier = 'mock' | 'ollama' | 'cloud';

/**
 * Detect the LLM tier from environment variables.
 * Explicit LLM_TEST_TIER takes priority over auto-detection.
 */
export function getLlmTier(): LlmTier {
  const explicit = process.env.LLM_TEST_TIER;
  if (explicit === 'mock' || explicit === 'ollama' || explicit === 'cloud') {
    return explicit;
  }

  if (process.env.OPENAI_API_KEY) {
    return 'cloud';
  }

  if (process.env.OLLAMA_API_URL) {
    return 'ollama';
  }

  return 'mock';
}

/**
 * Get LLM connection config for a given tier.
 */
export function getLlmConfig(tier: LlmTier): {
  apiBaseUrl: string;
  model: string;
  apiKey: string;
} {
  switch (tier) {
    case 'mock':
      return {
        apiBaseUrl: 'http://mock-llm:8080',
        model: 'test-model',
        apiKey: 'sk-mock-test-key',
      };
    case 'ollama':
      return {
        apiBaseUrl: process.env.OLLAMA_API_URL || 'http://ollama:11434',
        model: process.env.OLLAMA_MODEL || 'llama3.2:1b',
        apiKey: 'ollama',
      };
    case 'cloud':
      return {
        apiBaseUrl: process.env.OPENAI_API_BASE || 'https://api.openai.com',
        model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
        apiKey: process.env.OPENAI_API_KEY || '',
      };
  }
}

/**
 * Configure the SemPKM backend's LLM settings for the detected tier.
 *
 * Sends three PUT requests to /browser/llm/config to set api_base_url,
 * default_model, and api_key. Returns the tier that was configured.
 *
 * @param request - Playwright APIRequestContext (authenticated)
 * @param baseURL - Base URL of the SemPKM instance (e.g. http://localhost:3901)
 * @param tier - Override tier selection (defaults to auto-detect via getLlmTier())
 */
export async function configureLlmForTier(
  request: APIRequestContext,
  baseURL: string,
  tier?: LlmTier,
): Promise<LlmTier> {
  const resolvedTier = tier ?? getLlmTier();
  const config = getLlmConfig(resolvedTier);

  const configUrl = `${baseURL}/browser/llm/config`;

  await request.put(configUrl, {
    data: { key: 'api_base_url', value: config.apiBaseUrl },
  });

  await request.put(configUrl, {
    data: { key: 'default_model', value: config.model },
  });

  await request.put(configUrl, {
    data: { key: 'api_key', value: config.apiKey },
  });

  return resolvedTier;
}
