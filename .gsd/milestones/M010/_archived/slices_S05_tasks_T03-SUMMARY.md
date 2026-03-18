---
id: T03
parent: S05
milestone: M010
provides:
  - GET/POST /_fragments/settings routes for reading and saving app settings
  - Settings manifest declarations (articlesPerPage, markReadOnOpen) with validation
  - Testable helper functions get_settings_context() and save_settings() for settings logic
  - Gear icon in feed sidebar header to access settings page
key_files:
  - apps/rss-reader/manifest.yaml
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/settings.html
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - backend/tests/test_rss_settings.py
key_decisions:
  - Extracted settings logic into get_settings_context() and save_settings() pure async helpers for direct unit testing without Starlette request mocking
  - articlesPerPage validation uses clamp-to-range (10-200) rather than error rejection — always saves a valid value
patterns_established:
  - Settings helper pattern: extract async logic into helpers accepting ctx + form_data, test via mock ctx.settings with AsyncMock get/set
  - SETTINGS_DEFAULTS dict at module level for default values matching manifest declarations
observability_surfaces:
  - GET /_fragments/settings renders form with current values in input value attributes — inspectable without JS
  - POST /_fragments/settings returns <div class="rss-success">Settings saved</div> or <div class="rss-error"> with descriptive text
  - Settings route errors logged via logger.warning("Settings GET/POST error: ...")
duration: 8 minutes
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Add settings manifest declarations, route, template, and tests

**Added 2 app settings (articlesPerPage, markReadOnOpen) with manifest declarations, GET/POST routes, settings form template, sidebar gear icon, and 14 passing tests.**

## What Happened

1. Added `permissions.settings: true` and a top-level `settings:` array with 2 entries (articlesPerPage number/default "50", markReadOnOpen toggle/default "true") to manifest.yaml. Validated via `parse_app_manifest()` — the `validate_settings_permission` cross-validator confirms consistency.

2. Created GET `/_fragments/settings` route that reads current values via `ctx.settings.get()`, falls back to SETTINGS_DEFAULTS when None, and renders settings.html with template context.

3. Created POST `/_fragments/settings` route that validates/clamps articlesPerPage to 10-200 range, handles checkbox absent = "false" semantics, saves via `ctx.settings.set()`, and returns success/error HTML fragment.

4. Extracted core logic into `get_settings_context(ctx)` and `save_settings(ctx, form_data)` helpers for clean testability — routes are thin wrappers.

5. Created settings.html template with number input, checkbox, and htmx POST form matching the subscribe-dialog.html styling pattern.

6. Updated feed-sidebar.html header to a flex row with the "Feeds" title and a gear icon button that loads settings into the reading pane.

7. Created test_rss_settings.py with 14 tests across 3 test classes: manifest validation (3), get_settings_context (3), and save_settings (8).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v` — **14 passed** (exceeds ≥8 requirement)
- `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('../apps/rss-reader/manifest.yaml')"` — no error
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py tests/test_opml_import.py -v` — **104 passed**, zero regressions

### Slice-level verification status (T03 is final task):
- ✅ `test_rss_settings.py` — 14 tests pass (≥8 required)
- ✅ `test_opml_import.py` — 27 tests pass (≥20 required, includes parser + route tests)
- ✅ `app.py` syntax OK
- ✅ `opml_parser.py` syntax OK (not modified this task)
- ✅ `test_rss_feed_parser.py` + `test_feed_service.py` — 77 tests pass, zero regressions

## Diagnostics

- **Settings round-trip:** GET `/_fragments/settings` returns current values in form field `value` attributes. POST returns `<div class="rss-success">Settings saved</div>` on success, `<div class="rss-error">` with descriptive text on failure.
- **Settings persistence:** Values stored via `ctx.settings.set(key, value)` with auto-prefix `settings:` in state graph. Read back via `ctx.settings.get(key)` — returns None when unset, triggering default fallback.
- **Logger:** Settings route errors logged via `logger.warning("Settings GET error: ...")` and `logger.warning("Settings POST error: ...")`.
- **Manifest validation:** `parse_app_manifest()` raises ValidationError if `permissions.settings` is false but settings are declared.
- **Test command:** `cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v`

## Deviations

- Plan suggested "Alternative approach (simpler): Extract settings logic into testable helper functions" — adopted this approach with `get_settings_context()` and `save_settings()`, testing helpers directly rather than mocking full Starlette requests. This yielded 14 tests (vs plan's ≥8 minimum) with cleaner test code.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/manifest.yaml` — added `permissions.settings: true` and 2 settings definitions
- `apps/rss-reader/app.py` — added GET/POST settings routes, `get_settings_context()`, `save_settings()`, `SETTINGS_DEFAULTS`
- `apps/rss-reader/frontend/templates/settings.html` — new settings form template with number input and checkbox
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — added gear icon button in sidebar header
- `backend/tests/test_rss_settings.py` — 14 tests across manifest, get_settings_context, and save_settings
- `.gsd/milestones/M010/slices/S05/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
