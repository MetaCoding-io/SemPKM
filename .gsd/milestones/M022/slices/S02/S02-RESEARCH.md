# S02: Pull sync with configurable field transforms + subtask nesting — Research

**Date:** 2026-03-19

## Summary

This slice implements pull sync (Asana tasks → bpkm:Task objects) using S01's persisted field mapping configuration. The core architecture is identical to the 6 prior sync apps: field_mapper.py (pure transforms), sync_engine.py (two-phase bulk orchestration), and person_matcher.py (SPARQL email lookup). The two novel aspects are: (1) field mapper reads status/priority mapping from StateClient config at sync time instead of using hardcoded maps, and (2) subtask recursion bounded at 5 levels requires a depth-tracking loop in the sync engine.

Both are tractable — the configurable mapping is just "read JSON from state and use as lookup dict" and subtask recursion is "call `get_subtasks()` per parent with a depth counter." The rest is standard property building, SPARQL IRI lookup, and two-phase bulk command submission.

## Recommendation

Build three files in this order:
1. **field_mapper.py** — pure functions, no side effects, testable in isolation. This is the most logic-dense file.
2. **person_matcher.py** — clone from Linear/Todoist, trivial adaptation (same email SPARQL pattern).
3. **sync_engine.py** — orchestration layer. Depends on field_mapper and person_matcher. Wires up client calls, recursion, and bulk commands.

Wire `poll_tasks` in app.py to call `pull_sync()` — replacing the skeleton handler from S01.

## Implementation Landscape

### Key Files

**To create:**

- `apps/asana-sync/services/field_mapper.py` (~350-400 lines) — configurable status/priority mapping, section-based status extraction, subtask parent linking, tag extraction, milestone detection (`resource_subtype: "milestone"` → `bpkm:Milestone`), HTML→Markdown notes conversion (markdownify), `compute_task_slug()`, `build_task_properties()`. The key novelty: `build_task_properties()` takes a `field_config` dict (read from StateClient) containing `status_source`, `status_mapping`, `priority_mapping`, `status_field_gid`, `priority_field_gid`, `story_points_field_gid`. Pure function — all state read happens in sync_engine and gets passed in.
- `apps/asana-sync/services/person_matcher.py` (~140 lines) — clone from `apps/linear-sync/services/person_matcher.py` with zero functional changes. Same SPARQL email lookup (`foaf:mbox` / `crm:email` UNION), same create-on-miss, same LRU cache.
- `apps/asana-sync/services/sync_engine.py` (~400-450 lines) — `pull_sync(ctx)` with: read field config from StateClient → iterate selected projects → `get_tasks()` with opt_fields → classify create/update → two-phase bulk → subtask recursion via `_fetch_subtasks_recursive()` with depth counter (max 5). New vs prior: subtask fetching loop in the main pull flow, field config dict passed to `build_task_properties()`.
- `backend/tests/test_asana_field_mapper.py` (~600-700 lines) — pure function tests covering all 3 status modes (completed_only, custom_field, section), priority mapping from config, tag extraction, milestone detection, HTML→Markdown, date truncation, slug computation, follower extraction. Target: 50-60+ tests.
- `backend/tests/test_asana_sync_engine.py` (~800-1000 lines) — async mock tests for pull_sync: auth guard, no-projects guard, new task creation, existing task update, loop prevention (lastSyncedAt), trashed→cancelled, subtask recursion (1 level, 3 levels, max depth enforcement), per-task error isolation, incremental sync (modified_since). Target: 40-50+ tests.
- `backend/tests/test_asana_person_matcher.py` (~250 lines) — same pattern as `test_linear_person_matcher.py`. Email match, login fallback, cache hit, person creation. Target: 10-12 tests.

**To modify:**

- `apps/asana-sync/app.py` — replace `poll_tasks` skeleton handler with call to `sync_engine.pull_sync(ctx)`. Add `last_sync_at` state cursor update. Add Sync Now route handler to trigger pull. Wire settings template to show sync stats (last_pull_result).

### Build Order

1. **field_mapper.py + test_asana_field_mapper.py** — pure functions, zero dependencies on running services. Must prove all three status modes work before sync engine can use them. This is the riskiest file because it handles the novel configurable transforms.

2. **person_matcher.py + test_asana_person_matcher.py** — trivial clone, 10 min. Unblocks sync engine.

3. **sync_engine.py + test_asana_sync_engine.py** — orchestration. Two novel pieces vs prior: (a) reading field config from state and passing to mapper, (b) `_fetch_subtasks_recursive()` with depth counter. Everything else is cloned from Linear/Todoist pattern.

4. **app.py wiring** — replace skeleton `poll_tasks`, add Sync Now, update settings template. Light.

### Verification Approach

```bash
# Field mapper tests (pure, no conftest)
pytest backend/tests/test_asana_field_mapper.py -v --noconftest

# Person matcher tests
pytest backend/tests/test_asana_person_matcher.py -v --noconftest

# Sync engine tests
pytest backend/tests/test_asana_sync_engine.py -v --noconftest

# Python syntax check on all new files
python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"
python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"
python3 -c "import ast; ast.parse(open('apps/asana-sync/services/person_matcher.py').read())"
```

Target: 100+ tests across the three test files, all passing with `--noconftest`.

## Constraints

- **Tests require `--noconftest`** — backend's pydantic Settings model doesn't recognize Asana env vars. All tests must be fully self-contained with mocks. Same as S01.
- **App Platform SDK IRI prefix enforcement** — sync engine must bypass `CommandClient` via `ctx.commands._client` for bulk commands on platform-minted IRIs (same D204 workaround as all prior sync apps).
- **opt_fields must be explicit** — Asana returns minimal data without `opt_fields`. The sync engine must construct the complete field list: `name,notes,html_notes,completed,completed_at,due_on,due_at,start_on,start_at,assignee,assignee.email,assignee.name,followers,followers.email,followers.name,tags,tags.name,memberships.section,memberships.section.name,custom_fields,custom_fields.name,custom_fields.enum_value,custom_fields.enum_value.name,custom_fields.number_value,parent,permalink_url,resource_subtype,modified_at`.
- **Asana `notes` is plain text, `html_notes` is HTML** — the design doc simplifies this. Use `html_notes` when available (convert via markdownify), fall back to `notes` (plain text passthrough).
- **Subtask API is per-parent** — `get_subtasks(task_gid)` returns only direct children. Recursion required for nesting. Each level is N API calls where N is the parent count at that level.

## Common Pitfalls

- **Custom field value extraction** — Asana custom field values live at `custom_fields[n].enum_value.name` for enums and `custom_fields[n].number_value` for numbers. The field mapper must match by `gid` against `status_field_gid`/`priority_field_gid`/`story_points_field_gid` from config, not by field name. Names can change; GIDs are stable.
- **Section membership path** — Task section is at `memberships[n].section.name`, not top-level. For section-based status mapping, extract the first section name from `memberships` and look it up in the status_mapping dict.
- **Subtask opt_fields** — subtask endpoint may need its own opt_fields string. The `get_subtasks()` client method already accepts opt_fields, but the sync engine must pass the same comprehensive field list used for top-level tasks.
- **Milestone detection** — tasks with `resource_subtype: "milestone"` should create `bpkm:Milestone` type instead of `bpkm:Task`. The `build_task_properties()` function should return the type, and the sync engine should use it in the create command.
- **MockResponse pattern** — per KNOWLEDGE.md pattern #2, use `data if data is not None else {}` not `data or {}` in test mocks to avoid empty list → empty dict coercion.

## Open Risks

- **Rate limit pressure from subtask recursion** — 100 top-level tasks × 5 subtasks each × 5 levels = worst case 2500+ API calls in a single sync. The first sync of a heavily nested project could exhaust the ~1500 units/min budget. Mitigation: depth counter enforces max 5 levels, and the client's 429 handler (built in S01) backs off via Retry-After. No proactive batching needed for v1.
- **Custom field GID stability across project re-selection** — if user changes selected projects, the old field GIDs may not exist in the new projects' custom fields. The field mapper should gracefully handle missing GIDs (skip the field, don't crash).

## Sources

- `apps/linear-sync/services/` — reference architecture: field_mapper.py (358 lines), sync_engine.py (529 lines), person_matcher.py (139 lines)
- `apps/todoist-sync/services/` — REST-only provider reference (closest API pattern to Asana)
- `apps/outlook-calendar/services/field_mapper.py` — markdownify HTML→Markdown pattern
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §1 — complete Asana field/entity/status/priority mapping tables
- S01 Summary forward intelligence — StateClient keys, status_source modes, client method signatures
