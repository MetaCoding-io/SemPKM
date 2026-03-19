# S02: In-context actions — Link to page and Add Evidence

**Goal:** Wire the two stub sidebar action buttons into real API calls: "Link to this page" creates a `schema:url` edge, "Add Evidence" captures selected text and creates/links an Evidence object.
**Demo:** User opens sidebar via Alt+K, clicks "Link to this page" on a result → toast confirms, edge visible in SemPKM relations panel. User clicks "Add Evidence" on a Claim → selects text on the page → clicks Capture → toast confirms, Evidence object created and linked.

## Must-Haves

- "Link to this page" button sends `edge.create` command (source=object IRI, target=page URL, predicate=`schema:url`) via service worker relay, shows success/error toast
- "Add Evidence" button only appears on Claim-type results (`type_iri` contains `Evidence` parent type check — actually Claim: `urn:sempkm:model:research:Claim`)
- "Add Evidence" flow: sidebar shows capture prompt → user selects text on page → clicks Capture → `chrome.scripting.executeScript` extracts selection → service worker creates Evidence object + edge to Claim → toast confirms
- Both actions disable the button and show loading state during API call to prevent double-clicks
- Existing 23 unit tests still pass (no regressions)
- All modified files pass `node --check` syntax validation

## Proof Level

- This slice proves: integration (sidebar → service worker → API round-trip)
- Real runtime required: yes (sideload against Docker stack for full verification in S03)
- Human/UAT required: no (S03 covers E2E tests)

## Verification

- `node --check extension/sidebar/sidebar.js` — syntax valid
- `node --check extension/background/service-worker.js` — syntax valid
- `node --test extension/tests/test-context-utils.js` — 23/23 tests pass (no regressions)
- Manual inspection: "Link to this page" button has `.action-link` class (not `.action-stub`)
- Manual inspection: "Add Evidence" button has `.action-evidence` class (not `.action-stub`), only rendered when `item.type_iri` contains `Claim`
- Evidence capture prompt panel exists in sidebar with Capture/Cancel buttons
- Service worker handles `linkToPage` and `addEvidence` message types

## Observability / Diagnostics

- Runtime signals: `[SemPKM]` prefixed console logs in service worker for linkToPage success/error, addEvidence step 1 (object.create) and step 2 (edge.create) success/error
- Inspection surfaces: sidebar toast messages ("✓ Linked to this page", "✓ Evidence captured and linked", error messages); service worker console in chrome://extensions
- Failure visibility: API errors surfaced in toast with detail message; orphaned Evidence IRI logged in error toast if edge.create fails after object.create succeeds
- Redaction constraints: none (no secrets in toast or console)

## Integration Closure

- Upstream surfaces consumed: `extension/sidebar/sidebar.js` (stub handlers from S01), `extension/background/service-worker.js` (message handler pattern, `_getApiConfig()` from S01), `extension/sidebar/sidebar.css` (`.action-stub` styles from S01)
- New wiring introduced: `linkToPage` and `addEvidence` message types in service worker; `chrome.scripting.executeScript` call from sidebar for text selection capture
- What remains before milestone is truly usable end-to-end: S03 (settings UI, E2E tests, user guide)

## Tasks

- [x] **T01: Wire "Link to this page" action through service worker** `est:45m`
  - Why: Replaces the stub "Link to this page" button with a real `edge.create` API call relayed through the service worker, covering EXT-17
  - Files: `extension/background/service-worker.js`, `extension/sidebar/sidebar.js`, `extension/sidebar/sidebar.css`
  - Do: Add `linkToPage` message handler to service worker (reads `_getApiConfig()`, POSTs `edge.create` with source=objectIri, target=pageUrl, predicate=`schema:url`). In sidebar.js, replace stub click handler with `_linkToPage(objectIri)` that gets page URL via `chrome.tabs.query`, sends message, shows loading state, shows success/error toast. Track `_currentTabUrl` by querying active tab on init and on `contextResultsUpdated`. Update CSS: replace `.action-stub` for link button with `.action-link` solid style.
  - Verify: `node --check extension/background/service-worker.js && node --check extension/sidebar/sidebar.js && node --test extension/tests/test-context-utils.js`
  - Done when: Link button has `.action-link` class, service worker handles `linkToPage` message, button disables during call and re-enables on response, toast shows result

- [ ] **T02: Wire "Add Evidence" action with text selection capture** `est:1h`
  - Why: Replaces the stub "Add Evidence" button with the full capture flow: prompt → text selection → create Evidence + link to Claim, covering EXT-18
  - Files: `extension/background/service-worker.js`, `extension/sidebar/sidebar.js`, `extension/sidebar/sidebar.css`, `extension/sidebar/sidebar.html`
  - Do: Add `addEvidence` message handler to service worker (two sequential API calls: `object.create` Evidence then `edge.create` linking Evidence→Claim via `res:supports`). In sidebar.js, replace stub click handler with `_addEvidence(claimIri, claimLabel)` that shows evidence capture prompt panel, waits for Capture click, executes `chrome.scripting.executeScript` to get `window.getSelection().toString().trim()`, validates non-empty, sends message to service worker, shows success/error toast. Only render "Add Evidence" button when `item.type_iri` matches Claim type. Add evidence prompt panel to sidebar.html (instruction text, selected-text preview area, Capture/Cancel buttons). Style `.evidence-prompt`, `.action-evidence` in CSS.
  - Verify: `node --check extension/background/service-worker.js && node --check extension/sidebar/sidebar.js && node --test extension/tests/test-context-utils.js`
  - Done when: Evidence button only appears on Claim-type results, capture prompt shows/hides correctly, service worker makes both API calls sequentially, orphaned Evidence IRI logged on partial failure, button disables during call

## Files Likely Touched

- `extension/background/service-worker.js`
- `extension/sidebar/sidebar.js`
- `extension/sidebar/sidebar.css`
- `extension/sidebar/sidebar.html`
