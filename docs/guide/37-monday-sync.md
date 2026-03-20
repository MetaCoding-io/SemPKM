# Chapter 37: Monday.com Sync

The **Monday.com Sync** app connects [Monday.com](https://monday.com) boards to SemPKM, synchronizing items as `bpkm:Task` objects. It supports **pull sync** (import Monday.com items into SemPKM), **push sync** (send SemPKM task changes back to Monday.com), and **bidirectional** mode that does both.

What makes Monday.com Sync unique is its **user-configurable column mapping**. Unlike Jira, GitHub, and Linear — where field structures are fixed — Monday.com boards have fully customizable columns. The app provides type-filtered dropdowns that let you map each Monday.com column to the appropriate SemPKM property. Combined with custom **label mapping** for status and priority values, and **LoopGuard echo prevention** for safe bidirectional sync, Monday.com Sync adapts to any board layout.

---

## Prerequisites

Before installing Monday.com Sync, ensure:

1. **Basic PKM model is installed.** Monday.com Sync creates `bpkm:Task` objects, which require the Basic PKM model. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed". If not, install it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A Monday.com account with board access.** You need access to at least one Monday.com board that contains items you want to sync.

3. **A Monday.com API token.** Generate one at your Monday.com account:
   - Click your profile avatar (bottom-left) → **Administration**
   - Go to **Connections** → **API**
   - Under **Personal API Token**, click **Generate** (or copy your existing token)
   - Alternatively: **Developers** → **My Access Tokens**
   - Copy the token — store it securely

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/monday-sync
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Connecting to Monday.com

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "Monday.com Sync" under the Apps section
- **Admin > Applications** — click the Monday.com Sync card, then click the settings link

### Authentication

Monday.com Sync uses a single **API token** — there is no email or site URL required, making it simpler than other sync apps.

| Method | Status | Notes |
|--------|--------|-------|
| API Token | Available | Single token — no email or site URL needed |
| OAuth 2.0 | Not available | Deferred — API tokens cover all single-user use cases |

### Connecting via API Token

1. Generate an API token in Monday.com (see [Prerequisites](#prerequisites) above).
2. In the Monday.com Sync settings page, enter your token in the **API Token** field.
3. Click **Connect**.

On success, the page updates to show:

- A **Connected** status badge
- Your **display name** (fetched via the Monday.com API to verify the token works)
- A list of **boards** accessible to your account
- **Sync configuration** options

If connection fails:
- Verify the API token has not expired or been revoked
- Regenerate the token in Monday.com if unsure
- Confirm that your SemPKM instance can reach `api.monday.com` over HTTPS
- Check that the token belongs to an account with board access

---

## Board Selection

After connecting, you'll see a list of Monday.com boards accessible to your account.

1. **Check the boxes** next to the boards you want to sync items from.
2. Click **Save Boards**.

Only items from selected boards are synced. You can change the selection at any time — new boards are included in the next sync cycle, and deselected boards stop syncing (existing synced tasks remain in SemPKM).

> **Tip:** Monday.com has no JQL-style filtering. Board selection is the primary way to control what gets synced. Select only the boards you actively work with to keep sync focused.

---

## Column Mapping

This is the key differentiator of Monday.com Sync. Unlike Jira, GitHub, or Linear — where field names are standardized — Monday.com boards have **fully customizable columns**. A "Status" column on one board might be called "Progress" on another. The column mapping step tells the app which of your board's columns correspond to which SemPKM properties.

### Configuring Column Mapping

After selecting a board, click **Configure Columns** to open the column mapping form.

The form displays a dropdown for each SemPKM property (status, priority, due date, assignee, etc.). Each dropdown is **type-filtered** — it shows only the Monday.com columns whose type is compatible with that property. For example, the "Due Date" dropdown only shows columns of type `date`, not text or status columns.

### Worked Example

Suppose your Monday.com board has these columns:

| Column Name | Column Type |
|---|---|
| Status | status |
| Priority | status |
| Due Date | date |
| Assignee | people |
| Description | long_text |
| Sprint | text |
| Tags | tag |
| Blocked By | dependency |

The column mapping form would present:

1. **taskStatus** dropdown → shows "Status" and "Priority" (both are `status` type) → select **Status**
2. **priority** dropdown → shows "Status" and "Priority" → select **Priority**
3. **dueDate** dropdown → shows "Due Date" (the only `date` column) → select **Due Date**
4. **assignedTo** dropdown → shows "Assignee" (the only `people` column) → select **Assignee**
5. **tags** dropdown → shows "Tags" (a `tag` column) → select **Tags**
6. **description** dropdown → shows "Description" (a `long_text` column) → select **Description**

Click **Save Column Mapping** to persist your choices.

### Column Type Compatibility

Each SemPKM property accepts only certain Monday.com column types:

| bpkm Property | Compatible Monday.com Column Types |
|---|---|
| `taskStatus` | `status` |
| `priority` | `status` |
| `dueDate` | `date` |
| `assignedTo` | `people` |
| `tags` | `tag`, `dropdown` |
| `description` | `text`, `long_text` |

> **Note:** Column mapping is stored per-board. If you sync multiple boards, you configure each one independently — different boards can map different columns to the same SemPKM properties.

---

## Status Label Mapping

Monday.com status columns use **custom labels** that vary by board. One board might use "Working on it", "Stuck", and "Done" while another uses "In Progress", "Blocked", and "Complete". Since these labels are arbitrary text, you need to map them to SemPKM's standard task status values.

### Configuring Status Labels

After configuring columns, click **Configure Labels** to open the label mapping form.

The form lists every label defined in your board's status column. For each label, select the corresponding SemPKM `bpkm:taskStatus` value from the dropdown.

### Example Mapping

| Monday.com Label | SemPKM `bpkm:taskStatus` |
|---|---|
| Working on it | `in-progress` |
| Done | `done` |
| Stuck | `blocked` |
| Not Started | `todo` |
| Cancelled | `cancelled` |

### Available Status Values

| Value | Meaning |
|---|---|
| `todo` | Not started |
| `in-progress` | Currently being worked on |
| `done` | Completed |
| `blocked` | Cannot proceed — waiting on something |
| `cancelled` | Abandoned or removed |

Labels not mapped to a status value are imported with the status omitted.

---

## Priority Label Mapping

The same approach applies to priority columns. Monday.com priority columns are `status`-type columns with custom labels like "Critical ⛑️", "High", "Medium", and "Low".

### Example Mapping

| Monday.com Label | SemPKM `bpkm:priority` |
|---|---|
| Critical ⛑️ | `critical` |
| High | `high` |
| Medium | `medium` |
| Low | `low` |

### Available Priority Values

| Value | Meaning |
|---|---|
| `critical` | Urgent — requires immediate attention |
| `high` | Important — should be addressed soon |
| `medium` | Normal priority |
| `low` | Can wait — address when convenient |

---

## Sync Configuration

Below the board selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | Monday.com → SemPKM. Items are imported as tasks but changes in SemPKM are not sent back. |
| **Bidirectional** | Monday.com ↔ SemPKM. Items are imported, and local task edits (title, status, and priority) are pushed back to Monday.com. |

### Poll Interval

How often the app checks Monday.com for updated items:

| Interval | Best For |
|----------|----------|
| Every 5 minutes | Active development where you need near-real-time sync |
| Every 15 minutes | Default — good balance of freshness and API usage |
| Every 30 minutes | Lower-activity boards |
| Every hour | Background archival, minimal API calls |

Click **Save Config** after making changes.

---

## Manual Sync

Don't want to wait for the next scheduled poll? Click **Sync Now** to trigger an immediate sync. The button shows a "Syncing…" indicator while the operation runs, then refreshes the page with updated stats.

Manual sync runs the same logic as the scheduled poll — it imports new and updated items from selected boards, and (in bidirectional mode) pushes local changes to Monday.com.

---

## Field Mapping

When importing a Monday.com item, the app maps columns to `bpkm:Task` properties as follows:

| Monday.com Column Type | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `status` | `bpkm:taskStatus` | Via label mapping | ↔ |
| `status` (priority) | `bpkm:priority` | Via label mapping | ↔ |
| `date` | `bpkm:dueDate` | Date string | ← only |
| `people` | `bpkm:assignedTo` | Person resolution | ← only |
| `text` | `dcterms:title` or body | Direct | ← only |
| `long_text` | Body content | Direct | ← only |
| `numbers` | Custom property | Numeric string | ← only |
| `tag` | `bpkm:tags` | Tag name resolution | ← only |
| `dropdown` | `bpkm:tags` | Label text | ← only |
| `dependency` | `bpkm:dependsOn` | Edge creation | ← only |
| Item name | `dcterms:title` | Direct | ↔ |
| Item URL | `bpkm:externalUrl` | Constructed | ← only |
| Item ID | `bpkm:externalUuid` | String | ← only |

> **Note:** Unlike Jira, Monday.com uses plain text and rich text columns — there is no document format conversion required.

---

## LoopGuard Echo Prevention

In bidirectional mode, an infinite loop can occur: when the app pushes a status change to Monday.com, the item's `updated_at` timestamp changes. On the next poll, the app sees the "updated" item and re-imports the same change, which triggers another push, and so on.

### How LoopGuard Works

LoopGuard solves this with an in-memory TTL (time-to-live) cache:

1. **On push:** When the app pushes a change to Monday.com for a specific item and column, it records the `(item_id, column_id)` pair in the cache with a **30-second TTL**.
2. **On pull:** When the next poll fetches updated items, the app checks each change against the cache. If the `(item_id, column_id)` pair is still within the TTL window, the change is recognized as an **echo** of the push and is skipped.
3. **After TTL expires:** The cache entry is removed. Genuine changes made by other users (or by Monday.com automations) after the 30-second window are imported normally.

### Important Notes

- LoopGuard is **in-memory only** — cache entries are lost if the app restarts. This is acceptable because echo loops only occur within the same process lifetime: a push and its echo happen within seconds of each other.
- The 30-second TTL is deliberately generous to account for Monday.com API propagation delays.
- LoopGuard operates at the column level, not the item level — a push to the status column does not suppress an unrelated change to the priority column on the same item.

---

## Groups as taskGroup

Monday.com boards organize items into **groups** — structural containers like "Sprint 5", "Backlog", or "Done Items". Groups are not columns; they are a structural feature of the board.

When syncing items, the app reads each item's group title and maps it to `bpkm:taskGroup`. For example, items in a group titled "Sprint 5" receive:

```
bpkm:taskGroup: "Sprint 5"
```

This lets you filter and organize synced tasks by their Monday.com group in SemPKM views.

---

## Subitems as parentTask

Monday.com supports **subitems** — items nested under a parent item. Each subitem is a separate item in Monday.com with its own columns and values.

When the app encounters a subitem, it:

1. Creates a `bpkm:Task` object for the subitem (with its own properties from column mapping)
2. Creates a `bpkm:parentTask` edge linking the subitem to the parent task in SemPKM

This preserves the hierarchical structure from Monday.com — you can see which tasks are subtasks of other tasks in SemPKM's views.

---

## Dependencies as dependsOn

Monday.com boards can include **dependency columns** that link items to their blockers. For example, "Task B depends on Task A" is expressed by a dependency column value on Task B pointing to Task A.

When the app encounters dependency column values, it creates `bpkm:dependsOn` edges between the corresponding tasks in SemPKM:

- If Item B has a dependency on Item A, a `bpkm:dependsOn` edge is created from B to A.
- The edge represents: "B depends on A" — B cannot proceed until A is resolved.

Multiple dependencies are supported — each linked item creates a separate edge.

---

## Push Sync

When sync direction is set to **Bidirectional**, the app runs a push cycle after each pull. During a push cycle:

1. The app queries SemPKM for tasks with `externalProvider: "monday"` that have been modified since the last sync.
2. For each modified task, it builds a column update mutation from the current property values.
3. The update is sent to Monday.com via the GraphQL API (`change_multiple_column_values` mutation).

### Supported Push Fields

| SemPKM Property | Monday.com Column | Notes |
|---|---|---|
| `dcterms:title` | Item name | Direct mapping |
| `bpkm:taskStatus` | Status column | Reverse label mapping — status value is converted back to the Monday.com label |
| `bpkm:priority` | Priority column | Reverse label mapping — priority value is converted back to the Monday.com label |

> **Note:** LoopGuard automatically prevents push→pull echo loops. See [LoopGuard Echo Prevention](#loopguard-echo-prevention) above.

---

## Troubleshooting

### "Not connected" after entering token

- Verify the API token has not expired or been revoked.
- Regenerate the token at Monday.com: Avatar → Administration → Connections → API.
- Confirm your SemPKM instance can reach `api.monday.com` over HTTPS.

### No boards appearing after connecting

- Your Monday.com account must have access to at least one board.
- Boards you are not a member of may not appear — ask the board owner to add you.
- If you recently created a new board, run **Sync Now** to refresh the board list.

### No tasks appearing after sync

- Verify at least one board is selected and saved.
- Check the Sync Status section — if it shows 0 created/updated, the board may have no items.
- Confirm the Basic PKM model is installed (the Task type must exist).
- Run a manual sync and check the stats for errors.

### Column mapping issues

- If a dropdown appears empty, the board may not have any columns of the required type.
- Verify your column mapping by clicking **Configure Columns** and checking each dropdown.
- Remember that column mapping is per-board — each board needs its own configuration.
- If items sync but properties are missing, the column mapping for those properties may not be set.

### Push changes not reflected in Monday.com

- Verify sync direction is set to **Bidirectional** (not "Pull only").
- Check the push stats — if "Pushed" is 0, no local changes were detected.
- Ensure you edited the task in SemPKM (not just viewed it) — only actual property changes to title, status, or priority trigger a push.
- Verify the label mapping includes the status/priority value you're trying to push — unmapped values cannot be pushed.
- Your API token must have write access to the board.

### App shows "Error" status

- Go to **Admin > Applications** and click the Monday.com Sync card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors often resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `monday-sync` entries.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Task type)
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `MONDAY_API_URL` override for testing

---

**Previous:** [Chapter 36: Jira Sync](36-jira-sync.md) | **Next:** [Chapter 38: Hosted Demo](38-hosted-demo.md)
