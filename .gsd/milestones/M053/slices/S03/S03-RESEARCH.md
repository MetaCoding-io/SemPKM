# S03 Research: Version Checking + Update Notifications

## Summary

Straightforward slice. All infrastructure exists — the registry catalog (with version fields) is already fetched and cached by `MarketplaceRegistryService`, installed models already store version strings in the triplestore (`sempkm:version`), and `packaging.version.Version` is already a dependency for semver comparison. The work is: compare versions, surface badges in the UI, add an update flow that uninstalls then reinstalls from the registry.

## Recommendation

Light implementation across 2 tasks: (1) backend version comparison logic + update endpoint, (2) UI badges + update button wiring. No new libraries, no new services, no architectural decisions needed.

## Implementation Landscape

### Data Available for Version Comparison

**Installed models** — `InstalledModel` dataclass from `registry.py:list_models()`:
- `model_id: str` (e.g. "basic-pkm")
- `version: str` (e.g. "2.2.0")
- Queried from `GRAPH <urn:sempkm:models>` via SPARQL

**Registry catalog** — `list[dict]` from `MarketplaceRegistryService.fetch_catalog()`:
- `entry["id"]` — model ID
- `entry["version"]` — latest version string
- Cached in-memory with 1-hour TTL

**Version comparison** — `packaging.version.Version` is already in `pyproject.toml` (`packaging~=25.0`). Handles semver comparison correctly: `Version("2.2.0") > Version("1.0.0")`.

### Where to Add Version Comparison

**Option: Add a method to `MarketplaceRegistryService`**

A `check_updates(installed_models)` method that:
1. Calls `fetch_catalog()` (uses cache if warm)
2. For each installed model, finds the matching catalog entry by `model_id`
3. Compares versions using `packaging.version.Version`
4. Returns a dict mapping `model_id → {installed_version, latest_version, has_update}`

This keeps the comparison logic in the service layer, testable in isolation.

### Update Flow

The update is conceptually: uninstall old version → download and install new version. The existing `ModelService` already has `remove()` and the marketplace has `download_and_install()`. The update endpoint chains them:

1. `model_service.remove(model_id)` — clears triplestore graphs + registry entry
2. `registry_service.download_and_install(model_id, model_service, user_id)` — downloads, verifies, extracts, installs
3. `_cleanup_inference_on_uninstall(...)` — clears inferred graph + settings (already exists)

**Risk:** If download fails after uninstall, the model is gone. Mitigation: download and verify the archive FIRST, then uninstall + install. The `download_and_install()` method already downloads to a tempdir and verifies SHA-256 before calling `model_service.install()`. The update endpoint should restructure the flow as: download → verify → uninstall old → install new.

### UI Changes

**Installed Models table (`models.html`)** — Add a version status column or inline badges:
- "Up to date" (green badge) — installed version equals or exceeds registry version
- "Update available: v2.3.0" (amber badge + update button) — registry has newer version
- No badge — model not in registry (bundled-only model)

**Marketplace cards (`_marketplace.html`)** — Already shows "✓ Installed" badge for installed models. Can be enhanced to show "Update available" when the installed version is behind.

**Update button** — htmx POST to `/admin/models/{model_id}/update` with `hx-target="#model-table"` and `hx-indicator` for loading spinner. Follows the exact same pattern as the install and remove buttons.

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/services/marketplace.py` | Add `check_updates()` method |
| `backend/app/admin/router.py` | Add update status to `admin_models()` context, add POST `/models/{model_id}/update` endpoint |
| `backend/app/templates/admin/models.html` | Add version badges and update button to installed models table |
| `backend/app/templates/admin/_marketplace.html` | Enhance installed badge to show update available |
| `frontend/static/css/style.css` | Add `.version-badge--uptodate` and `.version-badge--update` CSS |
| `backend/tests/test_marketplace_service.py` | Add tests for `check_updates()` |

### Constraints

- **`packaging.version.Version`** — already available, no new dependency
- **Version format** — manifests enforce `^\d+\.\d+\.\d+$` (strict semver), so `Version()` parsing will always succeed for valid installed models. Registry entries should follow the same format — add a try/except for malformed registry versions.
- **Marketplace disabled** — when `marketplace_registry_url` is empty, `check_updates()` returns empty dict. No update badges shown. The UI gracefully degrades.
- **Network failure** — `fetch_catalog()` already returns `[]` on timeout/error. `check_updates()` inherits this behavior — no updates shown when registry is unreachable.
- **CSS pattern** — per CLAUDE.md rule, use `color-mix(in srgb, var(--_color-*) N%, transparent)` with theme tokens, zero hardcoded hex. Existing marketplace CSS follows this pattern already.

### Safe Update Ordering

Critical: don't uninstall before confirming the new archive is valid.

```
POST /admin/models/{model_id}/update
  1. Fetch catalog, find entry for model_id
  2. Download archive to tempdir
  3. Verify SHA-256
  4. Validate archive (tar safety checks)
  5. Extract to tempdir, confirm manifest.yaml exists
  --- at this point, the new version is fully validated on disk ---
  6. model_service.remove(model_id) — uninstall old
  7. _cleanup_inference_on_uninstall(...)
  8. model_service.install(extracted_dir) — install new
  9. Copy to /app/data/models/{model_id}/ — persist
  10. Clean up tempdir
```

This is essentially the same as `download_and_install()` but with steps 6-7 inserted before step 8. Rather than duplicating, the update endpoint can call a modified version or sequence the existing methods.

### Existing Test Patterns

`test_marketplace_service.py` uses:
- `_mock_response()` for httpx responses
- `_sample_model_entry()` for catalog entries
- Direct service construction with `tmp_path` fixtures
- `patch("app.services.marketplace.validate_outbound_url")` for SSRF bypass in tests
- `AsyncMock` for `model_service.install`

The `check_updates()` tests follow the same pattern — mock the catalog, provide installed models, assert the comparison results.
