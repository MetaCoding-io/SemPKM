---
id: T03
parent: S05
milestone: M010
provides:
  - GET/POST /_fragments/settings routes for reading/writing app settings
  - settings.html template with number input and checkbox form
  - Manifest settings declarations (articlesPerPage, markReadOnOpen) with permissions.settings: true
  - Settings gear icon in feed sidebar header
  - Testable helper functions: get_settings_context(), save_settings(), validate_articles_per_page()
key_files:
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/settings.html
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - backend/tests/test_rss_settings.py
key_decisions:
  - Extracted settings logic into pure testable helpers (get_settings_context, save_settings, validate_articles_per_page) rather than testing HTTP layer
  - articlesPerPage clamped to [10, 200] range; non-integer input falls back to default "50"
  - Checkbox absence in form data (unchecked) maps to "false" string for markReadOnOpen
patterns_established:
  - Reuse existing sys.modules entry for rss_reader_app_mod to prevent cross-test module duplication
observability_surfaces:
  - GET /_fragments/settings returns current values in form field value attributes — inspectable without JS
  - POST /_fragments/settings returns <div class="rss-success">Settings saved</div> or <div class="rss-error"> with descriptive text
  - Settings errors logged via logger.warning("Settings ... error: ...")
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Add settings manifest declarations, route, template, and tests

**Added settings manifest declarations, GET/POST routes, settings template with gear icon, and 20 passing tests**

## What Happened

Added two app settings (`articlesPerPage` number, `markReadOnOpen` toggle) to the RSS Reader manifest with `permissions.settings: true`. Created testable helper functions (`get_settings_context`, `save_settings`, `validate_articles_per_page`) that separate business logic from route handling. Wired GET and POST `/_fragments/settings` routes that read/write via `ctx.settings` with fallback to manifest defaults. Created `settings.html` template matching the existing form styling conventions. Added a settings gear icon button to the feed sidebar header alongside existing subscribe and OPML import buttons. Wrote 20 tests covering manifest validation, settings context retrieval, value clamping, and save behavior. Also fixed a cross-test module duplication bug in `test_opml_import.py` where re-executing `app.py` under the same `sys.modules` key broke patch targets in `test_rss_feed_parser.py`.

## Verification

- 20 settings tests pass (4 manifest + 3 get_settings_context + 8 validate_articles_per_page + 5 save_settings)
- Manifest validates: 2 settings, permissions.settings=True
- app.py syntax OK
- All 140 tests pass across 4 test files with zero regressions

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v` | 0 | ✅ pass | 0.30s |
| 2 | `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('../apps/rss-reader/manifest.yaml')"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py tests/test_opml_import.py tests/test_rss_settings.py -v` | 0 | ✅ pass | 0.45s |

## Diagnostics

- **Settings round-trip:** GET `/_fragments/settings` returns form with `value` attributes inspectable via curl or browser automation. POST returns `<div class="rss-success">Settings saved</div>` on success.
- **Error paths:** Settings read/write failures return `<div class="rss-error">Failed to {load/save} settings: {exc}</div>`.
- **Manifest cross-validation:** `validate_settings_permission` model validator in `manifest.py` catches misconfigured manifests (settings declared without `permissions.settings: true`).
- **Logger:** Settings errors logged with `Settings read error` or `Settings save error` prefix.

## Deviations

- Fixed pre-existing cross-test module duplication bug in `test_opml_import.py` — the unconditional re-exec of `app.py` into `sys.modules["rss_reader_app_mod"]` was creating a second module object, breaking `patch()` targets in `test_rss_feed_parser.py`. Added `if "rss_reader_app_mod" in sys.modules` guard to both `test_opml_import.py` and `test_rss_settings.py`.
- Wrapped sidebar action buttons in a `<div class="rss-sidebar-actions">` container for better layout organization instead of placing gear icon as a raw sibling.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — added `permissions.settings: true` and 2 settings definitions
- `apps/rss-reader/app.py` — added settings helpers (get_settings_context, save_settings, validate_articles_per_page) and GET/POST /_fragments/settings routes
- `apps/rss-reader/frontend/templates/settings.html` — new settings form template with number input and checkbox
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — added settings gear icon button in header, wrapped actions in container div
- `backend/tests/test_rss_settings.py` — new test file with 20 tests
- `backend/tests/test_opml_import.py` — fixed module loading to reuse existing sys.modules entry
