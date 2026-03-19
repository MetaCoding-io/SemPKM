---
id: T03
parent: S01
milestone: M017
provides:
  - pull_sync() engine with two-phase bulk create, delta sync, per-issue error isolation
  - App routes for connect/api-key, settings/repos, sync-now, disconnect
  - Frontend templates (connect.html + connect_status.html) with repo selection and sync stats
  - last_pull_result structured diagnostic surface in StateClient
key_files:
  - apps/github-sync/services/sync_engine.py
  - apps/github-sync/app.py
  - apps/github-sync/frontend/templates/connect.html
  - apps/github-sync/frontend/templates/connect_status.html
  - apps/github-sync/frontend/static/styles.css
  - backend/tests/test_github_sync_engine.py
key_decisions:
  - Used ctx-based API (matching linear-sync pattern) rather than explicit params for pull_sync — simpler routes and task handler integration
  - GitHub repos stored in settings_client (prefixed) vs state_client — matches SDK convention for user-configurable data
patterns_established:
  - MockExternalHttpClient with ordered response queue for testing multi-step API flows (verify_token + fetch_issues)
  - MockResponse must use `data if data is not None else {}` not `data or {}` to handle empty list responses correctly
observability_surfaces:
  - StateClient key `last_pull_result` — JSON with status/created/updated/skipped/errors/failed_issues/duration_ms/timestamp
  - StateClient key `last_sync_at` — ISO-8601 timestamp for delta sync
  - Logger `github_sync.sync` at INFO for sync start/complete with counts
duration: 30m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Pull sync engine + app routes + templates

**Wired GitHub client, field mapper, auth, and person matcher into a complete pull sync engine with app routes, templates, and 26 sync engine tests — 124 total tests passing across all 5 github-sync test files.**

## What Happened

Built the sync engine (`sync_engine.py`) following the linear-sync reference pattern adapted for GitHub's REST API. Key differences: repos come from settings (not teams), issues are fetched per-repo with PR filtering, and `get_connection_status` takes both state_client and github_client (since GitHub auth uses PAT verification vs Linear's stored auth_method flag).

The `pull_sync()` function implements the full pipeline: auth check → read selected repos from settings → fetch issues per repo with delta sync `since` parameter → filter out PRs → resolve assignees via PersonMatcher → build properties via field mapper → two-phase bulk create for new issues (object.create → SPARQL discover IRI → body.set) → object.patch + body.set for existing issues → write `last_pull_result` structured diagnostic to StateClient.

Per-issue error isolation wraps each issue's processing in try/except, recording failures in the `failed_issues` list. The overall status degrades from "success" → "partial" → "error" based on whether any issues were created/updated alongside errors.

App routes handle the complete user flow: POST api-key stores and verifies PAT, POST repos saves selected repos, POST sync-now triggers pull_sync, POST disconnect clears credentials. Task handlers registered for poll-tasks (calls pull_sync) and push-changes (stub for S03).

Templates use `/app/github-sync/` prefix for all htmx URLs per the knowledge entry. connect.html has the PAT form, connect_status.html has repo checkboxes, sync stats panel, and disconnect button.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py -v` — 26/26 pass
- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` — 124/124 pass
- `pytest --co -q tests/test_github_sync_engine.py -k "error"` — 4 error-related tests collected (error isolation, partial failure, all-fail, SPARQL error)
- Diagnostic check: `test_partial_failure_diagnostics` asserts `last_pull_result` contains error count, failed_issues list, duration_ms, and timestamp when individual issue processing fails

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `pytest tests/test_github_sync_engine.py -v` | 0 | ✅ pass | 0.08s |
| 2 | `pytest tests/test_github_*.py tests/test_github_sync_engine.py -v` | 0 | ✅ pass | 0.14s |
| 3 | `pytest --co -q tests/test_github_sync_engine.py -k "error"` | 0 | ✅ pass (4 collected) | 0.02s |
| 4 | `pytest --co -q tests/test_github_*.py` (total count) | 0 | ✅ 124 tests | 0.05s |

## Diagnostics

- **last_pull_result** in StateClient: JSON with `{status, created, updated, skipped, errors, failed_issues, duration_ms, timestamp}`. Read via `ctx.state.get("last_pull_result")`. Visible in connect_status.html sync stats panel.
- **last_sync_at** in StateClient: ISO-8601 timestamp. Used as `since` param for delta sync on next run.
- **Logger `github_sync.sync`**: INFO at sync start (repo list) and completion (counts). WARNING for per-issue failures with issue reference.
- **Failure state**: `failed_issues` contains strings like `"owner/repo#42"` or `"owner/repo(fetch)"` for repo-level failures. Status field shows "success" / "partial" / "error".

## Deviations

- Plan specified explicit params for `pull_sync(github_client, graph_client, ...)` — used `pull_sync(ctx)` instead to match the linear-sync pattern and SDK's AppContext convention. Routes and task handlers naturally pass ctx.
- Plan mentioned `body.diff` for existing issues — used `body.set` instead since body.diff requires the previous body content which isn't tracked. Simpler and correct for idempotent updates.
- Plan estimated ~400 lines for sync_engine.py — actual is ~280 lines due to simpler GitHub REST flow vs Linear's GraphQL pagination.

## Known Issues

None.

## Files Created/Modified

- `apps/github-sync/services/sync_engine.py` — Pull sync engine with two-phase bulk, delta sync, per-issue error isolation
- `apps/github-sync/app.py` — Complete app routes (connect, repos, sync-now, disconnect) + task handlers
- `apps/github-sync/frontend/templates/connect.html` — PAT input form with fine-grained token instructions
- `apps/github-sync/frontend/templates/connect_status.html` — Connected status with repo checkboxes, sync stats, disconnect
- `apps/github-sync/frontend/static/styles.css` — Scoped styles for github-sync settings UI
- `backend/tests/test_github_sync_engine.py` — 26 tests covering find_existing_task, submit_commands_batched, pull_sync, PR filtering, error isolation, diagnostics, person matching
