---
id: T01
parent: S02
milestone: M010
provides:
  - parse_json_feed() — JSON Feed 1.1 → feedparser-compatible dict
  - discover_feeds_from_html() — HTML page → feed URL list
  - parse_feed_content() — content-type dispatch (XML→feedparser, JSON→parse_json_feed)
  - services/ package under apps/rss-reader/
key_files:
  - apps/rss-reader/services/__init__.py
  - apps/rss-reader/services/feed_service.py
  - backend/tests/test_feed_service.py
key_decisions:
  - Used html.parser.HTMLParser (stdlib) for feed discovery instead of regex — more robust tag attribute parsing
  - SimpleNamespace for JSON Feed entries to match feedparser's attribute-access pattern
  - ISO 8601 parsing via datetime.strptime with multiple format fallbacks (no dateutil dependency)
patterns_established:
  - importlib.util.spec_from_file_location to import services module in tests (avoids backend/app collision)
  - feedparser-compatible bozo pattern for JSON Feed parse errors (bozo=True, bozo_exception, empty entries)
  - FEED_TYPES frozenset for recognized feed content types
observability_surfaces:
  - parse_json_feed returns bozo=True + bozo_exception on failure (callers check result["bozo"])
  - parse_feed_content propagates feedparser's bozo flag for XML parse failures
  - 20 pytest tests validate all happy + error paths
duration: 10m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Implement FeedService pure functions — JSON Feed parser, feed discovery, and content type dispatch

**Built three pure data-transformer functions (parse_json_feed, discover_feeds_from_html, parse_feed_content) with 20 passing tests.**

## What Happened

Created the `apps/rss-reader/services/` package and implemented `feed_service.py` with three pure functions:

1. **`parse_json_feed(content)`** — Parses JSON Feed 1.1 content into feedparser-compatible dicts. Handles `authors[]` array (takes first name), `content_text` vs `content_html` priority, ISO 8601 date parsing to `time.struct_time`, and the bozo error pattern for invalid input.

2. **`discover_feeds_from_html(html, base_url)`** — Uses stdlib `HTMLParser` to extract `<link rel="alternate">` tags with feed content types (RSS, Atom, JSON Feed). Resolves relative hrefs via `urllib.parse.urljoin`.

3. **`parse_feed_content(raw_bytes, content_type)`** — Dispatches to `parse_json_feed()` when content_type contains "json", otherwise passes to `feedparser.parse(BytesIO(...))`.

Wrote 20 tests covering: well-formed/minimal/malformed JSON feeds, date parsing, author extraction, bytes input, HTML discovery with multiple formats, relative URL resolution, empty pages, and content-type dispatch for RSS/Atom/JSON/unknown.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v` — **20 passed** (≥12 required) ✅
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` — syntax OK ✅
- `test -f apps/rss-reader/services/__init__.py` — exists ✅
- S01 regression: `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v` — **23 passed** ✅

### Slice-level checks (partial — T01 is first of 4 tasks):
- ✅ `tests/test_feed_service.py` — 20 tests pass (35+ target is cumulative across T01-T04)
- ✅ `tests/test_rss_feed_parser.py` — 23 tests, zero regressions
- ✅ `feed_service.py` syntax valid
- ⏳ `app.py` syntax — not yet modified (T03)
- ✅ `services/__init__.py` exists

## Diagnostics

- `parse_json_feed()` returns `{"bozo": True, "bozo_exception": <exc>, "entries": [], "feed": {}}` on any parse failure — callers inspect `result["bozo"]` to detect bad feeds
- Tests can be run in isolation: `.venv/bin/python -m pytest tests/test_feed_service.py -v`
- No runtime logging yet — these are pure functions; logging is added when I/O methods wrap them in T02

## Deviations

- Wrote 20 tests instead of the planned 12 — added tests for bytes input, missing-items-key, non-feed-alternate-ignored, application/json dispatch, and Atom content type to improve coverage.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/services/__init__.py` — empty package marker (new)
- `apps/rss-reader/services/feed_service.py` — three pure functions + HTMLParser subclass (new)
- `backend/tests/test_feed_service.py` — 20 unit tests across 3 test classes (new)
- `.gsd/milestones/M010/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section (pre-flight fix)
