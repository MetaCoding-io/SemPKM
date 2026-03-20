---
id: T04
parent: S01
milestone: M022
provides:
  - Custom field discovery route that unions enum/number fields and sections across selected projects
  - Field mapping save route for status/priority/story-points configuration
  - Complete mapping UI with status source radios, enum-to-bpkm mapping tables, and conditional display
  - Configuration persistence in StateClient as separate JSON keys
key_files:
  - apps/asana-sync/app.py
  - apps/asana-sync/frontend/templates/connect_status.html
  - apps/asana-sync/frontend/static/styles.css
key_decisions:
  - Status mapping form keys use status_map_{option_name} convention to enable arbitrary enum option names without a separate index scheme
  - Discovered field data persisted in StateClient so mapping UI survives page reloads without re-calling Asana API
  - Disconnect handler clears all 10 field mapping StateClient keys alongside auth state to prevent stale config on reconnect
patterns_established:
  - Inline IIFE JS pattern for configuration forms — window._asanaFieldMapping exposes handlers for onchange events, runs init on both DOMContentLoaded and immediately (for htmx swaps)
  - data-options attribute on select options containing JSON-encoded enum option names for client-side mapping table rendering
observability_surfaces:
  - "Logger: asana.sync.app logs discover-fields events (field counts by type) and field-mapping saves (status_source, mapping counts)"
  - "StateClient keys: discovered_enum_fields, discovered_number_fields, discovered_sections, status_source, status_field_gid, status_mapping, priority_field_gid, priority_mapping, story_points_field_gid"
  - "Template flag: fields_discovered boolean controls mapping form visibility — false after discovery indicates API failure or no custom fields"
duration: 18min
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T04: Custom field discovery, mapping UI, and configuration persistence

**Added field discovery route, status/priority/story-points mapping UI with conditional display, and JSON configuration persistence to StateClient**

## What Happened

Built the "configure before sync" flow that distinguishes Asana from prior sync apps. Three major additions to app.py:

1. **discover-fields route** (`POST /_fragments/settings/discover-fields`): Reads selected project GIDs from state, calls `get_custom_fields()` and `get_sections()` for each, unions results by GID, separates into enum vs number fields, and persists discovered data as JSON in StateClient.

2. **field-mapping route** (`POST /_fragments/settings/field-mapping`): Reads form data for status_source (3 modes), status/priority enum-to-bpkm value mappings via `status_map_*`/`priority_map_*` form keys, and story_points_field_gid. Persists each as separate StateClient key.

3. **Updated `_render_connect_status()`**: Loads all 9 field-related state keys and passes them to the template alongside existing connection/project data.

The template was rewritten from the T03 placeholder to include: discover-fields button (visible when projects are selected), full mapping form (visible after discovery) with status source radios, custom field dropdown with dynamic mapping table, section-based mapping table, priority field selector with mapping table, story points number field selector, and a saved configuration summary. Inline JS handles conditional show/hide and dynamic table rendering from `data-options` attributes. The disconnect handler was updated to clear all 10 field mapping keys.

## Verification

- `python3 -c "import ast; ast.parse(...)"` — app.py parses without syntax errors
- `grep -c 'status_source'` in template — 10 occurrences (radios, conditionals, saved config)
- `grep -c 'priority_field_gid'` in template — 4 occurrences (select, pre-select, saved config)
- `grep -c 'story_points_field_gid'` in template — 4 occurrences (select, pre-select, saved config)
- All 4 htmx URLs in template use `/app/asana-sync/` prefix
- 58 existing tests pass (30 auth + 28 client) with no regressions

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `grep -c 'status_source' connect_status.html` → 10 | 0 | ✅ pass | <1s |
| 3 | `grep -c 'priority_field_gid' connect_status.html` → 4 | 0 | ✅ pass | <1s |
| 4 | `grep -c 'story_points_field_gid' connect_status.html` → 4 | 0 | ✅ pass | <1s |
| 5 | `grep '/app/asana-sync/' connect_status.html \| wc -l` → 4 | 0 | ✅ pass | <1s |
| 6 | `pytest test_asana_auth.py test_asana_client.py -v` — 58 passed | 0 | ✅ pass | 1.7s |
| 7 | All 8 app files present (ls -la) | 0 | ✅ pass | <1s |
| 8 | manifest.yaml: appId=asana-sync, network perms, task entries | 0 | ✅ pass | <1s |

## Diagnostics

- **Logger:** `grep "asana.sync.app"` shows field discovery (project count, field counts) and mapping save (status_source, mapping counts) events
- **StateClient inspection:** `ctx.state.get("discovered_enum_fields")` returns JSON array of `{gid, name, resource_subtype, enum_options}` dicts; similarly for `discovered_number_fields`, `discovered_sections`
- **Mapping config:** `ctx.state.get("status_source")` → "completed_only" / "custom_field" / "section"; `ctx.state.get("status_mapping")` → JSON dict of option_name → bpkm_value
- **Template debugging:** `fields_discovered` template var controls mapping form visibility — check StateClient for discovered_enum_fields if form doesn't appear
- **API errors during discovery:** Logged at WARNING with project GID context; status page renders without field data (graceful degradation)

## Deviations

- Disconnect handler was updated to clear all field mapping state keys (10 keys total) — not in original plan but necessary to prevent stale config on reconnect
- Added a "Current Configuration" summary section below the mapping form to give visual feedback that config was saved — not planned but improves UX

## Known Issues

None.

## Files Created/Modified

- `apps/asana-sync/app.py` — Added discover-fields and field-mapping routes, updated _render_connect_status() with 9 field-related state keys, updated disconnect to clear mapping state (~586 lines total)
- `apps/asana-sync/frontend/templates/connect_status.html` — Complete rewrite: project selection + discover fields button + status/priority/story-points mapping form + inline JS for conditional display (~260 lines)
- `apps/asana-sync/frontend/static/styles.css` — Added mapping table, field selector, radio group, config summary styles; replaced dashed placeholder with active section styling (~380 lines total)
