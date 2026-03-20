---
estimated_steps: 7
estimated_files: 5
---

# T03: Write Chapter 40 user guide and update README/glossary/appendix/nav-chain

**Slice:** S04 — E2E tests + mock server + user guide
**Milestone:** M022

## Description

Write the Chapter 40 user guide documenting Asana Sync setup and usage, including the novel field mapping configuration walkthrough. Update README TOC, glossary, appendix A, and navigation chain to integrate the new chapter.

The distinctive content in this chapter is the **field mapping configuration** — explaining the 3 status modes (completed_only, custom_field, section), priority mapping, and story points. No prior user guide chapter covers configurable field mapping because prior sync apps have fixed mappings. This is what makes Chapter 40 unique.

**Reference:** `docs/guide/39-caldav-calendar-sync.md` (368 lines) for structure and tone, `docs/guide/38-outlook-calendar-sync.md` (484 lines) for a longer example.

## Steps

1. **Read reference files:**
   - `docs/guide/39-caldav-calendar-sync.md` — structure, navigation pattern, field mapping tables
   - `docs/guide/appendix-a-environment-variables.md` — existing env var table format
   - `docs/guide/appendix-d-glossary.md` — existing glossary entry format
   - `docs/guide/README.md` — TOC structure (line numbering for insertion point)

2. **Create `docs/guide/40-asana-sync.md`** (~400-450 lines). Sections:
   - **Title:** `# Chapter 40: Asana Sync`
   - **Introduction:** Brief description — syncs Asana tasks to bpkm:Task objects with configurable field mapping for status/priority. Seventh sync app.
   - **Prerequisites:** basic-pkm model installed, Asana account, either OAuth app credentials or a Personal Access Token.
   - **Installing:** Admin > Applications > install path `/app/apps/asana-sync`. Wait for "Running" status.
   - **Connecting — OAuth 2.0:** Enter Client ID and Client Secret, click "Connect with Asana", authorize in Asana. Tokens refresh automatically.
   - **Connecting — Personal Access Token:** Generate PAT in Asana Developer Console (My Settings > Apps > Manage Developer Apps > Personal Access Tokens). Paste into PAT field, verify connection.
   - **Selecting Workspaces and Projects:** Checkboxes grouped by workspace. Select which projects to sync.
   - **Discovering Custom Fields:** Click "Discover Fields" to scan selected projects for enum and number custom fields plus sections.
   - **Configuring Status Mapping:** 3 modes with explanation:
     - *Completed Only* — simplest. Asana completed=true → done, everything else → todo.
     - *Custom Field* — select an enum custom field (e.g., "Status"), map each value (e.g., "Not Started" → todo, "In Progress" → in-progress, "Completed" → done).
     - *Section-Based* — map project sections/columns (e.g., "To Do" → todo, "In Progress" → in-progress, "Done" → done). Status changes push back by moving the task between sections.
   - **Configuring Priority Mapping:** Select an enum priority field, map values (e.g., "High" → high, "Medium" → medium, "Low" → low).
   - **Story Points:** Select a number custom field for story point tracking (optional).
   - **Sync Configuration:** Sync direction (Pull Only / Bidirectional), poll interval (5m/15m/30m/1h).
   - **Manual Sync:** Sync Now button. Stats display (created/updated/unchanged/errors for pull, pushed/skipped/errors for push).
   - **Field Mapping Reference:** Two tables:
     - Core Properties table: Asana field → bpkm property (name→title, notes→body, due_on→dueDate, completed→taskStatus, assignee→assignedTo, tags→tags, followers→edges, permalink_url→externalUrl, gid→externalUuid, subtasks→dcterms:isPartOf, resource_subtype=milestone→bpkm:Milestone)
     - Status Modes table: Mode → Source → Push Behavior
   - **Subtask Nesting:** Up to 5 levels, linked via dcterms:isPartOf hierarchy.
   - **Troubleshooting:** Common issues (rate limiting 429, no custom fields found, connection expired, status not mapping).
   - **See Also:** Links to Ch 10 (Mental Models), Ch 34 (Todoist Sync for comparison), App Platform concepts.
   - **Navigation footer:** `**Previous:** [Chapter 39: CalDAV Calendar Sync](39-caldav-calendar-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

3. **Update `docs/guide/README.md`:** Add line after CalDAV entry:
   ```
   40. [Asana Sync](40-asana-sync.md)
   ```

4. **Update `docs/guide/appendix-d-glossary.md`:** Add "Asana Sync" entry in alphabetical position:
   ```
   **Asana Sync**
   A SemPKM app that synchronizes tasks from Asana workspaces and projects with `bpkm:Task` objects. Features configurable field mapping for status (via custom enum fields or project sections) and priority (via custom enum fields), subtask nesting up to 5 levels, and bidirectional sync with reverse field mapping including section-based status moves. Supports OAuth 2.0 and Personal Access Token authentication. See [Chapter 40: Asana Sync](40-asana-sync.md).
   ```

5. **Update `docs/guide/appendix-a-environment-variables.md`:** Add two rows after the OUTLOOK entries:
   ```
   | `ASANA_API_URL` | Base URL for Asana REST API v1.0. Override to redirect the Asana Sync app to a mock server for testing. | `https://app.asana.com/api/1.0` | No |
   | `ASANA_TOKEN_URL` | Asana OAuth token endpoint. Override for testing against a mock OAuth server. | `https://app.asana.com/-/oauth_token` | No |
   ```

6. **Update `docs/guide/39-caldav-calendar-sync.md`:** Change the navigation footer's "Next" link from Appendix A to Chapter 40:
   - Old: `**Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`
   - New: `**Next:** [Chapter 40: Asana Sync](40-asana-sync.md)`

7. **Verify:** All 5 files updated, nav chain is Ch 39 → Ch 40 → Appendix A, README has line 40, glossary has entry, appendix has 2 env var rows.

## Must-Haves

- [ ] Chapter 40 documents all 3 status mapping modes (completed_only, custom_field, section)
- [ ] Chapter 40 has field mapping reference tables (core properties + status modes)
- [ ] README TOC has line 40
- [ ] Glossary has "Asana Sync" entry cross-referencing Chapter 40
- [ ] Appendix A has ASANA_API_URL and ASANA_TOKEN_URL rows
- [ ] Navigation chain: Ch 39 Next → Ch 40, Ch 40 Previous → Ch 39, Ch 40 Next → Appendix A

## Verification

- `test -f docs/guide/40-asana-sync.md` — file exists
- `grep -c "completed_only\|custom_field\|section" docs/guide/40-asana-sync.md` — ≥ 3 (all 3 modes documented)
- `grep "40-asana-sync" docs/guide/README.md` — present
- `grep "Asana Sync" docs/guide/appendix-d-glossary.md` — present
- `grep "ASANA_API_URL" docs/guide/appendix-a-environment-variables.md` — present
- `grep "Chapter 40" docs/guide/39-caldav-calendar-sync.md` — present in nav footer
- `grep "Appendix A" docs/guide/40-asana-sync.md` — present in nav footer

## Inputs

- `docs/guide/39-caldav-calendar-sync.md` — reference structure, current nav footer to update
- `docs/guide/38-outlook-calendar-sync.md` — longer reference for field mapping tables
- `docs/guide/README.md` — current TOC for insertion point
- `docs/guide/appendix-a-environment-variables.md` — env var table format
- `docs/guide/appendix-d-glossary.md` — glossary entry format and alphabetical position
- `apps/asana-sync/services/field_mapper.py` — authoritative source for field mapping details
- `apps/asana-sync/frontend/templates/connect_status.html` — UI sections to document

## Expected Output

- `docs/guide/40-asana-sync.md` — ~400-450 line user guide chapter with field mapping walkthrough
- `docs/guide/README.md` — updated with line 40 entry
- `docs/guide/appendix-d-glossary.md` — updated with "Asana Sync" entry
- `docs/guide/appendix-a-environment-variables.md` — updated with 2 ASANA_ env var rows
- `docs/guide/39-caldav-calendar-sync.md` — updated navigation footer pointing to Ch 40

## Observability Impact

This task is documentation-only — no runtime code changes. No new logs, metrics, health endpoints, or error surfaces are introduced.

**Inspection:** Verify the nav chain is correct by grepping for navigation links: `grep -n "Previous\|Next" docs/guide/39-caldav-calendar-sync.md docs/guide/40-asana-sync.md`. Verify cross-references with `grep "40-asana-sync" docs/guide/README.md docs/guide/appendix-d-glossary.md`.
