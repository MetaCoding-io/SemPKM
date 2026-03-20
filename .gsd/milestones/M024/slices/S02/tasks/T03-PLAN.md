---
estimated_steps: 5
estimated_files: 1
---

# T03: Column mapping route unit tests

**Slice:** S02 — Column mapping configuration UI + pull sync
**Milestone:** M024

## Description

Create `test_monday_column_mapping.py` with 50+ unit tests proving the column mapping UI routes, type compatibility filtering, label discovery from `settings_str`, client extension for groups and subitems, and error paths. Uses the importlib loading pattern established in S01 tests and the mock client pattern from the Jira sync tests.

**Relevant skills:** Load the `test` skill for test generation patterns.

## Steps

1. **Create file with importlib module loading.** Path: `backend/tests/test_monday_column_mapping.py`. Load modules in dependency order using the importlib pattern from `test_monday_field_mapper.py`:
   ```python
   _SERVICES_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "monday-sync" / "services"
   _APP_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "monday-sync"
   ```
   Load: `monday_client.py` (for MondayClient class, error classes), `auth.py`, `field_mapper.py`, `app.py` (for route handler functions, COLUMN_TYPE_COMPATIBILITY, BPKM_PROPERTY_LABELS, BPKM_STATUS_VALUES, BPKM_PRIORITY_VALUES).

   **Important:** The app module uses `from sempkm_app_sdk import App, AppContext` and `from starlette.requests import Request` which won't be available in test context. Instead of loading the full app.py module, extract and test the constants and helper functions directly. For route handler testing, use mock request/response patterns or test the logic extracted into helpers.

   **Alternative approach:** Test the constants and type-compatibility filtering as pure logic (COLUMN_TYPE_COMPATIBILITY dict lookups). Test the route handlers by constructing mock Request objects with form data, mock AppContext, and calling the handler functions directly. Follow the pattern from `test_monday_auth.py` or similar S01 test files.

2. **Build mock clients.** Create `MockStateClient`, `MockSettingsClient`, `MockHttpClient`, `MockGraphClient` classes following the Jira test pattern:
   - `MockStateClient`: in-memory key-value store with async `get()` / `set()` methods
   - `MockSettingsClient`: same pattern for settings
   - `MockHttpClient`: tracks requests, returns configurable MockResponse objects
   - `MockGraphClient`: returns SPARQL results by pattern matching (not needed for most column mapping tests but needed for completeness)

   Also create a `MockMondayClient` that returns configurable board columns:
   ```python
   class MockMondayClient:
       def __init__(self, columns=None, subitems=None, items=None):
           self.columns = columns or []
           self.subitems = subitems or []
           self.items = items or []
       
       async def get_board_columns(self, board_id):
           return self.columns
       
       async def get_board_items(self, board_id, limit=100, cursor=None):
           return {"items": self.items, "cursor": None}
       
       async def get_subitems(self, item_ids):
           return self.subitems
   ```

3. **Test COLUMN_TYPE_COMPATIBILITY filtering logic.** 10+ tests:
   - `taskStatus` only matches `status` type columns
   - `priority` matches `status` and `color` type columns
   - `dueDate` matches `date` and `timeline` columns
   - `assignedTo` matches only `people` columns
   - `description` matches `text` and `long_text` columns
   - `estimatedEffort` matches only `numbers` columns
   - `tags` matches `tags` and `dropdown` columns
   - Non-compatible column types are excluded
   - Empty column list returns empty compatible sets
   - All bpkm properties in BPKM_PROPERTY_LABELS have entries in COLUMN_TYPE_COMPATIBILITY

4. **Test column mapping save/load.** 15+ tests:
   - Save mapping for board — JSON stored in settings as `column_mapping_{board_id}`
   - Save mapping with all properties mapped
   - Save mapping with some properties empty (only non-empty saved)
   - Load existing mapping — pre-selects correct dropdowns
   - Multiple boards have independent mappings
   - Board ID is correctly passed through hidden form field
   - Missing board_id returns error
   - Empty columns (board with no columns) handled gracefully

5. **Test label discovery from `settings_str`.** 15+ tests:
   - Parse `settings_str` with labels: `{"labels": {"0": "", "1": "Working on it", "2": "Done"}}` → extracts 3 labels
   - Empty string label shows as "Default / Not Started" in the labels list
   - Malformed `settings_str` (not valid JSON) → returns empty labels
   - Missing `labels` key in settings_str → returns empty labels
   - `settings_str` is None → returns empty labels
   - `settings_str` is empty string → returns empty labels
   - Priority column settings_str parsed independently from status
   - Save label mapping — JSON stored as `label_mapping_{board_id}`
   - Save label mapping with status and priority separately
   - Load existing label mapping — pre-selects correct values
   - No status column mapped → configure-labels shows no status section
   - No priority column mapped → configure-labels shows no priority section

6. **Test MondayClient extensions.** 10+ tests:
   - `get_board_items` query includes `group { id title }`
   - Items returned include group data
   - `get_subitems(item_ids)` returns subitems with parent_item_id
   - `get_subitems` with empty item_ids returns empty list
   - `get_subitems` handles items with no subitems
   - Subitem dicts include `id`, `name`, `group`, `column_values`

## Must-Haves

- [ ] Test file at `backend/tests/test_monday_column_mapping.py`
- [ ] Uses importlib loading pattern (no package installation required)
- [ ] 50+ tests total
- [ ] COLUMN_TYPE_COMPATIBILITY filtering tests
- [ ] Column mapping save/load tests
- [ ] Label discovery from settings_str tests (including edge cases: empty, malformed, None)
- [ ] MondayClient extension tests (group in items query, get_subitems)
- [ ] All tests pass: `cd backend && .venv/bin/python3 -m pytest tests/test_monday_column_mapping.py -v`
- [ ] Existing S01 tests still pass

## Verification

- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_column_mapping.py -v` — 50+ tests pass
- `cd backend && .venv/bin/python3 -m pytest tests/test_monday_auth.py tests/test_monday_client.py tests/test_monday_field_mapper.py tests/test_monday_person_matcher.py tests/test_monday_column_mapping.py -v` — 327+ tests pass (277 S01 + 50+ S02)
- `wc -l backend/tests/test_monday_column_mapping.py` — substantial file (600+ lines)

## Inputs

- `apps/monday-sync/app.py` — T01 output with COLUMN_TYPE_COMPATIBILITY, BPKM_PROPERTY_LABELS, BPKM_STATUS_VALUES, BPKM_PRIORITY_VALUES constants and 4 column mapping routes
- `apps/monday-sync/services/monday_client.py` — T01 output with get_board_items (group field) and get_subitems method
- `backend/tests/test_monday_field_mapper.py` — reference for importlib loading pattern and test structure
- `backend/tests/test_monday_client.py` — reference for MockResponse and MondayClient test patterns
- `backend/tests/test_jira_sync_engine.py` — reference for MockStateClient, MockSettingsClient, MockHttpClient patterns

## Observability Impact

- **Test-time signals:** 107 unit tests covering column mapping routes, type compatibility, label parsing, and MondayClient extensions. Error-path tests (14 selected via `-k "error or malformed or missing"`) verify failure visibility for missing board_id, malformed settings_str, API errors, and auth failures.
- **Inspection:** Run `pytest tests/test_monday_column_mapping.py -v` to see per-test pass/fail. Use `-k` filtering to isolate specific test sections (e.g., `-k "label"` for label parsing, `-k "subitem"` for subitem tests).
- **Failure visibility:** Test failures surface as pytest assertion errors with descriptive messages. The constants extraction approach (parsing app.py source) will break visibly if constant definitions change format.

## Expected Output

- `backend/tests/test_monday_column_mapping.py` — NEW: 50+ tests, 600+ lines
