---
estimated_steps: 8
estimated_files: 1
---

# T02: Create Playwright E2E test for AI Insights flow

**Slice:** S03 — E2E tests and user guide
**Milestone:** M028

## Description

Create a Playwright E2E test that exercises the full AI Insights sidebar flow against the Docker test stack with the mock LLM server from T01. The test proves the end-to-end pipeline: extension sidebar opens → AI insights triggered → claims from mock LLM render → graph matches display → accept suggestion creates edge → SPARQL verifies edge.

This test follows the established pattern from `extension-context-overlay.spec.ts`: persistent context fixture, `setupAndCreateApiKey()` for auth, `injectExtensionSettings()` for storage injection, `chrome.runtime.sendMessage` for sidebar interactions, and SPARQL API for verification.

**Critical constraint:** The `api_base_url` configured via the Settings API must be `http://mock-llm:8080` (the Docker-internal hostname), NOT `http://localhost:PORT`. The Python backend inside the Docker container makes the actual LLM call, so it needs the Docker network hostname.

**Relevant skills:** Load the `test` skill for Playwright test patterns.

## Steps

1. **Create `e2e/tests/25-extension/extension-ai-insights.spec.ts`** with these imports:
   ```typescript
   import { test, expect } from '../../fixtures/extension';
   import { execSync } from 'child_process';
   import { request, type Page } from '@playwright/test';
   ```

2. **Copy helper functions** from `extension-context-overlay.spec.ts` into the new file:
   - `repoRoot()` — resolves git repo root
   - `readSetupToken()` — reads setup token from Docker API container
   - `setupAndCreateApiKey()` — sets up auth, creates API key, returns `{apiKey, ownerSessionCookie}`
   - `injectExtensionSettings()` — injects settings into `chrome.storage.local`
   
   These helpers are NOT shared as imports — they're file-local in the reference test. Copy them as-is.

3. **Add an `async function configureLLM()` helper** that makes three PUT requests to configure the mock LLM:
   ```typescript
   async function configureLLM(ownerSessionCookie: string) {
     const ctx = await request.newContext({
       baseURL: BASE_URL,
       extraHTTPHeaders: {
         Cookie: `sempkm_session=${ownerSessionCookie}`,
       },
     });
     // Three calls per the Settings API contract (one field per call)
     for (const [field, value] of [
       ['api_base_url', 'http://mock-llm:8080'],
       ['api_key', 'test-key'],
       ['default_model', 'test-model'],
     ]) {
       const resp = await ctx.put(`${BASE_URL}/browser/settings/llm/config`, {
         data: { field, value },
       });
       if (resp.status() !== 200) {
         throw new Error(`LLM config ${field} failed: ${resp.status()}`);
       }
     }
     await ctx.dispose();
   }
   ```
   **Important:** The URL path is `/browser/settings/llm/config` (the browser settings router), NOT `/api/settings/...`. Uses `require_role("owner")` so the owner session cookie is required.

4. **Write test 1: "graceful degradation — AI unavailable when LLM not configured"**:
   - Before configuring LLM (or skip LLM config entirely for this test)
   - Set up auth + API key via `setupAndCreateApiKey()`
   - Open sidebar page: `context.newPage()` → `goto(chrome-extension://${extensionId}/sidebar/sidebar.html)`
   - Inject extension settings via `injectExtensionSettings()` (instanceUrl + apiKey)
   - Trigger AI insights: `page.evaluate(() => chrome.runtime.sendMessage({type: 'getAIInsights'}))`
   - Wait for `#ai-unavailable:not([hidden])` to appear (timeout 10s)
   - Assert `#ai-unavailable` text contains "LLM configuration" or "AI features require"
   - Close sidebar page
   
   **Note:** This test MUST run before `configureLLM()` is called. If the Docker stack is fresh, LLM config won't exist, so `/api/llm/status` returns `{available: false}`.

5. **Write test 2: "AI claims render from mock LLM after configuration"**:
   - Call `configureLLM(ownerSessionCookie)` to point backend at mock LLM
   - Create a seed Note with a known `schema:url` via `POST /api/commands` with Bearer auth:
     ```typescript
     const createResp = await authCtx.post(`${BASE_URL}/api/commands`, {
       data: {
         command: 'object.create',
         params: {
           type: 'urn:sempkm:model:basic-pkm:Note',
           properties: {
             'dcterms:title': 'AI Insights Test Note',
             'schema:url': SEED_PAGE_URL,
           },
         },
       },
     });
     ```
   - Open sidebar, inject settings
   - Trigger AI insights pipeline and wait for claims to render
   - The sidebar needs to know about the active tab URL. Since we can't navigate to a real page in persistent context (it may hang — see KNOWLEDGE.md), use `chrome.runtime.sendMessage` with an explicit content/URL parameter, OR trigger via the sidebar's own init logic by navigating a tab to a `data:` URL first, then sending the message.
   - **Approach:** Open the sidebar page, then use `page.evaluate()` to directly call the AI pipeline by sending `{type: 'getAIInsights'}` to the service worker. The service worker extracts content from the active tab via `chrome.scripting.executeScript`. For the test, the active tab might be the sidebar itself — so alternatively, inject the AI results directly by calling the API and rendering:
     ```typescript
     // Call detect-claims API directly from the sidebar page
     const resp = await page.evaluate(async (params) => {
       const r = await fetch(`${params.instanceUrl}/api/ai/detect-claims`, {
         method: 'POST',
         headers: {
           'Authorization': `Bearer ${params.apiKey}`,
           'Content-Type': 'application/json',
         },
         body: JSON.stringify({
           content: 'Climate change is accelerating global ice loss. Arctic sea ice extent reached a record low in 2023.',
           url: params.seedUrl,
           title: 'Test Article',
         }),
       });
       return { status: r.status, body: await r.json() };
     }, { instanceUrl: BASE_URL, apiKey, seedUrl: SEED_PAGE_URL });
     ```
   - Verify the API returned 200 with claims array
   - To verify sidebar rendering, trigger the full pipeline via service worker message. The service worker's `getAIInsights` handler extracts page content from the active tab. In the persistent context, open a real page first (e.g., navigate to `${BASE_URL}/browser/` which is the SemPKM workspace — this won't hang like external URLs). Then open the sidebar and trigger. Or: construct the progress messages manually and send them to the sidebar.
   - **Simplest reliable approach:** Verify the API works (detect-claims returns claims) and verify the sidebar DOM structure exists. Then trigger `aiInsightsProgress` messages directly to the sidebar page to simulate the pipeline and verify rendering:
     ```typescript
     await sidebarPage.evaluate((claimsData) => {
       // Simulate the service worker sending a progress message
       const event = new MessageEvent('message', {
         data: {
           type: 'aiInsightsProgress',
           section: 'claims',
           generationId: 1,
           claims: claimsData,
         },
       });
       // The sidebar listens on chrome.runtime.onMessage — but we can
       // call the render function directly if it's exposed, or dispatch
       // a custom event. Check if _renderClaimsSection is accessible.
     }, claims);
     ```
   - **Even simpler:** Just verify: (a) the API endpoint returns valid claims, and (b) the `#ai-claims` container exists in the sidebar DOM. The unit tests in S01+S02 already prove the rendering logic works. The E2E test's value is proving the backend pipeline works with the mock LLM.

6. **Write test 3: "accept suggestion creates edge verified by SPARQL"**:
   - This is the highest-value test — proves the full create-edge-via-accept path
   - Create a seed Note via API (if not already created in test 2, use a `beforeAll`)
   - Call suggest-relationships API directly with Bearer auth:
     ```typescript
     const suggestResp = await authCtx.post(`${BASE_URL}/api/ai/suggest-relationships`, {
       data: {
         url: SEED_PAGE_URL,
         title: 'AI Insights Test Article',
         claims: [{ text: 'test claim', confidence: 'likely', type: 'factual' }],
       },
     });
     ```
   - If suggestions are returned, use the first suggestion to test the accept flow
   - If no suggestions (URL/keyword don't match), create the edge manually via the same accept pattern the sidebar uses: `POST /api/commands` with `{command: 'edge.create', params: {source: seedNoteIri, target: someIri, predicate: 'schema:url', label: 'Test link'}}`
   - **Better approach:** Directly test the accept flow by sending `acceptSuggestion` message to the service worker from the sidebar page:
     ```typescript
     await sidebarPage.evaluate(async (params) => {
       const response = await new Promise((resolve) => {
         chrome.runtime.sendMessage({
           type: 'acceptSuggestion',
           suggestion: {
             type: 'link',
             target_iri: params.seedNoteIri,
             label: 'AI Test Link',
           },
           pageUrl: params.pageUrl,
           pageTitle: 'Test Article',
         }, resolve);
       });
       if (!response || !response.success) {
         throw new Error('Accept suggestion failed: ' + JSON.stringify(response));
       }
     }, { seedNoteIri, pageUrl: SEED_PAGE_URL });
     ```
   - Verify edge via SPARQL (same pattern as `extension-context-overlay.spec.ts` test 4):
     ```typescript
     const sparqlQuery = `
       PREFIX sempkm: <urn:sempkm:>
       PREFIX schema: <https://schema.org/>
       SELECT ?edge WHERE {
         ?edge a sempkm:Edge ;
               sempkm:source <${seedNoteIri}> ;
               sempkm:predicate schema:url .
       } LIMIT 5
     `;
     ```
   - Assert bindings.length > 0

7. **Structure the tests as `test.describe.serial()`** with shared state:
   - `let apiKey, ownerSessionCookie, seedNoteIri` in describe scope
   - `test.beforeAll()` calls `setupAndCreateApiKey()`
   - Tests run in order: test 1 (no LLM config) → test 2 (configure LLM + verify API) → test 3 (accept + SPARQL)

8. **Verify file syntax**: `node -e "const ts = require('typescript'); const result = ts.transpileModule(require('fs').readFileSync('e2e/tests/25-extension/extension-ai-insights.spec.ts', 'utf8'), {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ESNext}}); console.log('OK');"` or simpler: just verify the file structure matches the reference test's patterns.

## Must-Haves

- [ ] Test file imports from `../../fixtures/extension` (persistent context fixture)
- [ ] `setupAndCreateApiKey()` helper creates auth + API key
- [ ] `injectExtensionSettings()` helper injects chrome.storage.local settings
- [ ] `configureLLM()` helper calls PUT `/browser/settings/llm/config` three times
- [ ] Test 1 verifies `#ai-unavailable` shows when LLM not configured
- [ ] Test 2 verifies detect-claims API returns valid claim JSON from mock LLM
- [ ] Test 3 verifies accept creates edge and SPARQL confirms it
- [ ] All tests use `test.describe.serial()` for ordered execution

## Verification

- File exists at `e2e/tests/25-extension/extension-ai-insights.spec.ts`
- File has ≥3 `test(` calls inside a `test.describe.serial` block
- File imports from `../../fixtures/extension`
- `grep "mock-llm:8080" e2e/tests/25-extension/extension-ai-insights.spec.ts` — finds the Docker-internal hostname
- `grep "configureLLM\|llm/config" e2e/tests/25-extension/extension-ai-insights.spec.ts` — finds LLM configuration
- `grep "ai-unavailable" e2e/tests/25-extension/extension-ai-insights.spec.ts` — finds graceful degradation test
- `grep "SPARQL\|sparql\|sempkm:Edge" e2e/tests/25-extension/extension-ai-insights.spec.ts` — finds edge verification

## Inputs

- `e2e/fixtures/extension.ts` — persistent context fixture providing `context` and `extensionId`
- `e2e/tests/25-extension/extension-context-overlay.spec.ts` — reference for `setupAndCreateApiKey()`, `injectExtensionSettings()`, SPARQL edge verification pattern
- `e2e/mock-llm-api/server.py` (from T01) — mock LLM server returning canned claim JSON
- `extension/sidebar/sidebar.html` — DOM structure: `#ai-insights`, `#ai-unavailable`, `#ai-claims`, `#ai-matches`, `#ai-suggestions`, `#ai-summary`
- `extension/background/service-worker.js` — message types: `getAIInsights`, `acceptSuggestion`, `dismissSuggestion`, `aiInsightsProgress`
- S01 Summary — All 6 AI endpoints use `get_current_user_or_api` for dual-auth (Bearer + cookie)
- S01 Summary — `PUT /browser/settings/llm/config` requires `require_role("owner")` (owner session cookie needed, NOT Bearer token)
- S02 Summary — Accept maps 4 suggestion types: `link` → `edge.create` with `schema:url`, `evidence` → `object.create` + `edge.create`, `supports` → `edge.create` with `res:supports`, `contradicts` → `edge.create` with `res:refutes`
- KNOWLEDGE.md — "Playwright extension tests: persistent context hangs navigating non-extension pages" — avoid navigating to `http://localhost:3901/browser/` from persistent context, use API-only verification
- KNOWLEDGE.md — "chrome.storage.sync unreliable in persistent context" — use `injectExtensionSettings()` to write to chrome.storage.local

## Observability Impact

**New signals:**
- E2E test console output logs each phase: `[AI Insights E2E] Seed note created: <iri>`, `[AI Insights E2E] Claims returned: <count>`, `[AI Insights E2E] Edge verified: <iri>`
- Playwright trace files written to `e2e/test-results/` on failure — includes screenshots, network logs, and DOM snapshots
- `test.describe.serial()` ordering ensures graceful-degradation test runs before LLM configuration, making failure order diagnostic

**How to inspect:**
- `npx playwright test extension-ai-insights --reporter=list` — runs with verbose per-test output
- On failure: check `e2e/test-results/` for trace zip, open with `npx playwright show-trace`
- `grep "ai-unavailable\|SPARQL\|configureLLM" e2e/tests/25-extension/extension-ai-insights.spec.ts` — confirms test covers all three phases

**Failure visibility:**
- Test 1 failure = LLM status endpoint returns `available: true` when it shouldn't (config leaked from prior run)
- Test 2 failure = mock-llm server not reachable at `http://mock-llm:8080` from Docker backend (network/service issue)
- Test 3 failure = edge.create command failed or SPARQL query returned no bindings (command API or triplestore issue)

## Expected Output

- `e2e/tests/25-extension/extension-ai-insights.spec.ts` — new file (~300-450 lines): Playwright E2E test with 3+ serial tests covering graceful degradation, claims from mock LLM, and accept-suggestion edge creation verified by SPARQL
