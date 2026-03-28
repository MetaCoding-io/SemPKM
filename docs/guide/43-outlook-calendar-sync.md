# Chapter 43: Outlook Calendar Sync

The **Outlook Calendar Sync** app connects your Microsoft Outlook Calendar to SemPKM, synchronizing events as `bpkm:Event` objects. It supports **pull sync** (import Outlook events into SemPKM), **RSVP push-back** (send your response status changes back to Outlook), and **bidirectional** mode that does both.

Once configured, the app polls your selected calendars on a schedule you choose, creating and updating Event objects automatically. It uses Microsoft Graph **delta queries** for efficient incremental polling — after the first full sync, only changed events are fetched. Each synced event carries its full set of properties — times, time zone, location, attendees, conference links, recurrence rules, categories, and a link back to the original event in Outlook.

---

## Prerequisites

Before installing Outlook Calendar Sync, ensure:

1. **Basic PKM model is installed.** Outlook Calendar Sync creates `bpkm:Event` objects, which require the Basic PKM model v2.1 or later. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed" and version ≥2.1.0. If not, install or refresh it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **An Azure AD app registration with OAuth 2.0 credentials.** You need:
   - An Azure account with access to the [Azure Portal](https://portal.azure.com)
   - An **App Registration** in Azure Active Directory
   - An **Application (client) ID** and **Client Secret**
   - A **Redirect URI** configured for your SemPKM instance

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/outlook-calendar
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Setting Up Azure AD

Outlook Calendar Sync uses **OAuth 2.0** via the Microsoft Identity Platform to access your calendars securely. You never share your Microsoft password with SemPKM — instead, you grant scoped permission through Microsoft's consent screen.

### Creating an App Registration

1. Go to the [Azure Portal](https://portal.azure.com).
2. Navigate to **Azure Active Directory > App registrations**.
3. Click **+ New registration**.
4. Give it a name (e.g., "SemPKM Calendar Sync").
5. Under **Supported account types**, select "Accounts in any organizational directory and personal Microsoft accounts" (the `/common/` endpoint).
6. Under **Redirect URI**, select **Web** and enter:
   ```
   http://localhost:4000/app/outlook-calendar/_fragments/oauth-callback
   ```
   > **Important:** Replace `http://localhost:4000` with your actual SemPKM base URL if deployed remotely. The path `/app/outlook-calendar/_fragments/oauth-callback` must match exactly.
7. Click **Register**.

### Creating a Client Secret

1. On your new app registration's page, navigate to **Certificates & secrets**.
2. Under **Client secrets**, click **+ New client secret**.
3. Enter a description (e.g., "SemPKM") and choose an expiration period.
4. Click **Add**.
5. **Copy the secret value immediately** — it is only shown once. You'll need this in the next step along with the **Application (client) ID** from the app's Overview page.

### API Permissions

The app requests the following scopes during the OAuth flow:

- `Calendars.ReadWrite` — read and write access to calendar events
- `offline_access` — enables refresh token issuance for background sync

These scopes are requested dynamically at consent time via the `/common/` authorization endpoint. No manual API permission configuration is required in the Azure Portal unless your organization's admin has restricted consent.

---

## Connecting Your Account

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "Outlook Calendar" under the Apps section
- **Admin > Applications** — click the Outlook Calendar card, then click the settings link

### Entering Credentials

1. In the app's connect form, enter your **Application (client) ID** and **Client Secret** from the Azure Portal.
2. Click **Connect with Microsoft**.
3. You'll be redirected to Microsoft's OAuth consent screen. Review the requested permissions and click **Accept**.
4. Microsoft redirects you back to SemPKM with an authorization code. The app exchanges this code for access and refresh tokens automatically.

On success, the page updates to show:

- A **Connected** status badge
- Your **Microsoft email address** (fetched via the Graph API to verify the token works)
- A **Disconnect** button

If connection fails:

- Verify the Application (client) ID and Client Secret are correct.
- Check that the redirect URI in your Azure app registration matches exactly: `{APP_BASE_URL}/app/outlook-calendar/_fragments/oauth-callback`.
- Ensure the account type supports personal Microsoft accounts if you're using one.

### Token Refresh

Access tokens expire after approximately one hour. The app automatically refreshes them using the stored refresh token before making API calls. A 5-minute buffer ensures tokens are refreshed proactively, preventing mid-sync failures. If refresh fails (e.g., the user revoked access or the client secret expired), the connection status changes and you'll need to reconnect.

---

## Selecting Calendars

After connecting, you'll see a list of your Outlook calendars with checkboxes.

1. **Check the boxes** next to the calendars you want to sync events from.
2. Your **default calendar** is auto-detected and labeled.
3. Click **Save Calendars**.

Only events from selected calendars are synced. You can change the selection at any time — new calendars are included in the next sync cycle, and deselected calendars stop syncing (existing synced events remain in SemPKM).

---

## Sync Configuration

Below the calendar selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Outlook → SemPKM. Events are imported but changes in SemPKM are not sent back. |
| **Bidirectional** | Outlook ↔ SemPKM. Events are imported, and local RSVP status changes are pushed back to Outlook. |

> **Note:** Push-back is scoped to **RSVP status changes only** (accepted, declined, tentative, needs-action). Other event properties like title, time, and location are never pushed from SemPKM to Outlook. See [RSVP Push-Back](#rsvp-push-back) for details.

### Poll Interval

How often the app checks Outlook Calendar for updated events:

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
| **Updated** | Existing synced events updated with changes from Outlook |
| **Unchanged** | Events that had no changes since the last sync |
| **Errors** | Number of individual events that failed to sync |

### Incremental Sync via Delta Queries

Outlook Calendar Sync uses Microsoft Graph's **delta query** protocol. After the first full sync, subsequent syncs request only events that changed since the last sync, using a `deltaLink`. This dramatically reduces API calls and processing time for large calendars.

If the `deltaLink` becomes invalid (e.g., after an extended period without syncing), Microsoft returns a `410 Gone` error. The app automatically falls back to a full resync — no manual intervention needed.

---

## Field Mapping

When importing an Outlook Calendar event, the app maps fields to `bpkm:Event` properties as follows:

### Core Properties

| Outlook Graph Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `subject` | `dcterms:title` | Direct (defaults to "(No title)") | ← only |
| `body.content` | Body content | HTML → Markdown via markdownify; plain text passed through | ← only |
| `start.dateTime` | `schema:startDate` | ISO-8601 dateTime | ← only |
| `end.dateTime` | `schema:endDate` | ISO-8601 dateTime | ← only |
| `start.timeZone` | `bpkm:timeZone` | IANA timezone identifier | ← only |
| `isAllDay` | `bpkm:allDay` | `"true"` for all-day, `"false"` for timed | ← only |
| `location.displayName` | `bpkm:location` | Direct | ← only |
| `webLink` | `bpkm:externalUrl` | Direct URL to event in Outlook | ← only |
| `id` | `bpkm:externalId` | Microsoft Graph opaque event identifier | ← only |
| `iCalUId` | *(IRI slug)* | Used in SHA-256 hash for deterministic Event IRI | ← only |
| `createdDateTime` | `dcterms:created` | ISO-8601 dateTime | ← only |
| `lastModifiedDateTime` | `dcterms:modified` | ISO-8601 dateTime | ← only |

### Status and Visibility

Outlook has no single `status` field like Google Calendar. The event status is derived from multiple fields:

| Outlook Graph Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `isCancelled` | `bpkm:eventStatus` | `true` → `"cancelled"` | ← only |
| `responseStatus.response` | `bpkm:eventStatus` | `"tentativelyAccepted"` → `"tentative"`; all others → `"confirmed"` | ← only |
| `sensitivity` | `bpkm:visibility` | See sensitivity mapping table below | ← only |
| `responseStatus.response` | `bpkm:responseStatus` | See response status table below | ↔ |

#### Sensitivity → Visibility Mapping

| Outlook `sensitivity` | SemPKM `bpkm:visibility` |
|---|---|
| `normal` | *(omitted)* |
| `personal` | *(omitted)* |
| `private` | `private` |
| `confidential` | `confidential` |

#### showAs Mapping

| Outlook `showAs` | SemPKM `bpkm:showAs` |
|---|---|
| `free` | `free` |
| `tentative` | `tentative` |
| `busy` | `busy` |
| `oof` | `out-of-office` |
| `workingElsewhere` | `working-elsewhere` |

### Recurrence

Outlook represents recurring events using a structured **recurrence object** with separate `pattern` and `range` sub-objects, rather than the RFC 5545 RRULE strings used by most calendar systems. The app converts all 18 combinations (6 pattern types × 3 range types) into standard RRULE strings.

#### Pattern Types

| Outlook `pattern.type` | RRULE `FREQ` | Additional Components |
|---|---|---|
| `daily` | `FREQ=DAILY` | — |
| `weekly` | `FREQ=WEEKLY` | `BYDAY=MO,WE,FR` (from `daysOfWeek`) |
| `absoluteMonthly` | `FREQ=MONTHLY` | `BYMONTHDAY=15` (from `dayOfMonth`) |
| `relativeMonthly` | `FREQ=MONTHLY` | `BYDAY=2TU` (from `index` + `daysOfWeek`) |
| `absoluteYearly` | `FREQ=YEARLY` | `BYMONTH=3;BYMONTHDAY=15` (from `month` + `dayOfMonth`) |
| `relativeYearly` | `FREQ=YEARLY` | `BYMONTH=11;BYDAY=-1TH` (from `month` + `index` + `daysOfWeek`) |

#### Range Types

| Outlook `range.type` | RRULE Component |
|---|---|
| `endDate` | `UNTIL=20261231T000000Z` (from `endDate`) |
| `numbered` | `COUNT=10` (from `numberOfOccurrences`) |
| `noEnd` | *(no terminator — rule repeats indefinitely)* |

#### Relative Index Mapping

For `relativeMonthly` and `relativeYearly` patterns, the `index` field maps to an RRULE positional prefix:

| Outlook `index` | RRULE Position |
|---|---|
| `first` | `1` (e.g., `1MO` = first Monday) |
| `second` | `2` |
| `third` | `3` |
| `fourth` | `4` |
| `last` | `-1` (e.g., `-1FR` = last Friday) |

The `INTERVAL` component is added when `pattern.interval` is greater than 1 (e.g., every 2 weeks → `INTERVAL=2`).

### Attendees

| Outlook Graph Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `attendees[].emailAddress.address` | `bpkm:attendee` edges | Each attendee resolved to Person/Contact via SPARQL | ← only |
| `attendees[].status.response` | `bpkm:responseStatus` | See response status mapping below | ← only |

#### Response Status Mapping

| Outlook `response` | SemPKM `bpkm:responseStatus` |
|---|---|
| `none` | `needs-action` |
| `organizer` | `accepted` |
| `tentativelyAccepted` | `tentative` |
| `accepted` | `accepted` |
| `declined` | `declined` |
| `notResponded` | `needs-action` |

### Categories

| Outlook Graph Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `categories[]` | `bpkm:tags` | Comma-joined (e.g., `"Work,Important"`) | ← only |

### Conference URL

| Outlook Graph Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `onlineMeeting.joinUrl` | `bpkm:conferenceUrl` | Direct; fallback to `onlineMeetingUrl` | ← only |

### Sync Metadata

| Field | SemPKM Property | Value | Direction |
|---|---|---|---|
| *(calendar name)* | `bpkm:calendarName` | Human-readable name of source calendar | ← only |
| *(constant)* | `bpkm:externalProvider` | Always `"outlook-calendar"` | ← only |
| *(sync timestamp)* | `bpkm:lastSyncedAt` | ISO-8601 UTC timestamp of sync run | internal |

---

## RSVP Push-Back

When sync direction is set to **Bidirectional**, the app pushes RSVP status changes back to Outlook after each pull sync.

### How It Works

1. The app queries SemPKM for Event objects with `externalProvider: "outlook-calendar"` that have a changed `bpkm:responseStatus` since the last sync.
2. For each changed event, it reverse-maps the SemPKM status back to Outlook's format.
3. A `PATCH` request updates the authenticated user's attendee entry on the Outlook event via the Graph API at `/v1.0/me/calendars/{calendarId}/events/{eventId}`.

### Reverse RSVP Status Mapping

| SemPKM `bpkm:responseStatus` | Outlook `response` |
|---|---|
| `needs-action` | `notResponded` |
| `accepted` | `accepted` |
| `declined` | `declined` |
| `tentative` | `tentativelyAccepted` |

> **Note:** The `organizer` response status has no reverse mapping — you cannot set yourself as organizer via RSVP push-back.

### Scope Limitation

Push-back is deliberately limited to RSVP status only. Event title, time, location, description, and other properties are **never** pushed from SemPKM to Outlook. This keeps the sync safe — your Outlook Calendar remains the system of record for event details, while SemPKM captures your response intent.

### Loop Prevention

When the app pushes a status change to Outlook, it updates the event's `bpkm:lastSyncedAt` timestamp. On the next pull cycle, the app compares the event's modification timestamp against `lastSyncedAt` — if the change originated from the push, it's skipped. This prevents infinite sync loops.

---

## Recurrence Handling

Outlook represents recurring events differently from most calendar systems. Instead of an RFC 5545 RRULE string, Outlook uses a **structured recurrence object** with separate `pattern` and `range` sub-objects.

### How Conversion Works

The field mapper's `convert_recurrence_to_rrule` function handles all 18 combinations of pattern type × range type. For example, an Outlook recurrence like:

```json
{
  "pattern": {
    "type": "weekly",
    "interval": 1,
    "daysOfWeek": ["monday", "wednesday", "friday"]
  },
  "range": {
    "type": "endDate",
    "endDate": "2026-12-31"
  }
}
```

Becomes the RRULE string: `FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20261231T000000Z`

### relativeMonthly and relativeYearly

These pattern types combine an `index` (first, second, third, fourth, last) with a day of the week. The `index` maps to an RRULE positional prefix in the `BYDAY` component. For example, "second Tuesday of every month" becomes `FREQ=MONTHLY;BYDAY=2TU`, and "last Friday of November" becomes `FREQ=YEARLY;BYMONTH=11;BYDAY=-1FR`.

> **Note:** SemPKM does **not** expand recurring events into individual instances. The master event represents the entire series. Individual occurrences are only synced if Outlook has explicit data for them (i.e., they've been individually modified as exception instances).

---

## All-Day Events

Outlook Calendar marks all-day events with `isAllDay: true`. Unlike Google Calendar (which uses separate `date` vs `dateTime` fields), Outlook always provides `start.dateTime` and `end.dateTime` — for all-day events these are set to midnight-to-midnight.

| Event Type | `isAllDay` | SemPKM `schema:startDate` | `bpkm:allDay` |
|---|---|---|---|
| Timed | `false` | `xsd:dateTime` | `"false"` |
| All-day | `true` | `xsd:date` (date portion extracted) | `"true"` |

The `bpkm:allDay` flag makes it easy to filter all-day events in SPARQL queries and views without checking the datatype of `schema:startDate`.

---

## Conference URLs

Outlook Calendar events can include video conference links from Microsoft Teams, Zoom, and other providers via the `onlineMeeting` field.

The app extracts conference URLs in priority order:

1. **onlineMeeting.joinUrl** — the primary meeting join URL (Teams, Zoom, etc.) stored as `bpkm:conferenceUrl`.
2. **onlineMeetingUrl** — fallback field for legacy or third-party meeting links.

Both Microsoft Teams (`https://teams.microsoft.com/...`) and third-party video links (Zoom, Google Meet) are captured when present.

---

## Attendee Resolution

When an event includes attendees, Outlook Calendar Sync resolves each attendee to a SemPKM Person or Contact object:

1. **Email match** — queries the knowledge graph for existing Person or Contact objects with a matching email address (via `foaf:mbox` or `crm:email`).
2. **Create on miss** — if no match is found, creates a new Person object with the attendee's email and display name.
3. **Edge creation** — creates a `bpkm:attendee` edge from the Event to the resolved Person.

An in-memory LRU cache ensures each email is looked up only once per sync run, even if the same person appears on many events.

---

## HTML Body Conversion

Outlook Calendar event bodies can be either HTML or plain text, indicated by the `body.contentType` field:

- **HTML bodies** — converted to Markdown using the `markdownify` library, preserving formatting like headings, links, and lists. If `markdownify` is not available, HTML tags are stripped to plain text as a fallback.
- **Plain text bodies** — passed through as-is.

Empty or whitespace-only bodies are omitted from the Event object.

---

## Admin Monitoring

The **Admin > Applications > Outlook Calendar** detail page provides operational visibility:

- **Status badge** — Running (green), Stopped (gray), or Error (red)
- **Uptime** — How long the app has been running since last start
- **PID** — Process identifier for the app subprocess
- **Restart count** — How many times the app has been restarted

### Task History

The detail page shows scheduled task execution history. Outlook Calendar Sync registers background tasks:

| Task ID | Description | Default Interval |
|---|---|---|
| `poll-events` | Poll Outlook Calendar for updated events and sync to SemPKM | 15 minutes |
| `push-changes` | Push local RSVP changes back to Outlook | 15 minutes |

Each task run shows its timestamp, duration, and success/failure status.

---

## Troubleshooting

### OAuth redirect URI mismatch

If connecting fails with a redirect error, verify the redirect URI in your Azure app registration matches exactly:

```
{APP_BASE_URL}/app/outlook-calendar/_fragments/oauth-callback
```

Common mistakes: trailing slash mismatch, `http` vs `https`, wrong port number, missing `/app/outlook-calendar` prefix.

### Expired client secret

Azure AD client secrets have an expiration date. If sync stops working and reconnecting fails, check whether your client secret has expired in **Azure Portal > App registrations > [your app] > Certificates & secrets**. Create a new secret and re-enter it in the app's connect form.

### Token refresh failure

If sync stops working after a period of inactivity, the refresh token may have been revoked. Go to [Microsoft Account > App permissions](https://account.live.com/consent/Manage) (personal accounts) or the Azure AD admin portal (organization accounts) and check whether SemPKM still has access. If not, disconnect and reconnect through the app settings.

### Empty sync (no events imported)

If a sync completes but creates 0 events:

- Verify at least one calendar is selected in the calendar selection form.
- Check that the selected calendars actually contain events in the synced time range.
- Ensure the OAuth token has `Calendars.ReadWrite` scope — if consent was incomplete, the Graph API may return empty results.

### 410 Gone (full resync)

When a delta link expires (typically after an extended period without sync), Microsoft returns `410 Gone`. The app automatically triggers a full resync. You may see a temporary increase in created/updated counts — this is expected. No data is lost.

### Rate limiting

Microsoft Graph API has throttling limits. If you sync many calendars with many events, you may hit rate limits (HTTP 429). The app respects `Retry-After` headers. Symptoms include slower sync runs. Increase the poll interval to reduce API usage.

### App shows "Error" status

- Go to **Admin > Applications** and click the Outlook Calendar card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `outlook_calendar` entries.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Event type)
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `OUTLOOK_API_URL`, `OUTLOOK_TOKEN_URL`, and `OUTLOOK_AUTH_URL` overrides

---

**Previous:** [Chapter 42: Todoist Sync](42-todoist-sync.md) | **Next:** [Chapter 44: CalDAV Calendar Sync](44-caldav-calendar-sync.md)
