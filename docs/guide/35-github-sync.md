# Chapter 35: GitHub Sync

The **GitHub Sync** app connects [GitHub](https://github.com) Issues and Pull Requests to SemPKM, synchronizing them as `bpkm:Task` objects. It supports **pull sync** (import GitHub issues and PRs into SemPKM), **push sync** (send SemPKM task changes back to GitHub), and **bidirectional** mode that does both.

Once configured, the app polls selected repositories on a schedule you choose, creating and updating Task objects automatically. Each synced task carries its GitHub issue number, status, labels, assignee, and a link back to the original issue or PR. Pull requests that reference issues are linked via `bpkm:dependsOn` edges, preserving the development workflow context in your knowledge graph.

---

## Prerequisites

Before installing GitHub Sync, ensure:

1. **Basic PKM model is installed.** GitHub Sync creates `bpkm:Task` objects, which require the Basic PKM model. Navigate to **Admin > Mental Models** and verify Basic PKM appears with status "Installed". If not, install it first — see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A GitHub Personal Access Token (PAT).** You need a GitHub account and a PAT with the `repo` scope. Both classic tokens and fine-grained tokens work:
   - **Classic PAT:** Go to [github.com/settings/tokens](https://github.com/settings/tokens) → Generate new token (classic) → select the `repo` scope.
   - **Fine-grained PAT:** Go to [github.com/settings/tokens](https://github.com/settings/tokens) → Generate new token (fine-grained) → select the repositories you want to sync → grant **Issues** read/write permission.

---

## Installing the App

1. Navigate to **Admin > Applications**.
2. In the **Install App** form, enter the app path:
   ```
   /app/apps/github-sync
   ```
   > **Note:** This is the path inside the Docker container. If you mounted apps at a different location, adjust accordingly.
3. Click **Install**.
4. The platform validates the manifest, registers the app, and starts it. Wait for the status badge to show **Running** (green).

If installation fails, check that the path is correct and the directory contains a valid `manifest.yaml`. See [Chapter 29: App Platform](29-app-platform.md) for troubleshooting app installation.

---

## Connecting to GitHub

After installation, open the app's settings page. You can reach it from:

- **Workspace sidebar** — look for "GitHub Sync" under the Apps section
- **Admin > Applications** — click the GitHub Sync card, then click the settings link

### Authentication

GitHub Sync uses **Personal Access Tokens only** — there is no OAuth flow. This keeps the setup simple: paste your token and go.

| Method | Status | Notes |
|--------|--------|-------|
| Personal Access Token | Available | Classic (`ghp_...`) or fine-grained tokens |
| OAuth App | Not available | Not implemented — PAT covers all use cases for single-user setups |

### Connecting via PAT

1. Generate a PAT in GitHub (see [Prerequisites](#prerequisites) above).
2. In the GitHub Sync settings page, paste the token into the **Token** field.
3. Click **Connect**.

On success, the page updates to show:

- A **Connected** status badge
- Your **GitHub username** (fetched via the `/user` API to verify the token works)
- A masked preview of the token (e.g., `ghp_****ab12`)
- A list of **repositories** available to the token
- **Sync configuration** options

If connection fails, verify the token is valid and has the `repo` scope. Classic tokens must not be expired; fine-grained tokens must have the correct repository access.

---

## Selecting Repositories

After connecting, you'll see a list of repositories accessible to your token, including both public and private repos.

1. **Check the boxes** next to the repositories you want to sync issues from.
2. Click **Save Repos**.

Only issues (and PRs) from selected repositories are synced. You can change the selection at any time — new repositories are included in the next sync cycle, and deselected repositories stop syncing (existing synced tasks remain in SemPKM).

> **Tip:** If you manage many repositories, the list is sorted by most recently updated. Select only the repositories you actively work in to keep sync fast and focused.

---

## Sync Configuration

Below the repository selection, configure how sync behaves:

### Direction

| Option | Behavior |
|--------|----------|
| **Pull only** (default) | GitHub → SemPKM. Issues and PRs are imported as tasks but changes in SemPKM are not sent back. |
| **Bidirectional** | GitHub ↔ SemPKM. Issues are imported, and local task edits (title and status) are pushed back to GitHub. |

### Poll Interval

How often the app checks GitHub for updated issues:

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

Manual sync runs the same logic as the scheduled poll — it imports new and updated issues from selected repositories, and (in bidirectional mode) pushes local changes to GitHub.

---

## Understanding Sync Stats

After at least one sync has run, the **Sync Status** section shows:

### Last Sync Time

The UTC timestamp of the most recent sync operation.

### Pull Results

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `success`, `partial` (some issues failed), or `error` |
| **Created** | New issues/PRs imported as SemPKM tasks for the first time |
| **Updated** | Existing synced tasks updated with changes from GitHub |
| **Errors** | Number of individual issues that failed to sync |

If errors are present, the diagnostic data includes a `failed_issues` list identifying which issues failed and why.

### Push Results

Shown only when sync direction is "Bidirectional":

| Stat | Meaning |
|------|---------|
| **Status** | Overall result: `success` or `error` |
| **Pushed** | Tasks whose local changes were sent to GitHub |
| **Skipped** | Tasks with no local changes, or changes that originated from GitHub (loop prevention) |
| **Errors** | Number of tasks that failed to push |

---

## Field Mapping

When importing a GitHub issue, the app maps fields to `bpkm:Task` properties as follows:

| GitHub Field | SemPKM Property | Transform | Direction |
|---|---|---|---|
| `title` | `dcterms:title` | Direct | ↔ |
| `body` (Markdown) | Body content | Direct (both Markdown) | ↔ |
| `state` | `bpkm:taskStatus` | See status mapping below | ↔ |
| `state_reason` | `bpkm:externalStatus` | completed / not_planned / reopened | ← only |
| `labels[].name` | `bpkm:tags` | Label names as tags | ↔ |
| `assignees[].login` | `bpkm:assignedTo` | First assignee → Person IRI | ↔ |
| `milestone.title` | `bpkm:taskProject` | Milestone → Project/Milestone IRI | ← only |
| `number` | `bpkm:externalId` | Stored as "#42" | ← only |
| `html_url` | `bpkm:externalUrl` | Direct link to issue/PR | ← only |
| `node_id` | `bpkm:externalUuid` | GitHub's global node ID | ← only |
| `updated_at` | *(internal)* | ISO-8601 for loop prevention | internal |
| `pull_request` key | `bpkm:externalProvider` | `"github-pr"` if PR, `"github"` if issue | ← only |

### Status Mapping

GitHub uses a simpler state model than some other platforms — issues are either **open** or **closed**. The `state_reason` field refines the meaning of "closed":

| GitHub `state` | `state_reason` | SemPKM `bpkm:taskStatus` |
|---|---|---|
| `open` | *(any)* | `todo` |
| `closed` | `completed` | `done` |
| `closed` | `not_planned` | `cancelled` |
| `closed` | *(null or other)* | `done` |
| *(reopened)* | `reopened` | `todo` |

> **Note:** GitHub has no native priority field. If you need priority tracking, use GitHub labels (e.g., `priority:high`) — they sync as `bpkm:tags` and can be filtered in SemPKM views.

### Assignee Resolution

GitHub issues can have multiple assignees. GitHub Sync maps the **first assignee** to `bpkm:assignedTo`. The assignee is resolved to a SemPKM Person object by:

1. Matching the assignee's **email** against existing Person objects
2. Falling back to matching the GitHub **login/username** (via `bpkm:externalId`)
3. Creating a new Person object if no match is found

---

## Push Sync

When sync direction is set to **Bidirectional**, the app runs a push cycle after each pull. During a push cycle:

1. The app queries SemPKM for tasks with `externalProvider: "github"` that have been modified since the last sync (comparing `dcterms:modified` against `bpkm:lastSyncedAt`).
2. For each modified task, it builds a PATCH payload from the current property values.
3. The update is sent to GitHub via the REST API (`PATCH /repos/{owner}/{repo}/issues/{number}`).

### Supported Push Fields

| SemPKM Property | GitHub Field | Notes |
|---|---|---|
| `dcterms:title` | `title` | Direct mapping |
| `bpkm:taskStatus` | `state` | Reverse-mapped: `todo` → `open`, `done` → `closed`, `cancelled` → `closed` |

> **Note:** Push sync currently supports **title and status only**. Labels, assignees, and body content are not pushed back to GitHub in the current version.

### Loop Prevention

When the app pushes a change to GitHub, it updates the task's `bpkm:lastSyncedAt` timestamp. On the next pull cycle, the app compares the issue's `updated_at` timestamp against `lastSyncedAt` — if the GitHub timestamp is older or equal, the update is skipped. This prevents infinite sync loops where a push triggers a pull triggers a push.

---

## PR-to-Issue Linking

GitHub Sync handles Pull Requests alongside issues. PRs are synced as `bpkm:Task` objects with `externalProvider` set to `"github-pr"` (instead of `"github"` for regular issues). The field mapping is identical.

### How Linking Works

When a PR body contains a reference like "Closes #42" or "Fixes #42", GitHub records this as a cross-reference in the issue's timeline. After syncing issues and PRs, GitHub Sync:

1. Fetches the **timeline** for each synced issue (via GitHub's Timeline API).
2. Looks for `cross-referenced` events where the source is a Pull Request.
3. If the referenced PR is also synced, creates a `bpkm:dependsOn` edge from the PR task to the issue task.

This preserves the "PR closes issue" relationship in your knowledge graph, making it visible in SemPKM's graph views and edge lists.

### Limitations

- **Same-repo only.** Cross-repository PR references (e.g., a PR in `org/repo-a` referencing issue #42 in `org/repo-b`) are not linked. Both the PR and the issue must be in a synced repository.
- **Direction.** The edge goes from PR → Issue (the PR depends on / closes the issue).
- **Timeline API cost.** Each issue requires a separate API call for timeline data. For repositories with many issues, this adds to API quota usage.

---

## Admin Monitoring

The **Admin > Applications > GitHub Sync** detail page provides operational visibility:

- **Status badge** — Running (green), Stopped (gray), or Error (red)
- **Uptime** — How long the app has been running since last start
- **PID** — Process identifier for the app subprocess
- **Restart count** — How many times the app has been restarted

### Task History

The detail page also shows scheduled task execution history. GitHub Sync registers two background tasks:

| Task ID | Description | Default Interval |
|---|---|---|
| `poll-tasks` | Poll GitHub for updated issues/PRs and sync to SemPKM | 15 minutes |
| `push-changes` | Push local task changes back to GitHub | 15 minutes |

Each task run shows its timestamp, duration, and success/failure status. Failed task runs include error messages that help diagnose sync issues.

---

## Troubleshooting

### "Not connected" after entering token

- Verify the PAT is valid and not expired — regenerate it in GitHub if unsure.
- **Classic tokens** must have the `repo` scope selected.
- **Fine-grained tokens** must have repository access and Issues read/write permission.
- Check that your SemPKM instance can reach `api.github.com` over HTTPS.

### No repositories appearing after connecting

- The token must have access to at least one repository.
- Fine-grained tokens are scoped to specific repositories — check that the desired repos are selected in the token settings on GitHub.
- Classic tokens with `repo` scope can see all repositories the user owns or has been granted access to.

### No tasks appearing after sync

- Verify at least one repository is selected and saved.
- Check the Sync Status section — if it shows 0 created/updated, the repositories may have no issues.
- Run a manual sync and check the stats for errors.
- Confirm the Basic PKM model is installed (the Task type must exist).

### Push changes not reflected in GitHub

- Verify sync direction is set to **Bidirectional** (not "Pull only").
- Check the push stats — if "Pushed" is 0, no local changes were detected.
- Ensure you edited the task in SemPKM (not just viewed it) — only actual property changes to title or status trigger a push.
- The PAT must have write access to issues (classic: `repo` scope; fine-grained: Issues read/write).

### App shows "Error" status

- Go to **Admin > Applications** and click the GitHub Sync card for details.
- Check the task history for recent failures and their error messages.
- Try **Restart** — transient network errors or rate-limit hits resolve on retry.
- If the error persists, check the app logs via `docker compose logs api` and search for `github-sync` entries.

### Rate limiting

GitHub allows 5,000 API requests per hour with token authentication. If you sync many repositories with many issues, you may approach this limit. Symptoms include sync errors or incomplete results. The app proactively checks the `X-RateLimit-Remaining` header and pauses when the limit is low. If rate limiting is a concern, increase the poll interval or reduce the number of synced repositories.

---

## See Also

- [Chapter 29: App Platform](29-app-platform.md) — managing apps, installation, monitoring
- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — installing Basic PKM (required for Task type)
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — `GITHUB_API_URL` override for GitHub Enterprise

---

**Previous:** [Chapter 34: Linear Sync](34-linear-sync.md) | **Next:** [Chapter 36: Jira Sync](36-jira-sync.md)
