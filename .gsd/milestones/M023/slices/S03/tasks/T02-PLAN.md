---
estimated_steps: 5
estimated_files: 2
---

# T02: Add issue link processing to pull sync with dependsOn edge creation

**Slice:** S03 — Push sync + issue links
**Milestone:** M023

## Description

Add issue link processing to the Jira pull sync pipeline. Jira issues have an `issuelinks` array in their fields containing link type information and linked issue references. Links of type "Blocks" should create `bpkm:dependsOn` edges between the corresponding Task objects in SemPKM.

This is a pull-side addition — no new Jira API calls are needed because `issuelinks` data is already included in the `search_all_issues()` response (which fetches `fields: ["*all"]`). The implementation adds a new helper function and integrates it as Phase 4 of the existing pull_sync pipeline.

**Key design decisions for deduplication:** If issue A blocks B, both A's and B's `issuelinks` arrays contain the same link — A sees it with `outwardIssue: B` and B sees it with `inwardIssue: A`. To avoid creating duplicate edges, process only links where the current issue has an `inwardIssue` entry (the current issue IS the one being blocked → it `dependsOn` the other issue). The `inwardIssue` is the blocked task, and the link's `outwardIssue` would be the other issue (the blocker). But actually Jira's link structure is: each link object has EITHER `inwardIssue` OR `outwardIssue` — the description text tells you the direction. For "Blocks" type: `outward: "blocks"`, `inward: "is blocked by"`. When the current issue has `outwardIssue`, it means the current issue blocks that issue. When it has `inwardIssue`, it means the current issue is blocked by that issue.

**Correct mapping:** When the current issue has `inwardIssue` in a link (meaning "current issue is blocked by inwardIssue"), create: `dependsOn` edge from current issue → inwardIssue. When the current issue has `outwardIssue` (meaning "current issue blocks outwardIssue"), create: `dependsOn` edge from outwardIssue → current issue. But since we process all issues, processing ONLY `inwardIssue` links covers all edges without duplication.

**Relevant skills:** `test` skill for unit test generation patterns.

## Steps

1. **Add `_process_issue_links()` helper** in `sync_engine.py`. Function signature: `async def _process_issue_links(issues: list[dict], graph_client) -> list[dict]`. For each issue in the list:
   - Get `fields.issuelinks` (default to empty list)
   - For each link, check `link.get("type", {}).get("name", "")` — match case-insensitively for "block" substring (handles "Blocks", "blocks", localized variations)
   - Process only links that have `inwardIssue` key (meaning current issue "is blocked by" the inward issue) — this avoids duplicate edges since each link appears in exactly one direction per issue
   - Extract the inward issue key: `link["inwardIssue"]["key"]`
   - Compute both slugs: current issue slug from `issue["key"]` and `issue["fields"]["project"]["key"]`, blocker slug from inward issue key (extract project key from the key format "PROJ-123")
   - Look up both Task IRIs via `_find_existing_task(graph_client, slug)`
   - If both found, create edge command: `{"command": "edge.create", "params": {"source": current_task_iri, "predicate": f"{BPKM}dependsOn", "target": blocker_task_iri}}`
   - Log skips (linked issue not synced) at DEBUG level
   - Wrap per-link processing in try/except for error isolation
   - Return the list of edge commands

2. **Integrate into pull_sync** as Phase 4 — after Phase 3 (epic→child linking) and before the final follow-up command submission. Call `issue_link_commands = await _process_issue_links(all_issues, ctx.graph)` and include the results in the `all_follow_up` list. Update the log message to include issue link count. Note: pass ALL issues (tasks + epics), not just non-epic tasks, since epics can also have blocking relationships.

3. **Update pull_sync result** to include issue link count in the log message and optionally in the result dict (add `"issue_links": len(issue_link_commands)` to the result).

4. **Write ~20 unit tests** in `test_jira_sync_engine.py`. Add a new test class `TestIssueLinks`:

   **TestIssueLinks (~12 tests):**
   - "Blocks" inward link → creates dependsOn edge (source=current task, target=blocker)
   - Outward "blocks" link → ignored (dedup — will be processed as inward from the other issue)
   - Link type not "Blocks" (e.g., "Relates", "Duplicate") → ignored
   - Link type case-insensitive: "blocks", "Blocks", "BLOCKS" all match
   - Empty issuelinks array → no edge commands
   - No issuelinks field → no edge commands
   - Linked issue not synced (not found in graph) → skip, no error
   - Current issue not found in graph → skip, no error
   - Multiple links on one issue → multiple edge commands
   - Issue with both inward and outward blocks links → only inward processed
   - Error in one link processing doesn't stop others (isolation)

   **TestPullSyncWithIssueLinks (~5 tests):**
   - Full pull_sync with issues that have blocking links → edges created
   - Full pull_sync with no issue links → still works (regression)
   - Issue link commands included in follow-up batch
   - Pull result includes issue_links count
   - Issue link phase runs after epic linking phase

   **Mock infrastructure:**
   - Add helper `_make_issue_with_links(key, links)` that creates an issue dict with issuelinks array
   - Each link dict needs: `{"type": {"name": "Blocks"}, "inwardIssue": {"key": "PROJ-456"}}` or `{"type": {"name": "Blocks"}, "outwardIssue": {"key": "PROJ-789"}}`

5. **Verify** all tests pass: `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -v` and `python -m pytest backend/tests/test_jira_*.py -v`

## Must-Haves

- [ ] `_process_issue_links()` function exists and processes "Blocks" type links
- [ ] Only `inwardIssue` links processed (deduplication — avoids creating same edge twice)
- [ ] Link type matching is case-insensitive (contains "block")
- [ ] Both Task IRIs looked up via `_find_existing_task()` — skip if either not found
- [ ] `bpkm:dependsOn` edge: source = current (blocked) task, target = blocker task
- [ ] Integrated into pull_sync as Phase 4 (after epic linking, before final submission)
- [ ] Per-link error isolation
- [ ] All existing ~125 tests still pass (regression from T01 + original 95)
- [ ] ~20 new issue link tests pass

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_sync_engine.py -v` — all ~145 tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_jira_*.py -v` — combined suite passes
- `python3 -c "import ast; ast.parse(open('apps/jira-sync/services/sync_engine.py').read()); print('VALID')"` — prints VALID
- `grep -c "dependsOn" apps/jira-sync/services/sync_engine.py` — at least 1 occurrence
- `grep -c "_process_issue_links" apps/jira-sync/services/sync_engine.py` — at least 2 occurrences (def + call)

## Inputs

- `apps/jira-sync/services/sync_engine.py` — T01's completed file with real push_sync, _find_changed_tasks, plus existing pull_sync with Phase 1-3 structure. `_find_existing_task(graph_client, slug)` already exists and can be reused for link lookup. `BPKM` constant available. `_submit_commands_batched()` available for edge command submission.
- `backend/tests/test_jira_sync_engine.py` — T01's completed test file with ~125 tests. MockGraphClient with slug_map routing, MockAppContext, all mock infrastructure in place.
- Jira issuelinks structure: `issue["fields"]["issuelinks"]` is a list of link dicts. Each link has `{"type": {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"}, "inwardIssue": {"key": "PROJ-456"} | "outwardIssue": {"key": "PROJ-789"}}`. A link has EITHER inwardIssue OR outwardIssue, not both.
- `compute_issue_slug(project_key, issue_key)` from field_mapper.py — already imported in sync_engine.py. For linked issues, extract project_key from the issue key format (e.g., "PROJ" from "PROJ-456").
- Reference: `apps/github-sync/services/sync_engine.py` lines 555-595 — Phase 3 dependsOn edge creation from timeline cross-references. Same `edge.create` command structure.

## Expected Output

- `apps/jira-sync/services/sync_engine.py` — `_process_issue_links()` function (~40 lines) added. pull_sync gains Phase 4 integration (~5 lines). File grows from ~810 to ~860 lines.
- `backend/tests/test_jira_sync_engine.py` — ~20 new tests in TestIssueLinks and TestPullSyncWithIssueLinks classes. File grows from ~2900 to ~3400 lines.

## Observability Impact

- **Pull result enrichment:** `ctx.state.get("last_pull_result")` now includes `"issue_links": <int>` count alongside existing created/updated/skipped/errors. This surfaces in connect_status.html.
- **Structured logging:** Phase 4 logs at INFO level: `"pull_sync: Phase 4 — N issue link (dependsOn) edges"`. Per-link errors logged at WARNING level with issue key.
- **Follow-up summary:** The bulk command summary string now includes issue link count alongside epic link count.
- **Failure visibility:** Link processing errors are isolated per-link (try/except) — one broken link doesn't prevent others from being processed. Errors are logged but don't increment the pull result's `errors` count (link edges are best-effort).
