# S03: Push sync + section-based status moves — Research

**Date:** 2026-03-19

## Summary

Push sync follows the established pattern from 6 prior sync apps (Linear, GitHub, GCal, Outlook, CalDAV, Todoist): SPARQL query finds locally-changed tasks → reverse-map bpkm properties to provider fields → call provider API → update `lastSyncedAt` to prevent re-import loops. The novel element is section-based status push — when `status_source` is `"section"`, changing a task's status requires `POST /sections/{gid}/addTask` instead of a custom field PATCH. Both paths must coexist based on the user's stored configuration.

The AsanaClient already has both `patch_task()` (for custom field updates) and `add_task_to_section()` (for section moves). The field_mapper needs reverse mapping functions. The sync_engine needs `push_sync()` and `_find_changed_tasks()`. The settings UI needs sync direction/interval controls and push result stats. All of these are direct clones from Linear with Asana-specific adaptations.

## Recommendation

Build in three units: (1) reverse mapping functions in field_mapper.py, (2) push_sync pipeline in sync_engine.py, (3) settings UI + route wiring in app.py + connect_status.html. Follow the Linear push sync implementation exactly — same SPARQL change detection pattern, same `lastSyncedAt` loop prevention, same result structure.

## Implementation Landscape

### Key Files

- `apps/asana-sync/services/field_mapper.py` (~388 lines) — Needs reverse mapping functions: `reverse_status()` returns either a custom field enum value name or a section name depending on `status_source`; `reverse_priority()` returns a custom field enum value name; `build_asana_update()` assembles the PATCH body (and separately, section GID if section-based). No existing reverse functions — all new code.
- `apps/asana-sync/services/sync_engine.py` (~640 lines) — Needs `_find_changed_tasks()` SPARQL query (clone from Linear, change provider to `"asana"`), `push_sync()` pipeline (auth check → direction check → find changed → for each: reverse map → PATCH or section move → update lastSyncedAt → store result). The `_read_field_config()` and `_submit_commands_batched()` helpers already exist and are reusable.
- `apps/asana-sync/services/asana_client.py` (~400 lines) — Already has `patch_task(task_gid, data)` and `add_task_to_section(section_gid, task_gid)`. No changes needed.
- `apps/asana-sync/app.py` (~606 lines) — Needs: (a) settings route `/_fragments/settings/sync-config` for direction/interval, (b) update `sync_now` to run push after pull when bidirectional, (c) update `push_changes` task handler to call `push_sync()`, (d) update `_render_connect_status()` to pass sync direction/interval/push result to template.
- `apps/asana-sync/frontend/templates/connect_status.html` — Needs sync config section (direction radios, interval dropdown), Sync Now section, and push result stats. Clone from Linear's `connect_status.html`.
- `backend/tests/test_asana_field_mapper.py` (~872 lines, 92 tests) — Add reverse mapping tests.
- `backend/tests/test_asana_sync_engine.py` (~1258 lines, 58 tests) — Add push sync tests.

### Prior Art (reference implementations)

| Component | Linear Reference | Key Differences for Asana |
|-----------|-----------------|--------------------------|
| `_find_changed_tasks()` | `apps/linear-sync/services/sync_engine.py` | Change `externalProvider` filter from `"linear"` to `"asana"` |
| `push_sync()` | Same file, ~60 lines | Two push paths: custom field PATCH vs section move. Read `field_config` to decide. |
| `reverse_status()` | `apps/linear-sync/services/field_mapper.py` — `REVERSE_STATUS_MAP` | Asana uses dynamic mapping from user config, not a static dict. Invert `status_mapping` dict from StateClient. |
| `build_issue_update_input()` | Same file, ~50 lines | Asana equivalent builds `{"custom_fields": {gid: {enum_value: {gid: ...}}}}` or returns section info for the section path. |
| Settings UI | `apps/linear-sync/frontend/templates/connect_status.html` lines 45-95 | Same sync direction radios, poll interval dropdown, Sync Now button. |
| Push result stats | Same template, lines 135-170 | Same stat-group/stat-row HTML pattern for push result display. |

### Reverse Mapping Detail

**Custom field status push:** The stored `status_mapping` maps `{AsanaEnumName: bpkmStatus}`. Reverse is `{bpkmStatus: AsanaEnumName}`. But PATCH needs the enum option's GID, not its name. Options: (a) store enum option GIDs in the mapping config during S01 field discovery, or (b) look up GID from `discovered_enum_fields` at push time. The `discovered_enum_fields` StateClient key already has `enum_options` with both `name` and `gid` per option. Push should read this to resolve name→GID.

**Section-based status push:** The stored `status_mapping` maps `{SectionName: bpkmStatus}`. Reverse is `{bpkmStatus: SectionName}`. Then resolve section name → section GID from `discovered_sections` StateClient key (which stores `{gid, name}` per section). Then call `add_task_to_section(section_gid, task_gid)`.

**Priority push:** Same as status custom field — invert `priority_mapping`, resolve enum option GID from `discovered_enum_fields`.

### Build Order

1. **Reverse mapping functions in field_mapper.py** — Pure functions, no I/O, testable in isolation. Build `reverse_status_mapping()`, `reverse_priority_mapping()`, `build_asana_patch()`, `resolve_section_gid_for_status()`. This unblocks everything else.

2. **push_sync pipeline in sync_engine.py** — `_find_changed_tasks()` SPARQL (clone from Linear), `push_sync()` orchestrator. Depends on reverse mappers from step 1. Two push paths: if `status_source == "section"` and status changed, call `add_task_to_section`; otherwise (or additionally) call `patch_task` with custom field updates.

3. **Settings UI + route wiring in app.py + template** — Add sync-config route, update sync_now to be bidirectional, wire push_changes task, add UI controls to template. This is mostly copy from Linear's pattern.

### Verification Approach

- `uv run pytest backend/tests/test_asana_field_mapper.py backend/tests/test_asana_sync_engine.py -q` — expect 200+ tests (92 existing + ~30 reverse mapping + 58 existing + ~30 push sync)
- `ast.parse()` on all 4 modified source files
- All existing 168 Asana tests continue to pass (no regressions)

## Constraints

- **Custom field PATCH payload format**: Asana's custom field update uses `{"custom_fields": {"<field_gid>": "<enum_option_gid>"}}` — the value is the enum option's GID, not the option's name. The `discovered_enum_fields` data must be read at push time to resolve names to GIDs.
- **Section move is additive**: `POST /sections/{gid}/addTask` moves a task to a section but doesn't explicitly remove it from the previous section. Asana handles this — a task in a project can only be in one section at a time (the API moves it). No explicit "remove from old section" needed.
- **htmx URLs must use `/app/asana-sync/` prefix** — per KNOWLEDGE.md, all htmx URLs in app templates must route through the proxy.
- **`_read_field_config()` already exists** in sync_engine.py — reuse it for push, don't duplicate.
- **D204 bypass**: Push needs `ctx.commands._client` for `_submit_commands_batched` to update `lastSyncedAt` — same pattern as pull.

## Common Pitfalls

- **Enum option GID resolution** — The `status_mapping` and `priority_mapping` store human-readable names as keys (e.g. `"To Do": "todo"`). The Asana PATCH API needs enum option GIDs, not names. Push must cross-reference `discovered_enum_fields` to get the GID for a given option name. If the discovered fields data is stale (field options renamed in Asana), the push will fail per-task — error isolation handles this gracefully.
- **Section GID resolution** — Same issue: `discovered_sections` maps names to GIDs. If sections are renamed in Asana, the stored name won't match. Consider matching by GID stored in `status_mapping` instead — but S01 already stores by name. Accept this limitation and document it.
- **Push result key naming** — Linear uses `last_push_result` with keys `pushed`, `skipped`, `errors`. Maintain the same key names for template compatibility.
