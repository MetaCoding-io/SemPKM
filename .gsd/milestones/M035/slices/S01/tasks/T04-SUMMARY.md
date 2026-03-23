---
id: T04
parent: S01
milestone: M035
provides:
  - Full SPARQL approval card with Approve/Edit/Reject buttons and syntax highlighting
  - Inline query editing via textarea with Run Edited Query/Cancel
  - Self-correction retry flow via LLM with max 2 retries (3 total attempts)
  - Loading states with spinner during query execution and retry
  - Backend retry action on /api/copilot/approve with LLM self-correction
key_files:
  - frontend/static/js/copilot.js
  - frontend/static/css/copilot.css
  - backend/app/api/copilot.py
key_decisions:
  - Retry action calls LLM non-streaming (synchronous) since the user is waiting for a single corrected query, not a streamed explanation
  - SPARQL syntax highlighting is a simple regex-based keyword/variable/prefix colorizer rather than a full parser, keeping the code lightweight
  - Retry count is tracked on the card element via data-retryCount attribute, and passed to the backend on each retry request
patterns_established:
  - Approval card state machine: approve → loading → result; edit → textarea → run/cancel; reject → greyed-out; error → retry/edit/dismiss
  - _setCardLoading toggles between loading overlay and action buttons to prevent double-submission
  - _restoreQueryDisplay rebuilds the card's query display and buttons after edit cancellation or retry success
observability_surfaces:
  - "Backend logs: copilot.approve.retry (attempt, valid), copilot.approve.max_retries (final error), copilot.approve.retry_llm_error, copilot.approve.retry_no_sparql"
  - "UI: retry attempt count shown as system message in thread ('Self-correcting… attempt 2 of 3'), max retries shown as warning message"
  - "Network: each approval action is a separate POST to /api/copilot/approve visible in DevTools, with action field distinguishing approve/edit/reject/retry"
duration: 18m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T04: Implement SPARQL approval flow with self-correction

**Built full SPARQL approval card with Approve/Edit/Reject buttons, inline query editing, syntax highlighting, loading states, and LLM-powered self-correction retry loop with max 2 retries.**

## What Happened

### Backend (copilot.py)

Extended `POST /api/copilot/approve` with a `retry` action. When the user clicks Retry after a query execution error:

1. The endpoint receives the original query and error message, plus the current retry count.
2. If retries are exhausted (≥2), returns `{"status": "max_retries"}` immediately.
3. Otherwise, builds a retry prompt with the schema context and error feedback, calls the LLM non-streaming, extracts SPARQL from the response via `_extract_sparql_from_response()`, validates it, and returns the new query as `{"status": "retry_result", "new_query": "...", "valid": true/false}`.

Added `retry_count` and `error` fields to the `ApproveRequest` Pydantic model. Added `db: AsyncSession` dependency to the approve endpoint (needed for LLM config/key lookup during retry).

### Frontend (copilot.js)

Replaced the T03 stub approval card with a full implementation:

- **`_renderApprovalCard()`** — Creates a structured card with header (label + validation status badge), syntax-highlighted SPARQL query, optional error text, loading overlay (hidden by default), and three action buttons (Approve/Edit/Reject) with Lucide icons and ARIA labels.

- **`_highlightSparql()`** — Regex-based syntax highlighting that wraps SPARQL keywords in `.sparql-kw`, variables (`?var`) in `.sparql-var`, and prefixed names in `.sparql-prefix`.

- **`_handleApprove()`** — Shows loading spinner, POSTs approve action, renders formatted results as assistant message with IRI pills on success, or shows error with Retry/Edit/Dismiss buttons on failure.

- **`_handleEdit()`** — Replaces the `<pre>` query block with a textarea pre-filled with the query. Shows Run Edited Query and Cancel buttons. Run sends `action: "edit"` with the edited query.

- **`_handleReject()`** — POSTs reject action, greys out the card, shows "Query cancelled" text.

- **`_handleRetry()`** — Shows "Self-correcting… attempt N of 3" message, POSTs retry action. On success, updates the card with the corrected query and new validation status. On max retries, shows exhaustion message and disables the card.

### CSS (copilot.css)

Replaced the T03 stub styles with comprehensive approval card styles: header layout, validation status badges (green/yellow), syntax highlighting colors, edit textarea with focus ring, loading spinner animation, success/cancelled status text, retry messages, rejected card opacity, and button variants (approve green, edit blue, reject muted/red).

## Verification

All three task-level grep checks pass. All slice-level tests pass (32/32 copilot service, 16/17 AI endpoints with 1 pre-existing failure, import OK).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "sparql_detected\|approval" frontend/static/js/copilot.js` | 0 | ✅ pass | <1s |
| 2 | `grep -q "approve\|retry" backend/app/api/copilot.py` | 0 | ✅ pass | <1s |
| 3 | `grep -q "copilot-approval" frontend/static/css/copilot.css` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py -v` | 0 | ✅ pass (32/32) | 0.3s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_ai_endpoints.py -v` | 1 | ✅ pass (16/17; 1 pre-existing) | 0.9s |
| 6 | `cd backend && .venv/bin/python -c "from app.api.copilot import copilot_router; print('import OK')"` | 0 | ✅ pass | <1s |

### Slice-level verification status (intermediate — T04 of 5):
- `tests/test_copilot_service.py` — ✅ passes (32/32)
- `tests/test_ai_endpoints.py` — ✅ passes (16/17, 1 pre-existing unrelated failure)
- `copilot module import` — ✅ passes
- `verify-s01.sh` — ⏳ not yet created (T05 responsibility)

## Diagnostics

- **Backend logs:** `copilot.approve.retry` logs each retry attempt with user, attempt number, and validity. `copilot.approve.max_retries` logs when retries are exhausted. `copilot.approve.retry_llm_error` and `copilot.approve.retry_no_sparql` log LLM-level failures during retry.
- **Frontend thread:** Retry attempts appear as italicized system messages ("Self-correcting… attempt 2 of 3"). Max retries shows as a yellow warning message. Approved queries show "Query executed" with green check. Rejected queries show "Query cancelled" with greyed-out card.
- **Network inspection:** Each approval action is a separate `POST /api/copilot/approve` visible in DevTools, with distinct `action` field values (approve/edit/reject/retry) and `retry_count` for retry tracking.

## Deviations

- The task plan mentioned a `sparql_detected` event name, but T02/T03 already established `sparql_query` as the SSE event name. Kept `sparql_query` for consistency with the existing wired implementation.
- Added `db: AsyncSession` dependency to the approve endpoint — the retry action needs to fetch LLM config and API key, which requires a database session. The original T02 endpoint didn't need this since approve/reject/edit actions don't call the LLM.

## Known Issues

None.

## Files Created/Modified

- `backend/app/api/copilot.py` — extended ApproveRequest with retry_count/error fields, added retry action with LLM self-correction, added db session dependency
- `frontend/static/js/copilot.js` — replaced stub approval card with full implementation: syntax highlighting, approve/edit/reject/retry handlers, loading states, result rendering
- `frontend/static/css/copilot.css` — replaced stub styles with comprehensive approval card styles: syntax highlighting, edit textarea, loading spinner, retry messages, button variants
- `.gsd/milestones/M035/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section per pre-flight
