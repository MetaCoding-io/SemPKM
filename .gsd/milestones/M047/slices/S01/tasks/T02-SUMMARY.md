---
id: T02
parent: S01
milestone: M047
key_files:
  - backend/app/services/models.py
  - backend/app/models/router.py
  - backend/app/main.py
  - models/ppv/manifest.yaml
  - models/ppv/dashboards/ppv.json
key_decisions:
  - Dashboard/workflow services injected into ModelService via late property assignment because ModelService is created before DB init in the lifespan
  - TBox creation requires user_id; None skips TBox silently (covers starter model auto-install)
  - TBox creation/deletion failure is warning-level, not install/remove failure (D380 degraded mode)
duration: 
verification_result: passed
completed_at: 2026-04-04T23:22:00.612Z
blocker_discovered: false
---

# T02: Wire TBox dashboard/workflow lifecycle into ModelService install/remove/refresh and create PPV v2 manifest with test dashboard

**Wire TBox dashboard/workflow lifecycle into ModelService install/remove/refresh and create PPV v2 manifest with test dashboard**

## What Happened

Extended ModelService with optional dashboard_service and workflow_service params. Added user_id parameter to install(), remove(), and refresh_artifacts() — all optional with None default for backward compatibility. In install(): after seed materialization, loads TBox dashboards/workflows from manifest via tbox_loader and creates them tagged with source_model. In remove(): before graph clearing, deletes model-sourced surfaces. In refresh_artifacts(): deletes old and recreates from disk. Updated router to pass user.id, main.py to inject services via late property assignment. Created PPV v2 manifest with test dashboard definition.

## Verification

Ran task verification script: PPV parses as v2 with dashboards entrypoint, tbox_loader loads 1 dashboard. All 8 existing models parse unchanged. 21 existing model refresh tests pass. LSP diagnostics show no new errors. Install/remove/refresh method signatures backward compatible (all new params have defaults).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c 'parse PPV v2 manifest + load dashboards'` | 0 | ✅ pass | 1200ms |
| 2 | `python -c 'parse all 8 models'` | 0 | ✅ pass | 800ms |
| 3 | `python -c 'verify signatures backward compat'` | 0 | ✅ pass | 500ms |
| 4 | `pytest tests/test_model_refresh.py -x -q` | 0 | ✅ pass | 2600ms |

## Deviations

Dashboard/workflow services injected via late property assignment in main.py rather than at constructor time, because ModelService is created before DB initialization. Plan suggested constructor params, which are accepted but None at construction time.

## Known Issues

None.

## Files Created/Modified

- `backend/app/services/models.py`
- `backend/app/models/router.py`
- `backend/app/main.py`
- `models/ppv/manifest.yaml`
- `models/ppv/dashboards/ppv.json`
