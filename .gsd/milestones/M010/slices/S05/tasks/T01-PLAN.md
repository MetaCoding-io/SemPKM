---
estimated_steps: 5
estimated_files: 2
---

# T01: Create OPML parser pure function with comprehensive tests

**Slice:** S05 — OPML import + app settings
**Milestone:** M010

## Description

Build the `parse_opml()` pure function that converts OPML XML bytes into a list of feed entry dicts. OPML is a simple XML format where `<outline>` elements with `xmlUrl` attributes are feeds, and `<outline>` elements without `xmlUrl` are category folders. The parser must walk the tree tracking parent category context so nested categories are preserved as `/`-delimited strings on child feeds.

This is a pure data transformer with zero SDK or app dependency — fully testable without mocking. It's the foundation that T02 wires into the import route.

**Relevant skill:** `test` (for test generation patterns)

## Steps

1. **Create `apps/rss-reader/services/opml_parser.py`** with a single public function:
   ```python
   def parse_opml(xml_content: bytes) -> list[dict]:
   ```
   - Use `xml.etree.ElementTree.fromstring(xml_content)` — pass bytes so the XML parser handles encoding declarations
   - Find the `<body>` element (OPML spec: `<opml><body><outline .../>`)
   - Recursively walk `<outline>` elements:
     - If outline has `xmlUrl` attribute → it's a feed entry. Extract: `url` = `xmlUrl`, `title` = `text` or `title` attr (fall back to `xmlUrl` if both empty), `html_url` = `htmlUrl` or `None`, `category` = parent category string or `None`
     - If outline has NO `xmlUrl` → it's a category folder. Its `text` attribute becomes the category label. Recurse into children with this category as context.
   - For nested categories (2+ levels), join with `/` delimiter (e.g., `"Tech/Blogs"`)
   - Wrap entire function in try/except for `ET.ParseError` and generic `Exception` — return empty list on any parse error (log warning if possible, but don't import logging if it adds complexity)
   - Return `list[dict]` where each dict has keys: `url`, `title`, `html_url`, `category`

2. **Ensure `apps/rss-reader/services/__init__.py` exists** (it should from S02, but verify)

3. **Create `backend/tests/test_opml_import.py`** with parser unit tests using `importlib.util.spec_from_file_location` pattern to import the module:
   ```python
   import importlib.util
   _spec = importlib.util.spec_from_file_location(
       "opml_parser",
       str(Path(__file__).resolve().parents[2] / "apps" / "rss-reader" / "services" / "opml_parser.py")
   )
   _mod = importlib.util.module_from_spec(_spec)
   _spec.loader.exec_module(_mod)
   parse_opml = _mod.parse_opml
   ```

4. **Write ≥12 test cases** covering:
   - Valid OPML with flat feeds (no categories) → returns list with `category=None`
   - Valid OPML with single-level category folders → feeds have `category="Tech"` etc.
   - Nested categories (2 levels) → `category="Tech/Blogs"`
   - Deeply nested categories (3+ levels) → `category="Tech/Blogs/Python"`
   - Feeds with missing `text` and `title` → falls back to `xmlUrl` as title
   - Empty OPML body (no `<outline>` children) → returns `[]`
   - Invalid XML (not well-formed) → returns `[]`, no exception raised
   - OPML with no `<body>` element → returns `[]`
   - Mixed: some outlines are categories, some are feeds at same level
   - Feed with `htmlUrl` attribute → `html_url` populated
   - Feed without `htmlUrl` → `html_url` is `None`
   - Encoding: OPML with UTF-8 declared in XML prolog (pass as bytes)

5. **Run tests and verify syntax:**
   ```bash
   cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v
   python3 -c "import ast; ast.parse(open('../apps/rss-reader/services/opml_parser.py').read())"
   ```

## Must-Haves

- [ ] `parse_opml(xml_content: bytes) -> list[dict]` is a pure function with no SDK dependency
- [ ] Category folders tracked via recursive tree walk, nested categories `/`-delimited
- [ ] Missing titles fall back to URL
- [ ] Invalid XML returns empty list (no raised exception)
- [ ] ≥12 pure function tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_opml_import.py -v -k "test_parse"` — ≥12 tests pass
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/opml_parser.py').read())"` — syntax OK
- No imports from SDK or app framework in `opml_parser.py`

## Inputs

- `apps/rss-reader/services/__init__.py` — exists from S02
- KNOWLEDGE.md — `importlib.util.spec_from_file_location` pattern for test imports

## Expected Output

- `apps/rss-reader/services/opml_parser.py` — new pure function module (~40-60 lines)
- `backend/tests/test_opml_import.py` — new test file with ≥12 parser tests

## Observability Impact

- **New signal:** `parse_opml()` emits `logging.warning` on invalid XML input (exception type + message), enabling log-based diagnosis of malformed OPML uploads in production.
- **Inspection surface:** The function's return value is the primary diagnostic — an empty list means parse failure. Callers (T02's import route) will surface this as a user-visible error count.
- **Failure visibility:** All parse errors are caught and converted to empty-list returns with logged warnings. No unhandled exceptions escape the function boundary.
