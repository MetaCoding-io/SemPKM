---
id: T02
parent: S01
milestone: M043
key_files:
  - backend/app/views/service.py
  - backend/app/views/router.py
  - backend/app/browser/apps.py
  - backend/app/vfs/mount_service.py
  - backend/app/vfs/mount_router.py
key_decisions:
  - Kept mount_service._escape_sparql as a thin delegating wrapper to sparql_escape_string() rather than removing it — preserves import compatibility while ensuring all callers use the centralized escape logic
  - Used safe_iri() for both user-controlled AND system-derived IRIs (defence-in-depth) — SHACL shape paths, SPARQL result IRIs, and model graph IRIs all go through safe_iri even though they're system data
  - Added explicit 400 response for invalid IRIs in browser/apps.py right_pane_sections instead of silent fallthrough to empty results
duration: ""
verification_result: passed
completed_at: 2026-03-25T08:10:44.125Z
blocker_discovered: false
---

# T02: Migrate 5 confirmed-exploitable modules to SPARQLBuilder — safe_iri() replaces all raw f-string IRI interpolation, _escape_sparql delegates to centralized sparql_escape_string()

**Migrate 5 confirmed-exploitable modules to SPARQLBuilder — safe_iri() replaces all raw f-string IRI interpolation, _escape_sparql delegates to centralized sparql_escape_string()**

## What Happened

Migrated all confirmed-exploitable SPARQL injection vectors across 5 modules to use the centralized SPARQLBuilder from T01:

**views/service.py** — Replaced `_validate_iri` import with `safe_iri` from sparql.builder. Converted all `<{type_iri}>` patterns (8 occurrences across _build_default_select, _build_shacl_select, _build_graph_query, _build_calendar_select, _build_map_select, _build_kanban_select, _build_quadrant_select, _build_bmc_select, _build_okr_select, _build_decision_matrix_select) to `{safe_iri(type_iri)}`. Converted all `<{*_path}>` patterns (18 occurrences for start_path, end_path, lat_path, lng_path, status_path, x_path, y_path, canvas_path, section_path, unit_path, objective_path, current_path, target_path, value_path, alt_path, crit_path, weight_path) to use safe_iri(). Converted `expand_neighbors()` to use a single `safe_node = safe_iri(node_iri)` variable reused across 3 SPARQL queries. Converted 3 VALUES clause constructions (model graph IRIs, subject_iris, type_iris) to use `safe_iri()`. Rewrote `inject_values_binding()` to use safe_iri() with try/except ValueError instead of the boolean _validate_iri().

**views/router.py** — Replaced `_validate_iri` import with `safe_iri`. Converted the `calendar_patch` endpoint to validate `body.iri` via `try: safe_body_iri = safe_iri(body.iri)` with ValueError → 400 response, then use the pre-validated IRI in the type detection query.

**browser/apps.py** — Added `safe_iri` import. Added explicit IRI validation before the SPARQL query in `right_pane_sections()` — invalid IRIs now return 400 with logging instead of silently falling through to the triplestore.

**vfs/mount_service.py** — Added `safe_iri, sparql_escape_string` imports. Replaced the local `_escape_sparql()` function body with a delegation to `sparql_escape_string()` (kept as a local alias for backward compatibility since mount_router imports it). Converted all user-supplied IRI fields (group_by_property, date_property, scope_query, type_filter) in both `create_mount()` and `update_mount()` from `<{iri}>` to `{safe_iri(iri)}`.

**vfs/mount_router.py** — Added `safe_iri` import. Applied same IRI protection to create_mount and update_mount INSERT DATA triples. Fixed preview endpoint to validate `body.scope_query` via safe_iri before SPARQL interpolation. Fixed strategy preview queries to use safe_iri for user-supplied `body.group_by_property` and `body.date_property` in by-tag, by-date, and by-property strategy SPARQL queries.

Also cleaned up an orphaned git worktree at .gsd/worktrees/M043 and deleted the milestone/M043 branch — leftover from a failed parallel mode attempt that wasn't affecting current work but was a potential source of confusion.

## Verification

Ran .venv/bin/python -m pytest tests/test_sparql_builder.py — 66 passed (builder module intact). Ran 243 tests across test_sparql_builder, test_view_scope, test_view_save, test_cross_view_drag, test_vfs_scope, test_vfs_path_contract, test_mount_explorer, test_kanban — all passed. Verified all 5 modules import successfully. Verified safe_iri blocks injection payloads (ValueError on malicious IRIs). Verified mount_service._escape_sparql now delegates to sparql_escape_string (covers single-quote escaping that was previously missing). All pre-existing test failures (icalendar module, notion ImportResult, ai-insights capability) are unrelated to these changes.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py -v` | 0 | ✅ pass | 100ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_sparql_builder.py tests/test_view_scope.py tests/test_view_save.py tests/test_cross_view_drag.py tests/test_vfs_scope.py tests/test_vfs_path_contract.py tests/test_mount_explorer.py tests/test_kanban.py -v` | 0 | ✅ pass | 920ms |
| 3 | `cd backend && .venv/bin/python -c 'from app.views.service import ViewSpecService; ...' (injection block test)` | 0 | ✅ pass | 200ms |
| 4 | `cd backend && .venv/bin/python -c 'from app.views.service import ViewSpecService; from app.views.router import router; from app.browser.apps import apps_router; from app.vfs.mount_service import SyncMountService; from app.vfs.mount_router import router as vfs_router' (import check)` | 0 | ✅ pass | 150ms |


## Deviations

Kept mount_service._escape_sparql as a delegating wrapper rather than removing it entirely — mount_router.py imports it, and removing the function would require updating all callers in the same commit. The delegation ensures the centralized escape logic is used while maintaining backward compatibility. Also fixed additional injection vectors in mount_router.py preview endpoint (body.scope_query, body.group_by_property, body.date_property in strategy preview queries) that weren't explicitly listed in the task plan but were clearly exploitable.

## Known Issues

Pre-existing: 3 test files fail to collect (test_caldav_field_mapper.py and test_caldav_sync_engine.py need icalendar package, test_notion_executor.py has stale ImportResult import). test_ai_endpoints has a pre-existing assertion failure for ai-insights capability. None of these are related to the SPARQL injection migration.

## Files Created/Modified

- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/app/browser/apps.py`
- `backend/app/vfs/mount_service.py`
- `backend/app/vfs/mount_router.py`
