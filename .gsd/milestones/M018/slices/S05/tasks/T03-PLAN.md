---
estimated_steps: 7
estimated_files: 6
---

# T03: Chapter 36 user guide + docs updates + requirement validation

**Slice:** S05 — E2E tests + user guide
**Milestone:** M018

## Description

Write the Chapter 36 user guide for Google Calendar Sync following the Chapter 35 (GitHub Sync) structure. Update all cross-reference points: README TOC, chapter 35 navigation footer, glossary, appendix-a environment variables. Move GCAL-05, GCAL-06, GCAL-09 to validated in REQUIREMENTS.md with proof references.

## Steps

1. **Create `docs/guide/36-google-calendar-sync.md`** (~250-350 lines) following Chapter 35 structure. Sections:
   - Title: "# Chapter 36: Google Calendar Sync"
   - Intro paragraph (what the app does — bidirectional sync of Google Calendar events to bpkm:Event objects)
   - **Prerequisites** — Basic PKM model installed, Google Cloud Console project with OAuth 2.0 Client ID (Calendar API enabled), redirect URI configuration
   - **Installing the App** — Admin > Applications, path `/app/apps/google-calendar`, wait for Running
   - **Setting Up OAuth** — Step-by-step: create OAuth client in Google Cloud Console, configure authorized redirect URI (`http://localhost:3000/app/google-calendar/_fragments/oauth-callback`), copy Client ID and Client Secret
   - **Connecting to Google** — Enter credentials in app settings, click "Connect with Google", complete OAuth consent, verify "Connected" status with email
   - **Selecting Calendars** — Check calendars to sync, primary calendar auto-detected, save selection
   - **Configuring Sync** — Direction (pull-only vs bidirectional), poll interval (5m/15m/30m/1h), save config
   - **Running a Sync** — Sync Now button, sync stats (created/updated/unchanged/errors)
   - **Field Mapping** — Table showing Google Calendar field → bpkm:Event property mapping for all ~22 properties:
     - summary → rdfs:label, description → body (HTML stripped), start → schema:startDate, end → schema:endDate, start.timeZone → bpkm:timeZone
     - status → bpkm:eventStatus (confirmed/tentative/cancelled), visibility → bpkm:visibility, transparency → bpkm:showAs
     - location → bpkm:location, htmlLink → bpkm:externalUrl, id → bpkm:externalId, iCalUID → bpkm:externalUuid
     - conferenceData → bpkm:conferenceUrl (Meet/Zoom), reminders → bpkm:reminderMinutes
     - attendees → bpkm:attendee edges to Person objects, organizer → bpkm:organizer edge
     - self responseStatus → bpkm:responseStatus, recurrence → bpkm:recurrenceRule, recurringEventId → bpkm:recurringEventId
     - start.date (all-day) → bpkm:allDay=true + xsd:date, calendarId → bpkm:calendarName
   - **RSVP Push-Back** — How bidirectional mode pushes responseStatus changes back to Google via PATCH, scope limited to RSVP only (per D213)
   - **Recurrence Handling** — Recurring events stored as master with RRULE, individually modified instances as separate Events linked to master via recurringEventId, no expansion of recurring series
   - **All-Day Events** — How all-day events are distinguished (xsd:date vs xsd:dateTime, bpkm:allDay flag)
   - **Conference URLs** — Automatic extraction from conferenceData (Meet, Zoom) with hangoutLink fallback
   - **Attendee Resolution** — How attendees are matched to existing Person/Contact objects by email, creation on miss
   - **Admin Monitoring** — Admin > Applications > Google Calendar detail page, task history, sync stats
   - **Troubleshooting** — Common issues: OAuth redirect URI mismatch, token refresh failure, 410 Gone (full resync), rate limiting, missing calendars
   - **See Also** — Links to Chapter 29 (App Platform), Chapter 10 (Managing Mental Models), Appendix A (env vars)
   - **Navigation footer** — `**Previous:** [Chapter 35: GitHub Sync](35-github-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. **Update `docs/guide/README.md`** — Add `36. [Google Calendar Sync](36-google-calendar-sync.md)` to the TOC, after the Chapter 35 entry.

3. **Update `docs/guide/35-github-sync.md` navigation footer** — Change the "Next" link from Appendix A to Chapter 36:
   - Old: `**Previous:** [Chapter 34: Linear Sync](34-linear-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`
   - New: `**Previous:** [Chapter 34: Linear Sync](34-linear-sync.md) | **Next:** [Chapter 36: Google Calendar Sync](36-google-calendar-sync.md)`

4. **Update `docs/guide/appendix-d-glossary.md`** — Add "Google Calendar Sync" entry with brief description and cross-reference to Chapter 36. Follow existing glossary entry format.

5. **Update `docs/guide/appendix-a-environment-variables.md`** — Add two rows to the table:
   - `GCAL_API_URL` — "Base URL for the Google Calendar REST API v3. Override to redirect the Google Calendar Sync app to a different endpoint (e.g. a mock server for testing)." Default: `https://www.googleapis.com/calendar/v3`. Required: No.
   - `GOOGLE_TOKEN_URL` — "Google OAuth 2.0 token exchange endpoint. Override for testing against a mock OAuth server." Default: `https://oauth2.googleapis.com/token`. Required: No.

6. **Update `.gsd/REQUIREMENTS.md`** — Move three requirements to validated:
   - **GCAL-05** (RSVP push-back) → validated. Primary Slice: M018/S04. Proof: 32 push pipeline unit tests (test_gcal_sync_engine.py + test_gcal_field_mapper.py push tests). push_sync() detects responseStatus changes via SPARQL, reverse maps, PATCHes Google API with loop prevention.
   - **GCAL-06** (Recurrence handling) → validated. Primary Slice: M018/S04. Proof: pull_sync stores RRULE on master events, recurrence property in field_mapper.py extract_recurrence_rule(). Note: exception→master linking code (T02) is not present in worktree; master RRULE storage is proven by unit tests.
   - **GCAL-09** (E2E tests and user guide) → validated. Primary Slice: M018/S05. Proof: Mock Google Calendar API server (selftest), Playwright E2E test (install → OAuth → sync → verify), Chapter 36 user guide.

7. **Verify all cross-references** — Confirm navigation chain: Ch 35 → Ch 36 → Appendix A. Confirm README TOC has Ch 36. Confirm glossary has entry. Confirm appendix-a has env vars.

## Must-Haves

- [ ] Chapter 36 exists at `docs/guide/36-google-calendar-sync.md` with ≥200 lines covering all major sections
- [ ] Field mapping table covers all ~22 Google Calendar → bpkm:Event property transforms
- [ ] README TOC includes Chapter 36
- [ ] Chapter 35 navigation footer links to Chapter 36 (not Appendix A)
- [ ] Glossary has "Google Calendar Sync" entry
- [ ] Appendix A has `GCAL_API_URL` and `GOOGLE_TOKEN_URL` entries
- [ ] GCAL-05, GCAL-06, GCAL-09 moved to validated with proof references in REQUIREMENTS.md

## Verification

- `wc -l docs/guide/36-google-calendar-sync.md` — ≥200 lines
- `rg 'Chapter 36|36-google-calendar' docs/guide/README.md` — TOC entry present
- `rg 'Google Calendar Sync' docs/guide/appendix-d-glossary.md` — glossary entry present
- `rg 'GCAL_API_URL' docs/guide/appendix-a-environment-variables.md` — env var present
- `rg 'GOOGLE_TOKEN_URL' docs/guide/appendix-a-environment-variables.md` — env var present
- `rg 'Chapter 36' docs/guide/35-github-sync.md` — navigation link updated
- `rg 'GCAL-05' .gsd/REQUIREMENTS.md | grep validated` — requirement moved
- `rg 'GCAL-06' .gsd/REQUIREMENTS.md | grep validated` — requirement moved
- `rg 'GCAL-09' .gsd/REQUIREMENTS.md | grep validated` — requirement moved

## Inputs

- `docs/guide/35-github-sync.md` — reference chapter structure (309 lines, field mapping tables, troubleshooting)
- `docs/guide/README.md` — current TOC (ends at Chapter 35)
- `docs/guide/appendix-d-glossary.md` — glossary format
- `docs/guide/appendix-a-environment-variables.md` — env var table format
- `.gsd/REQUIREMENTS.md` — current GCAL-05, GCAL-06, GCAL-09 entries (status: active)
- `apps/google-calendar/services/field_mapper.py` — property transform functions and normalization maps for the field mapping table
- `apps/google-calendar/services/auth.py` — OAuth flow details for the user guide
- S03 Summary — field mapping details, attendee resolution pattern
- S04 T01 Summary — RSVP push-back pipeline details, reverse mapping
- S04 T02 Summary — recurrence handling details (what was built, what's missing)
- D210 (OAuth), D211 (polling), D212 (cross-provider superset), D213 (RSVP-only push), D214 (GCAL-/EVENT- prefixes) — architectural decisions to reference

## Observability Impact

This task produces documentation artifacts only — no runtime behavior changes. No new logs, metrics, or diagnostic endpoints. The observable signals are:

- **File existence:** `docs/guide/36-google-calendar-sync.md` exists with ≥200 lines.
- **Cross-reference integrity:** Navigation chain Ch 35 → Ch 36 → Appendix A verifiable via `rg` commands.
- **Requirement status:** `rg 'GCAL-05|GCAL-06|GCAL-09' .gsd/REQUIREMENTS.md | grep validated` confirms three requirements moved.
- **Failure shape:** If the doc file is missing or navigation links are broken, downstream users and agents will hit dead links or missing TOC entries.

## Expected Output

- `docs/guide/36-google-calendar-sync.md` — new, ~250-350 lines
- `docs/guide/README.md` — modified with Ch 36 TOC entry
- `docs/guide/35-github-sync.md` — modified navigation footer
- `docs/guide/appendix-d-glossary.md` — modified with new entry
- `docs/guide/appendix-a-environment-variables.md` — modified with 2 new rows
- `.gsd/REQUIREMENTS.md` — modified with 3 requirements moved to validated
