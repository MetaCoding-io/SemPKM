---
estimated_steps: 5
estimated_files: 3
---

# T01: Implement FeedService pure functions — JSON Feed parser, feed discovery, and content type dispatch

**Slice:** S02 — Feed service + content extraction + feed management
**Milestone:** M010

## Description

Create the `services/` package under `apps/rss-reader/` and implement the foundational pure functions in `feed_service.py`. These functions have zero SDK dependency — they're pure data transformers that parse JSON Feed content, discover feeds from HTML pages, and dispatch between feed formats by content type.

This task establishes the module structure that T02-T04 build on and covers the JSON Feed support gap (feedparser doesn't handle JSON Feed) and feed discovery from website URLs (RSS-08). All functions are importable and testable without mocked SDK clients.

**Relevant skills:** test (for pytest patterns)

## Steps

1. Create `apps/rss-reader/services/__init__.py` as an empty file (makes `services` a package).

2. Create `apps/rss-reader/services/feed_service.py` with these pure functions:

   **`parse_json_feed(content: str | bytes) -> dict`**
   - Parse a JSON Feed 1.1 string into a normalized dict matching feedparser's output structure.
   - JSON Feed spec: top-level `version`, `title`, `items[]` array. Each item has `id`, `title`, `url`, `content_text` and/or `content_html`, `date_published`, `authors[]`.
   - Return a dict with `feed` (title, link) and `entries` list. Each entry is a `SimpleNamespace` with: `id`, `title`, `link`, `author`, `summary` (prefer `content_text`, fall back to `content_html` truncated), `published_parsed` (parsed `date_published` to `time.struct_time`).
   - On invalid JSON or missing `items`, return `{"feed": {}, "entries": [], "bozo": True, "bozo_exception": ...}` — matching feedparser's error pattern.

   **`discover_feeds_from_html(html: str, base_url: str) -> list[dict]`**
   - Parse HTML looking for `<link rel="alternate" type="..." href="...">` tags where type is one of: `application/rss+xml`, `application/atom+xml`, `application/feed+json`, `application/json`.
   - Use a simple regex or `html.parser.HTMLParser` (stdlib, no extra dep). Prefer HTMLParser for robustness.
   - Resolve relative hrefs against `base_url` using `urllib.parse.urljoin`.
   - Return a list of dicts: `[{"url": ..., "title": ..., "type": ...}]`.
   - Return empty list if no feeds found.

   **`parse_feed_content(raw_bytes: bytes, content_type: str) -> dict`**
   - If `content_type` contains `json` (e.g. `application/json`, `application/feed+json`), decode and call `parse_json_feed()`.
   - Otherwise (XML: `application/rss+xml`, `application/atom+xml`, `text/xml`, `application/xml`, or anything else), pass to `feedparser.parse(io.BytesIO(raw_bytes))`.
   - Return the normalized dict (feedparser-compatible structure).
   - Import feedparser at module level (it's in requirements.txt).

3. Write unit tests in `backend/tests/test_feed_service.py`:
   - Use `importlib.util.spec_from_file_location` to import `feed_service.py` from its file path (same pattern as `test_rss_feed_parser.py` to avoid module name collisions with `backend/app/`). The services module path is: `Path(__file__).resolve().parent.parent.parent / "apps" / "rss-reader" / "services" / "feed_service.py"`.
   - **JSON Feed tests (≥5):**
     - Well-formed JSON Feed 1.1 with 3 items → 3 entries with correct title, link, id, author, summary
     - JSON Feed with `content_text` preferred over `content_html`
     - JSON Feed with `date_published` parsed to struct_time (ISO 8601)
     - Minimal JSON Feed (items with only `id` and `url`) → entries with missing fields handled
     - Malformed JSON (invalid JSON string) → bozo=True, entries=[]
   - **Feed discovery tests (≥4):**
     - HTML with RSS + Atom link tags → both discovered
     - HTML with relative href → resolved against base_url
     - HTML with no alternate links → empty list
     - HTML with `application/feed+json` type → JSON Feed discovered
   - **Content type dispatch tests (≥3):**
     - XML content type → feedparser used (verify entries parsed)
     - JSON content type → parse_json_feed used (verify entries parsed)
     - Empty/unknown content type → feedparser used (fallback)

4. Verify all tests pass: `cd backend && python -m pytest tests/test_feed_service.py -v`

5. Verify syntax: `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('syntax OK')"`

## Must-Haves

- [ ] `apps/rss-reader/services/__init__.py` exists (empty or minimal)
- [ ] `parse_json_feed()` normalizes JSON Feed 1.1 items to feedparser-compatible dicts with `id`, `title`, `link`, `author`, `summary`, `published_parsed`
- [ ] `discover_feeds_from_html()` extracts feed URLs from `<link rel="alternate">` tags, resolves relative URLs
- [ ] `parse_feed_content()` dispatches to feedparser for XML and parse_json_feed for JSON based on content_type
- [ ] ≥12 unit tests pass in `backend/tests/test_feed_service.py`
- [ ] JSON Feed with invalid JSON returns bozo=True pattern (not an exception)
- [ ] All three functions are importable from `feed_service.py` without SDK dependencies

## Verification

- `cd backend && python -m pytest tests/test_feed_service.py -v` — ≥12 tests pass
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/feed_service.py').read()); print('OK')"` — syntax valid
- `test -f apps/rss-reader/services/__init__.py` — services package exists

## Inputs

- `apps/rss-reader/app.py` — existing constants (`ARTICLE_TYPE`, `SUBSCRIPTION_TYPE`, `RSS_NS`) and `entry_to_article()` function patterns. FeedService should be consistent with these naming conventions.
- `backend/tests/test_rss_feed_parser.py` — import pattern using `importlib.util.spec_from_file_location` to load app modules without colliding with `backend/app/`.
- JSON Feed 1.1 spec: top-level keys are `version`, `title`, `home_page_url`, `feed_url`, `items`. Item keys: `id`, `url`, `title`, `content_text`, `content_html`, `summary`, `date_published`, `authors` (array of `{name, url}`).

## Observability Impact

- **Signals added:** None at runtime — these are pure functions with no logging or side effects. Callers (T02+) are responsible for logging parse results.
- **Inspection:** `parse_json_feed()` returns `bozo=True` + `bozo_exception` on parse failure, matching feedparser's error convention. Callers can check `result["bozo"]` to detect bad feeds.
- **Failure visibility:** Malformed JSON Feed content returns a well-structured error dict instead of raising. `parse_feed_content()` propagates feedparser's bozo flag for XML parse failures.
- **Test signals:** ≥12 pytest tests in `test_feed_service.py` validate all happy + error paths. Test failures surface exact function + input that broke.

## Expected Output

- `apps/rss-reader/services/__init__.py` — empty file (package marker)
- `apps/rss-reader/services/feed_service.py` — module with `parse_json_feed`, `discover_feeds_from_html`, `parse_feed_content` functions
- `backend/tests/test_feed_service.py` — ≥12 tests covering all three functions
