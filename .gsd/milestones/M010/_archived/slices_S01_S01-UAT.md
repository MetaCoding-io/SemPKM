# S01: Platform fix + Mental Model + App data pipeline — UAT

**Milestone:** M010
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice produces code artifacts (SDK fix, model, app skeleton, tests) that are fully verifiable without a running Docker stack. Unit tests cover the critical data pipeline. Docker integration testing is deferred to S06 E2E.

## Preconditions

- Backend venv exists at `backend/.venv/` with all dependencies installed (including feedparser)
- Working directory is the repository root
- No Docker stack required for these tests

## Smoke Test

Run the combined test suite:
```
cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py -v
```
**Expected:** 36 tests pass (13 + 23), zero failures.

## Test Cases

### 1. IRI prefix validation whitelist

1. `cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py -v`
2. **Expected:** 13/13 tests pass. Model type IRIs, standard vocab IRIs, user-types IRIs all pass validation. Foreign app IRIs and data namespace IRIs are blocked with PermissionError.

### 2. PermissionError diagnostic message quality

1. `cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_foreign_app_iri_blocked -v`
2. Inspect the test — it asserts the PermissionError message includes both the offending IRI and the required prefix.
3. **Expected:** Test passes. Error message is actionable for debugging.

### 3. Existing permission tests unbroken

1. `cd backend && .venv/bin/python -m pytest tests/test_app_permissions.py -v`
2. **Expected:** 33/33 tests pass. No regressions from the IRI prefix fix. Updated tests (`test_foreign_app_iri_raises`, `test_nested_params_foreign_app_iri_scanned`, `test_deeply_nested_data_iri_caught`, `test_http_url_in_params_allowed`) reflect new enforcement scope.

### 4. rss-feeds model manifest validation

1. `cd backend && .venv/bin/python -c "from app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('../models/rss-feeds')); print(f'{m.modelId} v{m.version}, icons: {len(m.icons)}')"` 
2. **Expected:** Output is `rss-feeds v1.0.0, icons: 2`

### 5. rss-feeds JSON-LD files are valid

1. `python3 -c "import json; [json.load(open(f'models/rss-feeds/{d}')) for d in ['ontology/rss-feeds.jsonld', 'shapes/rss-feeds.jsonld', 'views/rss-feeds.jsonld']]; print('All valid')"`
2. **Expected:** Prints `All valid` — no JSON parse errors.

### 6. rss-feeds ontology has correct classes and properties

1. `python3 -c "import json; d=json.load(open('models/rss-feeds/ontology/rss-feeds.jsonld')); classes=[e['@id'] for e in d['@graph'] if e.get('@type')=='owl:Class']; print(f'Classes: {classes}')"` 
2. **Expected:** Classes include `rss:Article` and `rss:FeedSubscription`.

### 7. rss-reader app manifest validation

1. `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); print(f'{m.appId} v{m.version}, tasks: {[t.id for t in m.tasks]}')"` 
2. **Expected:** Output shows `rss-reader v1.0.0, tasks: ['poll-feeds']`

### 8. rss-reader app.py syntax and importability

1. `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('Syntax OK')"`
2. **Expected:** Prints `Syntax OK`.

### 9. Feed parsing pipeline unit tests

1. `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py -v`
2. **Expected:** 23/23 tests pass covering: RSS 2.0 entry mapping, Atom entry mapping, missing field handling, article IRI determinism, duplicate detection, bulk command assembly, feed error handling, date parsing, real-world entry, and constants.

### 10. Article IRI determinism

1. `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py::TestArticleIRI -v`
2. **Expected:** 4/4 tests pass. Same inputs produce same IRI. Different entry IDs produce different IRIs. IRI contains SHA-256 hex.

### 11. Cross-test-file compatibility

1. `cd backend && .venv/bin/python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py tests/test_app_permissions.py -v`
2. **Expected:** 69/69 tests pass. All three test files run together without import conflicts or fixture collisions.

## Edge Cases

### Model type IRI in object.create params

1. Simulate the exact pattern RSS Reader uses: `_check_iri_prefix("rss-reader", {"type": "urn:sempkm:model:rss-feeds:Article", "properties": {"http://purl.org/dc/terms/title": "Test"}})`
2. **Expected:** No PermissionError raised. Both the model type IRI and the dcterms property IRI pass validation.

### Bozo feed handling

1. `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py::TestFeedErrorHandling -v`
2. **Expected:** Malformed XML feeds that still have entries are processed (entries extracted). Empty feeds produce zero articles.

### Module name collision

1. The test file uses `importlib.util.spec_from_file_location` to import `apps/rss-reader/app.py` as `rss_reader_app` (not `app`).
2. **Expected:** No import error. The test file successfully imports `entry_to_article`, `_mint_article_iri`, `_time_struct_to_iso`, `get_existing_article_iris` without conflicting with `backend/app/` package.

## Failure Signals

- Any test in `test_iri_prefix_fix.py` failing → the IRI prefix fix was broken or reverted
- `test_foreign_app_iri_blocked` failing → foreign app IRIs are no longer blocked (security regression)
- `test_http_url_in_params_allowed` failing → standard vocab IRIs are still being rejected (the original bug)
- `parse_manifest` raising `ValidationError` → model manifest structure is incorrect
- `parse_app_manifest` raising `ValidationError` → app manifest structure is incorrect  
- `ImportError` in `test_rss_feed_parser.py` → module name collision not handled correctly
- `test_deterministic_iri` failing → article dedup will break (same feed entry creates multiple articles)

## Requirements Proved By This UAT

- RSS-01 (partial) — poll-feeds task handler with feedparser parsing, dedup, and bulk creation. Not yet proven at runtime.
- RSS-07 (partial) — rss-feeds model created and validates. Not yet proven installable in triplestore.

## Not Proven By This UAT

- Docker integration: model install → app install → trigger poll-feeds → articles queryable in triplestore. This requires a running stack and is covered by S06 E2E tests.
- Feed polling at scheduled intervals (requires AppScheduler running).
- UI rendering of articles in object browser (requires frontend + triplestore).
- Error tracking per-feed (requires runtime context).
- FeedSubscription creation flow (S02 scope).

## Notes for Tester

- All tests run without Docker — pure unit tests with mocks.
- feedparser must be installed in the backend venv (`pip install feedparser>=6.0`). It should already be there from the app development.
- The `importlib.util` pattern in `test_rss_feed_parser.py` is intentional — see KNOWLEDGE.md entry "App module import collision in tests".
- Frontend templates are intentionally stubs (placeholder HTML). The real reader UI is S03.
- The rss-feeds model has no seed data file. This is correct — FeedSubscriptions and Articles are created by the app at runtime.
