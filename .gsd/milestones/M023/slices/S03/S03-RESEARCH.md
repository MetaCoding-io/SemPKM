# S03: Push sync + issue links — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

S03 is straightforward application of established push sync patterns already implemented in Linear (M016) and GitHub (M017) sync apps. The Jira sync engine has a `push_sync` stub that checks auth and sync_direction — S03 replaces it with a real implementation following the identical `_find_changed_tasks` → reverse map → API update → lastSyncedAt update pipeline. The Jira-specific addition is description push via `markdown_to_adf()` conversion (already built in S01's `adf_converter.py`).

Issue link processing during pull sync is also well-understood — Jira's `issuelinks` array is available on every issue from the `search_all_issues()` call (which uses `fields: ["*all"]`). Issue links of type "Blocks" map to `bpkm:dependsOn` edges between the corresponding Task objects. This is simpler than GitHub's timeline-based PR-to-issue linking because the link data is already present in the search results (no extra API call needed).

All building blocks exist: `build_issue_patch()` in field_mapper.py (title + priority reverse mapping), `markdown_to_adf()` in adf_converter.py, `JiraClient.update_issue()` in jira_client.py, `_find_existing_task()` in sync_engine.py, and the test mock infrastructure (MockGraphClient, MockAppContext, etc.) in test_jira_sync_engine.py.

## Recommendation

Two independent work units:

1. **Push sync** — Replace `push_sync()` stub with real implementation. Add `_find_changed_tasks()` SPARQL query for Jira-provider tasks (clone from Linear/GitHub pattern). For each changed task: extract externalId (issue key), build `build_issue_patch()` for title/priority, read body via SPARQL (`urn:sempkm:body`), convert via `markdown_to_adf()`, call `JiraClient.update_issue()`. Update `lastSyncedAt` on pushed task.

2. **Issue links** — Add `_process_issue_links()` to pull_sync that runs after Phase 2. For each issue, iterate `fields.issuelinks`, filter for link type name "Blocks", extract linked issue key, look up the corresponding Task IRI via `_find_existing_task()`, create `bpkm:dependsOn` edge command. This is a pull-side addition — no new Jira API calls needed since issuelinks are already in the search response.

## Implementation Landscape

### Key Files

- `apps/jira-sync/services/sync_engine.py` — Replace `push_sync()` stub (lines 352-382) with real implementation. Add `_find_changed_tasks()` SPARQL function. Add `_process_issue_links()` helper for pull_sync. Current file is ~380 lines, will grow to ~550-600.
- `apps/jira-sync/services/field_mapper.py` — `build_issue_patch()` already exists (lines 368-403) handling title + priority. Needs extension to include description (as ADF dict). Add `parse_external_id()` helper to extract issue key from externalId property.
- `apps/jira-sync/services/adf_converter.py` — `markdown_to_adf()` already exists (line 356+). No changes needed.
- `apps/jira-sync/services/jira_client.py` — `update_issue(issue_key, fields)` already exists (line 195). No changes needed.
- `backend/tests/test_jira_sync_engine.py` — Currently 95 tests, 2328 lines. Add ~50+ new tests for push sync real implementation, `_find_changed_tasks`, issue link processing, and edge cases.

### Reference Implementations

- `apps/linear-sync/services/sync_engine.py` lines 87-130 — `_find_changed_tasks()` SPARQL pattern: select tasks where `externalProvider = "linear"` AND (`dcterms:modified > bpkm:lastSyncedAt` OR no lastSyncedAt). Returns iri, externalUuid, status, priority, title, dueDate, lastSyncedAt.
- `apps/linear-sync/services/sync_engine.py` lines 238-350 — `push_sync()` pipeline: auth check → direction check → find changed → for-each reverse map + mutation + lastSyncedAt update → store result.
- `apps/github-sync/services/sync_engine.py` lines 181-225 — `_find_changed_tasks()` SPARQL (nearly identical to Linear, adds externalUrl for URL parsing).
- `apps/github-sync/services/sync_engine.py` lines 555-595 — Phase 3 `bpkm:dependsOn` edge creation from timeline cross-references.

### Build Order

1. **Push sync first** (higher risk, requires SPARQL + API + ADF conversion integration). Add `_find_changed_tasks()` SPARQL query, real `push_sync()` implementation, and unit tests. This proves the bidirectional sync loop.

2. **Issue links second** (lower risk, pull-side only, no new API calls). Add issue link processing to pull_sync and unit tests. This is additive — doesn't change existing pull_sync behavior for non-linked issues.

### Verification Approach

- `pytest backend/tests/test_jira_sync_engine.py -v` — all existing 95 tests must still pass (regression), plus ~50 new tests
- `pytest backend/tests/test_jira_*.py -v` — combined suite (~380+ tests)
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read())"` — valid Python
- New tests must cover:
  - `_find_changed_tasks`: no tasks, one changed, one unchanged (modified <= lastSyncedAt), pull-only direction filter
  - `push_sync` happy path: find changed → reverse map → update_issue called with correct fields dict including ADF description
  - `push_sync` with description: body text queried via SPARQL, converted to ADF, included in update_issue fields
  - `push_sync` loop prevention: lastSyncedAt updated after push so next pull_sync skips re-import
  - `push_sync` error isolation: one task fails, others continue
  - `push_sync` skip conditions: not connected, pull-only, no changed tasks
  - Issue link processing: "Blocks" type → dependsOn edge, other types ignored, linked issue not synced → skip, duplicate link handling

## Constraints

- **D237: Push limited to title/description/priority** — no status transitions. `build_issue_patch()` already enforces this. Description push uses `markdown_to_adf()` → Jira's `description` field (ADF format).
- **Jira update_issue expects ADF for description** — `PUT /rest/api/3/issue/{key}` requires `fields.description` to be an ADF document dict, not Markdown text. Must convert via `markdown_to_adf()`.
- **`externalId` stores the issue key** (e.g., "PROJ-123") — push sync uses this to call `update_issue(issue_key, fields)`. No URL parsing needed (unlike GitHub which parses owner/repo/number from URL).
- **Body stored at `urn:sempkm:body` predicate** — SPARQL query in `_find_changed_tasks` needs to OPTIONAL-bind this predicate to get description text for ADF conversion.
- **Result dict must use `status: "success"` not `"ok"`** — S02 forward intelligence notes this for connect_status.html template compatibility. However, Linear/GitHub push sync uses `"ok"` — check which the Jira template expects and be consistent.
- **`ctx.settings` for config, `ctx.state` for runtime** — S02 established this split. Push sync reads `sync_direction` from `ctx.settings`, stores `last_push_result` in `ctx.state`.

## Common Pitfalls

- **Result dict status string mismatch** — Linear push uses `"ok"`, Jira pull uses `"success"`. The Jira connect_status.html template checks for `"success"` in its conditional rendering. Use `"success"` for consistency with pull_sync's result format.
- **Issue link directionality** — Jira issuelinks have `inwardIssue` and `outwardIssue`. For "Blocks" link type: the outward issue is the blocker, the inward issue is blocked. `dependsOn` source should be the blocked task (inward), target the blocker (outward). Alternatively: iterate all issuelinks on the current issue, if the current issue IS the blocker (outwardIssue), the dependent is the other issue (inwardIssue), and vice versa.
- **Issue link type name variations** — The "Blocks" link type may be named differently in localized Jira instances. Match against `type.name` containing "block" (case-insensitive) for robustness.
- **Duplicate edge commands** — If issue A blocks B, both A and B have the same link in their `issuelinks` array (one as inward, one as outward). The edge creation should deduplicate, or process links only from one direction (e.g., only when the current issue has the `outwardIssue` entry — meaning it IS the blocker).

## Sources

- `apps/linear-sync/services/sync_engine.py` — Reference push_sync implementation (lines 238-350)
- `apps/github-sync/services/sync_engine.py` — Reference push_sync + dependsOn edge creation (lines 234-595)
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §4 — Jira field mapping table, `issuelinks (blocks) → bpkm:dependsOn`
