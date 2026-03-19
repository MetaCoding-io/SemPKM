# S02 — Research: In-context actions — Link to page and Add Evidence

**Date:** 2026-03-18

## Summary

S02 wires the two stub action buttons in the sidebar ("Link to this page" and "Add Evidence") into real API calls. Both actions follow the same messaging pattern established in S01: sidebar sends action request → service worker executes API call → service worker responds with success/error → sidebar shows toast.

"Link to this page" is simple — one `edge.create` call: source = object IRI, target = page URL (a valid IRI), predicate = `schema:url`. The `edge.create` handler wraps the target in `URIRef()`, and HTTP URLs are valid URIs, so this works without minting a separate web-page object.

"Add Evidence" is the complex action — it's a multi-step flow: (1) prompt user to select text on the page, (2) capture the selection via `chrome.scripting.executeScript`, (3) `object.create` an Evidence object with the selection as description and the page URL as source, (4) `edge.create` linking Evidence → Claim via `res:supports`. The sidebar has access to `chrome.scripting` (it's an extension page with `scripting` permission), but the API calls should go through the service worker for consistency with S01's messaging pattern.

All code changes are in existing files — `sidebar.js` (replace stub handlers, add evidence capture UI), `service-worker.js` (add message handlers for `linkToPage` and `addEvidence`), and `sidebar.css` (style the evidence capture prompt). No new files needed.

## Recommendation

Add two new message types to the service worker (`linkToPage` and `addEvidence`) that make the API calls using the existing inline fetch + `_getApiConfig()` pattern. The sidebar handles all UI (text selection capture, loading states, toasts) and sends action requests to the service worker. Keep the text selection capture in sidebar.js using `chrome.scripting.executeScript` directly — the sidebar is an extension page with full API access, and routing text extraction through the service worker would add unnecessary complexity.

Build "Link to this page" first (single API call, straightforward) then "Add Evidence" (multi-step with content script interaction). Both can be verified with `node --check` syntax validation and manual sideload testing.

## Implementation Landscape

### Key Files

**Modify:**
- `extension/sidebar/sidebar.js` — Replace the two stub `addEventListener` handlers in `_renderCard()` with real action logic. Add `_currentTabUrl` and `_currentTabTitle` state tracking (populated from `getContextResults` response or `chrome.tabs.query`). Add `_linkToPage(objectIri)` function that sends `{type: 'linkToPage', objectIri, pageUrl, pageTitle}` to service worker. Add `_addEvidence(claimIri, claimLabel)` function that: (a) shows an "evidence capture" prompt in the sidebar, (b) calls `chrome.scripting.executeScript` to get selected text from active tab, (c) sends `{type: 'addEvidence', claimIri, selectedText, pageUrl, pageTitle}` to service worker. Add evidence capture UI elements (prompt panel, confirm/cancel buttons).
- `extension/background/service-worker.js` — Add `linkToPage` message handler: reads `_getApiConfig()`, calls `POST /api/commands` with `edge.create` params (`{source: objectIri, target: pageUrl, predicate: 'schema:url'}`). Add `addEvidence` message handler: two sequential API calls — first `object.create` (`{type: claimTypeIri, properties: {'res:description': selectedText, 'res:source': pageUrl, 'res:evidenceType': 'quote', 'dcterms:created': todayDate}}`), then `edge.create` (`{source: evidenceIri, target: claimIri, predicate: 'res:supports'}`). Both handlers return `{success: true}` or `{error: message}`.
- `extension/sidebar/sidebar.css` — Add styles for evidence capture prompt (`.evidence-prompt` panel with instruction text, selected text preview, confirm/cancel buttons). Update `.action-stub` → `.action-link` and `.action-evidence` with distinct active styling (no longer dashed-border stubs).

### Architecture

```
"Link to this page" flow:
  sidebar: user clicks "Link to this page" on result card
    → sidebar.js: _linkToPage(objectIri)
      → chrome.runtime.sendMessage({type: 'linkToPage', objectIri, pageUrl})
        → service-worker.js: POST /api/commands {command: 'edge.create',
            params: {source: objectIri, target: pageUrl, predicate: 'schema:url'}}
          → response → sendResponse({success: true})
    → sidebar.js: showToast('✓ Linked to this page')

"Add Evidence" flow:
  sidebar: user clicks "Add Evidence" on a Claim card
    → sidebar.js: _addEvidence(claimIri, claimLabel)
      → show evidence prompt: "Select text on the page, then click Capture"
      → user clicks "Capture" button
        → chrome.scripting.executeScript on active tab → get selectedText
        → if no selection: showToast('Select text on the page first', 'error')
        → chrome.runtime.sendMessage({type: 'addEvidence', claimIri, selectedText, pageUrl, pageTitle})
          → service-worker.js:
            1. POST /api/commands {command: 'object.create',
                params: {type: 'urn:sempkm:model:research:Evidence',
                  properties: {'res:description': selectedText, 'res:source': pageUrl,
                    'res:evidenceType': 'quote', 'dcterms:created': today}}}
            2. POST /api/commands {command: 'edge.create',
                params: {source: newEvidenceIri, target: claimIri, predicate: 'res:supports'}}
          → sendResponse({success: true, evidenceIri})
    → sidebar.js: showToast('✓ Evidence captured and linked')
    → hide evidence prompt
```

### Key Implementation Details

**Page URL/title tracking in sidebar:**
The `getContextResults` response from the service worker already includes `url`. The sidebar should store this as `_currentTabUrl`. For the title, add it to the response (service worker's `getContextResults` handler can include `tab.title` alongside `tab.url`). Alternatively, sidebar can call `chrome.tabs.query({active: true, currentWindow: true})` directly — simpler and avoids modifying the service worker's existing response shape.

**Evidence type detection for "Add Evidence" button visibility:**
The "Add Evidence" button should only appear on Claim-type results (not Notes, Concepts, etc.). The context query results include `type_iri` — check if it matches `urn:sempkm:model:research:Claim`. In `_renderCard()`, conditionally render the evidence button based on `item.type_iri`.

**Text selection from sidebar context:**
The sidebar is a Chrome side panel (extension page), not a content script. It has `chrome.scripting.executeScript` access via the `scripting` permission. The content script function is simple — just `window.getSelection().toString().trim()`. This is a subset of what `extractor.js` already does, but we don't need the full extraction — just the selection text.

**Edge predicate for "Link to this page":**
Use `schema:url` (`http://schema.org/url`) as the predicate. The page URL is the target (a valid URI). The source is the existing object IRI. This creates the same kind of relationship that the context-query endpoint searches for (URL matching tier), so after linking, the object will appear in context results when visiting that page again.

**Evidence type IRI:**
The research model Evidence type is `urn:sempkm:model:research:Evidence`. The `object.create` handler resolves full IRIs directly. Evidence properties use the `res:` prefix (`urn:sempkm:model:research:`): `res:description`, `res:evidenceType`, `res:source`, `res:strength`.

**Loading/disabled state during API calls:**
While an action is in progress, disable the button and show a spinner or "Linking..." text to prevent double-clicks. Re-enable on success or error.

### Build Order

1. **T01: "Link to this page" action** — Modify service-worker.js (add `linkToPage` message handler with inline fetch `edge.create` call). Modify sidebar.js (replace link stub handler with `_linkToPage()`, track page URL via `chrome.tabs.query`, add loading state). Update sidebar.css (`.action-link` style replacing `.action-stub` for the link button). Verify with `node --check` on both files.

2. **T02: "Add Evidence" action** — Modify service-worker.js (add `addEvidence` message handler with two sequential API calls: `object.create` then `edge.create`). Modify sidebar.js (replace evidence stub handler with `_addEvidence()`, add evidence capture prompt UI, add `chrome.scripting.executeScript` for text selection, conditionally show button only for Claims). Update sidebar.css (`.evidence-prompt` panel styles, `.action-evidence` button style). Verify with `node --check` on all modified files.

3. **T03: Unit tests + syntax validation** — Add Node.js unit tests for any new pure functions (if any are extracted to context-utils.js). Run `node --check` on all modified files. Verify Chrome manifest still validates (no new permissions needed — `scripting` already present).

### Verification Approach

- `node --check extension/background/service-worker.js` — syntax valid
- `node --check extension/sidebar/sidebar.js` — syntax valid  
- `node --test extension/tests/test-context-utils.js` — existing 23 tests still pass (no regressions from context-utils.js changes, if any)
- Manual sideload verification: load unpacked extension in Chrome, navigate to a page with matching objects, open sidebar via Alt+K, click "Link to this page" → check toast success → verify edge appears in SemPKM relations panel
- Manual sideload verification: open sidebar showing a Claim result, click "Add Evidence" → select text on page → click Capture → check toast success → verify Evidence object created in SemPKM

## Constraints

- **No ES module imports in sidebar.js** — sidebar loads as a plain script via `<script>` tag. Cannot `import` from api-client.js. All API calls must go through service worker messaging (S01 pattern).
- **No ES module imports in service-worker.js** — uses `importScripts()` (classic script) for Firefox compatibility. All new code must be plain functions, no `import` statements.
- **`chrome.scripting.executeScript` requires active tab** — the function injected into the page must be self-contained (no closures over extension variables). Same constraint as extractor.js.
- **Edge target must be a URI** — `edge_create.py` wraps `params.target` in `URIRef()`. Page URLs (http/https) are valid URIs. Non-URL strings would fail.
- **Evidence type only exists when research model is installed** — the "Add Evidence" action will fail if the user hasn't installed the research mental model. The service worker should return a clear error, and the sidebar should show a helpful toast ("Research model not installed" or similar). Ideally, the button only appears for Claim-type items (which only exist when the research model is installed).

## Common Pitfalls

- **Double-click on action buttons** — If the user clicks "Link to this page" twice before the first call completes, two edges get created. Disable the button and show loading state during the API call.
- **Stale `_currentTabUrl` after navigation** — If the user navigates to a new page while the sidebar is open, the cached URL is stale. Listen for `contextResultsUpdated` messages (already done) and re-query `chrome.tabs.query` when results update.
- **Evidence capture with no text selected** — User clicks "Add Evidence" then "Capture" without selecting text. Handle gracefully: check `selectedText.length > 0` before proceeding, show "Select text on the page first" toast.
- **Service worker shutdown during multi-step "Add Evidence"** — MV3 can terminate the service worker mid-execution. The two API calls (object.create + edge.create) are not atomic. If the first succeeds and the second fails, an orphaned Evidence object exists. Accept this — the user can link it manually later. Log the created Evidence IRI in the error toast.

## Open Risks

- **Evidence flow UX may feel clunky** — The user must: click "Add Evidence" in sidebar → go to the page and select text → return to sidebar and click "Capture". This back-and-forth between sidebar and page content may feel awkward. If usability testing shows friction, a future improvement could use a content script overlay for text selection instead of the sidebar prompt.
- **Research model may not be installed** — "Add Evidence" only makes sense when the research model (with Claim and Evidence types) is installed. The button visibility should be conditional on `type_iri` matching Claim. If no research model is installed, no Claims appear in results, so no "Add Evidence" buttons appear — this is naturally handled.
