---
id: T04
parent: S01
milestone: M010
provides:
  - 23 unit tests covering feed parsing pipeline, article creation, IRI hashing, dedup, bulk assembly, error handling
key_files:
  - backend/tests/test_rss_feed_parser.py
key_decisions:
  - "Used importlib.util to load rss-reader app.py as 'rss_reader_app' module — avoids name collision with backend/app/ package that sys.path.insert cannot resolve"
patterns_established:
  - "SimpleNamespace mocks feedparser entry objects for getattr()-based code (matches feedparser's FeedParserDict attribute access pattern)"
  - "importlib.util.spec_from_file_location pattern for importing app modules that collide with backend package names"
observability_surfaces:
  - "pytest tests/test_rss_feed_parser.py -v — 23 tests with per-test PASS/FAIL output"
  - "Any regression in entry_to_article, _mint_article_iri, _time_struct_to_iso, or get_existing_article_iris surfaces as assertion failure"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T04: Unit tests for feed parsing pipeline and article creation

**23 unit tests covering RSS 2.0/Atom entry mapping, IRI determinism, SHA-256 hashing, dedup, bulk command assembly, error handling, and date parsing — all pass without Docker.**

## What Happened

Created `backend/tests/test_rss_feed_parser.py` with 23 tests organized into 9 test classes:

- **TestRSS20EntryMapping** (3 tests): Full RSS 2.0 entry mapping, published date, summary
- **TestAtomEntryMapping** (2 tests): Atom `id` field, `updated_parsed` fallback
- **TestMissingOptionalFields** (1 test): Minimal entry with only title+link
- **TestArticleIRI** (4 tests): Determinism, different IDs → different IRIs, SHA-256 hex verification, direct hash match
- **TestDuplicateDetection** (3 tests): SPARQL result parsing, filtering against existing IRIs, query failure resilience
- **TestBulkCommandAssembly** (1 test): Mock batch.add() calls verified per-article
- **TestFeedErrorHandling** (2 tests): Bozo feed with entries still usable, empty feed → no articles
- **TestDateParsing** (3 tests): time.struct_time → ISO 8601, None input, round-trip in article
- **TestRealWorldEntry** (1 test): Realistic RSS 2.0 entry with all feedparser-normalized fields
- **TestConstants** (3 tests): ARTICLE_TYPE, SUBSCRIPTION_TYPE, RSS_NS constants

Key implementation detail: The rss-reader `app.py` module name collides with `backend/app/` package. Used `importlib.util.spec_from_file_location` to load the module from an explicit file path, avoiding the `sys.path` ordering conflict.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v` — **23 tests passed**
- `cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py tests/test_app_permissions.py -v` — **69 tests passed** (all three test files together)

Slice-level checks (this is the final task in S01):
- ✅ IRI prefix whitelist tests: 13 pass (≥8 required)
- ✅ Feed parsing tests: 23 pass (≥10 required)
- ✅ Model manifest validates: `rss-feeds v1.0.0`
- ✅ App manifest validates: `rss-reader v1.0.0`
- ⏳ Docker integration (install model → install app → trigger poll-feeds → articles queryable) — requires running stack, not verifiable in unit test context

## Diagnostics

- Run `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v --tb=short` to see all test outcomes
- Run a single test class: `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py::TestArticleIRI -v`
- Grep for `FAILED` in pytest output to find regressions

## Deviations

- Used `importlib.util.spec_from_file_location` instead of plain `sys.path.insert` — the rss-reader `app.py` name collides with `backend/app/` package and `sys.path` manipulation alone cannot resolve the ambiguity at collection time.
- Added Observability Impact section to T04-PLAN.md as required by pre-flight check.

## Known Issues

None.

## Files Created/Modified

- `backend/tests/test_rss_feed_parser.py` — new: 23 unit tests for feed parsing pipeline
- `.gsd/milestones/M010/slices/S01/tasks/T04-PLAN.md` — added Observability Impact section
- `.gsd/milestones/M010/slices/S01/S01-PLAN.md` — marked T04 as complete
