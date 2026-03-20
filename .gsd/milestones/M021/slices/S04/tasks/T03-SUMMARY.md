---
id: T03
parent: S04
milestone: M021
provides:
  - Chapter 39 user guide documenting CalDAV Calendar Sync setup, field mapping, and troubleshooting
  - README TOC entry for Chapter 39
  - Glossary entry for "CalDAV Calendar Sync"
  - Navigation chain: Ch 38 → Ch 39 → Appendix A
key_files:
  - docs/guide/39-caldav-calendar-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/38-outlook-calendar-sync.md
key_decisions:
  - No Appendix A update needed — CalDAV has no environment variable overrides (server URL is user-entered)
  - externalProvider value is "caldav" (not "caldav-calendar") — matches field_mapper.py constant
patterns_established:
  - CalDAV chapter follows Ch 38 Outlook structure but replaces OAuth section with simpler HTTP Basic credentials section
observability_surfaces:
  - none (documentation-only task)
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Chapter 39 user guide and README/glossary/nav-chain updates

**Wrote 368-line Chapter 39 documenting CalDAV Calendar Sync with field mapping tables, server-specific notes, RSVP push-back, and nav-chain updates**

## What Happened

Created Chapter 39 of the user guide following the Ch 38 Outlook pattern but adapted for CalDAV's simpler auth model and protocol-specific details. Key sections:

- **Connecting Your Server** — HTTP Basic auth (server URL, username, password) with PROPFIND discovery chain explanation, replacing the Azure AD OAuth setup from Ch 38
- **Field Mapping** — Two table groups: Core Properties (SUMMARY→title, DTSTART→startDate, etc.) and Attendees/Recurrence (ATTENDEE, ORGANIZER, RRULE, VALARM), plus sub-tables for STATUS, CLASS, and TRANSP mappings — all sourced from `field_mapper.py` constants
- **RSVP Push-Back** — fetch-modify-PUT pattern with ETag concurrency control and reverse PARTSTAT mapping
- **Recurrence Handling** — native RRULE passthrough (contrast with Outlook's structured→RRULE conversion)
- **Server-Specific Notes** — URL patterns for Fastmail, Nextcloud, Synology, Radicale, plus generic discovery
- **Troubleshooting** — connection failures, self-signed certs, empty calendars, ETag conflicts

Updated README TOC, glossary (alphabetically positioned entry), and Ch 38 nav footer. Confirmed no Appendix A update needed — no `CALDAV_*` env vars in the app code.

## Verification

- File exists: `test -f docs/guide/39-caldav-calendar-sync.md` ✓
- Line count: 368 lines (target 300-450) ✓
- README TOC entry present ✓
- Glossary entry present (2 occurrences of "caldav") ✓
- Nav chain Ch 38 → Ch 39 ✓
- Nav chain Ch 39 → Appendix A ✓
- Nav chain Ch 39 → Ch 38 (Previous) ✓
- No CALDAV_* env var overrides in app code ✓
- htmx prefix audit: 0 violations ✓

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/39-caldav-calendar-sync.md` | 0 | ✅ pass | <1s |
| 2 | `grep "39.*CalDAV\|39-caldav" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 3 | `grep -i "caldav calendar sync" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 4 | `grep "Chapter 39" docs/guide/38-outlook-calendar-sync.md` | 0 | ✅ pass | <1s |
| 5 | `grep "Appendix A" docs/guide/39-caldav-calendar-sync.md` | 0 | ✅ pass | <1s |
| 6 | `grep "Chapter 38" docs/guide/39-caldav-calendar-sync.md` | 0 | ✅ pass | <1s |
| 7 | `wc -l docs/guide/39-caldav-calendar-sync.md` (368) | 0 | ✅ pass | <1s |
| 8 | `grep -rE "hx-post\|hx-get" apps/caldav-calendar/frontend/templates/ \| grep -v "/app/caldav-calendar/" \| wc -l` (0) | 0 | ✅ pass | <1s |

## Diagnostics

Documentation-only task — no runtime diagnostics. Verify content accuracy by comparing field mapping tables against `apps/caldav-calendar/services/field_mapper.py` constants (STATUS_MAP, CLASS_MAP, TRANSP_MAP, PARTSTAT_MAP, REVERSE_RESPONSE_STATUS_MAP).

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/39-caldav-calendar-sync.md` — Created: 368-line Chapter 39 user guide
- `docs/guide/README.md` — Added Ch 39 TOC entry after Ch 38
- `docs/guide/appendix-d-glossary.md` — Added "CalDAV Calendar Sync" glossary entry in alphabetical position
- `docs/guide/38-outlook-calendar-sync.md` — Updated nav footer Next link from Appendix A to Chapter 39
- `.gsd/milestones/M021/slices/S04/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
