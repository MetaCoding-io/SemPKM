---
id: S02
parent: M054
milestone: M054
provides:
  - ExplorerConfigSpec model + migration 026
  - ExplorerConfigService async CRUD + preset seeding
  - 4 REST API endpoints for config CRUD
  - Config selector UI with presets + saved configs
  - Multi-panel OBJECTS sections with independent state
  - refreshExplorerTreeForSection() for section-scoped refresh
requires:
  - slice: S01
    provides: ExplorerConfig dataclass, config-options API, config-tree endpoint, explorer-config.js base module
affects:
  []
key_files:
  - backend/app/browser/explorer_models.py
  - backend/app/browser/explorer_config_service.py
  - backend/migrations/versions/026_add_explorer_configs.py
  - backend/app/browser/workspace.py
  - backend/app/main.py
  - backend/tests/test_explorer_config_service.py
  - frontend/static/js/explorer-config.js
  - backend/app/templates/browser/explorer_config_panel.html
  - frontend/static/css/explorer-config.css
  - e2e/helpers/selectors.ts
key_decisions:
  - D402: Multi-panel DOM access via class-based section-scoped selectors with Map-keyed per-section state
  - Presets use user_id=NULL (system-level, visible to all users via OR query in list_for_user)
  - Hierarchy is a pseudo-preset using sentinel value __hierarchy__, not stored as ExplorerConfig row
  - Update/delete structurally reject preset rows via is_preset=False in WHERE clause
  - API paths mounted under /browser prefix matching workspace_router convention
patterns_established:
  - ExplorerConfigService follows DashboardService pattern — async CRUD with session_factory constructor, get_or_create_presets for seeding
  - Per-section state Map keyed by DOM element for multi-instance UI components — avoids ID collisions when duplicating sections
  - Sentinel value pseudo-preset pattern (__hierarchy__) for special options that bypass the standard config pipeline
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M054/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M054/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M054/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T05:32:18.573Z
blocker_discovered: false
---

# S02: Config Persistence, Multi-Panel & Presets

**Added server-side explorer config CRUD with preset seeding, config selector UI with save/load/delete, Hierarchy pseudo-preset, localStorage persistence, and multi-panel OBJECTS sections with independent per-section state.**

## What Happened

Three tasks built the full persistence and multi-panel layer on top of S01's composable config engine.

**T01** created the ExplorerConfigSpec SQLAlchemy model (UUID PK, nullable user_id FK for system presets, config_json Text, is_preset Boolean), Alembic migration 026, and ExplorerConfigService with async CRUD methods. Presets (By Type, By Tag) are is_preset=True rows with user_id=NULL, visible to all users via OR query. Update and delete structurally reject preset rows by including is_preset=False in the WHERE clause. Four REST endpoints (GET list, POST create, PATCH update, DELETE) were added to workspace_router. Preset seeding runs at app startup via get_or_create_presets(). 24 unit tests cover CRUD, presets, user isolation, delete-preset-rejected, and config_json round-trip.

**T02** added the config selector UI — a dropdown with Presets and Saved Configs optgroups, a name input, and Save/Delete buttons above the config builder panel. Six new JS functions handle config list loading, saving, loading a selected config, deleting, and Hierarchy pseudo-preset handling. Hierarchy uses sentinel value `__hierarchy__` and calls the legacy mode=hierarchy endpoint rather than the composable config-tree endpoint; when selected, the config builder panel hides since filter/group/sort don't apply. Active config ID persists in localStorage and restores on page load.

**T03** refactored all DOM access from ID-based to class-based section-scoped selectors, enabling multiple independent OBJECTS sections. A `Map` keyed by DOM element stores per-section config state. A Duplicate button in the OBJECTS section header clones the section with a unique ID, independent config state, tree body, and localStorage key. Each duplicate has a close button. All existing exports (refreshExplorerTree, applyExplorerConfig, etc.) remain backward-compatible wrappers operating on the primary section. Template onclick handlers use internal helpers exposed on window.SemPKM for cleaner section-root extraction.

## Verification

24/24 backend unit tests pass (test_explorer_config_service.py, 0.60s). Model and service imports verified. All 4 CRUD API routes confirmed registered on workspace_router. ExplorerConfigService wired in main.py lifespan with preset seeding on startup. All key files exist on disk. window.SemPKM exports verified — 11 functions exported including duplicateExplorerSection, refreshExplorerTreeForSection, loadConfigList, saveCurrentConfig, deleteSelectedConfig. Per-section Map state, class-based DOM selectors, and backward-compat wrappers all confirmed in source.

## Requirements Advanced

- R011 — ExplorerConfigSpec model with CRUD API, preset seeding, config selector UI with save/load/delete, localStorage persistence across reloads
- R012 — Multi-panel OBJECTS sections via Duplicate button with independent per-section state Map, scoped localStorage keys, and close button
- R013 — By Type and By Tag presets auto-seeded on startup; Hierarchy pseudo-preset handled via sentinel value calling legacy endpoint

## Requirements Validated

- R011 — 24 unit tests prove CRUD round-trip. Config selector loads from API, save persists via POST, reload restores from localStorage UUID reference
- R012 — Duplicate creates independent section with own config state Map entry, tree body, and localStorage key. Close removes duplicate without affecting primary.
- R013 — Config selector shows By Type, By Tag as API-sourced presets and Hierarchy as pseudo-preset. Each renders correct tree (composable config for By Type/Tag, legacy endpoint for Hierarchy).

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

API paths use /browser/api/explorer/configs (under workspace_router's /browser prefix) rather than the plan's /api/explorer/configs. Hierarchy is handled as a pseudo-preset with sentinel value __hierarchy__ rather than a stored ExplorerConfig row. Template onclick handlers use internal helpers (_applyFromPanel, _resetFromPanel) exposed on window.SemPKM rather than calling public function names directly.

## Known Limitations

Migration 026 requires manual docker compose cp if container was started before the migration file existed on the host volume. Hierarchy preset is not a real ExplorerConfig row — it's a frontend-only sentinel that triggers the legacy endpoint.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/browser/explorer_models.py` — New ExplorerConfigSpec SQLAlchemy model with UUID PK, nullable user_id FK, config_json, is_preset
- `backend/app/browser/explorer_config_service.py` — New async CRUD service with create/get/list_for_user/update/delete/get_or_create_presets
- `backend/migrations/versions/026_add_explorer_configs.py` — New Alembic migration creating explorer_configs table
- `backend/app/browser/workspace.py` — Added 4 REST API endpoints for explorer config CRUD
- `backend/app/main.py` — Wired ExplorerConfigService in lifespan + preset seeding on startup
- `backend/tests/test_explorer_config_service.py` — 24 unit tests covering CRUD, presets, user isolation, config_json round-trip
- `frontend/static/js/explorer-config.js` — Major refactor: config selector UI, CRUD functions, section-scoped DOM access, per-section state Map, duplicateExplorerSection
- `backend/app/templates/browser/explorer_config_panel.html` — Added config selector row with dropdown/save/delete; changed IDs to classes for multi-section
- `frontend/static/css/explorer-config.css` — Styles for config selector row, save/delete buttons, duplicate/close buttons, multi-section
- `backend/app/templates/browser/workspace.html` — Added Duplicate button in OBJECTS section header
- `frontend/static/js/workspace.js` — Updated persona mode compat for section-scoped explorer config
- `e2e/helpers/selectors.ts` — Updated explorer selectors for class-based access pattern
