---
id: T01
parent: S01
milestone: M009
provides:
  - AppManifestSchema Pydantic model with all nested models and validators
  - parse_app_manifest() YAML loader
  - packaging + PyJWT dependencies in pyproject.toml
key_files:
  - backend/app/apps/manifest.py
  - backend/tests/test_app_manifest.py
  - backend/app/apps/__init__.py
  - backend/pyproject.toml
key_decisions:
  - Implemented schema exactly as specified in design §14 — no deviations from the Pydantic code provided
patterns_established:
  - App manifest validation follows same conventions as Mental Model ManifestSchema (camelCase fields, regex patterns, model_validator for cross-field checks)
  - Interval shorthand validator: 30s floor, 24h ceiling, plus ISO 8601 PT-format passthrough
observability_surfaces:
  - Pydantic ValidationError with structured error list (field path, type, message) on invalid manifests
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: AppManifestSchema Pydantic model + validation tests

**Implemented full AppManifestSchema with 17 nested Pydantic models, field/cross-field validators, and 61 passing tests covering all constraint boundaries.**

## What Happened

Created the `backend/app/apps/` package and implemented the complete manifest validation schema from design §14. The schema includes all 17+ nested models (AppAuthor, AppModelDependency, AppDependencies, AppPermissionsSparql, AppPermissions, AppBackend, AppTaskRetryPolicy, AppTask, AppFrontend, AppPage, AppRightPaneContribution, AppViewContribution, AppCommandPaletteEntry, AppObjectRendererModes, AppObjectRenderer, AppContributions, AppUI, AppSettingDef, AppManifestSchema). Field validators cover appId pattern, semver version, interval shorthand with 30s-24h bounds plus ISO 8601, version range validation via `packaging.specifiers.SpecifierSet`, and setting key patterns. Cross-field validators enforce tasks↔backgroundTasks permission and settings↔settings permission consistency, plus command palette action-target requirements (dialog→fragment, post→endpoint, navigate→path).

Added `packaging~=25.0` and `PyJWT~=2.10` to `backend/pyproject.toml` and ran `uv sync` to update the lockfile.

Wrote 61 tests organized into 10 test classes covering valid manifests (minimal + full RSS Reader example), appId rejection patterns, semver enforcement, dependency version ranges, interval boundary testing, cross-field validators, command palette action validation, object renderer mode requirements, settings validation, parse_app_manifest with real YAML files, and edge cases (retry policy bounds, priority bounds, length limits).

## Verification

- `uv run python -m pytest tests/test_app_manifest.py -v` — **61 passed** in 0.18s
- `uv run python -c "from app.apps.manifest import AppManifestSchema, parse_app_manifest; print('OK')"` — **OK**

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `uv run python -m pytest tests/test_app_manifest.py -v` | 0 | ✅ pass | 0.18s |
| 2 | `uv run python -c "from app.apps.manifest import AppManifestSchema, parse_app_manifest; print('OK')"` | 0 | ✅ pass | <1s |
| 3 | `uv run python -c "from app.apps.models import AppInstance..."` | 1 | ⏳ expected (T02 scope) | <1s |
| 4 | `python -m pytest tests/test_app_manager.py -v` | — | ⏳ expected (T03 scope) | — |
| 5 | `python -m pytest tests/test_app_lifecycle_contract.py -v` | — | ⏳ expected (T04 scope) | — |
| 6 | `uv run python -c "from app.apps.manager import AppManager..."` | — | ⏳ expected (T03 scope) | — |

## Diagnostics

This task is a pure validation schema — no runtime processes or persistent state. Validation errors surface as Pydantic `ValidationError` with structured error lists containing field path, error type, and human-readable messages. Any caller of `parse_app_manifest()` or `AppManifestSchema(**data)` gets machine-parseable diagnostics.

## Deviations

None. Schema implemented exactly as specified in design §14.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/__init__.py` — new empty package init for apps module
- `backend/app/apps/manifest.py` — full AppManifestSchema with 17+ nested Pydantic models and validators
- `backend/tests/test_app_manifest.py` — 61 tests covering all validation paths and constraint boundaries
- `backend/pyproject.toml` — added `packaging~=25.0` and `PyJWT~=2.10` dependencies
