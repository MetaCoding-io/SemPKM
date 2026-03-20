---
estimated_steps: 6
estimated_files: 5
---

# T03: Write Chapter 37 user guide and update documentation chain

**Slice:** S03 — E2E Tests + User Guide
**Milestone:** M019

## Description

Write Chapter 37 (Todoist Sync) user guide following the Ch. 35 (GitHub Sync) structure as the closest pattern match (both are REST+PAT sync apps). Update all documentation cross-references: README TOC, glossary, appendix A environment variables, and navigation chain (Ch 36 → Ch 37 → Appendix A).

## Steps

1. **Create `docs/guide/37-todoist-sync.md`** (~250-300 lines) with these sections following Ch. 35 as pattern:
   - Title: `# Chapter 37: Todoist Sync`
   - **Prerequisites**: Basic PKM model must be installed (provides `bpkm:Task` type). Need a Todoist account with a Personal API Token.
   - **Installing the App**: Navigate to Admin > Applications, enter path `/app/apps/todoist-sync`, click Install. Wait for "Running" status.
   - **Connecting to Todoist**: PAT-only auth. Describe how to get a Todoist API token (Settings → Integrations → Developer → API token). Open workspace → APPS section → Todoist Sync → paste token → click Connect. Token verified via `GET /rest/v2/projects`.
   - **Selecting Projects**: After connecting, project list appears. Check which Todoist projects to sync. Click Save Selection.
   - **Sync Configuration**: Direction section (pull-only: Todoist → SemPKM; bidirectional: Todoist ↔ SemPKM). Poll Interval section (10m, 30m, 1h, 6h, 24h options).
   - **Manual Sync**: Sync Now button triggers immediate pull (and push if bidirectional).
   - **Understanding Sync Stats**: Last sync time, pull results (created/updated/unchanged/errors), push results (pushed/closed/reopened/updated/skipped/errors).
   - **Field Mapping** — the core documentation section with these subsections:
     - **Priority Mapping** table: Todoist 1 → Low, 2 → Medium, 3 → High, 4 → Critical. Note the inversion: Todoist's "priority 4" (red flag, p1 in UI) maps to "critical" in SemPKM. Todoist's "priority 1" (no priority, p4 in UI) maps to "low".
     - **Status Mapping** table: `is_completed: false` → `todo`, `is_completed: true` → `done`. Push direction: `todo` → reopen, `done` → close, `cancelled` → close.
     - **Due Dates**: `due.date` (date-only) maps to `bpkm:dueDate` as `xsd:date`. `due.datetime` maps as `xsd:dateTime`. No due date → property omitted.
     - **Labels**: Todoist labels pass through directly as `bpkm:tags` array.
     - **External Link**: `url` field stored as `bpkm:externalUrl` for linking back to Todoist.
     - **Sync Metadata**: `externalId`, `externalProvider: "todoist"`, `lastSyncedAt` tracked per task.
   - **Push Sync** with subsections:
     - **Close/Reopen Pattern**: Unlike other sync apps that PATCH a status field, Todoist uses dedicated `POST /tasks/{id}/close` and `POST /tasks/{id}/reopen` endpoints. When a task is marked "done" in SemPKM, the app calls the close endpoint. When reopened, it calls the reopen endpoint.
     - **Supported Push Fields**: Status (close/reopen), title, priority, labels, due date.
     - **Loop Prevention**: `lastSyncedAt` comparison prevents re-importing pushed changes.
   - **Assignee Resolution**: Email/name-based SPARQL lookup against existing Person/Contact objects. Creates Person on miss.
   - **Admin Monitoring**: Task History on admin detail page shows sync runs.
   - **Troubleshooting** subsections:
     - "Not connected" after entering token — check token validity, firewall
     - No projects appearing — token may lack permissions
     - No tasks after sync — check project selection, check Todoist project has tasks
     - Push changes not reflected in Todoist — check sync direction is bidirectional
     - App shows "Error" status — check container logs
   - **See Also**: Links to Ch. 29 (App Platform), Ch. 10 (Managing Mental Models), Appendix A
   - **Navigation footer**: `**Previous:** [Chapter 36: Google Calendar Sync](36-google-calendar-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. **Update `docs/guide/README.md`**: Add line `37. [Todoist Sync](37-todoist-sync.md)` after the line for chapter 36.

3. **Update `docs/guide/appendix-d-glossary.md`**: Add entry after "Google Calendar Sync" entry (alphabetically under T):
   ```
   **Todoist Sync**
   A SemPKM app that synchronizes Todoist tasks with `bpkm:Task` objects. Supports pull sync (Todoist → SemPKM) and push sync (close/reopen tasks bidirectionally). Handles priority inversion (Todoist 1=low → 4=critical), labels as tags, due dates, and project selection. See [Chapter 37: Todoist Sync](37-todoist-sync.md).
   ```

4. **Update `docs/guide/appendix-a-environment-variables.md`**: Add row to the environment variables table after the `GOOGLE_TOKEN_URL` row:
   ```
   | `TODOIST_API_URL` | Base URL for the Todoist REST API v2. Override to redirect the Todoist Sync app to a different endpoint (e.g. a mock server for testing). | `https://api.todoist.com/rest/v2` | No |
   ```

5. **Update `docs/guide/36-google-calendar-sync.md`** navigation footer: Change `**Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)` to `**Next:** [Chapter 37: Todoist Sync](37-todoist-sync.md)`.

6. **Verify cross-references**: Run `rg "37-todoist" docs/guide/` to confirm hits in README, glossary, appendix, and Ch. 36.

## Must-Haves

- [ ] Chapter 37 includes priority inversion table with all 4 levels mapped bidirectionally
- [ ] Chapter 37 documents close/reopen endpoint pattern (distinct from PATCH-based push in other sync apps)
- [ ] Chapter 37 has status mapping table (is_completed → todo/done, push direction close/reopen)
- [ ] README TOC has entry for Chapter 37
- [ ] Glossary has "Todoist Sync" entry
- [ ] Appendix A has `TODOIST_API_URL` row
- [ ] Navigation chain: Ch 36 → Ch 37 → Appendix A

## Verification

- `rg "37-todoist" docs/guide/` — hits in README.md, appendix-d-glossary.md, 36-google-calendar-sync.md, and 37-todoist-sync.md itself
- `rg "Todoist Sync" docs/guide/appendix-d-glossary.md` — glossary entry present
- `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md` — env var documented
- `grep -c "^##" docs/guide/37-todoist-sync.md` — at least 12 sections

## Inputs

- `docs/guide/35-github-sync.md` — Reference structure for REST+PAT sync app guide (309 lines, closest pattern)
- `docs/guide/36-google-calendar-sync.md` — Navigation footer needs updating (Next → Ch 37)
- `docs/guide/README.md` — TOC needs new entry after line 36
- `docs/guide/appendix-d-glossary.md` — Needs "Todoist Sync" entry (alphabetical under T)
- `docs/guide/appendix-a-environment-variables.md` — Needs `TODOIST_API_URL` row
- S01 summary: field_mapper handles priority inversion (1→low, 2→medium, 3→high, 4→critical), status mapping (is_completed ↔ taskStatus), due date extraction, labels passthrough
- S02 summary: push_sync uses close/reopen endpoints for status changes, lastSyncedAt loop prevention

## Expected Output

- `docs/guide/37-todoist-sync.md` — ~250-300 line user guide with field mapping tables and troubleshooting
- `docs/guide/README.md` — Updated TOC with Chapter 37
- `docs/guide/appendix-d-glossary.md` — "Todoist Sync" entry added
- `docs/guide/appendix-a-environment-variables.md` — `TODOIST_API_URL` row added
- `docs/guide/36-google-calendar-sync.md` — Navigation footer updated to point to Ch 37

## Observability Impact

This task produces documentation only — no runtime code changes.

- **No new runtime signals.** No logs, metrics, or health endpoints are added or modified.
- **Inspection:** Verify documentation completeness with `rg "37-todoist" docs/guide/` (cross-references) and `grep -c "^##" docs/guide/37-todoist-sync.md` (section count ≥ 12).
- **Failure visibility:** Broken cross-references surface as 404 links when serving docs. Verify all internal links target existing files: `ls docs/guide/37-todoist-sync.md`.
