# S01: Auth + GraphQL client + field mapper + person matcher — UAT

**Milestone:** M024
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All S01 deliverables are offline service modules tested via importlib loading with mocks. No runtime, Docker, or UI interaction needed — contract verification via 277 unit tests proves all interfaces.

## Preconditions

- Working directory: `/home/james/Code/SemPKM/.gsd/worktrees/M023`
- Python venv available at `backend/.venv/`
- No Docker stack required — all tests use importlib and mocks

## Smoke Test

```bash
cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py tests/test_monday_client.py tests/test_monday_field_mapper.py tests/test_monday_person_matcher.py -v --tb=short
```
Expected: 277 tests pass in under 5 seconds.

## Test Cases

### 1. Auth credential lifecycle

1. Run `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py -v`
2. **Expected:** 31 tests pass covering:
   - `store_credentials` stores token as `monday_api_token` in state
   - `get_credentials` returns `{"api_token": "..."}` or None when empty
   - `clear_credentials` removes the state key
   - `verify_connection` calls `me` query and returns `(True, user_data)` on success
   - `verify_connection` returns `(False, error_msg)` on API failure
   - `get_connection_status` returns dict with `connected=True`, `display_name`, `email`, `token_preview` when credentials valid
   - `get_connection_status` returns `connected=False` when no credentials
   - `_mask_token` masks to `first4+****+last4` for tokens > 8 chars

### 2. GraphQL client error hierarchy and convenience methods

1. Run `cd backend && .venv/bin/python3 -m pytest tests/test_monday_client.py -v`
2. **Expected:** 64 tests pass covering:
   - Auth header is bare `Authorization: <token>` (no Bearer prefix)
   - HTTP 401 → `MondayAuthError` with status_code=401
   - HTTP 429 → `MondayRateLimitError` with parsed `retry_after`
   - 200 with complexity error → `MondayComplexityError` with `reset_in_seconds`
   - `get_boards()` returns list of board dicts
   - `get_board_columns(board_id)` returns column metadata
   - `get_board_items(board_id)` handles cursor pagination
   - `get_all_board_items()` paginates with MAX_PAGINATION_PAGES=50 safety
   - `change_multiple_column_values()` sends correct mutation
   - `create_item()` sends correct mutation
   - `MONDAY_API_URL` env var overrides default endpoint

### 3. Field mapper configurable column extraction

1. Run `cd backend && .venv/bin/python3 -m pytest tests/test_monday_field_mapper.py -v`
2. **Expected:** 155 tests pass covering:
   - Status column: extracts `label` field, maps via `status_label_mapping`
   - Priority column: extracts `label`, maps via `priority_label_mapping`, None for unknown
   - Date column: extracts `date` field as ISO string
   - People column: extracts first `personsAndTeams[0].id`
   - Text/long_text: extracts `text` or `value` field
   - Numbers: extracts `value` as string
   - Tags: extracts `tag_ids` list
   - Dropdown: extracts `labels` list
   - Missing columns handled gracefully (no exceptions)
   - `build_reverse_column_values` produces correct write format per type
   - `compute_slug("My Task", "12345")` produces deterministic `monday-{sha256[:16]}`

### 4. Person matcher resolution cascade

1. Run `cd backend && .venv/bin/python3 -m pytest tests/test_monday_person_matcher.py -v`
2. **Expected:** 27 tests pass covering:
   - `resolve_person(None, ...)` returns None
   - Email provided → SPARQL lookup via foaf:mbox/crm:email → returns Person IRI
   - No email → fetches from Monday.com API → then SPARQL lookup
   - No SPARQL match → externalId fallback
   - Full miss → creates new Person with name/email/externalId
   - Cache hit on second call with same user_id
   - API failure → graceful handling, falls through to create
   - `_slugify` handles unicode, special chars, empty strings

### 5. App scaffold completeness

1. Run `ls apps/monday-sync/manifest.yaml apps/monday-sync/requirements.txt apps/monday-sync/services/__init__.py apps/monday-sync/services/auth.py apps/monday-sync/services/monday_client.py apps/monday-sync/services/field_mapper.py apps/monday-sync/services/person_matcher.py apps/monday-sync/app.py apps/monday-sync/frontend/templates/connect.html apps/monday-sync/frontend/templates/connect_status.html apps/monday-sync/frontend/static/styles.css`
2. **Expected:** All 11 files exist.

### 6. Python syntax validation

1. Run `find apps/monday-sync -name "*.py" -exec python3 -c "import ast; ast.parse(open('{}').read())" \;`
2. **Expected:** No syntax errors — all files parse cleanly.

### 7. Manifest structure

1. Run `python3 -c "import yaml; m = yaml.safe_load(open('apps/monday-sync/manifest.yaml')); assert m['appId'] == 'monday-sync'; assert 'api.monday.com' in m['network']; assert 'poll-tasks' in [t['id'] for t in m['tasks']]; print('OK')"`
2. **Expected:** Prints "OK" — manifest has correct appId, network domain, and task definitions.

## Edge Cases

### Missing API token returns disconnected status

1. Create a mock StateClient that returns None for `get_state("monday_api_token")`
2. Call `get_connection_status(state, client)`
3. **Expected:** Returns `{"connected": False, "display_name": None, "email": None, "token_preview": None, "error": None}`

### Complexity error detected by message keyword fallback

1. In test_monday_client.py, the test `test_complexity_error_by_message_keyword` verifies this
2. **Expected:** Response with `errors: [{message: "Query has complexity of ..."}]` raises `MondayComplexityError`

### Column value as JSON string vs pre-parsed dict

1. In test_monday_field_mapper.py, `TestParseColValue` covers JSON string, dict, None, empty string, null string
2. **Expected:** All shapes normalize correctly before type-specific extraction

### Person matcher with numeric user_id vs string cache key

1. In test_monday_person_matcher.py, `test_cache_key_is_string_of_user_id` verifies int 12345 and string "12345" resolve the same way
2. **Expected:** Cache key is always `str(user_id)`, so repeated calls with int or string hit the cache

## Failure Signals

- Any of the 277 tests failing indicates a broken service contract
- `ast.parse()` failure on any .py file means syntax corruption
- Missing files in `apps/monday-sync/` means incomplete scaffold
- `MondayApiError` hierarchy tests failing means error handling won't work at runtime
- Field mapper round-trip tests failing means push sync will produce incorrect column values

## Requirements Proved By This UAT

- MON-01 (auth) — credential storage, verification, masked display proven by 31 auth tests
- MON-02 (board discovery) — `get_boards()` and `get_board_columns()` proven by client tests; board selection UI exists in template
- MON-13 (person matching) — full resolution cascade proven by 27 person matcher tests

## Not Proven By This UAT

- MON-03 through MON-12 — column mapping UI, pull sync, push sync, LoopGuard, dependencies, groups, subitems, tags (S02-S04)
- MON-14 — E2E test and mock server (S04)
- MON-15 — user guide (S04)
- Runtime integration — all tests use mocks; actual Monday.com API, Docker deployment, and UI interaction not tested

## Notes for Tester

- All tests run offline with importlib loading — no Docker stack, no network, no Monday.com API key needed
- The `backend/.venv` must exist with pytest installed; run from `backend/` directory
- Field mapper tests are comprehensive (155 tests) and exercise every column type with multiple input shapes — if these pass, the data transformation layer is solid
- The connect_status.html template references MondayClient methods that are imported in app.py — the template will render correctly when the app is actually running, but template rendering is not tested in S01 (deferred to S02/S04 integration)
