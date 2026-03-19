---
estimated_steps: 8
estimated_files: 2
---

# T02: Write E2E Playwright tests for context overlay against Docker stack

**Slice:** S03 — Settings, E2E tests, and user guide
**Milestone:** M015

## Description

Write a Playwright E2E test file that proves the context overlay pipeline works end-to-end against the Docker test stack: create seed data with a matching URL, inject extension settings, trigger the context pipeline, verify sidebar results render, test the Open action, and test the Link-to-page action with SPARQL verification. Then update REQUIREMENTS.md to validate EXT-14 through EXT-19 based on test evidence.

Reuse the established patterns from `e2e/tests/25-extension/extension-capture.spec.ts`: same fixture import, same `setupAndCreateApiKey()` helper (copy it — self-contained test files per M014 precedent), same `injectExtensionSettings()` helper.

**Key constraints from KNOWLEDGE.md and research:**
- Badge text (`chrome.action.getBadgeText()`) is NOT accessible from Playwright — test sidebar results instead (same underlying data)
- `chrome.storage.sync` is unreliable in persistent context — use `injectExtensionSettings()` to write to `chrome.storage.local`
- Service worker debounce is 2000ms default — wait at least 3-5s after navigation before checking sidebar
- Persistent context navigating to `http://localhost:3901/browser/` can hang — use API-only verification (SPARQL) for SemPKM state assertions
- SHACL form required fields block native form validation — set `form.noValidate = true` if creating objects via popup (but this test creates via API)
- Open the sidebar HTML directly as a page (`chrome-extension://${extensionId}/sidebar/sidebar.html`) rather than trying the Side Panel API

**Skills:** Load `~/.gsd/agent/skills/test/SKILL.md` before executing this task.

## Steps

1. **Read the reference test file** — `e2e/tests/25-extension/extension-capture.spec.ts` to confirm helper patterns and imports.

2. **Read the sidebar JS** — `extension/sidebar/sidebar.js` to understand message types and DOM structure for assertions. Key details:
   - Sidebar sends `{type: 'getContextResults'}` to service worker on init
   - Service worker sends `{type: 'contextResultsUpdated', results, tabUrl}` messages
   - DOM panels: `#loading` (visible during fetch), `#error`, `#empty`, `#results`
   - Results render inside `#results` with `.result-group` sections containing `.result-item` elements
   - "Open" button has class `.action-open` (opens `chrome.tabs.create`)
   - "Link to this page" button has class `.action-link`

3. **Read the service worker** — `extension/background/service-worker.js` to understand message handler types:
   - `getContextResults` — returns cached results for active tab
   - `refreshContextResults` — forces re-query (bypasses cache)
   - `linkToPage` — creates schema:url edge

4. **Create `e2e/tests/25-extension/extension-context-overlay.spec.ts`** with:

   **Helpers** (copied from extension-capture.spec.ts for self-containment):
   - `repoRoot()` — git rev-parse --show-toplevel
   - `readSetupToken()` — reads from Docker container
   - `setupAndCreateApiKey()` — ensures setup + creates API key
   - `injectExtensionSettings()` — injects settings into chrome.storage.local

   **Additional helper:**
   - `injectContextSettings()` — extends injectExtensionSettings to also set `autoCheckContext: true`, `contextCheckDelay: 1000` (faster for tests), `contextTimeout: 10000`

   **Test suite** (`test.describe.serial('Context overlay flow')`):

   **beforeAll:** Call `setupAndCreateApiKey()` to get apiKey and ownerSessionCookie. Create a test Note with a known `schema:url` via POST /api/commands:
   ```
   POST /api/commands
   Authorization: Bearer <apiKey>
   {
     "type": "object.create",
     "params": {
       "type_iri": "<Note type IRI from basic-pkm>",
       "properties": {
         "dcterms:title": "Context Overlay Test Note",
         "schema:url": "http://example.com/test-context-page"
       }
     }
   }
   ```
   Store the created object IRI for later assertions.

   **Test 1: "settings round-trip for context overlay options"**
   - Open options page at `chrome-extension://${extensionId}/options/options.html`
   - Inject settings
   - Verify the three Context Overlay fields exist: `#auto-check-context`, `#context-check-delay`, `#context-timeout`
   - Change contextCheckDelay to 3000, save, reload, verify the value persisted

   **Test 2: "sidebar shows context results for matching URL"**
   - Inject extension settings (instanceUrl, apiKey, autoCheckContext:true, contextCheckDelay:1000)
   - Open sidebar page at `chrome-extension://${extensionId}/sidebar/sidebar.html`
   - The sidebar will try to get context results from the service worker. Since there's no active tab with matching URL, it may show empty. Instead, send a `refreshContextResults` message or use `chrome.runtime.sendMessage` to trigger a query with a known URL.
   - **Alternative approach (more reliable):** Rather than relying on the tab navigation pipeline, open a new tab navigating to a page, wait for debounce, then open the sidebar and verify. But since persistent context tab navigation can hang on certain pages, a better approach is:
     1. Open any simple page (e.g., `data:text/html,<h1>Test</h1>` or `chrome-extension://${extensionId}/options/options.html`)
     2. Navigate it to `http://example.com/test-context-page` (external URL — this won't hang since it's not the SemPKM workspace)
     3. Wait 3-5 seconds for service worker debounce + query
     4. Open sidebar page directly
     5. Sidebar calls `getContextResults` → service worker returns cached results
     6. Assert `#results` panel is visible, `.result-group` exists, result contains "Context Overlay Test Note"
   - **Fallback if tab navigation doesn't trigger service worker:** Open sidebar page, use `page.evaluate()` to send `chrome.runtime.sendMessage({type: 'refreshContextResults'})` directly, then wait for results to render.

   **Test 3: "Open action creates new tab pointing to SemPKM object"**
   - From the sidebar page with results rendered (continuation from test 2)
   - Click the first `.action-open` button
   - Verify a new page/tab was created in the context (check `context.pages()` length increased)
   - The new tab URL should contain the SemPKM instance URL and the object IRI

   **Test 4: "Link to this page creates schema:url edge"**
   - Open a new page, navigate to a test URL
   - Inject settings, wait for context query to complete
   - Open sidebar, wait for results
   - Click the first `.action-link` button
   - Wait for the success toast (`.toast` element with "Linked" text)
   - Verify via SPARQL query that a `schema:url` edge was created from the test Note to the current page URL

5. **Handle the Note type IRI** — The Note type IRI from basic-pkm needs to be discovered. Use `GET /api/types` with Bearer auth to find it, filtering for a type whose label contains "Note".

6. **Validate requirements** — After tests pass, update `.gsd/REQUIREMENTS.md`:
   - EXT-14 (badge): partially validated (badge set from same data as sidebar; sidebar results proven by test 2)
   - EXT-15 (sidebar): validated by test 2
   - EXT-16 (open action): validated by test 3
   - EXT-17 (link action): validated by test 4
   - EXT-18 (evidence capture): advanced but not validated (requires real content script text selection which is hard to automate; code review proves implementation)
   - EXT-19 (auto-context settings): validated by test 1 (settings round-trip)
   - EXT-20 (URL caching): partially validated (cache exercised implicitly by tests; 23 unit tests from S01 prove LRU logic)
   - EXT-21 (cross-browser): partially validated (Chromium E2E; Firefox manifest verified by node --check in S01)

7. **Run the tests** — `npx playwright test --project=extension extension-context-overlay` against running Docker test stack

8. **Fix any failures** — Debug and fix issues iteratively until all tests pass

## Must-Haves

- [ ] Test file at `e2e/tests/25-extension/extension-context-overlay.spec.ts`
- [ ] Test creates seed Note with schema:url via API
- [ ] Test verifies sidebar shows context results for matching URL
- [ ] Test verifies Open action creates new tab
- [ ] Test verifies Link action creates edge (SPARQL verification)
- [ ] Test verifies settings round-trip for context overlay options
- [ ] All tests pass against Docker test stack
- [ ] EXT-14 through EXT-21 updated in REQUIREMENTS.md with validation evidence

## Verification

- `npx playwright test --project=extension e2e/tests/25-extension/extension-context-overlay.spec.ts` passes
- Docker test stack must be running on port 3901 with basic-pkm model installed
- SPARQL query after link action returns the created edge

## Observability Impact

- Test console output shows step progression for debugging failures
- Service worker `[SemPKM]` console logs capture query pipeline state
- Sidebar DOM panels (#loading, #error, #empty, #results) provide visual state indication

## Inputs

- `e2e/fixtures/extension.ts` — persistent context fixture providing `context` and `extensionId`
- `e2e/tests/25-extension/extension-capture.spec.ts` — reference for helper patterns (setupAndCreateApiKey, injectExtensionSettings)
- `extension/sidebar/sidebar.js` — DOM structure and message types for assertions
- `extension/background/service-worker.js` — message handler types for service worker communication
- `extension/shared/storage.js` — settings keys and DEFAULTS
- S01 summary — context pipeline architecture (tab listener → debounce → query → rank → cache → badge)
- S02 summary — link action creates `schema:url` edge, evidence action creates Evidence object

## Expected Output

- `e2e/tests/25-extension/extension-context-overlay.spec.ts` — complete E2E test file with 4 serial tests
- `.gsd/REQUIREMENTS.md` — EXT-14 through EXT-21 updated with validation status and evidence
