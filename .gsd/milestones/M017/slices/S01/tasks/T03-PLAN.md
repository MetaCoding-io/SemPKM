---
estimated_steps: 7
estimated_files: 7
---

# T03: Pull sync engine + app routes + templates

**Slice:** S01 — GitHub Client + PAT Auth + Issue Pull Sync
**Milestone:** M017

## Description

Wire the client, field mapper, auth, and person matcher into a complete pull sync engine, then build the app routes and templates that expose the user-facing connect → configure → sync flow. This is the integration task that makes the slice demo true: a user can install the app, enter a PAT, pick repos, and pull GitHub issues into SemPKM as bpkm:Task objects.

Key concern: the sync engine must record structured failure state in StateClient (`last_pull_result`) so that sync problems are diagnosable without reading logs. At least one test must assert this failure-reporting behavior.

Reference: `apps/linear-sync/services/sync_engine.py` (529 lines), `apps/linear-sync/app.py` (397 lines).

## Steps

1. **Write `apps/github-sync/services/sync_engine.py`:**
   - Read `apps/linear-sync/services/sync_engine.py` for structure reference — this is the most complex file
   - Import from sibling modules using try/except pattern (same as linear-sync):
     ```python
     try:
         from services.field_mapper import ...
     except ImportError:
         from field_mapper import ...
     ```
   - `BATCH_SIZE = 1000`
   - `async def _find_existing_task(graph_client, slug: str) -> dict | None` — SPARQL `SELECT ?iri ?title ?status WHERE { ?iri a <bpkm:Task> . FILTER(STRENDS(STR(?iri), "/Task/gh-{slug}")) }` — returns dict with `iri`, `title`, `status` or None
   - `async def _submit_commands_batched(http_client, commands: list) -> list` — POST to `/api/commands/bulk` in chunks of BATCH_SIZE. Returns list of all response results. Uses `http_client` directly (bypasses SDK CommandClient per D204 pattern).
   - `async def pull_sync(github_client, graph_client, http_client, state_client, settings_client, person_matcher) -> dict`:
     - Read `selected_repos` from settings_client (list of `"owner/repo"` strings)
     - Read `last_sync_at` from state_client for delta sync `since` param
     - For each repo: `fetch_issues(owner, repo, since=last_sync_at)`
     - Filter out PRs: `[i for i in issues if not is_pull_request(i)]`
     - For each issue (wrapped in try/except for per-issue error isolation):
       - Resolve assignee via PersonMatcher if present
       - Build properties via `build_task_properties()`
       - Compute slug via `compute_issue_slug()`
       - Check existing via `_find_existing_task()`
       - **New issues (not found):** collect `object.create` commands
       - **Existing issues:** collect `object.patch` commands, conditional `body.diff` if body changed
     - Phase 1: submit all `object.create` commands via `_submit_commands_batched()`
     - Phase 2: SPARQL lookup to discover minted IRIs for new issues, then submit `body.set` commands
     - Update `last_sync_at` in state_client to current timestamp
     - Write `last_pull_result` to state_client: `{"status": "success"|"partial"|"error", "created": N, "updated": N, "skipped": N, "errors": N, "failed_issues": ["owner/repo#42", ...], "duration_ms": N, "timestamp": ISO8601}`
     - Return the result dict
   - Logger: `github_sync.sync` at INFO for sync start/complete with counts

2. **Complete `apps/github-sync/app.py`:**
   - Read `apps/linear-sync/app.py` (397 lines) for structure reference
   - `github_sync_app = App()`
   - Route: `POST /_fragments/connect/api-key` — reads PAT from form data, stores via `store_pat()`, verifies via `verify_pat()`, returns updated connect fragment
   - Route: `GET /_fragments/connect` — renders `connect.html` or `connect_status.html` based on connection status
   - Route: `POST /_fragments/settings/sync-now` — triggers `pull_sync()`, returns updated status fragment
   - Route: `POST /_fragments/settings/repos` — saves selected repos to settings_client
   - Route: `POST /_fragments/connect/disconnect` — calls `disconnect()`, returns connect fragment
   - Task handler: `poll-tasks` — calls `pull_sync()` (registered via `@github_sync_app.task("poll-tasks")`)
   - Task handler: `push-changes` — stub that logs "push sync not implemented yet" (S03)
   - **All htmx URLs in templates use `/app/github-sync/` prefix** (critical — see knowledge entry "App template htmx URLs must use proxy prefix")

3. **Write `apps/github-sync/frontend/templates/connect.html`:**
   - Read `apps/linear-sync/frontend/templates/connect.html` (56 lines) for reference
   - PAT input form with `hx-post="/app/github-sync/_fragments/connect/api-key"`
   - Instructions: "Create a Personal Access Token at github.com/settings/tokens with `repo` scope"
   - Connection status indicator (green dot + username when connected)
   - Note about fine-grained PATs needing Issues read/write permission

4. **Write `apps/github-sync/frontend/templates/connect_status.html`:**
   - Read `apps/linear-sync/frontend/templates/connect_status.html` (177 lines) for reference
   - Connected status banner with username + masked PAT + disconnect button
   - **Repository selection:** checkboxes for each repo from `fetch_repos()`, pre-checked based on settings. `hx-post="/app/github-sync/_fragments/settings/repos"` on change.
   - **Sync Now button:** `hx-post="/app/github-sync/_fragments/settings/sync-now"`, shows loading indicator during sync
   - **Last sync stats panel:** created/updated/skipped/errors counts from `last_pull_result` StateClient data. Show "N issues synced" or "Sync failed: N errors" with error details if present. Last sync timestamp in relative format.
   - Sync direction section (placeholder text: "Pull only — push sync coming in a future update")

5. **Write `apps/github-sync/frontend/static/styles.css`:**
   - Copy `apps/linear-sync/frontend/static/styles.css` (497 lines), change branding tokens (accent colors, etc.)
   - Ensure repo checkbox list styles, stats panel styles, connection indicator styles are present

6. **Write `backend/tests/test_github_sync_engine.py` (~20+ tests):**
   - Load via importlib with dependency-order loading (field_mapper → person_matcher → github_client → auth → sync_engine) — same pattern as `backend/tests/test_sync_engine.py`
   - Mock graph_client, http_client, state_client, settings_client, person_matcher, github_client
   - Test groups:
     - **_find_existing_task** (~3 tests): found, not found, SPARQL error handling
     - **_submit_commands_batched** (~3 tests): single batch, multi-batch (>1000 commands), empty commands
     - **pull_sync basic** (~5 tests): new issues create tasks, existing issues update tasks, empty repo, multiple repos, delta sync uses since param
     - **PR filtering** (~2 tests): issues with `pull_request` key are skipped, count reflects skipped PRs
     - **Error isolation** (~3 tests): single issue failure doesn't abort sync, `last_pull_result` contains error_count and failed_issues list, all issues fail → status "error"
     - **last_pull_result diagnostics** (~3 tests): success result has correct structure, partial failure records failed issues, result includes duration_ms and timestamp
     - **Person matching integration** (~2 tests): assignee resolved via PersonMatcher, no assignee skips matching

7. **Run full verification:**
   - `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v`
   - Confirm ≥80 total tests with `pytest --co -q tests/test_github_*.py tests/test_github_sync_engine.py | tail -1`

## Must-Haves

- [ ] `pull_sync()` creates new tasks via two-phase bulk (D204 pattern)
- [ ] `pull_sync()` updates existing tasks via `object.patch`
- [ ] PR issues (with `pull_request` key) are skipped — not synced
- [ ] Delta sync uses `since` parameter from `last_sync_at` StateClient key
- [ ] Per-issue error isolation — single failure doesn't abort sync
- [ ] `last_pull_result` written to StateClient with structured error info (status, created, updated, errors, failed_issues, duration_ms)
- [ ] At least one test asserts `last_pull_result` error reporting on partial failure
- [ ] App routes: connect/api-key, settings, sync-now, repos, disconnect
- [ ] All htmx URLs prefixed with `/app/github-sync/`
- [ ] Templates: connect.html + connect_status.html with repo selection and sync stats

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -v` — all pass
- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v --tb=short` — ≥80 total tests, all passing
- Specifically confirm error isolation test exists: `pytest --co -q tests/test_github_sync_engine.py -k "error" | head`

## Observability Impact

- Signals added: `last_pull_result` StateClient key with structured JSON (status, counts, failed_issues, duration_ms, timestamp)
- How a future agent inspects this: Read `last_pull_result` from StateClient (visible in settings page sync stats panel, or query directly)
- Failure state exposed: Per-issue failures recorded with repo+number identifiers, overall status degrades from "success" → "partial" → "error" based on error ratio

## Inputs

- `apps/github-sync/services/github_client.py` — from T01, provides GitHubClient with fetch_issues(), fetch_repos()
- `apps/github-sync/services/field_mapper.py` — from T02, provides build_task_properties(), compute_issue_slug(), is_pull_request()
- `apps/github-sync/services/auth.py` — from T02, provides store_pat(), verify_pat(), get_connection_status(), disconnect()
- `apps/github-sync/services/person_matcher.py` — from T02, provides PersonMatcher
- `apps/linear-sync/services/sync_engine.py` — reference sync engine (529 lines) — clone and adapt
- `apps/linear-sync/app.py` — reference app routes (397 lines) — clone and adapt
- `apps/linear-sync/frontend/templates/` — reference templates — clone and adapt
- `backend/tests/test_sync_engine.py` — reference test structure for importlib loading

## Expected Output

- `apps/github-sync/services/sync_engine.py` — pull sync engine (~400 lines)
- `apps/github-sync/app.py` — app routes with connect, settings, sync-now (~350 lines)
- `apps/github-sync/frontend/templates/connect.html` — PAT connect form (~60 lines)
- `apps/github-sync/frontend/templates/connect_status.html` — settings + sync status page (~180 lines)
- `apps/github-sync/frontend/static/styles.css` — app styles (~500 lines)
- `backend/tests/test_github_sync_engine.py` — ~20+ tests including error isolation diagnostics
- Full slice passes with ≥80 tests across 5 test files
