# S02: Extension sidebar AI Insights UI — UAT

**Milestone:** M028
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for contract verification + live-runtime for visual/interaction verification)
- Why this mode is sufficient: Syntax validation and unit tests prove code contracts offline. Visual progressive loading, badge colors, accept/dismiss UX, and toast notifications require a running Chrome extension instance. The full E2E automation is S03's scope — this UAT covers what a human tester should verify in a live browser.

## Preconditions

1. Docker test stack running (`docker compose -f docker-compose.test.yml up -d`) with at least one Mental Model installed (basic-pkm)
2. LLM configured on the backend (any provider — or intentionally unconfigured for degradation test)
3. An API token created at Admin > API Keys
4. Extension loaded unpacked in Chrome (`chrome://extensions` → Developer mode → Load unpacked → `extension/` directory)
5. Extension configured: Settings page → Instance URL = `http://localhost:3901`, API Key = the token from step 3, Test Connection = green
6. At least one Note object exists in SemPKM (for graph matching to find results)

## Smoke Test

Open any web page (e.g., a Wikipedia article), press Alt+K to open the sidebar, and verify the "AI Insights" section appears with a loading spinner that transitions through status messages. If LLM is configured, claims should appear within 5 seconds.

## Test Cases

### 1. Progressive Loading — Claims appear before matches

1. Navigate to a content-rich web page (e.g., a Wikipedia article about a well-known topic)
2. Press Alt+K to open the sidebar
3. Observe the AI Insights section loading state
4. **Expected:** Loading text shows "Analyzing page..." initially, then "Matching against your graph..." after claims render, then "Finding relationships..." after matches render, then "Generating summary..." after suggestions render. Each section appears independently as its API call completes.

### 2. Claim Cards with Confidence Badges

1. After AI Insights loads on a content page, look at the Claims section
2. Expand the "Detected Claims" sub-group if collapsed
3. **Expected:** Each claim card shows the claim text, a confidence badge (one of: established/green, likely/blue, possible/amber, speculative/gray), and a type badge (e.g., "factual", "causal"). Badges are color-coded and legible.

### 3. Graph Matches with Indicator Badges

1. With claims loaded, check the "Graph Matches" section
2. **Expected:** If the graph has matching objects, matches appear nested under the claim text they match. Each match shows the object label, a colored indicator badge (contradicts=red, corroborates=green, contested=amber, related=gray), and a confidence level. If no matches found, the section is empty/hidden.

### 4. Research Gap Alert Cards

1. If the Research model is installed with ResearchQuestion objects, load a page related to one of those questions
2. **Expected:** Research gaps appear as alert-style cards with an amber left border, showing the research question text and a message about missing evidence. If no Research model or no matching questions, this section is absent.

### 5. Accept a Relationship Suggestion

1. After AI Insights loads, find a suggestion card in the "Suggestions" section
2. Click the "Accept" button on a suggestion
3. **Expected:** Button changes to "Accepting..." and becomes disabled. On success, a green toast "✓ Linked to [target label]" appears. The Accept/Dismiss buttons are replaced with a green "✓ Accepted" badge. The card has a green left border and muted styling.

### 6. Dismiss a Suggestion

1. Find another suggestion card (or reload the page to get fresh suggestions)
2. Click the "Dismiss" button
3. **Expected:** A brief "Dismissed" toast appears. The card fades out with a slide-up animation and is removed from the DOM. The suggestion count badge updates.

### 7. Dismissed Suggestions Persist Across Reloads

1. After dismissing a suggestion, close and reopen the sidebar (or navigate away and back)
2. **Expected:** The previously dismissed suggestion does not reappear. The remaining suggestions show correctly.

### 8. LLM Unavailable Degradation

1. Temporarily remove LLM configuration from the backend (or use a stack with no LLM configured)
2. Open sidebar on any page
3. **Expected:** AI Insights section shows "AI features require LLM configuration" message with a link to settings. No loading spinner. No error toasts. No claims/matches/suggestions/summary sections rendered.

### 9. Summary Panel

1. After all AI Insights sections load on a content page (with LLM configured)
2. Scroll to the bottom of the AI Insights section
3. **Expected:** A summary panel shows a personalized text summary of the page content, styled in a distinct container with a subtle background.

### 10. Status Badge Count

1. After all AI Insights sections finish loading
2. Look at the AI Insights section header
3. **Expected:** A badge shows the total count of AI items (claims + matches + suggestions). Badge is hidden if count is 0.

## Edge Cases

### Rapid Page Navigation During Loading

1. Open sidebar on page A, immediately navigate to page B before AI results arrive
2. **Expected:** Results from page A do not render. Page B's AI pipeline starts fresh. No stale results from page A appear. Console may log "[SemPKM Sidebar] AI Insights: stale progress" for discarded messages.

### Restricted Page (chrome://, about:blank)

1. Navigate to `chrome://extensions` or `about:blank`
2. Open the sidebar
3. **Expected:** Content extraction fails gracefully. Either no AI Insights section loads, or it shows an appropriate message. No error toasts or console errors.

### Accept Error (Network Failure)

1. Disconnect from the network or stop the backend
2. Click Accept on a suggestion
3. **Expected:** Button re-enables after failure. Red toast shows error detail. The suggestion card remains in its original state (not marked as accepted).

### Empty Suggestions After All Dismissed

1. Dismiss every suggestion card in the list
2. **Expected:** The Suggestions sub-group header disappears or shows count 0. No empty container visible.

## Failure Signals

- Loading spinner stays indefinitely with no section content appearing → pipeline failure (check service worker console for `[SemPKM] AI Insights:` errors)
- All badges appear gray or unstyled → CSS not loaded (check sidebar.css is included)
- Accept button has no effect → service worker `acceptSuggestion` handler missing or erroring (check service worker console)
- Dismissed suggestions reappear on reload → chrome.storage.local not persisting (check `dismissed_*` key in DevTools Application tab)
- "undefined" text in claim cards → API response shape mismatch (check backend detect-claims response JSON)
- Green toast after Accept but no object in SemPKM → POST /api/commands Bearer auth failure (check service worker console for 401 errors)

## Requirements Proved By This UAT

- EXT-29 — Accept/dismiss UI: Test cases 5, 6, 7 prove accept creates edges and dismiss persists per-URL
- EXT-30 — Progressive loading: Test cases 1, 2, 3, 9 prove sections render independently as API calls complete
- EXT-31 — Graceful degradation: Test case 8 proves LLM-unavailable shows clear message without errors

## Not Proven By This UAT

- E2E automated verification of the full flow (S03 scope — Playwright test with mock LLM server)
- Claim extraction quality on real web pages (subjective quality check — requires diverse page testing)
- Graph matching false positive rate (requires populated graph with Research model objects)
- Performance under slow LLM responses (no latency simulation in this UAT)
- Firefox sidebar_action compatibility (Firefox extension loading not covered)

## Notes for Tester

- The AI pipeline makes 5 sequential API calls — total time depends on LLM response speed. Budget 5-15 seconds for a full pipeline run.
- The `aiCache` caches results per URL. To re-test the same page, navigate to a different URL first and come back, or clear the cache by reloading the extension.
- Accept creates real objects/edges in the graph — use a test instance or be prepared to clean up.
- The Dismiss key in chrome.storage.local is `dismissed_${pageURL}` — you can clear it manually in DevTools > Application > Storage > chrome.storage.local to re-test dismissals.
- If badges look unstyled, verify that `sidebar.css` is loaded by inspecting the sidebar iframe's `<link>` tags.
