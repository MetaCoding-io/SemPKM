# S03: Push Sync + Settings Polish + Admin Detail — Research

**Date:** 2026-03-18

## Summary

S03 adds the "bi" to bidirectional sync: detecting changes to Linear-synced tasks in SemPKM, reverse-mapping fields back to Linear's GraphQL mutation format, pushing changes via `issueUpdate`, and preventing re-import loops. Alongside push sync, it polishes the settings page (team multi-select, sync direction toggle, poll interval) and enriches the admin detail page with sync-specific metadata.

The codebase is well-positioned. S02 built the forward field mapping (6 pure functions), IRI slug infrastructure, and the `pull_sync()` orchestrator with two-phase bulk submission. S01 built the `LinearClient` with authenticated GraphQL execution, token refresh, pagination, and three convenience methods (`get_viewer`, `get_teams`, `get_organization`). The settings page exists with connect/disconnect flow and a read-only team list. The admin detail page (platform-owned `detail.html`) already shows task run history via `AppTaskRun` records.

The main complexity is in three areas: (1) **reverse status mapping** — bpkm `taskStatus` must map to a Linear `stateId`, which requires querying the team's workflow states to find the right state; (2) **loop prevention** — when push sync writes a change to Linear, the next poll sees it as "updated" and would re-import it without filtering; (3) **change detection** — identifying which synced tasks have been modified in SemPKM since the last sync, using `dcterms:modified` vs `bpkm:lastSyncedAt` comparison.

## Recommendation

Build bottom-up: (1) reverse field mapper functions, (2) push sync engine, (3) settings page polish, (4) admin detail enrichment. Reverse mapping first because push sync depends on it. Push sync second because it's the core deliverable. Settings third because team selection is already stored (`sync_teams` state key from S02 pull sync) — the UI just needs checkboxes and save. Admin detail last because the platform's task history already works.

For loop prevention, use the `bpkm:lastSyncedAt` timestamp: after push sync writes to Linear, update the task's `lastSyncedAt` to the current time. On next pull, compare each issue's `updatedAt` against the task's `lastSyncedAt` — if `updatedAt <= lastSyncedAt`, the change originated from our push, so skip it. This is simple, correct for single-user, and doesn't require external state.

For status reverse mapping, cache the team's workflow states on first push sync run. Linear's `workflowStates` query returns `{id, name, type}` per state per team. Build a `{(team_id, state_type): state_id}` lookup table. When pushing a status change, find the target `state_type` from `REVERSE_STATUS_MAP` and look up the `stateId` from the cached workflow states. If a team has multiple states of the same type (e.g. two "started" states like "In Progress" and "In Review"), pick the first one — the user can refine in Linear.

## Implementation Landscape

### Key Files

**Existing — will be modified:**
- `apps/linear-sync/services/field_mapper.py` — Add reverse mapping constants and functions: `REVERSE_STATUS_MAP`, `REVERSE_PRIORITY_MAP`, `reverse_status()`, `reverse_priority()`, `build_push_properties()`, `build_issue_update_mutation()`
- `apps/linear-sync/services/sync_engine.py` — Add `push_sync(ctx)` function, `_find_changed_tasks()` SPARQL query, `_push_task_changes()` per-task mutation
- `apps/linear-sync/app.py` — Add `push-changes` task handler, update settings route to handle team selection form POST, add sync-now endpoint
- `apps/linear-sync/services/linear_client.py` — Add `get_workflow_states(team_id)` and `mutate(mutation, variables)` convenience methods
- `apps/linear-sync/manifest.yaml` — Add `push-changes` task definition
- `apps/linear-sync/frontend/templates/connect_status.html` — Replace read-only team table with multi-select checkboxes, add sync controls (direction, interval), add "Sync Now" button
- `apps/linear-sync/frontend/static/styles.css` — Styles for new settings controls

**New files:**
- `backend/tests/test_push_sync.py` — Unit tests for reverse mapping + push sync logic

**Platform files — read-only reference:**
- `backend/app/apps/admin_router.py` — Admin detail endpoint. Task runs already recorded. The `summary` field on `AppTaskRun` is never populated by the scheduler (it records HTTP status/error only). **Approach:** Have the task handlers return structured JSON via their HTTP response, and surface sync metadata through the app's own settings page section rather than modifying the platform template.
- `backend/app/apps/scheduler.py` — Scheduler invokes tasks via `AppProxy.invoke_task()`, records success/error/duration. No capture of task return body.
- `backend/app/templates/admin/apps/detail.html` — Platform template. Has "Data Statistics" placeholder. No mechanism for app-contributed sections. The existing task history table shows task_id, started_at, status, duration, error — already useful for sync history at a glance.

### Build Order

**1. Reverse field mapper (pure functions, no IO)**
Add to `field_mapper.py`:
- `REVERSE_STATUS_MAP: dict[str, str]` — `{"todo": "backlog", "in-progress": "started", "done": "completed", "blocked": "unstarted", "cancelled": "cancelled"}`
- `REVERSE_PRIORITY_MAP: dict[str, int]` — `{"critical": 1, "high": 2, "medium": 3, "low": 4}`
- `reverse_status(bpkm_status: str) -> str` — returns Linear `state.type` string
- `reverse_priority(bpkm_priority: str) -> int | None` — returns Linear priority int or None
- `build_issue_update_input(task_properties: dict, workflow_states: dict) -> dict` — builds `IssueUpdateInput` fields dict from bpkm task properties. Uses workflow_states for stateId resolution.
- `build_issue_update_mutation(issue_id: str, input_dict: dict) -> tuple[str, dict]` — returns (GraphQL mutation string, variables dict)

All pure, testable, no side effects. Follow S02's convention of full IRI keys for bpkm properties.

**2. LinearClient mutation support**
Add to `linear_client.py`:
- `get_workflow_states(team_id: str) -> list[dict]` — queries `team(id) { states { nodes { id name type } } }`
- `update_issue(issue_id: str, input_dict: dict) -> dict` — executes `issueUpdate` mutation. The existing `query()` method handles mutations — GraphQL doesn't distinguish at the transport level.

**3. Push sync engine**
Add to `sync_engine.py`:
- `_find_changed_tasks(graph_client) -> list[dict]` — SPARQL query: find tasks where `externalProvider = "linear"`, `syncDirection != "pull-only"`, and `dcterms:modified > bpkm:lastSyncedAt`. Returns list of `{iri, externalId, status, priority, title, lastSyncedAt, ...}`
- `_resolve_workflow_states(client, state_client) -> dict` — fetch and cache workflow states in StateClient
- `push_sync(ctx) -> dict` — orchestrator: check auth → find changed tasks → for each: reverse map properties → build mutation → execute → update lastSyncedAt. Returns `{status, pushed, skipped, errors}`
- Loop prevention in `pull_sync()`: after push, update `lastSyncedAt` on each pushed task. In `pull_sync()`, compare issue `updatedAt` with task `lastSyncedAt` — skip if issue wasn't updated after last sync.

**4. Settings page polish**
Modify `connect_status.html`:
- Team section: checkboxes per team (checked = synced), form POST to `/_fragments/settings/teams`
- Sync direction: radio buttons (pull-only / bidirectional)
- Poll interval: select dropdown with preset options (5m, 15m, 30m, 1h)
- "Sync Now" button: triggers immediate `poll-tasks` + `push-changes` via htmx POST

Add routes to `app.py`:
- `POST /_fragments/settings/teams` — saves selected team IDs to `sync_teams` state key
- `POST /_fragments/settings/sync-config` — saves sync direction and poll interval
- `POST /_fragments/sync-now` — immediately runs pull + push sync

**5. Admin detail enrichment**
The platform's admin detail page already shows task history (run status, duration, error). The `AppTaskRun.summary` field exists in the model but the scheduler never populates it (it only records HTTP status). Rather than modifying the platform template, add a sync-specific stats section to the app's own settings page:
- Last sync time (from `last_sync_at` state key)
- Last sync result counts (from `last_sync_result` state key — store pull_sync/push_sync return dicts as JSON)
- Total synced tasks count (SPARQL count query)
- Connection health indicator

This keeps all sync metadata in the app's own UI fragment, which the admin can reach via the app's settings page link in the admin portal.

### Verification Approach

**Unit tests (pure functions):**
- Reverse status mapping — all 5 bpkm statuses map correctly, unknown defaults to "backlog"
- Reverse priority mapping — all 4 bpkm priorities map correctly, None for unknown
- `build_issue_update_input()` — correct field extraction from task properties dict, workflow state resolution for stateId
- `build_issue_update_mutation()` — correct GraphQL mutation string with variables
- `_find_changed_tasks()` — SPARQL query construction (mock graph client)
- `push_sync()` — full orchestration with mocked clients: auth check, changed task detection, mutation execution, lastSyncedAt update, error isolation
- Loop prevention — verify that `pull_sync()` skips issues whose `updatedAt <= lastSyncedAt`

Target: ~40-50 tests in `test_push_sync.py`, following the same importlib loading pattern from S02.

**Integration verification:** Run all existing + new tests together:
```bash
cd backend && .venv/bin/python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py tests/test_push_sync.py -v
```

## Constraints

- **SDK IRI prefix bypass continues:** Push sync uses the same `ctx.commands._client.post("/api/commands/bulk")` bypass as pull sync for updating `lastSyncedAt` on platform-minted Task IRIs. The `_submit_commands_batched()` function from sync_engine.py is reusable.
- **LinearClient `query()` handles mutations:** Despite the method name, `query()` POSTs any GraphQL string. Mutations work through the same path. No separate mutation method needed at the transport level — just add a convenience wrapper for readability.
- **Workflow states are team-scoped:** Each Linear team has its own workflow states. A workspace with 3 teams could have 3 different "In Progress" state IDs. The workflow state cache must be keyed by `(team_id, state_type)`.
- **Push sync needs the Linear issue UUID, not the identifier:** `issueUpdate` takes the issue's UUID (`id` field), not its human-readable identifier (`identifier` like "LIN-123"). The pull sync stores `bpkm:externalId` as the identifier string. We need to either: (a) also store the UUID in a property during pull, or (b) look up the UUID from the identifier via SPARQL/Linear API. **Option (a) is simpler** — add a `bpkm:externalUuid` or reuse an existing property during pull sync. Actually, looking at the pull sync code: `build_task_properties()` stores `bpkm:externalId` as `issue["identifier"]` (e.g. "LIN-123") but the issue `id` (UUID) is available in the GraphQL response. We need to store it. The cleanest approach: store both — `externalId` stays as the human-readable identifier, and add the UUID to properties during pull, or store the UUID→identifier mapping in StateClient.

## Common Pitfalls

- **Missing Linear issue UUID for mutations:** `issueUpdate(id: ...)` needs the UUID, not the identifier string. Pull sync currently stores only `bpkm:externalId` (the "LIN-123" identifier). Need to also store or derive the UUID. Best: add the UUID as an additional task property during pull sync, or store the `{slug: issue_uuid}` mapping in StateClient.
- **Workflow state caching stale data:** Linear admins can add/rename/remove workflow states. The cached mapping will be stale if this happens between syncs. Mitigate by refreshing the cache on each push sync run (states query is cheap — one per team).
- **Push-back of non-pushable fields:** Not all bpkm fields have Linear equivalents going back. `completedDate` and `externalUrl` are pull-only. The reverse mapper must silently skip these. The design doc's "Direction" column is the guide.
- **Label sync requires fetching current labels:** Linear's `issueUpdate` with `labelIds` replaces ALL labels. To add/remove a label, you must first fetch current labels, merge, then update. For v1, skip label push-back — too complex for the initial implementation.

## Open Risks

- **Concurrent push + pull:** If push-changes and poll-tasks overlap (both triggered near the same time), there's a race: push writes to Linear, pull reads the same change back before the push completes and updates `lastSyncedAt`. The scheduler's concurrency guard prevents two runs of the same task but doesn't prevent different tasks from running simultaneously. Mitigate by having push sync set a `last_push_at` timestamp and having pull sync filter by it, or by running push→pull sequentially in a single task. **Recommendation:** For v1, make `push-changes` a separate task but add a brief check: if a push sync ran within the last 30 seconds, skip the pull of issues whose `updatedAt` falls within that window.
- **stateId resolution failure:** If the workflow states cache doesn't contain a matching state type for the target status, the push for that field must be skipped (not the whole issue). Log a warning and push other fields.
