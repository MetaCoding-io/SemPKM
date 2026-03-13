---
estimated_steps: 4
estimated_files: 1
---

# T03: E2E test coverage for comments

**Slice:** S06 — Threaded Object Comments
**Milestone:** M003

## Description

Create Playwright E2E tests proving CMT-01 (threaded collaborative comments) and CMT-02 (comment panel with author attribution and timestamps) requirements. Tests exercise the full stack against a running Docker Compose instance: post comments, reply to create threads, verify display, soft-delete, and check empty state.

## Steps

1. **Create test file and fixtures** — `e2e/tests/21-comments/comments.spec.ts`:
   - Import existing test helpers (login, object creation)
   - Setup: log in as a user, ensure at least one object exists (create via UI or API fixture if needed)
   - Navigate to workspace, select the test object

2. **Test: empty state and post first comment** —
   - Verify "Comments" section visible in right pane
   - Verify empty state message "No comments yet" (or similar)
   - Type a comment body in the textarea
   - Click Post/submit
   - Verify the comment appears with author display name and a timestamp
   - Verify the empty state message is gone

3. **Test: reply to comment and verify threading** —
   - Click "Reply" on the posted comment
   - Verify inline reply form appears
   - Type a reply body and submit
   - Verify the reply appears indented below the parent comment
   - Verify both comments show correct author names
   - Post another top-level comment — verify ordering (newest or oldest first, depending on implementation)

4. **Test: soft-delete a comment with replies** —
   - Delete the parent comment (the one with a reply)
   - Accept the confirmation dialog
   - Verify the parent comment body now shows "[deleted]"
   - Verify the reply is still visible and intact (thread structure preserved)
   - Verify the author name is removed from the deleted comment

## Must-Haves

- [ ] E2E test for empty state → post comment → verify display
- [ ] E2E test for reply → threaded indentation verified
- [ ] E2E test for soft-delete → "[deleted]" body, replies preserved
- [ ] Tests run against Docker Compose stack (full integration)
- [ ] Tests prove CMT-01 (threaded comments exist and work) and CMT-02 (author + timestamp visible)

## Verification

- `npx playwright test e2e/tests/21-comments/ --headed` — all tests pass
- Tests are deterministic (no flaky timing issues — use proper waitFor assertions)

## Observability Impact

- Signals added/changed: None (test-only, no production code)
- How a future agent inspects this: Run `npx playwright test e2e/tests/21-comments/ --headed` to watch tests execute; check `e2e/test-results/` for failure screenshots and traces
- Failure state exposed: Playwright test report shows which assertion failed with screenshot and DOM snapshot

## Inputs

- `backend/app/browser/comments.py` — T01's endpoints (must be functional)
- `backend/app/templates/browser/partials/comments_section.html` — T02's templates (must render correctly)
- `frontend/static/js/workspace.js` — T02's JS integration (comments section must load)
- `e2e/tests/20-favorites/` — reference for existing E2E test patterns in this project

## Expected Output

- `e2e/tests/21-comments/comments.spec.ts` — complete E2E test file with 3+ test scenarios covering CMT-01 and CMT-02
