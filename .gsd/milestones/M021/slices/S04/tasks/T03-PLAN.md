---
estimated_steps: 6
estimated_files: 4
---

# T03: Chapter 39 user guide and README/glossary/nav-chain updates

**Slice:** S04 — E2E Tests + User Guide + Docs
**Milestone:** M021

## Description

Write Chapter 39 of the user guide documenting CalDAV Calendar Sync — the sixth sync app. Follow the Chapter 38 (Outlook) guide structure but adapted for CalDAV's simpler auth (HTTP Basic instead of Azure AD OAuth) and protocol-specific details (WebDAV, iCalendar, RRULE passthrough, server-specific URL patterns). Update README TOC, glossary, and navigation chain.

CalDAV has no environment variable overrides (unlike Google/Outlook which use env vars to point at mock servers) — the server URL is user-entered in the credential form. So there's no Appendix A update needed.

## Steps

1. **Create `docs/guide/39-caldav-calendar-sync.md`** (~350-400 lines). Structure:
   - Title: "# Chapter 39: CalDAV Calendar Sync"
   - Intro paragraph explaining CalDAV sync, supported servers (Fastmail, Nextcloud, Synology, Radicale)
   - **Prerequisites** — Basic PKM v2.1+, a CalDAV server with credentials
   - **Installing the App** — same pattern as Ch 38 (Admin > Applications, enter path)
   - **Connecting Your Server** — HTTP Basic auth section: enter server URL, username, password. No OAuth setup needed. Include note about server URL discovery (well-known URIs).
   - **Selecting Calendars** — checkboxes, save
   - **Sync Configuration** — direction (pull-only, bidirectional), poll interval
   - **Running a Sync** — Sync Now button, sync-collection REPORT with sync-token for incremental
   - **Field Mapping** — Two tables:
     - Core Properties table: iCalendar VEVENT property → bpkm:Event property (SUMMARY→rdfs:label, DTSTART→bpkm:startDate, DTEND→bpkm:endDate, LOCATION→bpkm:location, DESCRIPTION→body, STATUS→bpkm:eventStatus, CLASS→bpkm:visibility, TRANSP→bpkm:showAs, CATEGORIES→bpkm:tags, UID→bpkm:externalUuid, URL→bpkm:externalUrl)
     - Attendees & Recurrence table: ATTENDEE→bpkm:hasAttendee (Person match), ORGANIZER→bpkm:organizer (Person match), PARTSTAT→bpkm:responseStatus, RRULE→bpkm:recurrenceRule (native passthrough), VALARM→bpkm:reminderMinutes
   - **RSVP Push-Back** — fetch-modify-PUT pattern, ETag concurrency, ATTENDEE PARTSTAT modification
   - **Recurrence Handling** — native RRULE passthrough (simpler than Outlook which converts from recurrence patterns). Note: RRULE stored as-is from iCalendar, no conversion needed.
   - **Server-Specific Notes** — subsections for:
     - Fastmail: `https://caldav.fastmail.com/dav/calendars/user/{email}/`
     - Nextcloud: `https://{host}/remote.php/dav/calendars/{username}/`
     - Synology: `https://{nas-ip}:5001/caldav/{username}/`
     - Radicale: `http://{host}:5232/{username}/`
     - Generic: enter the server's CalDAV URL, the app discovers calendars via PROPFIND chain
   - **Troubleshooting** — connection failures, self-signed certs, empty calendar list, sync errors
   - **See Also** — links to Ch 29 (App Platform), Ch 10 (Mental Models)
   - **Nav footer:** Previous: Ch 38 | Next: Appendix A

2. **Update `docs/guide/README.md`** — Add entry after line containing Ch 38:
   ```
   39. [CalDAV Calendar Sync](39-caldav-calendar-sync.md)
   ```

3. **Update `docs/guide/appendix-d-glossary.md`** — Add "CalDAV Calendar Sync" glossary entry in alphabetical position. Follow existing entry format (term as `##` heading, definition paragraph, cross-reference to Chapter 39).

4. **Update `docs/guide/38-outlook-calendar-sync.md`** nav footer — Change the "Next" link from Appendix A to Chapter 39:
   - Old: `**Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`
   - New: `**Next:** [Chapter 39: CalDAV Calendar Sync](39-caldav-calendar-sync.md)`

5. **Verify nav chain integrity:**
   - Ch 38 footer → Next: Ch 39 ✓
   - Ch 39 footer → Previous: Ch 38, Next: Appendix A ✓
   - README has Ch 39 entry ✓
   - Glossary has CalDAV entry ✓

6. **Verify no Appendix A update needed** — CalDAV has no env var overrides. Confirm by checking that the app code doesn't read any CALDAV_* environment variables (it shouldn't — the server URL comes from user input in the credential form).

## Must-Haves

- [ ] Chapter 39 with field mapping tables (Core Properties + Attendees/Recurrence)
- [ ] Server-Specific Notes section with URL patterns for Fastmail, Nextcloud, Synology, Radicale
- [ ] RSVP Push-Back section explaining fetch-modify-PUT pattern
- [ ] README TOC entry for Ch 39
- [ ] Glossary entry for "CalDAV Calendar Sync"
- [ ] Nav chain: Ch 38 → Ch 39 → Appendix A

## Verification

- `test -f docs/guide/39-caldav-calendar-sync.md` — file exists
- `grep "39.*CalDAV\|39-caldav" docs/guide/README.md` — TOC entry present
- `grep -i "caldav calendar sync" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "Chapter 39" docs/guide/38-outlook-calendar-sync.md` — nav chain from Ch 38 to Ch 39
- `grep "Appendix A" docs/guide/39-caldav-calendar-sync.md` — nav chain from Ch 39 to Appendix A
- `grep "Chapter 38" docs/guide/39-caldav-calendar-sync.md` — nav chain from Ch 39 back to Ch 38
- `wc -l docs/guide/39-caldav-calendar-sync.md` — should be 300-450 lines

## Inputs

- `docs/guide/38-outlook-calendar-sync.md` — Reference pattern for chapter structure, field mapping tables, troubleshooting
- `docs/guide/README.md` — TOC file to update
- `docs/guide/appendix-d-glossary.md` — Glossary to update
- `apps/caldav-calendar/services/field_mapper.py` — Authoritative source for field mappings (enum maps, extraction functions). Contains STATUS_MAP, CLASS_MAP, TRANSP_MAP, PARTSTAT_MAP, REVERSE_RESPONSE_STATUS_MAP.
- `apps/caldav-calendar/services/caldav_client.py` — Discovery chain details for server-specific notes
- S01/S02/S03 summaries — Key decisions, known limitations, and patterns for accurate documentation

## Observability Impact

This task produces documentation only — no runtime behavior changes.

- **Signals changed:** None. No code, API, or runtime modifications.
- **Future agent inspection:** Verify Chapter 39 exists and nav chain is intact via `grep` commands in the Verification section. Check field mapping tables match `apps/caldav-calendar/services/field_mapper.py` constants.
- **Failure visibility:** Documentation build failures (if any static-site generator is introduced) would surface as broken links. Currently, docs are plain Markdown served via volume mount — no build step.

## Expected Output

- `docs/guide/39-caldav-calendar-sync.md` — ~350-400 line user guide chapter
- `docs/guide/README.md` — Modified with Ch 39 entry
- `docs/guide/appendix-d-glossary.md` — Modified with CalDAV glossary entry
- `docs/guide/38-outlook-calendar-sync.md` — Modified nav footer (Next → Ch 39)
