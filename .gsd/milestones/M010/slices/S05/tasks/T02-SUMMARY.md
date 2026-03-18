---
id: T02
parent: S05
milestone: M010
provides:
  - POST /_fragments/import-opml route for OPML file upload → bulk subscribe
  - GET /_fragments/opml-import-dialog route serving upload form
  - process_opml_import() testable async function for OPML import logic
  - "Import OPML" button in feed sidebar (header + empty state)
  - 11 integration tests covering success, duplicates, errors, categories
key_files:
  - apps/rss-reader/app.py
  - apps/rss-reader/frontend/templates/opml-import.html
  - apps/rss-reader/frontend/templates/feed-sidebar.html
  - backend/tests/test_opml_import.py
key_decisions:
  - Extracted core logic into process_opml_import() async function for testability rather than testing HTTP layer directly
patterns_established:
  - process_opml_import() returns structured dict {created, duplicate, errors, feeds} — separates logic from route rendering
observability_surfaces:
  - POST import-opml returns HTML with data-created/data-duplicates/data-errors attributes on summary div
  - All error paths return <div class="rss-error"> with user-visible messages
  - HX-Trigger feedsChanged emitted on successful import
  - logger.warning on subscribe failures ("OPML import subscribe error") and tag patch failures ("Failed to patch tags")
duration: 15m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: Wire OPML import route + template into app with integration tests

**Added OPML import route, upload template, and sidebar button with 11 integration tests covering success/duplicate/error/category paths**

## What Happened

Wired T01's `parse_opml()` into the RSS Reader app with a complete file upload flow:

1. Added `parse_opml` import fallback in `app.py` using the same `try/except` pattern as `feed_service`.
2. Created `process_opml_import(ctx, xml_bytes)` — an async function that parses OPML, calls `subscribe()` sequentially per feed, patches `bpkm:tags` for categorized feeds, and returns structured counts `{created, duplicate, errors, feeds}`.
3. Added GET `/_fragments/opml-import-dialog` route rendering the upload form template.
4. Added POST `/_fragments/import-opml` route: reads multipart file, delegates to `process_opml_import()`, returns HTML summary with structured data attributes and `HX-Trigger: feedsChanged`.
5. Created `opml-import.html` template with `hx-encoding="multipart/form-data"` file input.
6. Added "Import OPML" button to `feed-sidebar.html` in both the feeds-present header and the empty-state block.
7. Added 11 integration tests to `test_opml_import.py` covering: 3 feeds all created, subscribe called per feed, some duplicates, all duplicates, empty OPML, invalid XML, category patching, no patch for uncategorized, no patch for duplicates, subscribe exception handling, tag patch failure tolerance.

## Verification

- `pytest tests/test_opml_import.py -v` — **32 passed** (21 parser + 11 integration)
- `ast.parse(open('apps/rss-reader/app.py').read())` — syntax OK
- `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` — **88 passed**, zero regressions
- Invalid XML diagnostic: `parse_opml(b'<not xml')` returns `[]` ✓

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` | 0 | ✅ pass (32 tests) | 0.29s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` | 0 | ✅ pass (88 tests) | 0.32s |
| 4 | Invalid XML returns `[]` (importlib path) | 0 | ✅ pass | <1s |

## Diagnostics

- **Import route summary:** POST `/_fragments/import-opml` returns `<div class="rss-success" data-created="N" data-duplicates="M" data-errors="K">` — inspectable via `browser_find` or curl.
- **Error divs:** All error paths (no file, empty file, invalid XML) return `<div class="rss-error">` with user-visible messages.
- **HX-Trigger:** Successful imports emit `HX-Trigger: feedsChanged` — observable via network logs.
- **Logger warnings:** Subscribe failures logged as `OPML import subscribe error for {url}`, tag patch failures as `Failed to patch tags for {url}`.

## Deviations

- Plan suggested ≥8 integration tests; delivered 11 to cover additional edge cases (tag patch failure tolerance, no-patch-for-duplicates-with-category).
- The `from apps.rss_reader.services.opml_parser import parse_opml` diagnostic command in the slice plan doesn't work because the app isn't installed as a Python package. The same check passes via `importlib.util.spec_from_file_location`. Not a real issue — just a slice plan diagnostic path typo.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/app.py` — added `parse_opml` import fallback, `process_opml_import()` helper, GET opml-import-dialog route, POST import-opml route
- `apps/rss-reader/frontend/templates/opml-import.html` — new file upload form template with htmx multipart encoding
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — added "Import OPML" button in header and empty-state blocks
- `backend/tests/test_opml_import.py` — expanded with 11 integration tests (32 total with T01's 21 parser tests)
