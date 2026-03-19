---
estimated_steps: 9
estimated_files: 3
---

# T03: Build sync engine, wire poll-tasks, and add unit tests

**Slice:** S02 — Pull Sync — Linear Issues to bpkm:Task
**Milestone:** M016

## Description

The sync engine is the orchestrator that ties LinearClient, field mapper, person matcher, and bulk commands together into a working pull sync pipeline. It must handle a critical constraint: the SDK's `CommandClient` enforces IRI prefix checking on `object.patch`, `body.set`, `body.diff`, and `edge.create` commands, but platform-minted Task IRIs use `{base_namespace}/Task/issue-{hash16}` — not the app's `urn:sempkm:app:linear-sync:` prefix. The engine bypasses the SDK by posting command payloads directly to `/api/commands/bulk` via the shared httpx client.

After building the engine, wire it into the `poll-tasks` handler in `app.py` to complete the slice.

## Steps

1. **Create `apps/linear-sync/services/sync_engine.py`** with the `pull_sync` function and supporting helpers:

   ```python
   import logging
   import json
   from datetime import datetime, timezone
   
   from services.field_mapper import (
       build_issue_query, build_task_properties, compute_issue_slug,
       normalize_status, BPKM,
   )
   from services.person_matcher import PersonMatcher
   from services.auth import get_connection_status
   
   logger = logging.getLogger("linear_sync.sync")
   
   BATCH_SIZE = 1000  # Max commands per bulk batch
   ```

   Use try/except import chain for test compatibility (same pattern as S01's auth.py):
   ```python
   try:
       from services.field_mapper import ...
   except ImportError:
       from field_mapper import ...
   ```

2. **Implement `_find_existing_task(graph_client, slug: str) -> dict | None`** — SPARQL query to check if a Task with the given slug already exists:
   ```sparql
   SELECT ?task ?status ?desc WHERE {
     ?task a <urn:sempkm:model:basic-pkm:Task> .
     ?task <urn:sempkm:model:basic-pkm:externalProvider> "linear" .
     FILTER(STRENDS(STR(?task), "/Task/{slug}"))
     OPTIONAL {{ ?task <urn:sempkm:model:basic-pkm:taskStatus> ?status }}
     OPTIONAL {{ ?task <urn:sempkm:model:basic-pkm:externalId> ?desc }}
   }
   LIMIT 1
   ```
   Return `{"iri": ..., "status": ..., "externalId": ...}` or None. Uses `STRENDS` to match the slug suffix of the IRI without needing to know the base namespace.

3. **Implement `_build_create_commands(issue, properties, slug, description) -> list[dict]`** — Generate the command dicts for a new task:
   - `{"command": "object.create", "params": {"type": "urn:sempkm:model:basic-pkm:Task", "slug": slug, "properties": properties}}`
   - If `description` is not None/empty: `{"command": "body.set", "params": {"iri": "DEFERRED", "body": description}}` — **Note:** body.set needs the task IRI, but we don't know it until the platform creates it. For new tasks, the body.set must reference the same slug. Actually, the bulk endpoint processes commands sequentially, and `object.create` returns the IRI in its response — but in bulk mode, all commands are submitted at once. **Resolution:** Omit `body.set` from the bulk batch for new tasks. Instead, after the bulk batch succeeds, issue a separate body.set for each newly created task. OR: include body.set with a constructed IRI (we know the slug and type, but not the base_namespace). **Better approach:** The field mapper's `compute_issue_slug()` produces a deterministic slug. The platform mints `{base_namespace}/Task/{slug}`. But we don't know `base_namespace` at sync time. **Pragmatic solution:** For new tasks, skip body.set in the initial bulk. The sync engine can set bodies in a follow-up batch once it knows the IRIs from SPARQL lookups in the next sync run. OR: query for newly-created tasks after the create batch and issue body.set commands in a second batch.

   **Revised approach:** Use a two-phase bulk for new issues:
   - Phase 1: All `object.create` commands (no IRI needed)
   - Phase 2: SPARQL-discover the IRIs of just-created tasks, then issue `body.set`, `edge.create` commands using the discovered IRIs
   
   For existing tasks (updates): IRIs already known from the SPARQL lookup, so `object.patch`, `body.set/body.diff`, `edge.create` can all go in one batch.

4. **Implement `_build_update_commands(existing_iri, issue, old_properties, new_properties, description) -> list[dict]`** — Generate commands for updating an existing task:
   - Compare `new_properties` with `old_properties` (fetched from SPARQL or from the previous sync) — if properties differ, emit `{"command": "object.patch", "params": {"iri": existing_iri, "properties": new_properties}}`
   - For simplicity in v1: always emit `object.patch` with the full properties dict (idempotent). The platform handles partial updates.
   - If description changed or is new: `{"command": "body.set", "params": {"iri": existing_iri, "body": description}}`
   - These commands bypass the SDK — the `iri` field would fail the prefix check.

5. **Implement `_submit_commands_batched(http_client, commands, summary, source) -> list[dict]`** — Submit commands in ≤1000-op batches:
   ```python
   async def _submit_commands_batched(http_client, commands, summary, source):
       results = []
       for i in range(0, len(commands), BATCH_SIZE):
           batch = commands[i:i + BATCH_SIZE]
           payload = {
               "commands": batch,
               "summary": summary,
               "source": source,
           }
           resp = await http_client.post("/api/commands/bulk", json=payload)
           resp.raise_for_status()
           results.append(resp.json())
       return results
   ```
   The `http_client` is `ctx.commands._client` — the shared httpx.AsyncClient with platform auth.

6. **Implement `pull_sync(ctx) -> dict`** — The main orchestrator:
   ```python
   async def pull_sync(ctx) -> dict:
       # 1. Check auth
       status = await get_connection_status(ctx.state)
       if not status["connected"]:
           return {"status": "skipped", "reason": "not connected"}
       
       # 2. Read sync state
       last_sync_at = await ctx.state.get("last_sync_at")
       sync_teams_json = await ctx.state.get("sync_teams")
       if not sync_teams_json:
           return {"status": "skipped", "reason": "no teams selected"}
       sync_teams = json.loads(sync_teams_json)
       
       # 3. Build query and fetch issues
       from services.linear_client import LinearClient
       client = LinearClient(http_client=ctx.http, state_client=ctx.state)
       query, variables = build_issue_query(sync_teams, last_sync_at or None)
       issues = await client.query_paginated(query, variables, "issues.nodes", "issues.pageInfo")
       
       # 4. Process issues
       person_matcher = PersonMatcher(ctx.graph, ctx.commands)
       http_client = ctx.commands._client  # bypass SDK for bulk commands
       
       create_commands = []
       update_commands = []
       created_count = 0
       updated_count = 0
       unchanged_count = 0
       errors = []
       new_issue_descriptions = {}  # slug -> description
       new_issue_assignees = {}     # slug -> {"email": ..., "name": ...}
       
       sync_timestamp = datetime.now(timezone.utc).isoformat()
       
       for issue in issues:
           try:
               slug = compute_issue_slug(status.get("workspace_id", ""), issue["id"])
               existing = await _find_existing_task(ctx.graph, slug)
               properties = build_task_properties(issue, status.get("workspace_id", ""), sync_timestamp)
               
               if issue.get("trashed"):
                   if existing:
                       # Previously synced, now trashed → cancel
                       update_commands.append({
                           "command": "object.patch",
                           "params": {"iri": existing["iri"], "properties": {f"{BPKM}taskStatus": "cancelled"}}
                       })
                       updated_count += 1
                   # Skip trashed issues that aren't already synced
                   continue
               
               if existing:
                   # Always patch with current properties (idempotent)
                   update_commands.append({
                       "command": "object.patch",
                       "params": {"iri": existing["iri"], "properties": properties}
                   })
                   # Body set if description present
                   desc = issue.get("description")
                   if desc:
                       update_commands.append({
                           "command": "body.set",
                           "params": {"iri": existing["iri"], "body": desc}
                       })
                   # Assignee edge
                   assignee = issue.get("assignee")
                   if assignee and assignee.get("email"):
                       person_iri = await person_matcher.match_or_create(
                           assignee["email"], assignee.get("displayName")
                       )
                       if person_iri:
                           update_commands.append({
                               "command": "edge.create",
                               "params": {
                                   "source": existing["iri"],
                                   "predicate": f"{BPKM}assignedTo",
                                   "target": person_iri,
                               }
                           })
                   updated_count += 1
               else:
                   # New issue → create
                   create_commands.append({
                       "command": "object.create",
                       "params": {
                           "type": "urn:sempkm:model:basic-pkm:Task",
                           "slug": slug,
                           "properties": properties,
                       }
                   })
                   desc = issue.get("description")
                   if desc:
                       new_issue_descriptions[slug] = desc
                   assignee = issue.get("assignee")
                   if assignee and assignee.get("email"):
                       new_issue_assignees[slug] = {
                           "email": assignee["email"],
                           "name": assignee.get("displayName"),
                       }
                   created_count += 1
           except Exception as e:
               errors.append({"issue_id": issue.get("id", "unknown"), "error": str(e)})
               logger.warning("Error processing issue %s: %s", issue.get("id"), e)
       
       # 5. Submit create commands (phase 1)
       if create_commands:
           await _submit_commands_batched(
               http_client, create_commands,
               f"Linear sync: created {len(create_commands)} tasks",
               "linear-sync"
           )
       
       # 6. For newly created tasks, discover IRIs and submit body.set + edge commands (phase 2)
       phase2_commands = []
       for slug, desc in new_issue_descriptions.items():
           task_info = await _find_existing_task(ctx.graph, slug)
           if task_info:
               phase2_commands.append({
                   "command": "body.set",
                   "params": {"iri": task_info["iri"], "body": desc}
               })
       for slug, assignee_info in new_issue_assignees.items():
           task_info = await _find_existing_task(ctx.graph, slug)
           if task_info:
               person_iri = await person_matcher.match_or_create(
                   assignee_info["email"], assignee_info["name"]
               )
               if person_iri:
                   phase2_commands.append({
                       "command": "edge.create",
                       "params": {
                           "source": task_info["iri"],
                           "predicate": f"{BPKM}assignedTo",
                           "target": person_iri,
                       }
                   })
       
       # 7. Submit update + phase2 commands
       all_follow_up = update_commands + phase2_commands
       if all_follow_up:
           await _submit_commands_batched(
               http_client, all_follow_up,
               f"Linear sync: updated {updated_count} tasks, {len(phase2_commands)} follow-ups",
               "linear-sync"
           )
       
       # 8. Update sync cursor
       await ctx.state.set("last_sync_at", sync_timestamp)
       
       result = {
           "status": "ok",
           "created": created_count,
           "updated": updated_count,
           "unchanged": unchanged_count,
           "errors": errors,
       }
       logger.info("Pull sync complete: %s", result)
       return result
   ```

7. **Wire `poll_tasks` in `apps/linear-sync/app.py`**:
   - Add import: `from services.sync_engine import pull_sync`
   - Replace the noop handler body:
     ```python
     @linear_sync_app.task("poll-tasks")
     async def poll_tasks(ctx: AppContext):
         logger.info("poll-tasks: starting pull sync")
         try:
             result = await pull_sync(ctx)
             logger.info("poll-tasks: completed — %s", result)
             return result
         except Exception as exc:
             logger.error("poll-tasks: sync failed — %s", exc, exc_info=True)
             return {"status": "error", "message": str(exc)}
     ```
   - Note: the handler must be `async def` now since `pull_sync` is async.

8. **Create `backend/tests/test_sync_engine.py`** with comprehensive mocked tests:

   Mock classes needed:
   - `MockLinearClient` with `query_paginated()` returning issue fixtures
   - `MockGraphClient` with `query()` returning SPARQL results (empty for new tasks, populated for existing)
   - `MockStateClient` with `get()`/`set()` storing key-value pairs in a dict
   - `MockHttpClient` with `post()` recording calls and returning success responses
   - `MockAppContext` combining all mocks with `.http`, `.state`, `.graph`, `.commands` attributes (where `.commands._client` is the MockHttpClient)

   Issue fixtures — create helper functions returning realistic Linear issue dicts:
   ```python
   def make_issue(id="issue-1", title="Fix bug", state_type="started", **overrides):
       base = {
           "id": id, "identifier": "ENG-1", "title": title,
           "description": "Bug description", "url": "https://linear.app/team/ENG-1",
           "state": {"type": state_type}, "priority": 2,
           "dueDate": "2026-04-01", "completedAt": None,
           "labels": {"nodes": [{"name": "bug"}]},
           "estimate": 3, "trashed": False,
           "assignee": {"id": "user-1", "displayName": "Alice", "email": "alice@example.com"},
           "updatedAt": "2026-03-18T12:00:00.000Z",
           "createdAt": "2026-03-17T10:00:00.000Z",
       }
       base.update(overrides)
       return base
   ```

   Tests (~20):
   - **Auth/state checks:**
     - `test_skips_when_not_connected` — returns skipped status
     - `test_skips_when_no_teams_selected` — returns skipped status
   - **New issue creation:**
     - `test_creates_task_for_new_issue` — SPARQL returns empty → object.create command submitted
     - `test_create_command_has_correct_properties` — verify properties dict structure
     - `test_create_command_has_deterministic_slug` — slug matches compute_issue_slug output
     - `test_body_set_for_new_issue_with_description` — phase 2 submits body.set after create
   - **Existing issue update:**
     - `test_patches_existing_task` — SPARQL returns existing → object.patch submitted
     - `test_body_set_for_existing_task` — body.set with existing IRI
   - **Assignee handling:**
     - `test_assignee_creates_edge` — edge.create with assignedTo predicate
     - `test_no_assignee_no_edge` — issue without assignee → no edge command
   - **Trashed issues:**
     - `test_skips_new_trashed_issue` — trashed=True, no existing → no commands
     - `test_cancels_existing_trashed_issue` — trashed=True, has existing → patch status to cancelled
   - **Delta sync cursor:**
     - `test_stores_last_sync_at_on_success` — StateClient.set called with timestamp
     - `test_passes_last_sync_at_to_query` — updatedAfter variable populated
   - **Batching:**
     - `test_batches_large_command_sets` — 1500 commands → 2 bulk POST calls
   - **Error handling:**
     - `test_per_issue_error_does_not_abort_sync` — one bad issue, others still processed
     - `test_error_recorded_in_result` — errors list contains issue ID and message
   - **Result shape:**
     - `test_result_contains_counts` — status, created, updated, unchanged, errors fields present
   - **Bulk command bypass:**
     - `test_commands_posted_directly_not_via_sdk` — verify http_client.post called with /api/commands/bulk path

9. **Verify all tests together:**
   - `cd backend && python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py -v`
   - All three test files pass
   - `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` — syntax valid
   - `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` — syntax valid

## Must-Haves

- [ ] `pull_sync(ctx)` implemented with full pipeline: auth check → query → process → create/update → cursor
- [ ] IRI prefix bypass: commands posted directly to `/api/commands/bulk` via httpx, not through SDK CommandClient
- [ ] Two-phase bulk for new issues: create first, then discover IRIs for body.set/edge.create
- [ ] Bulk batch size limit of 1000 commands per POST
- [ ] Delta sync cursor (`last_sync_at`) stored in StateClient on success
- [ ] Trashed issues: skip new, cancel existing
- [ ] Per-issue error handling: one bad issue doesn't abort the sync
- [ ] `poll_tasks` in `app.py` calls `pull_sync(ctx)` as async handler
- [ ] ~20 unit tests with mocked clients covering all paths

## Verification

- `cd backend && python -m pytest tests/test_sync_engine.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_field_mapper.py tests/test_person_matcher.py tests/test_sync_engine.py -v` — full suite passes
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/sync_engine.py').read())"` — syntax valid
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/app.py').read())"` — syntax valid

## Observability Impact

- Signals added: Logger `linear_sync.sync` — INFO for sync start/complete with count dict, WARNING for per-issue errors, DEBUG for individual issue processing. Logger `linear_sync` in app.py — INFO/ERROR for poll-tasks lifecycle.
- How a future agent inspects this: `await ctx.state.get("last_sync_at")` shows when sync last ran. `pull_sync()` return dict has `created`, `updated`, `unchanged`, `errors` counts.
- Failure state exposed: `{"status": "error", "message": ...}` on auth or API failure. `errors` list in result contains `{"issue_id": ..., "error": ...}` for per-issue failures.

## Inputs

- `apps/linear-sync/services/field_mapper.py` (T01) — `build_issue_query()`, `build_task_properties()`, `compute_issue_slug()`, `normalize_status()`, `BPKM` constant
- `apps/linear-sync/services/person_matcher.py` (T02) — `PersonMatcher` class with `match_or_create(email, name)`
- `apps/linear-sync/services/linear_client.py` (S01) — `LinearClient.query_paginated()` for GraphQL pagination
- `apps/linear-sync/services/auth.py` (S01) — `get_connection_status()` to check if auth is valid
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — `CommandClient._client` is the httpx.AsyncClient for direct bulk POST; `_IRI_PARAMS` shows which commands check which IRI fields
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — `GraphClient.query()` returns SPARQL JSON results

## Expected Output

- `apps/linear-sync/services/sync_engine.py` — ~250 lines, `pull_sync()` + helper functions
- `apps/linear-sync/app.py` — modified poll-tasks handler to call pull_sync
- `backend/tests/test_sync_engine.py` — ~20 tests with comprehensive mocked fixtures
