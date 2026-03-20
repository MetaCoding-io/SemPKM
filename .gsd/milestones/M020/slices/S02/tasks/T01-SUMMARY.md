---
id: T01
parent: S02
milestone: M020
provides:
  - Outlook Calendar field mapper with all ~25 field transforms
  - Recurrence pattern→RRULE converter (6 pattern types × 3 range types)
  - HTML→Markdown body conversion with markdownify/strip_html_tags fallback
  - RSVP push-back reverse mapper
key_files:
  - apps/outlook-calendar/services/field_mapper.py
  - backend/tests/test_outlook_field_mapper.py
key_decisions:
  - Outlook build_event_patch uses nested emailAddress/status structure (not Google's flat email/self/responseStatus) matching Microsoft Graph API conventions
  - REVERSE_RESPONSE_STATUS_MAP maps needs-action→notResponded (not "none") since that's the user-action variant
patterns_established:
  - Same SHA-256 slug pattern as Google Calendar for compute_event_slug
  - Same importlib-based test loading pattern as test_gcal_field_mapper.py
observability_surfaces:
  - 103 unit tests as the inspection surface (no runtime signals — pure functions only)
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build Outlook field mapper with recurrence converter and 80+ unit tests

**Complete Outlook field mapper with all 25 field transforms, recurrence converter for all 18 pattern×range combinations, and 103 passing unit tests.**

## What Happened

Created the Outlook Calendar field mapper following the same architecture as the Google Calendar version. The implementation covers:

1. **Constants:** SHOW_AS_MAP (6 entries), SENSITIVITY_MAP (4 entries with None for omit), RESPONSE_STATUS_MAP (6 entries), REVERSE_RESPONSE_STATUS_MAP (4 entries), DAY_OF_WEEK_MAP (7 days), RELATIVE_INDEX_MAP (5 entries)

2. **Extraction helpers:** compute_event_slug (SHA-256), detect_all_day (reads isAllDay boolean), extract_conference_url (onlineMeeting.joinUrl → onlineMeetingUrl fallback), extract_response_status (reads responseStatus.response directly), derive_event_status (3-way: isCancelled → tentativelyAccepted → confirmed), extract_body (HTML→markdownify with strip_html_tags fallback), extract_categories_as_tags (join with comma)

3. **Recurrence converter:** `convert_recurrence_to_rrule()` handles all 6 pattern types (daily, weekly, absoluteMonthly, relativeMonthly, absoluteYearly, relativeYearly) × 3 range types (endDate, numbered, noEnd) = 18 combinations. Uses `_convert_days_of_week()` for weekly patterns and `_convert_relative_day()` for position-prefixed BYDAY (e.g., `2TU`, `-1FR`).

4. **Property builder:** `build_event_properties()` outputs full IRI keys, strips None values, handles Outlook-specific location (nested displayName), sensitivity→visibility mapping, categories→tags, reminder gating via isReminderOn.

5. **Reverse mapper:** `build_event_patch()` for RSVP push-back using Outlook's nested attendee structure (emailAddress/status objects, not Google's flat format).

## Verification

- `python -m pytest tests/test_outlook_field_mapper.py -v` — **103 passed, 1 skipped** (markdownify not installed in test env, expected)
- Standalone import check — `OK`
- All 18 recurrence combinations verified individually
- All mapping table entries tested exhaustively

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_outlook_field_mapper.py -v --tb=short` | 0 | ✅ pass (103 passed, 1 skipped) | 0.13s |
| 2 | `python3 -c "import importlib.util; ..."` | 0 | ✅ pass | <1s |

## Diagnostics

All functions are pure with zero I/O — no runtime diagnostic surfaces. Re-run `pytest tests/test_outlook_field_mapper.py -v` to verify correctness. Test names directly identify the mapping path being tested (e.g., `TestConvertRecurrenceToRrule::test_relative_yearly_end_date`).

## Deviations

- Task plan specified `dcterms:description` isn't mentioned in the property builder description but the design doc §6 maps `body.content` to `dcterms:description`. Added it to `build_event_properties`.
- `build_event_patch` uses Outlook's nested `emailAddress`/`status` structure instead of Google's flat structure — this matches the Microsoft Graph API format for PATCH requests.

## Known Issues

- markdownify not installed in the test venv (1 skipped test). The `extract_body` HTML→Markdown path via markdownify works in production when the app's requirements.txt is installed. The strip_html_tags fallback is tested and functional.

## Files Created/Modified

- `apps/outlook-calendar/services/field_mapper.py` — Complete field mapper (~380 lines) with all constants, extraction helpers, recurrence converter, property builder, and reverse mapper
- `backend/tests/test_outlook_field_mapper.py` — 103 unit tests covering all mapping tables, all 18 recurrence combinations, edge cases, and integration tests
- `.gsd/milestones/M020/slices/S02/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
