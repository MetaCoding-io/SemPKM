---
estimated_steps: 6
estimated_files: 1
---

# T02: Pull sync engine with group and subitem support

**Slice:** S02 — Column mapping configuration UI + pull sync
**Milestone:** M024

## Description

Create `sync_engine.py` implementing the Monday.com pull sync pipeline. This is the largest single file in the slice (~450 lines) but follows the established Jira sync engine pattern exactly. The main differences from Jira are: (1) per-board iteration with per-board column mapping config, (2) groups from `item.group.title` (not column values), (3) subitems → parentTask edges, (4) no delta query (content comparison for change detection instead of `updatedAt`).

**Relevant skills:** None specific — follows the Jira sync engine pattern from `apps/jira-sync/services/sync_engine.py`.

## Steps

1. **Create file header and imports.** Path: `apps/monday-sync/services/sync_engine.py`. Import `json`, `logging`, `time`, `datetime`. Use the try/except importlib pattern from other sync engines for importing `field_mapper`, `person_matcher`, `auth`, `monday_client`. Import `build_task_properties`, `compute_slug`, `BPKM` from field_mapper; `PersonMatcher` from person_matcher; `get_connection_status` from auth; `MondayClient` from monday_client. Set `BATCH_SIZE = 1000` and logger `"monday_sync.sync"`.

2. **Implement SPARQL lookup helper: `_find_existing_task(graph_client, slug)`**. Query: SELECT with `STRENDS(STR(?task), "/Task/{slug}")`, matching `externalProvider "monday"`. Returns `{"iri", "status", "externalId", "lastSyncedAt", "properties_hash"}` or None. **Important:** Use `"monday"` as the externalProvider value (matching field_mapper.py's setting).

   Also implement `_find_all_tasks_for_board(graph_client, board_id)` that returns all Monday-synced tasks with their current property values for content comparison. SPARQL query:
   ```sparql
   SELECT ?task ?slug ?status ?priority ?dueDate ?title ?lastSynced WHERE {
     ?task a <BPKM:Task> .
     ?task <BPKM:externalProvider> "monday" .
     ?task <BPKM:externalUrl> ?url .
     FILTER(CONTAINS(STR(?url), "/boards/{board_id}/"))
     OPTIONAL { ?task <BPKM:taskStatus> ?status }
     ...
   }
   ```

3. **Implement command builders.** Clone exactly from Jira pattern:
   - `_build_create_command(slug, properties, obj_type)` — returns `object.create` command dict
   - `_build_update_commands(existing_iri, properties, description, assignee_iri)` — returns list of `object.patch` + optional `body.set` + optional `edge.create` commands
   - `_submit_commands_batched(http_client, commands, summary, source)` — posts to `/api/commands/bulk` in batches of ≤ BATCH_SIZE

4. **Implement `pull_sync(ctx)`** — the main function. Follow this exact structure:

   ```python
   async def pull_sync(ctx) -> dict:
       start_time = time.monotonic()
       
       # 1. Auth check
       client = MondayClient(http_client=ctx.http, state_client=ctx.state)
       status = await get_connection_status(ctx.state, client)
       if not status["connected"]:
           return _make_result("skipped", start_time, reason="not connected")
       
       # 2. Read selected boards
       selected_boards_json = await ctx.settings.get("selected_boards")
       selected_boards = json.loads(selected_boards_json) if selected_boards_json else []
       if not selected_boards:
           return _make_result("skipped", start_time, reason="no boards selected")
       
       # 3. Create PersonMatcher (Monday.com version: 3 args)
       person_matcher = PersonMatcher(ctx.graph, ctx.commands, client)
       http_client = ctx.commands._client  # bypass SDK for bulk
       
       sync_timestamp = datetime.now(timezone.utc).isoformat()
       
       # Tracking
       create_commands = []
       update_commands = []
       created_count = updated_count = skipped_count = error_count = 0
       failed_items = []
       
       # Deferred for Phase 2
       new_task_descriptions = {}  # slug → description
       new_task_assignees = {}     # slug → person IRI
       new_task_groups = {}        # slug → group title
       
       # Deferred for Phase 3 (subitem→parentTask)
       subitem_parent_map = {}     # subitem_slug → parent_slug
       
       # 4. Per-board iteration
       for board_id_str in selected_boards:
           board_id = int(board_id_str)
           
           # Read column mapping config for this board
           mapping_json = await ctx.settings.get(f"column_mapping_{board_id}")
           if not mapping_json:
               logger.warning("No column mapping for board %s, skipping", board_id)
               continue
           mapping_config = json.loads(mapping_json)
           column_mapping = mapping_config.get("column_mapping", {})
           
           # Read label mappings
           label_json = await ctx.settings.get(f"label_mapping_{board_id}")
           label_config = json.loads(label_json) if label_json else {}
           status_label_mapping = label_config.get("status_label_mapping")
           priority_label_mapping = label_config.get("priority_label_mapping")
           
           # Fetch all items from this board (paginated)
           items = await client.get_all_board_items(board_id)
           logger.info("Board %s: fetched %d items", board_id, len(items))
           
           # Collect parent item IDs for subitem fetching
           parent_item_ids = [int(item["id"]) for item in items if item.get("id")]
           
           # Process each item
           for item in items:
               try:
                   item_id = str(item.get("id", ""))
                   item_name = item.get("name", "")
                   slug = compute_slug(item_name, item_id)
                   
                   existing = await _find_existing_task(ctx.graph, slug)
                   
                   # Build properties using stored mapping
                   properties, assignee_user_id = build_task_properties(
                       item, column_mapping,
                       status_label_mapping=status_label_mapping,
                       priority_label_mapping=priority_label_mapping,
                       board_id=board_id,
                       sync_time=sync_timestamp,
                   )
                   
                   # Set taskGroup from item.group.title (NOT column_values)
                   group_info = item.get("group")
                   if group_info and isinstance(group_info, dict):
                       group_title = group_info.get("title")
                       if group_title:
                           properties[f"{BPKM}taskGroup"] = group_title
                   
                   # Resolve assignee
                   assignee_iri = None
                   if assignee_user_id:
                       try:
                           assignee_iri = await person_matcher.resolve(
                               str(assignee_user_id), item_name
                           )
                       except Exception as exc:
                           logger.warning("Assignee resolution failed for %s: %s", item_id, exc)
                   
                   # Description from column mapping (if mapped)
                   description = properties.pop(f"{BPKM}description", None)
                   
                   if existing:
                       # Content comparison — skip if unchanged
                       # Compare key properties to detect changes
                       changed = _has_changes(existing, properties)
                       if not changed:
                           skipped_count += 1
                           continue
                       
                       update_commands.extend(
                           _build_update_commands(
                               existing["iri"], properties, description, assignee_iri,
                           )
                       )
                       updated_count += 1
                   else:
                       create_commands.append(
                           _build_create_command(slug, properties, f"{BPKM}Task")
                       )
                       if description:
                           new_task_descriptions[slug] = description
                       if assignee_iri:
                           new_task_assignees[slug] = assignee_iri
                       created_count += 1
                       
               except Exception as e:
                   failed_items.append(str(item.get("id", "unknown")))
                   error_count += 1
                   logger.warning("Error processing item %s: %s", item.get("id"), e)
           
           # Fetch and process subitems for this board
           if parent_item_ids:
               try:
                   subitems = await client.get_subitems(parent_item_ids)
                   for subitem in subitems:
                       try:
                           # process subitem same as item, but track parent link
                           sub_id = str(subitem.get("id", ""))
                           sub_name = subitem.get("name", "")
                           sub_slug = compute_slug(sub_name, sub_id)
                           parent_id = str(subitem.get("parent_item_id", ""))
                           
                           # Find parent slug
                           parent_item = next(
                               (i for i in items if str(i.get("id")) == parent_id), None
                           )
                           if parent_item:
                               parent_slug = compute_slug(parent_item["name"], parent_id)
                               subitem_parent_map[sub_slug] = parent_slug
                           
                           existing = await _find_existing_task(ctx.graph, sub_slug)
                           
                           sub_props, sub_assignee_id = build_task_properties(
                               subitem, column_mapping,
                               status_label_mapping=status_label_mapping,
                               priority_label_mapping=priority_label_mapping,
                               board_id=board_id,
                               sync_time=sync_timestamp,
                           )
                           
                           # Subitem group
                           sub_group = subitem.get("group")
                           if sub_group and isinstance(sub_group, dict):
                               gt = sub_group.get("title")
                               if gt:
                                   sub_props[f"{BPKM}taskGroup"] = gt
                           
                           sub_assignee_iri = None
                           if sub_assignee_id:
                               try:
                                   sub_assignee_iri = await person_matcher.resolve(
                                       str(sub_assignee_id), sub_name
                                   )
                               except Exception:
                                   pass
                           
                           sub_desc = sub_props.pop(f"{BPKM}description", None)
                           
                           if existing:
                               if not _has_changes(existing, sub_props):
                                   skipped_count += 1
                                   continue
                               update_commands.extend(
                                   _build_update_commands(
                                       existing["iri"], sub_props, sub_desc, sub_assignee_iri
                                   )
                               )
                               updated_count += 1
                           else:
                               create_commands.append(
                                   _build_create_command(sub_slug, sub_props, f"{BPKM}Task")
                               )
                               if sub_desc:
                                   new_task_descriptions[sub_slug] = sub_desc
                               if sub_assignee_iri:
                                   new_task_assignees[sub_slug] = sub_assignee_iri
                               created_count += 1
                               
                       except Exception as e:
                           failed_items.append(str(subitem.get("id", "unknown")))
                           error_count += 1
                           logger.warning("Error processing subitem %s: %s", subitem.get("id"), e)
               except Exception as exc:
                   logger.warning("Subitem fetch failed for board %s: %s", board_id, exc)
       
       # Phase 1: submit create commands
       if create_commands:
           logger.info("Phase 1: submitting %d create commands", len(create_commands))
           await _submit_commands_batched(
               http_client, create_commands,
               f"Monday.com sync: created {len(create_commands)} tasks",
               "monday-sync",
           )
       
       # Phase 2: discover IRIs, submit body + edges
       phase2_commands = []
       for slug, desc in new_task_descriptions.items():
           task_info = await _find_existing_task(ctx.graph, slug)
           if task_info:
               phase2_commands.append({
                   "command": "body.set",
                   "params": {"iri": task_info["iri"], "body": desc},
               })
       for slug, p_iri in new_task_assignees.items():
           task_info = await _find_existing_task(ctx.graph, slug)
           if task_info:
               phase2_commands.append({
                   "command": "edge.create",
                   "params": {
                       "source": task_info["iri"],
                       "predicate": f"{BPKM}assignedTo",
                       "target": p_iri,
                   },
               })
       
       # Phase 3: subitem → parentTask edges
       parent_link_commands = []
       for sub_slug, parent_slug in subitem_parent_map.items():
           sub_info = await _find_existing_task(ctx.graph, sub_slug)
           parent_info = await _find_existing_task(ctx.graph, parent_slug)
           if sub_info and parent_info:
               parent_link_commands.append({
                   "command": "edge.create",
                   "params": {
                       "source": sub_info["iri"],
                       "predicate": f"{BPKM}parentTask",
                       "target": parent_info["iri"],
                   },
               })
       
       if parent_link_commands:
           logger.info("Phase 3: %d subitem→parentTask edges", len(parent_link_commands))
       
       # Submit all follow-up commands
       all_follow_up = update_commands + phase2_commands + parent_link_commands
       if all_follow_up:
           await _submit_commands_batched(
               http_client, all_follow_up,
               f"Monday.com sync: {updated_count} updates, "
               f"{len(phase2_commands)} follow-ups, "
               f"{len(parent_link_commands)} parent links",
               "monday-sync",
           )
       
       # Store sync state
       await ctx.state.set("last_sync_at", sync_timestamp)
       
       result = _make_result(
           _compute_status(created_count, updated_count, skipped_count, error_count),
           start_time,
           created=created_count,
           updated=updated_count,
           skipped=skipped_count,
           errors=error_count,
           failed_items=failed_items,
           parent_links=len(parent_link_commands),
       )
       logger.info("Pull sync complete: %s", result)
       await ctx.state.set("last_pull_result", json.dumps(result))
       return result
   ```

5. **Implement change detection: `_has_changes(existing, new_properties)`**. Since Monday.com has no `updatedAt` filter, compare key property values. The existing task from SPARQL has `status`, `externalId`, `lastSyncedAt`. For change detection, always return True for now (sync is idempotent, correctness > performance). A later optimization can compare status/priority/title to skip no-op updates.

   Simpler approach: if the existing task has a `lastSyncedAt` and the sync has been run before, compare the lastSyncedAt. For a first implementation, just always process (return True) — the two-phase bulk is idempotent.

6. **Implement result helpers** — Copy exactly from Jira pattern:
   - `_compute_status(created, updated, skipped, errors)` — returns "success", "partial", or "error"
   - `_make_result(status, start_time, **kwargs)` — returns standardised result dict with duration_ms, created, updated, skipped, errors, failed_items, parent_links, reason

7. **Implement `push_sync(ctx)` stub**:
   ```python
   async def push_sync(ctx) -> dict:
       """Push stub — real push sync implemented in S03."""
       return {"status": "skipped", "reason": "not implemented"}
   ```

## Must-Haves

- [ ] `sync_engine.py` exists at `apps/monday-sync/services/sync_engine.py`
- [ ] `pull_sync(ctx)` is async and returns a result dict
- [ ] Auth check: returns skipped if not connected
- [ ] No boards check: returns skipped if no boards selected
- [ ] Per-board iteration with per-board column mapping config from settings
- [ ] Column mapping read from settings key `column_mapping_{board_id}`
- [ ] Label mapping read from settings key `label_mapping_{board_id}`
- [ ] Properties built via `build_task_properties()` with stored mapping
- [ ] Group title set from `item["group"]["title"]` (not column_values)
- [ ] Subitem → parentTask edge creation (Phase 3)
- [ ] Two-phase bulk create (Phase 1 create, Phase 2 body/edges)
- [ ] Per-item error isolation (try/except per item, count errors, continue)
- [ ] `push_sync(ctx)` returns `{"status": "skipped", "reason": "not implemented"}`
- [ ] Bulk commands bypass SDK via `ctx.commands._client` posting to `/api/commands/bulk`
- [ ] Source string is `"monday-sync"` in bulk command submissions
- [ ] File passes `ast.parse()` syntax check

## Verification

- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/sync_engine.py').read())"` — passes
- `grep "async def pull_sync" apps/monday-sync/services/sync_engine.py` — found
- `grep "async def push_sync" apps/monday-sync/services/sync_engine.py` — found
- `grep "monday-sync" apps/monday-sync/services/sync_engine.py` — source string present
- `grep "parentTask" apps/monday-sync/services/sync_engine.py` — present
- `grep "group.*title" apps/monday-sync/services/sync_engine.py` — group title handling present

## Inputs

- `apps/jira-sync/services/sync_engine.py` — reference pattern (553 lines). **Clone the structure, adapt for Monday.com specifics.** Key differences: per-board iteration, configurable column mapping, group from item.group, subitems, no delta query.
- `apps/monday-sync/services/field_mapper.py` — `build_task_properties(item, column_mapping, status_label_mapping, priority_label_mapping, board_id, sync_time)` returns `(props, assignee_user_id)`. `compute_slug(item_name, item_id)` returns `"monday-{hash16}"`. `BPKM` constant.
- `apps/monday-sync/services/person_matcher.py` — `PersonMatcher(graph, commands, client)` with `resolve(user_id, display_name)` returning Person IRI.
- `apps/monday-sync/services/auth.py` — `get_connection_status(state, client)` returns dict with `connected` bool.
- `apps/monday-sync/services/monday_client.py` — `MondayClient(http_client, state_client)` with `get_all_board_items(board_id)`, `get_subitems(item_ids)` (added in T01).
- T01 output: column mapping stored in settings as `column_mapping_{board_id}` JSON with shape `{"column_mapping": {...}, ...}`. Label mapping stored as `label_mapping_{board_id}` with shape `{"status_label_mapping": {...}, "priority_label_mapping": {...}}`.

## Observability Impact

- **New logger:** `monday_sync.sync` — INFO for sync start/complete/phase transitions, WARNING for per-item errors and subitem fetch failures
- **State keys written:** `last_sync_at` (ISO timestamp), `last_pull_result` (JSON with status, created, updated, skipped, errors, duration_ms, failed_items, parent_links)
- **Inspection:** Read `last_pull_result` from state to see sync outcomes. `failed_items` list identifies which Monday.com item IDs failed with per-item error isolation
- **Failure visibility:** `_make_result()` captures duration_ms and error counts; `_compute_status()` returns "error" when all items fail, "partial" on mixed results

## Expected Output

- `apps/monday-sync/services/sync_engine.py` — NEW: ~450 lines, complete pull sync engine + push stub
