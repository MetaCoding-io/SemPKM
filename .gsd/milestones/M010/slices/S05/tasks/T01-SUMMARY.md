---
id: T01
parent: S05
milestone: M010
provides:
  - parse_opml() pure function for OPML XML → feed dict list conversion
  - 21 parser unit tests covering all edge cases
key_files:
  - apps/rss-reader/services/opml_parser.py
  - backend/tests/test_opml_import.py
key_decisions: []
patterns_established:
  - Recursive tree walk with category_parts accumulator for nested OPML categories
observability_surfaces:
  - logging.warning on OPML parse errors with exception type and message
duration: 10m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T01: Create OPML parser pure function with comprehensive tests

**Added `parse_opml()` pure function that converts OPML XML bytes to feed dicts with nested category support, plus 21 passing unit tests.**

## What Happened

Created `apps/rss-reader/services/opml_parser.py` with a single public function `parse_opml(xml_content: bytes) -> list[dict]`. The function uses stdlib `xml.etree.ElementTree` to parse OPML XML and recursively walks `<outline>` elements — outlines with `xmlUrl` are feed entries, those without are category folders. Category nesting is tracked via a `category_parts` list accumulator, joined with `/` for multi-level paths (e.g. `"Tech/Blogs/Python"`). Title resolution follows `text` → `title` → `xmlUrl` fallback. All parse errors are caught and return `[]` with a logged warning.

Created `backend/tests/test_opml_import.py` with 21 test cases organized into 10 test classes covering: flat feeds, single-level categories, nested categories (2 and 3 levels), mixed outlines, title fallback (4 cases including empty strings), htmlUrl presence/absence/empty, empty body, missing body, invalid XML (3 error variants), and UTF-8 encoding.

## Verification

- 21/21 tests pass via `pytest tests/test_opml_import.py -v`
- Syntax check passes on `opml_parser.py`
- Invalid XML failure-path check returns `[]` with logged warning
- No SDK or framework imports in parser (only `logging` and `xml.etree.ElementTree`)
- S01/S02 regression check: 88/88 tests pass in `test_rss_feed_parser.py` and `test_feed_service.py`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` | 0 | ✅ pass | 0.03s |
| 2 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/opml_parser.py').read())"` | 0 | ✅ pass | <1s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` | 0 | ✅ pass (not yet modified by this task) | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v` | 0 | ✅ pass (88 tests) | 0.33s |
| 5 | Failure-path check: `parse_opml(b'<not xml')` returns `[]` | 0 | ✅ pass | <1s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v` | — | ⏳ pending (T03) | — |

## Diagnostics

- `parse_opml()` emits `logging.warning` on any parse failure — grep for "OPML parse error" in logs
- Function return value is the primary diagnostic: empty list means parse failure
- No secrets or PII involved; feed URLs logged as-is

## Deviations

- Slice plan verification command `cd backend && .venv/bin/python -c "from apps.rss_reader.services.opml_parser import parse_opml; ..."` uses dot-path import that fails because directory is `rss-reader` (hyphenated). Verified via `importlib.util.spec_from_file_location` instead, which matches the actual test pattern.
- Task plan verification `-k "test_parse"` filter matches 0 tests because test names don't contain "parse". All 21 tests pass without the filter, exceeding the ≥12 requirement.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/services/opml_parser.py` — new pure function module (75 lines), `parse_opml()` + `_walk_outlines()` helper
- `backend/tests/test_opml_import.py` — new test file with 21 parser unit tests across 10 test classes
