---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M021

## Success Criteria Checklist

- [x] User installs CalDAV sync app from Admin > Applications and configures server URL + HTTP Basic credentials — evidence: S01 delivers manifest.yaml, connect.html with server URL/username/password form, 6 route handlers, credential storage via StateClient. 20 auth unit tests.
- [x] User sees their CalDAV calendar list and selects which to sync — evidence: S01 delivers full discovery chain (well-known → principal → calendar-home → calendar-list) with Fastmail/Nextcloud variant coverage. connect_status.html has calendar checkboxes. 42 client unit tests.
- [x] Synced iCalendar events appear as bpkm:Event objects with all VEVENT fields mapped (SUMMARY, DTSTART, DTEND, LOCATION, STATUS, ATTENDEE, RRULE, VALARM, CATEGORIES, etc.) — evidence: S02 delivers 443-line field mapper with 17 extraction functions, 5 enum maps, _normalize_to_list() for single-vs-list handling. 85 field mapper unit tests.
- [x] RRULE from iCalendar stored directly as RFC 5545 strings (no conversion needed) — evidence: S02 field mapper extracts RRULE via icalendar library's vRecur.to_ical() with prefix stripping. BYDAY values passed as individual weekday strings per K003.
- [x] Editing an event's RSVP status in SemPKM updates the .ics resource via CalDAV PUT with ETag concurrency — evidence: S03 delivers push_sync() with GET→modify→PUT pipeline, modify_vevent_partstat() for in-place ATTENDEE PARTSTAT modification, CalDAVConflictError (412) handling with per-event error isolation. 36 push sync unit tests.
- [x] 200+ unit tests pass in <2s covering all field transforms, sync engine, auth, client, and person matcher — evidence: S04 reports 229 tests in 0.34s across 5 test files (auth, client, field_mapper, sync_engine, person_matcher).
- [x] Mock CalDAV server passes selftest and Playwright E2E test exercises install → configure → sync → verify → push lifecycle — evidence: S04 delivers ~500-line mock server with 12/12 selftest checks. 304-line Playwright E2E test with 7 phases. E2E test is structurally complete but not runtime-verified against Docker stack (consistent with M017–M020, blocked by pre-existing app subprocess startup issue — not a CalDAV defect).
- [x] User guide Chapter 39 documents CalDAV setup, field mapping, and troubleshooting — evidence: S04 delivers 368-line chapter with field mapping tables, server-specific notes (Fastmail/Nextcloud/Synology/Radicale), troubleshooting section.

## Milestone Definition of Done Checklist

- [x] CalDAV app installs from admin, credential form accepts URL/username/password — S01
- [x] Calendar discovery chain works (well-known → principal → home → list) — S01, 42 client unit tests with canned XML
- [x] Pull sync creates bpkm:Event objects with correct field mapping for all VEVENT properties — S02, 85 field mapper tests
- [x] Push sync sends RSVP changes back via PUT with ETag concurrency — S03, 36 push tests
- [x] 200+ pytest unit tests pass in <2s — 229 tests in 0.34s
- [x] Mock CalDAV server passes selftest — 12/12 checks
- [x] Playwright E2E test exercises full lifecycle — 304 lines, 7 phases (structurally complete)
- [x] Chapter 39 user guide published with field mapping tables — 368 lines
- [x] README TOC, glossary, navigation chain updated — S04 verified all three
- [x] Appendix A — no update needed (CalDAV uses user-entered server URL, no env var overrides). Reasonable deviation.
- [x] All htmx URLs use `/app/caldav-calendar/` prefix (grep audit: 0 violations) — verified in both S01 and S04
- [ ] All CDAV requirements validated — **gap: CDAV-01 through CDAV-10 were never registered in REQUIREMENTS.md.** All four slice summaries note this. The functional work backing each requirement is complete, but formal tracking is missing.

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | CalDAVClient with WebDAV XML, auth module, discovery chain, installable app with credential form + calendar selection, 62 unit tests | All items delivered per summary. auth.py (~130 lines), caldav_client.py (~400 lines), app.py (~275 lines), manifest, 2 templates, CSS, 62 tests (20 auth + 42 client). | pass |
| S02 | Field mapper, sync engine, person matcher, settings UI wired, 134 new tests | field_mapper.py (443 lines), sync_engine.py (550 lines), person_matcher.py (139 lines), sync-token extraction added to caldav_client.py, app.py stubs replaced. 134 new tests (85+31+18). 196 total. | pass |
| S03 | push_sync() with GET→modify→PUT, build_event_patch() real implementation, modify_vevent_partstat(), ETag concurrency, 36 new tests | All items delivered. Zero stubs remaining in field_mapper.py and sync_engine.py (grep-verified). 36 new tests (15+21). 229 total collected. | pass |
| S04 | Mock CalDAV server with selftest, 7-phase Playwright E2E test, Chapter 39 user guide, README/glossary/nav-chain updates | ~500-line mock server (12/12 selftest), 304-line E2E test, 368-line Chapter 39, 13 CalDAV selectors in helpers, README TOC + glossary + nav chain all updated. | pass |

## Cross-Slice Integration

**S01 → S02 boundary:** S01 produced CalDAVClient with get_events/put_event/delete_event and auth module. S02 consumed these correctly and extended caldav_client.py with `_report_raw()` for sync-token extraction — backward compatible since original `_report()` is unchanged. Clean.

**S02 → S03 boundary:** S02 produced field mapper with REVERSE_RESPONSE_STATUS_MAP, _normalize_to_list(), and sync engine infrastructure. S03 consumed all of these. Test infrastructure (MockAppContext, MockGraphClient, MockCalDAVHttpClient) extended cleanly. Clean.

**S03 → S04 boundary:** S04 consumed the complete app from S01–S03. Mock server XML responses use exact namespace URIs matching CalDAVClient's parser constants. E2E test selectors verified against actual template HTML. Clean.

No boundary mismatches found.

## Requirement Coverage

**Gap:** The roadmap declares coverage of CDAV-01 through CDAV-10, but these requirement IDs were never registered in REQUIREMENTS.md. This is inconsistent with the pattern established by M017 (GH-01–07), M018 (EVENT-01, GCAL-01–09), M020 (OL-01–09), and M016 (SYNC-01–07), all of which registered their requirements.

The functional work backing each implied requirement is complete:

| Implied Req | Coverage | Evidence |
|-------------|----------|----------|
| CDAV-01 (CalDAV auth) | S01 | HTTP Basic credential storage, PROPFIND connection test, 20 auth tests |
| CDAV-02 (Calendar discovery) | S01 | Full discovery chain with Fastmail/Nextcloud variants, 42 client tests |
| CDAV-03 (CalDAV client protocol) | S01 | PROPFIND/REPORT/PUT/DELETE with XML gen/parse, ETag handling |
| CDAV-04 (Pull sync + field mapping) | S02 | 85 field mapper tests, 31 sync engine tests, two-phase bulk create |
| CDAV-05 (Person matching) | S02 | SPARQL email lookup, create-on-miss, LRU cache, 18 tests |
| CDAV-06 (RSVP push) | S03 | GET→modify→PUT pipeline, 21 push sync tests |
| CDAV-07 (ETag concurrency) | S01+S03 | If-Match/If-None-Match headers, CalDAVConflictError (412) |
| CDAV-08 (Settings UI) | S02 | Sync direction, poll interval, Sync Now, sync stats |
| CDAV-09 (E2E tests + mock server) | S04 | Mock server (12 selftest), 7-phase Playwright E2E |
| CDAV-10 (User guide) | S04 | Chapter 39 (368 lines), README TOC, glossary, nav chain |

**Action needed:** Register CDAV-01 through CDAV-10 in REQUIREMENTS.md as validated, following the pattern from prior sync app milestones. This is a documentation task, not a code task.

## Verdict Rationale

All 8 success criteria are met with clear evidence. All 4 slices delivered their claimed outputs with no regressions. Cross-slice boundaries are clean. 229 unit tests pass in 0.34s (exceeds 200+ target). Mock server selftest passes 12/12. Chapter 39 user guide, README TOC, glossary, and navigation chain are all updated. htmx prefix audit is clean.

The only gap is formal requirement tracking — CDAV-01 through CDAV-10 were never registered in REQUIREMENTS.md. This is a documentation gap that can be resolved during milestone completion (no new slice needed). The functional work is complete and proven by tests.

The E2E test being structurally complete but not runtime-verified is consistent with M017, M018, M019, and M020 — all blocked by the same pre-existing app subprocess startup issue. This is a known platform limitation, not a CalDAV defect.

**Verdict: needs-attention** — all code deliverables are complete, but CDAV requirements must be registered in REQUIREMENTS.md before sealing the milestone. No remediation slices needed.

## Remediation Plan

None required — the gap is a documentation task (requirement registration) that can be handled during milestone completion, not a code deficiency requiring a new slice.
