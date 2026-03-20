---
id: T02
parent: S01
milestone: M023
provides:
  - "Jira field mapper: STATUS_MAP, PRIORITY_MAP, REVERSE_STATUS_MAP, REVERSE_PRIORITY_MAP"
  - "build_task_properties(issue, person_iri, sync_time) → bpkm property dict from Jira issue JSON"
  - "build_milestone_properties(epic, sync_time) → bpkm property dict for Epic→Milestone mapping"
  - "compute_issue_slug(project_key, issue_key) → deterministic jira-{hash16} slug"
  - "build_issue_patch(task_props) → Jira update body (title + priority only per D237)"
  - "normalize_status(), normalize_priority(), reverse_status(), reverse_priority() helper functions"
key_files:
  - apps/jira-sync/services/field_mapper.py
  - backend/tests/test_jira_field_mapper.py
key_decisions:
  - "D233/D235: statusCategory.key normalization — new→todo, indeterminate→in-progress, done→done"
  - "D237: Push sync limited to title/priority for v1 — no status transitions (requires transition IDs)"
  - "Status name stored in bpkm:externalStatus for display, not used for status mapping"
  - "Labels and components both merged into bpkm:tags (labels first, then components)"
patterns_established:
  - "Jira issue field access supports both nested {fields: {...}} and flat dict shapes"
  - "External URL constructed from issue self link (urlparse to extract site base)"
  - "_make_issue() and _make_epic() test fixtures replace (not merge) fields when fields= kwarg is passed"
observability_surfaces:
  - "Pure module — no runtime state, logging, or side effects"
  - "Inspect via direct function calls: normalize_status('key'), normalize_priority('name')"
  - "Unknown statusCategory keys default to 'todo'; unknown priority names return None"
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Build field mapper with statusCategory normalization and 74 unit tests

**Implemented Jira field mapper with STATUS_MAP/PRIORITY_MAP/reverse maps, build_task_properties, build_milestone_properties, compute_issue_slug, and build_issue_patch — 74 passing tests covering all mapping paths including round-trip consistency and lossy mapping verification.**

## What Happened

Built `apps/jira-sync/services/field_mapper.py` as a pure Python module (~280 lines) following the established Linear/GitHub sync field mapper patterns. The module encodes the statusCategory.key normalization strategy per D233/D235, maps all 8 Jira priority name variants, and implements both pull (Jira→bpkm) and push (bpkm→Jira) directions.

Key implementation details:
- **STATUS_MAP** maps the 3 Jira statusCategory.key values (new, indeterminate, done) to bpkm taskStatus values
- **PRIORITY_MAP** maps 8 Jira priority names (Highest, Critical, Blocker, High, Medium, Low, Lowest, Trivial) to 4 bpkm values
- **build_task_properties** handles nested `{fields: {...}}` and flat dict shapes, extracts tags from both labels and components, constructs external URL from the issue's `self` link, and always includes lastSyncedAt
- **build_milestone_properties** maps Epic→Milestone with status done→completed, else active
- **build_issue_patch** maps only title and priority per D237 (no status transitions without transition IDs)
- **compute_issue_slug** produces deterministic `jira-{16 hex chars}` slugs via sha256

Test file covers 74 tests across 9 test classes: STATUS_MAP (5), PRIORITY_MAP (10), compute_issue_slug (5), build_task_properties (20), build_milestone_properties (5), build_issue_patch (9), REVERSE_STATUS_MAP (6), REVERSE_PRIORITY_MAP (5), round-trip consistency (9).

## Verification

All 74 tests pass:
```
cd backend && .venv/bin/python -m pytest tests/test_jira_field_mapper.py -v
# 74 passed in 0.10s
```

Module import verification:
```
python3 -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('x', 'apps/jira-sync/services/field_mapper.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print(mod.STATUS_MAP)"
# {'new': 'todo', 'indeterminate': 'in-progress', 'done': 'done'}
```

T01 ADF converter tests still pass (95 tests, no regression).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_jira_field_mapper.py -v` | 0 | ✅ pass | 0.10s |
| 2 | `python3 -c "import importlib.util, sys; spec = ... print(mod.STATUS_MAP)"` | 0 | ✅ pass | <1s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_jira_adf_converter.py -v` | 0 | ✅ pass | 0.08s |

## Diagnostics

Pure module with no runtime state. To inspect field mapper behavior:
- Call `build_task_properties(issue_dict)` with sample Jira issue JSON to see bpkm property output
- Call `build_milestone_properties(epic_dict)` for Epic→Milestone mapping
- Call `build_issue_patch(props_dict)` for reverse mapping
- `normalize_status("unknown")` returns "todo" — unknown statusCategory keys always safe-default
- `normalize_priority("Nonexistent")` returns None — unknown priorities are omitted from output

## Deviations

- Test count is 74 (exceeding the 40+ target) — additional tests added for round-trip consistency, lossy mapping verification, and edge cases like string labels, missing statusCategory, and external URL construction.
- The `_make_issue()`/`_make_epic()` fixtures use replace semantics for the `fields=` kwarg (not merge), which is a deliberate deviation from the initial pattern to properly test minimal issue scenarios.

## Known Issues

None.

## Files Created/Modified

- `apps/jira-sync/services/field_mapper.py` — Pure field mapper module (~280 lines) with STATUS_MAP, PRIORITY_MAP, reverse maps, build_task_properties, build_milestone_properties, compute_issue_slug, build_issue_patch
- `backend/tests/test_jira_field_mapper.py` — 74 unit tests covering all mapping paths, edge cases, and round-trip consistency
- `.gsd/milestones/M023/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
