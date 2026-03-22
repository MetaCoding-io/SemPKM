---
estimated_steps: 4
estimated_files: 2
skills_used:
  - test
---

# T03: Unit and API tests for federation features

**Slice:** S05 — Federated SPARQL Console
**Milestone:** M033

## Description

Write automated tests covering the federation config persistence layer (`federation_config.py`) and the API endpoints (POST/DELETE/GET on `/api/sparql/mirror/endpoints`). These tests validate the contract that the admin page and SPARQL console depend on.

## Steps

1. **Create `backend/tests/test_federation_config.py`** — unit tests for the persistence module:
   - `test_load_empty_file` — absent file returns model with empty endpoints list
   - `test_save_and_load_roundtrip` — save endpoints, load them back, verify equality
   - `test_merge_with_env_var` — mock `settings.get_allowed_endpoints()` returning `["https://a.example.org/sparql"]`, persist `["https://b.example.org/sparql"]`, verify merged list has both with correct source annotations
   - `test_merge_deduplicates` — same URL in both env and file → appears once with source "env"
   - `test_malformed_file` — write invalid JSON to the file, verify `load_federation_endpoints()` returns empty model without raising
   - `test_atomic_write` — verify temp file is used (check that save creates the file at the expected path)
   - Use `tmp_path` pytest fixture for file operations — pass explicit `path=` arguments to load/save functions

2. **Create `backend/tests/test_federation_endpoints_api.py`** — integration tests using FastAPI TestClient:
   - Follow the testing patterns in `backend/tests/test_mirror_service.py` for fixture setup
   - `test_add_endpoint` — POST a new endpoint URL, verify 200 and URL in response
   - `test_add_duplicate_endpoint` — POST the same URL twice, verify it's not duplicated
   - `test_add_invalid_url` — POST a non-HTTP URL (e.g. `ftp://...`), verify 400/422
   - `test_delete_endpoint` — POST to add, then DELETE, verify URL is gone from GET
   - `test_delete_env_endpoint_rejected` — mock env var with a URL, DELETE that URL, verify 400/409 response indicating env-sourced entries can't be removed
   - `test_get_merged_list` — mock env var with one URL, persist another, GET returns both with correct source annotations
   - `test_owner_only_access` — attempt POST/DELETE as non-owner user, verify 403
   - Use `tmp_path` to override the federation config file path in tests (monkeypatch `DEFAULT_FEDERATION_PATH`)

3. **Verify both test files pass:**
   - `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py -v`
   - `cd backend && .venv/bin/python -m pytest tests/test_federation_endpoints_api.py -v`

4. **Verify existing mirror tests still pass** (the GET endpoint response shape changed):
   - `cd backend && .venv/bin/python -m pytest tests/test_mirror_service.py tests/test_federation_discovery.py -v`
   - If any existing tests fail due to the response shape change, update them to match the new `{url, source, removable}` format

## Must-Haves

- [ ] Unit tests cover load/save/merge/dedup/malformed-file edge cases
- [ ] API tests cover add/delete/get/access-control/env-protection
- [ ] All new tests pass
- [ ] Existing mirror and federation tests still pass (or are updated for response shape change)

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_federation_config.py tests/test_federation_endpoints_api.py tests/test_mirror_service.py tests/test_federation_discovery.py -v`
- All tests pass with zero failures

## Inputs

- `backend/app/sparql/federation_config.py` — module under test (from T01)
- `backend/app/sparql/mirror_router.py` — API routes under test (from T01)
- `backend/tests/test_mirror_service.py` — existing test patterns to follow
- `backend/tests/test_federation_discovery.py` — existing test patterns to follow

## Expected Output

- `backend/tests/test_federation_config.py` — new unit test file
- `backend/tests/test_federation_endpoints_api.py` — new API test file
- `backend/tests/test_mirror_service.py` — potentially updated if response shape change breaks existing tests
- `backend/tests/test_federation_discovery.py` — potentially updated if response shape change breaks existing tests
