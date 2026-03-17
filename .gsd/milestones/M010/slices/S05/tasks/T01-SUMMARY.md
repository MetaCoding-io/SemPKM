---
id: T01
parent: S05
milestone: M010
provides:
  - parse_opml() pure function for OPML XML → feed dict list conversion
  - 17 comprehensive parser tests covering all edge cases
key_files:
  - apps/rss-reader/services/opml_parser.py
  - backend/tests/test_opml_import.py
key_decisions:
  - Used logging.warning for parse errors rather than silent failure — enables log-based diagnosis
patterns_established:
  - Recursive _walk_outlines() with category accumulation via slash-delimited string passing
observability_surfaces:
  - logging.warning on parse errors with exception type and message
duration: 10m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Create OPML parser pure function with comprehensive tests

**Built `parse_opml(bytes) → list[dict]` pure function with 17 passing tests covering flat/nested categories, title fallbacks, encoding, and all error paths.**

## What Happened

Created `opml_parser.py` with a single public function `parse_opml()` that uses stdlib `xml.etree.ElementTree` to parse OPML XML bytes. The parser recursively walks `<outline>` elements: nodes with `xmlUrl` become feed entries, nodes without become category folders whose `text` attribute is accumulated into `/`-delimited category strings for child feeds. Title resolution follows `text > title attr > xmlUrl` fallback chain. All parse errors are caught and return `[]` with a `logging.warning`.

Wrote 17 test cases organized into 5 test classes: flat feeds, category handling (1/2/3 levels + mixed), title fallback logic, htmlUrl presence/absence, and edge cases (empty body, invalid XML, no body element, empty bytes, UTF-8 encoding, non-bytes input).

## Verification

- `pytest tests/test_opml_import.py -v` — 17/17 passed (≥12 required) ✓
- `ast.parse()` on opml_parser.py — syntax OK ✓
- Only stdlib imports: `logging`, `xml.etree.ElementTree` — no SDK deps ✓
- S01/S02 regression: `test_rss_feed_parser.py` + `test_feed_service.py` — 77 passed ✓

## Diagnostics

- Run `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v` to verify parser behavior
- Parse errors are logged via `logging.getLogger("opml_parser").warning(...)` — check app logs for `OPML parse error` prefix
- Function never raises — empty return list is the failure signal for callers

## Deviations

- Wrote 17 tests instead of the minimum 12 — added extra edge cases for empty bytes, non-bytes input, and empty text+title attrs
- Added `test_parse_non_bytes_returns_empty_list` to verify the function handles string input gracefully (not in original spec but a realistic caller mistake)

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/services/opml_parser.py` — new pure function module (68 lines), parse_opml() + _walk_outlines() helper
- `backend/tests/test_opml_import.py` — new test file with 17 parser tests across 5 test classes
- `.gsd/milestones/M010/slices/S05/S05-PLAN.md` — added Observability / Diagnostics section and failure-path verification step
- `.gsd/milestones/M010/slices/S05/tasks/T01-PLAN.md` — added Observability Impact section
