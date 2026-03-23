---
estimated_steps: 5
estimated_files: 5
skills_used:
  - frontend-design
  - make-interfaces-feel-better
  - accessibility
---

# T03: Build copilot chat UI with streaming and markdown rendering

**Slice:** S01 — Copilot Chat with SPARQL Generation
**Milestone:** M035

## Description

Replace the "AI Copilot — coming in v2.1" placeholder in the workspace bottom panel with a fully functional chat UI. This includes a message thread display (user and assistant messages), a text input with send button, SSE streaming display with typing indicator, markdown rendering in responses, and clickable IRI object pill links. The module is lazy-loaded on first tab activation (same pattern as the SPARQL console).

## Steps

1. **Create `frontend/static/js/copilot.js`** as a lazy-loaded ES module (same import pattern as `sparql-console.js`). Key exports: `initCopilotChat()`. Internal structure:
   - `_messageThread` array holding `{role: 'user'|'assistant'|'system', content: string, timestamp: Date}` objects
   - `_sendMessage(text)`: creates user message element, appends to thread, calls `_streamCopilotResponse(messages)`.
   - `_streamCopilotResponse(messages)`: opens `fetch()` with `POST /api/copilot/chat` and `{messages}` body, reads the SSE stream via `ReadableStream` reader, accumulates tokens into the assistant message element in real-time, handles `event: sparql_query` events by calling `_renderApprovalCard(data)` (T04 will flesh this out — create a stub here).
   - `_renderMessage(msg)`: creates a DOM element for a message. User messages: right-aligned bubble with plain text. Assistant messages: left-aligned with markdown rendering. Use `window.renderMarkdown(content)` if available (from `markdown-render.js`), otherwise innerHTML with basic escaping.
   - `_convertIriPills(html)`: post-processes rendered markdown to convert `[Label](iri:full-iri)` links into clickable object pills using the same pattern as the SPARQL console (`<a class="iri-pill" href="#" onclick="openObject('full-iri')">Label</a>`). Reference `backend/app/templates/browser/sparql_result_embed.html` for the pill HTML pattern.
   - `_showLlmNotConfigured()`: renders a friendly message with a link to Settings page when LLM is not available. Check via `fetch('/api/llm/status')` on init.

2. **Create `frontend/static/css/copilot.css`** with chat UI styles:
   - `.copilot-container`: full-height flex column (message thread + input area)
   - `.copilot-messages`: scrollable message thread, flex-grow: 1, overflow-y: auto
   - `.copilot-msg`: base message style with padding, margin, border-radius
   - `.copilot-msg-user`: right-aligned, accent background (`var(--color-accent)` at 15% opacity), rounded corners (12px, 12px top-left/right, 4px bottom-right, 12px bottom-left)
   - `.copilot-msg-assistant`: left-aligned, surface background, full-width
   - `.copilot-msg-system`: centered, muted text, italic
   - `.copilot-input-area`: flex row at bottom with textarea + send button, border-top
   - `.copilot-input`: auto-growing textarea (min 1 row, max 5 rows), same font as rest of UI
   - `.copilot-send-btn`: Lucide `send` icon button, accent color, disabled when empty
   - `.copilot-typing`: typing indicator (3 animated dots) shown during streaming
   - `.copilot-sparql-block`: syntax-highlighted SPARQL code block within messages
   - `.copilot-iri-pill`: clickable object pill (reuse `.iri-pill` styles from sparql results or define compatible ones)
   - Dark mode: all colors use CSS custom properties from `theme.css`
   - Follow Lucide icon rules from CLAUDE.md: size via CSS, `flex-shrink: 0`, `stroke: currentColor`

3. **Update `backend/app/templates/browser/workspace.html`** — replace the placeholder div at `#panel-ai-copilot` (lines ~183-187):
   ```html
   <div class="panel-pane" id="panel-ai-copilot">
     <div class="copilot-container" id="copilot-container">
       <div class="copilot-messages" id="copilot-messages"></div>
       <div class="copilot-input-area">
         <textarea class="copilot-input" id="copilot-input"
                   placeholder="Ask about your knowledge graph..."
                   rows="1"></textarea>
         <button class="copilot-send-btn" id="copilot-send-btn" title="Send message (Enter)">
           <i data-lucide="send-horizontal"></i>
         </button>
       </div>
     </div>
   </div>
   ```
   Add `<link rel="stylesheet" href="/css/copilot.css">` in the head block (after workspace CSS).

4. **Update `frontend/static/js/workspace.js`** — add lazy-load hook in `_applyPanelState()` for the ai-copilot tab, following the exact pattern of the sparql console lazy-load (line ~418):
   ```javascript
   if (panelState.open && panelState.activeTab === 'ai-copilot') {
     if (!window._copilotInit) {
       window._copilotInit = true;
       import('/js/copilot.js').then(function(mod) {
         mod.initCopilotChat();
       }).catch(function(err) {
         console.error('Failed to load copilot:', err);
         window._copilotInit = false;
       });
     }
   }
   ```
   Also add the same lazy-load trigger in `initPanelTabs()` click handler for the `ai-copilot` tab (same pattern as `event-log` lazy-load).

5. **Handle Enter key for send, Shift+Enter for newline** in copilot.js. Auto-resize textarea on input (adjust rows attribute up to max 5). Auto-scroll message thread to bottom on new messages. Focus the input when the copilot tab becomes active.

## Must-Haves

- [ ] `copilot.js` lazy-loaded on first AI COPILOT tab activation
- [ ] Chat messages render with user (right) and assistant (left) alignment
- [ ] SSE streaming displays tokens incrementally with typing indicator
- [ ] Markdown rendered in assistant messages
- [ ] IRI references converted to clickable object pills
- [ ] "LLM not configured" state shown when LLM unavailable
- [ ] Enter sends message, Shift+Enter adds newline
- [ ] Dark mode works correctly via CSS custom properties
- [ ] Lucide icons sized via CSS with `flex-shrink: 0` per CLAUDE.md rules

## Verification

- `test -f frontend/static/js/copilot.js && test -f frontend/static/css/copilot.css` — files exist
- `grep -q "initCopilotChat\|initCopilot" frontend/static/js/workspace.js` — lazy-load hook present
- `grep -q "copilot-container" backend/app/templates/browser/workspace.html` — placeholder replaced
- `! grep -q "coming in v2.1" backend/app/templates/browser/workspace.html` — old placeholder removed

## Inputs

- `backend/app/templates/browser/workspace.html` — existing workspace template with AI COPILOT placeholder at #panel-ai-copilot
- `frontend/static/js/workspace.js` — existing panel tab handler and lazy-load pattern
- `frontend/static/js/sparql-console.js` — reference for lazy-load ES module pattern
- `frontend/static/css/workspace.css` — existing panel styles (`.panel-pane`, `.panel-placeholder`, etc.)
- `frontend/static/css/theme.css` — CSS custom properties for dark mode
- `backend/app/api/copilot.py` — the SSE endpoint from T02

## Expected Output

- `frontend/static/js/copilot.js` — new copilot chat module
- `frontend/static/css/copilot.css` — new copilot styles
- `backend/app/templates/browser/workspace.html` — modified (placeholder replaced with chat container)
- `frontend/static/js/workspace.js` — modified (lazy-load hook added for ai-copilot tab)

## Observability Impact

- **Console logging:** `copilot.js` logs `copilot: initialized` on successful init and `copilot: stream error` on fetch failures — check browser DevTools console.
- **SSE stream inspection:** Open browser DevTools Network tab, filter by EventStream, and inspect the `/api/copilot/chat` SSE stream to see `data:`, `event: sparql_query`, and `event: error` events in real time.
- **LLM status check:** On init, the UI fetches `GET /api/llm/status` — a 200 with `{"available": false}` renders the "not configured" state; a 200 with `{"available": true}` shows the chat input. Network tab shows this request.
- **Failure states visible in UI:** LLM not configured → grey "not configured" card. Stream errors → red error messages in the chat thread. Typing indicator visible during streaming. SPARQL validation errors shown on approval cards.
- **Future agent inspection:** `grep -rn "copilot:" frontend/static/js/copilot.js` to see all console log sites. `grep -q "copilot-container" backend/app/templates/browser/workspace.html` to verify the chat container is present.
