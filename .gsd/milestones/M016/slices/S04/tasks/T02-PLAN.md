---
estimated_steps: 5
estimated_files: 4
---

# T02: User guide Chapter 34 — Linear Sync

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M016

## Description

Write user guide Chapter 34 documenting the full Linear sync workflow. This is the user-facing documentation for the linear-sync app built in S01–S03. Follow the established guide chapter pattern (see Chapter 29 for app-related reference, Chapter 32 for extension-related reference).

The chapter covers: what the app does, prerequisites, installation, connecting via API key, team selection, sync configuration (direction + interval), manual sync, understanding sync stats, field mapping details, push sync behavior, admin monitoring, and troubleshooting. Update the README TOC, navigation chain, and glossary.

## Steps

1. **Write `docs/guide/34-linear-sync.md`** with these sections:

   - **Introduction paragraph** — The Linear Sync app connects Linear project management to SemPKM, syncing issues as `bpkm:Task` objects. Bidirectional sync: pull issues from Linear, push changes back.

   - **Prerequisites** — basic-pkm model must be installed (provides the Task type). Accessible from Admin > Mental Models.

   - **Installing the App** — Navigate to Admin > Applications. Enter the app path (`/app/apps/linear-sync` in Docker). Click Install. Wait for "Running" status.

   - **Connecting to Linear** — Two auth methods: API Key (recommended for personal use) and OAuth (not yet available). For API key: go to Linear Settings → API → Personal API keys, create one, paste into the app's settings page. After connecting, the workspace name and team list appear.

   - **Selecting Teams** — Check the teams to sync from. Click Save Teams. Only issues from selected teams are synced.

   - **Sync Configuration** — Direction: "Pull only" (Linear → SemPKM) or "Bidirectional" (Linear ↔ SemPKM). Poll interval: 5m, 15m, 30m, or 1h. Click Save Config.

   - **Manual Sync** — Click "Sync Now" to trigger an immediate sync instead of waiting for the next scheduled poll.

   - **Understanding Sync Stats** — The stats section shows: last sync time, pull results (created/updated/unchanged counts), push results (pushed/skipped counts), and any errors.

   - **Field Mapping** — A table showing how Linear fields map to bpkm:Task properties:

     | Linear Field | SemPKM Property | Notes |
     |---|---|---|
     | title | dcterms:title | Direct mapping |
     | description | Body (markdown) | Stored as object body |
     | state.type | bpkm:taskStatus | triage/backlog→todo, unstarted→todo, started→in-progress, completed→done, canceled→canceled |
     | priority (1-4) | bpkm:taskPriority | 1→urgent, 2→high, 3→medium, 4→low, 0→none |
     | assignee | bpkm:assignedTo | Matched by email to existing Person objects |
     | labels | bpkm:tags | Comma-joined label names |
     | dueDate | bpkm:dueDate | ISO date |
     | url | schema:url | Link back to Linear issue |
     | identifier | bpkm:externalId | e.g. "ENG-123" |

   - **Push Sync** — When sync direction is "Bidirectional", changes made to synced tasks in SemPKM are pushed back to Linear on the next push cycle. Supported push fields: status, priority, title, due date. Loop prevention: changes pushed to Linear are not re-imported on the next pull.

   - **Admin Monitoring** — The Admin > Applications > Linear Sync detail page shows app status, uptime, and task run history. Scheduled tasks (poll-tasks, push-changes) appear in the task history with timestamps and success/failure status.

   - **Troubleshooting** — Common issues:
     - "Not connected" after entering API key → verify the key is valid, check network connectivity
     - No tasks appearing after sync → verify a team is selected, check sync stats for errors
     - Push changes not reflected in Linear → verify sync direction is "Bidirectional", check push stats for errors
     - App shows "Error" status → check Admin > Applications detail page for error messages, try restart

   - **See Also** — Links to Chapter 29 (App Platform), Chapter 10 (Managing Mental Models), Appendix A (Environment Variables)

   - **Navigation footer** — `**Previous:** [Chapter 33: Context Overlay](33-context-overlay.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. **Update `docs/guide/README.md`** — Add line `34. [Linear Sync](34-linear-sync.md)` after the line for Chapter 33 in the numbered chapters list.

3. **Update `docs/guide/33-context-overlay.md` navigation footer** — Change:
   ```
   **Previous:** [Chapter 32: Browser Extension](32-browser-extension.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```
   to:
   ```
   **Previous:** [Chapter 32: Browser Extension](32-browser-extension.md) | **Next:** [Chapter 34: Linear Sync](34-linear-sync.md)
   ```

4. **Add glossary entries to `docs/guide/appendix-d-glossary.md`** — Add four entries in alphabetical order:
   - **Bidirectional Sync** — A sync mode where changes flow in both directions between two systems. In Linear Sync, bidirectional mode pushes SemPKM task changes back to Linear in addition to pulling Linear issues. See [Chapter 34](34-linear-sync.md).
   - **Linear Sync** — A SemPKM app that synchronizes Linear project management issues with bpkm:Task objects. Supports pull sync (Linear → SemPKM), push sync (SemPKM → Linear), and bidirectional mode. See [Chapter 34](34-linear-sync.md).
   - **Pull Sync** — The process of fetching data from an external system into SemPKM. In Linear Sync, pull sync imports Linear issues as bpkm:Task objects with field mapping. See [Chapter 34](34-linear-sync.md).
   - **Push Sync** — The process of sending local changes from SemPKM back to an external system. In Linear Sync, push sync detects modified tasks and updates the corresponding Linear issues. See [Chapter 34](34-linear-sync.md).

5. **Verify all links resolve:**
   ```bash
   grep "34-linear-sync" docs/guide/README.md
   grep "Chapter 34" docs/guide/33-context-overlay.md
   grep "Linear Sync" docs/guide/appendix-d-glossary.md
   grep "Appendix A" docs/guide/34-linear-sync.md
   ```

## Must-Haves

- [ ] `docs/guide/34-linear-sync.md` exists with all sections (intro, prerequisites, install, connect, teams, config, manual sync, stats, field mapping, push sync, admin, troubleshooting, see also)
- [ ] README TOC includes Chapter 34
- [ ] Navigation chain: Ch 33 → Ch 34 → Appendix A
- [ ] Four glossary entries added (Bidirectional Sync, Linear Sync, Pull Sync, Push Sync)

## Verification

- `test -f docs/guide/34-linear-sync.md && echo "exists"` — exists
- `grep "34-linear-sync" docs/guide/README.md` — returns a match
- `grep "Chapter 34" docs/guide/33-context-overlay.md` — returns a match in navigation footer
- `grep "Appendix A" docs/guide/34-linear-sync.md` — returns a match in navigation footer
- `grep -c "Linear Sync\|Pull Sync\|Push Sync\|Bidirectional Sync" docs/guide/appendix-d-glossary.md` — returns ≥ 4
- Chapter content includes a field mapping table with at least 8 rows

## Inputs

- `docs/guide/29-app-platform.md` — reference pattern for app-related guide chapter (read first 40 lines for structure)
- `docs/guide/33-context-overlay.md` — navigation footer to update (last line)
- `docs/guide/README.md` — TOC to update (add after line 62)
- `docs/guide/appendix-d-glossary.md` — glossary to add entries to (alphabetical)
- `apps/linear-sync/manifest.yaml` — app metadata for documentation
- `apps/linear-sync/services/field_mapper.py` — field mapping constants for the mapping table
- `apps/linear-sync/frontend/templates/connect.html` — API key form UX for documentation
- `apps/linear-sync/frontend/templates/connect_status.html` — settings page UX for documentation
- S03 summary — sync state keys, routes, template structure

## Expected Output

- `docs/guide/34-linear-sync.md` — complete Chapter 34 with ~300-500 lines of content
- `docs/guide/README.md` — one line added to TOC
- `docs/guide/33-context-overlay.md` — navigation footer updated
- `docs/guide/appendix-d-glossary.md` — four entries added
