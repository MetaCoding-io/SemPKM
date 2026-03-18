---
id: T04
parent: S01
milestone: M010
provides:
  - 38 unit tests covering feed entry → article mapping, IRI minting, date parsing, dedup, bulk assembly, error handling, and poll-feeds task flow
key_files:
  - backend/tests/test_rss_feed_parser.py
key_decisions:
  - "Used importlib.util.spec_from_file_location to load rss-reader app.py — avoids name collision with backend/app/ package that sys.path.insert cannot resolve"
patterns_established:
  - "Import pattern for testing app modules that collide with backend package names: use importlib.util.spec_from_file_location + sys.modules registration, then patch with the registered module name"
  - "Mocking async context managers for ctx.commands.bulk(): use MagicMock (not AsyncMock) for the method itself, wire __aenter__/__aexit__ on the return value"
observability_surfaces:
  - "pytest tests/test_rss_feed_parser.py -v — per-test PASS/FAIL for 38 tests covering entry_to_article, _mint_article_iri, _struct_time_to_iso, get_existing_article_iris, poll_feeds"
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T04: Unit tests for feed parsing pipeline and article creation

**Created 38 unit tests in test_rss_feed_parser.py covering RSS/Atom entry mapping, IRI determinism, date parsing, dedup, bulk command assembly, bozo/empty feed error handling, and poll-feeds task flow with mocked SDK.**

## What Happened

Created `backend/tests/test_rss_feed_parser.py` with 38 tests organized into 9 test classes:

- **TestRSS2EntryMapping** (4 tests): RSS 2.0 entry → article dict mapping including title, link, author, defaults, published date, summary
- **TestAtomEntryMapping** (3 tests): Atom entry id field, missing published_parsed handling, full field mapping
- **TestMissingFields** (4 tests): Minimal entry, no author, no summary, completely empty entry
- **TestArticleIRIDeterminism** (7 tests): Same inputs = same IRI, different inputs = different IRI, SHA-256 hex verification, hash length, manual hash comparison, entry_to_article determinism
- **TestDateParsing** (4 tests): Valid struct_time conversion, None input, epoch time, ISO 8601 parseability
- **TestDuplicateDetection** (3 tests): get_existing_article_iris returns set, empty result, SPARQL references feed IRI
- **TestBulkCommandAssembly** (3 tests): Article dict keys, batch.add call count, dedup filtering
- **TestErrorHandling** (4 tests): Bozo feed with no entries, empty feed, bozo with valid entries, no subscriptions
- **TestRealisticEntry** (3 tests): Full feedparser-normalized entry, HTML summary passthrough, link as fallback ID
- **TestConstants** (3 tests): ARTICLE_TYPE, SUBSCRIPTION_TYPE, RSS_NS values

Hit two issues during development:
1. `from app import ...` resolved to `backend/app/__init__.py` instead of the rss-reader's `app.py` — solved with `importlib.util.spec_from_file_location` to load the module by path and register under `rss_reader_app_mod`.
2. `patch("app.parse_feed")` similarly targeted the wrong module — fixed by patching `rss_reader_app_mod.parse_feed`.
3. `ctx.commands.bulk()` async context manager mock failed because AsyncMock makes `bulk()` return a coroutine — fixed by using MagicMock for `commands.bulk` and wiring `__aenter__`/`__aexit__` on its return value.

## Verification

- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — 38 tests passed
- `cd backend && python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py -v` — all 51 tests passed (13 IRI + 38 feed parser)
- Model manifest validates: `rss-feeds 1.0.0`
- App manifest validates: `rss-reader`

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v` | 0 | ✅ pass | 0.28s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py -v` | 0 | ✅ pass | 0.26s |
| 3 | Model manifest validation (`parse_manifest(Path('models/rss-feeds'))`) | 0 | ✅ pass | <1s |
| 4 | App manifest validation (`parse_app_manifest('apps/rss-reader/manifest.yaml')`) | 0 | ✅ pass | <1s |
| 5 | Docker integration (install model → app → poll-feeds → SPARQL) | — | ⏳ deferred to slice integration | — |

## Diagnostics

- **Run all feed parser tests:** `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v --tb=short`
- **Run specific test class:** `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py::TestErrorHandling -v`
- **Grep for regressions:** `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v | grep FAILED`
- **Import verification:** `cd backend && .venv/bin/python -c "import sys; sys.path.insert(0, '../apps/rss-reader'); from app import entry_to_article; print('OK')"`

## Deviations

- Plan specified `test_app_permissions.py` in the combined test run, but that file doesn't exist in this worktree. Verified with `test_iri_prefix_fix.py` instead (which covers the same IRI prefix validation).
- Wrote 38 tests (vs plan's ≥10 minimum / observability section's 23 estimate) — extra coverage costs nothing and strengthens the contract.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_rss_feed_parser.py` — new: 38 unit tests for feed parsing pipeline covering entry mapping, IRI minting, date parsing, dedup, bulk assembly, error handling, and task flow
