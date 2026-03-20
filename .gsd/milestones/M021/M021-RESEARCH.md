# M021: CalDAV Calendar Sync — Research

**Date:** 2026-03-19

## Summary

CalDAV is the sixth sync app on the App Platform and the third calendar provider (after Google M018, Outlook M020). The codebase has a mature, battle-tested pattern for calendar sync apps — two prior implementations provide near-identical scaffolding. CalDAV is architecturally simpler than Google or Outlook because iCalendar (RFC 5545) is the *native* format for bpkm:Event properties: RRULE, STATUS, CLASS, TRANSP, ATTENDEE PARTSTAT all map directly without conversion. The main novel complexity is the CalDAV/WebDAV protocol layer itself (PROPFIND, REPORT, PUT, DELETE with XML request/response bodies) and iCalendar parsing/generation.

The `icalendar` Python library handles RFC 5545 parsing/generation. The CalDAV protocol requires hand-crafted XML for PROPFIND/REPORT requests and XML parsing for responses — no standard Python CalDAV client library is mature enough to justify a dependency (caldav 1.x exists but has inconsistent API and limited maintenance). httpx with hand-crafted XML is the cleanest approach given the SDK's HttpClient already wraps httpx.

**Primary recommendation:** Follow the M018/M020 pattern exactly (manifest, services/, frontend/templates/, field_mapper, sync_engine, person_matcher, auth, client) with two key differences: (1) the REST client speaks WebDAV XML instead of JSON, and (2) auth supports HTTP Basic + OAuth 2.0 (no proprietary auth flow like Microsoft). RRULE handling is trivially simpler — iCalendar RRULE strings pass through directly (no Outlook-style pattern→RRULE conversion needed).

## Recommendation

**Approach:** Clone the Google Calendar app structure, replace GCalClient with a CalDAVClient that speaks WebDAV/XML, replace JSON field mapping with iCalendar property extraction via the `icalendar` library, and simplify auth to HTTP Basic (primary) with optional OAuth 2.0.

**Why this approach:**
- 5 prior sync apps prove the manifest/services/frontend pattern works
- bpkm:Event type (EVENT-01) already has the cross-provider superset properties (D212)
- iCalendar → bpkm:Event mapping is the most direct of all three calendar providers (native RRULE, native STATUS enum, native CLASS, native TRANSP)
- CalDAV sync-token incremental sync matches Google's syncToken pattern conceptually
- ETag-based concurrency for PUT is standard HTTP — simpler than Google/Outlook's proprietary conflict handling

**What's different from Google/Outlook:**
- **Protocol:** XML-over-HTTP (WebDAV) instead of JSON REST. PROPFIND for discovery, REPORT for sync-collection, PUT/DELETE for mutations.
- **Auth:** HTTP Basic is the primary auth method (Fastmail, Nextcloud, Synology, Radicale). OAuth 2.0 is a secondary path (Google CalDAV, some enterprise setups). No complex OAuth flow needed for the primary audience.
- **Data format:** iCalendar (.ics) text format instead of JSON. The `icalendar` library parses VEVENT components into Python objects with typed properties.
- **RRULE:** Direct passthrough — iCalendar RRULE strings are RFC 5545 native. No conversion needed (unlike Outlook's pattern→RRULE converter which was 18 combinations).
- **Bidirectional write:** PUT with full .ics body (not PATCH with partial JSON). Requires regenerating the complete VEVENT from bpkm:Event properties.
- **Discovery:** CalDAV well-known URLs (`/.well-known/caldav`) + PROPFIND for calendar home set + PROPFIND for calendar list. Multi-step discovery unlike single-endpoint Google/Outlook APIs.

## Implementation Landscape

### Key Files

**Existing pattern files to clone from `apps/google-calendar/`:**
- `manifest.yaml` — app manifest (permissions, tasks, UI page). Change appId to `caldav-calendar`, network permissions to `*` (any CalDAV server), icon to `calendar-sync` or similar.
- `app.py` — app entry point with route handlers and task handlers. Same structure, different auth flow.
- `services/auth.py` — auth module. Simplify to HTTP Basic credential storage (URL + username + password via StateClient). Add optional OAuth 2.0 path.
- `services/gcal_client.py` → `services/caldav_client.py` — REST client. Replace JSON requests with WebDAV XML (PROPFIND, REPORT, PUT, DELETE). Handle XML response parsing. Support sync-token incremental sync via `sync-collection` REPORT.
- `services/field_mapper.py` — field mapping. Replace Google JSON extraction with iCalendar property extraction using the `icalendar` library. Simpler than both Google and Outlook mappers (direct enum mappings, native RRULE).
- `services/sync_engine.py` — sync orchestration. Same two-phase bulk pattern. Same SPARQL lookup for existing events. Same push_sync with RSVP push-back (PUT instead of PATCH).
- `services/person_matcher.py` — copy verbatim from Google Calendar (same SPARQL email lookup + create-on-miss + LRU cache pattern).
- `frontend/templates/connect.html` — credential entry form (server URL, username, password). No OAuth redirect dance for Basic auth.
- `frontend/templates/connect_status.html` — calendar list with checkboxes. Same UI pattern, populated from PROPFIND calendar list.
- `frontend/static/styles.css` — copy from Google Calendar.

**Test files to create:**
- `backend/tests/test_caldav_auth.py` — credential storage, connection test
- `backend/tests/test_caldav_client.py` — WebDAV XML request/response, pagination, sync-token, ETag handling
- `backend/tests/test_caldav_field_mapper.py` — iCalendar↔bpkm:Event property transforms (all field directions)
- `backend/tests/test_caldav_sync_engine.py` — pull sync, push sync, loop prevention, error isolation
- `backend/tests/test_caldav_person_matcher.py` — email lookup, create-on-miss
- `e2e/tests/mock-caldav/server.py` — mock CalDAV server returning canned XML/ICS responses
- `e2e/tests/28-caldav-calendar/caldav-calendar-sync.spec.ts` — Playwright E2E test

**Docs:**
- `docs/guide/39-caldav-calendar-sync.md` — user guide chapter

### Key Libraries

| Problem | Library | Why |
|---------|---------|-----|
| iCalendar parsing/generation | `icalendar` (PyPI) | Standard Python library for RFC 5545. Parses .ics text into Python objects (Calendar, Event components). Generates valid .ics output. Already listed in CONTEXT.md constraints. |
| XML generation for WebDAV | stdlib `xml.etree.ElementTree` | PROPFIND/REPORT request bodies are small XML documents. No need for lxml — stdlib ET is sufficient. |
| XML response parsing | stdlib `xml.etree.ElementTree` | WebDAV responses (multistatus, propstat) are XML. Namespace-aware parsing with ET handles CalDAV XML cleanly. |

**Do NOT use:**
- `caldav` library (PyPI) — inconsistent API, limited maintenance, brings its own HTTP client which conflicts with SDK's HttpClient. Hand-crafted XML with httpx is cleaner and fully under our control.
- `vobject` — older iCalendar library, superseded by `icalendar`. Less actively maintained.

### CalDAV Protocol Details

**Discovery chain (one-time on connect):**
1. `GET /.well-known/caldav` → 301/302 redirect to CalDAV root
2. `PROPFIND /` with `DAV:current-user-principal` → user's principal URL
3. `PROPFIND {principal}` with `urn:ietf:params:xml:ns:caldav:calendar-home-set` → calendar home URL
4. `PROPFIND {calendar-home}` with Depth:1 → list of calendars with displayname, ctag, supported components

**Incremental sync via sync-collection REPORT:**
```xml
<d:sync-collection xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:sync-token>{previous_token}</d:sync-token>
  <d:sync-level>1</d:sync-level>
  <d:prop>
    <d:getetag/>
    <c:calendar-data/>
  </d:prop>
</d:sync-collection>
```
Response includes changed/added resources (with full .ics data) and deleted resource hrefs. New sync-token in response for next call.

**Full sync (no sync-token):**
`REPORT` with `calendar-query` requesting all VEVENTs, or `PROPFIND` Depth:1 to list all resources, then `GET` each .ics.

**Event creation/update via PUT:**
```
PUT /calendars/user/default/{uid}.ics HTTP/1.1
Content-Type: text/calendar
If-Match: "etag-value"  (for updates only)
If-None-Match: *  (for creates only)

BEGIN:VCALENDAR
...VEVENT...
END:VCALENDAR
```

**Event deletion:**
```
DELETE /calendars/user/default/{uid}.ics HTTP/1.1
If-Match: "etag-value"
```

### iCalendar Field Mapping (via `icalendar` library)

The `icalendar` library parses VEVENT components into objects with typed property access:

```python
from icalendar import Calendar
cal = Calendar.from_ical(ics_text)
for component in cal.walk('VEVENT'):
    summary = str(component.get('SUMMARY', ''))
    dtstart = component.get('DTSTART')  # vDate or vDatetime
    rrule = component.get('RRULE')      # vRecur dict
    attendees = component.get('ATTENDEE', [])  # vCalAddress list
    # etc.
```

Key extraction patterns:
- `DTSTART.dt` — returns `datetime` or `date` object. `isinstance(dt, date) and not isinstance(dt, datetime)` → all-day event.
- `DTSTART.params.get('TZID')` → timezone string
- `RRULE.to_ical().decode()` → RRULE string (already RFC 5545 format, strip "RRULE:" prefix if present)
- `ATTENDEE` — `vCalAddress` with `str(attendee)` → `mailto:user@example.com`. `attendee.params.get('PARTSTAT')` → response status.
- `VALARM` — nested component. `TRIGGER.dt` → timedelta. Convert to minutes.
- `CATEGORIES` — `component.get('CATEGORIES')` returns list or vText. May need `.to_ical().decode()` and split on comma.

For **generation** (push-back / event creation):
```python
from icalendar import Calendar, Event as iEvent, vText, vDatetime
cal = Calendar()
event = iEvent()
event.add('summary', title)
event.add('dtstart', start_datetime)
# ... all properties
cal.add_component(event)
ics_bytes = cal.to_ical()
```

### Build Order

**S01: Auth + CalDAV Client + Calendar Discovery** `risk:high`
- HTTP Basic auth (URL + username + password storage)
- CalDAVClient with PROPFIND/REPORT/PUT/DELETE
- Well-known discovery chain
- Calendar list via PROPFIND
- Connect UI with credential form and calendar checkboxes
- **Proves:** CalDAV protocol works through SDK's HttpClient, discovery chain navigable, credentials stored
- **Risk:** WebDAV XML handling, server compatibility differences (Fastmail vs Nextcloud vs Radicale may differ in discovery responses)

**S02: Pull Sync + Field Mapping + Person Matching** `risk:medium`
- iCalendar parsing with `icalendar` library
- Field mapper (VEVENT → bpkm:Event properties)
- sync-collection REPORT with sync-token
- Two-phase bulk create (same as Google/Outlook)
- Person matcher (mailto: extraction → SPARQL email lookup)
- Settings UI (sync direction, poll interval, Sync Now)
- **Proves:** Full pull pipeline works, iCalendar fields map correctly, incremental sync

**S03: Push Sync + Bidirectional Write** `risk:medium`
- RSVP push-back via PUT (change ATTENDEE PARTSTAT)
- Full event create via PUT (generate .ics from bpkm:Event properties)
- ETag-based optimistic concurrency (If-Match header)
- Loop prevention (lastSyncedAt comparison, same as Google/Outlook)
- **Proves:** Bidirectional sync works, ETag conflicts handled

**S04: E2E Tests + User Guide + Docs** `risk:low`
- Mock CalDAV server (returns canned XML/ICS responses)
- Playwright E2E test (install → configure → sync → verify → push)
- Chapter 39 user guide
- README TOC, glossary, appendix A env vars

### Verification Approach

**Unit tests:** Import app modules via importlib (same pattern as M016-M020). Mock SDK clients. Test all field mapper transforms, sync engine phases, auth helpers, CalDAV XML generation/parsing.

**Mock CalDAV server:** Standalone Python HTTP server responding to PROPFIND/REPORT/PUT/DELETE with canned XML and .ics responses. Selftest to verify mock correctness. Docker service for E2E testing.

**E2E test:** Playwright test following the 7-phase pattern from M020:
1. Install app via admin
2. Configure credentials (point at mock server)
3. Select calendars
4. Trigger sync
5. Verify events via SPARQL
6. Modify event (RSVP)
7. Verify push-back

## Constraints

- **SDK HttpClient domain enforcement:** The manifest `network` permissions must list the CalDAV server domain. Since CalDAV servers are user-configured (any domain), the manifest should use `*` wildcard or the SDK needs to support dynamic domain addition. Check whether `*` is supported by `fnmatch` in the SDK's permission enforcement — if not, this is a blocker that needs a platform change.
- **No standard push mechanism:** Polling only (same as Google/Outlook). Apple push notifications are proprietary and out of scope per CONTEXT.
- **htmx URL prefix:** All template htmx URLs must use `/app/caldav-calendar/` prefix per the knowledge base entry about app template proxy routing.
- **IRI prefix bypass:** Bulk commands must bypass SDK's CommandClient IRI prefix checking (same pattern as D204 used by all sync apps).
- **sync-collection REPORT support:** Some very old or minimal CalDAV servers may not support sync-collection. Fallback to full PROPFIND + GET would be needed. For v1, assume sync-collection support (Fastmail, Nextcloud, Synology, Radicale all support it).

## Common Pitfalls

- **WebDAV XML namespaces:** CalDAV uses multiple XML namespaces (`DAV:`, `urn:ietf:params:xml:ns:caldav`, `http://calendarserver.org/ns/`). Every PROPFIND/REPORT request must declare the correct namespaces. Missing namespace declarations cause cryptic 400 errors from servers.
- **iCalendar timezone handling:** `DTSTART` can be a `date` (all-day), `datetime` with TZID (localized), or `datetime` with UTC suffix Z. The `icalendar` library normalizes these but the extraction code must handle all three forms.
- **ATTENDEE as list or single value:** When there's one attendee, `component.get('ATTENDEE')` returns a single `vCalAddress`, not a list. Must normalize to always iterate.
- **RRULE as vRecur object:** The `icalendar` library returns RRULE as a `vRecur` dict-like object. Use `.to_ical().decode()` to get the string, or iterate the dict keys to build the RRULE string manually. The `.to_ical()` output includes the `RRULE:` prefix which must be stripped.
- **ETag quoting:** ETags in HTTP headers are enclosed in double quotes per RFC 7232. Some CalDAV servers return strong ETags (`"abc"`), others return weak ETags (`W/"abc"`). The If-Match header must include the quotes.
- **PUT requires full VCALENDAR:** Unlike REST API PATCH, CalDAV PUT replaces the entire .ics resource. For RSVP push-back, we must fetch the current .ics, modify the ATTENDEE PARTSTAT, and PUT the complete modified VCALENDAR back.
- **Calendar home set discovery varies:** Fastmail, Nextcloud, and Radicale return slightly different XML structures for the discovery chain. Test against multiple servers or use the mock server to cover variants.
- **VALARM TRIGGER format:** Can be a negative timedelta (`-PT15M` = 15 minutes before) or a positive one. The `icalendar` library returns a `timedelta` — convert to absolute minutes.

## Open Risks

- **SDK network permission wildcard (`*`):** The manifest needs to permit HTTP requests to user-configured CalDAV server URLs. If `fnmatch` in the SDK's HttpClient domain enforcement doesn't support `*` as a catch-all, the app can't connect to arbitrary CalDAV servers. This would require either a platform change (allow apps to declare `"*"` for network access) or a per-install permission grant. **Investigate early in S01.**
- **Server compatibility:** CalDAV implementations vary. Fastmail is well-behaved but Nextcloud has known quirks (non-standard properties, different discovery paths). Radicale is minimal. Testing against real servers (not just mock) would increase confidence but is out of scope for automated E2E. Document known server-specific notes.
- **Self-signed certificates:** Self-hosted CalDAV servers (Nextcloud, Radicale, Synology) may use self-signed TLS certificates. The SDK's HttpClient (httpx) will reject these by default. May need a "verify SSL" toggle in settings. Low priority for v1 but worth noting.

## Candidate Requirements

Based on CONTEXT.md scope and the integration domain mapping, these are the requirements for M021:

| ID | Requirement | Type | Notes |
|---|---|---|---|
| CDAV-01 | CalDAV authentication (HTTP Basic + optional OAuth 2.0) | core | Primary: Basic auth with URL/username/password. Secondary: OAuth 2.0 for Google CalDAV, enterprise. |
| CDAV-02 | CalDAV discovery (well-known URLs, PROPFIND chain) | core | Multi-step discovery: .well-known → principal → calendar-home → calendar list |
| CDAV-03 | Calendar list and selection UI | core | PROPFIND Depth:1 on calendar home, checkboxes, persist selection |
| CDAV-04 | Pull sync (VEVENT → bpkm:Event) with iCalendar field mapping | core | ~20 field transforms, direct RRULE passthrough, all-day detection, VALARM→minutes |
| CDAV-05 | Incremental sync via sync-collection REPORT with sync-token | core | Efficient delta sync, 410 recovery to full sync |
| CDAV-06 | Attendee resolution (mailto: → Person matching) | core | Extract email from mailto: URI, SPARQL lookup, create-on-miss |
| CDAV-07 | RSVP push-back via PUT (ATTENDEE PARTSTAT modification) | core | Fetch current .ics → modify PARTSTAT → PUT with If-Match |
| CDAV-08 | Event create/update/delete via PUT/DELETE with ETag concurrency | core | Full .ics generation from bpkm:Event properties |
| CDAV-09 | Settings UI (sync direction, poll interval, Sync Now) | core | Same pattern as Google/Outlook settings |
| CDAV-10 | E2E tests + user guide Chapter 39 | quality | Mock CalDAV server, Playwright E2E, docs |

**Not included (out of scope per CONTEXT.md):**
- VTODO, VJOURNAL, VFREEBUSY support
- Apple push notifications
- Calendar sharing/ACL management
- Real-time push (no standard CalDAV mechanism)

## Sources

- iCalendar field mapping from `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §7 (CalDAV/iCalendar → bpkm:Event)
- Cross-provider field coverage matrix from same doc §8
- CalDAV protocol: RFC 4791 (CalDAV), RFC 5545 (iCalendar), RFC 6578 (sync-collection REPORT)
- Existing sync app implementations: `apps/google-calendar/` (M018), `apps/outlook-calendar/` (M020)
- App Platform SDK patterns: D204 (IRI prefix bypass), D179 (prefix enforcement scope), knowledge base entry on htmx URL proxy prefix
