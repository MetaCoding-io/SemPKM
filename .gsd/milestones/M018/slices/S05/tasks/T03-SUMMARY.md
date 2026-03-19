---
id: T03
parent: S05
milestone: M018
provides:
  - Chapter 36 user guide for Google Calendar Sync (377 lines)
  - README TOC entry for Chapter 36
  - Chapter 35 navigation footer updated to link to Chapter 36
  - Glossary entry for Google Calendar Sync
  - Appendix A entries for GCAL_API_URL and GOOGLE_TOKEN_URL
  - GCAL-05, GCAL-06, GCAL-09 requirements moved to validated
key_files:
  - docs/guide/36-google-calendar-sync.md
  - docs/guide/README.md
  - docs/guide/35-github-sync.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-a-environment-variables.md
  - .gsd/REQUIREMENTS.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - "File existence: docs/guide/36-google-calendar-sync.md (377 lines)"
  - "Navigation chain: rg 'Chapter 36' docs/guide/35-github-sync.md"
  - "Requirement status: rg -A1 'GCAL-0[569]' .gsd/REQUIREMENTS.md | grep validated"
duration: 18m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Chapter 36 user guide + docs updates + requirement validation

**Added Chapter 36 Google Calendar Sync user guide (377 lines), updated all cross-references (README TOC, Ch 35 footer, glossary, appendix-a env vars), and moved GCAL-05/06/09 to validated**

## What Happened

Wrote `docs/guide/36-google-calendar-sync.md` (377 lines) following the Chapter 35 GitHub Sync structure. The chapter covers: prerequisites (Basic PKM + Google Cloud Console OAuth setup), app installation, OAuth credential configuration, connecting to Google (consent flow, token refresh), calendar selection, sync direction and poll interval, manual sync with stats, comprehensive field mapping tables organized into 7 groups covering all ~22 Google Calendar → bpkm:Event property transforms, RSVP push-back workflow (scope limitation, status mapping, loop prevention), recurrence handling (master events with RRULE, exception instances), all-day event detection, conference URL extraction, attendee resolution (email match, create on miss, LRU cache), admin monitoring, and troubleshooting (6 common issues).

Updated all cross-reference points: README TOC has Ch 36, Ch 35 footer links to Ch 36 instead of Appendix A, glossary has "Google Calendar Sync" entry, appendix-a has GCAL_API_URL and GOOGLE_TOKEN_URL rows.

Moved three requirements to validated in REQUIREMENTS.md with proof references: GCAL-05 (RSVP push-back — 32 unit tests, reverse mapping, loop prevention), GCAL-06 (recurrence handling — RRULE extraction, recurringEventId propagation), GCAL-09 (E2E tests + user guide — mock server, E2E test, Chapter 36).

## Verification

All 9 task-level verification checks pass:
- Chapter 36 exists at 377 lines (≥200 ✓)
- README TOC includes Chapter 36 ✓
- Glossary has "Google Calendar Sync" entry ✓
- Appendix A has GCAL_API_URL ✓
- Appendix A has GOOGLE_TOKEN_URL ✓
- Ch 35 footer links to Chapter 36 ✓
- GCAL-05 status: validated ✓
- GCAL-06 status: validated ✓
- GCAL-09 status: validated ✓

Slice-level verification (partial — this is the final task):
- Mock selftest: 11/11 passed ✓
- Chapter 36 exists at 377 lines ✓
- README TOC has Ch 36 ✓
- Glossary has entry ✓
- Appendix A has env vars ✓
- Navigation chain: Ch 35 → Ch 36 → Appendix A ✓
- Requirements validated ✓
- E2E Playwright test: not re-run in this task (T02 scope)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `wc -l docs/guide/36-google-calendar-sync.md` | 0 | ✅ 377 lines | <1s |
| 2 | `rg 'Chapter 36\|36-google-calendar' docs/guide/README.md` | 0 | ✅ TOC entry present | <1s |
| 3 | `rg 'Google Calendar Sync' docs/guide/appendix-d-glossary.md` | 0 | ✅ glossary entry | <1s |
| 4 | `rg 'GCAL_API_URL' docs/guide/appendix-a-environment-variables.md` | 0 | ✅ env var present | <1s |
| 5 | `rg 'GOOGLE_TOKEN_URL' docs/guide/appendix-a-environment-variables.md` | 0 | ✅ env var present | <1s |
| 6 | `rg 'Chapter 36' docs/guide/35-github-sync.md` | 0 | ✅ nav link updated | <1s |
| 7 | `rg -A1 'GCAL-05' .gsd/REQUIREMENTS.md \| grep validated` | 0 | ✅ validated | <1s |
| 8 | `rg -A1 'GCAL-06' .gsd/REQUIREMENTS.md \| grep validated` | 0 | ✅ validated | <1s |
| 9 | `rg -A1 'GCAL-09' .gsd/REQUIREMENTS.md \| grep validated` | 0 | ✅ validated | <1s |
| 10 | `python3 e2e/mock-google-calendar-api/server.py --selftest` | 0 | ✅ 11/11 passed | 1s |

## Diagnostics

Documentation-only task. No runtime diagnostics. Cross-reference integrity verifiable via:
- `rg 'Chapter 36' docs/guide/35-github-sync.md` — navigation chain forward link
- `rg '36-google-calendar' docs/guide/README.md` — TOC presence
- `rg -A1 'GCAL-0[569]' .gsd/REQUIREMENTS.md | grep validated` — requirement status

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/36-google-calendar-sync.md` — new, Chapter 36 user guide (377 lines)
- `docs/guide/README.md` — added Ch 36 to TOC
- `docs/guide/35-github-sync.md` — updated navigation footer to point to Ch 36
- `docs/guide/appendix-d-glossary.md` — added "Google Calendar Sync" entry
- `docs/guide/appendix-a-environment-variables.md` — added GCAL_API_URL and GOOGLE_TOKEN_URL rows
- `.gsd/REQUIREMENTS.md` — moved GCAL-05, GCAL-06, GCAL-09 to validated with proof
- `.gsd/milestones/M018/slices/S05/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
