# S02: Pull Sync + Field Mapping + Recurrence Conversion — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

S02 adapts the M018 Google Calendar pull sync pattern (field_mapper.py + sync_engine.py + person_matcher.py) for Microsoft Graph API conventions. The three modules total ~1030 lines in M018 — Outlook's version will be similar in size but with a substantially different field_mapper.py due to: (1) the recurrence pattern→RRULE converter (the only genuinely new algorithm), (2) richer showAs/sensitivity/responseStatus enums with Outlook-specific derivation logic, (3) HTML→Markdown body conversion via `markdownify`, and (4) categories→tags mapping. The sync_engine.py and person_matcher.py are near-identical clones — the only structural difference is delta queries using `@odata.deltaLink` instead of Google's syncToken.

The bpkm:Event SHACL shape (basic-pkm v2.1.0, validated in M018/S01) already includes all Outlook-specific enum values: `showAs` has `out-of-office` and `working-elsewhere`, `visibility` has `confidential`. No model changes needed.

The recurrence converter is the highest-risk piece — 6 pattern types × 3 range types = 18 combinations, with the relativeMonthly/relativeYearly index→BYDAY mapping being the trickiest. The design doc (INTEGRATION-DOMAIN-MAPPING.md §6) provides complete mapping tables. This is a pure function with zero dependencies, so exhaustive unit testing is the safety net.

## Recommendation

Build in three tasks matching the natural seams:

1. **Field mapper (highest risk):** All ~25 field transforms + recurrence converter + HTML→Markdown body + categories→tags. Pure functions, no I/O, exhaustive unit tests. This is the core of S02 and should be proven first.
2. **Sync engine:** Clone M018's sync_engine.py, swap GCalClient→OutlookClient, adapt delta query handling (`@odata.deltaLink` instead of syncToken, error handling for expired delta tokens), wire up the new field mapper. Async tests with mock clients.
3. **Person matcher:** Near-identical clone of M018's person_matcher.py — same SPARQL lookup, same create-on-miss, same LRU cache. Only the import path changes.

The `markdownify` library needs to be added to `apps/outlook-calendar/requirements.txt`. It's a lightweight pure-Python library (no C extensions) that converts HTML to Markdown. Tests should mock it or test inline since it won't be in the backend's own venv — only in the app's venv at runtime. For unit tests, import it conditionally or use a simple `strip_html_tags` fallback.

## Implementation Landscape

### Key Files

**Create:**

- `apps/outlook-calendar/services/field_mapper.py` — All field transforms. Key differences from M018:
  - `SHOW_AS_MAP`: 6 values (`free`→`free`, `tentative`→`tentative`, `busy`→`busy`, `oof`→`out-of-office`, `workingElsewhere`→`working-elsewhere`, `unknown`→`busy`)
  - `SENSITIVITY_MAP`: `normal`→omit, `personal`→omit, `private`→`private`, `confidential`→`confidential`
  - `RESPONSE_STATUS_MAP`: 6 values (`none`→`needs-action`, `organizer`→`accepted`, `tentativelyAccepted`→`tentative`, `accepted`→`accepted`, `declined`→`declined`, `notResponded`→`needs-action`)
  - `REVERSE_RESPONSE_STATUS_MAP`: reverse of above (for push in S03)
  - `derive_event_status(event)`: implements derived status logic — `isCancelled=true`→`cancelled`, `responseStatus.response=tentativelyAccepted`→`tentative`, else `confirmed`
  - `convert_recurrence_to_rrule(recurrence)`: pure function converting Outlook's structured recurrence object to RFC 5545 RRULE string. Handles 6 pattern types × 3 range types. Day-of-week mapping: `{"monday": "MO", "tuesday": "TU", ...}`. Index mapping for relativeMonthly/relativeYearly: `{"first": 1, "second": 2, "third": 3, "fourth": 4, "last": -1}`. Range types: `endDate`→`UNTIL=<date>T000000Z`, `numbered`→`COUNT=<n>`, `noEnd`→omit
  - `extract_body(event)`: checks `body.contentType` — if `html`, converts via markdownify; if `text`, passes through. Falls back to `strip_html_tags()` if markdownify unavailable
  - `extract_conference_url(event)`: checks `onlineMeeting.joinUrl` then `onlineMeetingUrl` fallback
  - `extract_response_status(event)`: reads `responseStatus.response` directly (not from attendees list like Google)
  - `extract_categories_as_tags(event)`: returns `categories` array as comma-joined string or list for bpkm:tags
  - `detect_all_day(event)`: reads `isAllDay` boolean directly (Google uses start.date vs start.dateTime heuristic)
  - `compute_event_slug(calendar_id, event_id)`: same SHA-256 pattern as M018
  - `build_event_properties(event, calendar_name, sync_time)`: assembles all property mappings
  - `build_event_patch(event_props, microsoft_email)`: reverse RSVP mapping for push (S03 will use this)

- `apps/outlook-calendar/services/sync_engine.py` — Clone of M018 with these adaptations:
  - Import `OutlookClient` instead of `GCalClient`, `OutlookAPIError` instead of `GCalAPIError`
  - `pull_sync()`: uses `client.get_events_delta(calendar_id, delta_link)` which returns `(events, new_delta_link)`. Delta link stored via StateClient as `delta_link:{calendar_id}`. On expired delta token (likely 410 or specific error code), falls back to full sync by clearing the stored delta link
  - `_find_existing_event()`: same STRENDS pattern, `externalProvider = "outlook-calendar"`
  - Deleted events: check for `@removed` key in event dict (Outlook delta query convention)
  - `push_sync()`: same pattern as M018 — find changed events via SPARQL, reverse map, PATCH. Uses `OutlookClient.patch_event()`. (Actual push logic deferred to S03 but the skeleton/imports should be clean)
  - Two-phase bulk create: identical to M018 (phase 1: object.create, phase 2: discover IRIs → body.set + edge.create)

- `apps/outlook-calendar/services/person_matcher.py` — Near-identical clone of M018. Same SPARQL lookup (`foaf:mbox` UNION `crm:email`), same `_slugify`, same `_email_local_part`, same `PersonMatcher` class with LRU cache. Only the logger name changes to `"outlook.sync.person_matcher"`.

- `apps/outlook-calendar/requirements.txt` — Add `markdownify` dependency

**Test files (create):**

- `backend/tests/test_outlook_field_mapper.py` — Emphasis on recurrence conversion. Target: ~80+ tests covering:
  - `compute_event_slug`: deterministic, different inputs differ
  - `detect_all_day`: isAllDay=true vs false, missing field
  - `extract_conference_url`: onlineMeeting.joinUrl, onlineMeetingUrl fallback, neither
  - `extract_response_status`: all 6 response values + missing
  - `extract_body`: HTML body with markdownify, plain text body, empty/missing
  - `derive_event_status`: isCancelled=true, tentativelyAccepted, default confirmed
  - `extract_categories_as_tags`: array with items, empty array, missing
  - `convert_recurrence_to_rrule`: 18 combinations (6 pattern types × 3 range types) + edge cases (interval>1, multiple daysOfWeek, firstDayOfWeek, dayOfMonth, month, relativeMonthly index mapping, relativeYearly, missing/null recurrence)
  - `SHOW_AS_MAP`: all 6 values
  - `SENSITIVITY_MAP`: all 4 values including omit cases
  - `build_event_properties`: full event with all fields, minimal event, Outlook-specific fields
  - `build_event_patch`: RSVP reverse mapping (for S03 prep)

- `backend/tests/test_outlook_sync_engine.py` — Target: ~40 tests covering:
  - `_find_existing_event`: found, not found, SPARQL structure
  - `pull_sync`: not connected → skip, no calendars → skip, new events created, existing events updated, deleted events handled, loop prevention via lastSyncedAt, delta link storage/retrieval, expired delta link recovery (full re-sync), per-event error isolation, attendee/organizer edge creation
  - `_build_create_command` / `_build_update_commands`: command structure
  - `_submit_commands_batched`: batching at BATCH_SIZE boundary

- `backend/tests/test_outlook_person_matcher.py` — Target: ~12 tests (same as M018):
  - `_slugify`: various inputs
  - `_email_local_part`: standard cases
  - `PersonMatcher.match_or_create`: cache hit, SPARQL match, create new, None email

**Reference (read-only):**

- `apps/google-calendar/services/field_mapper.py` (258 lines) — clone source for property builder pattern
- `apps/google-calendar/services/sync_engine.py` (634 lines) — clone source for pull/push orchestration
- `apps/google-calendar/services/person_matcher.py` (139 lines) — clone source (near-identical)
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §6 — authoritative field mapping tables
- `models/basic-pkm/shapes/basic-pkm.jsonld` — confirms bpkm:Event enum values include Outlook-specific ones

### Build Order

1. **Field mapper first** — it's the highest-risk piece (recurrence converter is new algorithm) and has zero dependencies on network/async. Pure functions, immediate unit testability. Proves: all 25+ field transforms, all 18 recurrence combinations, HTML→Markdown, status derivation.

2. **Person matcher second** — near-identical clone, quick to build, needed by sync engine. Proves: email resolution works with Outlook-style email format.

3. **Sync engine last** — depends on both field_mapper and person_matcher. Wires everything together. Proves: delta query flow, two-phase bulk create, deleted event handling, loop prevention.

### Verification Approach

```bash
# Field mapper tests (pure functions — fast, no mocks needed for most)
cd backend && python -m pytest tests/test_outlook_field_mapper.py -v

# Person matcher tests
cd backend && python -m pytest tests/test_outlook_person_matcher.py -v

# Sync engine tests (async mocks)
cd backend && python -m pytest tests/test_outlook_sync_engine.py -v

# All Outlook tests together
cd backend && python -m pytest tests/test_outlook_*.py -v --tb=short

# Verify no import errors in app modules
python3 -c "
import importlib.util, sys
from pathlib import Path
base = Path('apps/outlook-calendar/services')
for f in ['field_mapper.py', 'sync_engine.py', 'person_matcher.py']:
    spec = importlib.util.spec_from_file_location(f.replace('.py',''), base / f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(f'{f}: OK')
"
```

Target: 130+ tests across the three test files (80+ field mapper, 40+ sync engine, 12+ person matcher).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| HTML→Markdown body conversion | `markdownify` Python library | Outlook `body.content` defaults to HTML. Lightweight, pure-Python, no C deps. Falls back to simple tag stripping if unavailable. |

## Constraints

- `markdownify` must be listed in `apps/outlook-calendar/requirements.txt` — the app manager installs it into the app's venv at install time. For unit tests that run in the backend's own venv, either install markdownify there too or use conditional import with fallback to `strip_html_tags()`
- Unit tests load app modules via `importlib.util.spec_from_file_location` — same pattern as M018's test files. Dependency loading order matters: field_mapper must be loaded before sync_engine (sync_engine imports from field_mapper)
- The sync engine bypasses SDK's `CommandClient` for bulk operations by posting directly to `/api/commands/bulk` — same pattern as M018 (D204 IRI prefix enforcement bypass)
- `OUTLOOK_API_URL` env var must be used in sync engine for mock server testability (already set up in S01's outlook_client.py)
- Outlook's `start.dateTime` format includes timezone offset but also has a separate `start.timeZone` field — the dateTime value should be used directly for `schema:startDate`, and the timeZone stored in `bpkm:timeZone`
- Outlook's `isAllDay` is an explicit boolean field (unlike Google where all-day is detected by the presence of `start.date` vs `start.dateTime`)
- Deleted events in delta responses have an `@removed` key — must be handled in sync engine to either skip or mark as cancelled

## Common Pitfalls

- **Outlook eventStatus is derived, not a direct field** — isCancelled + responseStatus.response must be combined. Don't look for a `status` field
- **Outlook body defaults to HTML** — must check `body.contentType` before processing. Plain text bodies pass through unchanged
- **Outlook sensitivity ≠ Google visibility** — `normal` and `personal` both map to omitting bpkm:visibility. `private` and `confidential` are distinct values preserved on bpkm:Event
- **Recurrence daysOfWeek uses lowercase full names** — `["monday", "wednesday"]` maps to RRULE `BYDAY=MO,WE`. Need a lookup dict
- **relativeMonthly/relativeYearly use `index` + `daysOfWeek`** — e.g. "second Tuesday" = `{index: "second", daysOfWeek: ["tuesday"]}`. Maps to RRULE `BYDAY=2TU`. The index values are: `first`→1, `second`→2, `third`→3, `fourth`→4, `last`→-1
- **Categories are a string array** — directly mappable to bpkm:tags. Must handle the case where categories is missing or empty list
- **MockResponse pattern** — per KNOWLEDGE.md pattern #2, use `data if data is not None else {}` not `data or {}` to avoid falsy empty-list bug
- **`@removed` key on deleted events** — delta queries include deleted events with `{"@removed": {"reason": "deleted"}}`. The sync engine must detect this and either skip the event or mark existing events as cancelled
- **Outlook conference URL path** — `onlineMeeting.joinUrl` (nested object) is primary, `onlineMeetingUrl` (flat string) is fallback. Different from Google's `conferenceData.entryPoints[type=video]`
- **markdownify in tests** — the backend test venv may not have markdownify installed. The field_mapper should use conditional import: `try: from markdownify import markdownify as md; except ImportError: md = None` with fallback to strip_html_tags. Tests can then test both paths

## Open Risks

- **Delta query behavior for recurring events** — unclear whether delta returns only series masters or also individual occurrences/exceptions. The sync engine should handle both (use `seriesMasterId` to detect exceptions). If delta returns expanded occurrences, filter by `type == "seriesMaster"` or process all with appropriate slug computation
- **Expired delta token error code** — Microsoft Graph may return 410 Gone or a specific error body when the delta token expires. The sync engine should catch both 410 and any error containing "syncStateNotFound" or similar, and fall back to full re-sync
- **markdownify output fidelity** — converting Outlook's HTML body (which can include Office-specific formatting) to Markdown may lose some formatting. Acceptable for v1 — body is supplementary to structured event data

## Sources

- Outlook field mapping tables: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §6
- Recurrence pattern→RRULE conversion: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §6 "Recurrence Handling"
- M018 Google Calendar field mapper: `apps/google-calendar/services/field_mapper.py`
- M018 Google Calendar sync engine: `apps/google-calendar/services/sync_engine.py`
- M018 Google Calendar person matcher: `apps/google-calendar/services/person_matcher.py`
- bpkm:Event SHACL shape: `models/basic-pkm/shapes/basic-pkm.jsonld` (confirms Outlook-specific enum values present)
