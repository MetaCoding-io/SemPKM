# Chapter 42: Todoist Sync

The **Todoist Sync** app connects [Todoist](https://todoist.com) tasks to SemPKM, synchronizing them as `bpkm:Task` objects. It supports **pull sync** (import Todoist tasks into SemPKM), **push sync** (close, reopen, and update tasks bidirectionally), and **bidirectional** mode that does both.

Once configured, the app polls selected Todoist projects on a schedule you choose, creating and updating Task objects automatically. Each synced task carries its priority, status, labels, due date, assignee, and a link back to the original task in Todoist.

---

## Prerequisites

Before installing Todoist Sync, ensure:

1. **Basic PKM model is installed.** Todoist Sync creates `bpkm:Task` objects, which require the Basic PKM model. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed". If not, install it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A Todoist Personal API Token.** You need a Todoist account and a Personal API Token:
   - Open [Todoist](https://todoist.com) and sign in.
   - Go to **Settings → Integrations → Developer**.
   - Copy your **API token** from the Developer section.

   > **Note:** Todoist uses a single long-lived API token per account. There is no OAuth flow and no scoping — the token grants full access to all projects and tasks in the account.

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/todoist-sync
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Connecting to Todoist

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "Todoist Sync" under the Apps section
- **Admin > Applications** — click the Todoist Sync card, then click the settings link

### Authentication

Todoist Sync uses **Personal API Tokens only** — there is no OAuth flow. This keeps the setup simple: paste your token and go.

| Method | Status | Notes |
|--------|--------|-------|
| Personal API Token | Available | Single long-lived token per Todoist account |
| OAuth App | Not available | Not implemented — PAT covers all use cases for single-user setups |

### Connecting via API Token

1. Generate an API token in Todoist (see [Prerequisites](#prerequisites) above).
2. In the Todoist Sync settings page, paste the token into the **Token** field.
3. Click **Connect**.

On success, the page updates to show:

- A **Connected** status badge
- Your **project count** (fetched via `GET /rest/v2/projects` to verify the token works)
- A masked preview of the token
- A list of **Todoist projects** available to the token
- **Sync configuration** options

If connection fails, verify the token is valid. Todoist API tokens do not expire, but they can be regenerated (which invalidates the old one). Check that your SemPKM instance can reach `api.todoist.com` over HTTPS.

---

## Selecting Projects

After connecting, you'll see a list of your Todoist projects with checkboxes.

1. **Check the boxes** next to the projects you want to sync tasks from.
2. Click **Save Selection**.

Only tasks from selected projects are synced. You can change the selection at any time — new projects are included in the next sync cycle, and deselected projects stop syncing (existing synced tasks remain in SemPKM).

---

## Sync Configuration

Below the project selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Todoist → SemPKM. Tasks are imported but changes in SemPKM are not sent back. |
| **Bidirectional** | Todoist ↔ SemPKM. Tasks are imported, and local task changes are pushed back to Todoist. |

### Poll Interval

How often the app checks Todoist for updated tasks:

| Interval | Best For |
|----------|----------|
| Every 10 minutes | Active task management where you need near-real-time sync |
| Every 30 minutes | Default — good balance of freshness and API usage |
| Every hour | Lower-activity projects |
| Every 6 hours | Background archival, minimal API calls |
| Every 24 hours | Daily snapshots only |

Click **Save Config** after making changes.

---

## Manual Sync

Don't want to wait for the next scheduled poll? Click **Sync Now** to trigger an immediate sync. The button shows a syncing indicator while the operation runs, then refreshes the page with updated stats.

Manual sync runs the same logic as the scheduled poll — it imports new and updated tasks from selected projects, and (in bidirectional mode) pushes local changes to Todoist.

---

## Understanding Sync Stats

After at least one sync has run, the **Sync Status** section shows:

### Last Sync Time

The UTC timestamp of the most recent sync operation.

### Pull Results

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `success`, `partial` (some tasks failed), or `error` |
| **Created** | New tasks imported as SemPKM Task objects for the first time |
| **Updated** | Existing synced tasks updated with changes from Todoist |
| **Unchanged** | Tasks that had no changes since the last sync |
| **Errors** | Number of individual tasks that failed to sync |

### Push Results

Shown only when sync direction is "Bidirectional":

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `success` or `error` |
| **Pushed** | Tasks whose local changes were sent to Todoist |
| **Closed** | Tasks marked done in SemPKM and closed in Todoist |
| **Reopened** | Tasks reopened in SemPKM and reopened in Todoist |
| **Updated** | Tasks with non-status field changes pushed to Todoist |
| **Skipped** | Tasks with no local changes, or changes that originated from Todoist (loop prevention) |
| **Errors** | Number of tasks that failed to push |

---

## Field Mapping

When importing a Todoist task, the app maps fields to `bpkm:Task` properties as follows:

| Todoist Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `content` (title) | `dcterms:title` | Direct | ↔ |
| `description` | Body content | Direct (Markdown) | ← only |
| `is_completed` | `bpkm:taskStatus` | See status mapping below | ↔ |
| `priority` | `bpkm:priority` | See priority mapping below | ↔ |
| `labels[]` | `bpkm:tags` | Label names as tags | ↔ |
| `due.date` / `due.datetime` | `bpkm:dueDate` | See due date handling below | ↔ |
| `assignee_id` | `bpkm:assignedTo` | Resolved to Person IRI | ← only |
| `id` | `bpkm:externalId` | Todoist task ID string | ← only |
| `url` | `bpkm:externalUrl` | Direct link to task in Todoist | ← only |
| *(constant)* | `bpkm:externalProvider` | Always `"todoist"` | ← only |
| *(sync timestamp)* | `bpkm:lastSyncedAt` | ISO-8601 UTC timestamp of sync run | internal |

### Priority Mapping

Todoist uses an **inverted priority scale** — in the Todoist UI, "Priority 1" (red flag) is the most urgent, but in the REST API this is represented as `priority: 4`. SemPKM normalizes this to conventional priority labels:

| Todoist API `priority` | Todoist UI Label | SemPKM `bpkm:priority` |
|---|---|---|
| 1 | Priority 4 (no flag) | `low` |
| 2 | Priority 3 (blue flag) | `medium` |
| 3 | Priority 2 (orange flag) | `high` |
| 4 | Priority 1 (red flag) | `critical` |

> **Important:** The mapping is between Todoist's **API** value and SemPKM's label. Todoist's API `priority: 4` corresponds to what users see as "Priority 1" in the Todoist UI. The app handles this inversion transparently — you work with `low`, `medium`, `high`, and `critical` in SemPKM, and the correct Todoist priority is set automatically during push sync.

### Status Mapping

Todoist tasks are either **active** or **completed**. The `is_completed` boolean maps to SemPKM's richer status model:

#### Pull Direction (Todoist → SemPKM)

| `is_completed` | SemPKM `bpkm:taskStatus` |
|---|---|
| `false` | `todo` |
| `true` | `done` |

#### Push Direction (SemPKM → Todoist)

| SemPKM `bpkm:taskStatus` | Todoist Action |
|---|---|
| `todo` | Reopen task (`POST /tasks/{id}/reopen`) |
| `in-progress` | Reopen task (keep active) |
| `done` | Close task (`POST /tasks/{id}/close`) |
| `cancelled` | Close task |
| `blocked` | Reopen task (keep active) |

> **Note:** Unlike GitHub Sync and Linear Sync which use `PATCH` to update a status field, Todoist uses **dedicated close and reopen endpoints**. This is a Todoist API design choice — there is no `status` field to PATCH. See [Push Sync](#push-sync) for details.

### Due Dates

Todoist supports both date-only and date-time due dates:

| Todoist `due` field | SemPKM `bpkm:dueDate` | Datatype |
|---|---|---|
| `due.date` (e.g., `"2025-03-15"`) | `2025-03-15` | `xsd:date` |
| `due.datetime` (e.g., `"2025-03-15T14:00:00Z"`) | `2025-03-15T14:00:00Z` | `xsd:dateTime` |
| No `due` field | Property omitted | — |

When a Todoist task has a `due.datetime` value, it takes precedence over `due.date`. If neither is present, the `bpkm:dueDate` property is not set on the SemPKM task.

### Labels

Todoist labels are passed through directly as `bpkm:tags` array entries. Each label name becomes a tag string:

- Todoist labels: `["work", "urgent", "client-project"]`
- SemPKM tags: `["work", "urgent", "client-project"]`

Labels sync bidirectionally — tags added in SemPKM are pushed back as Todoist labels when sync direction is bidirectional.

### External Link

The `url` field from Todoist is stored as `bpkm:externalUrl`, providing a direct link back to the task in the Todoist web interface. This appears in the object's property panel and can be clicked to jump to the original task.

### Sync Metadata

Each synced task carries internal metadata for tracking:

| Property | Purpose |
|---|---|
| `bpkm:externalId` | Todoist task ID — used to match tasks across sync cycles |
| `bpkm:externalProvider` | Always `"todoist"` — identifies the sync source |
| `bpkm:lastSyncedAt` | ISO-8601 timestamp of the last sync that touched this task — used for loop prevention |

---

## Push Sync

When sync direction is set to **Bidirectional**, the app runs a push cycle after each pull. During a push cycle:

1. The app queries SemPKM for tasks with `externalProvider: "todoist"` that have been modified since the last sync (comparing `dcterms:modified` against `bpkm:lastSyncedAt`).
2. For each modified task, it detects what changed and builds the appropriate API calls.
3. Changes are sent to Todoist via the REST API.

### Close/Reopen Pattern

Todoist's API does not have a generic status field that can be set via `PATCH`. Instead, it provides **dedicated endpoints** for completing and reopening tasks:

- **Close:** `POST /rest/v2/tasks/{id}/close` — marks the task as completed
- **Reopen:** `POST /rest/v2/tasks/{id}/reopen` — marks the task as active again

When a task's status changes in SemPKM (e.g., from `todo` to `done`), the app calls the appropriate endpoint first, then sends any other field updates via `POST /rest/v2/tasks/{id}`.

This differs from GitHub Sync (which PATCHes `state: "closed"`) and Linear Sync (which PATCHes `stateId`). If you're familiar with those apps, the key difference is that Todoist status changes are **separate API calls**, not fields on an update payload.

### Supported Push Fields

| SemPKM Property | Todoist Field | Notes |
|---|---|---|
| `bpkm:taskStatus` | Close / Reopen | Via dedicated endpoints (see above) |
| `dcterms:title` | `content` | Direct mapping |
| `bpkm:priority` | `priority` | Reverse-mapped through priority table |
| `bpkm:tags` | `labels` | Direct mapping |
| `bpkm:dueDate` | `due_date` / `due_datetime` | Based on datatype |

### Loop Prevention

When the app pushes a change to Todoist, it updates the task's `bpkm:lastSyncedAt` timestamp. On the next pull cycle, the app compares the task's modification time against `lastSyncedAt` — if the remote update is older or equal, the update is skipped. This prevents infinite sync loops where a push triggers a pull triggers a push.

---

## Assignee Resolution

When a Todoist task has an assignee, the app resolves the assignee to a SemPKM Person object by:

1. Matching the assignee's **email** against existing Person or Contact objects in the knowledge graph.
2. Falling back to matching the **name** (via `bpkm:externalId`).
3. Creating a new Person object if no match is found.

An in-memory LRU cache ensures each assignee is looked up only once per sync run.

---

## Admin Monitoring

The **Admin > Applications > Todoist Sync** detail page provides operational visibility:

- **Status badge** — Running (green), Stopped (gray), or Error (red)
- **Uptime** — How long the app has been running since last start
- **PID** — Process identifier for the app subprocess
- **Restart count** — How many times the app has been restarted

### Task History

The detail page shows scheduled task execution history. Todoist Sync registers two background tasks:

| Task ID | Description | Default Interval |
|---|---|---|
| `poll-tasks` | Poll Todoist for updated tasks and sync to SemPKM | 30 minutes |
| `push-changes` | Push local task changes back to Todoist | 30 minutes |

Each task run shows its timestamp, duration, and success/failure status. Failed task runs include error messages that help diagnose sync issues.

---

## Troubleshooting

### "Not connected" after entering token

- Verify the API token is valid — go to **Settings → Integrations → Developer** in Todoist and check the token.
- If you regenerated the token, the old one is invalidated. Paste the new token and reconnect.
- Check that your SemPKM instance can reach `api.todoist.com` over HTTPS.
- If running behind a corporate firewall, ensure outbound HTTPS to `api.todoist.com` is allowed.

### No projects appearing after connecting

- The token grants access to all projects in your Todoist account. If no projects appear, check that your Todoist account has at least one project.
- Try disconnecting and reconnecting with a fresh token.

### No tasks appearing after sync

- Verify at least one project is selected and saved.
- Check the Sync Status section — if it shows 0 created/updated, the selected projects may have no tasks.
- Run a manual sync and check the stats for errors.
- Confirm the Basic PKM model is installed (the Task type must exist).

### Push changes not reflected in Todoist

- Verify sync direction is set to **Bidirectional** (not "Pull only").
- Check the push stats — if "Pushed" is 0, no local changes were detected.
- Ensure you edited the task in SemPKM (not just viewed it) — only actual property changes trigger a push.
- Only tasks that were originally pulled from Todoist can be pushed back. Tasks created natively in SemPKM are not pushed to Todoist.

### App shows "Error" status

- Go to **Admin > Applications** and click the Todoist Sync card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `todoist` entries.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Task type)
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `TODOIST_API_URL` override for testing

---

**Previous:** [Chapter 41: Google Calendar Sync](41-google-calendar-sync.md) | **Next:** [Chapter 43: Outlook Calendar Sync](43-outlook-calendar-sync.md)
