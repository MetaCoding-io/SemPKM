---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M020

## Success Criteria Checklist

- [x] User installs "Outlook Calendar Sync" from Admin > Applications and connects via Microsoft OAuth 2.0 — evidence: S01 manifest.yaml validates against AppManifestSchema, 10 route handlers for OAuth lifecycle, 41 auth unit tests covering code exchange/refresh/rotation/buffer expiry
- [x] User selects calendars from their Microsoft 365 account and triggers sync — evidence: S01 calendar list with checkboxes (calendars.html, connect_status.html), selection save route, 24 client unit tests including pagination
- [x] Outlook events appear as bpkm:Event objects with correct times, timezone, attendees, location, conference URLs — evidence: S02 field_mapper.py with all ~25 field transforms from design doc §6, build_event_properties covers times/timezone/attendees/location/conferenceUrl, 103 field mapper tests
- [x] Outlook categories appear as bpkm:tags on synced events — evidence: S02 extract_categories_as_tags helper in field_mapper.py, covered by field mapper unit tests
- [x] showAs values (busy, free, tentative, out-of-office, working-elsewhere) preserved on events — evidence: S02 SHOW_AS_MAP with 6 entries in field_mapper.py, unit tested
- [x] sensitivity→visibility mapping works (normal/personal→omit, private→private, confidential→confidential) — evidence: S02 SENSITIVITY_MAP with 4 entries including None for omit, unit tested
- [x] Outlook recurrence patterns (6 types × 3 range types) correctly convert to RFC 5545 RRULE strings — evidence: S02 recurrence converter covering all 18 combinations exhaustively, 103 field mapper tests include all pattern×range permutations
- [x] RSVP status changes in SemPKM push back to Outlook via Graph API PATCH — evidence: S02 push_sync() fully implemented with REVERSE_RESPONSE_STATUS_MAP, build_event_patch() using Outlook's nested emailAddress/status structure, test_successful_rsvp_push passes
- [x] Delta queries provide efficient incremental sync (only changed events fetched) — evidence: S01 get_events_delta() returns (events, delta_link) tuples; S02 sync_engine stores delta_link:{calendar_id} state keys, test_expired_delta_410_retries_full_sync proves recovery path
- [x] Settings UI offers calendar selection, sync direction, poll interval, Sync Now — evidence: S01 calendar selection UI with checkboxes; S03 15 route-handler tests proving sync_direction, poll_interval, Sync Now dispatch (bidirectional + pull-only), sync-config persistence
- [x] 200+ unit tests covering auth, client, field mapper, sync engine, person matcher — evidence: 41 (auth) + 24 (client) + 103 (field mapper) + 75 (sync engine incl. 15 route-handler) + 14 (person matcher) = 257 tests, S03 reports 192 passed + 1 skipped in 0.39s for combined suite (field mapper + sync engine + person matcher); full count exceeds 200+ target
- [x] Mock Microsoft Graph API server passes selftest — evidence: S04 `python3 server.py --selftest` → 13/13 passed, exit 0. Covers health, token exchange, user profile, calendar list, delta events, RSVP PATCH, and error path (404 on unknown event)
- [x] Playwright E2E test structurally complete — evidence: S04 outlook-calendar-sync.spec.ts (394 lines, 7 phases: cleanup → model → app install → OAuth simulation → calendar selection + sync config → Sync Now + SPARQL verification → admin uninstall). 13 selectors in selectors.ts. Not runtime-executed (pre-existing subprocess startup timing issue, same as M017/M018/M019)
- [x] User guide Chapter 38 documents Outlook sync with field mapping tables and Azure AD setup — evidence: S04 38-outlook-calendar-sync.md (~380 lines) with Azure AD app registration walkthrough, showAs 5-value enum table, sensitivity→visibility table, response status 6→4 mapping, recurrence 6×3 pattern-range matrix with relative index mapping, RSVP push-back, delta sync, HTML body conversion, troubleshooting
- [x] All htmx URLs use `/app/outlook-calendar/` prefix — evidence: S01 grep-verified (0 unprefixed); S04 URL-bearing attribute audit confirmed 0 violations
- [x] README TOC, glossary, appendix A env vars, navigation chain updated — evidence: S04 README TOC entry, glossary "Outlook Calendar Sync" (alphabetically before "Todoist Sync"), 3 OUTLOOK_* env var rows in appendix A, Ch 37 → Ch 38 → Appendix A navigation chain

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Microsoft OAuth + Graph API Client | manifest.yaml, auth.py (7 functions + constants), outlook_client.py (get_calendar_list, get_events_delta, patch_event, 401→refresh→retry), app.py (10 routes), 5 templates, scoped CSS, 65 unit tests (41 auth + 24 client) | pass |
| S02 | Pull Sync + Field Mapping + Recurrence Conversion | field_mapper.py (~380 lines, all constant maps, extraction helpers, recurrence converter, property builder, reverse mapper), sync_engine.py (~680 lines, pull + push with delta queries, @removed handling, two-phase bulk, error isolation), person_matcher.py (~140 lines), requirements.txt (markdownify), 177 unit tests (103 + 60 + 14). **Deviation:** push_sync fully implemented here (not skeleton) — positive scope pull-forward | pass |
| S03 | Push Sync + Settings UI | 15 route-handler unit tests proving template context, bidirectional/pull-only dispatch, push-changes handler, error isolation, sync-config persistence. Push implementation already done in S02, so S03 is test-only. Full suite: 192 passed, 1 skipped | pass |
| S04 | E2E Tests + User Guide | Mock server (server.py ~480 lines, 6 endpoints, 13-check selftest), Docker service wiring (mock-outlook + 3 env vars), Playwright E2E (394 lines, 7 phases, 13 selectors), Chapter 38 (~380 lines), README TOC, glossary, appendix A (3 rows), navigation chain | pass |

## Cross-Slice Integration

**S01 → S02 boundary:** S01 produced auth.py, outlook_client.py, app.py scaffold, manifest, templates, and 65 unit tests. S02 consumed auth module for token management and client for delta queries. No mismatches — S02 used AUTH_STATE_KEYS, get_events_delta() returning (events, delta_link) tuples, and OUTLOOK_API_URL env var override as documented in S01 forward intelligence.

**S02 → S03 boundary:** S02 produced field_mapper.py, sync_engine.py (including complete push_sync), person_matcher.py, and 177 tests. S03 consumed these for route-handler test wiring. Deviation: push_sync was fully implemented in S02 rather than as a skeleton, making S03 lighter (test-only). This is documented in both S02 and S03 summaries. No functional gap.

**S03 → S04 boundary:** S04 consumed all prior outputs for E2E testing and documentation. Mock server PATCH endpoint uses `/v1.0/me/calendars/{calId}/events/{eventId}` matching real OutlookClient (minor path difference from plan, correctly documented as deviation). No integration issues.

## Requirement Coverage

**Gap identified:** The roadmap states "Covers: SYNC-13 (Outlook calendar sync — new, to be registered during execution)" and S02/S04 summaries reference "OL-01 through OL-09" requirement IDs. However, **no OL-* requirements appear in REQUIREMENTS.md**. S04 summary claims "OL-09 — Mock server passes 13-check selftest" as validated, but the requirement was never formally registered.

This is a **bookkeeping gap**, not a functional gap. All prior sync milestones (M016 SYNC-*, M017 GH-*, M018 GCAL-*/EVENT-*) have their requirements formally registered in REQUIREMENTS.md. M020 does not, despite the summaries referencing them.

**Existing requirements used:** EVENT-01 (bpkm:Event type) — validated in M018, correctly reused here. APP-01–14 (App Platform) — active, correctly depended on.

## Known Limitations (non-blocking)

1. **E2E test not runtime-executed** — same pre-existing app subprocess startup timing issue as M017/M018/M019. Structurally complete per success criterion wording.
2. **1 skipped test** — markdownify HTML→Markdown test skipped (optional dependency not in test venv). strip_html_tags fallback path tested and functional.
3. **OL-* requirements not registered** — see Requirement Coverage above.

## Verdict Rationale

All 16 success criteria met with evidence. All 4 slices delivered their claimed outputs with one positive deviation (push_sync pulled forward from S03 to S02). Cross-slice integration clean — boundary map entries align with actual delivery. 257 unit tests exceed the 200+ target. Mock server, E2E test, and user guide all delivered.

The only gap is the missing formal registration of OL-01 through OL-09 requirements in REQUIREMENTS.md. This is a documentation/bookkeeping issue that does not affect the shipped functionality. All capabilities described by those requirement IDs are built, tested, and documented — they just need the REQUIREMENTS.md entries created and the traceability table updated.

**Verdict: needs-attention** — all functional deliverables complete, minor requirement registration gap.

## Attention Items

1. **Register OL-01 through OL-09 in REQUIREMENTS.md** — Create requirement entries matching the pattern of GCAL-01–09/GH-01–07. Cover: OL-01 (MS OAuth), OL-02 (calendar selection), OL-03 (pull sync), OL-04 (attendee resolution), OL-05 (RSVP push-back), OL-06 (recurrence conversion), OL-07 (showAs/sensitivity mapping), OL-08 (delta queries), OL-09 (E2E + user guide). All should be status: validated with appropriate proof references.
2. **Update PROJECT.md** — Add M020 shipping summary to current state section.
