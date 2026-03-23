# Chapter 44: CalDAV Calendar Sync

The **CalDAV Calendar Sync** app connects any CalDAV-compatible calendar server to SemPKM, synchronizing events as `bpkm:Event` objects. It supports **pull sync** (import calendar events into SemPKM), **RSVP push-back** (send your response status changes back to the server), and **bidirectional** mode that does both.

CalDAV is an open standard (RFC 4791) built on WebDAV (RFC 4918). Unlike proprietary APIs, CalDAV works with a wide range of calendar servers — Fastmail, Nextcloud, Synology Calendar, Radicale, and any other server that speaks the protocol. Authentication uses **HTTP Basic** credentials rather than OAuth, making setup straightforward: enter your server URL, username, and password.

Once configured, the app polls your selected calendars on a schedule you choose, creating and updating Event objects automatically. It uses the CalDAV **sync-collection REPORT** with **sync-tokens** for efficient incremental polling — after the first full sync, only changed events are fetched. Each synced event carries its full set of properties — times, time zone, location, attendees, recurrence rules, categories, and a link back to the original event.

---

## Prerequisites

Before installing CalDAV Calendar Sync, ensure:

1. **Basic PKM model is installed.** CalDAV Calendar Sync creates `bpkm:Event` objects, which require the Basic PKM model v2.1 or later. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed" and version ≥2.1.0. If not, install or refresh it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A CalDAV server with credentials.** You need:
   - A CalDAV server URL (see [Server-Specific Notes](#server-specific-notes) for common providers)
   - A username and password with calendar access
   - For self-hosted servers: network access from the SemPKM host to the CalDAV server

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/caldav-calendar
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Connecting Your Server

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "CalDAV Calendar" under the Apps section
- **Admin > Applications** — click the CalDAV Calendar card, then click the settings link

### Entering Credentials

1. Enter your **CalDAV server URL** — the base URL of your CalDAV server. See [Server-Specific Notes](#server-specific-notes) for URL patterns.
2. Enter your **Username** and **Password**.
3. Click **Connect**.

The app performs a **PROPFIND discovery chain** to verify the credentials work:

1. PROPFIND on the server URL → discovers `current-user-principal`
2. PROPFIND on the principal URL → discovers `calendar-home-set`
3. PROPFIND Depth:1 on the calendar home → lists available calendars

On success, the page updates to show:

- A **Connected** status badge
- Your **username** (confirming which account is connected)
- A **Disconnect** button

If connection fails:

- Verify the server URL is correct and accessible from the SemPKM host.
- Check that the username and password are correct.
- For self-hosted servers, ensure the CalDAV port is open and not blocked by a firewall.
- For servers behind HTTPS with self-signed certificates, see [Troubleshooting](#troubleshooting).

### Server URL Discovery

Most CalDAV servers support the `/.well-known/caldav` redirect (RFC 6764). If you're unsure of the exact URL, try entering the server's base domain — the app follows well-known redirects automatically. If that doesn't work, use the server-specific URL patterns listed in [Server-Specific Notes](#server-specific-notes).

---

## Selecting Calendars

After connecting, you'll see a list of your calendars with checkboxes. Only calendars that support VEVENT components are shown.

1. **Check the boxes** next to the calendars you want to sync events from.
2. Click **Save Calendars**.

Only events from selected calendars are synced. You can change the selection at any time — new calendars are included in the next sync cycle, and deselected calendars stop syncing (existing synced events remain in SemPKM).

---

## Sync Configuration

Below the calendar selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Server → SemPKM. Events are imported but changes in SemPKM are not sent back. |
| **Bidirectional** | Server ↔ SemPKM. Events are imported, and local RSVP status changes are pushed back to the server. |

> **Note:** Push-back is scoped to **RSVP status changes only** (accepted, declined, tentative, needs-action). Other event properties like title, time, and location are never pushed from SemPKM to the server. See [RSVP Push-Back](#rsvp-push-back) for details.

### Poll Interval

How often the app checks the CalDAV server for updated events:

| Interval | Best For |
|----------|----------|
| Every 5 minutes | Active scheduling where you need near-real-time sync |
| Every 15 minutes | Default — good balance of freshness and API usage |
| Every 30 minutes | Lower-activity calendars |
| Every hour | Background archival, minimal server load |

Click **Save Config** after making changes.

---

## Running a Sync

Don't want to wait for the next scheduled poll? Click **Sync Now** to trigger an immediate sync. The button shows a "Syncing…" indicator while the operation runs, then refreshes the page with updated stats.

After at least one sync has run, the **Sync Status** section shows:

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `success`, `partial` (some events failed), or `error` |
| **Created** | New events imported as SemPKM Event objects for the first time |
| **Updated** | Existing synced events updated with changes from the server |
| **Unchanged** | Events that had no changes since the last sync |
| **Errors** | Number of individual events that failed to sync |

### Incremental Sync via sync-collection

CalDAV Calendar Sync uses the **sync-collection REPORT** (RFC 6578) for incremental polling. After the first full sync (which uses a calendar-query REPORT to fetch all VEVENTs), subsequent syncs request only events that changed since the last sync, using a **sync-token**. This dramatically reduces network traffic and processing time for large calendars.

If the sync-token becomes invalid (e.g., the server has purged old change history), the server returns an error and the app automatically falls back to a full resync — no manual intervention needed.

---

## Field Mapping

When importing a CalDAV calendar event (iCalendar VEVENT), the app maps fields to `bpkm:Event` properties as follows:

### Core Properties

| iCalendar Property | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `SUMMARY` | `dcterms:title` | Direct (defaults to "(No title)") | ← only |
| `DESCRIPTION` | Body content | HTML tags stripped to plain text | ← only |
| `DTSTART` | `schema:startDate` | ISO-8601 date (all-day) or dateTime (timed) | ← only |
| `DTEND` | `schema:endDate` | ISO-8601 date (all-day) or dateTime (timed) | ← only |
| `DTSTART;TZID=` | `bpkm:timeZone` | IANA timezone identifier from TZID parameter | ← only |
| *(date vs datetime)* | `bpkm:allDay` | `"true"` if DTSTART is a date; `"false"` if dateTime | ← only |
| `LOCATION` | `bpkm:location` | Direct | ← only |
| `URL` | `bpkm:externalUrl` | Direct | ← only |
| `UID` | `bpkm:externalId` | iCalendar UID string | ← only |
| `UID` + calendar href | *(IRI slug)* | SHA-256 hash → `caldav-{hash12}` for deterministic Event IRI | ← only |
| `CREATED` | `dcterms:created` | ISO-8601 dateTime | ← only |
| `LAST-MODIFIED` | `dcterms:modified` | ISO-8601 dateTime | ← only |

### Status, Visibility, and Show-As

| iCalendar Property | SemPKM Property | Mapping | Direction |
|---|---|---|---|
| `STATUS` | `bpkm:eventStatus` | See status mapping table below | ← only |
| `CLASS` | `bpkm:visibility` | See class mapping table below | ← only |
| `TRANSP` | `bpkm:showAs` | See transparency mapping table below | ← only |

#### STATUS → eventStatus Mapping

| iCalendar `STATUS` | SemPKM `bpkm:eventStatus` |
|---|---|
| `TENTATIVE` | `tentative` |
| `CONFIRMED` | `confirmed` |
| `CANCELLED` | `cancelled` |

#### CLASS → visibility Mapping

| iCalendar `CLASS` | SemPKM `bpkm:visibility` |
|---|---|
| `PUBLIC` | `public` |
| `PRIVATE` | `private` |
| `CONFIDENTIAL` | `confidential` |

#### TRANSP → showAs Mapping

| iCalendar `TRANSP` | SemPKM `bpkm:showAs` |
|---|---|
| `OPAQUE` | `busy` |
| `TRANSPARENT` | `free` |

### Categories

| iCalendar Property | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `CATEGORIES` | `bpkm:tags` | Comma-separated values parsed to list | ← only |

### Attendees and Recurrence

| iCalendar Property | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `ATTENDEE` | `bpkm:attendee` edges | Each attendee resolved to Person/Contact via email match | ← only |
| `ATTENDEE;CN=` | *(display name)* | Used for Person creation if no email match | ← only |
| `ATTENDEE;PARTSTAT=` | `bpkm:responseStatus` | See PARTSTAT mapping below | ↔ |
| `ORGANIZER` | `bpkm:organizer` | Resolved to Person/Contact via email match | ← only |
| `RRULE` | `bpkm:recurrenceRule` | Native passthrough — RFC 5545 string stored as-is | ← only |
| `RECURRENCE-ID` | `bpkm:recurringEventId` | ISO-8601 date or dateTime | ← only |
| `VALARM` | `bpkm:reminderMinutes` | First VALARM trigger → positive integer minutes | ← only |

#### PARTSTAT → responseStatus Mapping

| iCalendar `PARTSTAT` | SemPKM `bpkm:responseStatus` |
|---|---|
| `NEEDS-ACTION` | `needs-action` |
| `ACCEPTED` | `accepted` |
| `DECLINED` | `declined` |
| `TENTATIVE` | `tentative` |

### Sync Metadata

| Field | SemPKM Property | Value | Direction |
|---|---|---|---|
| *(calendar name)* | `bpkm:calendarName` | Human-readable `displayname` of source calendar | ← only |
| *(constant)* | `bpkm:externalProvider` | Always `"caldav"` | ← only |
| *(sync timestamp)* | `bpkm:lastSyncedAt` | ISO-8601 UTC timestamp of sync run | internal |

---

## RSVP Push-Back

When sync direction is set to **Bidirectional**, the app pushes RSVP status changes back to the CalDAV server after each pull sync.

### How It Works

1. The app queries SemPKM for Event objects with `externalProvider: "caldav"` that have a changed `bpkm:responseStatus` since the last sync.
2. For each changed event, it **fetches the current .ics resource** from the server via GET, capturing the ETag.
3. It parses the VCALENDAR, locates the ATTENDEE entry matching your email address, and modifies the `PARTSTAT` parameter.
4. It **PUTs the modified VCALENDAR** back to the server with an `If-Match` header containing the captured ETag.

This is the standard CalDAV **fetch-modify-PUT** pattern for atomic updates.

### ETag Concurrency Control

The PUT request includes an `If-Match: <etag>` header. If another client modified the event between the GET and PUT, the server returns **412 Precondition Failed** and the push-back is skipped for that event (it will retry on the next sync cycle). This prevents data loss from concurrent edits.

### Reverse RSVP Status Mapping

| SemPKM `bpkm:responseStatus` | iCalendar `PARTSTAT` |
|---|---|
| `needs-action` | `NEEDS-ACTION` |
| `accepted` | `ACCEPTED` |
| `declined` | `DECLINED` |
| `tentative` | `TENTATIVE` |

### Scope Limitation

Push-back is deliberately limited to RSVP status only. Event title, time, location, description, and other properties are **never** pushed from SemPKM to the CalDAV server. This keeps the sync safe — your calendar server remains the system of record for event details, while SemPKM captures your response intent.

### Loop Prevention

When the app pushes a status change, it updates the event's `bpkm:lastSyncedAt` timestamp. On the next pull cycle, the app compares the event's modification timestamp against `lastSyncedAt` — if the change originated from the push, it's skipped. This prevents infinite sync loops.

---

## Recurrence Handling

CalDAV uses the standard RFC 5545 `RRULE` format for recurring events. Unlike Outlook Calendar Sync (which must convert structured recurrence objects into RRULE strings), CalDAV Calendar Sync performs a **native passthrough** — the RRULE is stored exactly as received from the iCalendar data, with no conversion needed.

### Examples

| RRULE | Meaning |
|---|---|
| `FREQ=WEEKLY;BYDAY=MO,WE,FR` | Every Monday, Wednesday, and Friday |
| `FREQ=MONTHLY;BYMONTHDAY=15` | The 15th of every month |
| `FREQ=YEARLY;BYMONTH=11;BYDAY=-1TH` | Last Thursday of November (US Thanksgiving) |
| `FREQ=DAILY;COUNT=10` | Daily for 10 occurrences |
| `FREQ=WEEKLY;INTERVAL=2;UNTIL=20261231T000000Z` | Every 2 weeks until end of 2026 |

> **Note:** SemPKM does **not** expand recurring events into individual instances. The master event represents the entire series. Individual occurrences are only synced if the server has explicit data for them (i.e., they've been individually modified as exception instances, identified by a `RECURRENCE-ID`).

---

## Server-Specific Notes

CalDAV Calendar Sync works with any standards-compliant CalDAV server, but each server has its own URL structure. Here are the patterns for popular providers:

### Fastmail

- **Server URL:** `https://caldav.fastmail.com/dav/calendars/user/{email}/`
- Replace `{email}` with your full Fastmail email address.
- Uses your Fastmail password or an app-specific password (recommended).

### Nextcloud

- **Server URL:** `https://{host}/remote.php/dav/calendars/{username}/`
- Replace `{host}` with your Nextcloud domain and `{username}` with your Nextcloud username.
- If you use two-factor authentication, generate an app-specific password in **Settings > Security > Devices & sessions**.

### Synology Calendar

- **Server URL:** `https://{nas-ip}:5001/caldav/{username}/`
- Replace `{nas-ip}` with your NAS IP address or hostname, and `{username}` with your Synology account.
- Uses port 5001 (HTTPS) by default. Adjust if you've changed the DSM port.

### Radicale

- **Server URL:** `http://{host}:5232/{username}/`
- Replace `{host}` with the machine running Radicale and `{username}` with the configured user.
- Default port is 5232. Radicale typically runs over HTTP locally — use HTTPS with a reverse proxy for remote access.

### Generic / Other Servers

If your server isn't listed above:

1. Check your server's documentation for the CalDAV base URL.
2. Try the server's base domain — the app follows `/.well-known/caldav` redirects (RFC 6764).
3. Enter the URL and the app performs the full PROPFIND discovery chain: server → principal → calendar-home → calendar list. If discovery succeeds, your URL works.

---

## Troubleshooting

### Connection fails with authentication error

- Verify your username and password are correct.
- Some servers (Fastmail, Nextcloud with 2FA) require **app-specific passwords** rather than your main account password. Check your server's security settings.
- Confirm the server URL is reachable from the SemPKM host: `curl -I {server_url}`.

### Self-signed certificates

If your CalDAV server uses a self-signed TLS certificate (common for self-hosted Nextcloud or Synology), the connection may fail with a certificate verification error. Options:

- Add the server's CA certificate to the SemPKM container's trust store.
- Use HTTP instead of HTTPS for local-network-only servers (less secure but functional).

### Empty calendar list after connecting

If the connection succeeds but no calendars appear:

- Verify your account has at least one calendar created on the server.
- Check that the calendars support VEVENT components (task-only or journal-only calendars are filtered out).
- Some servers require the exact calendar home URL rather than the server root — check [Server-Specific Notes](#server-specific-notes).

### Sync completes with 0 events

- Verify at least one calendar is selected in the calendar selection form.
- Check that the selected calendars actually contain events.
- Review the app logs via `docker compose logs api` and search for `caldav` entries.

### ETag conflict (412) during push-back

This means the event was modified on the server between the GET and PUT requests. The push-back is safely skipped and will retry on the next sync cycle. If this happens repeatedly, another client may be actively editing the same events. This is expected behavior — not a bug.

### App shows "Error" status

- Go to **Admin > Applications** and click the CalDAV Calendar card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `caldav` entries.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Event type)

---

**Previous:** [Chapter 38: Outlook Calendar Sync](38-outlook-calendar-sync.md) | **Next:** [Chapter 40: Asana Sync](40-asana-sync.md)
