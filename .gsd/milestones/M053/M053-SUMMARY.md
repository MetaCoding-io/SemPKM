---
id: M053
title: "Model Marketplace"
status: complete
completed_at: 2026-04-06T03:55:57.883Z
key_decisions:
  - D395: Static JSON registry + .tar.gz archives on GitHub Pages — zero-cost hosting with HTTPS, global CDN, forkable for private models
  - D396: Downloaded models stored in /app/data/models/ on writable sempkm_data volume — keeps bundled and downloaded models separate
  - D397: .tar.gz archive format with stdlib tarfile — flat directory structure preserved exactly, no new dependencies
  - D398: SHA-256 hash verification only (no GPG/Sigstore signing) — integrity verification sufficient for first-party registry over HTTPS
  - D399: Shared resolve_model_dir() utility searching [/app/models/, /app/data/models/] in order — minimum viable change for 3 critical call sites
key_files:
  - backend/app/security/tar_validator.py — tar archive security validator with 6 checks and safe_extract()
  - backend/app/services/marketplace.py — MarketplaceRegistryService with catalog caching, download/verify/install, version checking
  - backend/app/models/paths.py — resolve_model_dir() multi-directory model path resolution
  - backend/app/config.py — marketplace_registry_url and marketplace_models_dir config fields
  - backend/app/main.py — MarketplaceRegistryService wired to app.state
  - backend/app/admin/router.py — Browse/install/update marketplace endpoints + scan_available_models()
  - backend/app/templates/admin/_marketplace.html — Marketplace card grid partial with lazy-load
  - backend/app/templates/admin/models.html — Available models cards + version badges + update button
  - backend/tests/test_tar_validator.py — 33 unit tests for tar validator
  - backend/tests/test_marketplace_service.py — 30 unit tests for marketplace service
lessons_learned:
  - Tar archives lack per-entry compressed sizes (unlike ZIP). Archive-level compression ratio heuristic (total archive size / member count) is the practical alternative for tar bomb detection.
  - Python 3.12's tarfile.data_filter provides defense-in-depth for tar extraction — use it alongside custom validation for belt-and-suspenders security.
  - Safe update ordering (download → verify → extract → confirm → THEN remove old → install new) prevents data loss on download failure — never remove before the replacement is verified.
  - packaging.version.Version handles PEP 440 semver comparison correctly including pre-release, post-release, and dev suffixes — always use it instead of string comparison for version checks.
  - htmx lazy-load via hx-trigger='load' on a marketplace section prevents blocking the admin page render while the registry fetch completes — good pattern for optional remote-data sections.
---

# M053: Model Marketplace

**Built a cloud-hosted model marketplace with registry catalog, secure archive download/install pipeline, and version checking — enabling one-click model discovery and installation from an in-app admin UI without filesystem access.**

## What Happened

M053 delivered the full model marketplace in three slices across 7 tasks, producing 16 source files with 2,335 lines of changes and 63 unit tests.

**S01 — Auto-Discover Bundled Models** replaced the text-input install form with an auto-discovery system. `scan_available_models()` scans `/app/models/` for directories with valid `manifest.yaml` files, filters already-installed models, and returns metadata (name, version, description, type/icon counts). The admin Mental Models page now displays uninstalled bundled models as responsive CSS grid cards with one-click htmx install buttons. The original text-input form is preserved as a collapsed `<details>` fallback for advanced users.

**S02 — Marketplace Registry + Install-from-Cloud** was the high-risk slice, delivering the full pipeline from remote JSON registry to installed model. Three components: (1) `tar_validator.py` — security validator for tar.gz archives with 6 checks (path traversal, absolute paths, symlinks, hardlinks, size/count limits, compression ratio heuristic) plus `safe_extract()` using Python 3.12's `tarfile.data_filter` for defense-in-depth, backed by 33 unit tests. (2) `MarketplaceRegistryService` — HTTP client for the registry with 5s timeout, 1-hour monotonic cache, SSRF guard via `validate_outbound_url()` on both registry and archive URLs, SHA-256 hash verification before extraction, and graceful empty-list fallback on any network error, backed by 21 unit tests. (3) Integration wiring — service on `app.state`, admin GET/POST marketplace endpoints, `_marketplace.html` partial with htmx lazy-load, `resolve_model_dir()` for multi-directory model path resolution across 4 call sites, and `IconService` extended with `extra_dirs` parameter.

**S03 — Version Checking + Update Notifications** added `check_updates()` using `packaging.version.Version` for proper semantic version comparison. Admin UI shows green "Up to date" / amber "Update available: vX.Y.Z" badges on installed model cards. The update endpoint implements safe ordering: download → verify → extract → confirm → THEN remove old → install new, preventing data loss on download failure. 10 additional unit tests cover all edge cases.

All 63 tests pass. Cross-slice integration is clean — S01's card grid pattern was consumed by S02's marketplace cards, S02's service was extended by S03's version checking.

## Success Criteria Results

- ✅ **Admin → Mental Models shows available bundled models as clickable install cards** — S01 delivered `scan_available_models()` and card grid UI with htmx one-click install. Functional tests confirm 8 bundled models discovered with correct metadata.
- ✅ **Browse Marketplace section shows models from a remote registry** — S02/T03 created `_marketplace.html` partial loaded via `hx-trigger="load"` lazy-load with cards showing name, version, description, size, and tag pills.
- ✅ **Click Install on a marketplace model → download + verify + extract + install succeeds** — S02 delivered full pipeline with SSRF guard, SHA-256 verification, tar bomb/traversal protection. 54 unit tests pass (33 tar_validator + 21 marketplace_service).
- ✅ **Installed models show 'Up to date' or 'Update available' badge** — S03 added `check_updates()` with `packaging.version.Version` comparison, wired badges into both templates. 10 unit tests cover edge cases.
- ✅ **App functions normally when registry is unreachable** — `test_timeout_returns_empty_list` and `test_http_error_returns_empty_list` prove graceful degradation. `check_updates()` returns empty dict when disabled/unreachable.
- ✅ **Downloaded marketplace models persist in /app/data/models/** — Config field `marketplace_models_dir = "/app/data/models"` on writable `sempkm_data` volume. `resolve_model_dir()` searches both directories.
- ✅ **Archive downloads verified by SHA-256; tarfile extraction rejects path traversal** — 33 unit tests prove all rejection criteria. `test_sha256_mismatch_raises` proves hash verification. `safe_extract()` uses `tarfile.data_filter`.

## Definition of Done Results

- ✅ **All slices complete** — S01, S02, S03 all checked off in roadmap (0 unchecked items remain)
- ✅ **All slice summaries exist** — S01-SUMMARY.md, S02-SUMMARY.md, S03-SUMMARY.md all present on disk
- ✅ **All tests pass** — 63/63 tests pass (33 tar_validator + 30 marketplace_service) in 1.03s
- ✅ **Source files on integration branch** — 16 non-.gsd files changed, 2335 insertions confirmed via `git diff --stat`
- ✅ **Cross-slice integration verified** — S01→S02 card pattern reused, S02→S03 service extended with `check_updates()`, `resolve_model_dir()` consumed by 4 call sites across 2 files
- ✅ **Validation pass** — M053-VALIDATION.md exists with verdict: pass

## Requirement Outcomes

- **R002** (tarfile path validation): Active → **Validated**. 33 unit tests prove path traversal, absolute paths, symlinks, hardlinks all rejected with ValueError. `safe_extract()` uses Python 3.12 `data_filter` for defense-in-depth.
- **R003** (duplicate model install prevention): Remains **Active**. Marketplace cards show "Installed" badge instead of install button. No explicit unit test for a direct duplicate POST API call, but UI-level prevention is in place.
- **R004** (SSRF guard on outbound HTTP): Active → **Validated**. `validate_outbound_url()` called on both registry URL and archive URL in marketplace.py. Grep confirms both call sites.
- **R005** (SHA-256 hash verification): Active → **Validated**. `test_sha256_mismatch_raises` proves hash check blocks extraction before tar processing.
- **R006** (offline fallback): Active → **Validated**. `test_timeout_returns_empty_list`, `test_http_error_returns_empty_list`, and S03 `check_updates()` empty-dict return prove graceful degradation in all failure modes.
- **R007** (install progress visible): Remains **Active**. `hx-indicator` attribute wired on install buttons. No E2E visual verification of spinner.
- **R008** (duplicate prevention for marketplace): Remains **Active**. Same as R003 — "Installed" badge replaces install button in marketplace cards.

## Deviations

IconService extended with extra_dirs parameter across 6 call sites instead of planned 3 — more thorough coverage. 10 version-checking tests written instead of planned 7. Fixed 4 pre-existing hardcoded hex values in legend CSS during verification pass. S01 preserved original install form as collapsed details fallback (not in original plan but improves UX for advanced users).

## Follow-ups

Production registry needs actual .tar.gz archives hosted on GitHub Pages. GPG/Sigstore model signing deferred per D398 — add when community-submitted models are supported. E2E browser tests for the admin marketplace flow (currently only unit-tested). R003/R007/R008 remain active — could be validated with E2E tests in a future milestone.
