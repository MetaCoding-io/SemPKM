---
estimated_steps: 7
estimated_files: 2
---

# T02: Build field mapper with statusCategory normalization and 40+ unit tests

**Slice:** S01 — ADF converter + field mapper + Jira client + auth scaffold
**Milestone:** M023

## Description

Build the Jira field mapper as a pure Python module with zero side effects. This encodes the statusCategory.key normalization strategy (D235/D233), priority mapping, and property building for both pull (Jira→bpkm) and push (bpkm→Jira) directions. Follow the `apps/linear-sync/services/field_mapper.py` pattern exactly — it has STATUS_MAP, PRIORITY_MAP, reverse maps, `build_task_properties()`, `compute_issue_slug()`, and `build_issue_update_input()`.

**Key decisions:**
- D233/D235: Always use `statusCategory.key` (new/indeterminate/done) — never status.name
- Store status.name in `bpkm:externalStatus` for display
- D237: Push sync limited to title/description/priority for v1 (no status transitions)

## Steps

1. Create `apps/jira-sync/services/field_mapper.py` with module docstring
2. Define constants and mapping dicts:
   - `BPKM = "urn:sempkm:model:basic-pkm:"` (full IRI prefix)
   - `STATUS_MAP: dict[str, str]` — `{"new": "todo", "indeterminate": "in-progress", "done": "done"}`
   - `PRIORITY_MAP: dict[str, str]` — Jira priority names to bpkm values. Keys: `"Highest"`, `"Critical"`, `"Blocker"` → `"critical"`; `"High"` → `"high"`; `"Medium"` → `"medium"`; `"Low"` → `"low"`; `"Lowest"`, `"Trivial"` → `"low"`
   - `REVERSE_STATUS_MAP: dict[str, str]` — `{"todo": "new", "in-progress": "indeterminate", "done": "done", "blocked": "indeterminate", "cancelled": "done"}`
   - `REVERSE_PRIORITY_MAP: dict[str, str]` — `{"critical": "Highest", "high": "High", "medium": "Medium", "low": "Low"}`
3. Implement `compute_issue_slug(project_key: str, issue_key: str) -> str`:
   - Compute `sha256(f"{project_key}#{issue_key}").hexdigest()[:16]`
   - Return `f"jira-{digest}"`
4. Implement `build_task_properties(issue: dict, person_iri: str | None = None, sync_time: str | None = None) -> dict`:
   - Map: `summary` → `dcterms:title`, `statusCategory.key` → `bpkm:taskStatus` via STATUS_MAP, `status.name` → `bpkm:externalStatus`, `priority.name` → `bpkm:priority` via PRIORITY_MAP, `duedate` → `bpkm:dueDate` (truncate to date), `resolutiondate` → `bpkm:completedDate` (truncate to date, only if resolved), `assignee` → `bpkm:assignedTo` (person_iri param), `labels[].name` → `bpkm:tags` (list), `components[].name` → append to `bpkm:tags`, `sprint.name` → `bpkm:taskGroup`, `key` → `bpkm:externalId`, construct `bpkm:externalUrl` as `https://{site}/browse/{key}`, `id` → `bpkm:externalUuid`, `"jira"` → `bpkm:externalProvider`
   - Always set `bpkm:lastSyncedAt` to sync_time (or now if None)
   - Strip None, empty string, empty list values (except lastSyncedAt)
5. Implement `build_milestone_properties(epic: dict, sync_time: str | None = None) -> dict`:
   - Map: `summary` → `dcterms:title`, `duedate` → `bpkm:targetDate`, `key` → `bpkm:externalId`, `bpkm:externalUrl`, `"jira"` → `bpkm:externalProvider`, `bpkm:lastSyncedAt`
   - `bpkm:milestoneStatus`: if statusCategory.key == "done" → "completed", else "active"
6. Implement `build_issue_patch(task_props: dict) -> dict`:
   - Reverse map for push sync: `dcterms:title` → `summary`, `bpkm:priority` → `priority.name` via REVERSE_PRIORITY_MAP
   - Per D237: NO status mapping in v1 push (no transition IDs)
   - Return only non-None fields
7. Create `backend/tests/test_jira_field_mapper.py` using importlib loading pattern, with tests:
   - **STATUS_MAP tests:** all 3 statusCategory.key values map correctly, unknown key defaults to "todo"
   - **PRIORITY_MAP tests:** all Jira priority names map correctly, unknown priority returns None
   - **compute_issue_slug:** deterministic (same input → same output), different projects → different slugs, different keys → different slugs, prefix is `jira-`
   - **build_task_properties:** full issue dict with all fields populated, minimal issue (only required fields), issue with empty labels/components, issue with sprint, issue with resolution date, assignee mapping via person_iri param, sync_time default vs explicit
   - **build_milestone_properties:** epic with status done → completed, epic with status active, minimal epic
   - **build_issue_patch:** title mapping, priority mapping, empty props → empty result, unknown priority skipped
   - **REVERSE maps:** each entry maps correctly, round-trip consistency where possible

## Must-Haves

- [ ] STATUS_MAP maps all 3 statusCategory.key values correctly
- [ ] PRIORITY_MAP maps all Jira priority name variants
- [ ] build_task_properties produces correct bpkm property dict from Jira issue JSON
- [ ] build_milestone_properties handles Epic→Milestone mapping
- [ ] compute_issue_slug is deterministic with `jira-` prefix
- [ ] build_issue_patch maps title and priority (not status per D237)
- [ ] 40+ unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_jira_field_mapper.py -v` — all 40+ tests pass
- `python -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('x', 'apps/jira-sync/services/field_mapper.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print(mod.STATUS_MAP)"` — prints the status map

## Inputs

- `apps/jira-sync/services/__init__.py` — created in T01
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §4 — Jira field mapping table, status normalization, priority mapping
- `apps/linear-sync/services/field_mapper.py` — reference implementation (STATUS_MAP, PRIORITY_MAP, build_task_properties, compute_issue_slug, build_issue_update_input patterns)
- `apps/github-sync/services/field_mapper.py` — reference for build_issue_patch (reverse mapping)
- `backend/tests/test_github_field_mapper.py` — importlib test loading pattern
- D233/D235: statusCategory.key normalization. D237: push limited to title/description/priority

## Expected Output

- `apps/jira-sync/services/field_mapper.py` — ~250-line pure module with all maps and builder functions
- `backend/tests/test_jira_field_mapper.py` — 40+ unit tests covering all mapping paths

## Observability Impact

This module is a pure function library with no runtime state, logging, or side effects. Observability is via:

- **Inspection:** Import the module and call any function with sample data to verify mapping behavior. All functions are deterministic — same input always produces same output.
- **Debugging unknown mappings:** `normalize_status("someKey")` returns `"todo"` for unknown statusCategory keys; `normalize_priority("SomeName")` returns `None` for unknown priority names. Grep for `None` values in output dicts to identify unmapped fields.
- **Round-trip verification:** Forward maps (STATUS_MAP, PRIORITY_MAP) and reverse maps (REVERSE_STATUS_MAP, REVERSE_PRIORITY_MAP) can be checked for consistency. Known lossy paths: Blocker→critical→Highest, Lowest→low→Low, Trivial→low→Low.
- **Failure visibility:** No runtime failures possible — all functions handle missing/None/empty inputs gracefully with defaults or omission.

