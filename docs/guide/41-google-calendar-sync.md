# Chapter 41: Google Calendar Sync

The **Google Calendar Sync** app connects your Google Calendar to SemPKM, synchronizing events as `bpkm:Event` objects. It supports **pull sync** (import Google Calendar events into SemPKM), **RSVP push-back** (send your response status changes back to Google), and **bidirectional** mode that does both.

Once configured, the app polls your selected calendars on a schedule you choose, creating and updating Event objects automatically. Each synced event carries its full set of properties — times, time zone, location, attendees, conference links, recurrence rules, and a link back to the original event in Google Calendar.

---

## Prerequisites

Before installing Google Calendar Sync, ensure:

1. **Basic PKM model is installed.** Google Calendar Sync creates `bpkm:Event` objects, which require the Basic PKM model v2.1 or later. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed" and version ≥2.1.0. If not, install or refresh it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A Google Cloud Console project with OAuth 2.0 credentials.** You need:
   - A project in the [Google Cloud Console](https://console.cloud.google.com/)
   - The **Google Calendar API** enabled for that project
   - An **OAuth 2.0 Client ID** of type "Web application"

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/google-calendar
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Setting Up OAuth

Google Calendar Sync uses **OAuth 2.0** to access your calendars securely. You never share your Google password with SemPKM — instead, you grant scoped permission through Google's consent screen.

### Creating OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select or create a project.
3. Navigate to **APIs & Services > Library** and enable the **Google Calendar API**.
4. Navigate to **APIs & Services > Credentials**.
5. Click **+ CREATE CREDENTIALS > OAuth client ID**.
6. Select **Web application** as the application type.
7. Give it a name (e.g., "SemPKM Calendar Sync").
8. Under **Authorized redirect URIs**, add:
   ```
   http://localhost:4000/app/google-calendar/_fragments/oauth-callback
   ```
   > **Important:** Replace `http://localhost:4000` with your actual SemPKM base URL if deployed remotely. The path `/app/google-calendar/_fragments/oauth-callback` must match exactly.
9. Click **Create**.
10. Copy the **Client ID** and **Client Secret** — you'll need both in the next step.

### OAuth Scope

The app requests the `https://www.googleapis.com/auth/calendar.events` scope, which allows reading and writing event data. It does **not** request full calendar management, calendar deletion, or access to other Google services.

---

## Connecting to Google

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "Google Calendar" under the Apps section
- **Admin > Applications** — click the Google Calendar card, then click the settings link

### Entering Credentials

1. In the app's connect form, enter your **Client ID** and **Client Secret** from the Google Cloud Console.
2. Click **Connect with Google**.
3. You'll be redirected to Google's OAuth consent screen. Review the requested permissions and click **Allow**.
4. Google redirects you back to SemPKM with an authorization code. The app exchanges this code for access and refresh tokens automatically.

On success, the page updates to show:

- A **Connected** status badge
- Your **Google email address** (fetched via the Calendar API to verify the token works)
- A **Disconnect** button

If connection fails:

- Verify the Client ID and Client Secret are correct.
- Check that the redirect URI in your Google Cloud Console matches exactly: `{APP_BASE_URL}/app/google-calendar/_fragments/oauth-callback`.
- Ensure the Google Calendar API is enabled for your project.

### Token Refresh

Access tokens expire after one hour. The app automatically refreshes them using the stored refresh token before making API calls. A 5-minute buffer ensures tokens are refreshed proactively, preventing mid-sync failures. If refresh fails (e.g., the user revoked access), the connection status changes and you'll need to reconnect.

---

## Selecting Calendars

After connecting, you'll see a list of your Google calendars with checkboxes.

1. **Check the boxes** next to the calendars you want to sync events from.
2. Your **primary calendar** is auto-detected and labeled.
3. Click **Save Calendars**.

Only events from selected calendars are synced. You can change the selection at any time — new calendars are included in the next sync cycle, and deselected calendars stop syncing (existing synced events remain in SemPKM).

---

## Sync Configuration

Below the calendar selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Google → SemPKM. Events are imported but changes in SemPKM are not sent back. |
| **Bidirectional** | Google ↔ SemPKM. Events are imported, and local RSVP status changes are pushed back to Google. |

> **Note:** Push-back is scoped to **RSVP status changes only** (accepted, declined, tentative, needs-action). Other event properties like title, time, and location are never pushed from SemPKM to Google. See [RSVP Push-Back](#rsvp-push-back) for details.

### Poll Interval

How often the app checks Google Calendar for updated events:

| Interval | Best For |
|----------|----------|
| Every 5 minutes | Active scheduling where you need near-real-time sync |
| Every 15 minutes | Default — good balance of freshness and API usage |
| Every 30 minutes | Lower-activity calendars |
| Every hour | Background archival, minimal API calls |

Click **Save Config** after making changes.

---

## Running a Sync

Don't want to wait for the next scheduled poll? Click **Sync Now** to trigger an immediate sync. The button shows a "Syncing…" indicator while the operation runs, then refreshes the page with updated stats.

After at least one sync has run, the **Sync Status** section shows:

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `success`, `partial` (some events failed), or `error` |
| **Created** | New events imported as SemPKM Event objects for the first time |
| **Updated** | Existing synced events updated with changes from Google |
| **Unchanged** | Events that had no changes since the last sync |
| **Errors** | Number of individual events that failed to sync |

### Incremental Sync via syncToken

Google Calendar Sync uses Google's **incremental sync** protocol. After the first full sync, subsequent syncs request only events that changed since the last sync, using a `syncToken`. This dramatically reduces API calls and processing time for large calendars.

If the `syncToken` becomes invalid (e.g., after 7+ days without syncing), Google returns a `410 Gone` error. The app automatically falls back to a full resync — no manual intervention needed.

---

## Field Mapping

When importing a Google Calendar event, the app maps fields to `bpkm:Event` properties as follows:

### Core Properties

| Google Calendar Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `summary` | `dcterms:title` | Direct (defaults to "(No title)") | ← only |
| `description` | Body content | HTML tags stripped to plain text | ← only |
| `start.dateTime` | `schema:startDate` | ISO-8601 dateTime | ← only |
| `end.dateTime` | `schema:endDate` | ISO-8601 dateTime | ← only |
| `start.date` (all-day) | `schema:startDate` | ISO-8601 date (xsd:date) | ← only |
| `end.date` (all-day) | `schema:endDate` | ISO-8601 date (xsd:date) | ← only |
| `start.timeZone` | `bpkm:timeZone` | IANA timezone identifier | ← only |
| `created` | `dcterms:created` | ISO-8601 dateTime | ← only |
| `updated` | `dcterms:modified` | ISO-8601 dateTime | ← only |

### Status and Visibility

| Google Calendar Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `status` | `bpkm:eventStatus` | confirmed / tentative / cancelled (1:1) | ← only |
| `visibility` | `bpkm:visibility` | public / private / confidential ("default" omitted) | ← only |
| `transparency` | `bpkm:showAs` | opaque → busy, transparent → free | ← only |
| self `responseStatus` | `bpkm:responseStatus` | camelCase → kebab-case (see RSVP table) | ↔ |

### Location and Links

| Google Calendar Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `location` | `bpkm:location` | Direct | ← only |
| `htmlLink` | `bpkm:externalUrl` | Direct URL to event in Google Calendar | ← only |
| `id` | `bpkm:externalId` | Google's opaque event identifier | ← only |
| `iCalUID` | *(IRI slug)* | Used in SHA-256 hash for deterministic Event IRI | ← only |

### Conference and Reminders

| Google Calendar Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `conferenceData.entryPoints[video]` | `bpkm:conferenceUrl` | First video entry point URI; `hangoutLink` fallback | ← only |
| `reminders.overrides[0].minutes` | `bpkm:reminderMinutes` | First override reminder as string | ← only |

### Recurrence

| Google Calendar Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `recurrence[]` | `bpkm:recurrenceRule` | First RRULE entry, prefix stripped | ← only |
| `recurringEventId` | `bpkm:recurringEventId` | Links instance to master event | ← only |

### Attendees and Organizer

| Google Calendar Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `attendees[].email` | `bpkm:attendee` edges | Each attendee resolved to Person object | ← only |
| `organizer.email` | `bpkm:organizer` edge | Resolved to Person object | ← only |
| self attendee `responseStatus` | `bpkm:responseStatus` | needsAction→needs-action, accepted→accepted, declined→declined, tentative→tentative | ↔ |

### Sync Metadata

| Google Calendar Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| *(calendar name)* | `bpkm:calendarName` | Human-readable name of source calendar | ← only |
| *(constant)* | `bpkm:externalProvider` | Always `"google-calendar"` | ← only |
| *(constant)* | `bpkm:allDay` | `"true"` for all-day, `"false"` for timed | ← only |
| *(sync timestamp)* | `bpkm:lastSyncedAt` | ISO-8601 UTC timestamp of sync run | internal |

---

## RSVP Push-Back

When sync direction is set to **Bidirectional**, the app pushes RSVP status changes back to Google Calendar after each pull sync.

### How It Works

1. The app queries SemPKM for Event objects with `externalProvider: "google-calendar"` that have a changed `bpkm:responseStatus` since the last sync.
2. For each changed event, it reverse-maps the SemPKM status back to Google's format.
3. A `PATCH` request updates only the authenticated user's attendee entry on the Google event.

### RSVP Status Mapping

| SemPKM `bpkm:responseStatus` | Google `responseStatus` |
|---|---|
| `needs-action` | `needsAction` |
| `accepted` | `accepted` |
| `declined` | `declined` |
| `tentative` | `tentative` |

### Scope Limitation

Push-back is deliberately limited to RSVP status only. Event title, time, location, description, and other properties are **never** pushed from SemPKM to Google. This keeps the sync safe — your Google Calendar remains the system of record for event details, while SemPKM captures your response intent.

### Loop Prevention

When the app pushes a status change to Google, it updates the event's `bpkm:lastSyncedAt` timestamp. On the next pull cycle, the app compares Google's `updated` timestamp against `lastSyncedAt` — if the change originated from the push, it's skipped. This prevents infinite sync loops.

---

## Recurrence Handling

Google Calendar represents recurring events as a **master event** plus optional **exception instances**.

### Master Events

A recurring event (e.g., "Weekly Team Standup, every Monday at 10am") is stored as a single Event object in SemPKM with a `bpkm:recurrenceRule` property containing the RRULE (e.g., `FREQ=WEEKLY;BYDAY=MO`). The RRULE prefix is stripped — only the rule body is stored.

> **Note:** SemPKM does **not** expand recurring events into individual instances. The master event represents the entire series. Individual occurrences are only synced if Google has explicit data for them (i.e., they've been individually modified).

### Exception Instances

When you modify a single occurrence of a recurring event in Google Calendar (e.g., reschedule one standup), Google creates an exception instance. These are synced as separate Event objects in SemPKM, linked to the master via `bpkm:recurringEventId`.

---

## All-Day Events

Google Calendar distinguishes between timed events and all-day events at the API level:

| Event Type | `start` field | SemPKM `schema:startDate` | `bpkm:allDay` |
|---|---|---|---|
| Timed | `start.dateTime` (ISO-8601 with timezone) | `xsd:dateTime` | `"false"` |
| All-day | `start.date` (ISO-8601 date only) | `xsd:date` | `"true"` |

The `bpkm:allDay` flag makes it easy to filter all-day events in SPARQL queries and views without checking the datatype of `schema:startDate`.

---

## Conference URLs

Google Calendar events can include video conference links from Google Meet, Zoom, and other providers via the `conferenceData` field.

The app extracts conference URLs in priority order:

1. **conferenceData.entryPoints** — finds the first entry point with `entryPointType: "video"` and stores its URI as `bpkm:conferenceUrl`.
2. **hangoutLink** — if no video entry point exists, falls back to the legacy `hangoutLink` field (older Meet links).

Both Google Meet (`https://meet.google.com/...`) and third-party video links (Zoom, Teams) are captured when present in `conferenceData`.

---

## Attendee Resolution

When an event includes attendees, Google Calendar Sync resolves each attendee to a SemPKM Person or Contact object:

1. **Email match** — queries the knowledge graph for existing Person or Contact objects with a matching email address (via `foaf:mbox` or `crm:email`).
2. **Create on miss** — if no match is found, creates a new Person object with the attendee's email and display name.
3. **Edge creation** — creates a `bpkm:attendee` edge from the Event to the resolved Person. The organizer gets a `bpkm:organizer` edge instead.

An in-memory LRU cache ensures each email is looked up only once per sync run, even if the same person appears on many events.

---

## Admin Monitoring

The **Admin > Applications > Google Calendar** detail page provides operational visibility:

- **Status badge** — Running (green), Stopped (gray), or Error (red)
- **Uptime** — How long the app has been running since last start
- **PID** — Process identifier for the app subprocess
- **Restart count** — How many times the app has been restarted

### Task History

The detail page shows scheduled task execution history. Google Calendar Sync registers background tasks:

| Task ID | Description | Default Interval |
|---|---|---|
| `poll-events` | Poll Google Calendar for updated events and sync to SemPKM | 15 minutes |
| `push-changes` | Push local RSVP changes back to Google | 15 minutes |

Each task run shows its timestamp, duration, and success/failure status.

---

## Troubleshooting

### OAuth redirect URI mismatch

If connecting fails with a redirect error, verify the authorized redirect URI in your Google Cloud Console matches exactly:

```
{APP_BASE_URL}/app/google-calendar/_fragments/oauth-callback
```

Common mistakes: trailing slash mismatch, `http` vs `https`, wrong port number, missing `/app/google-calendar` prefix.

### Token refresh failure

If sync stops working after a period of inactivity, the refresh token may have been revoked. Go to [Google Account > Security > Third-party apps](https://myaccount.google.com/permissions) and check whether SemPKM still has access. If not, disconnect and reconnect through the app settings.

### 410 Gone (full resync)

When a `syncToken` expires (typically after 7+ days without sync), Google returns `410 Gone`. The app automatically triggers a full resync. You may see a temporary increase in created/updated counts — this is expected. No data is lost.

### Missing calendars

If calendars don't appear after connecting, verify the OAuth scope grants calendar access. The app requests `calendar.events` scope. If you're using a Google Workspace account, your administrator may need to allow the OAuth client in the admin console.

### Rate limiting

Google Calendar API has usage quotas. If you sync many calendars with many events, you may hit rate limits. Symptoms include partial sync results or error counts. Increase the poll interval to reduce API usage.

### App shows "Error" status

- Go to **Admin > Applications** and click the Google Calendar card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `google_calendar` entries.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Event type)
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `GCAL_API_URL` and `GOOGLE_TOKEN_URL` overrides

---

**Previous:** [Chapter 35: GitHub Sync](35-github-sync.md) | **Next:** [Chapter 42: Todoist Sync](42-todoist-sync.md)
