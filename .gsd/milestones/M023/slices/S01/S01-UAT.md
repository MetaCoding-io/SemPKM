# S01: ADF converter + field mapper + Jira client + auth scaffold — UAT

**Milestone:** M023
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 delivers pure service modules and an app scaffold — no runtime behavior beyond unit tests. All 237 tests use mocks. Live runtime testing deferred to S04 (E2E with mock Jira API server).

## Preconditions

- Working directory: `/home/james/Code/SemPKM/.gsd/worktrees/M023`
- Backend venv exists: `backend/.venv/`
- Python 3.14+ available

## Smoke Test

```bash
cd backend && .venv/bin/python -m pytest tests/test_jira_adf_converter.py tests/test_jira_field_mapper.py tests/test_jira_client.py tests/test_jira_auth.py tests/test_jira_person_matcher.py -q
```
**Expected:** `237 passed` in <1s

## Test Cases

### 1. ADF→Markdown: all 12 node types convert without errors

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_adf_converter.py -v -k "not md_to_adf and not round_trip"`
2. **Expected:** All ADF→Markdown tests pass. Output includes test names for paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, rule, mediaGroup, mention, inlineCard, text marks.

### 2. ADF→Markdown: unknown node types produce placeholder

1. Run:
```python
cd backend && .venv/bin/python -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('c', '../apps/jira-sync/services/adf_converter.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
doc = {'version': 1, 'type': 'doc', 'content': [{'type': 'unknownWidget', 'attrs': {}}]}
print(repr(mod.adf_to_markdown(doc)))
"
```
2. **Expected:** Output contains `[unsupported: unknownWidget]`

### 3. Markdown→ADF round-trip preserves structure

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_adf_converter.py -v -k "round_trip"`
2. **Expected:** All round-trip tests pass, verifying that `adf_to_markdown(markdown_to_adf(md))` preserves content structure for paragraphs, headings, lists, code blocks, and links.

### 4. ADF null/empty input handling

1. Run:
```python
cd backend && .venv/bin/python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('c', '../apps/jira-sync/services/adf_converter.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print('None:', repr(mod.adf_to_markdown(None)))
print('Empty:', repr(mod.adf_to_markdown({})))
print('MD None:', repr(mod.markdown_to_adf(None)))
print('MD empty:', repr(mod.markdown_to_adf('')))
"
```
2. **Expected:** All return empty string or empty ADF doc — no crashes, no exceptions.

### 5. statusCategory.key normalization maps all 3 values

1. Run:
```python
cd backend && .venv/bin/python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('f', '../apps/jira-sync/services/field_mapper.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print('new:', mod.normalize_status('new'))
print('indeterminate:', mod.normalize_status('indeterminate'))
print('done:', mod.normalize_status('done'))
print('unknown:', mod.normalize_status('garbage'))
"
```
2. **Expected:** `new→todo`, `indeterminate→in-progress`, `done→done`, `garbage→todo` (safe default)

### 6. Priority mapping covers all Jira names

1. Run:
```python
cd backend && .venv/bin/python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('f', '../apps/jira-sync/services/field_mapper.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
for p in ['Highest','Critical','Blocker','High','Medium','Low','Lowest','Trivial']:
    print(f'{p}: {mod.normalize_priority(p)}')
print('Unknown:', mod.normalize_priority('Nonexistent'))
"
```
2. **Expected:** Highest/Critical/Blocker→`critical`, High→`high`, Medium→`medium`, Low/Lowest/Trivial→`low`, Unknown→`None`

### 7. compute_issue_slug determinism

1. Run:
```python
cd backend && .venv/bin/python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('f', '../apps/jira-sync/services/field_mapper.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
s1 = mod.compute_issue_slug('PROJ', 'PROJ-123')
s2 = mod.compute_issue_slug('PROJ', 'PROJ-123')
s3 = mod.compute_issue_slug('PROJ', 'PROJ-456')
print(f's1: {s1}')
print(f's2: {s2}')
print(f'same: {s1 == s2}')
print(f'different: {s1 != s3}')
print(f'starts with jira-: {s1.startswith(\"jira-\")}')
"
```
2. **Expected:** s1 == s2, s1 != s3, all start with `jira-`

### 8. JiraClient error hierarchy

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_client.py -v -k "error"`
2. **Expected:** Tests pass covering 401→JiraAuthError, 429→JiraRateLimitError (with retry_after), 500→JiraAPIError, network error handling.

### 9. Auth credential masking

1. Run:
```python
cd backend && .venv/bin/python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('a', '../apps/jira-sync/services/auth.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(mod._mask_token('abcdefghijklmnop'))
print(mod._mask_token('short'))
print(mod._mask_token('ab'))
"
```
2. **Expected:** Long token shows first 4 + `****` + last 4. Short tokens fully masked. Never exposes full token.

### 10. Auth base64 header construction

1. Run:
```python
cd backend && .venv/bin/python -c "
import importlib.util, base64
spec = importlib.util.spec_from_file_location('a', '../apps/jira-sync/services/auth.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
header = mod.build_auth_header('user@example.com', 'mytoken')
print(f'starts with Basic: {header.startswith(\"Basic \")}')
decoded = base64.b64decode(header.split(' ')[1]).decode()
print(f'decoded: {decoded}')
"
```
2. **Expected:** Header starts with `Basic `, decoded value is `user@example.com:mytoken`

### 11. PersonMatcher resolution cascade

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_person_matcher.py -v`
2. **Expected:** 14 tests pass covering: None→None, email SPARQL hit, Jira API fallback, externalId hit, creation on miss, cache hit, API failure graceful fallthrough, display_name-only creation.

### 12. Manifest validity

1. Run:
```python
cd backend && .venv/bin/python -c "
import yaml
m = yaml.safe_load(open('../apps/jira-sync/manifest.yaml'))
assert m['appId'] == 'jira-sync', f'wrong appId: {m[\"appId\"]}'
assert 'commands' in m['permissions'], 'missing commands permission'
assert 'network' in m['permissions'], 'missing network permission'
assert any(t['id'] == 'poll-tasks' for t in m['tasks']), 'missing poll-tasks'
assert any(t['id'] == 'push-changes' for t in m['tasks']), 'missing push-changes'
print('Manifest valid: all assertions passed')
"
```
2. **Expected:** `Manifest valid: all assertions passed`

### 13. app.py syntax and imports

1. Run:
```bash
python3 -c "import ast; ast.parse(open('apps/jira-sync/app.py').read()); print('AST valid')"
```
2. **Expected:** `AST valid`

### 14. htmx proxy prefix compliance

1. Run:
```bash
grep -n 'hx-post=\|hx-get=' apps/jira-sync/frontend/templates/*.html
```
2. Verify every htmx URL contains `/app/jira-sync/` prefix.
3. **Expected:** All 5 htmx attributes use the proxy prefix. Zero bare `/_fragments/` paths.

## Edge Cases

### Null/missing fields in Jira issue JSON

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_field_mapper.py -v -k "missing or minimal or none"`
2. **Expected:** Tests pass — build_task_properties handles missing assignee, labels, components, sprint, dueDate gracefully (omits keys rather than crashing).

### ADF table with empty cells

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_adf_converter.py -v -k "table"`
2. **Expected:** Table conversion produces valid Markdown pipe tables even with empty cells.

### Large pagination (safety limit)

1. Run: `cd backend && .venv/bin/python -m pytest tests/test_jira_client.py -v -k "max_pages"`
2. **Expected:** Pagination stops at MAX_PAGINATION_PAGES (50) even if total exceeds it — prevents infinite loops.

## Failure Signals

- Any test in the 237-test suite failing indicates a regression
- `ImportError` when loading service modules indicates missing `__init__.py` or circular imports
- htmx URLs without `/app/jira-sync/` prefix will cause 404s when app is installed (requests bypass proxy)
- `normalize_status()` returning anything other than `todo`/`in-progress`/`done` indicates broken STATUS_MAP
- `_mask_token()` exposing full token in any case is a security issue

## Requirements Proved By This UAT

- JIRA-01 (ADF→Markdown) — test cases 1, 2, 4 prove all node type handling + unknown type safety
- JIRA-02 (Markdown→ADF) — test case 3 proves round-trip fidelity
- JIRA-03 (statusCategory normalization) — test case 5 proves all 3 category keys + unknown default
- JIRA-04 (priority mapping) — test case 6 proves all 8 Jira names + unknown handling
- JIRA-05 (Jira REST client) — test case 8 proves error hierarchy
- JIRA-06 (auth) — test cases 9, 10 prove masking and header construction
- JIRA-07 (person matching) — test case 11 proves full resolution cascade
- JIRA-08 (app scaffold) — test cases 12, 13, 14 prove manifest, syntax, and proxy compliance

## Not Proven By This UAT

- Live runtime behavior (app installation, subprocess lifecycle, real Jira API calls) — deferred to S04 E2E
- Sync engine integration (pull_sync, push_sync) — S02 and S03 scope
- Full UI rendering in browser (connect form, project list display) — S04 E2E scope
- Mock Jira API server — S04 scope

## Notes for Tester

- All tests are fast (<1s total) and require no network or Docker
- The `asyncio.run()` wrapper pattern in T03 tests is a known deviation — works but non-standard
- Service modules can be tested interactively via `importlib.util.spec_from_file_location` as shown in test cases above
- If any ADF round-trip tests fail on deeply nested inline formatting, this is a known limitation of the regex-based parser — not a blocker for S02
