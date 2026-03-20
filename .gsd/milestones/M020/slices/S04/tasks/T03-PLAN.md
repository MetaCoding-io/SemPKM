---
estimated_steps: 7
estimated_files: 5
---

# T03: Write Chapter 38 user guide and update README, glossary, appendix, navigation

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M020

## Description

Write the Chapter 38 user guide documenting Outlook Calendar Sync, following Chapter 36 (Google Calendar Sync) as the structural template. Update all surrounding docs: README TOC, glossary, appendix A environment variables, and navigation chain (Ch 37 → Ch 38 → Appendix A). Also run the htmx prefix audit to confirm all app template URLs use the `/app/outlook-calendar/` proxy prefix.

## Steps

1. **Write `docs/guide/38-outlook-calendar-sync.md`** — follow Chapter 36's structure with Outlook-specific content. Sections:

   - **Title:** `# Chapter 38: Outlook Calendar Sync`
   - **Intro paragraph:** describes the app, pull sync, RSVP push-back, bidirectional mode, polling
   - **Prerequisites:** basic-pkm v2.1+ installed; Azure AD app registration (Application (client) ID + client secret + redirect URI)
   - **Installing the App:** `/app/apps/outlook-calendar` path, install steps
   - **Setting Up Azure AD:** Step-by-step Azure Portal instructions — App registrations → New registration → Set redirect URI (Web) to `http://localhost:3000/app/outlook-calendar/_fragments/oauth-callback` → Certificates & secrets → New client secret → Copy Application (client) ID and secret value. Note about API permissions: `Calendars.ReadWrite` and `offline_access` (added automatically with `/common/` endpoint).
   - **Connecting Your Account:** Enter credentials → click "Connect with Microsoft" → OAuth consent → redirect back → calendar list appears
   - **Selecting Calendars:** Check calendars to sync → Save
   - **Sync Configuration:** Sync direction (pull-only vs bidirectional), poll interval, explanation of delta queries for efficiency
   - **Running a Sync:** Sync Now button, what happens during sync (delta query → field mapping → bulk create), sync stats display
   - **Field Mapping** — the core reference section with tables:
     - Core properties table: subject→name, body→body (HTML→Markdown via markdownify), start/end→startTime/endTime, timeZone, isAllDay→allDay, location→location, webLink→externalUrl, id→externalId, iCalUId→externalUuid
     - Status/visibility table: isCancelled→eventStatus, sensitivity→visibility (normal/personal→omit, private→private, confidential→confidential)
     - showAs table: 5 values (free, tentative, busy, oof→outOfOffice, workingElsewhere)
     - Recurrence table: 6 pattern types (daily, weekly, absoluteMonthly, relativeMonthly, absoluteYearly, relativeYearly) × 3 range types (endDate→UNTIL, numbered→COUNT, noEnd→no terminator) with RRULE component mapping
     - Attendees table: attendees[].emailAddress.address → resolved Person/Contact via SPARQL, attendees[].status.response → responseStatus
     - Categories table: categories[] → bpkm:tags (comma-joined)
     - Conference URL: onlineMeeting.joinUrl → conferenceUrl
     - Sync metadata: lastSyncedAt, externalProvider="outlook"
   - **RSVP Push-Back:** How bidirectional mode detects responseStatus changes via SPARQL, reverse maps, PATCHes Graph API. Loop prevention via lastSyncedAt.
   - **Recurrence Handling:** Explanation of Outlook's structured pattern object vs RFC 5545 RRULE. The converter handles all 18 combinations. relativeMonthly/relativeYearly index→BYDAY note.
   - **All-Day Events:** `isAllDay: true` → `xsd:date` (not `xsd:dateTime`), `allDay: "true"`
   - **Conference URLs:** `onlineMeeting.joinUrl` extraction (Teams, Zoom, etc.)
   - **Attendee Resolution:** Email lookup via SPARQL (foaf:mbox, crm:email), Person creation on miss
   - **HTML Body Conversion:** Outlook bodies can be HTML — `markdownify` converts to Markdown, plain text passes through
   - **Admin Monitoring:** Admin > Applications > Outlook Calendar detail page — status, task history, start/stop/restart
   - **Troubleshooting:** Common issues — OAuth errors (wrong redirect URI, expired secret), empty sync (no calendars selected), token refresh failures, delta query 410 Gone recovery
   - **See Also:** Links to Ch 29 (App Platform), Ch 10 (Mental Models), Appendix A (env vars)
   - **Navigation footer:** `**Previous:** [Chapter 37: Todoist Sync](37-todoist-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. **Update `docs/guide/README.md`** — add line after the Todoist entry (line 66):
   ```
   38. [Outlook Calendar Sync](38-outlook-calendar-sync.md)
   ```

3. **Update `docs/guide/appendix-d-glossary.md`** — add "Outlook Calendar Sync" entry in alphabetical order:
   ```
   **Outlook Calendar Sync** — An app that synchronizes Microsoft Outlook Calendar events with SemPKM as `bpkm:Event` objects. Supports pull sync, RSVP push-back, delta queries for incremental polling, and recurrence pattern→RRULE conversion. See [Chapter 38](38-outlook-calendar-sync.md).
   ```

4. **Update `docs/guide/appendix-a-environment-variables.md`** — add 3 rows to the environment variables table:
   - `OUTLOOK_API_URL` — Base URL for Microsoft Graph API v1.0. Override for testing with mock server. Default: `https://graph.microsoft.com/v1.0`
   - `OUTLOOK_TOKEN_URL` — Microsoft Identity Platform token endpoint. Override for testing. Default: `https://login.microsoftonline.com/common/oauth2/v2.0/token`
   - `OUTLOOK_AUTH_URL` — Microsoft Identity Platform authorization endpoint. Override for testing. Default: `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`

5. **Update `docs/guide/37-todoist-sync.md`** — change the navigation footer from:
   ```
   **Previous:** [Chapter 36: Google Calendar Sync](36-google-calendar-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```
   to:
   ```
   **Previous:** [Chapter 36: Google Calendar Sync](36-google-calendar-sync.md) | **Next:** [Chapter 38: Outlook Calendar Sync](38-outlook-calendar-sync.md)
   ```

6. **Run htmx prefix audit:**
   ```bash
   grep -rn "hx-" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/"
   ```
   Must return 0 results. If any results found, the app templates have htmx URLs that bypass the proxy — flag this but do NOT fix (app code is from earlier slices).

7. **Verify all updates** with the verification commands listed below.

## Must-Haves

- [ ] Chapter 38 exists with field mapping tables (showAs 5 values, sensitivity→visibility, recurrence 6×3 matrix)
- [ ] Azure AD setup instructions with redirect URI
- [ ] README TOC has Chapter 38 entry
- [ ] Glossary has "Outlook Calendar Sync" entry
- [ ] Appendix A has 3 `OUTLOOK_*` env var rows
- [ ] Navigation chain: Ch 37 → Ch 38 → Appendix A
- [ ] htmx prefix audit clean (0 results)

## Verification

- `test -f docs/guide/38-outlook-calendar-sync.md` — file exists
- `grep "38.*Outlook" docs/guide/README.md` — TOC entry
- `grep "Outlook Calendar Sync" docs/guide/appendix-d-glossary.md` — glossary entry
- `grep -c "OUTLOOK_" docs/guide/appendix-a-environment-variables.md` — returns 3 (or more)
- `grep "Chapter 38" docs/guide/37-todoist-sync.md` — navigation updated
- `grep "Chapter 37" docs/guide/38-outlook-calendar-sync.md` — back-link exists
- `grep "Appendix A" docs/guide/38-outlook-calendar-sync.md` — forward-link exists
- `grep -rn "hx-" apps/outlook-calendar/ | grep -v "/app/outlook-calendar/" | wc -l` — returns 0

## Inputs

- `docs/guide/36-google-calendar-sync.md` — structural template (377 lines, 12 sections)
- `docs/guide/37-todoist-sync.md` — navigation footer to update (currently points to Appendix A)
- `docs/guide/README.md` — TOC, line 66 has Todoist entry
- `docs/guide/appendix-d-glossary.md` — alphabetical glossary entries
- `docs/guide/appendix-a-environment-variables.md` — env var table (has `TODOIST_API_URL` at line 32)
- `apps/outlook-calendar/services/field_mapper.py` — SHOW_AS_MAP (5 values), SENSITIVITY_MAP (4 mappings), RESPONSE_STATUS_MAP, recurrence converter (6 patterns × 3 ranges)
- `apps/outlook-calendar/services/auth.py` — env var defaults: `OUTLOOK_AUTH_URL` → `https://login.microsoftonline.com/common/oauth2/v2.0/authorize`, `OUTLOOK_TOKEN_URL` → `https://login.microsoftonline.com/common/oauth2/v2.0/token`, `OUTLOOK_API_URL` → `https://graph.microsoft.com/v1.0`

## Expected Output

- `docs/guide/38-outlook-calendar-sync.md` — new file, ~350-400 lines
- `docs/guide/README.md` — 1 line added (TOC entry)
- `docs/guide/appendix-d-glossary.md` — 1 entry added
- `docs/guide/appendix-a-environment-variables.md` — 3 rows added
- `docs/guide/37-todoist-sync.md` — navigation footer updated

## Observability Impact

This is a documentation-only task — no runtime behavior changes. No new logs, metrics, health endpoints, or diagnostic commands are introduced.

- **Inspection surface:** The five modified/created docs files can be validated with `grep` commands (see Verification section).
- **Failure visibility:** Broken navigation links or missing entries are detectable via the verification commands. Missing field mapping tables are visible by manual inspection of Ch 38 headings.
- **No runtime signals:** This task does not modify application code, so there are no status endpoints, log entries, or error shapes to monitor.
