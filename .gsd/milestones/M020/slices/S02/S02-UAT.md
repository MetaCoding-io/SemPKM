# S02: Pull Sync + Field Mapping + Recurrence Conversion — UAT

**Milestone:** M020
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All code is pure functions and async mocks — no running services needed. The 177 unit tests exercise every code path, mapping table entry, and edge case. Runtime integration is verified in S04's E2E tests.

## Preconditions

- Backend venv activated: `cd backend && source .venv/bin/activate`
- All three test files exist in `backend/tests/`
- All three service modules exist in `apps/outlook-calendar/services/`

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py tests/test_outlook_sync_engine.py tests/test_outlook_person_matcher.py --tb=short -q
```
Expected: `177 passed, 1 skipped` in <1s. The 1 skip is the markdownify HTML→Markdown test (not installed in test venv).

## Test Cases

### 1. All 18 recurrence pattern→RRULE combinations produce valid RRULEs

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py -k "TestConvertRecurrenceToRrule" -v`
2. **Expected:** 18+ tests pass. Each test name identifies the pattern×range combination (e.g., `test_daily_end_date`, `test_relative_monthly_numbered`, `test_absolute_yearly_no_end`). Every test asserts a specific RRULE string.

### 2. All showAs values map correctly

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py -k "test_show_as" -v`
2. **Expected:** 6 tests pass — one for each showAs value (free, tentative, busy, oof, workingElsewhere, unknown). Each asserts the correct `bpkm:showAs` property value.

### 3. All sensitivity→visibility values map correctly

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py -k "test_sensitivity" -v`
2. **Expected:** 4 tests pass — normal (omits visibility), personal (omits visibility), private (→ "private"), confidential (→ "confidential").

### 4. All responseStatus values map correctly (both directions)

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py -k "response_status" -v`
2. **Expected:** Forward: 6 tests (none→needs-action, organizer→accepted, tentativelyAccepted→tentative, accepted→accepted, declined→declined, notResponded→needs-action). Reverse: 4 tests for build_event_patch mapping.

### 5. Body extraction handles HTML, plain text, and empty

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py -k "TestExtractBody" -v`
2. **Expected:** Tests for plain text pass-through, empty body returns empty string, HTML with strip_html_tags fallback. The markdownify test may skip (1 skip expected).

### 6. Delta query sync stores and uses delta links

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestPullSyncDeltaLink" -v`
2. **Expected:** 4 tests pass — delta_link_stored (new link saved to state), incremental_sync_uses_delta_link (stored link passed to client), expired_delta_410_retries_full_sync (410 triggers full re-sync with fresh link), expired_delta_clears_stored_link (stale link removed from state).

### 7. @removed events in delta response are skipped

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestPullSyncRemovedEvents" -v`
2. **Expected:** 3 tests pass — removed events are not created or updated, only non-removed events in the same batch are processed.

### 8. Per-event error isolation preserves successful events

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestPullSyncErrorIsolation" -v`
2. **Expected:** 3 tests pass — one bad event doesn't block others, errors include event_id, last_pull_result state key contains structured error detail.

### 9. Push sync RSVP push-back works end-to-end

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestPushSync" -v`
2. **Expected:** 10 tests pass — not-connected skip, pull-only skip, no changes, successful RSVP push (patch_event called with correct args), lastSyncedAt updated, error isolation per event, last_push_result stored, all-errors status, skip without response status, missing calendar name errors.

### 10. Person matcher resolves attendees via SPARQL

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_person_matcher.py -v`
2. **Expected:** 14 tests pass — email match returns IRI, no match creates person, cache hit skips query, case-insensitive cache key, None/empty email returns None, display name used for slug, email local part used when no display name, slugify tests, email local part extraction.

### 11. Full build_event_properties integration

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py -k "TestBuildEventProperties" -v`
2. **Expected:** Tests pass verifying that a complete Outlook event JSON produces correct bpkm:* property dict with full IRI keys, timezone, dates, location (nested displayName), conference URL, showAs, sensitivity→visibility, categories→tags, reminder gating.

## Edge Cases

### Recurrence with relativeMonthly/relativeYearly index mapping

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_field_mapper.py -k "relative" -v`
2. **Expected:** Tests verify position-prefixed BYDAY values like `2TU` (second Tuesday), `-1FR` (last Friday). The RELATIVE_INDEX_MAP (first→1, second→2, third→3, fourth→4, last→-1) is exercised.

### Self-organizer not added as attendee

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "test_self_organizer_not_matched" -v`
2. **Expected:** When organizer email matches `microsoft_email` in state, no organizer edge is created (prevents self-referential attendee).

### Loop prevention — recently-pushed events skipped on pull

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_outlook_sync_engine.py -k "TestLoopPrevention" -v`
2. **Expected:** 3 tests — event with lastModifiedDateTime ≤ lastSyncedAt is skipped, event with lastModifiedDateTime > lastSyncedAt is processed, event with no lastSyncedAt is always processed.

## Failure Signals

- Any test failure in the full suite (expect exactly 177 passed, 1 skipped)
- markdownify skip count > 1 (would indicate additional import failures)
- Import errors on `field_mapper`, `sync_engine`, or `person_matcher` modules (indicates broken module structure)
- Tests taking >5s (indicates unexpected I/O or infinite loops — all tests should complete in <1s)

## Requirements Proved By This UAT

- Recurrence pattern→RRULE conversion for all 18 combinations — proven by 18+ dedicated tests
- Field mapping completeness for ~25 Outlook properties — proven by exhaustive mapping table tests
- Delta query incremental sync with 410 recovery — proven by delta link tests
- Per-event error isolation — proven by error isolation tests with structured result inspection
- RSVP push-back via Graph API PATCH — proven by push sync tests
- HTML→Markdown body conversion — proven by extract_body tests (markdownify path partially — strip_html_tags fallback fully)

## Not Proven By This UAT

- Runtime Docker integration (field mapper + sync engine running against real/mock Graph API)
- Full E2E lifecycle (install → OAuth → sync → verify → RSVP push) — deferred to S04
- markdownify HTML→Markdown quality with complex HTML — depends on library being installed
- Settings UI controls (sync direction, poll interval, Sync Now) — deferred to S03

## Notes for Tester

- The 1 skipped test (`test_extract_body_html_with_markdownify`) is expected — markdownify is not installed in the test venv. It works at runtime when the app's requirements.txt is installed.
- Test isolation relies on `_patch_outlook_client` context manager in sync engine tests. If you see `OutlookClient` import errors, check that the module loading order in conftest hasn't changed.
- All async tests use `pytest-asyncio` with mock SDK clients — no network calls or Docker required.
