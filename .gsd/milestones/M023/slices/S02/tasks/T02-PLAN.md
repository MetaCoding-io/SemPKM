---
estimated_steps: 7
estimated_files: 1
---

# T02: Comprehensive unit tests for Jira sync engine

**Slice:** S02 — Pull sync + settings UI
**Milestone:** M023

## Description

Write 60+ unit tests for the Jira sync engine in `backend/tests/test_jira_sync_engine.py`. Tests use mock clients (MockStateClient, MockSettingsClient, MockGraphClient, MockHttpClient) following the established pattern from `backend/tests/test_gcal_sync_engine.py`. Cover all sync paths: basic pull, Epic→Milestone, Epic→child linking, ADF description conversion, assignee resolution, JQL construction variants, delta sync, loop prevention, error isolation, skip conditions, and app.py handler wiring.

**Relevant skills:** `test` — load for test generation patterns

## Steps

1. **Set up importlib module loading** — copy the pattern from `backend/tests/test_gcal_sync_engine.py` lines 1-55. Load modules in dependency order:
   - `adf_converter` → `field_mapper` → `jira_client` → `auth` → `person_matcher` → `sync_engine`
   - Path: `apps/jira-sync/services/`
   - Import the key functions: `pull_sync`, `push_sync`, `_find_existing_task`, `_find_existing_milestone`, `_build_jql`, `_build_create_command`, `_build_update_commands`, `_submit_commands_batched`, `BATCH_SIZE`, `BPKM`, `compute_issue_slug`

2. **Build mock client classes:**
   - `MockStateClient` — in-memory dict with `async get(key)` and `async set(key, value)`. Pre-populated with data dict.
   - `MockSettingsClient` — same interface but separate from state (simulates the `settings:` prefix separation). The sync engine reads config from `ctx.settings` and runtime state from `ctx.state`.
   - `MockGraphClient` — returns SPARQL results based on query analysis:
     - `slug_map`: slug string → `{"iri": ..., "status": ..., "lastSyncedAt": ...}` for `_find_existing_task` (detects `STRENDS` + `/Task/` in query)
     - `milestone_slug_map`: slug string → `{"iri": ...}` for `_find_existing_milestone` (detects `STRENDS` + `/Milestone/` in query)
     - `email_to_iri`: email → Person IRI for PersonMatcher SPARQL lookup
     - Records all queries for assertion
   - `MockHttpClient` — records `post()` calls, returns `MockResponse(200, {})`. Stores `recorded_calls` list of `(url, json_payload)`.
   - `MockCommandClient` — has `_client` attribute pointing to MockHttpClient (sync engine accesses `ctx.commands._client` for bulk bypass)
   - `MockJiraClient` — mock for `search_all_issues(jql)`, `get_user(account_id)`, `get_projects()`. Returns canned data from init.
   - `MockAppContext` — combines all mock clients into a `ctx` object with `.state`, `.settings`, `.graph`, `.commands`, `.http` attributes
   - `MockResponse` — simple class with `status_code`, `json()` method, `raise_for_status()`. Use `data if data is not None else {}` pattern (KNOWLEDGE.md K002).

3. **Helper to build Jira issue fixtures:**
   - `_make_issue(key, summary, ...)` — builds a realistic Jira issue dict with nested `fields` structure including `status.statusCategory.key`, `priority.name`, `issuetype.name`, `assignee.accountId`, `description` (ADF doc), `labels`, `components`, `sprint`, `parent`, `duedate`, `updated`. Default to a standard task issue type.
   - `_make_epic(key, summary, ...)` — builds an Epic issue (issuetype.name = "Epic")
   - `_make_adf_doc(text)` — builds a minimal ADF document with a paragraph containing text

4. **Write test categories (60+ tests total):**

   **a) SPARQL helpers (~8 tests):**
   - `_find_existing_task` — found by slug, not found, returns all fields
   - `_find_existing_milestone` — found by slug, not found
   - `_build_jql` — projects only, projects + user filter, projects + delta, projects + filter + delta, empty projects, JQL date format (no T, no timezone, no seconds)

   **b) Command builders (~4 tests):**
   - `_build_create_command` — Task type, Milestone type
   - `_build_update_commands` — with/without description, with/without assignee

   **c) Pull sync happy path (~10 tests):**
   - Basic pull: 2 issues → 2 tasks created with correct properties
   - Pull with ADF description → body.set command includes markdown
   - Pull with assignee → edge.create with assignedTo predicate
   - Pull with labels + components → tags in properties
   - Pull with sprint → taskGroup in properties
   - Pull with due date → dueDate in properties
   - Update existing task (slug exists in graph) → object.patch
   - Empty issue list → ok with 0 counts
   - Verify result dict has correct keys: status, created, updated, skipped, errors, failed_issues, duration_ms

   **d) Epic→Milestone (~8 tests):**
   - Epic detected by issuetype.name "Epic" → creates Milestone object (not Task)
   - Epic uses build_milestone_properties() — verify milestoneStatus, targetDate
   - Non-Epic issues remain as Tasks
   - Mixed batch: 1 Epic + 2 Tasks → 1 Milestone + 2 Tasks
   - Epic→child linking via `fields.parent.key` → edge.create with bpkm:milestone predicate
   - Epic→child linking via `fields.customfield_10014` (classic Epic Link)
   - Child issue with no parent → no milestone edge
   - Epic parent not in synced set → no milestone edge created (no error)

   **e) Delta sync + loop prevention (~6 tests):**
   - Delta sync: last_sync_at set → JQL includes `AND updated >= "..."` with correct date format
   - First sync: no last_sync_at → full sync (no updated filter)
   - Loop prevention: issue.updated <= existing.lastSyncedAt → skipped (unchanged count++)
   - Loop prevention: issue.updated > existing.lastSyncedAt → updated
   - Loop prevention: new issue (no existing) → always created

   **f) JQL construction (~6 tests):**
   - Projects only: `project in (PROJ1, PROJ2)`
   - Projects + user JQL: `project in (PROJ1) AND (status = Open)`
   - Projects + delta: `project in (PROJ1) AND updated >= "2026/03/19 15:30"`
   - Projects + user JQL + delta: all three combined
   - Single project: `project in (PROJ1)` (not `project = PROJ1`)
   - JQL date format strips ISO T and timezone: `2026-03-19T15:30:45+00:00` → `2026/03/19 15:30`

   **g) Skip conditions (~6 tests):**
   - Not connected → status "skipped", reason "not connected"
   - No projects selected → status "skipped" or status "success" with 0 counts
   - Sync direction pull-only → pull runs (direction doesn't affect pull)
   - Empty selected_projects JSON → skip

   **h) Error isolation (~5 tests):**
   - One issue raises exception → other issues still processed, error recorded
   - PersonMatcher failure → issue still created without assignee edge
   - ADF conversion failure → issue still created without body
   - Error result includes issue key in failed_issues list

   **i) Push sync stub (~3 tests):**
   - push_sync returns status "skipped" when not connected
   - push_sync returns status "skipped" with reason when pull-only
   - push_sync returns status "skipped" with "not yet implemented" reason

   **j) App.py wiring (~5 tests):**
   - sync_now calls pull_sync and stores result
   - sync_now with bidirectional calls both pull_sync and push_sync
   - poll-tasks calls pull_sync
   - push-changes calls push_sync
   - sync_now stores last_sync_at timestamp

5. **Verify all existing S01 tests still pass alongside new tests:**
   - Run `pytest tests/test_jira_*.py -v` to confirm no regressions

6. **Verify test count meets target:**
   - `pytest tests/test_jira_sync_engine.py -v --co | wc -l` should show 60+

7. **Run full combined suite:**
   - `pytest tests/test_jira_*.py -v` — should show ~300+ tests passing (237 S01 + 60+ S02)

## Must-Haves

- [ ] importlib-based module loading for apps/jira-sync/services/ (matches existing test pattern)
- [ ] MockStateClient, MockSettingsClient, MockGraphClient, MockHttpClient, MockCommandClient, MockJiraClient, MockAppContext classes
- [ ] MockResponse uses `data if data is not None else {}` (not `data or {}`) per KNOWLEDGE.md K002
- [ ] Jira issue fixture builders (_make_issue, _make_epic, _make_adf_doc)
- [ ] Tests cover all 10 categories listed above (a-j)
- [ ] 60+ tests total, all passing
- [ ] No regressions in existing S01 test files

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023/backend && .venv/bin/python -m pytest tests/test_jira_sync_engine.py -v` — 60+ tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023/backend && .venv/bin/python -m pytest tests/test_jira_*.py -v` — ~300+ tests pass (no regressions)
- `wc -l backend/tests/test_jira_sync_engine.py` — significant file (1000+ lines expected)

## Inputs

- `apps/jira-sync/services/sync_engine.py` — T01 output: pull_sync, push_sync, SPARQL helpers, command builders, JQL builder
- `apps/jira-sync/services/field_mapper.py` — BPKM constant, compute_issue_slug, build_task_properties, build_milestone_properties (S01)
- `apps/jira-sync/services/adf_converter.py` — adf_to_markdown (S01)
- `apps/jira-sync/services/jira_client.py` — JiraClient, error hierarchy (S01)
- `apps/jira-sync/services/auth.py` — get_connection_status (S01)
- `apps/jira-sync/services/person_matcher.py` — PersonMatcher (S01)
- `backend/tests/test_gcal_sync_engine.py` — reference for mock client patterns and test structure (~2035 lines)
- `backend/tests/test_jira_field_mapper.py` — reference for Jira issue fixture structure (S01)

## Expected Output

- `backend/tests/test_jira_sync_engine.py` — new file, ~1500 lines, 60+ unit tests covering all sync engine paths with mock clients

## Observability Impact

- **Test signals:** 95 unit tests covering all sync engine code paths — SPARQL helpers, command builders, JQL construction, pull sync happy/error/skip paths, Epic→Milestone creation, delta sync, loop prevention, push stub, and app wiring. Run via `pytest tests/test_jira_sync_engine.py -v`.
- **Failure visibility:** Test failures surface specific sync engine regressions by category (SPARQL, JQL, command builder, pull path, push stub, error isolation). Each test class maps to a sync engine capability.
- **Mock coverage:** MockGraphClient distinguishes Task vs Milestone SPARQL lookups, MockResponse follows K002 (data if data is not None else {}), MockAppContext separates state/settings clients matching real SDK separation.
- **No runtime impact:** This task adds only test code — no production behavior changes.
