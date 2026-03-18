# S01: Platform fix + Mental Model + App data pipeline — UAT

**Milestone:** M010
**Written:** 2026-03-18

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 delivers code artifacts (SDK fix, model files, app skeleton, unit tests) — no live runtime UI to verify. Docker integration deferred to S02. All verification is via unit tests, manifest validation, and JSON-LD integrity checks.

## Preconditions

- Backend venv exists at `backend/.venv` with pytest, feedparser, and project dependencies installed
- Working directory is the M010 worktree
- No Docker stack required (all tests are offline)

## Smoke Test

Run both test suites:
```
cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py tests/test_rss_feed_parser.py -v
```
Expected: 51 tests pass (13 IRI prefix + 38 feed parser) in <1s.

## Test Cases

### 1. IRI prefix whitelist — model type IRIs pass validation

1. Run: `cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_model_type_iri_passes -v`
2. **Expected:** Test passes — `urn:sempkm:model:rss-feeds:Article` is accepted by `_check_iri_prefix()` for app `rss-reader`

### 2. IRI prefix whitelist — foreign app IRIs blocked

1. Run: `cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_foreign_app_iri_blocked -v`
2. **Expected:** Test passes — `urn:sempkm:app:other-app:thing` raises `PermissionError` with message containing both the offending IRI and the app's required prefix

### 3. IRI prefix whitelist — standard vocabulary IRIs pass

1. Run: `cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_standard_http_vocab_passes -v`
2. **Expected:** Test passes — `http://www.w3.org/1999/02/22-rdf-syntax-ns#type` passes validation

### 4. rss-feeds model manifest validates

1. Run: `cd backend && .venv/bin/python3 -c "from app.models.manifest import parse_manifest; from pathlib import Path; m = parse_manifest(Path('../models/rss-feeds')); print(f'{m.modelId} v{m.version}')"`
2. **Expected:** Prints `rss-feeds v1.0.0` with no errors

### 5. rss-feeds ontology contains Article and FeedSubscription classes

1. Run: `python3 -c "import json; data = json.load(open('models/rss-feeds/ontology/rss-feeds.jsonld')); classes = [e['@id'] for e in data['@graph'] if e.get('@type') == 'owl:Class']; print(classes)"`
2. **Expected:** Output includes `rss:Article` and `rss:FeedSubscription`

### 6. rss-feeds shapes have sufficient properties

1. Run: `python3 -c "import json; data = json.load(open('models/rss-feeds/shapes/rss-feeds.jsonld')); shapes = [e for e in data['@graph'] if e.get('@type') == 'sh:NodeShape']; print([(s['@id'], len(s.get('sh:property', []))) for s in shapes])"`
2. **Expected:** ArticleShape has ≥9 properties, FeedSubscriptionShape has ≥8 properties

### 7. rss-reader app manifest validates with poll-feeds task

1. Run: `cd backend && .venv/bin/python3 -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); print(f'{m.appId} v{m.version}, tasks: {[t.id for t in m.tasks]}')"`
2. **Expected:** Prints `rss-reader v1.0.0, tasks: ['poll-feeds']`

### 8. rss-reader app.py is syntactically valid

1. Run: `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read()); print('OK')"`
2. **Expected:** Prints `OK` with no SyntaxError

### 9. entry_to_article produces deterministic article IRIs

1. Run: `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py::TestArticleIRIDeterminism -v`
2. **Expected:** All 7 determinism tests pass — same inputs produce same IRIs, different inputs produce different IRIs

### 10. RSS 2.0 entry parsing maps fields correctly

1. Run: `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py::TestRSS2EntryMapping -v`
2. **Expected:** 4 tests pass — title, link, author, published date, summary all mapped to correct article properties

### 11. Atom entry parsing handles missing published date

1. Run: `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py::TestAtomEntryMapping::test_atom_entry_no_published_uses_none -v`
2. **Expected:** Test passes — missing `published_parsed` produces `None` for created date, not an error

### 12. Error handling: bozo feed with no entries

1. Run: `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py::TestErrorHandling -v`
2. **Expected:** 4 tests pass — bozo feeds handled gracefully, empty feeds produce zero articles, no subscriptions returns `{feeds_polled: 0, articles_created: 0}`

### 13. poll-feeds task flow with mocked SDK

1. Run: `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py::TestBulkCommandAssembly -v`
2. **Expected:** 3 tests pass — article dicts have required keys, bulk.add called per article, dedup filters existing articles

## Edge Cases

### PermissionError message content

1. Run: `cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_error_message_includes_offending_iri_and_prefix -v`
2. **Expected:** Test passes — error message includes the literal string of the blocked IRI and the expected prefix

### Completely empty feed entry

1. Run: `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py::TestMissingFields::test_completely_empty_entry -v`
2. **Expected:** Test passes — entry with no title, no link, no author still produces a valid article dict (with empty/None values, not an exception)

### Entry with link as fallback ID

1. Run: `cd backend && uv run python -m pytest tests/test_rss_feed_parser.py::TestRealisticEntry::test_entry_with_link_as_fallback_id -v`
2. **Expected:** Test passes — when `entry.id` is missing, `entry.link` is used as the identifier for IRI minting

### Non-IRI strings ignored

1. Run: `cd backend && uv run python -m pytest tests/test_iri_prefix_fix.py::TestIRIPrefixWhitelist::test_non_iri_strings_ignored -v`
2. **Expected:** Test passes — plain text values like "hello world" in command params are not treated as IRIs and not checked

## Failure Signals

- Any test in `test_iri_prefix_fix.py` failing → IRI prefix whitelist regression; `_check_iri_prefix()` was modified incorrectly
- `test_foreign_app_iri_blocked` failing → sandboxing broken; foreign app IRIs should not pass
- `parse_manifest` raising `ValidationError` → model manifest has structural issues (missing fields, wrong types)
- `parse_app_manifest` raising `ValidationError` → app manifest has structural issues
- JSON parse errors on any `.jsonld` file → malformed JSON-LD (missing commas, brackets, etc.)
- `SyntaxError` from `ast.parse(app.py)` → Python syntax error in app code
- `ImportError` when running feed parser tests → feedparser not installed or importlib path wrong

## Requirements Proved By This UAT

- APP-05 (partial) — IRI prefix enforcement correctly scoped: model types pass, foreign app IRIs blocked (13 unit tests)
- RSS-07 (partial) — rss-feeds model validates with Article and FeedSubscription types, OWL ontology, SHACL shapes, ViewSpecs
- RSS-01 (partial) — poll-feeds task handler parses feeds and creates articles via bulk commands (38 unit tests with mocked SDK)

## Not Proven By This UAT

- Docker integration (model install → app start → poll-feeds → articles in triplestore) — deferred to S02
- Reader UI rendering — templates are stubs, S03 builds real UI
- Feed subscription management UI — S02 implements subscribe/unsubscribe
- Workspace views and command palette entries — UI stubs only, S04 implements
- OPML import — S05
- Live polling behavior (scheduler triggering poll-feeds on 5m interval) — requires Docker stack

## Notes for Tester

- All tests run offline without Docker — just the backend venv is needed.
- If `feedparser` is not installed in the backend venv, run: `cd backend && .venv/bin/pip install feedparser`
- The test file `test_rss_feed_parser.py` uses `importlib.util.spec_from_file_location` to avoid the `backend/app/` name collision — this is intentional, not a hack (documented as Knowledge Pattern #2).
- Model and app manifests can also be validated via the Docker stack's admin UI once S02 proves integration.
