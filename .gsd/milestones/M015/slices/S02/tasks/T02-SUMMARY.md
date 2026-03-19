---
id: T02
parent: S02
milestone: M015
provides:
  - addEvidence service worker handler with two sequential API calls (object.create + edge.create)
  - Evidence capture prompt UI in sidebar with text selection via chrome.scripting.executeScript
  - Conditional "Add Evidence" button rendering for Claim-type results only
key_files:
  - extension/background/service-worker.js
  - extension/sidebar/sidebar.js
  - extension/sidebar/sidebar.css
  - extension/sidebar/sidebar.html
key_decisions:
  - Evidence prompt replaces results panel (hidden toggle) rather than overlaying, keeping the layout simple
  - Text preview shown after capture but before API send, so user sees what will be saved
patterns_established:
  - Two-step API call pattern in service worker with partial failure reporting (orphaned IRI in error response)
  - chrome.scripting.executeScript with self-contained function for cross-context text extraction
observability_surfaces:
  - Service worker console logs with [SemPKM] addEvidence prefix for each step (create, link, success/error)
  - Sidebar toast messages for success and error states including Evidence IRI on partial failure
  - Capture button disabled state during API call
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Wire "Add Evidence" action with text selection capture

**Replaced stub "Add Evidence" button with full capture flow: conditional Claim rendering, evidence prompt panel, chrome.scripting.executeScript text extraction, two-step service worker API (object.create + edge.create) with partial failure handling**

## What Happened

Added `addEvidence` message handler to service-worker.js following the same async IIFE pattern from T01's `linkToPage`. The handler makes two sequential POST calls to `/api/commands`: first `object.create` for the Evidence object, then `edge.create` to link it to the Claim. Partial failure (object created, edge failed) returns the Evidence IRI in the error response so the user can link it manually.

In sidebar.js, replaced the stub evidence button with a conditional check — only rendered when `item.type_iri` contains `research:Claim`. The button opens an evidence capture prompt panel that instructs the user to select text, then captures it via `chrome.scripting.executeScript` with a self-contained function. After capture, the selected text preview is shown and the `addEvidence` message is sent to the service worker.

Added the evidence prompt container to sidebar.html and styled it in sidebar.css with amber-tinted `.action-evidence` button and a full `.evidence-prompt` panel with title, instructions, monospace preview, and Capture/Cancel buttons.

Removed all `.action-stub` references from sidebar.js — both action buttons are now real implementations.

## Verification

- `node --check extension/background/service-worker.js` — syntax valid
- `node --check extension/sidebar/sidebar.js` — syntax valid
- `node --test extension/tests/test-context-utils.js` — 23/23 pass, 0 fail
- `rg` checks confirmed: `addEvidence` handler exists, `action-evidence` class used, `evidence-prompt` in HTML, `research:Claim` conditional check, `chrome.scripting.executeScript` call present
- No `action-stub` references remain in sidebar.js
- Both `linkToPage` and `addEvidence` handlers present in service-worker.js

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 2 | `node --check extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 3 | `node --test extension/tests/test-context-utils.js` | 0 | ✅ pass (23/23) | 3.5s |
| 4 | `rg "type === 'addEvidence'" extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 5 | `rg 'action-evidence' extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 6 | `rg 'evidence-prompt' extension/sidebar/sidebar.html` | 0 | ✅ pass | <1s |
| 7 | `rg 'research:Claim' extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |
| 8 | `rg 'chrome.scripting.executeScript' extension/sidebar/sidebar.js` | 0 | ✅ pass | <1s |

## Diagnostics

- **Service worker console** (`chrome://extensions` → service worker "Inspect"):
  - `[SemPKM] addEvidence: creating evidence object` — step 1 start
  - `[SemPKM] addEvidence: evidence created <IRI>` — step 1 success
  - `[SemPKM] addEvidence: linking evidence to claim` — step 2 start
  - `[SemPKM] addEvidence: success` — full success
  - `[SemPKM] addEvidence: error: <detail>` — any failure
- **Sidebar toasts**: "✓ Evidence captured and linked" on success, error detail on failure (includes Evidence IRI on partial failure)
- **Button states**: Capture button shows "Capturing…" and disables during API call
- **Evidence prompt**: `#evidence-prompt[hidden]` attribute tracks visibility

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `extension/background/service-worker.js` — added `addEvidence` message handler with two sequential API calls and partial failure reporting
- `extension/sidebar/sidebar.js` — conditional evidence button for Claims, evidence prompt flow, text capture via chrome.scripting.executeScript, _addEvidence message send
- `extension/sidebar/sidebar.css` — `.action-evidence` amber button styles, `.evidence-prompt` panel styles, `.btn-capture` / `.btn-cancel` styles
- `extension/sidebar/sidebar.html` — added `#evidence-prompt` container with title, instructions, preview, and action buttons
- `.gsd/milestones/M015/slices/S02/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
