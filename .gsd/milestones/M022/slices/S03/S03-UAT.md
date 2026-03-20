# S03: Push sync + section-based status moves — UAT

**Milestone:** M022
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Push sync is fully unit-tested with 59 new tests. E2E runtime testing deferred to S04.

## Preconditions

- Working directory: `.gsd/worktrees/M018/`
- Python environment: `uv` available for running pytest from `backend/`

## Smoke Test

```
cd backend && uv run pytest tests/test_asana_field_mapper.py tests/test_asana_sync_engine.py -q
```
Expected: 209 passed, 0 failed.

## Test Cases

### 1. Reverse status mapping (3 modes)
1. `uv run pytest tests/test_asana_field_mapper.py -q -k TestReverseStatusMapping`
2. **Expected:** All pass — custom_field→enum name, section→section name, completed_only→bool, unknown→None.

### 2. Build PATCH body with GID resolution
1. `uv run pytest tests/test_asana_field_mapper.py -q -k TestBuildAsanaPatch`
2. **Expected:** All pass — title, status, priority patches, section-mode exclusion, unknown values skipped.

### 3. Section GID resolution
1. `uv run pytest tests/test_asana_field_mapper.py -q -k TestResolveSectionGidForStatus`
2. **Expected:** All pass — successful resolution, unknown status→None, empty sections.

### 4. Push sync guards
1. `uv run pytest tests/test_asana_sync_engine.py -q -k "test_push_skip_not_connected or test_push_pull_only_skip"`
2. **Expected:** Both pass. last_push_result has status "skipped".

### 5. Push sync — custom field PATCH path
1. `uv run pytest tests/test_asana_sync_engine.py -q -k "test_push_custom_field"`
2. **Expected:** patch_task called with correct custom_fields body.

### 6. Push sync — section move path
1. `uv run pytest tests/test_asana_sync_engine.py -q -k "test_push_section_move"`
2. **Expected:** add_task_to_section called with resolved section GID.

### 7. Push sync — per-task error isolation
1. `uv run pytest tests/test_asana_sync_engine.py -q -k "test_push_per_task_error"`
2. **Expected:** One task failure doesn't block others. error_details includes task IRI, GID, error.

### 8. Diagnostic surface
1. `uv run pytest tests/test_asana_sync_engine.py -q -k "test_push_result_stored"`
2. **Expected:** last_push_result contains status, pushed, errors fields.

### 9. Syntax checks
1. `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"`
2. `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/sync_engine.py').read())"`
3. `python3 -c "import ast; ast.parse(open('apps/asana-sync/app.py').read())"`
4. **Expected:** All succeed.

### 10. Template structure
1. `grep -c 'hx-post="/app/asana-sync/' apps/asana-sync/frontend/templates/connect_status.html` → ≥6
2. `grep -c 'stat-group\|stat-row' apps/asana-sync/frontend/templates/connect_status.html` → ≥12
3. `grep 'push_sync' apps/asana-sync/app.py` → 3 matches (import, handler, route)

## Edge Cases

### Mixed push (section status + priority on same task)
1. `uv run pytest tests/test_asana_sync_engine.py -q -k "test_push_mixed"`
2. **Expected:** Both add_task_to_section and patch_task called for same task.

### No changed tasks
1. `uv run pytest tests/test_asana_sync_engine.py -q -k "test_push_no_changed"`
2. **Expected:** pushed=0, status="ok".

## Failure Signals

- Any test failure in the two Asana test files
- SyntaxError from ast.parse
- Missing push_sync references in app.py
- Template missing stat-group/stat-row or htmx URLs without `/app/asana-sync/` prefix

## Requirements Proved By This UAT

- Push sync pipeline (both PATCH and section move paths), reverse field mapping, settings UI structure, diagnostic surfaces

## Not Proven By This UAT

- E2E runtime against Docker stack (S04)
- Visual verification of settings UI (S04)
- Real Asana API interaction (always mocked)

## Notes for Tester

- All tests run from `backend/` directory
- Template htmx URLs MUST use `/app/asana-sync/` prefix per KNOWLEDGE.md
