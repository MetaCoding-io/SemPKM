# Chapter 34: Linear Sync

The **Linear Sync** app connects [Linear](https://linear.app) project management to SemPKM, synchronizing issues as `bpkm:Task` objects. It supports **pull sync** (import Linear issues into SemPKM), **push sync** (send SemPKM task changes back to Linear), and **bidirectional** mode that does both.

Once configured, the app polls Linear on a schedule you choose, creating and updating Task objects automatically. Each synced task carries its Linear identifier, status, priority, assignee, labels, and a link back to the original issue.

---

## Prerequisites

Before installing Linear Sync, ensure:

1. **Basic PKM model is installed.** Linear Sync creates `bpkm:Task` objects, which require the Basic PKM model. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed". If not, install it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A Linear account with API access.** You need a Linear workspace and permission to create API keys (any member role works).

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/linear-sync
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Connecting to Linear

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "Linear Sync" under the Apps section
- **Admin > Applications** — click the Linear Sync card, then click the settings link

### Authentication Methods

| Method | Status | Best For |
|--------|--------|----------|
| API Key | Available | Personal use, single-user setups |
| OAuth | Not yet available | Multi-user, team deployments |

### Connecting via API Key

1. In Linear, go to **Settings → API → Personal API keys** (or visit [linear.app/settings/api](https://linear.app/settings/api)).
2. Click **Create key**, give it a name (e.g., "SemPKM Sync"), and copy the generated key (starts with `lin_api_`).
3. In the Linear Sync settings page, paste the key into the **API Key** field.
4. Click **Connect**.

On success, the page updates to show:

- A **Connected** status badge with the authentication method
- Your **workspace name**
- A list of **teams** in the workspace
- **Sync configuration** options

If connection fails, verify the API key is valid and hasn't been revoked. The key must have read access to issues (the default for personal API keys).

---

## Selecting Teams

After connecting, you'll see a list of all teams in your Linear workspace.

1. **Check the boxes** next to the teams you want to sync issues from.
2. Click **Save Teams**.

Only issues from selected teams are synced. You can change the team selection at any time — new teams are included in the next sync cycle, and deselected teams stop syncing (existing synced tasks remain in SemPKM).

---

## Sync Configuration

Below the team selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Linear → SemPKM. Issues are imported as tasks but changes in SemPKM are not sent back. |
| **Bidirectional** | Linear ↔ SemPKM. Issues are imported, and local task edits are pushed back to Linear. |

### Poll Interval

How often the app checks Linear for updated issues:

| Interval | Best For |
|----------|----------|
| Every 5 minutes | Active sprint work where you need near-real-time sync |
| Every 15 minutes | Default — good balance of freshness and API usage |
| Every 30 minutes | Lower-activity projects |
| Every hour | Background archival, minimal API calls |

Click **Save Config** after making changes.

---

## Manual Sync

Don't want to wait for the next scheduled poll? Click **Sync Now** to trigger an immediate sync. The button shows a "Syncing…" indicator while the operation runs, then refreshes the page with updated stats.

Manual sync runs the same logic as the scheduled poll — it imports new and updated issues from selected teams, and (in bidirectional mode) pushes local changes to Linear.

---

## Understanding Sync Stats

After at least one sync has run, the **Sync Status** section shows:

### Last Sync Time

The UTC timestamp of the most recent sync operation.

### Pull Results

| Stat | Meaning |
|------|---------|
| **Created** | New issues imported as SemPKM tasks for the first time |
| **Updated** | Existing synced tasks updated with changes from Linear |
| **Unchanged** | Issues checked but no changes detected since last sync |

### Push Results

Shown only when sync direction is "Bidirectional":

| Stat | Meaning |
|------|---------|
| **Pushed** | Tasks whose local changes were sent to Linear |
| **Skipped** | Tasks with no local changes, or changes that originated from Linear (loop prevention) |

### Errors

If any issues failed to sync, an error count appears. Check the Admin detail page (see [Admin Monitoring](#admin-monitoring) below) for error details.

---

## Field Mapping

When importing a Linear issue, the app maps fields to `bpkm:Task` properties as follows:

| Linear Field | SemPKM Property | Notes |
|---|---|---|
| `title` | `dcterms:title` | Direct mapping |
| `description` | Body (Markdown) | Stored as the object's Markdown body, not a property |
| `state.type` | `bpkm:taskStatus` | See status mapping table below |
| `priority` (0–4) | `bpkm:priority` | See priority mapping table below |
| `assignee.email` | `bpkm:assignedTo` | Matched by email to existing Person objects |
| `labels` | `bpkm:tags` | Each label name becomes a tag entry |
| `dueDate` | `bpkm:dueDate` | ISO date (date portion only) |
| `completedAt` | `bpkm:completedDate` | Set only when state.type is "completed" |
| `estimate` | `bpkm:effort` | Mapped to named sizes (see effort mapping below) |
| `url` | `bpkm:externalUrl` | Link back to the Linear issue |
| `identifier` | `bpkm:externalId` | The human-readable issue key, e.g., "ENG-123" |
| `id` | `bpkm:externalUuid` | Linear's internal UUID |

### Status Mapping

| Linear `state.type` | SemPKM `bpkm:taskStatus` |
|---|---|
| `backlog` | `todo` |
| `unstarted` | `todo` |
| `started` | `in-progress` |
| `completed` | `done` |
| `cancelled` | `cancelled` |

Unrecognized state types default to `todo`.

### Priority Mapping

| Linear Priority | SemPKM `bpkm:priority` |
|---|---|
| 0 (No priority) | *(omitted)* |
| 1 (Urgent) | `critical` |
| 2 (High) | `high` |
| 3 (Medium) | `medium` |
| 4 (Low) | `low` |

### Effort Mapping

| Linear Estimate | SemPKM `bpkm:effort` |
|---|---|
| 0 | *(omitted)* |
| 1 | `trivial` |
| 2 | `small` |
| 3 | `medium` |
| 5 | `large` |
| 8 | `epic` |

Estimate values not in the table above are stored as their numeric string (e.g., "13").

---

## Push Sync

When sync direction is set to **Bidirectional**, the app runs a push cycle on the same schedule as the pull. During a push cycle:

1. The app queries SemPKM for tasks that have been modified since the last push.
2. For each modified task, it builds an update payload from the current property values.
3. The update is sent to Linear via the GraphQL API.

### Supported Push Fields

| SemPKM Property | Linear Field | Notes |
|---|---|---|
| `bpkm:taskStatus` | `state` | Reverse-mapped to Linear workflow state (e.g., `todo` → `backlog`) |
| `bpkm:priority` | `priority` | Reverse-mapped to integer (e.g., `critical` → 1) |
| `dcterms:title` | `title` | Direct mapping |
| `bpkm:dueDate` | `dueDate` | Direct mapping |

### Loop Prevention

When the app pushes a change to Linear, it marks that task's sync direction as `push` and records the sync timestamp. On the next pull cycle, the app detects that the most recent change originated from a push and skips re-importing it. This prevents infinite sync loops where a push triggers a pull triggers a push.

---

## Admin Monitoring

The **Admin > Applications > Linear Sync** detail page provides operational visibility:

- **Status badge** — Running (green), Stopped (gray), or Error (red)
- **Uptime** — How long the app has been running since last start
- **PID** — Process identifier for the app subprocess
- **Restart count** — How many times the app has been restarted

### Task History

The detail page also shows scheduled task execution history. Linear Sync registers two background tasks:

| Task ID | Description | Default Interval |
|---|---|---|
| `poll-tasks` | Poll Linear for updated issues and sync to SemPKM | 15 minutes |
| `push-changes` | Push local task changes back to Linear | 15 minutes |

Each task run shows its timestamp, duration, and success/failure status. Failed task runs include error messages that help diagnose sync issues.

---

## Troubleshooting

### "Not connected" after entering API key

- Verify the API key is valid and not revoked — regenerate it in Linear if unsure.
- Check that your SemPKM instance can reach `api.linear.app` over HTTPS.
- Look for error messages on the connection form — they appear in a red banner at the top.

### No tasks appearing after sync

- Verify at least one team is selected and saved.
- Check the Sync Status section — if it shows 0 created/updated/unchanged, the query returned no issues.
- Run a manual sync and check the stats for errors.
- Confirm the Basic PKM model is installed (the Task type must exist).

### Push changes not reflected in Linear

- Verify sync direction is set to **Bidirectional** (not "Pull only").
- Check the push stats — if "Pushed" is 0, no local changes were detected.
- Ensure you edited the task in SemPKM (not just viewed it) — only actual property changes trigger a push.
- The API key must have write access to issues.

### App shows "Error" status

- Go to **Admin > Applications** and click the Linear Sync card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `linear-sync` entries.

### Sync is slow or missing recent changes

- Reduce the poll interval (e.g., from 1 hour to 15 minutes).
- Use **Sync Now** for immediate results.
- Note that the first sync imports all issues from selected teams, which may take longer than incremental syncs.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Task type)
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `LINEAR_API_URL` and `LINEAR_TOKEN_URL` overrides

---

**Previous:** [Chapter 33: Context Overlay](33-context-overlay.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
