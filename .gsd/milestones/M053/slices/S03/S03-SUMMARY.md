---
id: S03
parent: M053
milestone: M053
provides:
  - Version status badges on installed model cards
  - Safe one-click model update from marketplace
requires:
  - slice: S02
    provides: MarketplaceRegistryService with fetch_catalog(), download_and_install(), SSRF guard, tar validation
affects:
  []
key_files:
  - backend/app/services/marketplace.py
  - backend/app/admin/router.py
  - backend/tests/test_marketplace_service.py
  - backend/app/templates/admin/models.html
  - backend/app/templates/admin/_marketplace.html
  - frontend/static/css/style.css
key_decisions:
  - Used packaging.version.Version for semantic version comparison — proper PEP 440 handling
  - Update endpoint downloads and verifies BEFORE removing old version to prevent data loss on download failure
  - CSS badges use color-mix() with theme tokens — consistent with M044 pattern
patterns_established:
  - Safe update pattern: download → verify → extract → confirm → THEN remove old → install new
observability_surfaces:
  - Ops log entries with activity_type=model.marketplace_update
  - Security audit log for update actions
drill_down_paths:
  - .gsd/milestones/M053/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M053/slices/S03/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T03:49:52.503Z
blocker_discovered: false
---

# S03: Version Checking + Update Notifications

**Installed model cards now show version status badges and a safe one-click Update button backed by download-before-remove logic and 10 new unit tests.**

## What Happened

Two tasks delivered end-to-end version checking and update UX for marketplace models.

T01 added `check_updates()` to `MarketplaceRegistryService` — compares installed model versions against the registry catalog using `packaging.version.Version` for proper semantic version comparison. Malformed versions are caught and skipped without crashing. The method returns a dict mapping model_id → {installed_version, latest_version, has_update}. A new POST `/admin/models/{model_id}/update` endpoint implements safe update ordering: download archive → verify SHA-256 → validate tar → extract → confirm manifest → THEN remove old version → install new version → persist to models_data_dir. This prevents data loss if the download or verification fails. Both `admin_models()` and `admin_models_marketplace()` now pass `update_status` context to templates. 10 unit tests cover all edge cases including malformed versions, multi-model scenarios, disabled service, and empty catalog.

T02 wired the `update_status` context into both admin templates. The installed models table gained a Status column with green "Up to date" / amber "Update available: vX.Y.Z" badges and a conditional Update button with `hx-post`, `hx-confirm` dialog, and loading indicator. The marketplace cards template shows "Update available" instead of "✓ Installed" for outdated models. CSS uses `color-mix()` with theme tokens (`--_color-green-500`, `--_color-amber-500`) — zero hardcoded hex values. Both templates degrade gracefully when `update_status` is empty (marketplace disabled or unreachable).

## Verification

All 30 marketplace tests pass (20 existing + 10 new TestCheckUpdates). Templates parse without Jinja2 errors. Zero hardcoded hex in style.css CSS additions. version-badge classes wired in CSS and both templates. update_status referenced in both models.html and _marketplace.html. check_updates() called from both admin_models and marketplace endpoints. hx-post update endpoint present in template.

## Requirements Advanced

- R006 — Update endpoint and check_updates() return empty dict when marketplace is disabled/unreachable — no crashes, no blocking waits

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T01 wrote 10 tests instead of the planned 7 — added malformed installed version and multi-model coverage. T02 used --_color-green-500 instead of --_color-green-600 because the latter doesn't exist in theme.css.

## Known Limitations

Update endpoint has not been tested against a live registry — only unit-tested with mocked HTTP. The update flow inherits the same SSRF guard and tar validation from S02's install flow.

## Follow-ups

None.

## Files Created/Modified

- `backend/app/services/marketplace.py` — Added check_updates() method with packaging.version.Version comparison
- `backend/app/admin/router.py` — Added POST /admin/models/{model_id}/update endpoint with safe download-before-remove flow; added update_status context to admin_models and marketplace endpoints
- `backend/tests/test_marketplace_service.py` — Added TestCheckUpdates class with 10 unit tests
- `backend/app/templates/admin/models.html` — Added Status column with version badges and Update button
- `backend/app/templates/admin/_marketplace.html` — Added update-available badge for outdated installed models
- `frontend/static/css/style.css` — Added version-badge CSS classes using color-mix() with theme tokens
