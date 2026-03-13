---
id: T03
parent: S06
milestone: M003
provides:
  - E2E test suite for threaded comments covering CMT-01 and CMT-02 requirements
key_files:
  - e2e/tests/21-comments/comments.spec.ts
key_decisions:
  - Cleanup uses direct SPARQL UPDATE to triplestore (bypassing EventStore) for hard-delete of test comments, since the app only supports soft-delete
  - SEMPKM namespace is urn:sempkm: (not urn:sempkm:ontology:) — must use correct prefix in any direct SPARQL operations
patterns_established:
  - Comment test cleanup via docker compose exec + SPARQL UPDATE to RDF4J /statements endpoint with file-based payload to avoid shell escaping
  - Cleanup verification query after SPARQL DELETE to ensure triplestore state is clean before test proceeds
observability_surfaces:
  - Playwright test results in e2e/test-results/ with failure screenshots and traces
duration: 1 session
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: E2E test coverage for comments

**Created 3 Playwright E2E tests proving CMT-01 (threaded comments) and CMT-02 (author attribution + timestamps) against the full Docker Compose stack.**

## What Happened

Built `e2e/tests/21-comments/comments.spec.ts` with 3 test scenarios:

1. **Empty state → post comment → verify display**: Confirms empty state message "No comments yet" appears, posts a comment, verifies the comment body renders with author display name (not "Unknown") and relative timestamp ("just now"), and shows "1 comment" badge.

2. **Reply creates threaded display**: Posts a root comment, clicks Reply to reveal inline reply form, submits a reply, verifies the reply is nested inside `.comment-thread-line` with indentation (`margin-left > 0`), confirms both author names are present, then posts a second top-level comment and verifies 2 root items and 3 total count.

3. **Soft-delete preserves thread structure**: Posts a parent comment, replies to it, then deletes the parent via the delete button (accepting the `hx-confirm` dialog). Verifies parent body shows "[deleted]", has `.comment-deleted` CSS class, author shows "Unknown", reply/delete buttons are hidden on deleted comment, reply is still fully intact with its original body and author, and total count remains "2 comments".

Key challenge was test cleanup: the app only supports soft-delete (replacing body with "[deleted]"), so leftover comments from prior runs couldn't be removed through the app API. Solved by sending SPARQL UPDATE directly to the RDF4J triplestore container to hard-delete all comment triples for the test object.

## Verification

- `npx playwright test e2e/tests/21-comments/ --project=chromium` — 3 passed (7.5s)
- `backend/.venv/bin/pytest backend/tests/test_comments.py -v` — 30 passed (slice unit tests)
- Tests are deterministic across consecutive runs (rate-limit permitting — 3 magic-link calls per run, within the 5/min limit for standalone execution)

## Diagnostics

- Run `npx playwright test e2e/tests/21-comments/ --headed` to watch tests execute visually
- Check `e2e/test-results/` for failure screenshots, traces, and error context on failure
- If tests fail with "Magic link request did not return a token", wait 60 seconds for rate limit reset

## Deviations

- **Cleanup approach**: Plan didn't specify cleanup strategy. Used direct SPARQL UPDATE to triplestore rather than soft-delete via API, since soft-deleted comments remain visible and pollute subsequent test runs. This is test-infrastructure-only, no production code changes.

## Known Issues

- Auth rate limit (5 magic-link requests/minute) can cause failures when tests are re-run rapidly in quick succession. This is a known infrastructure constraint that affects all E2E tests, not specific to comments.

## Files Created/Modified

- `e2e/tests/21-comments/comments.spec.ts` — Complete E2E test file with 3 scenarios covering CMT-01 and CMT-02
