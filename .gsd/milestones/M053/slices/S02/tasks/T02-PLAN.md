---
estimated_steps: 41
estimated_files: 4
skills_used: []
---

# T02: Implement MarketplaceRegistryService with fetch, cache, download, and SHA-256 verification

Create `backend/app/services/marketplace.py` with a `MarketplaceRegistryService` class that fetches a remote `registry.json`, caches it with a configurable TTL, downloads model archives, verifies SHA-256 hashes, and extracts to a target directory using the tar validator from T01. Also add config fields and create a `resolve_model_dir()` utility. Write unit tests with mocked httpx.

## Steps

1. Add two new config fields to `backend/app/config.py`:
   - `marketplace_registry_url: str = ""` (empty = marketplace disabled)
   - `marketplace_models_dir: str = "/app/data/models"`
2. Create `backend/app/models/paths.py` with `resolve_model_dir(model_id: str, extra_dirs: list[str] | None = None) -> Path | None` that searches `/app/models/` then `/app/data/models/` (and any extra_dirs) for a directory containing `manifest.yaml`
3. Create `backend/app/services/marketplace.py` with `MarketplaceRegistryService`:
   - `__init__(self, registry_url: str, models_data_dir: Path)` — store URL, data dir, init cache fields
   - `async def fetch_catalog(self) -> list[dict]` — fetch registry.json via httpx with 5s timeout, cache for 1 hour. On network error: log warning, return empty list. Call `validate_outbound_url()` on registry URL before fetch.
   - `async def download_and_install(self, model_id: str, model_service, user_id) -> dict` — find model in cached catalog, download archive URL (with `validate_outbound_url()`), compute SHA-256 of downloaded bytes and compare to registry manifest hash, extract to tempdir via `safe_extract()`, call `model_service.install(extracted_path, user_id)`, move extracted dir to `models_data_dir/model_id/` on success, clean up tempdir in finally block
   - Registry JSON schema: `{"models": [{"id": str, "name": str, "version": str, "description": str, "archive_url": str, "sha256": str, "size_bytes": int, "tags": [str]}]}`
4. Create `backend/tests/test_marketplace_service.py` with tests:
   - Catalog fetch: mock httpx response → returns parsed models list
   - Catalog cache: second call within TTL returns cached result without HTTP call
   - Catalog fetch failure: mock httpx timeout → returns empty list, no crash
   - Download + verify: mock archive download → SHA-256 matches → extraction succeeds
   - SHA-256 mismatch: mock download with wrong content → ValueError raised before extraction
   - SSRF guard: verify `validate_outbound_url()` is called (mock it to raise → confirm no HTTP call made)
   - Empty registry URL: service disabled, `fetch_catalog()` returns empty list immediately
5. Run tests

## Must-Haves

- [x] `validate_outbound_url()` called before every httpx request (R004)
- [x] SHA-256 hash verified before extraction (R005)
- [x] 5s timeout on registry fetch with graceful empty-list fallback (R006)
- [x] `resolve_model_dir()` searches both bundled and downloaded model directories
- [x] Registry response cached with 1-hour TTL
- [x] Tempdir cleanup in finally block — no leaked files on failure
- [x] Unit tests cover happy path, cache, timeout, hash mismatch, SSRF guard

## Verification

- `cd backend && python -m pytest tests/test_marketplace_service.py -v` — all tests pass

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Registry HTTP (catalog) | Log warning, return empty list | 5s httpx timeout, return empty list | Log warning for missing fields, return empty list |
| Archive HTTP (download) | ValueError with descriptive message | 30s httpx timeout, ValueError | ValueError — corrupt download caught by SHA-256 mismatch |
| Tar extraction | ValueError from tar_validator | N/A | ValueError — corrupt tar handled by tarfile module |
| Filesystem (tempdir) | OSError propagated | N/A | N/A |

## Observability Impact

- Structured logs: `registry.fetch` with URL, status, model count, duration
- Structured logs: `registry.download` with model_id, size, hash verification result
- Failure state: log warning on network errors with URL and exception type

## Inputs

- `backend/app/security/tar_validator.py`
- `backend/app/security/ssrf.py`
- `backend/app/config.py`
- `backend/app/services/models.py`

## Expected Output

- `backend/app/services/marketplace.py`
- `backend/app/config.py`
- `backend/app/models/paths.py`
- `backend/tests/test_marketplace_service.py`

## Verification

cd backend && python -m pytest tests/test_marketplace_service.py -v
