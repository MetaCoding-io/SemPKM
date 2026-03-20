---
estimated_steps: 6
estimated_files: 2
---

# T03: Wire Accept and Dismiss actions for suggestions

**Slice:** S02 — Extension sidebar AI Insights UI
**Milestone:** M028

## Description

Wire the Accept and Dismiss buttons rendered by T02's `_renderSuggestionsSection()` to the service worker message handlers built in T01. Accept creates objects/edges in the knowledge graph; Dismiss persists per-URL in chrome.storage.local and removes the card from the DOM.

The suggestion type determines what the Accept action creates:
- `"link"` → creates a `schema:url` edge from the target object to the page URL
- `"evidence"` → creates a `res:Evidence` object, then links it to the target via `res:supports`
- `"supports"` → creates a `res:supports` edge
- `"contradicts"` → creates a `res:refutes` edge

Dismiss stores the suggestion's `target_iri` in chrome.storage.local keyed by the current URL, and removes the card from the DOM with a fade animation. On subsequent sidebar loads, dismissed IRIs are filtered before rendering.

## Steps

1. **Add Accept click handler in `_renderSuggestionsSection()`.** In `sidebar.js`, within the function that renders suggestion cards (written in T02), wire the `.btn-accept` button's click event:
   - Read suggestion data from the card's data attributes or closure variable (prefer closure since the suggestion object is available at render time)
   - Set button text to "Accepting...", disable both Accept and Dismiss buttons on this card
   - Send message to service worker: `chrome.runtime.sendMessage({type: 'acceptSuggestion', suggestion: {type, label, target_iri, target_label, reason}, pageUrl: _currentTabUrl, pageTitle: _currentTabTitle}, callback)`
   - On success response (`response.success`): show green toast `✓ Linked to {target_label}`, update the card to show a "✓ Accepted" state (replace buttons with a green checkmark text, or add `.accepted` class that styles the card as completed)
   - On error response or `chrome.runtime.lastError`: show red error toast with detail, re-enable buttons, reset button text

2. **Add Dismiss click handler in `_renderSuggestionsSection()`.** Wire the `.btn-dismiss` button's click event:
   - Disable both buttons, set Dismiss text to "Dismissing..."
   - Send message: `chrome.runtime.sendMessage({type: 'dismissSuggestion', url: _currentTabUrl, suggestionIri: suggestion.target_iri}, callback)`
   - On success: add `.fade-out` class to the card element, after animation ends remove card from DOM. Show brief "Dismissed" toast. Decrement the suggestions group count badge.
   - On error: show error toast, re-enable buttons

3. **Ensure T02's `_initAIInsights()` fetches dismissed IRIs before rendering suggestions.** Verify that the dismissed IRIs are fetched via `getDismissedSuggestions` and stored in `_aiDismissedIris` before the `aiInsightsProgress` handler renders the suggestions section. The flow should be:
   - `_initAIInsights()` sends `getDismissedSuggestions` message, stores result
   - When `aiInsightsProgress` with `section: 'suggestions'` arrives, filter: `suggestions.filter(s => !_aiDismissedIris.includes(s.target_iri))`
   - This filtering was specified in T02's step 4 but verify it's properly implemented

4. **Add CSS for Accept/Dismiss interaction states.** In `sidebar.css`:
   - `.ai-suggestion-card.accepted` — muted background, green left border, reduced opacity
   - `.ai-suggestion-card.accepted .btn-accept, .ai-suggestion-card.accepted .btn-dismiss` — hidden
   - `.ai-suggestion-card .accepted-badge` — green text "✓ Accepted" that replaces buttons
   - `.ai-suggestion-card.fade-out` — animation: `fadeSlideOut 0.25s ease-in forwards`
   - `@keyframes fadeSlideOut` — from `{opacity: 1; max-height: 200px}` to `{opacity: 0; max-height: 0; padding: 0; margin: 0; overflow: hidden}`
   - `.btn-accept:disabled, .btn-dismiss:disabled` — ensure disabled state styles are present (opacity 0.5, cursor not-allowed)

5. **Handle edge cases:**
   - If `_currentTabUrl` is empty when Accept/Dismiss is clicked, show error toast "Navigate to a page first" (matching the `_linkToPage` guard pattern)
   - After Accept success, invalidate the `aiCache` for this URL in the service worker so next sidebar open fetches fresh data (send a `{type: 'invalidateAiCache', url: _currentTabUrl}` message, or just accept that cache will show stale accepted state until navigation). For v1, stale cache is acceptable — the card visually shows "Accepted" state.
   - After Dismiss, if the suggestions group has 0 remaining cards, hide the entire suggestions group.

6. **Verify.** `node --check` on both files. Grep for message sends.

## Must-Haves

- [ ] Accept button sends `acceptSuggestion` message with correct suggestion data and page URL
- [ ] Accept shows loading state, success toast with target label, and "Accepted" card state
- [ ] Accept error shows red toast and re-enables buttons
- [ ] Dismiss button sends `dismissSuggestion` message with URL and IRI
- [ ] Dismiss removes card from DOM with fade animation
- [ ] Dismiss shows brief toast
- [ ] Dismissed IRIs filtered from suggestions on subsequent sidebar loads
- [ ] Empty suggestions group hidden after last card dismissed
- [ ] `node --check extension/sidebar/sidebar.js` passes

## Verification

- `node --check extension/sidebar/sidebar.js` — zero errors
- `grep 'acceptSuggestion' extension/sidebar/sidebar.js` — confirms Accept sends this message type
- `grep 'dismissSuggestion' extension/sidebar/sidebar.js` — confirms Dismiss sends this message type
- `grep 'fade-out\|fadeSlideOut' extension/sidebar/sidebar.css` — confirms dismiss animation exists
- `grep 'accepted-badge\|\.accepted' extension/sidebar/sidebar.css` — confirms accepted card state styles

## Inputs

- `extension/sidebar/sidebar.js` — T02 output with `_renderSuggestionsSection()` rendering Accept/Dismiss buttons. T02 set data attributes or made suggestion objects available in closure. `_aiDismissedIris` state variable, `_currentTabUrl` state variable, `showToast()` function.
- `extension/sidebar/sidebar.css` — T02 output with `.btn-accept`, `.btn-dismiss` base styles
- `extension/background/service-worker.js` — T01 output with `acceptSuggestion` handler (maps type → API commands), `dismissSuggestion` handler (persists to chrome.storage.local), `getDismissedSuggestions` handler (reads dismissed IRIs)
- S01 accept mapping: "link" → edge.create(schema:url), "evidence" → object.create(res:Evidence) + edge.create(res:supports), "supports" → edge.create(res:supports), "contradicts" → edge.create(res:refutes)

## Expected Output

- `extension/sidebar/sidebar.js` — Accept and Dismiss click handlers wired in `_renderSuggestionsSection()`, interaction state management (~60 lines added/modified)
- `extension/sidebar/sidebar.css` — Accepted card state, fade-out animation, disabled button states (~25 lines added)

## Observability Impact

- **Accept tracing:** Filter sidebar console for `[SemPKM Sidebar] AI acceptSuggestion:` — logs suggestion type and target IRI on every Accept click.
- **Dismiss tracing:** Filter sidebar console for `[SemPKM Sidebar] AI dismissSuggestion:` — logs target IRI on every Dismiss click.
- **Error visibility:** Both handlers log `acceptSuggestion error:` / `dismissSuggestion error:` to console on chrome.runtime.lastError, plus show red toast to the user.
- **Visual states:** Accepted cards gain `.accepted` class (green border, muted); dismissed cards animate via `.fade-out` then are removed from DOM.
- **Dismiss persistence:** After dismiss, `_aiDismissedIris` array is updated in-memory so subsequent re-renders also filter the dismissed suggestion. Persistent storage checked via `chrome.storage.local` keys matching `dismissed_suggestions_{url}`.
- **Empty group:** When all suggestion cards are dismissed, the entire `#ai-suggestions` container is cleared.
