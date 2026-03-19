# S03: Pull sync + field mapping + settings — Research

**Date:** 2026-03-18

## Summary

S03 is the core value delivery slice — it turns authenticated Google Calendar connections (S02) into actual bpkm:Event objects in SemPKM. The work follows the established sync app pattern from Linear (M016) and GitHub (M017) exactly: field_mapper.py (pure functions), sync_engine.py (orchestration), person_matcher.py (reused pattern), plus settings UI and routes in app.py and templates. The bpkm:Event type (S01) provides 20 properties to map against the ~22 Google Calendar fields specified in INTEGRATION-DOMAIN-MAPPING.md §5.

The existing google-calendar app from S02 has: auth module (7 helpers), GCalClient (calendar list only), app.py (OAuth routes + skeleton task handlers for `poll-events` and `push-changes`), manifest, and templates. S03 needs to: (1) extend GCalClient with `get_events()` supporting syncToken and pagination, (2) build field_mapper.py with `build_event_properties()` covering all ~22 field transforms, (3) build sync_engine.py with `pull_sync()` using two-phase bulk create, (4) build person_matcher.py (copy from linear-sync, change type constant), (5) add settings UI (direction, poll interval, Sync Now) to connect_status.html, (6) wire task handlers and settings routes in app.py.

No unfamiliar technology — this is direct application of proven patterns to a new provider with a different data shape (Event vs Task).

## Recommendation

Follow the linear-sync and github-sync implementations line-for-line, adapting only the field mapping and API client methods. Build in this order:

1. **field_mapper.py first** — pure functions, no dependencies, easy to test exhaustively. This is where the domain complexity lives (all-day detection, timezone handling, visibility/transparency normalization, conference URL extraction, attendee self-detection for responseStatus, RRULE extraction, HTML description handling).
2. **person_matcher.py** — nearly identical to linear-sync's, just change the log namespace.
3. **GCalClient.get_events()** — extend existing client with events.list endpoint, syncToken support, and 410 Gone handling.
4. **sync_engine.py** — orchestrate field mapper + person matcher + client + bulk commands. Follow linear-sync's two-phase create pattern exactly.
5. **Settings UI + routes** — extend connect_status.html with direction/interval/Sync Now sections, add routes in app.py, wire task handlers.

## Implementation Landscape

### Key Files

**Existing (modify):**
- `apps/google-calendar/services/gcal_client.py` — Add `get_events(calendar_id, sync_token=None)` method with syncToken pagination, 410 Gone → full resync handling. Follow same `_request()` pattern as `get_calendar_list()`.
- `apps/google-calendar/app.py` — Replace skeleton `poll-events`/`push-changes` handlers with real implementations. Add settings routes (`/_fragments/settings/sync-config`, `/_fragments/sync-now`). Extend `_render_connect_status()` with sync config and stats context.
- `apps/google-calendar/frontend/templates/connect_status.html` — Add Sync Configuration section (direction radios, poll interval dropdown), Manual Sync section, and Sync Stats section. Copy structure from linear-sync's connect_status.html.
- `apps/google-calendar/frontend/static/styles.css` — Add styles for new settings sections (copy from linear-sync pattern).

**New (create):**
- `apps/google-calendar/services/field_mapper.py` — Pure field mapping functions. ~300 lines. Constants: `BPKM` prefix, `STATUS_MAP`, `RESPONSE_STATUS_MAP`, `VISIBILITY_MAP`, `TRANSPARENCY_MAP`. Functions: `build_event_properties(event, calendar_name, sync_time)`, `compute_event_slug(calendar_id, event_id)`, `extract_conference_url(event)`, `extract_response_status(event)`, `detect_all_day(event)`, `normalize_visibility(visibility)`, `normalize_transparency(transparency)`.
- `apps/google-calendar/services/sync_engine.py` — Pull sync orchestration. ~250 lines. Functions: `pull_sync(ctx)`, `_find_existing_event(graph_client, slug)`, `_build_create_command(slug, properties)`, `_build_update_commands(existing_iri, properties, description, attendee_iris, organizer_iri)`, `_submit_commands_batched(http_client, commands, summary, source)`.
- `apps/google-calendar/services/person_matcher.py` — Copy from linear-sync's person_matcher.py. Change logger name to `"google_calendar.person_matcher"`. Same SPARQL lookup, same create-on-miss, same LRU cache.
- `backend/tests/test_gcal_field_mapper.py` — Pure function tests. ~500 lines, ≥40 tests covering every field transform, edge case, and normalization.
- `backend/tests/test_gcal_sync_engine.py` — Async orchestration tests with mocked clients. ~600 lines, ≥30 tests covering pull_sync pipeline, two-phase create, syncToken handling, per-calendar state, error isolation.
- `backend/tests/test_gcal_person_matcher.py` — ~150 lines, ≥8 tests (same coverage as linear-sync pattern).

### Build Order

**T01: Field mapper (pure functions + tests).** Build `field_mapper.py` with all transforms and `test_gcal_field_mapper.py`. This is the largest body of domain logic and has zero dependencies on other S03 work. Test every transform path: all-day detection (start.date vs start.dateTime), timezone extraction, status/visibility/transparency normalization, conference URL extraction (conferenceData.entryPoints fallback to hangoutLink), attendee self-detection for responseStatus, RRULE extraction from recurrence array, HTML description stripping, reminder extraction, slug computation, externalProvider = "google-calendar".

**T02: Person matcher + GCalClient extension + sync engine + tests.** Build person_matcher.py (copy+adapt from linear-sync). Extend GCalClient with `get_events()`. Build sync_engine.py with `pull_sync()`. Write tests for all three. The sync engine depends on field_mapper (T01) and person_matcher, but the client extension and person_matcher are independently testable.

**T03: Settings UI + routes + task handler wiring.** Extend connect_status.html with sync config/stats sections. Add settings routes in app.py. Wire `poll-events` and `push-changes` task handlers to real sync engine calls. This is mostly UI and route plumbing — the logic is already built in T01/T02.

### Verification Approach

- `cd backend && .venv/bin/python -m pytest tests/test_gcal_field_mapper.py -v` — ≥40 pure function tests
- `cd backend && .venv/bin/python -m pytest tests/test_gcal_sync_engine.py -v` — ≥30 orchestration tests
- `cd backend && .venv/bin/python -m pytest tests/test_gcal_person_matcher.py -v` — ≥8 person matcher tests
- `cd backend && .venv/bin/python -m pytest -x` — full suite (currently 1498) must pass with zero regressions
- Jinja2 template syntax check for connect_status.html
- Verify all htmx URLs use `/app/google-calendar/` prefix (knowledge: App template htmx URLs must use proxy prefix)

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Person email matching | `PersonMatcher` from linear-sync | Proven SPARQL lookup + creation + LRU cache. Copy and adjust logger name. |
| Two-phase bulk create | `_submit_commands_batched` pattern from linear-sync sync_engine | Bypass SDK IRI prefix checks via direct `/api/commands/bulk` POST. |
| Slug computation | `hashlib.sha256` pattern from linear-sync field_mapper | Deterministic IRI slug from calendar_id + event_id. |
| Settings UI layout | linear-sync connect_status.html | Direction radios, poll interval dropdown, Sync Now button, stats panel — all templated. |
| HTML → plain text | Simple regex strip (`<[^>]+>`) or `re.sub` | Google Calendar descriptions CAN be HTML but often aren't. A lightweight strip is sufficient for v1 — no external dependency needed. A `strip_html_tags()` helper in field_mapper.py handles it. |

## Constraints

- **GCalClient.get_events() must support syncToken.** Google returns `nextSyncToken` on the last page of an events.list response. Store as `sync_token:{calendarId}` in StateClient. On 410 Gone, clear the token and do a full resync.
- **Per-calendar sync state.** Each selected calendar has its own syncToken. The sync engine must iterate over `selected_calendars` (JSON list from StateClient) and sync each independently.
- **Object properties use full IRIs.** The `BPKM` prefix constant is `"urn:sempkm:model:basic-pkm:"` — same as linear-sync. Event-specific properties: `{BPKM}eventStatus`, `{BPKM}location`, etc.
- **Shared properties reused from Task.** `bpkm:externalId`, `bpkm:externalUrl`, `bpkm:externalProvider`, `bpkm:lastSyncedAt`, `bpkm:syncDirection` are defined on Task in the ontology but usable on Events in RDF's open-world model. The S01 shapes also define these on EventShape.
- **externalProvider must be `"google-calendar"`** — not "google" or "gcal" (S01 forward intelligence).
- **startDate/endDate types.** Must write `xsd:dateTime` for timed events and `xsd:date` for all-day events. No shape validation will catch a type mismatch (S01 forward intelligence — shapes omit sh:datatype on these fields).
- **Attendee and organizer are ObjectProperties** → stored as edge.create commands to Person IRIs, not as string properties. The field mapper builds the properties dict; the sync engine handles edge creation separately.
- **`singleEvents=false`** on events.list query to get only master recurring events, not expanded instances. Individual exceptions have `recurringEventId` set.
- **Push handler remains skeleton.** S03 handles pull only. The `push-changes` task handler stays as a no-op placeholder for S04.
- **Bypass SDK CommandClient** for bulk commands — post directly to `/api/commands/bulk` via `ctx.commands._client` (same pattern as linear-sync/github-sync).

## Common Pitfalls

- **All-day event detection** — Google uses `start.date` (string, no time) for all-day events and `start.dateTime` for timed events. The field mapper must check for `start.date` first. If present, set `bpkm:allDay` to `"true"` (string, as xsd:boolean serialized in properties) and use the date value directly for `schema:startDate`.
- **Timezone handling** — `start.timeZone` is separate from `start.dateTime`. Store the dateTime as-is in `schema:startDate` (it's already ISO 8601 with offset) and store `start.timeZone` IANA identifier in `bpkm:timeZone`.
- **Attendee self-detection** — The user's own RSVP status is in `attendees[]` where `self: true`. Must find this specific entry for `bpkm:responseStatus`. Other attendees create edge.create commands to Person objects.
- **Conference URL extraction** — `conferenceData.entryPoints` is an array. Find the first with `entryPointType: "video"` and take its `uri`. Fall back to `hangoutLink` if `conferenceData` is absent or has no video entry point.
- **syncToken invalidation** — Google returns 410 Gone when a syncToken is too old. Must catch this (GCalAPIError with status_code 410), clear the stored syncToken for that calendar, and retry as a full sync.
- **HTML in description** — Google Calendar `description` field can contain HTML. Strip tags for body.set content. A simple regex `re.sub(r'<[^>]+>', '', text)` is sufficient for v1.
- **Visibility "default"** — Google's `visibility: "default"` means "use calendar default" (typically public). Omit the property rather than storing "default" (per design doc mapping).
- **Transparency → showAs** — Google's `transparency` field maps to `bpkm:showAs`: `opaque` → `busy`, `transparent` → `free`. Not a direct name match.
- **RRULE from recurrence array** — Google stores recurrence as `["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR", "EXDATE:..."]`. Extract the first string starting with `"RRULE:"` and strip the prefix. S03 stores this but doesn't handle exceptions — that's S04.
- **Reminder extraction** — `reminders.overrides` is an array. Take the first override's `minutes` value. If no overrides, use `reminders.useDefault` → store nothing (let the platform use its own default or omit the field).
- **MockResponse data pitfall** — Per Knowledge Pattern #2: use `data if data is not None else {}` not `data or {}` in test mocks, because `[] or {}` evaluates to `{}`.

## Open Risks

- **Description HTML complexity.** If Google Calendar descriptions contain complex HTML (tables, nested divs), the simple regex strip will produce poorly formatted text. Acceptable for v1 — a proper HTML→Markdown converter (markdownify) could be added later without changing the field mapper interface.
- **Large calendar initial sync.** A busy calendar with years of events could return thousands of events on first sync. Google paginates at 250/page (max 2500). The sync engine pages through all of them, which could hit the 500/100s/user rate limit. Acceptable for v1 — incremental syncs via syncToken are very efficient.

## Sources

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §5 — Complete Google Calendar → bpkm:Event field mapping with status/visibility/showAs normalization tables
- `apps/linear-sync/services/` — Reference implementation for field_mapper, sync_engine, person_matcher patterns
- `apps/github-sync/services/` — Second reference confirming the pattern
- S01 forward intelligence — Event property list, externalProvider enum value, startDate/endDate type constraints
- S02 forward intelligence — Auth module API, GCalClient construction pattern, StateClient key conventions
