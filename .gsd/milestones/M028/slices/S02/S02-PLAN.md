# S02: Extension sidebar AI Insights UI

**Goal:** The extension sidebar shows an "AI Insights" collapsible section that progressively loads detected claims, graph matches with contradiction/corroboration badges, relationship suggestions with Accept/Dismiss buttons, and a personalized summary — all consuming the S01 backend AI endpoints via service worker message passing.
**Demo:** User visits a page, opens sidebar via Alt+K, and sees progressive AI content: claims appear first, then matches with colored indicator badges, then suggestions with one-click Accept (creates object+edge) and Dismiss (persists per-URL), then a contextual summary. "AI features require LLM configuration" message shows when LLM is unavailable.

## Must-Haves

- Service worker handles `getAIInsights` message: calls GET /api/llm/status → POST /api/ai/detect-claims → POST /api/ai/match-claims → POST /api/ai/suggest-relationships → POST /api/ai/summarize sequentially, sending `aiInsightsProgress` messages to sidebar after each step completes
- Service worker extracts page content via `chrome.scripting.executeScript` (reusing addEvidence pattern)
- Service worker handles `acceptSuggestion` message: creates object + edge via two-step POST /api/commands pattern
- Service worker handles `dismissSuggestion` / `getDismissedSuggestions` messages: persists per-URL in chrome.storage.local
- Sidebar renders AI Insights section with per-section progressive loading and contextual loading text
- Claims render as cards with color-coded confidence badges (established=green, likely=blue, possible=amber, speculative=gray)
- Matches render nested under claims with indicator badges (contradicts=red, corroborates=green, contested=amber, related=gray)
- Research gaps render as alert-style cards
- Suggestions render with Accept and Dismiss buttons
- Summary renders as styled text panel
- LLM-unavailable state shows clear "AI features require LLM configuration" message
- Generation ID guards against stale results from prior page navigations
- Accept creates correct object/edge via existing two-step pattern (type varies by suggestion type)
- Dismiss persists IRI per-URL in chrome.storage.local and filters on subsequent loads
- `SemPKMClient` gains 5 new AI methods with Node.js unit tests

## Proof Level

- This slice proves: integration (extension sidebar consuming backend AI endpoints via service worker messaging)
- Real runtime required: yes (Chrome extension in browser, but static verification via `node --check` + unit tests for contracts)
- Human/UAT required: yes (visual verification of progressive loading UX, badge colors, accept/dismiss interaction)

## Verification

- `node --check extension/background/service-worker.js` — syntax valid
- `node --check extension/sidebar/sidebar.js` — syntax valid
- `node --check extension/shared/api-client.js` — syntax valid
- `node extension/tests/test-ai-client.js` — all new SemPKMClient AI method tests pass
- `grep -c 'getAIInsights\|acceptSuggestion\|dismissSuggestion\|getDismissedSuggestions\|getPageContent' extension/background/service-worker.js` — at least 5 message handlers present
- `grep -c '_renderAIInsights\|_renderClaimsSection\|_renderMatchesSection\|_renderSuggestionsSection\|_renderSummarySection' extension/sidebar/sidebar.js` — all 5 rendering functions present
- `grep 'ai-insights' extension/sidebar/sidebar.html` — AI Insights container div exists
- `grep 'ai-claims\|ai-matches\|ai-suggestions\|ai-summary\|ai-unavailable' extension/sidebar/sidebar.css` — CSS rules for all AI sections exist
- LLM-unavailable path: service worker returns `{available: false}` from status → sidebar shows message instead of loading AI results

## Observability / Diagnostics

- Runtime signals: `console.log('[SemPKM] AI Insights: ...')` messages in service worker for each pipeline step (status check, content extraction, detect-claims, match-claims, suggest-relationships, summarize)
- Inspection surfaces: `chrome.storage.local` keys `dismissed_suggestions_{url}` for dismiss persistence; service worker console for pipeline progress
- Failure visibility: Each pipeline step catches errors independently — partial results render (e.g., claims show even if match-claims fails). `console.error('[SemPKM] AI ...')` on every failure path. Toast notifications for accept/dismiss failures.
- Redaction constraints: API key never logged; page content truncated to 8000 chars before sending

## Integration Closure

- Upstream surfaces consumed: `GET /api/llm/status`, `POST /api/ai/detect-claims`, `POST /api/ai/match-claims`, `POST /api/ai/suggest-relationships`, `POST /api/ai/summarize`, `POST /api/commands` (all from S01, with Bearer auth)
- New wiring introduced in this slice: service worker message handlers (`getAIInsights`, `acceptSuggestion`, `dismissSuggestion`, `getDismissedSuggestions`), sidebar `_initAIInsights()` called from `init()`, `chrome.runtime.onMessage` listener for `aiInsightsProgress` in sidebar
- What remains before the milestone is truly usable end-to-end: S03 E2E tests with mock LLM server + Chapter 40 user guide

## Tasks

- [x] **T01: Service worker AI pipeline and page content extraction** `est:1h`
  - Why: Everything downstream (sidebar rendering, accept/dismiss) depends on these message handlers. The service worker is the bridge between sidebar UI and backend API — it has tab access for content extraction and can make authenticated fetch calls.
  - Files: `extension/background/service-worker.js`
  - Do: Add 5 new message handlers to the `chrome.runtime.onMessage.addListener` block: (1) `getAIInsights` — extracts page content via `chrome.scripting.executeScript` (copy the pattern from `_captureEvidence` in sidebar.js → use `document.body.innerText`, truncate to 8000 chars), calls `GET /api/llm/status` first, if `available: false` sends `{type: 'aiInsightsProgress', section: 'unavailable'}` and stops, otherwise sequentially calls detect-claims → match-claims → suggest-relationships → summarize, sending `{type: 'aiInsightsProgress', section: 'claims'|'matches'|'suggestions'|'summary', data: ...}` via `chrome.runtime.sendMessage` after each call. Includes a `generationId` (incrementing counter) in each progress message so sidebar can discard stale updates. Per-step error isolation — if detect-claims fails, still attempts suggest-relationships (which doesn't need claims). (2) `getPageContent` — extracts `document.body.innerText` from active tab via `chrome.scripting.executeScript`. (3) `acceptSuggestion` — creates object + edge via two-step fetch (exactly like `addEvidence` handler). Maps suggestion `type` to command params: "link" → edge.create with schema:url, "evidence" → object.create(res:Evidence) + edge.create(res:supports), "supports" → edge.create(res:supports), "contradicts" → edge.create(res:refutes). (4) `dismissSuggestion` — stores suggestion IRI in `chrome.storage.local` key `dismissed_${url}` (array of IRIs). (5) `getDismissedSuggestions` — reads dismissed IRIs for a given URL. Also add an in-memory `aiCache` (separate from `contextCache`) using the same LRU pattern (max 50 entries) for caching AI results per URL. All handlers must `return true` for async `sendResponse`.
  - Verify: `node --check extension/background/service-worker.js` passes. Grep confirms all 5 message types handled.
  - Done when: All 5 message handlers present and syntactically valid. Each handler follows existing patterns (async IIFE, error handling, `return true`).

- [x] **T02: Sidebar AI Insights rendering with progressive loading** `est:1h30m`
  - Why: This is the bulk of user-visible work — the sidebar must render AI results progressively as each backend call completes, with proper loading states, badges, and collapsible sections.
  - Files: `extension/sidebar/sidebar.js`, `extension/sidebar/sidebar.html`, `extension/sidebar/sidebar.css`
  - Do: (1) In sidebar.html: add `<div id="ai-insights" hidden>` after `#evidence-prompt`, containing inner containers: `#ai-unavailable` (message + settings link), `#ai-loading` (spinner + status text), `#ai-claims`, `#ai-matches`, `#ai-suggestions`, `#ai-summary`. (2) In sidebar.js: add `_initAIInsights()` function called from `init()` after `fetchResults()`. It sends `{type: 'getAIInsights'}` to the service worker. Add a `chrome.runtime.onMessage` listener for `aiInsightsProgress` that routes to section renderers. Implement `_aiGenerationId` counter that increments on each init — discard progress messages with stale generation IDs. (3) Section renderers: `_renderClaimsSection(claims)` — renders each claim as a card with confidence badge (span with CSS class `badge-confidence-{level}`), type badge, and claim text. `_renderMatchesSection(matches, gaps)` — renders matches nested under claim text, each matched object showing label + indicator badge (span with class `badge-indicator-{type}`) + confidence level. Research gaps rendered as alert-style cards with question icon. `_renderSuggestionsSection(suggestions)` — renders each suggestion as a card with label, reason text, target info, Accept button (class `btn-accept`) and Dismiss button (class `btn-dismiss`). `_renderSummarySection(summary)` — renders summary text in a styled container. `_renderUnavailable()` — shows "AI features require LLM configuration" with link to extension settings. (4) Loading states: `#ai-loading` shows initially with text "Analyzing page...", updates text as each section loads ("Matching against your graph...", "Finding relationships...", "Generating summary..."), hides when all complete. Per-section spinners are simpler — just show/hide the section container. (5) In sidebar.css: add styles for all new elements — AI section container, confidence badges (4 colors), indicator badges (4 colors), suggestion cards with action buttons, summary panel, unavailable message, section loading text, research gap alert cards.
  - Verify: `node --check extension/sidebar/sidebar.js` passes. Grep confirms all 5 rendering functions exist. HTML has `#ai-insights` div. CSS has rules for badges, indicators, suggestions, summary.
  - Done when: Sidebar shows AI Insights section with progressive loading. All section renderers produce correct DOM structure. Unavailable message shows when LLM not configured.

- [x] **T03: Wire Accept and Dismiss actions for suggestions** `est:45m`
  - Why: Accept and Dismiss are the primary user actions on AI suggestions — Accept creates graph objects/edges, Dismiss persists per-URL filtering. This task completes the interaction loop.
  - Files: `extension/sidebar/sidebar.js`, `extension/background/service-worker.js`
  - Do: (1) In sidebar.js: wire the Accept button click handler in `_renderSuggestionsSection()` — sends `{type: 'acceptSuggestion', suggestion: {type, label, target_iri, target_label, reason}, pageUrl: _currentTabUrl, pageTitle: _currentTabTitle}` to service worker. Shows loading state on button ("Accepting..."), disables it, on success shows green toast "✓ Linked to [target_label]", on error shows red toast with detail. (2) Wire the Dismiss button click handler — sends `{type: 'dismissSuggestion', url: _currentTabUrl, suggestionIri: suggestion.target_iri}`. On success, removes the card from DOM with a fade-out animation, shows brief "Dismissed" toast. (3) On sidebar init (in `_initAIInsights`), before rendering suggestions, send `{type: 'getDismissedSuggestions', url: _currentTabUrl}` and filter dismissed IRIs from the suggestions list. (4) Add CSS for button states (loading, disabled) and card fade-out animation. (5) Verify the service worker `acceptSuggestion` handler maps suggestion types correctly: for "link" type, create just an `edge.create` with `schema:url` predicate from the suggestion's `target_iri` to the page URL. For "evidence", create a `res:Evidence` object then `edge.create` with `res:supports`. For "supports"/"contradicts", create an `edge.create` with `res:supports`/`res:refutes`.
  - Verify: `node --check extension/sidebar/sidebar.js` and `node --check extension/background/service-worker.js` pass. Grep confirms `acceptSuggestion` and `dismissSuggestion` message sends in sidebar.js. Grep confirms `dismissed_` key pattern in service-worker.js chrome.storage.local usage.
  - Done when: Accept button sends correct message per suggestion type and shows success/error toast. Dismiss button persists to chrome.storage.local and removes card from UI. Dismissed suggestions filtered on next sidebar load.

- [x] **T04: Add SemPKMClient AI methods and Node.js unit tests** `est:45m`
  - Why: The SemPKMClient is the public API surface for the extension. Adding the 5 AI methods maintains API consistency and enables testability. The service worker can't use these (ES module limitation), but they're the correct interface for future use and Node.js unit testing.
  - Files: `extension/shared/api-client.js`, `extension/tests/test-ai-client.js`
  - Do: (1) Add 5 new methods to `SemPKMClient`: `getLLMStatus()` → `GET /api/llm/status`, `detectClaims({content, url, title})` → `POST /api/ai/detect-claims`, `matchClaims({claims})` → `POST /api/ai/match-claims`, `suggestRelationships({url, title, claims})` → `POST /api/ai/suggest-relationships`, `summarizePage({content, graph_context})` → `POST /api/ai/summarize`. Each follows the existing `_request()` pattern. (2) Write `extension/tests/test-ai-client.js` following the pattern from `test-context-utils.js` — use Node.js built-in `node:test` and `node:assert`. Mock `fetch` globally to verify request URLs, headers, and bodies. Test each method: correct URL path, correct HTTP method, correct body serialization, error handling (non-200 status throws SemPKMError with status and detail). Test `getLLMStatus` returns the parsed JSON directly. Test `detectClaims` sends content/url/title in body. Test `matchClaims` sends claims array. Test `suggestRelationships` sends url/title/claims. Test `summarizePage` sends content and graph_context.
  - Verify: `node --check extension/shared/api-client.js` passes. `node extension/tests/test-ai-client.js` — all tests pass (expect ~15-20 assertions).
  - Done when: All 5 methods on SemPKMClient match the backend Pydantic schemas. Node.js tests prove correct request construction and error handling.

## Files Likely Touched

- `extension/background/service-worker.js` — 5 new message handlers, AI pipeline, page content extraction, accept/dismiss logic
- `extension/sidebar/sidebar.js` — AI Insights init, progressive loading listener, 5 section renderers, accept/dismiss button handlers
- `extension/sidebar/sidebar.html` — new `#ai-insights` container with inner section divs
- `extension/sidebar/sidebar.css` — confidence badges, indicator badges, suggestion cards, summary panel, unavailable message, loading states
- `extension/shared/api-client.js` — 5 new AI methods on SemPKMClient
- `extension/tests/test-ai-client.js` — new Node.js unit tests for AI client methods
