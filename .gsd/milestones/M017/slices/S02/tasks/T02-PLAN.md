---
estimated_steps: 8
estimated_files: 4
---

# T02: Wire PR sync and edge creation into pull_sync() with tests

**Slice:** S02 — PR Pull Sync + PR-to-Issue Edge Linking
**Milestone:** M017

## Description

Modify the sync pipeline to include PRs as tasks and create `bpkm:dependsOn` edges from PR tasks to issue tasks based on timeline API cross-references. This is the integration task that consumes the pure functions from T01.

Key changes: (1) remove PR skip filter, (2) add optional `provider` param to `_find_existing_task()`, (3) add phase 3 link-discovery loop, (4) extend `_make_result()` with `edges_created`, (5) modify existing PR-filtering tests, (6) add ~17 new tests.

**Important mock pattern note from S01 Forward Intelligence:** `MockExternalHttpClient` response queue is order-sensitive. Adding timeline API calls changes the response sequence. Tests must carefully order mock responses: `verify_token → fetch_issues(repo1) → fetch_issues(repo2) → timeline(issue1) → timeline(issue2) → ...`. The `MockGraphClient.slug_map` must include both issue and PR slugs for edge creation tests.

## Steps

1. **Modify `_find_existing_task()` to accept optional `provider` parameter** in `apps/github-sync/services/sync_engine.py`:
   - Add `provider: str | None = "github"` parameter
   - When `provider` is not None, include `?task <{BPKM}externalProvider> "{provider}" .` in SPARQL (existing behavior)
   - When `provider` is None, omit the provider filter — lookup by slug only (for phase 3 edge resolution where we need to find tasks regardless of whether they're issues or PRs)
   - This is the simplest approach per research — slug is unique via SHA-256 hash

2. **Remove PR skip filter from `pull_sync()`**:
   - Delete the lines: `real_issues = [i for i in issues if not is_pull_request(i)]` and `skipped_count += len(issues) - len(real_issues)`
   - Process all items (issues and PRs) in the same loop — `build_task_properties()` already sets `externalProvider: "github-pr"` for PRs via `is_pull_request()`
   - Track which items are issues (not PRs) for timeline queries: maintain a `synced_issues: list[tuple[str, int]]` collecting `(repo_full_name, issue_number)` for non-PR items

3. **Add phase 3 link-discovery after phases 1+2**:
   - Import `fetch_timeline` pattern: create a new `GitHubClient` instance isn't needed — reuse the `github_client` already instantiated at the top of `pull_sync()`
   - Import `extract_linked_issue_numbers` from field_mapper (add to the try/except import block at top of file)
   - After all create/update commands are submitted, iterate `synced_issues`:
     ```python
     edges_created = 0
     for repo_full_name, issue_number in synced_issues:
         try:
             timeline = await github_client.fetch_timeline(owner, repo, issue_number)
             linked_prs = extract_linked_issue_numbers(timeline, repo_full_name)
             for pr_repo, pr_number in linked_prs:
                 pr_slug = compute_issue_slug(pr_repo, pr_number)
                 pr_task = await _find_existing_task(ctx.graph, pr_slug, provider=None)
                 if not pr_task:
                     logger.debug("PR task not found for %s#%d, skipping edge", pr_repo, pr_number)
                     continue
                 # Find the issue task IRI
                 issue_slug = compute_issue_slug(repo_full_name, issue_number)
                 issue_task = await _find_existing_task(ctx.graph, issue_slug, provider=None)
                 if not issue_task:
                     logger.debug("Issue task not found for %s#%d, skipping edge", repo_full_name, issue_number)
                     continue
                 edge_commands.append({
                     "command": "edge.create",
                     "params": {
                         "source": pr_task["iri"],
                         "target": issue_task["iri"],
                         "predicate": f"{BPKM}dependsOn",
                     },
                 })
                 edges_created += 1
         except Exception as exc:
             logger.warning("Error fetching timeline for %s#%d: %s", repo_full_name, issue_number, exc)
             error_count += 1
             failed_issues.append(f"{repo_full_name}#{issue_number}(timeline)")
     ```
   - Submit edge commands via `_submit_commands_batched()`
   - Note: `owner, repo` must be extracted from `repo_full_name` via split — same pattern used earlier in the function

4. **Extend `_make_result()` with `edges_created` parameter**:
   - Add `edges_created: int = 0` parameter to `_make_result()`
   - Include `"edges_created": edges_created` in the result dict
   - Pass `edges_created` count from phase 3 into the result
   - This extends the diagnostic surface so S04 E2E and future agents can verify edge creation

5. **Update `field_mapper` imports in `sync_engine.py`**:
   - Add `extract_linked_issue_numbers` to both the try and except import blocks

6. **Update existing PR-filtering tests in `TestPRFiltering`**:
   - `test_prs_are_skipped` → rename to `test_prs_are_created_as_tasks` — verify that PRs are now created (not skipped), assert `result["created"]` includes the PR count
   - `test_all_prs_yields_zero_created` → rename to `test_all_prs_creates_pr_tasks` — verify PRs are created as tasks with correct count
   - Both tests need their mock responses updated: after `fetch_issues`, the sync engine will now call `fetch_timeline()` for each issue (not PR) in the batch. Since these test fixtures contain only PRs, no timeline calls happen — but verify this assumption holds

7. **Add ~17 new sync engine tests** in new test classes:

   `TestPRSync` (~5 tests):
   - `test_pr_creates_task_with_github_pr_provider` — PR in fetch_issues → object.create with `externalProvider: "github-pr"` in properties
   - `test_mixed_issues_and_prs_all_created` — batch of 2 issues + 1 PR → 3 created tasks
   - `test_pr_body_set` — PR with body text gets body.set in phase 2
   - `test_pr_update_existing` — existing PR task gets object.patch
   - `test_pr_properties_include_correct_provider` — verify the properties dict in the create command has `externalProvider: "github-pr"`

   `TestTimelineEdgeCreation` (~8 tests):
   - `test_edge_created_for_cross_referenced_pr` — issue with timeline containing cross-referenced PR → `edge.create` command with `source=PR_IRI, target=Issue_IRI, predicate=bpkm:dependsOn`
   - `test_no_edges_when_no_cross_references` — issue with empty timeline → no edge commands
   - `test_edge_skipped_when_pr_task_not_found` — timeline references PR not in synced repos → no edge, no error
   - `test_edge_skipped_when_issue_task_not_found` — graceful skip when issue IRI lookup fails
   - `test_multiple_prs_referencing_same_issue` — issue timeline with 2 PR cross-refs → 2 edge.create commands
   - `test_timeline_api_error_isolated` — timeline fetch error for one issue doesn't abort other issues' timeline processing
   - `test_edges_created_in_result` — `last_pull_result["edges_created"]` contains correct count
   - `test_timeline_not_called_for_prs` — PRs don't trigger timeline queries (only issues do)

   `TestFindExistingTaskProvider` (~4 tests):
   - `test_find_with_default_provider` — existing behavior, `provider="github"`
   - `test_find_with_pr_provider` — `provider="github-pr"` filters to PR tasks
   - `test_find_with_no_provider` — `provider=None` finds task by slug regardless of provider
   - `test_find_with_no_provider_returns_pr_task` — `provider=None` can find a PR task by slug

8. **Run full test suite**: `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v`

## Must-Haves

- [ ] PR skip filter removed — PRs create tasks with `externalProvider: "github-pr"`
- [ ] `_find_existing_task()` accepts optional `provider` param (None = slug-only lookup)
- [ ] Phase 3 link-discovery produces `edge.create` commands with `source=PR_IRI, target=Issue_IRI, predicate=bpkm:dependsOn`
- [ ] Timeline errors are per-issue isolated (caught, logged, recorded in `failed_issues`)
- [ ] `last_pull_result` includes `edges_created` count
- [ ] Existing 124 tests still pass (with PR-filtering tests modified)
- [ ] ≥17 new sync engine tests passing
- [ ] Total test count across all 5 test files ≥150

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py tests/test_github_sync_engine.py -v` — all ≥150 tests pass
- `test_edges_created_in_result` confirms `last_pull_result["edges_created"]` is inspectable (diagnostic verification)
- `test_timeline_api_error_isolated` confirms timeline failures appear in `failed_issues` with `(timeline)` suffix (failure-path verification)

## Observability Impact

- Signals added: `edges_created` count in `last_pull_result` StateClient key; `(timeline)` suffix in `failed_issues` list entries for timeline-specific failures
- How a future agent inspects this: read `last_pull_result` from StateClient — JSON now includes `edges_created` alongside `created`/`updated`/`errors`
- Failure state exposed: timeline API failures per-issue in `failed_issues` list with `(timeline)` suffix distinguishing them from issue-processing failures

## Inputs

- `apps/github-sync/services/github_client.py` — `fetch_timeline()` from T01
- `apps/github-sync/services/field_mapper.py` — `extract_linked_issue_numbers()` from T01
- `apps/github-sync/services/sync_engine.py` — existing `pull_sync()`, `_find_existing_task()`, `_make_result()`
- `backend/tests/test_github_sync_engine.py` — existing 26 tests, mock infrastructure (`MockExternalHttpClient`, `MockGraphClient`, `MockAppContext`, etc.)
- S01 Forward Intelligence: `MockExternalHttpClient` response queue is order-sensitive — timeline API calls come after fetch_issues calls in the response sequence
- S01 Forward Intelligence: `MockResponse` default data must use `data if data is not None else {}` not `data or {}` (knowledge entry Pattern #2)

## Expected Output

- `apps/github-sync/services/sync_engine.py` — `_find_existing_task()` with provider param, PR skip filter removed, phase 3 link-discovery loop, `_make_result()` with `edges_created`
- `backend/tests/test_github_sync_engine.py` — `TestPRFiltering` renamed/updated, new `TestPRSync`, `TestTimelineEdgeCreation`, `TestFindExistingTaskProvider` classes with ~17 new tests
