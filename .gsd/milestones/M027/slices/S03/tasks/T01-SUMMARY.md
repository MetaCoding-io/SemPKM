---
id: T01
parent: S03
milestone: M027
provides:
  - ImportResult dataclass with unresolved_relations field and to_dict/from_dict
  - NotionImportExecutor with two-pass execute() (objects + relations)
  - 20 unit tests covering all import paths
key_files:
  - backend/app/notion/models.py
  - backend/app/notion/executor.py
  - backend/tests/test_notion_executor.py
key_decisions:
  - Used asyncio.run() in tests instead of pytest.mark.asyncio (pytest-asyncio not installed in venv)
patterns_established:
  - Notion executor follows same two-pass structure as Obsidian executor (Pass 1 objects, Pass 2 edges)
  - Body file matching uses _strip_notion_id for case-insensitive title→file lookup
observability_surfaces:
  - SSE events: import_progress (phase/current/total), import_complete (result dict), import_error (message)
  - Persisted file: import_result.json in import directory
  - ImportResult.errors list with path+message per failed row
  - ImportResult.unresolved_relations with source_iri+relation_key+value per failed lookup
duration: 20m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: ImportResult model + NotionImportExecutor + unit tests

**Add NotionImportExecutor two-pass import engine with ImportResult model and 20 unit tests covering object creation, body matching, relation resolution, error isolation, standalone pages, and SSE broadcast**

## What Happened

Added the `ImportResult` dataclass to `models.py` with Notion-specific `unresolved_relations` field (3-tuple: source_iri, relation_key, unmatched_value) and `to_dict()`/`from_dict()` serialization. Created `executor.py` with `NotionImportExecutor` following the Obsidian executor pattern: Pass 1 iterates CSV rows per mapped database, creates objects with mapped properties via `handle_object_create`, matches body files using `_strip_notion_id` for case-insensitive title lookup, and builds a `title_index` dict. Pass 2 re-reads CSVs, splits comma-separated relation cells, resolves targets by title→IRI lookup, and creates edges via `handle_edge_create` with batch commits every 10. Standalone pages are imported when `standalone_page_type_iri` is configured. SSE progress events fire throughout both phases. The catastrophic-error outer try/except broadcasts `import_error`. Result is persisted as `import_result.json`.

Wrote 20 unit tests covering: serialization round-trip (4), Pass 1 object creation with properties (5), Pass 2 relation resolution (3), error isolation (1), standalone pages (2), body file matching with Notion IDs (2), and SSE broadcast events (3).

## Verification

- `cd backend && python -m pytest tests/test_notion_executor.py -v` → 20/20 passed
- `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v` → 49/49 passed (zero regressions)
- `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"` → no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"` → no syntax errors
- `grep -rn "^<<<<<<< " backend/app/notion/ backend/tests/test_notion_executor.py` → zero conflict markers

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -m pytest tests/test_notion_executor.py -v` | 0 | ✅ pass | 0.5s |
| 2 | `python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v` | 0 | ✅ pass | 0.5s |
| 3 | `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"` | 0 | ✅ pass | <1s |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/notion/models.py').read())"` | 0 | ✅ pass | <1s |
| 5 | `grep -rn "^<<<<<<< " backend/app/notion/ backend/tests/test_notion_executor.py` | 1 | ✅ pass (no matches) | <1s |

### Slice-level checks (partial — T01 is intermediate task)

| # | Slice Check | Status | Notes |
|---|-------------|--------|-------|
| 1 | executor tests pass | ✅ | 20/20 |
| 2 | existing tests zero regressions | ✅ | 49/49 |
| 3 | executor.py AST parse | ✅ | |
| 4 | router.py AST parse | ⏳ | T02 (not yet created) |
| 5 | Jinja2 templates parse | ⏳ | T02 |
| 6 | Zero conflict markers | ✅ | |

## Diagnostics

- Inspect import results: `cat /app/data/imports/notion/{user_id}/{timestamp}/import_result.json`
- SSE event stream: connect to `/browser/notion/{import_id}/execute/stream` for real-time progress
- Per-row errors: `result.errors` list in import_result.json with path and message
- Unresolved relations: `result.unresolved_relations` with source IRI, relation key, and unmatched value
- Executor logging: `docker compose logs api | grep "Import error"` for per-row failures

## Deviations

- Used `asyncio.run()` wrapper in tests instead of `@pytest.mark.asyncio` decorator — pytest-asyncio is not installed in the venv (only anyio is available). This matches the pattern used in existing `test_notion_scanner.py`.
- Relaxed `duration_seconds > 0` assertion to `>= 0` — execution completes in under 10ms with mocks, rounding to 0.00.

## Known Issues

None.

## Files Created/Modified

- `backend/app/notion/models.py` — Added `ImportResult` dataclass with `unresolved_relations`, `to_dict()`, `from_dict()`
- `backend/app/notion/executor.py` — New file: `NotionImportExecutor` with two-pass `execute()` method (~290 lines)
- `backend/tests/test_notion_executor.py` — New file: 20 unit tests across 6 test classes (~760 lines)
