---
phase: 15
plan: 01
subsystem: settings
tags: [backend, frontend, settings, orm, migration, api, javascript]
dependency_graph:
  requires: []
  provides: [settings-infrastructure, user-settings-table, settings-api, settings-client]
  affects: [workspace, sidebar, manifest]
tech_stack:
  added: [SettingsService, UserSetting ORM, window.SemPKMSettings]
  patterns: [layered-settings-resolution, IIFE-module, FastAPI-dependency-injection]
key_files:
  created:
    - backend/app/services/settings.py
    - backend/migrations/versions/002_user_settings.py
    - backend/app/templates/browser/settings_page.html
    - frontend/static/js/settings.js
  modified:
    - backend/app/auth/models.py
    - backend/app/models/manifest.py
    - backend/app/browser/router.py
    - frontend/static/js/workspace.js
    - frontend/static/js/workspace-layout.js
    - backend/app/templates/components/_sidebar.html
    - backend/app/templates/base.html
decisions:
  - "SettingsService uses installed_models_dir=/app/models (matches Docker mount from main.py)"
  - "get_settings_service creates SettingsService per-request (stateless, no app.state needed)"
  - "ManifestSchema extensions use Field(default_factory=list) to preserve backward compatibility"
  - "special:settings tab skips right-pane section loading (no relations/lint for settings page)"
  - "settings.js auto-fetches on DOM ready so cache is warm before any consumer calls SemPKMSettings.get()"
metrics:
  duration: 6min
  completed: 2026-02-24
  tasks: 2
  files: 11
---

# Phase 15 Plan 01: Settings Infrastructure Summary

Settings infrastructure layer: UserSetting ORM with layered resolution service (system < manifest < user DB), four REST endpoints, window.SemPKMSettings client cache, and Ctrl+, shortcut opening a Settings tab in the active editor group.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | UserSetting ORM, migration, SettingsService, ManifestSchema extensions | d618833 | models.py, settings.py, 002_user_settings.py, manifest.py |
| 2 | Settings routes, settings.js client, Ctrl+, shortcut, sidebar link | 27a59ab | router.py, settings.js, workspace.js, workspace-layout.js, _sidebar.html |

## What Was Built

**Database layer:**
- `UserSetting` ORM model in `backend/app/auth/models.py` — per-user key/value overrides with unique constraint on (user_id, key)
- Alembic migration `002_user_settings.py` — creates user_settings table with index and cascade-delete FK
- Table auto-created via `Base.metadata.create_all` in main.py lifespan (verified present in SQLite DB)

**Service layer:**
- `SettingsService` in `backend/app/services/settings.py` with five methods: `get_all_settings`, `get_user_overrides`, `resolve`, `set_override`, `reset_override`, `remove_model_overrides`
- Three-layer resolution: system defaults (SYSTEM_SETTINGS dict) < model manifest defaults (scanned from /app/models) < user DB overrides
- `core.theme` registered as sole system setting (default: "system", options: light/dark/system)
- `SettingDefinition` dataclass with key/label/description/input_type/options/default/category/model_id

**Manifest extensions:**
- `ManifestSettingDef` — short key, label, description, input_type, options, default
- `ManifestIconContextDef` — per-context icon/color/size
- `ManifestIconDef` — type, fallback icon/color, tree/graph/tab context overrides
- `settings` and `icons` fields added to `ManifestSchema` as `Field(default_factory=list)` — existing manifests parse without changes

**API layer (4 routes):**
- `GET /browser/settings` — renders settings_page.html stub (Phase 15-02 fills in real UI)
- `GET /browser/settings/data` — returns resolved settings as JSON
- `PUT /browser/settings/{key:path}` — upserts user override, returns {key, value}
- `DELETE /browser/settings/{key:path}` — removes override, returns {key, default_value}

**Client layer:**
- `frontend/static/js/settings.js` — IIFE module exposing `window.SemPKMSettings` with get/set/reset/fetch
- Dispatches `sempkm:setting-changed` CustomEvent on set and reset
- Auto-fetches on DOM ready to warm cache
- Added to `base.html` before workspace-layout.js

**Workspace integration:**
- `openSettingsTab()` in workspace.js — opens or focuses `special:settings` tab in active group
- `Ctrl+,` shortcut added to `initKeyboardShortcuts()` keyboard handler
- `special:settings` branch in `loadTabInGroup()` in workspace-layout.js — routes to `/browser/settings`
- Right-pane section loading skipped for special:settings tabs
- User menu Settings link in `_sidebar.html` — removed `.disabled`, added `openSettingsTab()` onclick

## Deviations from Plan

**1. [Rule 2 - Missing critical functionality] Skip right-pane loading for special:settings tabs**
- **Found during:** Task 2
- **Issue:** `loadTabInGroup` would attempt to load relations/lint for `special:settings` which has no IRI to query
- **Fix:** Added `isSpecial` check alongside the existing view-tab guard before calling `loadRightPaneSection`
- **Files modified:** frontend/static/js/workspace-layout.js
- **Commit:** 27a59ab

## Self-Check: PASSED

All created files found on disk. Both task commits (d618833, 27a59ab) verified in git log.
