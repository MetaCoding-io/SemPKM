---
id: S01
parent: M047
milestone: M047
provides:
  - Manifest v2 schema with dashboards/workflows entrypoints for S02/S03 to use
  - source_model column and CRUD methods for tagging model-sourced surfaces
  - TBox loader module for reading dashboard/workflow JSON from model archives
  - PPV v2 manifest template that S03 will extend with real dashboards and workflows
  - ModelService install/remove/refresh lifecycle hooks for TBox surfaces
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - backend/app/models/manifest.py
  - backend/app/models/tbox_loader.py
  - backend/migrations/versions/025_add_source_model.py
  - backend/app/dashboard/models.py
  - backend/app/dashboard/service.py
  - backend/app/workflow/models.py
  - backend/app/workflow/service.py
  - backend/app/services/models.py
  - backend/app/models/router.py
  - backend/app/main.py
  - models/ppv/manifest.yaml
  - models/ppv/dashboards/ppv.json
  - backend/tests/test_manifest_v2.py
  - backend/tests/test_tbox_loader.py
  - backend/tests/test_tbox_lifecycle.py
key_decisions:
  - D376: TBox dashboards/workflows use plain JSON format matching existing service CRUD params, not RDF/JSON-LD
  - D377: source_model nullable column on dashboard_specs/workflow_specs distinguishes model-sourced from user-created
  - D378: manifest_version optional field (None=v1, '2.0'=v2) — zero migration of existing manifests
  - D380: TBox SQLite writes happen after RDF4J transaction — degraded failure mode, not full rollback
  - D381: user_id threaded through ModelService as optional param; None skips TBox creation silently (covers starter model auto-install)
patterns_established:
  - Manifest v2 schema extension pattern: optional fields with None defaults preserve v1 backward compat
  - source_model column pattern: NULL=user-created, model_id=model-sourced; delete_by_model()/list_by_model() for lifecycle
  - TBox loader JSON format: {"dashboards": [{name, description, layout, blocks}]} matching DashboardService.create() params
  - Late property assignment for services that depend on DB init completing after their consumer is constructed
observability_surfaces:
  - ModelService logs count of created/deleted TBox dashboards and workflows during install/remove
  - tbox_loader raises ValueError with file path context on malformed or missing JSON
drill_down_paths:
  - .gsd/milestones/M047/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M047/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M047/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-04T23:29:29.167Z
blocker_discovered: false
---

# S01: Manifest v2 Infrastructure + TBox Install/Uninstall Lifecycle

**Manifest v2 format with dashboards/workflows entrypoints, source_model tracking on SQLite rows, TBox loader module, and full install/uninstall lifecycle wiring — PPV ships as the first v2 model with a test dashboard. All 8 v1 models install unchanged. 43 unit tests prove the entire surface.**

## What Happened

This slice built the infrastructure layer for model-sourced operational surfaces (dashboards and workflows that ship with Mental Models rather than being user-created). Three tasks delivered a clean vertical:

**T01 — Schema & Data Layer:** Extended `ManifestSchema` with optional `manifest_version` field and `dashboards`/`workflows` entrypoints on `ManifestEntrypoints`, both supporting `{modelId}` placeholder resolution. Created Alembic migration 025 adding nullable `source_model` column with index to `dashboard_specs` and `workflow_specs` tables. Extended `DashboardService` and `WorkflowService` with `source_model` parameter on `create()`, plus `delete_by_model()` and `list_by_model()` methods. Created `tbox_loader` module that reads and validates JSON dashboard/workflow definitions from model archives.

**T02 — Lifecycle Wiring:** Extended `ModelService` with optional `dashboard_service` and `workflow_service` dependencies (injected via late property assignment in `main.py` because ModelService is created before DB init). Added `user_id` parameter to `install()`, `remove()`, and `refresh_artifacts()`. On install: after seed materialization, loads TBox definitions from manifest and creates them tagged with `source_model`. On remove: deletes model-sourced surfaces before graph clearing. On refresh: delete-and-recreate cycle. TBox creation failure is warning-level, not install failure (D380 degraded mode). Created PPV v2 manifest (`manifest_version: "2.0"`, `dashboards: "dashboards/ppv.json"`) with a test dashboard definition.

**T03 — Test Coverage:** 43 unit tests across 3 files: `test_manifest_v2.py` (16 tests — v1 backward compat parametrized over all 8 model dirs, v2 parsing, placeholder resolution), `test_tbox_loader.py` (14 tests — valid/invalid JSON, missing files, missing fields for both dashboards and workflows), `test_tbox_lifecycle.py` (13 tests — source_model CRUD on DashboardService/WorkflowService, ModelService integration with mocked triplestore proving v2 install creates dashboards, v1 install creates zero, no user_id skips silently, TBox failure returns success with warning, remove deletes model-sourced only).

## Verification

All 43 new tests pass (0.93s). 27 existing dashboard tests pass with zero regressions (0.77s). Slice-level verification confirms: v2 manifest parses with manifest_version and dashboards entrypoint, v1 manifest parses with None defaults, PPV v2 loads 1 dashboard from tbox_loader, all 8 existing models parse unchanged.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

Dashboard/workflow services injected via late property assignment in main.py rather than constructor params, because ModelService is created before DB initialization in the lifespan. Plan suggested constructor params — they're accepted but None at construction time, so late assignment was necessary. Minor: plan said 6 existing models, actual count is 8 — tests cover all 8.

## Known Limitations

PPV v2 manifest currently ships only a single test dashboard (markdown block). Real PPV dashboards (Action Items, Weekly Review, etc.) are S03 scope. The tbox_loader raises ValueError on missing files — the plan suggested returning None, but ValueError with file path context is more useful for debugging missing manifest entries.

## Follow-ups

S02 will expand PPV ontology with PillarScore, GuidingPrinciples, and enriched review fields. S03 will replace the test dashboard with 5 real dashboards and 5 workflows using the infrastructure built here.

## Files Created/Modified

- `backend/app/models/manifest.py` — Added manifest_version field and dashboards/workflows entrypoints to ManifestSchema/ManifestEntrypoints
- `backend/app/models/tbox_loader.py` — New module: load_tbox_dashboards() and load_tbox_workflows() for reading/validating JSON from model archives
- `backend/migrations/versions/025_add_source_model.py` — Alembic migration adding nullable source_model column with index to dashboard_specs and workflow_specs
- `backend/app/dashboard/models.py` — Added source_model column to DashboardSpec ORM model
- `backend/app/dashboard/service.py` — Added source_model param to create(), source_model field to DashboardData, delete_by_model(), list_by_model()
- `backend/app/workflow/models.py` — Added source_model column to WorkflowSpec ORM model
- `backend/app/workflow/service.py` — Added source_model param to create(), source_model field to WorkflowData, delete_by_model(), list_by_model()
- `backend/app/services/models.py` — Added dashboard/workflow service deps, user_id params, TBox create/delete in install/remove/refresh
- `backend/app/models/router.py` — Pass user.id to ModelService install/remove calls
- `backend/app/main.py` — Inject dashboard_service and workflow_service into ModelService via late property assignment
- `models/ppv/manifest.yaml` — Bumped to v2.0.0, added manifest_version: 2.0 and dashboards entrypoint
- `models/ppv/dashboards/ppv.json` — New file: test dashboard definition (markdown block) for PPV v2
- `backend/tests/test_manifest_v2.py` — 16 tests: v1 backward compat over 8 models, v2 parsing, placeholder resolution
- `backend/tests/test_tbox_loader.py` — 14 tests: valid/invalid JSON, missing files, missing fields for dashboards and workflows
- `backend/tests/test_tbox_lifecycle.py` — 13 tests: source_model CRUD, ModelService integration with install/remove TBox lifecycle
