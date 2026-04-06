---
id: T01
parent: S01
milestone: M053
key_files:
  - backend/app/admin/router.py
key_decisions:
  - type_count derived from distinct icon types in manifest, not from parsing ontology files
duration: 
verification_result: passed
completed_at: 2026-04-06T03:05:50.264Z
blocker_discovered: false
---

# T01: Added scan_available_models() function that discovers bundled Mental Models from /app/models/ and wired it into all admin model routes

**Added scan_available_models() function that discovers bundled Mental Models from /app/models/ and wired it into all admin model routes**

## What Happened

Added `scan_available_models(models_dir, installed_ids)` to `backend/app/admin/router.py`. The function iterates subdirectories of the given path, calls `parse_manifest()` on each (wrapped in try/except to skip invalid dirs), filters out already-installed models, and returns a list of dicts with model_id, name, description, version, path, type_count, and icon_count. Wired the function into admin_models(), admin_models_install(), admin_models_remove(), and admin_models_refresh_artifacts() routes so the template always has current available_models context.

## Verification

Import verification passed: `from app.admin.router import scan_available_models` succeeds. Functional test confirmed all 8 bundled models discovered, installed exclusion filtering works, nonexistent directory returns empty list, malformed dirs are skipped. LSP diagnostics show no new errors.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -c "from app.admin.router import scan_available_models; print('import OK')"` | 0 | ✅ pass | 2000ms |
| 2 | `Functional test: scan 8 models, filter exclusion, empty dir handling` | 0 | ✅ pass | 2000ms |
| 3 | `LSP diagnostics check` | 0 | ✅ pass | 1000ms |

## Deviations

Also wired available_models into the admin_models_refresh_artifacts() route's model_table partial branches for consistency.

## Known Issues

None.

## Files Created/Modified

- `backend/app/admin/router.py`
