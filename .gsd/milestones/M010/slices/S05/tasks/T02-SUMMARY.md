---
id: T02
parent: S05
milestone: M010
provides:
  - POST /_fragments/import-opml route accepting multipart OPML upload
  - GET /_fragments/opml-import-dialog route rendering file upload form
  - process_opml_import(ctx, xml_bytes) testable async helper for import logic
  - "Import OPML" button in feed sidebar (both feeds-present and empty state)
  - opml-import.html htmx template with file input and result target
  - 10 integration tests covering success, duplicates, categories, and error paths
key_files:
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/opml-import.html
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - backend/tests/test_opml_import.py
key_decisions:
  - Extracted core import logic into process_opml_import() async helper for testability — route handler is a thin wrapper
  - Category patching uses object.patch with bpkm:tags only on "created" subscriptions (not duplicates)
  - Subscribe calls are sequential (not gather) to avoid overwhelming SDK
patterns_established:
  - Test pattern: monkey-patch _app_mod.subscribe with AsyncMock side_effect list, restore in finally block
  - Route returns structured data-* attributes on summary div for programmatic inspection
observability_surfaces:
  - POST /_fragments/import-opml returns <div class="rss-success" data-created="N" data-duplicates="M" data-errors="K">
  - Error paths return <div class="rss-error"> with descriptive message
  - HX-Trigger: feedsChanged header emitted on successful import
  - logger.warning for subscribe failures and tag-patch failures in process_opml_import
duration: ~20m
verification_result: passed
blocker_discovered: false
---

# T02: Wire OPML import route + template into app with integration tests

**Wired OPML parser into app with file upload route, htmx template, sidebar button, and 10 integration tests — delivers RSS-05 (OPML import).**

## What Happened

1. Added `try/except ImportError` fallback import for `opml_parser.parse_opml` in app.py, following the existing `feed_service` pattern.

2. Created `process_opml_import(ctx, xml_bytes)` — a testable async helper that calls `parse_opml()`, iterates feeds sequentially calling `subscribe()`, patches `bpkm:tags` on created subscriptions with categories, and returns structured counts `{created, duplicate, errors, feeds}`.

3. Created GET `/_fragments/opml-import-dialog` route rendering the upload form template.

4. Created POST `/_fragments/import-opml` route that reads multipart file upload, delegates to `process_opml_import()`, and returns HTML summary with CSS status classes and `data-*` attributes. Emits `HX-Trigger: feedsChanged` on success. All error paths (no file, empty file, invalid XML, no feeds found) return `<div class="rss-error">` messages.

5. Created `opml-import.html` template with `hx-encoding="multipart/form-data"`, file input accepting `.opml,.xml`, and result target div.

6. Added "Import OPML" button with lucide `upload` icon to feed-sidebar.html in both the feeds-present block and the empty-state block.

7. Added 10 integration tests to `test_opml_import.py` (27 total: 17 parser + 10 integration), covering: 3 feeds all created, mixed duplicates, all duplicates, category tag patching, no-category skip, duplicate-with-category no-patch, empty OPML, invalid XML, subscribe exception resilience, all-failures.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` → **27 passed** (17 parser + 10 integration) ✅
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` → syntax OK ✅
- `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` → **77 passed** (zero regressions) ✅
- Invalid XML check: `parse_opml(b'<not xml')` → `[]` ✅

### Slice-level verification (partial — T02 is intermediate task):
- ✅ `test_opml_import.py` — 27 tests pass (≥20 required)
- ⬜ `test_rss_settings.py` — not yet created (T03)
- ✅ `opml_parser.py` syntax OK
- ✅ `app.py` syntax OK
- ✅ Feed parser + feed service regressions — 77 passed
- ✅ Invalid XML failure-path check

## Diagnostics

- **Import results:** POST `/_fragments/import-opml` returns `<div class="rss-success" data-created="N" data-duplicates="M" data-errors="K">` — inspect via browser automation or curl.
- **Error visibility:** All error paths return `<div class="rss-error">` with descriptive text.
- **Logger:** `process_opml_import()` logs `OPML import subscribe error for {url}` and `Failed to patch tags for {iri}` via `logger.warning`.
- **Test command:** `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v`

## Deviations

- Plan suggested 8+ integration tests; delivered 10 for better coverage (added all-duplicates test, duplicate-with-category-no-patch test, all-failures test).
- Plan suggested extracting logic into a separate testable function as "alternative approach (simpler)" — adopted this approach with `process_opml_import()` as it provides clean test surface without needing to mock Starlette Request objects.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/app.py` — added opml_parser import fallback, `process_opml_import()` helper, GET opml-import-dialog route, POST import-opml route
- `apps/rss-reader/frontend/templates/opml-import.html` — new file upload form template with htmx multipart encoding
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — added "Import OPML" button in both feeds-present and empty-state blocks
- `backend/tests/test_opml_import.py` — expanded with imports for app module, 10 integration test cases in 4 test classes
- `.gsd/milestones/M010/slices/S05/tasks/T02-PLAN.md` — added Observability Impact section (pre-flight fix)
