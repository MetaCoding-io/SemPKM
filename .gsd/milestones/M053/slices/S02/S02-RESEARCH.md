# S02 Research: Marketplace Registry + Install-from-Cloud

## Summary

This slice builds the entire download-verify-extract-install pipeline for cloud-hosted models. The core work is: (1) a `RegistryService` that fetches/caches a remote `registry.json`, (2) secure archive download with SHA-256 verification, (3) tarfile extraction with bomb/traversal protection, (4) wiring the extracted directory into the existing `ModelService.install()` pipeline, (5) a new admin endpoint + UI for marketplace browsing and install. The existing codebase provides strong foundations — `ModelService.install(Path)` is a clean boundary, `validate_outbound_url()` handles SSRF, and `validate_zip_contents()` provides the pattern for tarfile bomb protection.

## Requirements Owned

| ID | Description | Key Implementation Concern |
|----|-------------|---------------------------|
| R002 | Tarfile path traversal protection | Python 3.12 `tarfile.data_filter` handles this natively |
| R003 | Duplicate install prevented for marketplace | `ModelService.install()` already checks — verify it works on this path |
| R004 | SSRF guard on registry HTTP fetches | `validate_outbound_url()` before every httpx call |
| R005 | SHA-256 verification of downloaded archives | Compute hash of downloaded bytes, compare to registry manifest |
| R006 | App functions when registry unreachable | 5s timeout, graceful fallback to empty catalog, cached registry |
| R007 | Install progress visible in UI | htmx indicator pattern already used by S01's install button |
| R008 | Duplicate of R003 | Same requirement, different ID |

## Recommendation

Build in this order: (1) tarfile validator (security, testable in isolation), (2) RegistryService with fetch/cache/download, (3) admin endpoint + model directory resolution, (4) UI. The riskiest part is tarfile security — use Python 3.12's `data_filter` plus manual bomb checks. The registry service is straightforward httpx + caching. The UI extends the existing S01 card grid pattern.

## Implementation Landscape

### 1. RegistryService (new: `backend/app/services/registry.py`)

**Responsibility:** Fetch registry.json, cache it, download model archives, verify SHA-256, extract to tempdir.

```python
class RegistryService:
    def __init__(self, registry_url: str, models_data_dir: Path):
        self._registry_url = registry_url
        self._models_data_dir = models_data_dir  # /app/data/models
        self._cache: dict | None = None
        self._cache_time: float = 0
        self._cache_ttl: float = 3600  # 1 hour

    async def fetch_catalog(self) -> list[RegistryModel]:
        """Fetch registry.json, return model list. Cached for TTL."""

    async def download_and_extract(self, model_id: str) -> Path:
        """Download archive, verify SHA-256, extract, return path to extracted dir."""
```

**Key decisions:**
- Uses `httpx.AsyncClient` (already in deps, v0.28.1)
- `validate_outbound_url()` called on both registry URL and archive URL before any fetch
- Registry URL from `Settings.marketplace_registry_url` (new config field, default: empty string = disabled)
- Download to `tempfile.NamedTemporaryFile`, verify hash, then extract
- Extract to `/app/data/models/{modelId}/` (writable persistent volume)
- On success returns `Path` to extracted directory — caller passes to `ModelService.install()`
- On failure (network, hash mismatch, bomb, traversal) raises descriptive `ValueError`

### 2. Tarfile Validator (new: `backend/app/security/tar_validator.py`)

Adapts the `validate_zip_contents()` pattern for tarfile. Checks:
- Total uncompressed size (2GB max)
- File count (50,000 max)
- Compression ratio per member (100:1 max)
- Path traversal: rejects absolute paths, `..` components, symlinks
- Python 3.12 `tarfile.data_filter` for safe extraction (PEP 706)

```python
def validate_tar_contents(tar_path: Path, *, max_uncompressed_mb=2048, max_files=50000, max_ratio=100) -> None:
    """Validate a tar.gz archive before extraction. Raises ValueError on failure."""
```

### 3. Model Directory Resolution

Multiple files hardcode `/app/models/{model_id}`. The marketplace downloads go to `/app/data/models/`. A helper function resolves the model directory from either location:

```python
def resolve_model_dir(model_id: str) -> Path | None:
    """Find model directory in bundled or downloaded locations. Returns None if not found."""
    for base in [Path("/app/models"), Path("/app/data/models")]:
        candidate = base / model_id
        if (candidate / "manifest.yaml").exists():
            return candidate
    return None
```

**Files needing this change:**
- `backend/app/services/models.py` — `refresh_artifacts()` line 616
- `backend/app/admin/router.py` — `_load_entailment_defaults()` line 1074, `IconService` calls (lines 329, 416, 748), `scan_available_models` calls (lines 298, 536, 602, 694, 723)
- `backend/app/inference/service.py` — line 658
- `backend/app/sparql/router.py` — `_MODELS_DIR` line 66
- `backend/app/api/router.py` — line 212
- `backend/app/browser/_helpers.py` — `_MODELS_DIR` line 46

**Recommended approach:** Add `resolve_model_dir()` to a shared utility (e.g., `app.models.paths`). Update callers incrementally. For S02, the minimum viable change is just `refresh_artifacts()` and `_load_entailment_defaults()` — the rest can use a follow-up. But `IconService` lookups matter because new marketplace models need icons too.

**Practical scoping for S02:** The critical path is just ensuring a marketplace-installed model works end-to-end. This means `refresh_artifacts()`, `_load_entailment_defaults()`, and `IconService` must search both directories. The SPARQL router's `_MODELS_DIR` and browser helpers are only used for the auto-discover UI (S01 scope) and can stay hardcoded for now — they scan for *available* bundled models, not *installed* ones.

### 4. Settings Addition

Add to `backend/app/config.py`:

```python
# Marketplace
marketplace_registry_url: str = ""  # Empty = marketplace disabled
marketplace_models_dir: str = "/app/data/models"
```

Empty `marketplace_registry_url` means the Browse Marketplace section doesn't appear. This is the offline-safe default.

### 5. Admin Endpoint

New endpoint in `backend/app/admin/router.py`:

```python
@router.post("/models/marketplace-install")
async def admin_models_marketplace_install(
    request: Request,
    user: User = Depends(require_role("owner")),
    model_service: ModelService = Depends(get_model_service),
    model_id: str = Form(...),
):
    """Download and install a model from the marketplace registry."""
```

Flow:
1. Get RegistryService from `request.app.state.registry_service`
2. Call `registry_service.download_and_extract(model_id)` → returns `Path`
3. Call `model_service.install(extracted_path, user_id=user.id)` → returns `InstallResult`
4. Clean up tempdir on success or failure
5. Return updated model table partial (same pattern as existing install endpoint)

Also add `GET /admin/models/marketplace` to fetch and render the catalog:

```python
@router.get("/models/marketplace")
async def admin_models_marketplace(request: Request, ...):
    """Fetch registry catalog and return marketplace card grid partial."""
```

### 6. Admin UI (template changes to `models.html`)

Add a "Browse Marketplace" section between the Available Models grid and the Installed Models table. Uses the same card grid pattern from S01. Each marketplace card shows:
- Model name, version, description
- Size badge, tag pills
- Install button (htmx POST to `/admin/models/marketplace-install`)
- "Already installed" badge if model_id matches an installed model

The marketplace section loads lazily via htmx `hx-get="/admin/models/marketplace"` `hx-trigger="load"` to avoid blocking the page when registry is slow/down.

### 7. Startup Wiring

In `backend/app/main.py` lifespan:
- Create `RegistryService(settings.marketplace_registry_url, Path(settings.marketplace_models_dir))`
- Store on `app.state.registry_service`
- Ensure `/app/data/models/` directory exists (`os.makedirs(..., exist_ok=True)`)

## Key Files to Create

| File | Purpose |
|------|---------|
| `backend/app/security/tar_validator.py` | Tarfile bomb/traversal protection |
| `backend/app/services/registry.py` | Registry fetch, cache, download, extract |
| `backend/app/models/paths.py` | `resolve_model_dir()` utility |

## Key Files to Modify

| File | Change |
|------|--------|
| `backend/app/config.py` | Add `marketplace_registry_url`, `marketplace_models_dir` |
| `backend/app/main.py` | Create RegistryService at startup, ensure data models dir |
| `backend/app/admin/router.py` | Add marketplace-install + marketplace catalog endpoints, update scan paths |
| `backend/app/templates/admin/models.html` | Add Browse Marketplace section |
| `backend/app/services/models.py` | `refresh_artifacts()` use `resolve_model_dir()` |
| `frontend/static/css/style.css` | Marketplace card styles (minor, extends S01 grid) |

## Verification Strategy

1. **Unit test `tar_validator.py`:** Create malicious tar archives (path traversal, bomb, symlinks) → verify rejection. Create valid archive → verify acceptance.
2. **Unit test `registry.py`:** Mock httpx responses for registry.json fetch, archive download. Verify SHA-256 check, cache TTL, SSRF guard integration, timeout handling.
3. **Integration test:** Create a test registry.json + test .tar.gz archive locally. Run full download→verify→extract→install pipeline. Verify model appears in installed list.
4. **Offline test:** Set empty registry URL → verify marketplace section doesn't appear or shows graceful error. Set unreachable URL → verify 5s timeout and graceful fallback.
5. **Template test:** Parse Jinja2 template without error. Verify marketplace section loads lazily.

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Tarfile path traversal | Python 3.12 `data_filter` + manual `..` and absolute path checks |
| Tarfile bomb | Size/count/ratio checks adapted from zip_validator.py |
| Registry unreachable | 5s httpx timeout, cache with TTL, graceful empty fallback |
| Download corruption | SHA-256 hash verification before extraction |
| SSRF via crafted registry URL | `validate_outbound_url()` on every HTTP call |
| Concurrent downloads | Download to unique tempdir, atomic move to final location |
| Partial download / crash | Tempdir cleanup in finally block; don't install until extraction complete |

## Patterns to Follow

| Pattern | Source | How Used |
|---------|--------|----------|
| `validate_zip_contents()` | `app.security.zip_validator` | Adapt for tar_validator.py |
| `validate_outbound_url()` | `app.security.ssrf` | Guard all registry HTTP calls |
| `scan_available_models()` | `app.admin.router` | Card grid rendering pattern |
| htmx `hx-indicator` | `admin/models.html` | Install progress spinner |
| `httpx.AsyncClient` | `app.triplestore.client` | HTTP client for registry |
| `ModelService.install(Path)` | `app.services.models` | Called after download+extract |

## Seams for Task Decomposition

The natural task boundaries are:

1. **Tar validator** — `tar_validator.py` with unit tests. Zero dependencies on other new code. Can be built and verified independently.
2. **Registry service** — `registry.py` + config additions + `paths.py`. Depends on tar_validator. Unit-testable with mocked httpx.
3. **Admin endpoints + UI** — endpoint wiring, template changes, startup integration. Depends on registry service. Verifiable by running the app.
4. **Model directory resolution** — update `refresh_artifacts()`, `_load_entailment_defaults()`, `IconService` to search both directories. Can be built alongside or after the endpoints.

Tasks 1-2 are the core technical risk. Task 3 is integration wiring. Task 4 is necessary for marketplace-installed models to fully work.
