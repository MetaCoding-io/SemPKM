---
estimated_steps: 5
estimated_files: 3
---

# T01: AppManifestSchema Pydantic model + validation tests

**Slice:** S01 — Manifest, DB Schema & Subprocess Lifecycle
**Milestone:** M009

## Description

Implement the full `AppManifestSchema` Pydantic model from the design document §14. This is the app developer-facing contract — it validates `manifest.yaml` files and produces clear error messages on invalid input. Every downstream slice depends on this.

## Steps

1. Create `backend/app/apps/__init__.py` as empty package init.
2. Create `backend/app/apps/manifest.py` with the full Pydantic schema hierarchy from design §14. The design doc provides the exact code — implement it faithfully with these nested models:
   - `AppAuthor` (name, optional url)
   - `AppModelDependency` (id with pattern, version validated via `packaging.specifiers.SpecifierSet`, optional bool)
   - `AppDependencies` (models list, platform version range)
   - `AppPermissionsSparql` (read bool)
   - `AppPermissions` (commands list, sparql, network list, backgroundTasks bool, settings bool)
   - `AppBackend` (entrypoint, requirements path)
   - `AppTaskRetryPolicy` (maxRetries 0-10, backoffMultiplier 1-10, maxBackoff)
   - `AppTask` (id with pattern, description, interval with shorthand/ISO 8601 validator, configurable bool, retryPolicy)
   - `AppFrontend` (staticDir, css list, js list)
   - `AppPage` (id, path, label, icon, nav, fragment)
   - `AppRightPaneContribution`, `AppViewContribution`, `AppCommandPaletteEntry`, `AppObjectRendererModes`, `AppObjectRenderer`
   - `AppContributions` (rightPane, views, commandPalette)
   - `AppUI` (pages, contributions, objectRenderers)
   - `AppSettingDef` (key with pattern, label, description, inputType, options, default)
   - `AppManifestSchema` root model with cross-field validators: tasks↔backgroundTasks, settings↔settings permission
   - `parse_app_manifest(manifest_path: str) → AppManifestSchema` function
3. Add `packaging~=25.0` and `PyJWT~=2.10` to `backend/pyproject.toml` dependencies list (alphabetical order). Both are needed by S01 (packaging for version range validation, PyJWT for future token work but added now per roadmap boundary).
4. Write `backend/tests/test_app_manifest.py` with comprehensive tests:
   - Valid minimal manifest (only required fields)
   - Valid full manifest (all fields including RSS Reader example structure from design §13)
   - `appId` pattern validation (rejects uppercase, spaces, starting with digit)
   - `version` must be strict semver X.Y.Z
   - `dependencies.models[].version` validates via SpecifierSet (rejects garbage)
   - `dependencies.platform` validates via SpecifierSet
   - Interval validation: accepts "30s", "5m", "1h", "6h", "1d", "PT5M", "PT1H"; rejects "10s" (<30s floor), "48h" (>24h ceiling), "garbage"
   - Cross-field: tasks declared without backgroundTasks=true raises
   - Cross-field: settings declared without settings=true raises
   - Command palette: dialog without fragment raises, post without endpoint raises, navigate without path raises
   - Object renderer: at least one mode (read or edit) required
   - Settings: select inputType without options raises
   - `parse_app_manifest` with real YAML file (tmpdir fixture)
   - `parse_app_manifest` with missing file raises ValueError
5. Run tests and fix any issues.

## Must-Haves

- [ ] All 17+ nested Pydantic models from design §14 implemented
- [ ] Field validators: appId pattern, semver, interval shorthand+ISO 8601, version ranges via `packaging.specifiers`
- [ ] Cross-field validators: tasks↔backgroundTasks, settings↔permissions.settings, command palette action targets
- [ ] `parse_app_manifest()` loads YAML and returns validated schema
- [ ] Comprehensive unit tests covering all constraint boundaries
- [ ] `PyJWT~=2.10` and `packaging~=25.0` in pyproject.toml

## Verification

- `cd backend && python -m pytest tests/test_app_manifest.py -v` — all tests pass
- `cd backend && python -c "from app.apps.manifest import AppManifestSchema, parse_app_manifest; print('OK')"` — importable

## Inputs

- `.gsd/design/APP-PLATFORM-DESIGN.md` §14 (Pydantic Schema) — provides exact class definitions
- `.gsd/design/APP-PLATFORM-DESIGN.md` §3 (Complete field reference) — field constraints table
- `backend/app/models/manifest.py` — existing ManifestSchema pattern to follow for consistency

## Expected Output

- `backend/app/apps/__init__.py` — empty package init
- `backend/app/apps/manifest.py` — full AppManifestSchema with all nested models and validators
- `backend/tests/test_app_manifest.py` — 25+ tests covering all validation paths
- `backend/pyproject.toml` — updated with `packaging~=25.0` and `PyJWT~=2.10`

## Observability Impact

This task is a pure validation schema — no runtime processes, no persistent state. Observability surfaces:

- **Validation errors:** Pydantic `ValidationError` with structured error list (field path, type, message) — any code calling `parse_app_manifest()` or `AppManifestSchema(**data)` gets machine-parseable error details.
- **Inspection:** `parse_app_manifest(path)` returns a fully typed object; all fields accessible for downstream status/diagnostic endpoints.
- **No logs/metrics:** Schema validation is synchronous and stateless; no logging added. Callers (install flow, admin UI) will handle logging context.

