---
id: T02
parent: S01
milestone: M029
provides:
  - Jinja2 asset_url filter resolving logical names to content-hashed or dev paths
  - asset_manifest_available template global for conditional CDN fallback
  - init_template_helpers(app) wiring in main.py
key_files:
  - backend/app/template_helpers.py
  - backend/tests/test_template_helpers.py
  - backend/app/main.py
key_decisions:
  - Manifest presence is the sole dev/prod signal (no env var toggle needed)
  - _load_manifest caches after first read to avoid repeated filesystem access
  - asset_url returns empty string for None/empty input (safe for Jinja2 undefined vars)
patterns_established:
  - Module-level state with _load_manifest() idempotent loader pattern
  - autouse pytest fixture to reset module-level state between tests
observability_surfaces:
  - INFO log at startup with manifest path and entry count (production) or "running in dev mode" (development)
  - WARNING log if manifest contains invalid JSON or is not a dict
  - asset_manifest_available Jinja2 global visible to all templates
duration: ~10min
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Create Jinja2 asset_url filter with dev/prod mode and unit tests

**Added Jinja2 `asset_url` filter with manifest-based production resolution, dev-mode fallback, and 22 unit tests**

## What Happened

Created `backend/app/template_helpers.py` with four public functions: `_load_manifest()` reads and caches the JSON manifest, `asset_url()` resolves logical names to `/assets/hashed-name` (production) or `/js/name`, `/css/name` (dev), `is_asset_manifest_available()` returns the current mode, and `init_template_helpers(app)` wires everything into the Jinja2 environment.

Wired into `main.py` at line 478, after the existing filter registrations. The import is inline (same pattern as existing template setup code in that module-level block).

Wrote 22 unit tests covering: production resolution, dev fallback for JS/CSS/other, edge cases (None, empty, no extension, dotfiles), manifest loading from disk (valid JSON, missing file, invalid JSON, non-dict JSON, caching), and init_template_helpers registration in both modes.

## Verification

- `python -m pytest tests/test_template_helpers.py -v` — 22/22 passed in 0.03s
- `python -c "from app.template_helpers import asset_url; print(asset_url('workspace.js'))"` — printed `/js/workspace.js` (correct dev mode)
- LSP diagnostics on template_helpers.py — zero errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_template_helpers.py -v` | 0 | ✅ pass | 0.03s |
| 2 | `cd backend && .venv/bin/python -c "from app.template_helpers import asset_url; print(asset_url('workspace.js'))"` | 0 | ✅ pass | <1s |
| 3 | `lsp diagnostics backend/app/template_helpers.py` | - | ✅ pass | <1s |

### Slice-Level Verification (T02 — Partial)

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | `python -m pytest backend/tests/test_template_helpers.py -v` | ✅ pass | 22/22 tests pass |
| 2 | `grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/` — zero unguarded CDN refs | ⏳ not yet | Templates not modified until T03 |
| 3 | `docker compose build frontend` | ⏳ not yet | Dockerfile changes in T04 |

## Diagnostics

- **Check mode at runtime:** `from app.template_helpers import is_asset_manifest_available; print(is_asset_manifest_available())`
- **Check manifest loading:** Look for `Loaded asset manifest` or `Asset manifest not found` in startup logs
- **Override manifest path:** Set `ASSET_MANIFEST_PATH` env var to point at a custom manifest location
- **In Docker:** `docker compose logs api 2>&1 | grep 'asset manifest'` to confirm production mode

## Deviations

- Added a `test_non_dict_json` test (manifest is a JSON array) not explicitly listed in the plan — caught by the implementation's type check.

## Known Issues

None.

## Files Created/Modified

- `backend/app/template_helpers.py` — new module with asset_url filter, manifest loading, and init function
- `backend/app/main.py` — added import and call to init_template_helpers(app) after existing filter registrations
- `backend/tests/test_template_helpers.py` — 22 unit tests covering both modes + edge cases
- `.gsd/milestones/M029/slices/S01/tasks/T02-PLAN.md` — added Observability Impact section
