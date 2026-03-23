---
estimated_steps: 4
estimated_files: 4
skills_used:
  - frontend-design
  - accessibility
---

# T04: Implement SPARQL approval flow with self-correction

**Slice:** S01 — Copilot Chat with SPARQL Generation
**Milestone:** M035

## Description

Implement the SPARQL query approval flow — the key trust/safety feature of the copilot. When the LLM generates a SPARQL query, it's shown to the user in an approval card with Approve/Edit/Reject buttons. On approval, the query executes and results stream back as formatted prose. On failure, the self-correction loop feeds the error back to the LLM for up to 2 retries, showing each attempt in the chat.

## Steps

1. **Extend `backend/app/api/copilot.py`** SSE stream handling:
   - In the streaming response, after the full LLM response is received, check if it contains a ```sparql code fence. If so, extract the SPARQL query text.
   - Call `CopilotService.validate_query()` on the extracted query.
   - Emit a final SSE event: `event: sparql_detected\ndata: {"query": "<sparql>", "valid": true/false, "validation_error": "msg or null"}`.
   - The streaming content continues to render (the LLM's natural language explanation around the query), and the approval card appears after the message.

2. **Extend `POST /api/copilot/approve`** in `backend/app/api/copilot.py`:
   - On `action: "approve"`: call `CopilotService.execute_query(query)`. If success, call `CopilotService.format_results(results, db)` and return `{"status": "success", "results_markdown": "..."}`. If SPARQL execution fails, return `{"status": "error", "error": "msg"}`.
   - On `action: "edit"`: validate the `edited_query` via `CopilotService.validate_query()`. If valid, execute and format. If invalid, return the validation error.
   - On `action: "reject"`: return `{"status": "rejected"}`.
   - On `action: "retry"`: implement self-correction — call `CopilotService.build_retry_prompt(original_query, error_message)`, send to LLM (non-streaming), extract new SPARQL, validate, return the new query for another approval round. Track retry count (max 2 retries, 3 total attempts). After 3 failures, return `{"status": "max_retries", "error": "..."}`.

3. **Implement approval card UI in `frontend/static/js/copilot.js`**:
   - `_renderApprovalCard(data)`: called when `sparql_detected` SSE event is received. Creates a card element inserted after the assistant message containing:
     - SPARQL query in a `<pre><code>` block with basic syntax highlighting (highlight SELECT, WHERE, GRAPH, FILTER, PREFIX keywords)
     - Validation status: green checkmark if valid, yellow warning if invalid with error text
     - Three buttons: **Approve** (green, Lucide `check` icon), **Edit** (blue, Lucide `pencil` icon), **Reject** (red/muted, Lucide `x` icon)
   - On **Approve** click: POST to `/api/copilot/approve` with `{query, action: "approve"}`. Show a loading spinner. On success, render the results markdown as a new assistant message in the thread. On error, show the error and offer **Retry** button.
   - On **Edit** click: replace the `<pre>` block with a `<textarea>` pre-filled with the query. Show **Run Edited Query** and **Cancel** buttons. On Run, POST with `{query, action: "edit", edited_query}`.
   - On **Reject** click: POST with `{query, action: "reject"}`. Gray out the card and show "Query cancelled".
   - On **Retry** (after error): POST with `{query, action: "retry", error}`. Show "Retrying... (attempt 2/3)" message. On success, render new approval card with corrected query. After max retries, show "Unable to generate a valid query. Try rephrasing your question."

4. **Add approval card styles to `frontend/static/css/copilot.css`**:
   - `.copilot-approval-card`: bordered card (1px border, 8px radius, surface-elevated background), margin within the message thread
   - `.copilot-approval-query`: monospace pre block with subtle background, overflow-x auto
   - `.copilot-approval-actions`: flex row with gap, button group
   - `.copilot-approval-btn`: small button with icon + text, follows `.panel-btn` pattern but slightly larger
   - `.copilot-approval-btn-approve`: green accent
   - `.copilot-approval-btn-edit`: blue accent
   - `.copilot-approval-btn-reject`: muted/red
   - `.copilot-approval-status`: validation status indicator (green/yellow icon + text)
   - `.copilot-approval-loading`: spinner overlay during execution
   - `.copilot-approval-result`: formatted results area below the card
   - `.copilot-retry-msg`: system message for retry attempts
   - Dark mode: all via CSS custom properties

## Must-Haves

- [ ] SPARQL detected in streamed response triggers approval card
- [ ] Approve button executes query and shows formatted results with IRI pill links
- [ ] Edit button allows inline query editing before execution
- [ ] Reject button cancels the query
- [ ] Self-correction: retry on execution failure, up to 2 retries, with status messages
- [ ] Validation result shown on approval card (valid/invalid with error text)
- [ ] Loading state during query execution
- [ ] Max retries reached shows helpful error message

## Verification

- `grep -q "sparql_detected\|approval" frontend/static/js/copilot.js` — approval flow code in frontend
- `grep -q "approve\|retry" backend/app/api/copilot.py` — approval endpoint handles all actions
- `grep -q "copilot-approval" frontend/static/css/copilot.css` — approval card styles exist

## Observability Impact

- **New log events:** `copilot.approve.retry` (attempt number, original query length, error), `copilot.approve.max_retries` (final error). These extend the existing `copilot.approve.*` family from T02.
- **Inspection:** Retry attempts are visible in the chat thread as system messages with attempt counters ("Retrying... attempt 2/3"). The approval card shows validation status inline. Browser DevTools Network tab shows each POST to `/api/copilot/approve` with the action field.
- **Failure visibility:** Validation errors displayed on the approval card with yellow warning icon. Execution errors trigger a Retry button with the error message. After 3 failed attempts, a clear "max retries" message replaces the retry option.
- **Redaction:** No sensitive data in approval flow — queries are user-visible by design.

## Inputs

- `frontend/static/js/copilot.js` — chat UI from T03 (with approval stub)
- `frontend/static/css/copilot.css` — base chat styles from T03
- `backend/app/api/copilot.py` — copilot endpoints from T02
- `backend/app/services/copilot.py` — CopilotService from T01

## Expected Output

- `frontend/static/js/copilot.js` — modified with full approval card rendering and interaction
- `frontend/static/css/copilot.css` — modified with approval card styles
- `backend/app/api/copilot.py` — modified with extended approve endpoint (edit, retry, self-correction)
- `backend/app/services/copilot.py` — potentially modified if retry logic adjustments needed
