---
id: S01
parent: M053
milestone: M053
provides:
  - scan_available_models() function for discovering bundled models
  - Available-models card grid UI pattern for S02 marketplace extension
  - model_table block structure that includes both available and installed sections
requires:
  []
affects:
  - S02
key_files:
  - backend/app/admin/router.py
  - backend/app/templates/admin/models.html
  - frontend/static/css/style.css
key_decisions:
  - Available-models section placed inside model_table Jinja2 block so htmx partial swaps update both available and installed sections atomically
  - Original text-input install form preserved as collapsed details fallback for advanced users
  - type_count derived from distinct icon types in manifest rather than parsing ontology files
patterns_established:
  - scan_available_models() pattern: scan directory → parse manifests → filter installed → return metadata dicts
  - Card grid with htmx one-click install: hidden input carries model path, hx-target swaps encompassing block
observability_surfaces:
  - Structured log: 'Scanned %s: found %d available models' on each admin page load
drill_down_paths:
  - .gsd/milestones/M053/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M053/slices/S01/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T03:10:52.875Z
blocker_discovered: false
---

# S01: Auto-Discover Bundled Models

**Admin Mental Models page now auto-discovers bundled models from /app/models/ and displays them as installable cards with one-click install.**

## What Happened

Added `scan_available_models()` to `backend/app/admin/router.py` that scans a directory for subdirectories containing valid `manifest.yaml` files, parses each manifest, filters out already-installed models, and returns metadata dicts (model_id, name, description, version, path, type_count, icon_count). Wired the function into all four admin model routes (list, install, remove, refresh-artifacts) so the template always has current `available_models` context.

Restructured the admin Mental Models template to display uninstalled bundled models as styled cards in a responsive CSS grid. Each card shows model name, version badge, line-clamped description, and type/icon counts. Install button triggers htmx POST to the existing install endpoint with the model path as a hidden input. The available-models section lives inside the `model_table` Jinja2 block so htmx partial swaps after install/remove update both available and installed sections atomically. The original text-input install form is preserved as a collapsed `<details>` fallback for advanced path-based installs.

CSS follows the existing `upper-ontology-card` pattern using theme tokens and `color-mix()` for decorative tints. Responsive grid scales from 1 column on mobile to 3 on desktop.

## Verification

- `scan_available_models` import check: PASS
- Functional test: discovers all 8 bundled models with correct metadata: PASS
- Filtering: installed models excluded from available list: PASS
- Empty/invalid directory handling: returns empty list, no crash: PASS
- Template parse: Jinja2 loads without error: PASS
- Template structure: available-models-grid inside model_table block: PASS
- CSS: all new rules use theme tokens, zero hardcoded hex values: PASS
- htmx attributes: install button POSTs to correct endpoint with model path: PASS

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

scan_available_models also wired into admin_models_refresh_artifacts() route for consistency (not in original plan but logical). Install form kept as collapsed details element instead of fully removed.

## Known Limitations

The /app/models path is hardcoded at each call site in the routes (not a config variable). Scan reads from filesystem on every page load — no caching. Both are acceptable for the admin page's low traffic.

## Follow-ups

S02 will add marketplace registry (remote models). The available-models section established here is the UI pattern that S02 will extend with a "Browse Marketplace" section for cloud-hosted models.

## Files Created/Modified

- `backend/app/admin/router.py` — Added scan_available_models() function and wired into all 4 admin model routes
- `backend/app/templates/admin/models.html` — Added available-models card grid inside model_table block, collapsed original install form into details element
- `frontend/static/css/style.css` — Added responsive card grid and card component styles using theme tokens
