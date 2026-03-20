---
estimated_steps: 6
estimated_files: 5
---

# T03: Write user guide Chapter 36 and update cross-references

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M023

## Description

Write the user guide chapter documenting Jira sync for end users. Chapter 36 follows the structure established by Chapter 35 (GitHub Sync) but covers Jira-specific concepts: statusCategory-based status normalization, Atlassian Document Format (ADF) conversion, JQL filter queries, Epic→Milestone mapping, and the 3-field authentication flow. Also update the README TOC, glossary, appendix-a (environment variables), and navigation chain between chapters.

## Steps

1. **Write `docs/guide/36-jira-sync.md`** (~300 lines) following Chapter 35's structure. Sections:

   **Title & intro:** "Chapter 36: Jira Sync" — the app connects Jira Cloud issues to SemPKM as `bpkm:Task` objects with bidirectional sync. Mention statusCategory-based status normalization, ADF→Markdown conversion, JQL filtering, and Epic→Milestone mapping.

   **Prerequisites:** (1) Basic PKM model installed (link to Ch 10). (2) Jira Cloud account (not Server/Data Center). (3) API token generated at `id.atlassian.com/manage-profile/security/api-tokens`. (4) Site URL (e.g., `yourcompany.atlassian.net`).

   **Installing the App:** Path `/app/apps/jira-sync`. Same instructions as Ch 35 pattern. Link to Ch 29 for troubleshooting.

   **Connecting to Jira:** 3-field form (email, API token, site URL). Auth method table: API token (Available), OAuth 2.0 (Not available — deferred per D236). Explain how to generate token. On success shows Connected badge, display name, site URL.

   **Project Selection:** After connecting, project list appears with checkboxes. Select projects to sync. Explain that only selected projects' issues are synced.

   **JQL Filter:** Optional JQL clause to restrict synced issues. Examples: `project = PROJ AND issuetype != Sub-task`, `priority in (High, Highest)`, `labels = "frontend"`. Link to Atlassian JQL docs. Explain that JQL is applied in addition to project selection, not instead of.

   **Sync Configuration:** Direction (pull-only, bidirectional). Poll interval (5m, 15m, 30m, 1h). Sync Now button.

   **Field Mapping:** Two tables:

   Status Mapping table (4 columns: Jira statusCategory.key, Example Jira Status Names, SemPKM Status, Notes):
   | statusCategory.key | Example Status Names | SemPKM Status | Notes |
   | `new` | To Do, Open, Backlog | `todo` | All "not started" statuses |
   | `indeterminate` | In Progress, In Review, QA | `in-progress` | All "in flight" statuses |
   | `done` | Done, Closed, Resolved | `done` | All "completed" statuses |

   Priority Mapping table:
   | Jira Priority | SemPKM Priority |
   | Highest, Critical, Blocker | `critical` |
   | High | `high` |
   | Medium | `medium` |
   | Low, Lowest, Trivial | `low` |

   **Understanding statusCategory:** Paragraph explaining that Jira allows custom status names per project, but every status belongs to exactly one of three categories (new/indeterminate/done). SemPKM uses `statusCategory.key` (not the status name) for reliable cross-project normalization. The actual status name is preserved in `bpkm:externalStatus` for display.

   **Other Mapped Fields:** Table covering: assignee (→ Person via accountId resolution), labels + components (→ tags), sprint (→ taskGroup), created/updated dates, external URL, external ID.

   **ADF Conversion Notes:** Jira Cloud uses Atlassian Document Format (ADF) — a JSON document tree — instead of Markdown. SemPKM automatically converts ADF to Markdown on import and Markdown back to ADF on push. List of supported node types: paragraphs, headings (1-6), bullet lists, ordered lists, code blocks, blockquotes, tables, horizontal rules, text with marks (bold, italic, code, link, strikethrough), mentions, inline cards. Unsupported nodes show `[unsupported: {type}]` placeholder. Note that media/attachments are not imported.

   **Push Sync:** When direction is bidirectional, changes to title, description, and priority push back to Jira. Status transitions are NOT pushed (per D237 — Jira requires valid workflow transition IDs which vary per project). Description push converts Markdown back to ADF.

   **Epic → Milestone Mapping:** Jira Epics are created as `bpkm:Milestone` objects instead of Tasks. Child issues of the Epic are linked to the Milestone. This preserves the hierarchical organization from Jira.

   **Issue Links — dependsOn Edges:** Jira "Blocks" issue links create `bpkm:dependsOn` edges between tasks. If Issue A "is blocked by" Issue B, a dependsOn edge is created from A to B. Other link types (Relates, Clones, Duplicates) are not currently mapped.

   **Troubleshooting:** Common issues: wrong site URL format, expired API token, permissions insufficient (need Browse Projects), JQL syntax errors, empty sync (check project selection), rate limiting.

   **Navigation footer:**
   ```
   **Previous:** [Chapter 35: GitHub Sync](35-github-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```

2. **Update `docs/guide/README.md`** — add entry after line with "35. [GitHub Sync]":
   ```
   36. [Jira Sync](36-jira-sync.md)
   ```

3. **Update `docs/guide/appendix-d-glossary.md`** — add 3 entries in alphabetical order:
   - **Atlassian Document Format (ADF):** JSON-based rich text format used by Jira Cloud. SemPKM's Jira Sync automatically converts ADF to Markdown and vice versa. See [Chapter 36](36-jira-sync.md).
   - **Jira Sync:** App that synchronizes Jira Cloud issues with SemPKM Task objects. Supports bidirectional sync with statusCategory-based status normalization and ADF→Markdown conversion. See [Chapter 36](36-jira-sync.md).
   - **statusCategory:** Jira's three-way classification of all statuses: `new` (not started), `indeterminate` (in progress), and `done` (completed). Used by SemPKM for reliable cross-project status normalization. See [Chapter 36](36-jira-sync.md).

4. **Update `docs/guide/appendix-a-environment-variables.md`** — add `JIRA_API_URL` entry following the pattern of existing entries (like `GITHUB_API_URL`):
   - `JIRA_API_URL`: Override the Jira REST API base URL. Used for testing with a mock server. Default: uses the site URL from the app's stored credentials.

5. **Update `docs/guide/35-github-sync.md`** navigation footer — change the "Next" link from Appendix A to Chapter 36:
   - Old: `**Previous:** [Chapter 34: Linear Sync](34-linear-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`
   - New: `**Previous:** [Chapter 34: Linear Sync](34-linear-sync.md) | **Next:** [Chapter 36: Jira Sync](36-jira-sync.md)`

6. **Verify all cross-references:**
   - README.md has "36. [Jira Sync]"
   - Ch 35 footer points to Ch 36
   - Ch 36 footer points to Ch 35 (prev) and Appendix A (next)
   - Glossary has all 3 entries
   - Appendix-a has JIRA_API_URL

## Must-Haves

- [ ] `docs/guide/36-jira-sync.md` exists with all required sections
- [ ] Status mapping table shows all 3 statusCategory.key values
- [ ] Priority mapping table covers all 8 Jira priority names
- [ ] ADF conversion notes list supported node types
- [ ] Push sync section clearly states status transitions are NOT pushed (D237)
- [ ] Epic→Milestone mapping documented
- [ ] Issue links (Blocks→dependsOn) documented
- [ ] README.md TOC includes Chapter 36
- [ ] Glossary has Atlassian Document Format, Jira Sync, statusCategory entries
- [ ] Appendix-a has JIRA_API_URL
- [ ] Navigation chain: Ch 35 → Ch 36 → Appendix A

## Verification

- `test -f docs/guide/36-jira-sync.md` → exists
- `grep "36.*Jira" docs/guide/README.md` → found
- `grep -ci "jira sync" docs/guide/appendix-d-glossary.md` → ≥ 1
- `grep -ci "statusCategory" docs/guide/appendix-d-glossary.md` → ≥ 1
- `grep -ci "atlassian document format" docs/guide/appendix-d-glossary.md` → ≥ 1
- `grep "JIRA_API_URL" docs/guide/appendix-a-environment-variables.md` → found
- `grep "Chapter 36" docs/guide/35-github-sync.md` → found (in Next link)
- `grep "Appendix A" docs/guide/36-jira-sync.md` → found (in Next link)
- `grep "Chapter 35" docs/guide/36-jira-sync.md` → found (in Previous link)

## Inputs

- `docs/guide/35-github-sync.md` — reference chapter to follow (~309 lines, same structure)
- `docs/guide/README.md` — TOC to update (line 64 has Ch 35 entry)
- `docs/guide/appendix-d-glossary.md` — glossary to extend
- `docs/guide/appendix-a-environment-variables.md` — env var reference to extend
- `apps/jira-sync/services/field_mapper.py` — STATUS_MAP (new→todo, indeterminate→in-progress, done→done), PRIORITY_MAP (Highest/Critical/Blocker→critical, High→high, Medium→medium, Low/Lowest/Trivial→low), REVERSE_STATUS_MAP, REVERSE_PRIORITY_MAP
- `apps/jira-sync/services/adf_converter.py` — supported ADF node types list for the conversion notes section
- Decision D235: statusCategory.key normalization rationale
- Decision D237: push sync limited to title/description/priority (no status transitions)
- Decision D239: custom ADF converter (not library)
- Decision D240: inward-only dedup for issue links

## Observability Impact

This task is documentation-only — no runtime behavior changes. No new logs, metrics, or status endpoints are introduced.

- **Signals that change:** None (static docs files only).
- **How to inspect:** `test -f docs/guide/36-jira-sync.md` confirms the chapter exists. `grep` commands in Verification confirm cross-references are wired.
- **Failure visibility:** Broken cross-references manifest as 404s in any docs-serving tool; missing glossary entries are detectable via `grep`. No runtime failure modes — these are static Markdown files.

## Expected Output

- `docs/guide/36-jira-sync.md` — new chapter (~300 lines)
- `docs/guide/README.md` — modified (1 line added to TOC)
- `docs/guide/appendix-d-glossary.md` — modified (3 entries added)
- `docs/guide/appendix-a-environment-variables.md` — modified (1 entry added)
- `docs/guide/35-github-sync.md` — modified (navigation footer updated)
