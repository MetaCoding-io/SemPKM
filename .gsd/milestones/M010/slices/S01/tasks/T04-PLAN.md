---
estimated_steps: 4
estimated_files: 2
---

# T04: Unit tests for feed parsing pipeline and article creation

**Slice:** S01 — Platform fix + Mental Model + App data pipeline
**Milestone:** M010

## Description

Writes unit tests proving the feed entry → article data pipeline works correctly. Tests exercise `entry_to_article()` and the poll-feeds task flow with mocked SDK clients — no running Docker stack needed. This gives S02 a solid foundation to extend and verifies the boundary contract (boundary map S01→S02).

## Steps

1. Create `backend/tests/test_rss_feed_parser.py` with the following test structure:

   **Setup:**
   ```python
   import sys
   from pathlib import Path
   # Make the app importable
   sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "apps" / "rss-reader"))
   from app import entry_to_article, ARTICLE_TYPE, SUBSCRIPTION_TYPE, RSS_NS
   ```

   **Test: RSS 2.0 entry mapping:**
   - Create a feedparser-style entry dict with: `title`, `link`, `author`, `id` (guid), `published_parsed` (time.struct_time), `summary`
   - Call `entry_to_article(entry, feed_iri="urn:sempkm:app:rss-reader:feed-abc", app_id="rss-reader")`
   - Assert returned dict has `iri` starting with `urn:sempkm:app:rss-reader:article-`
   - Assert `type` == `urn:sempkm:model:rss-feeds:Article`
   - Assert `properties` includes mapped dcterms:title, rss:link, rss:author, rss:feedSource, rss:articleId

   **Test: Atom entry mapping:**
   - Similar to RSS 2.0 but entry uses `id` instead of `guid`, `updated_parsed` instead of `published_parsed`
   - Assert correct mapping

   **Test: Entry with missing optional fields:**
   - Entry with only `title` and `link` (no author, no published date, no summary)
   - Assert function does not raise, missing fields are omitted from properties

   **Test: Article IRI determinism:**
   - Same entry + feed_url produces same IRI on repeated calls
   - Different entry IDs produce different IRIs

   **Test: Article IRI uses SHA-256 hash:**
   - Verify the IRI contains a hex hash, not the raw entry ID

   **Test: Duplicate detection helper (if exposed):**
   - Test that given a set of existing article IRIs, new entries are filtered correctly

   **Test: Bulk command assembly:**
   - Given a list of article dicts from `entry_to_article()`, verify they can be added to a mock BulkCollector
   - Assert `batch.add("object.create", article_dict)` is called for each article

   **Test: Feedparser error handling:**
   - When feedparser returns a feed with `bozo=True` and `bozo_exception`, the poll handler should log a warning but not crash

   **Test: Empty feed handling:**
   - Feed with zero entries should produce no article creation commands

   **Test: Published date parsing:**
   - Verify `published_parsed` (time.struct_time) is correctly converted to ISO 8601 datetime string

   **Test: Real-world feed entry structure:**
   - Use a realistic RSS 2.0 entry structure (with all the fields feedparser normalizes) to verify no KeyError

2. Ensure proper imports work by running:
   ```bash
   cd backend && python -c "import sys; sys.path.insert(0, '../apps/rss-reader'); from app import entry_to_article; print('OK')"
   ```

3. Run the tests:
   ```bash
   cd backend && python -m pytest tests/test_rss_feed_parser.py -v
   ```

4. Verify all tests pass alongside the IRI prefix tests:
   ```bash
   cd backend && python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py -v
   ```

## Must-Haves

- [ ] ≥10 unit tests in `test_rss_feed_parser.py`
- [ ] Tests cover RSS 2.0 entry parsing, Atom entry parsing, missing fields, IRI determinism
- [ ] Tests cover bulk command assembly pattern
- [ ] Tests cover error handling (bozo feed, empty feed)
- [ ] Tests import `entry_to_article()` from `apps/rss-reader/app.py` directly
- [ ] All tests pass without a running Docker stack

## Verification

- `cd backend && python -m pytest tests/test_rss_feed_parser.py -v` — all ≥10 tests pass
- `cd backend && python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py tests/test_app_permissions.py -v` — all tests pass together

## Inputs

- `apps/rss-reader/app.py` — T03 output: `entry_to_article()` function and constants to test
- `backend/tests/test_app_permissions.py` — reference for test patterns and mock setup
- `backend/tests/test_sdk_app.py` — reference for SDK test patterns

## Expected Output

- `backend/tests/test_rss_feed_parser.py` — new test file with ≥10 passing tests covering the feed parsing pipeline

## Observability Impact

- **Test signals:** `pytest tests/test_rss_feed_parser.py -v` prints per-test PASS/FAIL — 23 tests covering entry mapping, IRI hashing, dedup, bulk assembly, error handling, and date parsing.
- **Failure visibility:** Any regression in `entry_to_article()`, `_mint_article_iri()`, `_time_struct_to_iso()`, or `get_existing_article_iris()` surfaces immediately via test failure with assertion message showing expected vs actual.
- **Future agent inspection:** Run `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v --tb=short` to see all test outcomes. Grep for `FAILED` in output to find regressions.
- **No runtime signals** — this task adds only offline tests, not runtime behavior.
