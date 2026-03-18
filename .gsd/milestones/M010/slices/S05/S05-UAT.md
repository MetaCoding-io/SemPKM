# S05: OPML import + app settings — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: OPML parsing is a pure function tested with 21 edge cases. Import routes and settings are tested with mocked SDK context (11+20 tests). No live runtime needed — S06 E2E tests will cover the Docker integration path.

## Preconditions

- Backend venv available at `backend/.venv/` (in the M010 worktree)
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
2. **Expected:** 2 tests pass — two-level nesting produces `"Parent/Child"` category, three-level produces `"L1/L2/L3"`

### 3. OPML parser handles title fallback chain

1. Run: `pytest tests/test_opml_import.py::TestTitleFallback -v`
2. **Expected:** 4 tests pass — text attr used first, title attr second, URL as last resort, empty text treated as missing

### 4. OPML parser rejects invalid XML gracefully

1. Run: `pytest tests/test_opml_import.py::TestInvalidXml -v`
2. **Expected:** 3 tests pass — malformed XML, garbage bytes, and empty bytes all return `[]` (never raise)

### 5. OPML import route creates subscriptions

1. Run: `pytest tests/test_opml_import.py::TestProcessOpmlImportSuccess -v`
2. **Expected:** 2 tests pass — 3 feeds created with correct counts, subscribe() called once per feed

### 6. OPML import handles duplicates and errors

1. Run: `pytest tests/test_opml_import.py::TestProcessOpmlImportDuplicates tests/test_opml_import.py::TestProcessOpmlImportErrors -v`
2. **Expected:** 4 tests pass — some/all duplicates counted correctly, subscribe exceptions increment error count, tag patch failure doesn't fail import

### 7. OPML import applies category tags

1. Run: `pytest tests/test_opml_import.py::TestProcessOpmlImportCategories -v`
2. **Expected:** 3 tests pass — categories patched as bpkm:tags on created feeds; no patch for uncategorized or duplicate feeds

### 8. Manifest validates with settings

1. Run: `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); assert m.permissions.settings == True; assert len(m.settings) == 2; print(f'Settings: {[s.key for s in m.settings]}')"`
2. **Expected:** Prints `Settings: ['articlesPerPage', 'markReadOnOpen']`

### 9. Settings context returns defaults when nothing saved

1. Run: `pytest tests/test_rss_settings.py::TestGetSettingsContext::test_returns_defaults_when_unset -v`
2. **Expected:** 1 test passes — articlesPerPage defaults to "50", markReadOnOpen defaults to "true"

### 10. Settings save round-trip

1. Run: `pytest tests/test_rss_settings.py::TestSaveSettings -v`
2. **Expected:** 5 tests pass — both values saved correctly, unchecked checkbox saves "false", checked saves "true", out-of-range values clamped, non-integer values fall back to default

### 11. articlesPerPage validation clamps to range

1. Run: `pytest tests/test_rss_settings.py::TestValidateArticlesPerPage -v`
2. **Expected:** 8 tests pass — valid in range accepted, below 10 clamped to "10", above 200 clamped to "200", negative clamped, "abc" returns default "50", empty string returns default, boundaries (10 and 200) accepted

### 12. Zero regressions on S01/S02 tests

1. Run: `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py -v`
2. **Expected:** 88 tests pass — no regressions from S05 changes to app.py or test file module loading

### 13. Full cross-test isolation

1. Run: `pytest tests/test_rss_feed_parser.py tests/test_feed_service.py tests/test_opml_import.py tests/test_rss_settings.py -v`
2. **Expected:** All 140 tests pass with zero cross-test interference

## Edge Cases

### Invalid XML returns empty list (not exception)

1. Run: `cd backend && .venv/bin/python -c "import importlib.util,sys,os; spec=importlib.util.spec_from_file_location('m',os.path.join('..','apps','rss-reader','services','opml_parser.py')); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); r=mod.parse_opml(b'<not xml'); assert r==[], f'Got {r}'; print('OK: invalid XML returns []')"`
2. **Expected:** Prints "OK: invalid XML returns []" — parse_opml never raises

### OPML with encoding declaration

1. Run: `pytest tests/test_opml_import.py::TestEncoding -v`
2. **Expected:** 2 tests pass — UTF-8 special characters and XML prolog with encoding declaration both parse correctly

### Empty and missing OPML body

1. Run: `pytest tests/test_opml_import.py::TestEmptyBody tests/test_opml_import.py::TestMissingBody -v`
2. **Expected:** 2 tests pass — both return empty list

### articlesPerPage boundary values

1. Run: `pytest tests/test_rss_settings.py::TestValidateArticlesPerPage::test_boundary_min tests/test_rss_settings.py::TestValidateArticlesPerPage::test_boundary_max -v`
2. **Expected:** 2 tests pass — 10 and 200 accepted without clamping

### Source file syntax verification

1. Run: `python3 -c "import ast; ast.parse(open('apps/rss-reader/services/opml_parser.py').read()); ast.parse(open('apps/rss-reader/app.py').read()); print('Both files syntax OK')"`
2. **Expected:** Prints "Both files syntax OK"

## Failure Signals

- Any `test_opml_import.py` test failure → OPML parser or import route logic broken
- Any `test_rss_settings.py` test failure → settings manifest, route, or validation broken
- `parse_app_manifest()` raises → manifest.yaml has invalid settings declarations
- `ast.parse()` fails → syntax error in source file
- Tests in `test_rss_feed_parser.py` or `test_feed_service.py` fail → S01/S02 regression caused by S05 changes (most likely the sys.modules guard issue)
- All 4 test files fail when run together but pass individually → cross-test module duplication bug (sys.modules guard missing or broken)

## Requirements Proved By This UAT

- **RSS-05** (OPML import) — artifact-level proof: parser handles all OPML variants (flat, nested categories, mixed outlines, invalid XML), import route creates subscriptions with category tags preserved as bpkm:tags, error handling verified. Awaits S06 E2E for live Docker proof.

## Not Proven By This UAT

- Live Docker round-trip (OPML upload through nginx → app subprocess → triplestore)
- Real browser interaction with the Import OPML button and file picker
- Settings persistence across app restart (requires running app process with real SettingsClient)
- Feed sidebar UI rendering with the new buttons (requires running frontend)
- That the settings values actually influence reader behavior (articlesPerPage limit, markReadOnOpen auto-read) — reader logic consuming these values is in S03/S04

## Notes for Tester

- All tests run from the M010 worktree backend directory (`.gsd/worktrees/M010/backend/`), not the main tree.
- Tests use mocked SDK context objects following established `test_rss_feed_parser.py` conventions.
- The `sys.modules` guard pattern is critical — if adding a new test file that imports `app.py` via importlib, check `if "rss_reader_app_mod" in sys.modules` first to prevent cross-test module duplication.
- OPML test data is inline XML bytes in the test file, not external fixture files — easy to inspect and modify.
- The manifest validation check requires the backend venv (Pydantic dependency for `parse_app_manifest()`).
