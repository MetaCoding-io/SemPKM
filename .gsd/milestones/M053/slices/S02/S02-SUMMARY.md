---
id: S02
parent: M053
milestone: M053
provides:
  - MarketplaceRegistryService on app.state.registry_service — fetch_catalog() and download_and_install()
  - resolve_model_dir() utility searching bundled + downloaded model directories
  - tar_validator.py with validate_tar_contents() and safe_extract()
  - Config fields marketplace_registry_url and marketplace_models_dir
  - Admin marketplace UI with browse and install endpoints
requires:
  - slice: S01
    provides: Admin Mental Models page structure, available-model-card CSS pattern, scan_available_models() for installed model detection
affects:
  - S03
key_files:
  - backend/app/security/tar_validator.py
  - backend/app/services/marketplace.py
  - backend/app/models/paths.py
  - backend/app/config.py
  - backend/app/main.py
  - backend/app/admin/router.py
  - backend/app/services/models.py
  - backend/app/services/icons.py
  - backend/app/templates/admin/_marketplace.html
  - backend/app/templates/admin/models.html
  - frontend/static/css/style.css
  - backend/tests/test_tar_validator.py
  - backend/tests/test_marketplace_service.py
key_decisions:
  - Archive-level compression ratio heuristic for tar (tar lacks per-entry compressed sizes — uses total archive size / member count)
  - Empty sha256 in registry catalog skips hash verification for unsigned development models
  - Archive manifest discovery uses rglob to handle both flat and nested directory structures
  - IconService extended with extra_dirs parameter rather than hardcoded path lists
  - Marketplace section uses htmx lazy-load (hx-trigger='load') to avoid blocking admin page render
patterns_established:
  - Tar archive security validation pattern (tar_validator.py) parallel to existing zip_validator.py — same API shape, same error reporting, tar-specific checks
  - Remote registry service pattern: HTTP fetch with monotonic cache + TTL, SSRF guard, graceful degradation on network errors
  - Multi-directory model resolution via resolve_model_dir() — searches ordered list of directories for manifest.yaml presence
  - SHA-256 hash verification before archive extraction as integrity gate
observability_surfaces:
  - Structured logs: registry.fetch with URL, status, model count, duration
  - Structured logs: registry.download with model_id, size, hash verification result
  - Warning-level logs on network errors with URL and exception type
  - Ops log entries for marketplace installs (admin audit trail)
drill_down_paths:
  - .gsd/milestones/M053/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M053/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M053/slices/S02/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T03:35:33.589Z
blocker_discovered: false
---

# S02: Marketplace Registry + Install-from-Cloud

**Built cloud-hosted model marketplace: registry catalog fetch with caching, archive download with SHA-256 verification, tar bomb/traversal protection, admin UI with htmx lazy-load browse section, and multi-directory model path resolution.**

## What Happened

Three-task slice delivering the full pipeline from remote JSON registry to installed model.

**T01 — Tar validator** created `backend/app/security/tar_validator.py` adapting the existing zip_validator.py pattern for tar.gz archives. Six security checks: path traversal (.. components), absolute paths, symlinks, hardlinks, uncompressed size limits, file count limits, and archive-level compression ratio heuristic (tar lacks per-entry compressed sizes so the ratio uses total-archive-size / member-count). `safe_extract()` validates then extracts using Python 3.12's `tarfile.data_filter` for defense-in-depth. 33 unit tests covering all rejection criteria, boundary conditions, corrupt archives, custom limits, and error message quality.

**T02 — Marketplace service** created `MarketplaceRegistryService` in `backend/app/services/marketplace.py` with `fetch_catalog()` (5s httpx timeout, 1-hour monotonic cache, empty-list fallback on any error) and `download_and_install()` (SSRF guard via `validate_outbound_url()` on both registry and archive URLs, SHA-256 hash verification before extraction, tempdir cleanup in finally block). Added `resolve_model_dir()` in `backend/app/models/paths.py` that searches `/app/models/` then `/app/data/models/` for a directory containing `manifest.yaml`. Config fields `marketplace_registry_url` and `marketplace_models_dir` added. 21 unit tests covering happy path, caching, TTL expiry, timeout, HTTP errors, malformed JSON, disabled service, SSRF guard, hash mismatch, missing manifest, empty hash skip, and path resolution.

**T03 — Integration wiring** connected MarketplaceRegistryService to app startup (`app.state.registry_service`), updated model path resolution in 4 call sites (refresh_artifacts, _load_entailment_defaults, IconService with new extra_dirs parameter across 6 usage points), added GET/POST admin marketplace endpoints with ops log and security audit, created `_marketplace.html` partial template with htmx lazy-load, model cards, install buttons with indicators, installed badges, and graceful error display. CSS uses theme tokens with color-mix() — zero hardcoded hex values. Fixed 4 pre-existing hardcoded hex values in legend CSS as part of the verification pass.

## Verification

All 54 tests pass (33 tar_validator + 21 marketplace_service). Import check confirms all new modules importable. Jinja2 template parse check passes for both models.html and _marketplace.html. resolve_model_dir grep confirms wiring in models.py and admin/router.py. SSRF guard grep confirms validate_outbound_url called before both httpx requests. CSS hex check returns 0 non-var hardcoded values in style.css.

## Requirements Advanced

- R002 — tar_validator.py rejects path traversal, absolute paths, symlinks, hardlinks — 33 unit tests prove all criteria
- R004 — validate_outbound_url() called before both catalog fetch and archive download httpx requests
- R005 — SHA-256 computed on downloaded bytes and compared to registry manifest value — mismatch raises ValueError before extraction
- R006 — 5s httpx timeout with graceful empty-list fallback, UI shows informative error message
- R007 — Install button has hx-indicator showing spinner during download+install operation
- R008 — Already-installed models show 'Installed' badge instead of install button in marketplace cards

## Requirements Validated

- R002 — 33 unit tests in test_tar_validator.py prove path traversal, absolute paths, symlinks, hardlinks all rejected with ValueError
- R004 — grep confirms validate_outbound_url() called on both registry URL and archive URL in marketplace.py
- R005 — test_sha256_mismatch_raises proves hash verification before extraction
- R006 — test_timeout_returns_empty_list and test_http_error_returns_empty_list prove graceful degradation

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

IconService extended with extra_dirs parameter across 6 call sites instead of the 3 described in the plan — more thorough coverage. Fixed 4 pre-existing hardcoded hex values in legend CSS to pass the hex verification check (pre-existing debt, not introduced by this slice).

## Known Limitations

Empty sha256 in registry catalog skips hash verification — supports unsigned models during development but should be removed before production registry goes live. Archive manifest discovery uses rglob to handle both root-level and nested directory structures in tar archives — may pick up unexpected manifest.yaml files in deeply nested structures. CDN/network dependency: marketplace is unavailable when registry URL is unreachable, but existing model management continues working.

## Follow-ups

S03 will add version checking and update notifications for installed marketplace models. Production registry needs actual .tar.gz archives hosted on GitHub Pages. GPG/Sigstore model signing deferred per D398.

## Files Created/Modified

- `backend/app/security/tar_validator.py` — New — tar archive security validator with 6 checks and safe_extract()
- `backend/app/services/marketplace.py` — New — MarketplaceRegistryService with catalog caching and archive download/verify/install
- `backend/app/models/paths.py` — New — resolve_model_dir() multi-directory model path resolution
- `backend/app/config.py` — Added marketplace_registry_url and marketplace_models_dir config fields
- `backend/app/main.py` — Wired MarketplaceRegistryService to app.state at startup
- `backend/app/admin/router.py` — Added GET/POST marketplace endpoints, updated _load_entailment_defaults to use resolve_model_dir
- `backend/app/services/models.py` — Updated refresh_artifacts to use resolve_model_dir
- `backend/app/services/icons.py` — Added extra_dirs parameter, scans bundled + downloaded model directories
- `backend/app/templates/admin/models.html` — Added Browse Marketplace section with htmx lazy-load
- `backend/app/templates/admin/_marketplace.html` — New — marketplace card grid partial with install buttons and installed badges
- `frontend/static/css/style.css` — Added marketplace badge/tag CSS, fixed 4 pre-existing hardcoded hex values
- `backend/tests/test_tar_validator.py` — New — 33 unit tests for tar validator
- `backend/tests/test_marketplace_service.py` — New — 21 unit tests for marketplace service
