# S05: OPML import + app settings — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: OPML parsing is a pure function tested with 21 edge cases. Import routes and settings are tested with mocked SDK context (11+20 tests). No live runtime needed — S06 E2E tests will cover the Docker integration path.

## Preconditions

- Backend venv available at `backend/.venv/`
- All test dependencies installed (`pytest`, `pydantic`)
- RSS reader app source at `apps/rss-reader/`
- No Docker stack needed (all tests are unit/integration with mocks)

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_opml_import.py tests/test_rss_settings.py -v --tb=short
```
Expected: 52 tests pass in <1s.

## Test Cases

### 1. OPML parser handles flat feeds

1. Run: `pytest tests/test_opml_import.py::TestFlatFeeds -v`
2. **Expected:** 2 tests pass — single feed and multiple flat feeds parsed with correct url/title/category/html_url fields

### 2. OPML parser handles nested categories

1. Run: `pytest tests/test_opml_import.py::TestNestedCategories -v`
2. **Expected:** 2 tests pass — two-level nesting produces "Parent/Child" category, three-level produces "L1/L2/L3"

### 3. OPML parser handles title fallback chain

1. Run: `pytest tests/test_opml_import.py::TestTitleFallback -v`
2. **Expected:** 4 tests pass — text attr used first, title attr second, URL as last resort, empty text treated as missing

### 4. OPML parser rejects invalid XML gracefully

1. Run: `pytest tests/test_opml_import.py::TestInvalidXml -v`
2. **Expected:** 3 tests pass — malformed XML, garbage bytes, and empty bytes all return `[]` (never raise)

### 5. OPML import route creates subscriptions

1. Run: `pytest tests/test_opml_import.py::TestProcessOpmlImportSuccess -v`
2. **Expected:** 2 tests pass — 3 feeds created with correct counts, subscribe() called once per feed

### 6. OPML import handles duplicates

1. Run: `pytest tests/test_opml_import.py::TestProcessOpmlImportDuplicates -v`
2. **Expected:** 2 tests pass — some and all duplicates counted correctly, no errors

### 7. OPML import applies category tags

1. Run: `pytest tests/test_opml_import.py::TestProcessOpmlImportCategories -v`
2. **Expected:** 3 tests pass — categories patched as bpkm:tags on created feeds; no patch for uncategorized or duplicate feeds

### 8. OPML import tolerates failures

1. Run: `pytest tests/test_opml_import.py::TestProcessOpmlImportErrors -v`
2. **Expected:** 2 tests pass — subscribe exception increments error count; tag patch failure doesn't fail the import

### 9. Manifest validates with settings

1. Run: `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); assert m.permissions.settings == True; assert len(m.settings) == 2; print('OK')"`
2. **Expected:** Prints "OK" — manifest has 2 settings and permissions.settings is True

### 10. Settings context returns defaults when nothing saved

1. Run: `pytest tests/test_rss_settings.py::TestGetSettingsContext::test_returns_defaults_when_unset -v`
2. **Expected:** 1 test passes — articlesPerPage defaults to "50", markReadOnOpen defaults to "true"

### 11. Settings context returns saved values

1. Run: `pytest tests/test_rss_settings.py::TestGetSettingsContext::test_returns_saved_values -v`
2. **Expected:** 1 test passes — saved values override defaults

### 12. articlesPerPage validation clamps to range

1. Run: `pytest tests/test_rss_settings.py::TestValidateArticlesPerPage -v`
2. **Expected:** 8 tests pass — valid in range, clamped below 10, clamped above 200, negatives clamped, non-integer returns default "50", empty string returns default, boundary values (10 and 200) accepted

### 13. Settings save persists correctly

1. Run: `pytest tests/test_rss_settings.py::TestSaveSettings -v`
2. **Expected:** 5 tests pass — both values saved, checkbox unchecked saves "false", checked saves "true", clamps articles_per_page, invalid value saves default

## Edge Cases

### Invalid XML returns empty list (not exception)

1. Run: `cd backend && .venv/bin/python -c "import importlib.util,sys,os; spec=importlib.util.spec_from_file_location('m',os.path.join('..','apps','rss-reader','services','opml_parser.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); r=mod.parse_opml(b'<not xml'); assert r==[], f'Got {r}'; print('OK')"`
2. **Expected:** Prints "OK" — parse_opml never raises, returns empty list

### OPML with encoding declaration

1. Run: `pytest tests/test_opml_import.py::TestEncoding -v`
2. **Expected:** 2 tests pass — UTF-8 special characters and XML prolog with encoding declaration both parse correctly

### articlesPerPage non-numeric input

1. Run: `pytest tests/test_rss_settings.py::TestValidateArticlesPerPage::test_non_integer_returns_default -v`
2. **Expected:** 1 test passes — "abc" input returns "50" default

### Cross-test module isolation

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py tests/test_opml_import.py tests/test_rss_settings.py -v`
2. **Expected:** All 140 tests pass — no cross-test interference from importlib module loading

## Failure Signals

- Any `test_opml_import.py` test failure → OPML parser or import route logic broken
- Any `test_rss_settings.py` test failure → settings manifest, route, or validation broken
- `parse_app_manifest()` raises → manifest.yaml has invalid settings declarations
- `ast.parse()` fails on app.py or opml_parser.py → syntax error in source
- Tests in `test_rss_feed_parser.py` fail → S01/S02 regression caused by S05 changes

## Requirements Proved By This UAT

- **RSS-05** (OPML import) — artifact-level proof: parser handles all OPML variants, import route creates subscriptions with category tags, error handling verified. Awaits S06 E2E for live Docker proof.

## Not Proven By This UAT

- Live Docker round-trip (OPML upload through nginx → app subprocess → triplestore)
- Real browser interaction with the Import OPML button and file picker
- Settings persistence across app restart (requires running app process with real SettingsClient)
- Feed sidebar UI rendering with the new buttons (requires running frontend)

## Notes for Tester

- All tests use mocked SDK context objects. The mock patterns follow the established `test_rss_feed_parser.py` conventions.
- The `sys.modules` guard pattern (Knowledge Pattern #3) is critical — if you add a new test file that imports `app.py` via importlib, you must check `if "rss_reader_app_mod" in sys.modules` first.
- OPML test data is inline XML bytes in the test file, not external fixture files.
