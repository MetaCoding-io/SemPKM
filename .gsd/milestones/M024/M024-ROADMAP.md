# M024: Monday.com Sync App

**Vision:** Bidirectional sync between Monday.com items and bpkm:Task objects, with user-configurable column→property mapping and LoopGuard echo prevention — the final task provider integration on the App Platform.

## Success Criteria

- User installs Monday.com Sync app, enters API token, and verifies connection showing their username
- User selects boards to sync and sees discovered columns with their types
- User configures which Monday.com columns map to which bpkm properties (status, priority, due date, assignee, etc.)
- User maps Monday.com custom status labels to bpkm:taskStatus values (e.g. "Working on it" → "in-progress")
- Monday.com items appear as bpkm:Task objects with correct field values derived from the user-configured mapping
- Monday.com groups appear as taskGroup values on synced tasks
- Subitems appear as separate tasks with bpkm:parentTask linking to parent
- User edits a task in SemPKM and changes push back to Monday.com via column value mutations
- Push→poll cycle does not cause infinite echo loops (LoopGuard prevents re-import of pushed changes)
- Dependency column values create bpkm:dependsOn edges between tasks
- 350+ unit tests pass across all service modules
- Mock Monday.com GraphQL server passes selftest in Docker
- Playwright E2E test exercises install → auth → configure columns → sync → verify → push lifecycle
- User guide Chapter 37 documents Monday.com setup, column mapping walkthrough, and troubleshooting

## Key Risks / Unknowns

- **Column mapping UI complexity** — Monday.com's fully customizable columns require a multi-step setup wizard that's novel to the platform (second implementation after Asana D228). The UI must present discovered columns with appropriate mapping dropdowns filtered by column type, plus status/priority label mapping. This is the highest-risk feature because it's the most user-facing novel work.
- **GraphQL column value read/write format asymmetry** — Column values read from queries use one JSON shape but mutations expect a different JSON shape (e.g., status reads as `{label, index}` but writes as `{label: "Done"}`). Getting the write format wrong means silent data corruption.
- **No delta query** — Monday.com has no `updatedAt` filter for items. Each poll fetches all items from selected boards. Change detection must rely on content comparison against stored values. For large boards this could be slow.

## Proof Strategy

- **Column mapping UI** → retire in S02 by building the real column mapping configuration UI with board-specific column discovery, type-filtered dropdown rendering, and status/priority label mapping. Proven when a user can configure mappings and pull sync uses them to produce correctly-typed bpkm:Task objects.
- **Column value write format** → retire in S03 by implementing actual `change_multiple_column_values` mutations with format-specific serializers per column type. Proven when push sync round-trips a status change without error.
- **No delta query / echo prevention** → retire in S03 by implementing LoopGuard TTL cache that marks pushed changes and skips them on the next poll. Proven when a push→poll cycle does not create duplicate task updates.

## Verification Classes

- Contract verification: 350+ pytest unit tests across 7 test files (auth, client, field_mapper, person_matcher, sync_engine, loop_guard, app routes). All tests run offline via importlib loading from apps/monday-sync/services/.
- Integration verification: Mock Monday.com GraphQL server with selftest, Playwright E2E test against Docker stack proving full lifecycle.
- Operational verification: Complexity-based rate limit handling (retry on ComplexityException), LoopGuard TTL expiry for echo prevention.
- UAT / human verification: Column mapping UI usability — dropdowns correctly filter by column type, label mapping is intuitive.

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 4 slice deliverables are complete with passing tests
- Monday.com GraphQL client handles pagination, complexity tracking, and error hierarchy
- Column mapping configuration UI works end-to-end (board selection → column discovery → mapping dropdowns → label mapping → save)
- Pull sync produces bpkm:Task objects with field values derived from stored column mapping configuration
- Push sync executes `change_multiple_column_values` mutations with correct per-column-type JSON format
- LoopGuard prevents push→poll echo loops
- Groups appear as taskGroup, subitems link via parentTask, dependencies create dependsOn edges
- Mock Monday.com GraphQL server passes selftest
- Playwright E2E test passes against Docker stack
- User guide Chapter 37 documents the full workflow
- All MON requirements validated with test evidence
- Success criteria are re-checked against live behavior

## Requirement Coverage

- Covers: MON-01 (auth), MON-02 (board discovery), MON-03 (column mapping), MON-04 (status label mapping), MON-05 (priority label mapping), MON-06 (pull sync), MON-07 (groups as taskGroup), MON-08 (subitems→parentTask), MON-09 (push sync), MON-10 (LoopGuard), MON-11 (dependency edges), MON-12 (tags mapping), MON-13 (person matching), MON-14 (E2E + mock server), MON-15 (user guide)
- Partially covers: none
- Leaves for later: none
- Orphan risks: none

## Slices

- [x] **S01: Auth + GraphQL client + field mapper + person matcher** `risk:medium` `depends:[]`
  > After this: User can install Monday.com Sync, enter an API token, verify connection, and select boards to sync. Board columns are discovered and displayed. App scaffold with all 6 service modules, manifest, templates, and CSS exists. 150+ unit tests prove auth, client pagination/complexity, field mapper configurable transforms, and person matcher email resolution.

- [x] **S02: Column mapping configuration UI + pull sync** `risk:high` `depends:[S01]`
  > After this: User configures which Monday.com columns map to which properties via type-filtered dropdowns, maps custom status/priority labels to bpkm enum values, and triggers sync. Monday.com items appear as correctly-mapped bpkm:Task objects with groups as taskGroup and subitems linked via parentTask. 150+ unit tests prove configurable transforms and sync orchestration.

- [x] **S03: Push sync + LoopGuard + dependency edges** `risk:medium` `depends:[S02]`
  > After this: User edits a task in SemPKM and changes push to Monday.com via column value mutations. Dependency columns create bpkm:dependsOn edges. LoopGuard prevents push→poll echo loops. Tag columns map to bpkm:tags. 100+ unit tests prove push pipeline, reverse column format, LoopGuard TTL, and dependency edge creation.

- [x] **S04: E2E tests + user guide** `risk:low` `depends:[S01,S02,S03]`
  > After this: Mock Monday.com GraphQL server passes Docker selftest. Playwright E2E test exercises full install → auth → column mapping → sync → verify → push lifecycle. Chapter 37 user guide documents Monday.com setup with column mapping walkthrough.

## Boundary Map

### S01 → S02

Produces:
- `apps/monday-sync/services/auth.py` — `store_credentials(token)`, `get_credentials()`, `verify_connection()`, `get_connection_status()`, `clear_credentials()` via StateClient
- `apps/monday-sync/services/monday_client.py` — `MondayClient` with `get_boards()`, `get_board_columns(board_id)`, `get_board_groups(board_id)`, `get_board_items(board_id, limit, cursor)`, `get_users(user_ids)`, `get_tags(tag_ids)`, `change_multiple_column_values(board_id, item_id, column_values_json)`, `create_item(board_id, group_id, name, column_values_json)`. Complexity tracking via query response. Pagination via cursor. Error hierarchy: `MondayApiError`, `MondayAuthError`, `MondayRateLimitError`, `MondayComplexityError`.
- `apps/monday-sync/services/field_mapper.py` — `build_task_properties(item, column_mapping, status_label_mapping, priority_label_mapping)` pure function that reads column values using the user's stored mapping config. `build_reverse_column_values(task_properties, column_mapping, reverse_status_mapping, reverse_priority_mapping)` for push. Slug computation via `compute_slug(item_name, item_id)`.
- `apps/monday-sync/services/person_matcher.py` — `PersonMatcher` with `resolve_person(user_id, monday_client)` doing SPARQL email lookup → create-on-miss, LRU cache.
- `apps/monday-sync/app.py` — Route handlers for connect, disconnect, board selection, connect_status fragment. Task handler stubs for poll-tasks and push-changes.
- `apps/monday-sync/manifest.yaml` — appId, permissions, tasks, UI page, network: ["api.monday.com"]
- `apps/monday-sync/frontend/templates/connect.html` — API token input form
- `apps/monday-sync/frontend/templates/connect_status.html` — Connected state with board selection (column mapping UI deferred to S02)
- `apps/monday-sync/frontend/static/styles.css` — Scoped CSS under .monday-sync-settings

### S01 → S03

Produces:
- `MondayClient.change_multiple_column_values()` — mutation method for push sync
- `MondayClient.create_item()` — mutation method for new item creation
- `field_mapper.build_reverse_column_values()` — reverse mapping for push

### S02 → S03

Produces:
- `apps/monday-sync/services/sync_engine.py` — `pull_sync(ctx, monday_client, field_mapper_config)` with two-phase bulk create, per-item error isolation, group→taskGroup, subitem→parentTask, content comparison for change detection
- Column mapping stored in StateClient as JSON: `{board_id: {column_mapping: {...}, status_label_mapping: {...}, priority_label_mapping: {...}}}`
- Column mapping configuration UI endpoints: `configure-columns` (GET to render mapping form), `save-column-mapping` (POST to save mapping config)

### S03 → S04

Produces:
- `apps/monday-sync/services/loop_guard.py` — `LoopGuard` TTL cache with `mark_pushed(item_id, column_id)`, `is_echo(item_id, column_id)`, `cleanup()`
- `sync_engine.push_sync()` — SPARQL change detection, reverse column value mutations, LoopGuard integration
- Dependency column → bpkm:dependsOn edge creation in pull_sync
- Tag column → bpkm:tags mapping in field_mapper
- Complete bidirectional sync pipeline ready for E2E testing
