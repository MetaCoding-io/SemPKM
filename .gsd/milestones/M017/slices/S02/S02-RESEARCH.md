# S02: PR Pull Sync + PR-to-Issue Edge Linking — Research

**Date:** 2026-03-18

## Summary

S02 is a targeted extension of S01's pull sync pipeline. The existing code already detects PRs (`is_pull_request()`) and maps them to `externalProvider: "github-pr"` in `build_task_properties()`. The current `pull_sync()` explicitly skips PRs with a filter. S02 removes that filter, processes PRs as Task objects, and adds a post-sync phase that queries the GitHub timeline API for each PR to discover cross-referenced issues, then creates `bpkm:dependsOn` edges between the PR task and the linked issue task.

`bpkm:dependsOn` is already declared in basic-pkm's ontology as an OWL ObjectProperty with domain/range `bpkm:Task → bpkm:Task`. The `edge.create` command pattern is established in linear-sync's `_build_update_commands()`. The timeline API returns `cross-referenced` events with a `source.issue` containing `pull_request` key to confirm the source is a PR. This is well-understood work — ~30 tests, no new dependencies, no novel architecture.

## Recommendation

Three focused tasks:

1. **GitHubClient + timeline parsing (pure functions):** Add `fetch_timeline()` to `GitHubClient`. Add `extract_linked_issue_numbers()` pure function to `field_mapper.py` that filters timeline events for `cross-referenced` type where `source.issue.pull_request` exists, returning issue numbers.

2. **Sync engine PR handling + edge creation:** Remove the PR skip filter from `pull_sync()`. After all issues and PRs are synced (so IRIs exist), run a link-discovery phase: for each PR that was synced, call timeline API, extract linked issue numbers, resolve issue task IRIs via `_find_existing_task()`, and submit `edge.create` commands with predicate `bpkm:dependsOn`.

3. **Unit tests (~30+):** Timeline parsing pure function tests, PR-as-task creation tests, edge creation tests, cross-repo graceful skip tests.

## Implementation Landscape

### Key Files

- `apps/github-sync/services/github_client.py` — Add `fetch_timeline(owner, repo, issue_number)` convenience method. Uses existing `_paginate()` for the `GET /repos/{owner}/{repo}/issues/{number}/timeline` endpoint.
- `apps/github-sync/services/field_mapper.py` — Add `extract_linked_issue_numbers(timeline_events, repo_full_name)` pure function. Filters events for `event == "cross-referenced"` where `source.issue.pull_request` exists. Returns list of `(repo_full_name, issue_number)` tuples. `build_task_properties()` already handles PR provider distinction — no changes needed there.
- `apps/github-sync/services/sync_engine.py` — Main changes:
  1. Remove the PR skip filter (`if is_pull_request(issue): skipped += 1; continue` → process PRs normally).
  2. Track which items are PRs during the sync loop (store `(repo_full_name, pr_number, slug)` in a list).
  3. After phase 1 (create) and phase 2 (body.set), add phase 3: for each synced PR, call `fetch_timeline()`, extract linked issue numbers, resolve issue task IRIs via `_find_existing_task(graph, compute_issue_slug(repo, issue_num))`, and build `edge.create` commands.
  4. Update `_find_existing_task()` to also accept `externalProvider` param (default `"github"`) so it can find both issue tasks and PR tasks by slug.
- `backend/tests/test_github_sync_engine.py` — Extend with PR sync tests. Existing `TestPRFiltering` class becomes `TestPRSync`. Add `MockExternalHttpClient` responses for timeline API calls.
- `backend/tests/test_github_field_mapper.py` — Add tests for `extract_linked_issue_numbers()`.
- `backend/tests/test_github_client.py` — Add tests for `fetch_timeline()`.

### Key Data Structures

**Timeline `cross-referenced` event structure (from GitHub API):**
```json
{
  "event": "cross-referenced",
  "source": {
    "type": "issue",
    "issue": {
      "number": 101,
      "pull_request": { "url": "..." },
      "repository": {
        "full_name": "owner/repo"
      }
    }
  }
}
```

The `source.issue.pull_request` key confirms the referencing item is a PR. The `source.issue.repository.full_name` enables cross-repo link detection. `source.issue.number` is the PR number that references the issue whose timeline we're querying.

**Edge direction:** When querying issue #42's timeline and finding PR #101 cross-referenced it, create edge: `PR-task → Issue-task` with predicate `bpkm:dependsOn`. This means: "PR #101 depends on (closes/fixes) issue #42."

**Approach nuance:** We query the *issue's* timeline (not the PR's) to find which PRs reference it. This is more efficient than querying every PR's timeline — we only need one API call per synced issue, and we get all PRs that reference it. However, this means we can only create edges when the *issue* is in a synced repo. Cross-repo PRs that reference issues in non-synced repos won't produce edges (graceful skip per research doc).

**Alternative approach (recommended):** Query the *PR's* timeline instead. When we iterate PRs during sync, call timeline on each PR. The timeline will contain `cross-referenced` events pointing to issues that the PR references (via "Closes #42" etc.). This is better because:
- We only call timeline for PRs (fewer calls than for all issues)
- Edge direction is natural: PR (source of the timeline query) → Issue (referenced)
- No need to re-discover which PRs reference which issues from the issue side

Actually, looking more carefully: the `cross-referenced` event appears on the **issue's** timeline when a PR mentions it. So querying the *issue's* timeline finds PRs that reference it. Querying the PR's timeline would find issues it was mentioned in (which is the reverse direction).

**Final approach:** Query each **issue's** timeline (not PR's). For each `cross-referenced` event where `source.issue.pull_request` exists, the `source.issue.number` is the PR number. Create edge: `PR-task (source.issue.number) → Issue-task (the issue whose timeline we queried)`.

This means the link-discovery phase iterates over synced **issues** (not PRs), and for each issue, finds PRs that reference it. More precisely: after all issues and PRs are synced, iterate the issues, call their timelines, and create edges from discovered PR tasks to the issue task.

### Build Order

1. **Pure functions first** — `fetch_timeline()` on client, `extract_linked_issue_numbers()` on field_mapper. Testable in isolation with zero mocks.
2. **Sync engine changes** — Remove PR skip, add phase 3 link discovery. Depends on (1).
3. **Tests** — Cover all three layers. Test timeline parsing, edge creation, cross-repo skip, empty timeline, PR-only repos.

### Verification Approach

```bash
cd backend && .venv/bin/python -m pytest tests/test_github_client.py tests/test_github_field_mapper.py tests/test_github_sync_engine.py -v
```

Target: all existing 124 tests still pass (some PR-filtering tests will be modified), plus ~30 new tests:
- ~5 `fetch_timeline()` client tests (pagination, empty, error)
- ~8 `extract_linked_issue_numbers()` pure function tests (cross-referenced with PR, without PR, cross-repo, empty, duplicate filtering)
- ~15 sync engine tests (PR creates task, PR body.set, timeline edge creation, edge skipped when issue not synced, edge skipped when no cross-references, multiple PRs referencing same issue, mixed PR+issue batch)
- ~2 modified existing PR-filtering tests (now verify PRs are *created* instead of *skipped*)

## Constraints

- `_find_existing_task()` currently filters by `externalProvider "github"`. PR tasks have `externalProvider "github-pr"`. Need to either: (a) add a provider param, or (b) create a separate `_find_existing_pr_task()`, or (c) make a provider-agnostic lookup by slug only (STRENDS is already unique since slugs use the same hash scheme). Option (c) is simplest — just remove the provider filter from the SPARQL when looking up by slug for edge targets, since the slug itself is unique.
- Timeline API is paginated (same Link header pattern). `_paginate()` already handles this.
- Cross-repo edge creation requires both repos to be in `selected_repos`. If PR references an issue in a non-synced repo, the issue task IRI won't exist — skip gracefully with a debug log.
- `MockExternalHttpClient` response queue is order-sensitive. Timeline API calls happen after fetch_issues calls, so responses must be queued in the right order. The mock setup will need careful response ordering: verify_token → fetch_issues(repo1) → fetch_issues(repo2) → timeline(issue1) → timeline(issue2) → ...

## Common Pitfalls

- **Response queue ordering in MockExternalHttpClient** — S01's Forward Intelligence warns this is fragile. Adding timeline API calls after fetch_issues changes the response queue order. Tests must carefully sequence mock responses. Consider using a URL-based dispatch mock instead of a queue for S02's more complex flow, or at minimum document the expected call sequence in each test.
- **Duplicate edges** — If PR #101 references issue #42 twice (e.g., "Closes #42" in body AND in a commit message), the timeline may have two `cross-referenced` events for the same PR-issue pair. `extract_linked_issue_numbers()` must deduplicate.
- **Rate limit on timeline calls** — Each issue's timeline is a separate API call. A repo with 100 issues means 100 extra calls. The existing rate-limit checking in `_paginate()` handles this, but initial sync of large repos could be slow. Consider making timeline queries optional or batched.

## Sources

- GitHub REST API issue event types: `cross-referenced` event has `source.issue` with `pull_request` key confirming PR origin
- `bpkm:dependsOn` OWL ObjectProperty: `models/basic-pkm/ontology/basic-pkm.jsonld` — domain `bpkm:Task`, range `bpkm:Task`
- `edge.create` command handler: `backend/app/commands/handlers/edge_create.py` — takes `source`, `target`, `predicate` params
- Linear sync `_build_update_commands()`: `apps/linear-sync/services/sync_engine.py` — reference pattern for `edge.create` in sync pipeline
