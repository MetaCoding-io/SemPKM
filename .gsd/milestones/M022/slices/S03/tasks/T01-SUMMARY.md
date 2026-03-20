---
id: T01
parent: S03
milestone: M022
provides:
  - reverse_status_mapping() — bpkm status → Asana enum option name / section name / completed bool
  - reverse_priority_mapping() — bpkm priority → Asana enum option name
  - build_asana_patch() — assembles PATCH body with GID-resolved enum values
  - resolve_section_gid_for_status() — bpkm status → section GID via discovered_sections
  - _resolve_enum_option_gid() — helper for GID lookup in discovered enum fields
key_files:
  - apps/asana-sync/services/field_mapper.py
  - backend/tests/test_asana_field_mapper.py
key_decisions:
  - Reverse mapping returns structured dicts with a "type" discriminator (custom_field/section/completed) so the push engine can dispatch correctly
  - _invert_mapping helper is shared across all reverse functions — last-wins on duplicate values
patterns_established:
  - Reverse mapping pattern: invert {AsanaName: bpkmValue} → {bpkmValue: AsanaName}, then lookup by bpkm value
  - GID resolution chain: bpkm value → enum option name (via inverted mapping) → enum option GID (via discovered_enum_fields scan)
observability_surfaces:
  - none — pure functions, observability comes from callers in T02
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Add reverse mapping functions to field_mapper.py

**Added 5 reverse mapping functions (4 public + 1 helper) to field_mapper.py with 33 unit tests covering all push sync mapping paths.**

## What Happened

Added reverse mapping functions at the bottom of `field_mapper.py` to convert bpkm properties back to Asana API format for push sync:

- `reverse_status_mapping()` handles all 3 status_source modes: custom_field returns enum option name, section returns section name, completed_only returns boolean
- `reverse_priority_mapping()` inverts the priority_mapping dict to get the Asana enum name
- `build_asana_patch()` assembles the full PATCH body — resolves enum option names to GIDs via `_resolve_enum_option_gid()`, handles title/status/priority, correctly excludes section-mode status from the PATCH (it's handled by section moves)
- `resolve_section_gid_for_status()` maps bpkm status → section name (via inverted mapping) → section GID (via discovered_sections scan)
- `_invert_mapping()` shared helper for dict inversion

All functions are pure — no I/O, no logging, no state. They take field_config and discovered field data as inputs.

## Verification

- `uv run python -m pytest tests/test_asana_field_mapper.py -q` — 125 passed (92 existing + 33 new)
- `python3 -c "import ast; ast.parse(...)"` — syntax OK for field_mapper.py
- All existing sync engine tests still pass (58 passed)
- All 3 syntax checks from slice verification pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -m pytest tests/test_asana_field_mapper.py -q` | 0 | ✅ pass | 0.15s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `uv run python -m pytest tests/test_asana_sync_engine.py -q` | 0 | ✅ pass | 0.06s |

## Diagnostics

Pure functions with no runtime signals. Failures surface via callers — T02's `push_sync()` will log errors when `build_asana_patch()` returns empty or `resolve_section_gid_for_status()` returns None. Run `uv run python -m pytest tests/test_asana_field_mapper.py -v -k TestReverse` to exercise all reverse mapping paths.

## Deviations

- Tests organized into 5 classes (TestReverseStatusMapping, TestReversePriorityMapping, TestResolveEnumOptionGid, TestBuildAsanaPatch, TestResolveSectionGidForStatus) instead of one TestReverseMapping class — cleaner separation with 33 tests total (exceeds the 25+ target)
- pytest invocation uses `uv run python -m pytest` rather than `uv run pytest` — the latter fails because pytest isn't a direct script entry point in the uv env

## Known Issues

None.

## Files Created/Modified

- `apps/asana-sync/services/field_mapper.py` — Added ~95 lines: 4 public reverse mapping functions + 1 GID helper + 1 dict inversion helper
- `backend/tests/test_asana_field_mapper.py` — Added ~250 lines: 33 new tests across 5 test classes + 3 helper functions for test data construction
- `.gsd/milestones/M022/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
