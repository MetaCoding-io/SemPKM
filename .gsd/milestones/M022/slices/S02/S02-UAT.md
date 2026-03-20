# S02: Pull sync with configurable field transforms + subtask nesting — UAT

**Milestone:** M022
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All three modules are pure functions or use injected dependencies — no runtime infrastructure needed. 168 unit tests with mocks prove every transform path, sync orchestration flow, and edge case.

## Preconditions

- Python 3.11+ with backend/.venv activated
- `markdownify` package available (optional — field mapper falls back to regex strip if missing)
- No Docker, triplestore, or running server needed

## Smoke Test

```bash
cd /home/james/Code/SemPKM/.gsd/worktrees/M018
backend/.venv/bin/pytest backend/tests/test_asana_field_mapper.py backend/tests/test_asana_person_matcher.py backend/tests/test_asana_sync_engine.py -v --noconftest
```

Expected: 168 tests pass in <1s. Zero failures.

## Test Cases

### 1. All three status modes produce correct bpkm:taskStatus

1. Run `pytest backend/tests/test_asana_field_mapper.py -k "test_completed_only_mode or test_custom_field_status or test_section_status" -v --noconftest`
2. **Expected:** All 3 tests pass. completed_only maps `completed=True` → "done". custom_field reads enum field by GID and maps via status_mapping. section maps section_name via status_mapping.

### 2. Priority extraction from custom field

1. Run `pytest backend/tests/test_asana_field_mapper.py -k "test_priority" -v --noconftest`
2. **Expected:** Tests pass. Priority extracted from custom_fields array by matching priority_field_gid, enum_value.name looked up in priority_mapping dict.

### 3. Milestone detection via resource_subtype

1. Run `pytest backend/tests/test_asana_field_mapper.py -k "test_milestone" -v --noconftest`
2. **Expected:** Tests pass. Tasks with `resource_subtype: "milestone"` return `bpkm:Milestone` type IRI.

### 4. HTML→Markdown conversion

1. Run `pytest backend/tests/test_asana_field_mapper.py -k "test_html" -v --noconftest`
2. **Expected:** Tests pass. `html_notes` field converted to markdown. Falls back to plain `notes` when no html_notes present.

### 5. Subtask recursion at multiple depths

1. Run `pytest backend/tests/test_asana_sync_engine.py -k "TestPullSyncSubtasks" -v --noconftest`
2. **Expected:** 4 tests pass. 1-level subtasks created. 3-level deep nesting works. Max depth (5) enforced — recursion stops at boundary. Subtask→parent edge uses dcterms:isPartOf.

### 6. Per-task error isolation

1. Run `pytest backend/tests/test_asana_sync_engine.py -k "TestPullSyncErrorIsolation" -v --noconftest`
2. **Expected:** 3 tests pass. One task failing doesn't block other tasks. API errors on a project produce partial results. Error details contain task_gid and project_gid.

### 7. Incremental sync via modified_since

1. Run `pytest backend/tests/test_asana_sync_engine.py -k "TestPullSyncIncremental" -v --noconftest`
2. **Expected:** 2 tests pass. When last_sync_at exists, modified_since parameter is passed to client. First sync sends None.

### 8. Person matcher email lookup and cache

1. Run `pytest backend/tests/test_asana_person_matcher.py -v --noconftest`
2. **Expected:** 18 tests pass. Email found → returns existing IRI (no creation). Email not found → creates Person via command API. Second call for same email → cache hit (no SPARQL query). Null/empty email → returns None.

### 9. Diagnostic surface: last_pull_result stored

1. Run `pytest backend/tests/test_asana_sync_engine.py -k "test_last_pull_result_stored" -v --noconftest`
2. **Expected:** 1 test passes. Stored JSON contains `created`, `errors`, `duration_ms`, `timestamp` keys.

### 10. Guard conditions prevent sync

1. Run `pytest backend/tests/test_asana_sync_engine.py -k "TestPullSyncGuards" -v --noconftest`
2. **Expected:** 4 tests pass. Not connected → skips. No selected_projects key → skips. Empty selected_projects → skips. Skipped result stored in state.

### 11. Syntax validity of all source files

1. Run:
   ```bash
   python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read()); print('OK')"
   python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read()); print('OK')"
   python3 -c "import ast; ast.parse(open('apps/asana-sync/services/person_matcher.py').read()); print('OK')"
   python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read()); print('OK')"
   ```
2. **Expected:** All 4 print "OK" with exit code 0.

## Edge Cases

### Status fallback when custom field value not in mapping

1. Run `pytest backend/tests/test_asana_field_mapper.py -k "test_custom_field_status_no_match" -v --noconftest`
2. **Expected:** Falls back to completed boolean mapping when custom field enum_value.name is not in status_mapping dict.

### Slug computation from Asana GID

1. Run `pytest backend/tests/test_asana_field_mapper.py -k "test_slug" -v --noconftest`
2. **Expected:** Slug is `asana-{gid}` format. Stable across repeated calls.

### Tag extraction from empty tags array

1. Run `pytest backend/tests/test_asana_field_mapper.py -k "test_tags_empty" -v --noconftest`
2. **Expected:** Empty tags array produces no tag properties (not a crash).

### Loop prevention skips unchanged tasks

1. Run `pytest backend/tests/test_asana_sync_engine.py -k "test_loop_prevention" -v --noconftest`
2. **Expected:** Tasks with lastSyncedAt >= modified_at are skipped to prevent re-importing pushed changes.

## Failure Signals

- Any test failure in the 168-test suite
- `ast.parse()` raising SyntaxError on any source file
- Missing `created`/`errors`/`duration_ms` keys in last_pull_result diagnostic output
- Import errors suggesting missing dependencies (markdownify is optional — should fall back gracefully)
- Subtask tests failing with recursion depth errors (would indicate unbounded recursion)

## Requirements Proved By This UAT

- ASANA-05 (pull sync) — tests prove task creation with all mapped fields
- ASANA-06 (subtask nesting) — tests prove 5-level bounded recursion with parent linking
- ASANA-07 (tag mapping) — field mapper tests prove tag extraction
- ASANA-08 (follower mapping) — person matcher tests prove email lookup and creation

## Not Proven By This UAT

- Push sync (S03 scope)
- Section-based status moves (S03 scope)
- Live runtime against real Asana API (mock-only)
- E2E integration through Docker stack (S04 scope)
- Settings UI for sync direction/interval (S03 scope)

## Notes for Tester

- All tests use `--noconftest` to run without the shared backend test fixtures — they're fully self-contained with inline mocks.
- The `_PatchedPullSync` context manager in sync engine tests monkeypatches AsanaClient to return canned data. This is intentional — it isolates sync logic from HTTP.
- Person matcher is a near-identical clone of the Linear version. If you've already verified the Linear person matcher pattern, focus testing here on the field mapper's configurable transforms, which are the novel piece.
