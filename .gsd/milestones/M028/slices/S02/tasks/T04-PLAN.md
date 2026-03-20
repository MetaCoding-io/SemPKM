---
estimated_steps: 5
estimated_files: 2
---

# T04: Add SemPKMClient AI methods and Node.js unit tests

**Slice:** S02 — Extension sidebar AI Insights UI
**Milestone:** M028

## Description

Add 5 new methods to the `SemPKMClient` class in `extension/shared/api-client.js` for the AI endpoints, then write Node.js unit tests verifying each method constructs the correct HTTP request and handles errors properly.

The service worker can't use these methods (ES module limitation — it uses classic `importScripts()`), but they're the public API surface for the extension and enable proper unit testing. The existing `test-context-utils.js` demonstrates the Node.js test pattern using `node:test` and `node:assert`.

## Steps

1. **Add `getLLMStatus()` method to SemPKMClient.** Simple GET request:
   ```javascript
   async getLLMStatus() {
     return this._request('/api/llm/status');
   }
   ```
   Returns the parsed JSON `{available: bool, provider: string|null}` directly.

2. **Add 4 POST methods to SemPKMClient:**
   ```javascript
   async detectClaims({ content, url = '', title = '' }) {
     return this._request('/api/ai/detect-claims', {
       method: 'POST',
       body: JSON.stringify({ content, url, title }),
     });
   }

   async matchClaims({ claims }) {
     return this._request('/api/ai/match-claims', {
       method: 'POST',
       body: JSON.stringify({ claims }),
     });
   }

   async suggestRelationships({ url = '', title = '', claims = [] }) {
     return this._request('/api/ai/suggest-relationships', {
       method: 'POST',
       body: JSON.stringify({ url, title, claims }),
     });
   }

   async summarizePage({ content, graph_context = [] }) {
     return this._request('/api/ai/summarize', {
       method: 'POST',
       body: JSON.stringify({ content, graph_context }),
     });
   }
   ```
   All follow the existing `_request()` pattern which handles headers and error throwing.

3. **Create `extension/tests/test-ai-client.js`.** Use `node:test` and `node:assert` (same pattern as `test-context-utils.js`). Mock global `fetch` before each test. Structure:

   ```javascript
   import { describe, it, beforeEach, afterEach } from 'node:test';
   import assert from 'node:assert/strict';
   import { SemPKMClient, SemPKMError } from '../shared/api-client.js';
   ```

   Create a `mockFetch` helper that captures calls and returns configured responses:
   ```javascript
   let fetchCalls = [];
   function mockFetch(status, body) {
     global.fetch = async (url, opts) => {
       fetchCalls.push({ url, ...opts });
       return {
         ok: status >= 200 && status < 300,
         status,
         statusText: status === 200 ? 'OK' : 'Error',
         json: async () => body,
       };
     };
   }
   ```

   Test groups:
   - **getLLMStatus**: verify GET to `/api/llm/status`, correct Authorization header, returns parsed JSON
   - **detectClaims**: verify POST to `/api/ai/detect-claims`, body has content/url/title, returns parsed response
   - **matchClaims**: verify POST to `/api/ai/match-claims`, body has claims array, returns parsed response
   - **suggestRelationships**: verify POST to `/api/ai/suggest-relationships`, body has url/title/claims
   - **summarizePage**: verify POST to `/api/ai/summarize`, body has content and graph_context
   - **Error handling**: verify non-200 status throws `SemPKMError` with correct status and detail. Test with 401 (auth failure), 503 (LLM unavailable), 400 (bad request).
   - **Request headers**: verify all requests include `Authorization: Bearer <key>`, `Content-Type: application/json`, `Accept: application/json`

4. **Run `node --check` on both files.** Verify syntax.

5. **Run the test suite.** `node --experimental-vm-modules extension/tests/test-ai-client.js` (or just `node extension/tests/test-ai-client.js` if ES module support is configured). All tests must pass.

## Must-Haves

- [ ] `getLLMStatus()` calls GET /api/llm/status
- [ ] `detectClaims({content, url, title})` calls POST /api/ai/detect-claims with correct body
- [ ] `matchClaims({claims})` calls POST /api/ai/match-claims with claims array
- [ ] `suggestRelationships({url, title, claims})` calls POST /api/ai/suggest-relationships
- [ ] `summarizePage({content, graph_context})` calls POST /api/ai/summarize
- [ ] All methods use Bearer auth header via existing `_request()` pattern
- [ ] Non-200 responses throw `SemPKMError` with status and detail
- [ ] Node.js tests verify URL paths, HTTP methods, request bodies, headers, and error handling
- [ ] `node --check extension/shared/api-client.js` passes
- [ ] `node extension/tests/test-ai-client.js` — all tests pass

## Verification

- `node --check extension/shared/api-client.js` — zero errors
- `node --test extension/tests/test-ai-client.js` — all tests pass (expect ~15-20 test cases)
- `grep -c 'getLLMStatus\|detectClaims\|matchClaims\|suggestRelationships\|summarizePage' extension/shared/api-client.js` — returns 5 or more (method definitions)

## Inputs

- `extension/shared/api-client.js` (209 lines) — existing `SemPKMClient` with `_request()`, `_headers()`, `connect()`, `getTypes()`, `getShape()`, `createObject()`, `createEdge()`, `searchObjects()`, `contextQuery()`. Uses ES module exports (`export class`).
- `extension/tests/test-context-utils.js` (9476 lines) — reference test pattern using `node:test` and `node:assert`
- S01 API contract: same as T01 inputs — endpoint paths and request/response schemas

## Observability Impact

- **Test suite signal:** `node --test extension/tests/test-ai-client.js` — 22 tests across 7 suites verify all AI method contracts. A failure pinpoints exactly which method, body field, header, or error-handling path regressed.
- **Method grep count:** `grep -c 'getLLMStatus\|detectClaims\|matchClaims\|suggestRelationships\|summarizePage' extension/shared/api-client.js` should return ≥6 (method defs + JSDoc). A count drop means a method was removed or renamed.
- **Runtime inspection:** All 5 methods delegate to `_request()`, which throws `SemPKMError` with HTTP status and backend detail. Any caller can catch and inspect `.status` and `.detail` properties for diagnostics.
- **No new runtime logs:** These are library methods, not entry points — they don't add console logging. Test failures are the primary diagnostic signal.

## Expected Output

- `extension/shared/api-client.js` — expanded with 5 new methods (~40 lines added): `getLLMStatus()`, `detectClaims()`, `matchClaims()`, `suggestRelationships()`, `summarizePage()`
- `extension/tests/test-ai-client.js` — new test file (~200-250 lines): 15-20 test cases covering all methods, request construction, headers, and error handling
