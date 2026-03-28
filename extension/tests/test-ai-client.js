/**
 * Unit tests for SemPKMClient AI / LLM methods.
 *
 * Run: node --test extension/tests/test-ai-client.js
 *
 * Uses only Node.js built-in test runner and assert — no external dependencies.
 * Global fetch is mocked before each test to capture request details.
 */

import { describe, it, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { SemPKMClient, SemPKMError } from '../shared/api-client.js';

// ---------------------------------------------------------------------------
// Helpers — mock fetch infrastructure
// ---------------------------------------------------------------------------

const BASE_URL = 'http://localhost:4000';
const API_KEY = 'test-api-key-12345';

/** Captured fetch calls — reset before every test. */
let fetchCalls = [];

/** Original global fetch ref — restored after each test. */
let _originalFetch;

/**
 * Install a mock fetch that records calls and returns a canned response.
 * @param {number} status - HTTP status code
 * @param {any} body - JSON-serialisable response body
 */
function mockFetch(status, body) {
  global.fetch = async (url, opts) => {
    fetchCalls.push({ url, ...(opts || {}) });
    return {
      ok: status >= 200 && status < 300,
      status,
      statusText: status >= 200 && status < 300 ? 'OK' : 'Error',
      json: async () => body,
    };
  };
}

/** Create a fresh SemPKMClient for tests. */
function makeClient() {
  return new SemPKMClient(BASE_URL, API_KEY);
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  _originalFetch = global.fetch;
  fetchCalls = [];
});

afterEach(() => {
  global.fetch = _originalFetch;
});

// ---------------------------------------------------------------------------
// getLLMStatus
// ---------------------------------------------------------------------------

describe('getLLMStatus', () => {
  it('sends GET to /api/llm/status', async () => {
    mockFetch(200, { available: true, provider: 'openai' });
    const client = makeClient();
    await client.getLLMStatus();
    assert.strictEqual(fetchCalls.length, 1);
    assert.strictEqual(fetchCalls[0].url, `${BASE_URL}/api/llm/status`);
    assert.strictEqual(fetchCalls[0].method, undefined); // GET has no method key
  });

  it('returns parsed JSON with available and provider', async () => {
    mockFetch(200, { available: true, provider: 'openai' });
    const result = await makeClient().getLLMStatus();
    assert.deepStrictEqual(result, { available: true, provider: 'openai' });
  });

  it('returns unavailable status correctly', async () => {
    mockFetch(200, { available: false, provider: null });
    const result = await makeClient().getLLMStatus();
    assert.strictEqual(result.available, false);
    assert.strictEqual(result.provider, null);
  });
});

// ---------------------------------------------------------------------------
// detectClaims
// ---------------------------------------------------------------------------

describe('detectClaims', () => {
  it('sends POST to /api/ai/detect-claims with correct body', async () => {
    mockFetch(200, { claims: [] });
    const client = makeClient();
    await client.detectClaims({ content: 'The sky is blue.', url: 'https://example.com', title: 'Sky' });
    assert.strictEqual(fetchCalls.length, 1);
    assert.strictEqual(fetchCalls[0].url, `${BASE_URL}/api/ai/detect-claims`);
    assert.strictEqual(fetchCalls[0].method, 'POST');
    const body = JSON.parse(fetchCalls[0].body);
    assert.strictEqual(body.content, 'The sky is blue.');
    assert.strictEqual(body.url, 'https://example.com');
    assert.strictEqual(body.title, 'Sky');
  });

  it('defaults url and title to empty strings', async () => {
    mockFetch(200, { claims: [] });
    await makeClient().detectClaims({ content: 'test' });
    const body = JSON.parse(fetchCalls[0].body);
    assert.strictEqual(body.url, '');
    assert.strictEqual(body.title, '');
  });

  it('returns parsed claims array', async () => {
    const mockClaims = [
      { text: 'Claim 1', confidence: 'established', type: 'factual' },
      { text: 'Claim 2', confidence: 'likely', type: 'causal' },
    ];
    mockFetch(200, { claims: mockClaims });
    const result = await makeClient().detectClaims({ content: 'text' });
    assert.deepStrictEqual(result.claims, mockClaims);
  });
});

// ---------------------------------------------------------------------------
// matchClaims
// ---------------------------------------------------------------------------

describe('matchClaims', () => {
  it('sends POST to /api/ai/match-claims with claims array', async () => {
    const claims = [{ text: 'Claim A', confidence: 'established', type: 'factual' }];
    mockFetch(200, { matches: [], gaps: [] });
    await makeClient().matchClaims({ claims });
    assert.strictEqual(fetchCalls[0].url, `${BASE_URL}/api/ai/match-claims`);
    assert.strictEqual(fetchCalls[0].method, 'POST');
    const body = JSON.parse(fetchCalls[0].body);
    assert.deepStrictEqual(body.claims, claims);
  });

  it('returns matches and gaps', async () => {
    const mockResponse = {
      matches: [{ claim_text: 'X', objects: [] }],
      gaps: [{ question: 'Why?' }],
    };
    mockFetch(200, mockResponse);
    const result = await makeClient().matchClaims({ claims: [] });
    assert.deepStrictEqual(result, mockResponse);
  });
});

// ---------------------------------------------------------------------------
// suggestRelationships
// ---------------------------------------------------------------------------

describe('suggestRelationships', () => {
  it('sends POST to /api/ai/suggest-relationships with url, title, claims', async () => {
    mockFetch(200, { suggestions: [] });
    await makeClient().suggestRelationships({
      url: 'https://page.com',
      title: 'Page',
      claims: [{ text: 'C1' }],
    });
    assert.strictEqual(fetchCalls[0].url, `${BASE_URL}/api/ai/suggest-relationships`);
    assert.strictEqual(fetchCalls[0].method, 'POST');
    const body = JSON.parse(fetchCalls[0].body);
    assert.strictEqual(body.url, 'https://page.com');
    assert.strictEqual(body.title, 'Page');
    assert.deepStrictEqual(body.claims, [{ text: 'C1' }]);
  });

  it('defaults url, title, and claims', async () => {
    mockFetch(200, { suggestions: [] });
    await makeClient().suggestRelationships({});
    const body = JSON.parse(fetchCalls[0].body);
    assert.strictEqual(body.url, '');
    assert.strictEqual(body.title, '');
    assert.deepStrictEqual(body.claims, []);
  });

  it('returns suggestions array', async () => {
    const suggestions = [
      { type: 'link', label: 'Link', target_iri: 'urn:x:1', target_label: 'X', reason: 'relevant' },
    ];
    mockFetch(200, { suggestions });
    const result = await makeClient().suggestRelationships({});
    assert.deepStrictEqual(result.suggestions, suggestions);
  });
});

// ---------------------------------------------------------------------------
// summarizePage
// ---------------------------------------------------------------------------

describe('summarizePage', () => {
  it('sends POST to /api/ai/summarize with content and graph_context', async () => {
    mockFetch(200, { summary: 'A summary.' });
    await makeClient().summarizePage({
      content: 'Full page text...',
      graph_context: [{ iri: 'urn:x:1', label: 'Note' }],
    });
    assert.strictEqual(fetchCalls[0].url, `${BASE_URL}/api/ai/summarize`);
    assert.strictEqual(fetchCalls[0].method, 'POST');
    const body = JSON.parse(fetchCalls[0].body);
    assert.strictEqual(body.content, 'Full page text...');
    assert.deepStrictEqual(body.graph_context, [{ iri: 'urn:x:1', label: 'Note' }]);
  });

  it('defaults graph_context to empty array', async () => {
    mockFetch(200, { summary: 'Short.' });
    await makeClient().summarizePage({ content: 'text' });
    const body = JSON.parse(fetchCalls[0].body);
    assert.deepStrictEqual(body.graph_context, []);
  });

  it('returns summary string', async () => {
    mockFetch(200, { summary: 'This page discusses X.' });
    const result = await makeClient().summarizePage({ content: 'X content' });
    assert.strictEqual(result.summary, 'This page discusses X.');
  });
});

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe('error handling', () => {
  it('throws SemPKMError on 401 unauthorized', async () => {
    mockFetch(401, { detail: 'Invalid API key' });
    await assert.rejects(
      () => makeClient().getLLMStatus(),
      (err) => {
        assert.ok(err instanceof SemPKMError);
        assert.strictEqual(err.status, 401);
        assert.strictEqual(err.detail, 'Invalid API key');
        return true;
      },
    );
  });

  it('throws SemPKMError on 503 LLM unavailable', async () => {
    mockFetch(503, { detail: 'LLM provider not configured' });
    await assert.rejects(
      () => makeClient().detectClaims({ content: 'test' }),
      (err) => {
        assert.ok(err instanceof SemPKMError);
        assert.strictEqual(err.status, 503);
        assert.strictEqual(err.detail, 'LLM provider not configured');
        return true;
      },
    );
  });

  it('throws SemPKMError on 400 bad request', async () => {
    mockFetch(400, { detail: 'content field required' });
    await assert.rejects(
      () => makeClient().summarizePage({ content: '' }),
      (err) => {
        assert.ok(err instanceof SemPKMError);
        assert.strictEqual(err.status, 400);
        assert.strictEqual(err.detail, 'content field required');
        return true;
      },
    );
  });

  it('throws SemPKMError on 500 internal server error', async () => {
    mockFetch(500, { error: 'Internal failure' });
    await assert.rejects(
      () => makeClient().matchClaims({ claims: [] }),
      (err) => {
        assert.ok(err instanceof SemPKMError);
        assert.strictEqual(err.status, 500);
        assert.strictEqual(err.detail, 'Internal failure');
        return true;
      },
    );
  });
});

// ---------------------------------------------------------------------------
// Request headers
// ---------------------------------------------------------------------------

describe('request headers', () => {
  it('includes Authorization Bearer header on GET', async () => {
    mockFetch(200, { available: true, provider: null });
    await makeClient().getLLMStatus();
    const headers = fetchCalls[0].headers;
    assert.strictEqual(headers['Authorization'], `Bearer ${API_KEY}`);
  });

  it('includes Authorization Bearer header on POST', async () => {
    mockFetch(200, { claims: [] });
    await makeClient().detectClaims({ content: 'x' });
    const headers = fetchCalls[0].headers;
    assert.strictEqual(headers['Authorization'], `Bearer ${API_KEY}`);
  });

  it('includes Content-Type application/json', async () => {
    mockFetch(200, { suggestions: [] });
    await makeClient().suggestRelationships({});
    const headers = fetchCalls[0].headers;
    assert.strictEqual(headers['Content-Type'], 'application/json');
  });

  it('includes Accept application/json', async () => {
    mockFetch(200, { summary: 'ok' });
    await makeClient().summarizePage({ content: 'x' });
    const headers = fetchCalls[0].headers;
    assert.strictEqual(headers['Accept'], 'application/json');
  });
});
