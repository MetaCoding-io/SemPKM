---
id: T01
parent: S02
milestone: M010
provides:
  - parse_json_feed() — JSON Feed 1.1 parser with feedparser-compatible output
  - discover_feeds_from_html() — HTML <link rel="alternate"> feed URL extractor
  - parse_feed_content() — content-type dispatcher (XML→feedparser, JSON→parse_json_feed)
  - services/ package structure for rss-reader app
key_files:
  - apps/rss-reader/services/__init__.py
  - apps/rss-reader/services/feed_service.py
  - backend/tests/test_feed_service.py
key_decisions:
  - Used SimpleNamespace for JSON Feed entries (attribute access like feedparser's FeedParserDict)
  - Used stdlib html.parser.HTMLParser for feed discovery (no extra dependencies)
  - Truncate content_html to 500 chars when used as summary fallback
patterns_established:
  - JSON Feed bozo pattern mirrors feedparser — bozo=True, bozo_exception, entries=[] on parse failure
  - importlib.util.spec_from_file_location pattern reused from test_rss_feed_parser.py for test imports
observability_surfaces:
  - none (pure functions — callers responsible for logging)
duration: 15m
verification_result: passed
completed_at: 2026-03-18T14:15:00-04:00
blocker_discovered: false
---

# T01: Implement FeedService pure functions — JSON Feed parser, feed discovery, and content type dispatch

**Created services/ package with three pure data-transformer functions: parse_json_feed (JSON Feed 1.1 → feedparser-compatible dict), discover_feeds_from_html (HTML link tag extraction), parse_feed_content (XML/JSON content-type dispatch). 18 unit tests pass.**

## What Happened

Created the `apps/rss-reader/services/` package with `__init__.py` and `feed_service.py`. Implemented three pure functions:

1. **`parse_json_feed(content)`** — Parses JSON Feed 1.1 content into a feedparser-compatible dict. Each entry is a `SimpleNamespace` with `id`, `title`, `link`, `author`, `summary`, `published_parsed`. Handles content_text/content_html precedence, ISO 8601 date parsing, and authors array. Returns `bozo=True` with empty entries on malformed input (matching feedparser's error convention).

2. **`discover_feeds_from_html(html, base_url)`** — Uses stdlib `HTMLParser` to find `<link rel="alternate" type="...">` tags for RSS, Atom, and JSON Feed types. Resolves relative URLs via `urljoin`. Returns list of `{url, title, type}` dicts.

3. **`parse_feed_content(raw_bytes, content_type)`** — Dispatches to `parse_json_feed()` when content_type contains "json", otherwise to `feedparser.parse(BytesIO(raw_bytes))`.

Wrote 18 unit tests (8 JSON Feed, 5 discovery, 5 dispatch) exceeding the ≥12 requirement.

## Verification

- 18/18 tests pass in `test_feed_service.py`
- 38/38 S01 tests pass in `test_rss_feed_parser.py` (zero regressions)
- Syntax check passes for `feed_service.py`
- Syntax check passes for `app.py`
- `services/__init__.py` exists

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_feed_service.py -v` | 0 | ✅ pass | 0.07s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v` | 0 | ✅ pass | 0.27s |
| 3 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"` | 0 | ✅ pass | <1s |
| 5 | `test -f apps/rss-reader/services/__init__.py` | 0 | ✅ pass | <1s |

## Diagnostics

- `parse_json_feed()` returns `bozo=True` + `bozo_exception` on parse failure — callers can check `result["bozo"]` to detect bad feeds
- All functions are pure (no side effects, no logging, no SDK dependency) — callers add observability

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/rss-reader/services/__init__.py` — empty package marker (new)
- `apps/rss-reader/services/feed_service.py` — three pure functions: parse_json_feed, discover_feeds_from_html, parse_feed_content (new)
- `backend/tests/test_feed_service.py` — 18 unit tests covering all three functions (new)
