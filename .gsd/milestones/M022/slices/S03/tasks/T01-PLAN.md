---
estimated_steps: 5
estimated_files: 2
---

# T01: Add reverse mapping functions to field_mapper.py

**Slice:** S03 — Push sync + section-based status moves
**Milestone:** M022

## Description

Add four reverse mapping functions to `field_mapper.py` that convert bpkm properties back to Asana API format for push sync. These are pure functions with no I/O — they take field_config and discovered field data as inputs and return Asana-formatted output. This is the prerequisite for the push pipeline in T02.

The core challenge is enum option GID resolution: the stored `status_mapping` and `priority_mapping` map `{AsanaEnumName: bpkmStatus}`, but the Asana PATCH API needs `{"custom_fields": {"<field_gid>": "<enum_option_gid>"}}`. The `discovered_enum_fields` data (from S01's discover-fields route) contains `enum_options` with both `name` and `gid` per option — this is the lookup source.

For section-based status, the stored `status_mapping` maps `{SectionName: bpkmStatus}` and `discovered_sections` maps `{gid, name}` per section. Reverse mapping goes: bpkm status → section name (via inverted mapping) → section GID (via discovered_sections lookup).

## Steps

1. **Read** `apps/asana-sync/services/field_mapper.py` to understand the existing forward mapping patterns and module structure.

2. **Add reverse mapping functions** at the bottom of `field_mapper.py`:
   - `reverse_status_mapping(bpkm_status, field_config)` → Returns a dict with key `"type"` ("custom_field" or "section") and either `"enum_option_name"` or `"section_name"` depending on `field_config["status_source"]`. Returns `None` if the status has no reverse mapping (unknown value). When `status_source` is `"completed_only"`, return the completed boolean mapping: `"done"` → `True`, anything else → `False`, via a `"completed"` type.
   - `reverse_priority_mapping(bpkm_priority, field_config)` → Returns the Asana enum option name (string) for the given bpkm priority, or `None` if unmapped. Inverts `field_config["priority_mapping"]`.
   - `build_asana_patch(bpkm_properties, field_config, discovered_enum_fields)` → Assembles the `{"custom_fields": {gid: enum_option_gid}}` dict for PATCH. Handles both status (when custom_field mode) and priority custom fields. Resolves enum option names to GIDs by scanning `discovered_enum_fields` list for matching field GID + option name. Also handles title update via `{"name": title}`. Returns the complete PATCH body dict (may be empty if no pushable changes).
   - `resolve_section_gid_for_status(bpkm_status, field_config, discovered_sections)` → Returns the section GID string for the target section, or `None` if no mapping found. Inverts `field_config["status_mapping"]` to get section name, then scans `discovered_sections` list for matching name → GID.

3. **Add a helper** `_resolve_enum_option_gid(field_gid, option_name, discovered_enum_fields)` → scans the list for the field with matching GID, then scans its `enum_options` for matching name, returns the option's GID or `None`.

4. **Add unit tests** to `backend/tests/test_asana_field_mapper.py` — approximately 30 tests in a new test class `TestReverseMapping`:
   - `test_reverse_status_custom_field_mapped` — status_source="custom_field", known bpkm status → correct enum option name
   - `test_reverse_status_custom_field_unknown` — unknown bpkm status → None
   - `test_reverse_status_section_mapped` — status_source="section", known status → correct section name
   - `test_reverse_status_section_unknown` — unknown status → None
   - `test_reverse_status_completed_only_done` — status_source="completed_only", "done" → completed=True
   - `test_reverse_status_completed_only_todo` — "todo" → completed=False
   - `test_reverse_priority_mapped` — known bpkm priority → enum option name
   - `test_reverse_priority_unknown` — unknown priority → None
   - `test_reverse_priority_empty_mapping` — empty priority_mapping → None
   - `test_build_asana_patch_status_custom_field` — builds correct custom_fields dict with GID-resolved enum value
   - `test_build_asana_patch_priority` — includes priority custom field in patch
   - `test_build_asana_patch_title` — includes name field for title changes
   - `test_build_asana_patch_combined` — status + priority + title all present
   - `test_build_asana_patch_empty` — no pushable changes → empty dict
   - `test_build_asana_patch_unknown_enum_gid` — field GID not in discovered_enum_fields → field omitted from patch
   - `test_build_asana_patch_unknown_option_name` — option name not in enum_options → field omitted
   - `test_build_asana_patch_section_mode_excludes_status` — when status_source="section", status NOT included in custom_fields patch (handled separately via section move)
   - `test_build_asana_patch_completed_only` — when status_source="completed_only", includes `"completed": True/False` in patch body
   - `test_resolve_section_gid_found` — known status → correct section GID
   - `test_resolve_section_gid_unknown_status` — unknown status → None
   - `test_resolve_section_gid_section_not_in_discovered` — section name found in mapping but GID not in discovered_sections → None
   - `test_resolve_enum_option_gid_found` — matching field + option → GID
   - `test_resolve_enum_option_gid_field_not_found` — wrong field GID → None
   - `test_resolve_enum_option_gid_option_not_found` — wrong option name → None

5. **Verify** all tests pass and syntax is valid.

## Must-Haves

- [ ] `reverse_status_mapping()` handles all 3 status_source modes (custom_field, section, completed_only)
- [ ] `reverse_priority_mapping()` inverts the priority_mapping dict
- [ ] `build_asana_patch()` resolves enum option names → GIDs via discovered_enum_fields
- [ ] `resolve_section_gid_for_status()` resolves bpkm status → section GID via discovered_sections
- [ ] All existing 92 field mapper tests still pass
- [ ] 25+ new reverse mapping tests pass

## Verification

- `uv run pytest backend/tests/test_asana_field_mapper.py -q` — 115+ tests pass
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"` — no SyntaxError

## Inputs

- `apps/asana-sync/services/field_mapper.py` — Existing forward mapping module (~388 lines). Add reverse functions at the bottom.
- `backend/tests/test_asana_field_mapper.py` — Existing 92 tests (~872 lines). Add new test class.
- S02 summary: `field_config` dict has keys: `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, `story_points_field_gid`. `status_mapping` maps `{AsanaEnumName: bpkmStatus}` (for custom_field mode) or `{SectionName: bpkmStatus}` (for section mode). `priority_mapping` maps `{AsanaEnumName: bpkmPriority}`.
- S01 field discovery: `discovered_enum_fields` is a list of `{"gid": str, "name": str, "resource_subtype": "enum", "enum_options": [{"name": str, "gid": str}, ...]}`. `discovered_sections` is a list of `{"gid": str, "name": str}`.
- BPKM namespace prefix used in the existing module: `BPKM = "urn:sempkm:model:basic-pkm:"` — reference this for property IRI keys in `build_asana_patch`.

## Observability Impact

- **New signals:** None (pure functions, no I/O, no logging). These are building blocks consumed by T02's push sync engine.
- **Inspection surface:** Unit tests exercise all reverse mapping paths. A failing reverse mapping in production would surface as a push sync error in T02's `last_push_result` StateClient key.
- **Failure visibility:** `build_asana_patch()` returns an empty dict when GID resolution fails — the caller (T02's push engine) must detect and log this. `resolve_section_gid_for_status()` returns `None` on failure — same pattern.
- **Future agent inspection:** Run `uv run pytest backend/tests/test_asana_field_mapper.py -q` to verify all mapping paths. Grep for `reverse_status_mapping\|reverse_priority_mapping\|build_asana_patch\|resolve_section_gid` in the sync engine to see call sites.

## Expected Output

- `apps/asana-sync/services/field_mapper.py` — Extended with 4 reverse mapping functions + 1 helper (~80-100 new lines)
- `backend/tests/test_asana_field_mapper.py` — Extended with TestReverseMapping class (~200-250 new lines, 25+ tests)
