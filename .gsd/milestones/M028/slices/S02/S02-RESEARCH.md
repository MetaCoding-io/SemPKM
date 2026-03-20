# S02: Extension sidebar AI Insights UI — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S02 adds an "AI Insights" collapsible section to the existing sidebar (`sidebar.js`, 556 lines) that progressively loads AI results from the four S01 backend endpoints: detect-claims → match-claims → suggest-relationships → summarize. The existing sidebar architecture provides strong foundations — `_renderGroup()` for collapsible sections, `_renderCard()` for result cards, `showToast()` for feedback, and the evidence capture flow as a complex action reference. The service worker (`service-worker.js`, 502 lines) already handles message-based communication between sidebar and background and direct `fetch()` calls with Bearer auth to the backend API.

The work divides into four natural tasks: (1) add `SemPKMClient` API methods + service worker message handlers for AI operations, (2) add the page content extraction pipeline to the service worker (the sidebar can't call endpoints directly — it must go through the service worker for tab access), (3) build the AI Insights rendering section in `sidebar.js` with progressive loading, and (4) wire Accept/Dismiss actions.

This is a medium-complexity slice — known technology (vanilla JS, chrome APIs, DOM rendering), known patterns (sidebar rendering, service worker messaging, two-step create), with the main complexity in progressive loading state management and the accept/dismiss action logic.

## Recommendation

Build the API client + service worker plumbing first (new methods on `SemPKMClient`, new message handlers in `service-worker.js`), then the sidebar rendering (`sidebar.js` + `sidebar.html` + `sidebar.css`), then the accept/dismiss actions. The progressive loading approach is straightforward: the sidebar sends a single `getAIInsights` message to the service worker, which makes 5 sequential API calls (status → detect-claims → match-claims → suggest-relationships → summarize) and sends intermediate `aiInsightsProgress` messages back to the sidebar as each section completes.

**Key design decision per D264:** Sequential fetch calls with incremental DOM rendering, no SSE. The service worker makes individual fetch calls and posts progress messages back to the sidebar.

## Implementation Landscape

### Key Files

- `extension/shared/api-client.js` (209 lines) — `SemPKMClient` with `_request()` helper. Needs 5 new methods: `getLLMStatus()`, `detectClaims()`, `matchClaims()`, `suggestRelationships()`, `summarizePage()`. Uses ES module exports (`export class SemPKMClient`).
- `extension/background/service-worker.js` (502 lines) — Message handler hub. Uses `importScripts()` (classic script, not ES module). Has `_getApiConfig()` for reading settings, `_queryContext()` for direct fetch with Bearer auth. Needs new message handlers: `getAIInsights` (triggers full pipeline), `acceptSuggestion` (creates object+edge), `dismissSuggestion` (stores in chrome.storage.local). **Cannot import api-client.js** (ES module) — must use direct `fetch()` calls like existing `_queryContext()` and `addEvidence` handlers.
- `extension/sidebar/sidebar.js` (556 lines) — IIFE with `_showState()`, `_renderGroup()`, `_renderCard()`, `showToast()`, `renderResults()`, `fetchResults()`, `init()`. Loads `context-utils.js` via `<script>` tag. Needs: `_renderAIInsights()` section orchestrator, individual section renderers (`_renderClaimsSection()`, `_renderMatchesSection()`, `_renderSuggestionsSection()`, `_renderSummarySection()`), LLM unavailable message, dismiss persistence.
- `extension/sidebar/sidebar.html` — Static HTML with `<div id="results">` and `<div id="evidence-prompt">`. Needs new `<div id="ai-insights">` section (initially hidden) placed after `#results`.
- `extension/sidebar/sidebar.css` — Dark theme CSS. Needs new rules for AI Insights section: collapsible header, claim cards with confidence badges, match cards with indicator badges, suggestion cards with accept/dismiss buttons, summary panel, loading spinners per section, LLM-unconfigured message.
- `extension/shared/storage.js` (ES module) — `getSettings()`, `saveSettings()`, `getClient()`. Not directly usable from service worker (ES module restriction), but the service worker has its own inline `_getApiConfig()`.

### Build Order

1. **T01 — Service worker AI pipeline + page content extraction.** Add new message handlers in `service-worker.js`:
   - `getAIInsights`: extracts page content via `chrome.scripting.executeScript()` (reusing the pattern from the `addEvidence` handler), calls `GET /api/llm/status` first for feature gating, then sequentially calls detect-claims → match-claims → suggest-relationships → summarize. After each call completes, sends `chrome.runtime.sendMessage({type: 'aiInsightsProgress', section: 'claims', data: ...})` to the sidebar. Stores complete results in a per-URL AI cache (separate from the context cache).
   - `acceptSuggestion`: creates object + edge via the existing two-step fetch pattern (exactly like the `addEvidence` handler but with configurable type/properties).
   - `dismissSuggestion`: stores dismissed suggestion IRIs per URL in `chrome.storage.local`.
   - `getDismissedSuggestions`: retrieves dismissed IRIs for the current URL.
   - Also adds `getPageContent` handler for extracting page text via `chrome.scripting.executeScript` on the active tab (returns `document.body.innerText`).
   - **Why first:** Everything downstream (sidebar rendering, accept/dismiss) depends on these message handlers.

2. **T02 — Sidebar AI Insights rendering with progressive loading.** Add the AI Insights UI to `sidebar.js`, `sidebar.html`, and `sidebar.css`:
   - New `<div id="ai-insights" hidden>` in sidebar.html after `#results`, with inner containers for each section: `#ai-claims`, `#ai-matches`, `#ai-suggestions`, `#ai-summary`, plus a `#ai-loading` spinner and `#ai-unavailable` message.
   - In sidebar.js: new `_initAIInsights()` called from `init()` after context results load. It sends `getAIInsights` message and listens for `aiInsightsProgress` updates. Each progress message renders its section immediately.
   - Section renderers follow the existing `_renderGroup()` pattern — collapsible headers with count badges, cards inside.
   - Claims section: each claim as a card with confidence badge (color-coded: established=green, likely=blue, possible=amber, speculative=gray) and type badge.
   - Matches section: nested under claims — each claim shows its matched objects with indicator badges (contradicts=red, corroborates=green, contested=amber, related=gray).
   - Suggestions section: each suggestion as a card with Accept and Dismiss buttons.
   - Summary section: rendered markdown text in a styled container.
   - Research gaps: rendered as alert-style cards below matches.
   - LLM unavailable: shows "AI features require LLM configuration" message with link to settings.
   - Per-section loading spinners that disappear as data arrives.
   - CSS: new rules for AI section, confidence badges, indicator badges, accept/dismiss buttons, summary panel, section spinners.
   - **Why second:** Rendering is the bulk of the user-visible work and depends on T01's message pipeline.

3. **T03 — Accept/Dismiss actions.** Wire the suggestion buttons:
   - Accept: sends `acceptSuggestion` message to service worker → service worker creates object (via `/api/commands` with `object.create`) and edge (via `edge.create`) using the same two-step pattern as the existing `addEvidence` handler. The suggestion's `type` and `target_iri` determine the command params. Shows toast on success/failure.
   - Dismiss: sends `dismissSuggestion` message → stores IRI in `chrome.storage.local` keyed by URL. On next load, dismissed IRIs are filtered from the suggestions list. Shows brief "Dismissed" toast.
   - On sidebar init, fetch dismissed suggestions for current URL and filter them before rendering.
   - **Why third:** Actions depend on both the message handlers (T01) and the rendered buttons (T02).

4. **T04 — api-client.js new methods + Node.js tests.** Add the 5 new methods to `SemPKMClient` class and write Node.js unit tests:
   - `getLLMStatus()` → `GET /api/llm/status`
   - `detectClaims({content, url, title})` → `POST /api/ai/detect-claims`
   - `matchClaims({claims})` → `POST /api/ai/match-claims`
   - `suggestRelationships({url, title, claims})` → `POST /api/ai/suggest-relationships`
   - `summarizePage({content, graph_context})` → `POST /api/ai/summarize`
   - These methods aren't used by the service worker directly (ES module limitation) but provide the public API for future use and testability.
   - Node.js unit tests for the new methods using the same pattern as `extension/tests/test-context-utils.js`.
   - **Why last:** The service worker uses direct fetch (not the client), so this doesn't block other tasks. Testing and API surface completeness.

### Verification Approach

- **T01:** Send `getAIInsights` message from a test page and verify the service worker returns structured responses. Test with LLM unconfigured to verify graceful degradation (status check should return `{available: false}`).
- **T02:** Open sidebar on a test page, visually verify AI Insights section appears with progressive loading. Verify LLM-unavailable message when backend returns 503.
- **T03:** Click Accept on a suggestion, verify toast and object creation via the backend. Click Dismiss, reload sidebar, verify suggestion is hidden.
- **T04:** `node --check` on api-client.js for syntax. Node.js test runner for new method contracts.
- **Overall:** All existing extension functionality (context results, evidence capture, link-to-page) must still work — no regressions.

## Constraints

- **Service worker cannot import ES modules** — `service-worker.js` uses `importScripts()` (classic script). The `SemPKMClient` class in `api-client.js` uses `export class` (ES module). All API calls in the service worker must use direct `fetch()` with inline auth headers, matching the existing `_queryContext()` and `addEvidence` patterns.
- **Chrome MV3 CSP** — No `eval()`, no inline scripts. All JS must be in separate files loaded via `<script>` tags.
- **Page content extraction needs `chrome.scripting.executeScript`** — The sidebar HTML runs in the extension context, not the page context. To get `document.body.innerText` from the current tab, must route through the service worker which has scripting permissions.
- **Side panel width 250–400px** — All AI Insights UI must work within this narrow width. Collapsible sections are essential to avoid scroll overflow.
- **Dismiss persistence must survive service worker restarts** — Use `chrome.storage.local` (persistent) not service worker memory.

## Common Pitfalls

- **Service worker lifetime** — The service worker can be killed and restarted by Chrome at any time. The AI results cache should be in-memory (acceptable loss), but dismiss state must be in `chrome.storage.local` (persistent). The `contextCache` LRU pattern works for AI cache too.
- **`chrome.runtime.sendMessage` in sidebar requires `return true`** — The service worker message handler must return `true` for async `sendResponse`. The existing handlers demonstrate this pattern correctly.
- **Progressive loading race condition** — If the user navigates to a new page while AI calls are in-flight, stale results for the old URL could render. Guard with a "generation ID" that increments on each `getAIInsights` call and is checked before rendering each progress update.
- **`chrome.scripting.executeScript` may fail** — Content script injection fails on chrome:// pages, extension pages, and sites with strict CSP. The `addEvidence` handler already demonstrates the error handling pattern (`chrome.runtime.lastError` check). The `getAIInsights` handler must degrade gracefully when page content extraction fails.
- **Accept suggestion object type varies** — The `suggest-relationships` response has `type` field with values "link", "evidence", "supports", "contradicts". The accept action must map these to the correct `object.create` command type and `edge.create` predicate. For "link" type, create a `schema:url` edge. For "evidence", create a `res:Evidence` object and edge. For "supports"/"contradicts", create a `res:supports`/`res:refutes` edge.

## Open Risks

- **Page content may be large** — `document.body.innerText` on some pages can be 100KB+. The backend truncates to 4000 chars, but sending huge payloads from the service worker could cause message serialization issues. Truncate to ~8000 chars in the service worker before sending to the API.
- **Progressive loading UX timing** — If the LLM call (detect-claims) takes 5+ seconds, the AI Insights section may feel "stuck" with just a spinner. Need clear loading state per section with contextual text ("Analyzing claims...", "Matching against your graph...", "Finding relationships...", "Generating summary...").
