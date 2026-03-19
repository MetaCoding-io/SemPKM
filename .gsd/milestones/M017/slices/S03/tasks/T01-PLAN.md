---
estimated_steps: 7
estimated_files: 4
---

# T01: Push sync engine with loop prevention and field mapper extensions

**Slice:** S03 — Push Sync + Settings Polish
**Milestone:** M017

## Description

Implement the push sync pipeline and supporting field mapper extensions. This is the core engine work: detecting locally-modified tasks via SPARQL, reverse-mapping their properties to GitHub's PATCH format, pushing changes via the REST API, updating `lastSyncedAt` timestamps to prevent re-import loops, and extending pull_sync with loop prevention. Follows the linear-sync `push_sync()` pattern closely but adapted for GitHub REST PATCH instead of GraphQL mutations.

## Steps

1. **Add `parse_external_url()` to `apps/github-sync/services/field_mapper.py`:**
   - Parse `https://github.com/{owner}/{repo}/issues/{number}` → `(owner, repo, number)`
   - Also handle `/pull/{number}` path (GitHub uses same PATCH endpoint for both)
   - Return `None` for invalid/unparseable URLs
   - Add tests in `backend/tests/test_github_field_mapper.py`: issue URL, PR URL, invalid URL, missing segments, non-GitHub URL

2. **Add `sync_time` parameter to `build_task_properties()` in field_mapper.py:**
   - Add `sync_time: str | None = None` parameter
   - If None, compute `datetime.now(timezone.utc).isoformat()`
   - Include `f"{BPKM}lastSyncedAt": sync_time` in the output properties dict (always present, not stripped)
   - Add test: `build_task_properties` output includes `lastSyncedAt` key
   - Note: `lastSyncedAt` should NOT be stripped even when other None values are — it's always set

3. **Extend `_find_existing_task()` in `apps/github-sync/services/sync_engine.py`:**
   - Add `OPTIONAL { ?task <{BPKM}lastSyncedAt> ?lastSynced }` to the SPARQL query
   - Include `"lastSyncedAt": row.get("lastSynced", {}).get("value")` in the return dict
   - Existing tests should still pass (new field is additive)

4. **Add `_find_changed_tasks(graph_client)` to sync_engine.py:**
   - SPARQL query matching tasks with `externalProvider "github"`, `externalUuid` present, `dcterms:modified > bpkm:lastSyncedAt` (or missing lastSyncedAt treated as changed)
   - Also fetch `externalUrl`, `externalId`, `title`, `taskStatus`, `tags`, `lastSyncedAt`
   - Filter: `FILTER(!BOUND(?syncDir) || ?syncDir != "pull-only")` and `FILTER(!BOUND(?lastSynced) || !BOUND(?modified) || STR(?modified) > STR(?lastSynced))`
   - Return list of dicts with: iri, externalUuid, externalUrl, externalId, status, title, tags, lastSyncedAt
   - Reference: `apps/linear-sync/services/sync_engine.py` lines 87-128 for the pattern

5. **Add `push_sync(ctx)` to sync_engine.py:**
   - Auth check via `get_connection_status()` → skip if not connected
   - Read `sync_direction` from `ctx.settings` → skip if "pull-only"
   - Call `_find_changed_tasks(ctx.graph)` → skip if empty
   - For each changed task:
     - Build task_props dict from SPARQL result fields
     - Call `build_issue_patch(task_props)` for reverse mapping
     - Call `parse_external_url(task["externalUrl"])` to get (owner, repo, number)
     - Call `github_client.patch_issue(owner, repo, number, patch_data)`
     - Build `object.patch` command to update `lastSyncedAt` on the task
     - Submit via `_submit_commands_batched()`
     - Wrap in try/except for per-task error isolation
   - Store `last_push_result` in `ctx.state` as JSON
   - Return structured result dict: `{status, pushed, skipped, errors, timestamp}`
   - Important: `sync_direction` is read from `ctx.settings` (not `ctx.state`) — the GitHub app uses `ctx.settings` for user preferences per research doc

6. **Add loop prevention to `pull_sync()`:**
   - After `existing = await _find_existing_task(ctx.graph, slug)`, check:
     - If `existing` and `existing.get("lastSyncedAt")` and issue has `updated_at`:
     - Compare: `issue["updated_at"] <= existing["lastSyncedAt"]`
     - If true: skip this issue (increment skipped_count, continue)
   - This prevents re-importing changes we just pushed
   - Test: create mock where existing task has lastSyncedAt > issue updated_at → verify skip

7. **Write ≥25 new tests:**
   - `TestParseExternalUrl`: issue URL, PR URL, invalid URL, non-github URL, missing segments, no path (≥5 tests)
   - `TestBuildTaskPropertiesLastSyncedAt`: lastSyncedAt present in output, custom sync_time used (≥2 tests)
   - `TestFindChangedTasks`: happy path returns tasks, empty result, query structure (≥3 tests)
   - `TestPushSync`: happy path, not connected skip, pull-only skip, no changed tasks, partial failure with errors, lastSyncedAt updated, parse_external_url failure handling (≥8 tests)
   - `TestLoopPrevention`: skip when updated_at <= lastSyncedAt, process when updated_at > lastSyncedAt, process when no lastSyncedAt (≥3 tests)
   - `TestPushSyncDiagnostics`: last_push_result contains status/pushed/errors/timestamp (≥1 test)

## Must-Haves

- [ ] `push_sync()` returns structured result with status, pushed count, errors
- [ ] `_find_changed_tasks()` SPARQL query filters by provider, modified > lastSyncedAt
- [ ] `parse_external_url()` handles both `/issues/N` and `/pull/N` paths
- [ ] `build_task_properties()` includes `bpkm:lastSyncedAt` in output
- [ ] `_find_existing_task()` returns `lastSyncedAt` field
- [ ] Loop prevention in pull_sync skips issues where updated_at <= lastSyncedAt
- [ ] `last_push_result` stored in StateClient as inspectable JSON
- [ ] ≥25 new tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_sync_engine.py tests/test_github_field_mapper.py -v` — all tests pass (existing + new)
- New test count ≥25
- `test_push_sync_diagnostics` (or similar) confirms `last_push_result` has status, pushed, errors, timestamp — proving failure-path inspectability

## Observability Impact

- Signals added: `last_push_result` StateClient key — JSON with status/pushed/skipped/errors/timestamp
- How a future agent inspects this: Read `last_push_result` from StateClient or view in settings UI (wired in T02)
- Failure state exposed: Per-task errors in `errors` list with IRI and error message

## Inputs

- `apps/github-sync/services/sync_engine.py` — existing pull_sync, _find_existing_task, _submit_commands_batched
- `apps/github-sync/services/field_mapper.py` — existing build_task_properties, build_issue_patch, REVERSE_STATUS_MAP
- `apps/github-sync/services/github_client.py` — existing GitHubClient.patch_issue()
- `apps/linear-sync/services/sync_engine.py` — reference pattern for _find_changed_tasks (lines 87-128) and push_sync (lines 238-350)
- `backend/tests/test_github_sync_engine.py` — existing mock infrastructure (MockAppContext, MockGraphClient, MockExternalHttpClient, MockStateClient, MockSettingsClient)
- S01/S02 summaries: `build_issue_patch()` reverse mapping already exists and is tested. `MockExternalHttpClient` uses ordered response queue. `_find_existing_task(provider=None)` variant available.

## Expected Output

- `apps/github-sync/services/field_mapper.py` — `parse_external_url()` added, `build_task_properties()` extended with sync_time/lastSyncedAt
- `apps/github-sync/services/sync_engine.py` — `_find_changed_tasks()`, `push_sync()` added, `_find_existing_task()` extended with lastSyncedAt, loop prevention in `pull_sync()`
- `backend/tests/test_github_field_mapper.py` — ≥7 new tests (parse_external_url + lastSyncedAt)
- `backend/tests/test_github_sync_engine.py` — ≥18 new tests (find_changed, push_sync, loop prevention, diagnostics)
