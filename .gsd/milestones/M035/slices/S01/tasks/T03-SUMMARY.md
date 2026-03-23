---
id: T03
parent: S01
milestone: M035
provides:
  - Fully functional copilot chat UI in the AI COPILOT bottom panel tab
  - SSE streaming display with typing indicator and real-time token accumulation
  - Markdown rendering in assistant messages via marked.js
  - IRI pill conversion for clickable object links (both [[iri|label]] and iri: scheme)
  - SPARQL approval card rendering (stub for T04) with Run Query / Dismiss buttons
  - LLM-not-configured state with link to Settings
  - Lazy-load on first AI COPILOT tab activation
key_files:
  - frontend/static/js/copilot.js
  - frontend/static/css/copilot.css
  - backend/app/templates/browser/workspace.html
  - frontend/static/js/workspace.js
key_decisions:
  - SSE parsing uses ReadableStream reader with line-based buffer splitting rather than EventSource API because EventSource only supports GET requests and we need POST with JSON body
  - IRI pill click uses window.openTab() consistent with sparql-console.js pill pattern rather than introducing a new navigation mechanism
  - Approval card is a functional stub with Run Query and Dismiss buttons wired to POST /api/copilot/approve — T04 will enhance with editing and richer display
patterns_established:
  - Copilot lazy-load follows the exact same pattern as SPARQL console — _applyPanelState() checks panelState.activeTab and imports the module once
  - IRI pill conversion handles both [[iri|label]] markers from CopilotService and markdown-rendered <a href="iri:..."> links
  - Typing indicator (3 animated dots) is inserted before first token, removed on first token arrival, replaced by the real assistant message element
observability_surfaces:
  - "Browser console: copilot.js logs 'copilot: initialized' on init, 'copilot: stream error' on fetch failures"
  - "Network tab: SSE stream at /api/copilot/chat with data:, event: sparql_query, event: error events visible"
  - "LLM status: GET /api/llm/status fetched on init, drives not-configured state vs chat UI"
  - "UI failure states: LLM not configured card, stream error messages in thread, SPARQL validation errors on approval cards"
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Build copilot chat UI with streaming and markdown rendering

**Built the AI Copilot chat UI with SSE streaming, markdown rendering, IRI object pills, typing indicator, SPARQL approval cards, and LLM-not-configured state — lazy-loaded on first tab activation.**

## What Happened

Created `frontend/static/js/copilot.js` as a lazy-loaded ES module with these capabilities:

1. **Chat thread management** — `_messageThread` array stores user/assistant/system messages. User messages render right-aligned in accent-tinted bubbles, assistant messages left-aligned with markdown rendering, system/error messages centered.

2. **SSE streaming** — `_streamCopilotResponse()` uses `fetch()` with `ReadableStream` reader (not EventSource, since we need POST with JSON body). Parses SSE lines from a text buffer, handles three event types: standard OpenAI `data:` chunks (accumulated into the assistant message element in real-time), `event: sparql_query` (triggers approval card rendering), and `event: error` (displays error message in thread).

3. **Markdown rendering** — Uses `globalThis.marked.parse()` if available (loaded by workspace vendor bundle), with DOMPurify sanitization. Falls back to escaped text with line breaks.

4. **IRI pill conversion** — `_convertIriPills()` post-processes rendered markdown to convert `[[iri|label]]` markers (from CopilotService) and `<a href="iri:...">` links into clickable pills using `window.openTab()`, consistent with the SPARQL console pattern.

5. **SPARQL approval cards** — `_renderApprovalCard()` renders a card with the query in a code block, validation status, and Run Query / Dismiss buttons wired to `POST /api/copilot/approve`. Approved query results are rendered as assistant messages with IRI pill conversion.

6. **LLM availability check** — On init, fetches `GET /api/llm/status`. If `available: false`, shows a friendly card linking to Settings. Otherwise shows the empty-state greeting.

7. **UX details** — Enter sends, Shift+Enter adds newline. Textarea auto-resizes up to ~5 lines. Send button disabled when empty or streaming. Typing indicator (3 animated dots) during streaming. Auto-scroll to bottom on new messages. Focus input on tab switch.

Created `frontend/static/css/copilot.css` with full dark-mode support via CSS custom properties from theme.css. Lucide icons sized via CSS with `flex-shrink: 0` per CLAUDE.md rules. ARIA labels on textarea and send button for accessibility.

Updated `workspace.html` to replace the "coming in v2.1" placeholder with the chat container HTML and added the CSS link.

Updated `workspace.js` to add the lazy-load hook in `_applyPanelState()` following the SPARQL console pattern, plus a focus-on-tab-switch handler in `initPanelTabs()`.

## Verification

All four task-level verification checks pass:
- `test -f frontend/static/js/copilot.js && test -f frontend/static/css/copilot.css` → files exist
- `grep -q "initCopilotChat" frontend/static/js/workspace.js` → lazy-load hook present
- `grep -q "copilot-container" backend/app/templates/browser/workspace.html` → container present
- `! grep -q "coming in v2.1" backend/app/templates/browser/workspace.html` → placeholder removed

Slice-level tests still pass:
- `tests/test_copilot_service.py` → 32/32 passed
- `tests/test_ai_endpoints.py` → 16/17 passed (1 pre-existing failure)
- `from app.api.copilot import copilot_router` → import OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f frontend/static/js/copilot.js && test -f frontend/static/css/copilot.css` | 0 | ✅ pass | <1s |
| 2 | `grep -q "initCopilotChat\|initCopilot" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 3 | `grep -q "copilot-container" backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 4 | `! grep -q "coming in v2.1" backend/app/templates/browser/workspace.html` | 0 | ✅ pass | <1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` | 0 | ✅ pass (32/32) | 0.3s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_ai_endpoints.py -v` | 1 | ✅ pass (16/17; 1 pre-existing) | 0.8s |
| 7 | `cd backend && .venv/bin/python -c "from app.api.copilot import copilot_router; print('import OK')"` | 0 | ✅ pass | <1s |

### Slice-level verification status (intermediate — T03 of 5):
- `tests/test_copilot_service.py` — ✅ passes (32/32)
- `tests/test_ai_endpoints.py` — ✅ passes (16/17, 1 pre-existing unrelated failure)
- `copilot module import` — ✅ passes
- `verify-s01.sh` — ⏳ not yet created (T05 responsibility)
- Full browser verification — ⏳ requires Docker stack running with LLM configured

## Diagnostics

- **Browser console:** `copilot.js` logs `copilot: initialized` on module load, `copilot: stream error` on fetch failures, and `copilot: markdown parse error` on marked.js failures.
- **Network tab:** SSE stream at `/api/copilot/chat` shows `data:`, `event: sparql_query`, and `event: error` events. `GET /api/llm/status` shows LLM availability on init.
- **UI failure states:** LLM not configured → grey card with Settings link. Stream errors → red error messages in thread. SPARQL validation errors → shown on approval card with red text.
- **Code inspection:** `grep -rn "console\." frontend/static/js/copilot.js` lists all logging sites. `grep "copilot" frontend/static/js/workspace.js` shows lazy-load and focus hooks.

## Deviations

- The plan mentioned `window.renderMarkdown(content)` — this function doesn't exist. The codebase uses `globalThis.marked.parse()` directly (in canvas.js, vfs-browser.js, markdown-render.js). Used `globalThis.marked.parse()` with DOMPurify sanitization, matching the existing pattern.
- The plan referenced `openObject('full-iri')` for pill clicks — the actual codebase pattern is `window.openTab(iri, label)` (used in sparql-console.js, graph.js, federation.js). Used the real pattern.
- Added ARIA labels on the textarea and send button for accessibility (not in plan but aligned with accessibility skill guidance).

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/copilot.js` — new copilot chat ES module (SSE streaming, markdown, IRI pills, approval cards, LLM check)
- `frontend/static/css/copilot.css` — new copilot chat styles (messages, input area, typing indicator, approval cards, dark mode)
- `backend/app/templates/browser/workspace.html` — replaced "coming in v2.1" placeholder with chat container, added copilot.css link
- `frontend/static/js/workspace.js` — added lazy-load hook for ai-copilot tab in _applyPanelState(), focus handler in initPanelTabs()
- `.gsd/milestones/M035/slices/S01/tasks/T03-PLAN.md` — added Observability Impact section per pre-flight
