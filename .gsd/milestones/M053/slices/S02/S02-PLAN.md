# S02: Marketplace Registry + Install-from-Cloud

**Goal:** Cloud-hosted model registry so users can browse and install Mental Models from a remote marketplace. Full pipeline: fetch registry catalog → download archive → SHA-256 verify → tarfile extract with bomb/traversal protection → install via existing ModelService.install(). Installed marketplace models fully functional (icons, refresh-artifacts, entailment defaults).
**Demo:** After this: Admin → Mental Models shows a Browse Marketplace section with models from a remote registry. Click Install on a marketplace model → download + verify + extract + install → model types appear in explorer.

## Tasks
- [x] **T01: Created tar_validator.py with six security checks and safe_extract() using Python 3.12 data_filter, with 33 passing unit tests** — Create `backend/app/security/tar_validator.py` adapting the existing `validate_zip_contents()` pattern for tar.gz archives. Must reject: path traversal (absolute paths, `..` components), symlinks, tar bombs (oversized archives, excessive file count, suspicious compression ratios). Use Python 3.12's `tarfile.data_filter` for safe extraction semantics.

Also create comprehensive unit tests at `backend/tests/test_tar_validator.py` following the pattern of `test_zip_validator.py`.

## Steps

1. Read `backend/app/security/zip_validator.py` for the pattern — adapt the three-check structure (total size, file count, per-entry ratio) plus add tarfile-specific checks (path traversal, symlinks, absolute paths)
2. Create `backend/app/security/tar_validator.py` with `validate_tar_contents(tar_path, *, max_uncompressed_mb=2048, max_files=50000, max_ratio=100) -> None` that raises `ValueError` on any failure. Also add `safe_extract(tar_path, dest_dir)` that validates then extracts using `tarfile.data_filter`
3. Checks to implement:
   - Total uncompressed size (sum of member.size) vs max_uncompressed_mb
   - File count vs max_files
   - Per-entry compression ratio (member.size / tar file size * member count approximation) — tar doesn't have per-entry compressed size like zip, so use total archive size / member count as heuristic
   - Reject members with absolute paths (`member.name.startswith('/')`)
   - Reject members with `..` path components (`'..' in member.name.split('/')`)
   - Reject symlinks (`member.issym()`) and hardlinks (`member.islnk()`)
4. Create `backend/tests/test_tar_validator.py` with tests for: valid archive passes, path traversal rejected, absolute paths rejected, symlinks rejected, oversized archive rejected, too many files rejected, empty archive passes, custom limits
5. Run tests to confirm all pass

## Must-Haves

- [x] `validate_tar_contents()` rejects path traversal via `..` components
- [x] `validate_tar_contents()` rejects absolute paths
- [x] `validate_tar_contents()` rejects symlinks and hardlinks
- [x] `validate_tar_contents()` rejects tar bombs (size, count)
- [x] `safe_extract()` uses `tarfile.data_filter` for Python 3.12+ safe extraction
- [x] Unit tests cover all rejection criteria and happy path

## Verification

- `cd backend && python -m pytest tests/test_tar_validator.py -v` — all tests pass

## Negative Tests

- Path traversal: archive with `../../etc/passwd` member → ValueError
- Absolute path: archive with `/etc/passwd` member → ValueError
- Symlink: archive with symlink member → ValueError
- Oversized: archive exceeding max_uncompressed_mb → ValueError
- Too many files: archive exceeding max_files → ValueError
- Empty archive: passes validation (zero files is valid)

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Filesystem (tar file) | ValueError with descriptive message | N/A | ValueError — corrupt tar raises tarfile.ReadError, caught and re-raised as ValueError |
  - Estimate: 45m
  - Files: backend/app/security/tar_validator.py, backend/tests/test_tar_validator.py
  - Verify: cd backend && python -m pytest tests/test_tar_validator.py -v
- [ ] **T02: Implement MarketplaceRegistryService with fetch, cache, download, and SHA-256 verification** — Create `backend/app/services/marketplace.py` with a `MarketplaceRegistryService` class that fetches a remote `registry.json`, caches it with a configurable TTL, downloads model archives, verifies SHA-256 hashes, and extracts to a target directory using the tar validator from T01. Also add config fields and create a `resolve_model_dir()` utility. Write unit tests with mocked httpx.

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
  - Estimate: 1h
  - Files: backend/app/services/marketplace.py, backend/app/config.py, backend/app/models/paths.py, backend/tests/test_marketplace_service.py
  - Verify: cd backend && python -m pytest tests/test_marketplace_service.py -v
- [ ] **T03: Wire admin endpoints, marketplace UI, model path resolution, and startup integration** — Add admin endpoints for marketplace catalog and install, wire `MarketplaceRegistryService` into app startup, update model path resolution call sites, and extend the admin models template with a Browse Marketplace section.

## Steps

1. **Startup wiring** in `backend/app/main.py`:
   - Import `MarketplaceRegistryService` from `app.services.marketplace`
   - After model_service creation, create `MarketplaceRegistryService(settings.marketplace_registry_url, Path(settings.marketplace_models_dir))`
   - Store on `app.state.registry_service`
   - Ensure `Path(settings.marketplace_models_dir)` directory exists (`os.makedirs(..., exist_ok=True)`)

2. **Model path resolution** — update 3 critical call sites to search both directories:
   - `backend/app/services/models.py` line ~616 in `refresh_artifacts()`: replace `Path(f"/app/models/{model_id}")` with `resolve_model_dir(model_id)` from `app.models.paths`. If None, return error.
   - `backend/app/admin/router.py` `_load_entailment_defaults()` line ~1074: replace `os.path.join("/app/models", model_id, ...)` with `resolve_model_dir(model_id)` lookup. If None, return defaults.
   - `backend/app/services/icons.py` `IconService._build_cache()`: update to scan BOTH `/app/models/` and settings `marketplace_models_dir`. Accept a list of model directories or add a second scan loop.

3. **Admin endpoints** in `backend/app/admin/router.py`:
   - Add `GET /admin/models/marketplace` endpoint that fetches catalog from `request.app.state.registry_service`, cross-references with installed model IDs, renders a marketplace partial template
   - Add `POST /admin/models/marketplace-install` endpoint with `model_id: str = Form(...)` that calls `registry_service.download_and_install(model_id, model_service, user.id)`, returns updated model table partial. On success, invalidate ViewSpec cache. On failure, return error in context.
   - Both endpoints require `owner` role

4. **Admin template** `backend/app/templates/admin/models.html`:
   - Add a "Browse Marketplace" section between the Available Models grid and Installed Models table
   - Use htmx lazy loading: `<div hx-get="/admin/models/marketplace" hx-trigger="load" hx-swap="innerHTML">Loading marketplace…</div>`
   - Create marketplace partial template at `backend/app/templates/admin/_marketplace.html` that renders marketplace model cards:
     - Card grid using same `.available-model-card` CSS pattern from S01
     - Each card shows: name, version badge, description, size badge, tag pills
     - Install button: htmx POST to `/admin/models/marketplace-install` with hidden model_id input, `hx-target="#model-table"`, `hx-indicator` for loading state (R007)
     - "Already installed" badge if model_id matches an installed model (R003/R008)
   - Show error message when registry is unreachable: "Marketplace unavailable. Check your internet connection."

5. **CSS additions** in `frontend/static/css/style.css`:
   - Add marketplace-specific badge styles (size badge, tag pills) using theme tokens and `color-mix()` per project convention
   - Reuse the `.available-model-card` and `.available-models-grid` classes from S01 for consistency

6. **Verify** the template renders without Jinja2 errors and endpoints exist in the router

## Must-Haves

- [x] `MarketplaceRegistryService` created at startup and stored on `app.state.registry_service`
- [x] `/app/data/models/` directory ensured to exist at startup
- [x] `refresh_artifacts()` finds models in both `/app/models/` and `/app/data/models/`
- [x] `_load_entailment_defaults()` finds models in both directories
- [x] `IconService` scans both model directories
- [x] `GET /admin/models/marketplace` returns marketplace cards from registry
- [x] `POST /admin/models/marketplace-install` downloads, verifies, extracts, installs model
- [x] Install button shows loading indicator during operation (R007)
- [x] Already-installed models show badge instead of install button (R003/R008)
- [x] Registry failure shows graceful error message, does not crash (R006)
- [x] Template uses theme tokens, no hardcoded hex values

## Verification

- `cd backend && python -c "from app.admin.router import router; from app.services.marketplace import MarketplaceRegistryService; from app.models.paths import resolve_model_dir; print('imports OK')"` — imports succeed
- `cd backend && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('app/templates')); env.get_template('admin/models.html'); env.get_template('admin/_marketplace.html'); print('templates OK')"` — templates parse
- `rg 'resolve_model_dir' backend/app/services/models.py backend/app/admin/router.py` — confirms call sites updated
- `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/style.css | grep -v 'var(' | wc -l` — zero hardcoded hex values outside theme references
  - Estimate: 1h15m
  - Files: backend/app/main.py, backend/app/admin/router.py, backend/app/services/models.py, backend/app/services/icons.py, backend/app/templates/admin/models.html, backend/app/templates/admin/_marketplace.html, frontend/static/css/style.css
  - Verify: cd backend && python -c "from app.admin.router import router; from app.services.marketplace import MarketplaceRegistryService; from app.models.paths import resolve_model_dir; print('imports OK')" && python -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('app/templates')); env.get_template('admin/models.html'); env.get_template('admin/_marketplace.html'); print('templates OK')"
