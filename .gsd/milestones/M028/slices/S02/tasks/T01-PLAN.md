---
estimated_steps: 7
estimated_files: 1
---

# T01: Service worker AI pipeline and page content extraction

**Slice:** S02 — Extension sidebar AI Insights UI
**Milestone:** M028

## Description

Add 5 new message handlers to `extension/background/service-worker.js` that form the backbone of the AI Insights feature. The service worker is the only context that can both access tab content (via `chrome.scripting.executeScript`) and make authenticated API calls (via `fetch` with Bearer token). The sidebar communicates exclusively through `chrome.runtime.sendMessage` — it cannot call APIs directly.

The primary handler is `getAIInsights`, which orchestrates the full AI pipeline: extract page content → check LLM status → detect claims → match claims → suggest relationships → summarize. It sends incremental `aiInsightsProgress` messages back to the sidebar as each step completes, enabling the progressive loading UX.

Supporting handlers provide accept/dismiss actions and dismissed-state persistence.

**Key constraint:** The service worker uses classic `importScripts()` — it CANNOT import ES modules. All API calls must use direct `fetch()` with inline `Authorization: Bearer` headers, matching the existing `_queryContext()` and `addEvidence` patterns in the file.

**Key pattern reference:** The existing `addEvidence` handler (starting around line 290 in current file) demonstrates the two-step object+edge creation via `POST /api/commands`. The `acceptSuggestion` handler follows this same pattern but maps different suggestion types to different command params.

## Steps

1. **Add an `_aiGenerationId` counter** at the top of the service worker (alongside `_debounceTimers` and `contextCache`). Also add an `aiCache` using the same `SemPKMContextUtils.LRUCache(50)` pattern for caching AI results per URL.

2. **Add `getPageContent` message handler.** When received, query the active tab via `chrome.tabs.query({active: true, currentWindow: true})`, then call `chrome.scripting.executeScript({target: {tabId}, func: () => document.body.innerText})`. Return the text (truncated to 8000 chars) via `sendResponse({content, url, title})`. Handle `chrome.runtime.lastError` for pages where script injection fails (chrome:// pages, extension pages). Return `{error: 'Cannot access page content'}` on failure. Must `return true` for async.

3. **Add `getAIInsights` message handler** — the core pipeline orchestrator. Steps within this handler:
   - Increment `_aiGenerationId` and capture current value as `genId`
   - Get active tab URL and title
   - Check `aiCache` — if hit, send all sections at once from cache and return
   - Extract page content via `chrome.scripting.executeScript` (inline, not via getPageContent message). Truncate `document.body.innerText` to 8000 chars. On failure, `sendResponse({error: 'Cannot access page content'})` and return
   - Call `GET /api/llm/status` with Bearer auth. If `available: false`, send `chrome.runtime.sendMessage({type: 'aiInsightsProgress', section: 'unavailable', generationId: genId})` and stop. Send `sendResponse({started: true, generationId: genId})`
   - Call `POST /api/ai/detect-claims` with `{content, url, title}`. On success, send `{type: 'aiInsightsProgress', section: 'claims', data: response.claims, generationId: genId}`. On error, send progress with empty claims and continue.
   - Call `POST /api/ai/match-claims` with `{claims: response.claims}`. On success, send `{type: 'aiInsightsProgress', section: 'matches', data: {matches: response.matches, research_gaps: response.research_gaps}, generationId: genId}`. On error, send empty matches.
   - Call `POST /api/ai/suggest-relationships` with `{url, title, claims}`. On success, send `{type: 'aiInsightsProgress', section: 'suggestions', data: response.suggestions, generationId: genId}`. On error, send empty suggestions.
   - Call `POST /api/ai/summarize` with `{content, graph_context}` where `graph_context` is built from match results (each matched object's `{iri, label, type_label, snippet}`). On success, send `{type: 'aiInsightsProgress', section: 'summary', data: response.summary, generationId: genId}`. On error, skip summary.
   - Store complete results in `aiCache` keyed by URL
   - Each API call uses the same fetch pattern: `fetch(config.instanceUrl + path, {method, headers: {Authorization: Bearer, Content-Type: application/json}, body: JSON.stringify(payload)})`
   - Each step wrapped in try/catch — errors for one step don't block subsequent steps

4. **Add `acceptSuggestion` message handler.** Receives `{suggestion: {type, label, target_iri, target_label, reason}, pageUrl, pageTitle}`. Maps suggestion type to API commands:
   - `"link"` → single `edge.create`: `{source: suggestion.target_iri, target: pageUrl, predicate: 'schema:url'}`
   - `"evidence"` → two-step: `object.create` with `type: 'urn:sempkm:model:research:Evidence'`, properties `{description: suggestion.label, source: pageUrl, evidenceType: 'supporting', created: today}`, then `edge.create` with `source: newEvidenceIri, target: suggestion.target_iri, predicate: 'urn:sempkm:model:research:supports'}`
   - `"supports"` → single `edge.create`: `{source: suggestion.target_iri, target: pageUrl, predicate: 'urn:sempkm:model:research:supports'}`
   - `"contradicts"` → single `edge.create`: `{source: suggestion.target_iri, target: pageUrl, predicate: 'urn:sempkm:model:research:refutes'}`
   - On success: `sendResponse({success: true})`. On failure: `sendResponse({error: detail})`.
   - Use the same error handling pattern as the existing `addEvidence` handler.

5. **Add `dismissSuggestion` message handler.** Receives `{url, suggestionIri}`. Reads existing dismissed array from `chrome.storage.local` key `dismissed_${url}`, appends `suggestionIri` if not already present, writes back. `sendResponse({success: true})`.

6. **Add `getDismissedSuggestions` message handler.** Receives `{url}`. Reads `chrome.storage.local` key `dismissed_${url}`, returns `{dismissed: [...iris]}` (empty array if key doesn't exist).

7. **Verify syntax and grep for all handlers.** Run `node --check` on the modified file. Grep for each message type to confirm handler presence.

## Must-Haves

- [ ] `getAIInsights` handler calls all 5 API endpoints sequentially and sends `aiInsightsProgress` messages after each
- [ ] `getAIInsights` checks `GET /api/llm/status` first and sends `unavailable` section if LLM not configured
- [ ] `getAIInsights` extracts page content via `chrome.scripting.executeScript`, truncated to 8000 chars
- [ ] `getAIInsights` includes `generationId` in every progress message for stale-update protection
- [ ] Per-step error isolation — failure in one API call doesn't block subsequent calls
- [ ] `acceptSuggestion` maps all 4 suggestion types (link, evidence, supports, contradicts) to correct API commands
- [ ] `dismissSuggestion` persists to `chrome.storage.local` with per-URL keys
- [ ] `getDismissedSuggestions` retrieves dismissed IRIs for a given URL
- [ ] All handlers use `return true` for async `sendResponse`
- [ ] `node --check extension/background/service-worker.js` passes

## Verification

- `node --check extension/background/service-worker.js` — zero errors
- `grep -c 'getAIInsights\|acceptSuggestion\|dismissSuggestion\|getDismissedSuggestions\|getPageContent' extension/background/service-worker.js` — returns 5 or more (one per handler minimum)
- `grep 'aiInsightsProgress' extension/background/service-worker.js` — confirms progress messages are sent
- `grep 'generationId' extension/background/service-worker.js` — confirms generation ID is used
- `grep 'chrome.storage.local' extension/background/service-worker.js` — confirms persistent dismiss storage

## Inputs

- `extension/background/service-worker.js` (502 lines) — existing file with `_getApiConfig()`, `_queryContext()`, `addEvidence` handler, `linkToPage` handler, `contextCache` LRU, `importScripts('../shared/context-utils.js')`
- S01 API contract: `GET /api/llm/status` returns `{available: bool, provider: string|null}`. `POST /api/ai/detect-claims` accepts `{content, url, title}` returns `{claims: [{text, confidence, type}], parse_error}`. `POST /api/ai/match-claims` accepts `{claims: [{text, confidence, type}]}` returns `{matches: [{claim_text, matched_objects: [{iri, label, type_iri, type_label, match_type, indicator, confidence, fts_score}]}], research_gaps: [{iri, label, question_text, status}]}`. `POST /api/ai/suggest-relationships` accepts `{url, title, claims}` returns `{suggestions: [{type, label, target_iri, target_label, reason}]}`. `POST /api/ai/summarize` accepts `{content, graph_context: [{iri, label, type, snippet}]}` returns `{summary: string}`.
- `POST /api/commands` accepts `{command: 'object.create'|'edge.create', params: {...}}` — existing pattern from `addEvidence` handler

## Observability Impact

- **New console signals:** `[SemPKM] AI Insights: ...` log lines for each pipeline step (status check, content extraction, detect-claims, match-claims, suggest-relationships, summarize). `console.error('[SemPKM] AI ...')` on every failure path.
- **Inspection surface:** `chrome.storage.local` keys `dismissed_${url}` store per-URL dismissed suggestion IRIs — inspectable via DevTools Application tab.
- **Failure visibility:** Each pipeline step catches errors independently; partial results flow to sidebar even when individual steps fail. Errors include API status codes and detail text.
- **Future agent inspection:** Run `grep '\[SemPKM\] AI' extension/background/service-worker.js` to see all instrumented log lines. Check `_aiGenerationId` counter to verify stale-update protection is wired.
- **Redaction:** API key never logged; page content truncated to 8000 chars before transmission.

## Expected Output

- `extension/background/service-worker.js` — expanded with 5 new message handlers (~250 lines added): `getAIInsights`, `getPageContent`, `acceptSuggestion`, `dismissSuggestion`, `getDismissedSuggestions`. Plus `_aiGenerationId` counter and `aiCache` LRU instance.
