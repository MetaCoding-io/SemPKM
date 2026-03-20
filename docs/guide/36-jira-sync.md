# Chapter 36: Jira Sync

The **Jira Sync** app connects [Jira Cloud](https://www.atlassian.com/software/jira) issues to SemPKM, synchronizing them as `bpkm:Task` objects. It supports **pull sync** (import Jira issues into SemPKM), **push sync** (send SemPKM task changes back to Jira), and **bidirectional** mode that does both.

Once configured, the app polls selected Jira projects on a schedule you choose, creating and updating Task objects automatically. Each synced task carries its Jira issue key, status, priority, labels, assignee, and a link back to the original issue. Key Jira-specific features include:

- **statusCategory-based status normalization** — reliable mapping across projects regardless of custom workflow status names
- **ADF→Markdown conversion** — Jira Cloud's Atlassian Document Format is automatically converted to Markdown on import and back to ADF on push
- **JQL filtering** — restrict which issues are synced using Jira Query Language
- **Epic→Milestone mapping** — Jira Epics become `bpkm:Milestone` objects with child issue linking

---

## Prerequisites

Before installing Jira Sync, ensure:

1. **Basic PKM model is installed.** Jira Sync creates `bpkm:Task` and `bpkm:Milestone` objects, which require the Basic PKM model. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed". If not, install it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A Jira Cloud account.** Jira Sync works with **Jira Cloud only** — Jira Server and Jira Data Center are not supported. You need access to at least one Jira project.

3. **An Atlassian API token.** Generate one at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens):
   - Click **Create API token**
   - Give the token a label (e.g., "SemPKM Jira Sync")
   - Copy the token — it is shown only once

4. **Your Jira site URL.** This is the URL you use to access Jira, e.g., `yourcompany.atlassian.net`. You only need the hostname — do not include `https://` or any path.

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/jira-sync
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Connecting to Jira

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "Jira Sync" under the Apps section
- **Admin > Applications** — click the Jira Sync card, then click the settings link

### Authentication

Jira Sync uses **API tokens with Basic authentication** — there is no OAuth flow.

| Method | Status | Notes |
|--------|--------|-------|
| API Token (Basic Auth) | Available | Email + API token pair sent as Basic auth credentials |
| OAuth 2.0 (3LO) | Not available | Deferred — API tokens cover all single-user use cases |

### Connecting via API Token

1. Generate an API token in Atlassian (see [Prerequisites](#prerequisites) above).
2. In the Jira Sync settings page, fill in three fields:
   - **Email** — the Atlassian account email associated with your API token
   - **API Token** — the token you generated
   - **Site URL** — your Jira site hostname (e.g., `yourcompany.atlassian.net`)
3. Click **Connect**.

On success, the page updates to show:

- A **Connected** status badge
- Your **display name** (fetched via the `/rest/api/3/myself` endpoint to verify the credentials work)
- Your **site URL**
- A list of **projects** available to your account
- **Sync configuration** options

If connection fails:
- Verify the email matches the account that owns the API token
- Check that the API token has not expired — regenerate it in Atlassian if unsure
- Ensure the site URL is correct (just the hostname, e.g., `yourcompany.atlassian.net`)
- Confirm that your SemPKM instance can reach `*.atlassian.net` over HTTPS

---

## Project Selection

After connecting, you'll see a list of Jira projects accessible to your account.

1. **Check the boxes** next to the projects you want to sync issues from.
2. Click **Save Projects**.

Only issues from selected projects are synced. You can change the selection at any time — new projects are included in the next sync cycle, and deselected projects stop syncing (existing synced tasks remain in SemPKM).

> **Tip:** If you work across many Jira projects, select only the ones you actively contribute to. Combined with JQL filtering (below), this keeps sync fast and focused.

---

## JQL Filter

Optionally, you can provide a JQL (Jira Query Language) clause to restrict which issues are synced. The JQL filter is applied **in addition to** project selection — it narrows the results further but does not replace the project filter.

Enter your JQL in the **JQL Filter** field. Examples:

```
project = PROJ AND issuetype != Sub-task
```
```
priority in (High, Highest)
```
```
labels = "frontend"
```
```
assignee = currentUser() AND resolution = Unresolved
```

Leave the field empty to sync all issues from selected projects (the default).

> **Note:** JQL syntax errors will cause the sync to fail. Test your JQL in Jira's issue search first. For JQL syntax reference, see [Atlassian's JQL documentation](https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql/).

---

## Sync Configuration

Below the project selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Jira → SemPKM. Issues are imported as tasks but changes in SemPKM are not sent back. |
| **Bidirectional** | Jira ↔ SemPKM. Issues are imported, and local task edits (title, description, and priority) are pushed back to Jira. |

### Poll Interval

How often the app checks Jira for updated issues:

| Interval | Best For |
|----------|----------|
| Every 5 minutes | Active development where you need near-real-time sync |
| Every 15 minutes | Default — good balance of freshness and API usage |
| Every 30 minutes | Lower-activity projects |
| Every hour | Background archival, minimal API calls |

Click **Save Config** after making changes.

---

## Manual Sync

Don't want to wait for the next scheduled poll? Click **Sync Now** to trigger an immediate sync. The button shows a "Syncing…" indicator while the operation runs, then refreshes the page with updated stats.

Manual sync runs the same logic as the scheduled poll — it imports new and updated issues from selected projects, and (in bidirectional mode) pushes local changes to Jira.

---

## Field Mapping

When importing a Jira issue, the app maps fields to `bpkm:Task` properties as follows:

| Jira Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `summary` | `dcterms:title` | Direct | ↔ |
| `description` (ADF) | Body content | ADF→Markdown (see below) | ↔ |
| `status.statusCategory.key` | `bpkm:taskStatus` | See status mapping below | ← only |
| `status.name` | `bpkm:externalStatus` | Preserved for display | ← only |
| `priority.name` | `bpkm:priority` | See priority mapping below | ↔ |
| `assignee.accountId` | `bpkm:assignedTo` | Resolved to Person IRI | ← only |
| `labels` + `components` | `bpkm:tags` | Names merged as tags | ← only |
| `sprint.name` | `bpkm:taskGroup` | Sprint name as task group | ← only |
| `duedate` | `bpkm:dueDate` | Truncated to date-only | ← only |
| `resolutiondate` | `bpkm:completedDate` | Truncated to date-only | ← only |
| `key` (e.g., PROJ-123) | `bpkm:externalId` | Issue key string | ← only |
| Issue browse URL | `bpkm:externalUrl` | Constructed from site URL | ← only |
| `id` | `bpkm:externalUuid` | Jira issue numeric ID | ← only |

### Status Mapping

Jira allows every project to define custom status names (e.g., "Code Review", "QA Testing", "Awaiting Deploy"). Instead of mapping each individual status name, SemPKM uses the `statusCategory.key` — Jira's built-in three-way classification that every status belongs to:

| `statusCategory.key` | Example Jira Status Names | SemPKM `bpkm:taskStatus` | Notes |
|---|---|---|---|
| `new` | To Do, Open, Backlog | `todo` | All "not started" statuses |
| `indeterminate` | In Progress, In Review, QA | `in-progress` | All "in flight" statuses |
| `done` | Done, Closed, Resolved | `done` | All "completed" statuses |

### Priority Mapping

Jira's built-in priority names map to SemPKM priorities:

| Jira Priority | SemPKM `bpkm:priority` |
|---|---|
| Highest | `critical` |
| Critical | `critical` |
| Blocker | `critical` |
| High | `high` |
| Medium | `medium` |
| Low | `low` |
| Lowest | `low` |
| Trivial | `low` |

> **Note:** If a Jira issue has no priority set, the `bpkm:priority` property is omitted from the synced task.

---

## Understanding statusCategory

Jira allows each project to define its own workflow with custom status names — one project might use "Code Review" while another uses "Peer Review" for the same workflow stage. Despite this flexibility, every Jira status belongs to exactly one of three **status categories**:

- **`new`** — the issue has not been started
- **`indeterminate`** — the issue is in progress (any "in flight" state)
- **`done`** — the issue is completed

SemPKM uses `statusCategory.key` (not the individual status name) for reliable cross-project normalization. This means that whether your team calls the active state "In Progress", "In Development", or "Under Review", it always maps to `in-progress` in SemPKM.

The actual Jira status name is preserved in `bpkm:externalStatus` so you can still see what specific workflow stage the issue is in when viewing the task in SemPKM.

---

## Assignee Resolution

Jira identifies users by `accountId` (an opaque string like `5b10ac8d14c9db0006b4...`). When importing an issue with an assignee, Jira Sync resolves the account to a SemPKM Person object by:

1. Fetching the user's profile via the `/rest/api/3/user` endpoint to get their email and display name
2. Matching the **email** against existing Person objects in SemPKM
3. Falling back to matching by `bpkm:externalId` (the Jira `accountId`)
4. Creating a new Person object if no match is found

---

## ADF Conversion Notes

Jira Cloud uses **Atlassian Document Format (ADF)** — a JSON document tree — instead of Markdown for issue descriptions and comments. SemPKM automatically converts between the two formats:

- **On import (pull):** ADF is converted to Markdown for display and editing in SemPKM
- **On push:** Markdown is converted back to ADF before sending to Jira

### Supported ADF Node Types

The following ADF node types are supported in the conversion:

- Paragraphs
- Headings (levels 1–6)
- Bullet lists
- Ordered lists
- Code blocks (with language annotation)
- Blockquotes
- Tables
- Horizontal rules (`rule`)
- Text with marks: **bold**, *italic*, `code`, [links](), ~~strikethrough~~
- Mentions (`@user`)
- Inline cards (links displayed as cards in Jira)

### Limitations

- **Unsupported node types** render as `[unsupported: {type}]` placeholders in the converted Markdown. This preserves the document structure without crashing on unknown content.
- **Media and attachments** are not imported. Jira media nodes appear as `[media: {id}]` placeholders.
- **Markdown→ADF reverse conversion** handles the subset that SemPKM typically produces: paragraphs, headings, lists, code blocks, blockquotes, and inline formatting (bold, italic, code, links, strikethrough). Complex ADF-only constructs (panels, decision lists, Jira-specific macros) cannot be round-tripped.

---

## Push Sync

When sync direction is set to **Bidirectional**, the app runs a push cycle after each pull. During a push cycle:

1. The app queries SemPKM for tasks with `externalProvider: "jira"` that have been modified since the last sync.
2. For each modified task, it builds an update payload from the current property values.
3. The update is sent to Jira via the REST API (`PUT /rest/api/3/issue/{key}`).

### Supported Push Fields

| SemPKM Property | Jira Field | Notes |
|---|---|---|
| `dcterms:title` | `summary` | Direct mapping |
| Body content | `description` | Markdown converted back to ADF |
| `bpkm:priority` | `priority.name` | Reverse-mapped: `critical`→Highest, `high`→High, `medium`→Medium, `low`→Low |

> **Important:** Status transitions are **not pushed** to Jira. Jira requires valid workflow transition IDs to change an issue's status, and these IDs vary per project and workflow configuration. Implementing status push would require querying each project's available transitions, which adds significant complexity. This limitation is by design for v1.

### Loop Prevention

When the app pushes a change to Jira, it updates the task's `bpkm:lastSyncedAt` timestamp. On the next pull cycle, the app compares the issue's `updated` timestamp against `lastSyncedAt` — if the Jira timestamp is older or equal, the update is skipped. This prevents infinite sync loops where a push triggers a pull triggers a push.

---

## Epic → Milestone Mapping

Jira Epics are handled differently from regular issues. When the sync encounters an issue with `issuetype.name` of "Epic", it creates a `bpkm:Milestone` object instead of a Task. The mapping is:

| Jira Epic Field | SemPKM Milestone Property |
|---|---|
| `summary` | `dcterms:title` |
| `status.statusCategory.key` | `bpkm:milestoneStatus` (`done`→`completed`, others→`active`) |
| `duedate` | `bpkm:targetDate` |
| `key` | `bpkm:externalId` |
| Issue browse URL | `bpkm:externalUrl` |

Child issues of the Epic (issues whose `epic` field references the Epic) are linked to the Milestone via the standard project/milestone relationship. This preserves the hierarchical organization from Jira — you can see which tasks belong to which epic/milestone in SemPKM's views.

---

## Issue Links — dependsOn Edges

Jira supports typed issue links between issues (e.g., "blocks", "relates to", "duplicates"). Jira Sync maps **"Blocks"** links to `bpkm:dependsOn` edges:

- If Issue A **is blocked by** Issue B (i.e., Issue B has an inward "Blocks" link from Issue A), a `bpkm:dependsOn` edge is created from A to B.
- The edge represents: "A depends on B" — A cannot proceed until B is resolved.

### What's Not Mapped

Other Jira link types are not currently mapped:

| Jira Link Type | Mapped? | Notes |
|---|---|---|
| Blocks | ✅ Yes | Creates `bpkm:dependsOn` edge |
| Relates to | ❌ No | Generic relationship, no semantic equivalent |
| Clones | ❌ No | Copy relationship, not dependency |
| Duplicates | ❌ No | Duplicate tracking, not dependency |

> **Deduplication:** Each "Blocks" relationship appears twice in Jira's data (once as an outward link on the blocking issue, once as an inward link on the blocked issue). Jira Sync uses only the inward link to avoid creating duplicate edges.

---

## Troubleshooting

### "Not connected" after entering credentials

- Verify the **email** matches the Atlassian account that owns the API token.
- Check that the **API token** has not expired — regenerate it at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens).
- Ensure the **site URL** is just the hostname (e.g., `yourcompany.atlassian.net`), not a full URL with `https://` or a path.
- Confirm your SemPKM instance can reach `*.atlassian.net` over HTTPS.

### No projects appearing after connecting

- Your Atlassian account must have the **Browse Projects** permission for at least one project.
- Check with your Jira administrator if your account has the correct project-level permissions.

### No tasks appearing after sync

- Verify at least one project is selected and saved.
- Check the Sync Status section — if it shows 0 created/updated, the projects may have no issues matching your JQL filter.
- If using a JQL filter, try removing it temporarily to see if issues sync without it.
- Run a manual sync and check the stats for errors.
- Confirm the Basic PKM model is installed (the Task type must exist).

### JQL filter errors

- Test your JQL in Jira's built-in issue search first — it provides syntax error messages.
- Common mistakes: missing quotes around string values, using field names that don't exist in your Jira instance, incorrect function syntax.
- Remember that the JQL filter is applied in addition to project selection — you don't need to include `project = X` in the JQL if you've already selected that project.

### Push changes not reflected in Jira

- Verify sync direction is set to **Bidirectional** (not "Pull only").
- Check the push stats — if "Pushed" is 0, no local changes were detected.
- Ensure you edited the task in SemPKM (not just viewed it) — only actual property changes to title, description, or priority trigger a push.
- **Status changes are not pushed** — this is by design (see [Push Sync](#push-sync) above).
- Your API token must have write access to the issues in the target projects.

### Rate limiting

Jira Cloud applies rate limiting to API requests. If you sync many projects with many issues, you may encounter rate limits. Symptoms include sync errors or incomplete results. If rate limiting is a concern, increase the poll interval or reduce the number of synced projects and tighten your JQL filter.

### App shows "Error" status

- Go to **Admin > Applications** and click the Jira Sync card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors or rate-limit hits often resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `jira-sync` entries.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Task and Milestone types)
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `JIRA_API_URL` override for testing

---

**Previous:** [Chapter 35: GitHub Sync](35-github-sync.md) | **Next:** [Chapter 37: Monday.com Sync](37-monday-sync.md)
