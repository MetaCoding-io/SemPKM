---
estimated_steps: 9
estimated_files: 4
---

# T02: Wire "Add Evidence" action with text selection capture

**Slice:** S02 — In-context actions — Link to page and Add Evidence
**Milestone:** M015

## Description

Replace the stub "Add Evidence" button with the full multi-step capture flow: user clicks "Add Evidence" on a Claim → sidebar shows evidence capture prompt → user selects text on the page → clicks "Capture" in sidebar → sidebar extracts selection via `chrome.scripting.executeScript` → service worker creates an Evidence object and links it to the Claim → toast confirms.

This is the complex action — two sequential API calls (object.create then edge.create) with content script interaction. The sidebar is a Chrome extension page (not a content script), so it has full access to `chrome.scripting.executeScript`. The function injected into the page must be self-contained (no closures).

The "Add Evidence" button should only appear on Claim-type results. The context query results include `type_iri` — check if it matches `urn:sempkm:model:research:Claim`. This naturally handles the case where the research model isn't installed (no Claims = no evidence buttons).

**Key constraint:** The `addEvidence` service worker handler makes two sequential API calls. If the first (object.create) succeeds but the second (edge.create) fails, an orphaned Evidence object exists. This is acceptable — log the Evidence IRI in the error toast so the user can link it manually.

## Steps

1. **Service worker — add `addEvidence` message handler** in `extension/background/service-worker.js`:
   - In the `chrome.runtime.onMessage.addListener` callback, add a new `if (message.type === 'addEvidence')` block
   - Handler receives `{claimIri, selectedText, pageUrl, pageTitle}` from the message
   - Read config via `_getApiConfig()` — if null, `sendResponse({error: 'SemPKM not configured'})`
   - **Step 1: Create Evidence object** — POST to `${config.instanceUrl}/api/commands`:
     ```json
     {
       "command": "object.create",
       "params": {
         "type": "urn:sempkm:model:research:Evidence",
         "properties": {
           "urn:sempkm:model:research:description": selectedText,
           "urn:sempkm:model:research:source": pageUrl,
           "urn:sempkm:model:research:evidenceType": "quote",
           "http://purl.org/dc/terms/created": new Date().toISOString().slice(0, 10)
         }
       }
     }
     ```
   - Parse the response to get the new Evidence IRI from `results[0].iri`
   - **Step 2: Link Evidence → Claim** — POST to `${config.instanceUrl}/api/commands`:
     ```json
     {
       "command": "edge.create",
       "params": {
         "source": evidenceIri,
         "target": claimIri,
         "predicate": "urn:sempkm:model:research:supports"
       }
     }
     ```
   - On full success: `sendResponse({success: true, evidenceIri})`
   - On step 1 failure: `sendResponse({error: 'Failed to create evidence: ' + detail})`
   - On step 2 failure: `sendResponse({error: 'Evidence created but linking failed. Evidence IRI: ' + evidenceIri, evidenceIri, partial: true})`
   - Console log `[SemPKM] addEvidence:` prefixed messages for each step
   - Return `true` for async sendResponse

2. **Sidebar — conditional evidence button rendering** in `extension/sidebar/sidebar.js`:
   - In `_renderCard()`, only create the "Add Evidence" button when `item.type_iri` ends with `:Claim` or equals `urn:sempkm:model:research:Claim`
   - Use a simple check: `var isClaim = item.type_iri && item.type_iri.indexOf(':Claim') !== -1 && item.type_iri.indexOf('research:Claim') !== -1;`
   - Only append `evidenceBtn` to `actions` div when `isClaim` is true
   - Change evidence button CSS class from `'action-stub'` to `'action-evidence'`

3. **Sidebar — evidence capture prompt UI** in `extension/sidebar/sidebar.js`:
   - Add a `_showEvidencePrompt(claimIri, claimLabel)` function that:
     - Creates (or shows) the evidence prompt panel in the results area
     - Prompt contains: instruction text ("Select text on the page, then click Capture"), a label showing the target Claim, Capture button, Cancel button
     - Stores `claimIri` in module-level `_pendingEvidenceClaim` variable
   - Add a `_hideEvidencePrompt()` function that hides/removes the prompt
   - Cancel button calls `_hideEvidencePrompt()`

4. **Sidebar — text selection capture via chrome.scripting.executeScript** in `extension/sidebar/sidebar.js`:
   - Capture button handler:
     - Query active tab via `chrome.tabs.query({active: true, currentWindow: true})`
     - Call `chrome.scripting.executeScript({target: {tabId: tab.id}, func: function() { return window.getSelection().toString().trim(); }})` — the function must be self-contained, no closures
     - Extract the result from `results[0].result`
     - If empty string: `showToast('Select text on the page first', 'error'); return;`
     - Show selected text preview in the prompt panel

5. **Sidebar — `_addEvidence()` sends message to service worker** in `extension/sidebar/sidebar.js`:
   - After successful text extraction, disable Capture button, show "Capturing…" text
   - Send `chrome.runtime.sendMessage({type: 'addEvidence', claimIri: _pendingEvidenceClaim, selectedText: extractedText, pageUrl: _currentTabUrl, pageTitle: _currentTabTitle})`
   - On success response: `showToast('✓ Evidence captured and linked')`, call `_hideEvidencePrompt()`
   - On error response: `showToast(response.error, 'error')` — if `response.partial`, the toast already includes the Evidence IRI
   - Re-enable Capture button on completion (success or error)
   - Handle `chrome.runtime.lastError`

6. **Sidebar HTML — add evidence prompt container** in `extension/sidebar/sidebar.html`:
   - Add a `<div id="evidence-prompt" class="evidence-prompt" hidden>` inside `<main>`, after the `#results` div
   - Contents: `<p class="evidence-prompt-title">` for claim label, `<p class="evidence-prompt-instructions">` for instruction text, `<div class="evidence-prompt-preview">` for selected text preview, `<div class="evidence-prompt-actions">` with Capture and Cancel buttons

7. **CSS — evidence prompt and button styles** in `extension/sidebar/sidebar.css`:
   - Add `.evidence-prompt` styles: surface background, border, padding, margin
   - Add `.evidence-prompt-title` — bold, truncated
   - Add `.evidence-prompt-instructions` — muted text
   - Add `.evidence-prompt-preview` — monospace, max-height with overflow, background slightly different for contrast
   - Add `.evidence-prompt-actions` — flex row with gap
   - Add `.action-evidence` button style (distinct from `.action-link`): slightly amber/yellow tint to differentiate from the link action
     ```css
     .action-evidence {
       color: #d97706;
       background: rgba(217, 119, 6, 0.1);
       border: 1px solid rgba(217, 119, 6, 0.25);
     }
     .action-evidence:hover {
       background: rgba(217, 119, 6, 0.2);
       border-color: #d97706;
     }
     .action-evidence:disabled {
       opacity: 0.5;
       cursor: not-allowed;
     }
     ```
   - Add `.btn-capture` and `.btn-cancel` for prompt action buttons

8. **Syntax validation**: Run `node --check` on `service-worker.js`, `sidebar.js`

9. **Regression check**: Run `node --test extension/tests/test-context-utils.js` — all 23 tests pass

## Must-Haves

- [ ] Service worker handles `addEvidence` message with two sequential API calls (object.create then edge.create)
- [ ] Partial failure (object created, edge failed) reports Evidence IRI in error response
- [ ] "Add Evidence" button only renders for Claim-type results (type_iri contains `research:Claim`)
- [ ] Evidence capture prompt shows in sidebar with instructions, claim label, Capture/Cancel buttons
- [ ] `chrome.scripting.executeScript` extracts selected text from active tab
- [ ] Empty selection shows error toast ("Select text on the page first")
- [ ] Capture button disables during API call and re-enables on response
- [ ] Success toast: "✓ Evidence captured and linked"
- [ ] Evidence prompt hides on success or Cancel
- [ ] `.action-evidence` CSS class on the button (amber-tinted, not dashed stub)
- [ ] `node --check` passes on all modified JS files
- [ ] 23 existing unit tests still pass

## Verification

- `node --check extension/background/service-worker.js` — no syntax errors
- `node --check extension/sidebar/sidebar.js` — no syntax errors
- `node --test extension/tests/test-context-utils.js` — 23/23 pass
- `rg "type === 'addEvidence'" extension/background/service-worker.js` — handler exists
- `rg 'action-evidence' extension/sidebar/sidebar.js` — button uses new class
- `rg 'evidence-prompt' extension/sidebar/sidebar.html` — prompt container exists
- `rg 'research:Claim' extension/sidebar/sidebar.js` — conditional rendering check exists
- `rg 'chrome.scripting.executeScript' extension/sidebar/sidebar.js` — text extraction call exists

## Inputs

- `extension/background/service-worker.js` — from T01, now has `linkToPage` handler alongside existing message handlers
- `extension/sidebar/sidebar.js` — from T01, now has `_currentTabUrl`/`_currentTabTitle` tracking and `_linkToPage()` function
- `extension/sidebar/sidebar.css` — from T01, now has `.action-link` styles
- `extension/sidebar/sidebar.html` — existing HTML from S01
- S01 summary: sidebar.js is an IIFE with `showToast(message, type)`, `_showState(name)`, `_renderCard(item)`, `renderResults(results)`. Items have `{iri, label, type_iri, type_label, match_type, snippet}`. Service worker uses inline fetch with `_getApiConfig()` returning `{instanceUrl, apiKey}`.
- Research doc constraints: Evidence type IRI is `urn:sempkm:model:research:Evidence`. Properties use `urn:sempkm:model:research:` prefix (description, source, evidenceType). Edge predicate is `urn:sempkm:model:research:supports`. `chrome.scripting.executeScript` injected function must be self-contained (no closures). The two API calls are not atomic — accept orphaned Evidence on partial failure.

## Expected Output

- `extension/background/service-worker.js` — extended with `addEvidence` message handler (two sequential API calls)
- `extension/sidebar/sidebar.js` — evidence button conditional on Claim type, `_addEvidence()` with prompt flow and text capture
- `extension/sidebar/sidebar.css` — `.evidence-prompt` panel styles, `.action-evidence` button styles
- `extension/sidebar/sidebar.html` — evidence prompt container div added

## Observability Impact

- **Service worker console** (`chrome://extensions` → service worker "Inspect"):
  - `[SemPKM] addEvidence: creating evidence object` — step 1 start
  - `[SemPKM] addEvidence: evidence created <IRI>` — step 1 success
  - `[SemPKM] addEvidence: linking evidence to claim` — step 2 start
  - `[SemPKM] addEvidence: success` — full success
  - `[SemPKM] addEvidence: error: <detail>` — any failure
- **Sidebar toast messages**: "✓ Evidence captured and linked" on success; error detail on failure (includes Evidence IRI on partial failure)
- **Button state**: "Capture" button disables during API calls, re-enables on completion
- **Evidence prompt panel**: visible when capture flow is active, hidden on success/cancel — inspect `#evidence-prompt[hidden]` attribute
- **Failure artifacts**: on partial failure (object created, edge failed), Evidence IRI is surfaced in both the error toast and the service worker console log
