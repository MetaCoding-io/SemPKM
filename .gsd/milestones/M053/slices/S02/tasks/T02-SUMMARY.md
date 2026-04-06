---
id: T02
parent: S02
milestone: M053
key_files:
  - backend/app/services/marketplace.py
  - backend/app/models/paths.py
  - backend/tests/test_marketplace_service.py
  - backend/app/config.py
key_decisions:
  - Empty sha256 in catalog skips hash verification to support unsigned models during development
  - Archive manifest discovery uses rglob to handle both root-level and nested directory structures in tar archives
duration: 
verification_result: passed
completed_at: 2026-04-06T03:24:46.976Z
blocker_discovered: false
---

# T02: Created MarketplaceRegistryService with catalog caching, SSRF-guarded HTTP, SHA-256 archive verification, and safe extraction — 21 unit tests passing

**Created MarketplaceRegistryService with catalog caching, SSRF-guarded HTTP, SHA-256 archive verification, and safe extraction — 21 unit tests passing**

## What Happened

Built MarketplaceRegistryService in backend/app/services/marketplace.py with fetch_catalog() (5s timeout, 1-hour monotonic cache, empty-list fallback on any error) and download_and_install() (SSRF guard, SHA-256 verification, safe_extract from T01, tempdir cleanup in finally). Added resolve_model_dir() utility in backend/app/models/paths.py searching bundled and downloaded model directories. Added marketplace_registry_url and marketplace_models_dir config fields. 21 unit tests cover happy path, caching, TTL expiry, timeout, HTTP errors, malformed JSON, disabled service, SSRF guard on both catalog and archive, SHA-256 mismatch, missing manifest, empty hash skip, and path resolution.

## Verification

All 21 marketplace service tests pass. All 33 tar validator tests from T01 still pass. Total 54 tests passing across both test files.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_marketplace_service.py -v` | 0 | ✅ pass | 360ms |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_tar_validator.py -v` | 0 | ✅ pass | 290ms |

## Deviations

httpx.Response mock required request= parameter for raise_for_status() — added _mock_response() test helper. Test-only adaptation, no code change.

## Known Issues

None.

## Files Created/Modified

- `backend/app/services/marketplace.py`
- `backend/app/models/paths.py`
- `backend/tests/test_marketplace_service.py`
- `backend/app/config.py`
