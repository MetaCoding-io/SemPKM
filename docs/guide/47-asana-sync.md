# Chapter 47: Asana Sync

The **Asana Sync** app connects your Asana workspace to SemPKM, synchronizing tasks as `bpkm:Task` objects with **configurable field mapping** for status, priority, and story points. It supports **pull sync** (import tasks from Asana), **bidirectional sync** (push SemPKM changes back to Asana), and subtask nesting up to 5 levels deep.

Unlike previous sync apps that use fixed field mappings, Asana Sync lets you choose *how* task status is determined — via the built-in completed flag, a custom enum field, or project sections (board columns). Priority and story points are similarly configurable, mapping your team's custom fields directly to SemPKM properties.

Asana Sync is the seventh sync app in the SemPKM ecosystem, following Linear, GitHub, Google Calendar, Todoist, Outlook Calendar, and CalDAV Calendar.

---

## Prerequisites

Before installing Asana Sync, ensure:

1. **Basic PKM model is installed.** Asana Sync creates `bpkm:Task` objects (and `bpkm:Milestone` objects for Asana milestones), which require the Basic PKM model v2.0 or later. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed" and version ≥2.0.0. If not, install or refresh it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **An Asana account with project access.** You need either:
   - **OAuth app credentials** — a Client ID and Client Secret from the Asana Developer Console, or
   - **A Personal Access Token (PAT)** — generated in the Asana Developer Console

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/asana-sync
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Connecting Your Account

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "Asana Sync" under the Apps section
- **Admin > Applications** — click the Asana Sync card, then click the settings link

Asana Sync supports two authentication methods: OAuth 2.0 (recommended for teams) and Personal Access Token (simpler for individual use).

### Option A: OAuth 2.0

OAuth gives scoped access without exposing your password and supports automatic token refresh.

1. **Create an OAuth app** at the [Asana Developer Console](https://app.asana.com/0/my-apps):
   - Go to **My Apps > Create New App**.
   - Set the **Redirect URL** to:
     ```
     http://localhost:4000/app/asana-sync/_fragments/oauth-callback
     ```
     Adjust the host and port if your SemPKM instance runs elsewhere.
   - Copy the **Client ID** and **Client Secret**.

2. In SemPKM, enter your **Client ID** and **Client Secret** in the OAuth Credentials section and click **Save Credentials**.

3. Click **Connect with Asana**. You'll be redirected to Asana to authorize the app.

4. After authorization, you're redirected back to SemPKM. The status shows **Connected** with your Asana email address.

Tokens refresh automatically — you won't need to re-authorize unless you revoke access in Asana.

### Option B: Personal Access Token

A PAT is simpler to set up but gives full account access and doesn't auto-refresh.

1. Go to the [Asana Developer Console](https://app.asana.com/0/my-apps) → **Personal Access Tokens**.
2. Click **Create New Token**, give it a name, and copy the token (it starts with `0/`).
3. In SemPKM, paste the token into the **Access Token** field and click **Connect**.
4. The app verifies the token against the Asana API. On success, the status shows **Connected** with your email.

> **Note:** PATs do not expire automatically, but they have full access to your Asana account. Store them securely and revoke them in the Developer Console when no longer needed.

---

## Selecting Workspaces and Projects

After connecting, the settings page shows your Asana workspaces with their projects listed as checkboxes.

1. **Check the boxes** next to the projects you want to sync tasks from. Projects are grouped under their workspace headings.
2. Click **Save Projects**.

Only tasks from selected projects are synced. You can change the selection at any time — newly selected projects are included in the next sync, and deselected projects stop syncing (existing synced tasks remain in SemPKM).

---

## Discovering Custom Fields

Before configuring field mappings, the app needs to scan your selected projects for available custom fields.

1. Click **Discover Fields**.
2. The app queries the Asana API for custom field settings on each selected project, collecting:
   - **Enum fields** — dropdown fields with named options (used for status and priority mapping)
   - **Number fields** — numeric fields (used for story points)
   - **Sections** — board columns / list sections from each project (used for section-based status)
3. After discovery, the field mapping form appears with your available fields.

If you add new custom fields in Asana or change your project selection, click **Re-discover Fields** to refresh the list.

---

## Configuring Status Mapping

Status mapping is the core configuration decision for Asana Sync. You choose one of three modes that determines how each Asana task's status translates to `bpkm:taskStatus`.

### Mode 1: Completed Only

The simplest option. Uses Asana's built-in completed/incomplete flag:

| Asana State | SemPKM Status |
|-------------|---------------|
| Completed (✓) | `done` |
| Incomplete | `todo` |

Best for teams that don't use custom status fields or boards — just mark tasks complete when they're finished.

### Mode 2: Custom Field

Maps an enum custom field's values to SemPKM statuses. For example, if your Asana project has a "Status" dropdown with values like "Not Started", "In Progress", and "Completed":

1. Select the **Custom field** radio button.
2. Choose the enum field from the **Status Field** dropdown.
3. A mapping table appears showing each enum value with a dropdown to assign a SemPKM status:

| Field Value | Maps to |
|-------------|---------|
| Not Started | To Do |
| In Progress | In Progress |
| Completed | Done |
| On Hold | Blocked |

Available SemPKM statuses: `todo`, `in-progress`, `done`, `blocked`, `cancelled`.

If a task's custom field value is null or not in the mapping, the app falls back to the completed boolean (done/todo).

In **bidirectional mode**, status changes in SemPKM are pushed back by setting the custom field's enum value to the reverse-mapped option.

### Mode 3: Section-Based

Maps project sections (board columns in Board view, or list sections in List view) to SemPKM statuses. This is ideal for teams using Asana boards with columns like "To Do", "In Progress", and "Done":

1. Select the **Section-based** radio button.
2. A mapping table shows each discovered section with a status dropdown:

| Section Name | Maps to |
|--------------|---------|
| To Do | To Do |
| In Progress | In Progress |
| Done | Done |
| Backlog | To Do |

The section is determined from the task's first membership — the project section it currently sits in.

In **bidirectional mode**, status changes in SemPKM are pushed back by *moving the task* between sections. For example, changing a task from "todo" to "done" in SemPKM moves it to the "Done" section in Asana.

If a task's section is not in the mapping, the app falls back to the completed boolean (done/todo).

---

## Configuring Priority Mapping

Priority mapping is optional. If your Asana projects use an enum custom field for priority (e.g., "Priority" with values "High", "Medium", "Low"):

1. Select the priority field from the **Priority Field** dropdown.
2. A mapping table appears:

| Field Value | Maps to |
|-------------|---------|
| High | High |
| Medium | Medium |
| Low | Low |
| Critical | Critical |

Available SemPKM priorities: `low`, `medium`, `high`, `critical`.

If no priority field is configured, tasks are created without a priority value.

In **bidirectional mode**, priority changes in SemPKM are pushed back by setting the custom field's enum value to the reverse-mapped option.

---

## Story Points

If your team tracks effort with a number custom field (e.g., "Story Points" or "Effort"):

1. Select the field from the **Story Points Field** dropdown.
2. The field's numeric value is stored as `bpkm:storyPoints` on each synced task.

This is optional. If no story points field is selected, the property is omitted.

---

## Sync Configuration

Below the field mapping, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Asana → SemPKM. Tasks are imported but changes in SemPKM are not sent back. |
| **Bidirectional** | Asana ↔ SemPKM. Tasks are imported, and local changes to title, status, and priority are pushed back to Asana. |

> **Note:** Push sync handles title (→ task name), status (→ custom field value, section move, or completed flag depending on mode), and priority (→ custom field value). Other properties like due date, tags, and assignee are pull-only.

### Poll Interval

How often the app checks Asana for updated tasks:

| Interval | Best For |
|----------|----------|
| Every 5 minutes | Active projects where you need near-real-time sync |
| Every 15 minutes | Default — good balance of freshness and API usage |
| Every 30 minutes | Lower-activity projects |
| Every hour | Background archival, minimal API load |

Click **Save Config** after making changes.

---

## Running a Sync

Don't want to wait for the next scheduled poll? Click **Sync Now** to trigger an immediate sync. The button shows a "Syncing…" indicator while the operation runs, then refreshes the page with updated stats.

After at least one sync has run, the **Sync Status** section shows:

### Pull Stats

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `ok`, or `error` |
| **Created** | New tasks imported as SemPKM Task objects for the first time |
| **Updated** | Existing synced tasks updated with changes from Asana |
| **Unchanged** | Tasks that had no changes since the last sync |
| **Errors** | Number of individual tasks that failed to sync |

### Push Stats (bidirectional only)

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `ok`, or `error` |
| **Pushed** | Tasks whose changes were sent back to Asana |
| **Skipped** | Tasks with no pushable changes |
| **Errors** | Number of tasks that failed to push |

---

## Field Mapping Reference

### Core Properties

| Asana Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `name` | `dcterms:title` | Direct | ↔ |
| `notes` / `html_notes` | Body content | HTML → Markdown (via markdownify), or plain text passthrough | ← only |
| `due_on` / `due_at` | `bpkm:dueDate` | Truncated to ISO date (YYYY-MM-DD) | ← only |
| `start_on` / `start_at` | `bpkm:startDate` | Truncated to ISO date (YYYY-MM-DD) | ← only |
| `completed` | `bpkm:taskStatus` | `true` → done, `false` → todo (completed_only mode) | ← only |
| `assignee` | `bpkm:assignedTo` | Resolved to Person/Contact via email match | ← only |
| `tags` | `bpkm:tags` | Tag names joined as comma-separated string | ← only |
| `followers` | Edge targets | Each follower resolved via email match | ← only |
| `permalink_url` | `bpkm:externalUrl` | Direct | ← only |
| `gid` | `bpkm:externalUuid` | Direct (also used as `bpkm:externalId`) | ← only |
| `resource_subtype` | Type selection | `"milestone"` → `bpkm:Milestone`, otherwise `bpkm:Task` | ← only |
| *(constant)* | `bpkm:externalProvider` | Always `"asana"` | internal |
| *(sync timestamp)* | `bpkm:lastSyncedAt` | ISO-8601 UTC timestamp of sync run | internal |

### Status Modes

| Mode | Source | Pull Behavior | Push Behavior |
|---|---|---|---|
| `completed_only` | `task.completed` boolean | `true` → done, `false` → todo | Sets `completed` flag |
| `custom_field` | Enum custom field by GID | Enum value name → mapped status | Sets enum value to reverse-mapped option |
| `section` | Task's project section name | Section name → mapped status | Moves task to reverse-mapped section |

In all three modes, if the source value is missing or not in the mapping, the app falls back to the `completed` boolean (done/todo).

---

## Subtask Nesting

Asana Sync fetches subtasks recursively up to **5 levels deep**. Each subtask is created as its own `bpkm:Task` object and linked to its parent via a `dcterms:isPartOf` edge.

The hierarchy is maintained by tracking each subtask's `_parent_gid` during the fetch phase and resolving it to the parent's SemPKM slug (`asana-{gid}`) when creating edges.

For example, a top-level task "Build Feature" with subtask "Write Tests" which itself has subtask "Unit Tests" produces:

```
Build Feature (bpkm:Task)
  └── Write Tests (bpkm:Task, dcterms:isPartOf → Build Feature)
       └── Unit Tests (bpkm:Task, dcterms:isPartOf → Write Tests)
```

Asana milestones (`resource_subtype: "milestone"`) are created as `bpkm:Milestone` objects rather than `bpkm:Task`.

---

## Troubleshooting

### Rate limiting (429 errors)

Asana enforces API rate limits. If the app hits a 429 response:

- The sync reports errors for affected tasks.
- Increase the **poll interval** to reduce API usage.
- Reduce the number of selected projects if you're syncing many large projects.
- The next sync cycle retries failed tasks automatically.

### No custom fields found after discovery

- Verify that your selected projects actually have custom fields defined.
- Custom fields must be **enum** type (dropdown with named options) for status and priority mapping, or **number** type for story points.
- Text, date, and other field types are not supported for mapping.
- Try **Re-discover Fields** after adding new custom fields in Asana.

### Connection expired or token invalid

- **OAuth:** Tokens refresh automatically. If refresh fails (e.g., the OAuth app was deleted in Asana), disconnect and reconnect.
- **PAT:** Personal Access Tokens don't expire automatically but can be revoked. Generate a new one in the Asana Developer Console if needed.
- Check that the SemPKM host can reach `app.asana.com` (or your configured `ASANA_API_URL`).

### Status not mapping correctly

- Verify the **status source** mode matches how your team tracks status in Asana.
- For **custom field** mode: ensure the correct enum field is selected and all its values are mapped.
- For **section-based** mode: ensure all project sections are mapped. New sections added after discovery won't appear until you re-discover fields.
- Check that the task actually has the expected custom field value or section membership — tasks without a value fall back to the completed boolean.

### App shows "Error" status

- Go to **Admin > Applications** and click the Asana Sync card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `asana` entries.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Task type)
- [Chapter 42: Todoist Sync](42-todoist-sync.md) — another task sync app for comparison

---

**Previous:** [Chapter 44: CalDAV Calendar Sync](44-caldav-calendar-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
