# S01: Manifest v2 Infrastructure + TBox Install/Uninstall Lifecycle — UAT

**Milestone:** M047
**Written:** 2026-04-04T23:29:29.167Z

# S01 UAT: Manifest v2 Infrastructure + TBox Install/Uninstall Lifecycle

## Preconditions
- Backend venv active (`cd backend && source .venv/bin/activate`)
- All 8 model directories present in `models/` (basic-pkm, business-planning, crm, media-scheduler, ppv, research, rss-feeds, zettelkasten)

---

## Test Case 1: V1 Backward Compatibility — All Existing Models Parse Unchanged

**Steps:**
1. Run: `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; from pathlib import Path; [print(f'{parse_manifest(d).modelId}: OK (v={parse_manifest(d).manifest_version or \"1.x\"})') for d in sorted(Path('../models').iterdir()) if d.is_dir() and (d/'manifest.yaml').exists()]"`
2. Verify each model prints `OK` with version `1.x` (except PPV which shows `2.0`)
3. Verify no exceptions are raised

**Expected:** 8 models parse, 7 show v=1.x, PPV shows v=2.0

---

## Test Case 2: V2 Manifest Schema — New Fields Parse Correctly

**Steps:**
1. Run: `cd backend && .venv/bin/python -c "from app.models.manifest import ManifestSchema; m = ManifestSchema(modelId='test', version='1.0.0', name='Test', namespace='urn:sempkm:model:test:', manifest_version='2.0', entrypoints={'dashboards': 'dashboards/{modelId}.json'}); print(f'version={m.manifest_version}, dashboards={m.entrypoints.dashboards}')"`
2. Verify output: `version=2.0, dashboards=dashboards/test.json` (placeholder resolved)
3. Run: `cd backend && .venv/bin/python -c "from app.models.manifest import ManifestSchema; m = ManifestSchema(modelId='test', version='1.0.0', name='Test', namespace='urn:sempkm:model:test:'); print(f'version={m.manifest_version}, dashboards={m.entrypoints.dashboards}')"`
4. Verify output: `version=None, dashboards=None`

**Expected:** V2 fields parse when present, default to None when absent

---

## Test Case 3: PPV V2 Manifest + TBox Loader

**Steps:**
1. Run: `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; from app.models.tbox_loader import load_tbox_dashboards; from pathlib import Path; m = parse_manifest(Path('../models/ppv')); d = load_tbox_dashboards(Path('../models/ppv'), m); print(f'manifest_version={m.manifest_version}, dashboards_entrypoint={m.entrypoints.dashboards}, loaded={len(d)} dashboards'); print(f'dashboard name: {d[0][\"name\"]}')"`
2. Verify manifest_version=2.0, dashboards entrypoint is set, 1 dashboard loaded
3. Verify dashboard name is "PPV Test Dashboard"

**Expected:** PPV v2 manifest loads with test dashboard definition

---

## Test Case 4: TBox Loader Validation — Malformed Input

**Steps:**
1. Run: `cd backend && .venv/bin/python -c "
from app.models.tbox_loader import load_tbox_dashboards
from app.models.manifest import ManifestSchema
from pathlib import Path
import tempfile, json, os

# Test missing 'name' field
d = tempfile.mkdtemp()
with open(os.path.join(d, 'bad.json'), 'w') as f:
    json.dump({'dashboards': [{'description': 'no name'}]}, f)
m = ManifestSchema(modelId='test', version='1.0.0', name='Test', namespace='urn:sempkm:model:test:', manifest_version='2.0', entrypoints={'dashboards': 'bad.json'})
try:
    load_tbox_dashboards(Path(d), m)
    print('FAIL: should have raised ValueError')
except ValueError as e:
    print(f'OK: ValueError raised: {e}')
"`
2. Verify ValueError is raised with descriptive message about missing 'name' field

**Expected:** Loader rejects malformed input with clear error

---

## Test Case 5: Source Model Column — CRUD Operations

**Steps:**
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_tbox_lifecycle.py -v --tb=short -k "test_create_with_source_model or test_delete_by_model or test_list_by_model" 2>&1 | tail -15`
2. Verify all 6 tests pass (3 for DashboardService, 3 for WorkflowService)

**Expected:** source_model column correctly tags, filters, and deletes model-sourced rows

---

## Test Case 6: ModelService Install/Remove Lifecycle Integration

**Steps:**
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_tbox_lifecycle.py -v --tb=short -k "ModelService" 2>&1 | tail -15`
2. Verify all 5 integration tests pass:
   - v2 install creates dashboards tagged with source_model
   - v1 install creates zero TBox surfaces
   - install without user_id skips TBox silently
   - TBox creation failure returns success with warning (degraded mode)
   - remove deletes model-sourced dashboards/workflows

**Expected:** Full install/remove lifecycle works correctly for both v1 and v2 models

---

## Test Case 7: No Regressions in Existing Dashboard Tests

**Steps:**
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_dashboard.py -v --tb=short 2>&1 | tail -5`
2. Verify all 27 existing tests pass

**Expected:** Zero regressions from source_model additions

---

## Test Case 8: Full Test Suite — All 43 New Tests

**Steps:**
1. Run: `cd backend && .venv/bin/python -m pytest tests/test_manifest_v2.py tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v --tb=short 2>&1 | tail -5`
2. Verify `43 passed` in output

**Expected:** Complete test coverage passes

---

## Edge Cases Covered by Unit Tests
- V2 manifest with dashboards but no workflows (optional fields)
- V2 manifest with both dashboards and workflows entrypoints
- TBox loader with None entrypoint returns None (no-op)
- TBox loader with missing JSON file raises ValueError
- TBox loader with malformed JSON raises ValueError
- TBox loader with missing required fields raises ValueError
- delete_by_model removes only model-sourced rows, leaves user-created intact
- ModelService install with TBox creation failure still returns success (degraded mode per D380)
