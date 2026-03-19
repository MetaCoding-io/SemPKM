---
estimated_steps: 8
estimated_files: 2
---

# T01: Build field mapper with full unit tests

**Slice:** S02 — Pull Sync — Linear Issues to bpkm:Task
**Milestone:** M016

## Description

Create the pure field mapping module that converts Linear issue data to `bpkm:Task` properties. This is the foundation for the entire sync pipeline — all mapping, normalization, slug computation, and GraphQL query construction lives here. Zero external dependencies means full unit testability without mocks.

All property keys must use full IRIs (e.g. `urn:sempkm:model:basic-pkm:taskStatus`) because the `bpkm:` prefix is NOT in the platform's `COMMON_PREFIXES`. Standard prefixes like `dcterms:title` work because `dcterms` is recognized.

## Steps

1. **Create `apps/linear-sync/services/field_mapper.py`** with these constants and functions:

   **Constants:**
   ```python
   # Full IRI prefix for basic-pkm properties
   BPKM = "urn:sempkm:model:basic-pkm:"
   
   # Linear state.type → bpkm:taskStatus
   STATUS_MAP = {
       "backlog": "todo",
       "unstarted": "todo", 
       "started": "in-progress",
       "completed": "done",
       "cancelled": "cancelled",
   }
   
   # Linear priority (0-4) → bpkm:priority
   # 0 = No priority (omit), 1 = Urgent, 2 = High, 3 = Medium, 4 = Low
   PRIORITY_MAP = {
       1: "critical",
       2: "high",
       3: "medium",
       4: "low",
   }
   
   # Linear estimate → bpkm:effort (lossy mapping)
   EFFORT_MAP = {
       0: None,
       1: "trivial",
       2: "small",
       3: "medium",
       5: "large",
       8: "epic",
   }
   ```

2. **Implement `normalize_status(state_type: str) -> str`** — Lookup in STATUS_MAP, default to `"todo"` for unknown types.

3. **Implement `normalize_priority(priority: int) -> str | None`** — Lookup in PRIORITY_MAP, return None for 0 or unknown values (caller omits None from properties).

4. **Implement `map_labels_to_tags(labels: list[dict]) -> list[str]`** — Extract `label["name"]` from each label dict. Return empty list for empty/None input.

5. **Implement `compute_issue_slug(workspace_id: str, issue_id: str) -> str`** — Return `f"issue-{hashlib.sha256((workspace_id + issue_id).encode()).hexdigest()[:16]}"`. This makes platform-minted Task IRIs deterministic: `{base_namespace}/Task/issue-{hash16}`.

6. **Implement `build_task_properties(issue: dict, workspace_id: str) -> dict`** — Build the full properties dict for `object.create`/`object.patch`. The issue dict has Linear's GraphQL shape:
   ```python
   {
       "id": "...", "identifier": "ENG-123", "title": "...", "description": "...",
       "state": {"type": "started"}, "priority": 2,
       "dueDate": "2026-04-01", "completedAt": "2026-03-18T10:00:00.000Z",
       "labels": {"nodes": [{"name": "bug"}]},
       "estimate": 3, "url": "https://linear.app/...",
       "trashed": false
   }
   ```
   
   Property mapping (key → value):
   - `"dcterms:title"` → `issue["title"]` (compact IRI works — dcterms in COMMON_PREFIXES)
   - `f"{BPKM}taskStatus"` → `normalize_status(issue["state"]["type"])`
   - `f"{BPKM}priority"` → `normalize_priority(issue["priority"])` — **omit if None**
   - `f"{BPKM}dueDate"` → `issue["dueDate"]` truncated to date-only (`[:10]`) — **omit if None/empty**
   - `f"{BPKM}completedDate"` → `issue["completedAt"][:10]` if present and state.type == "completed" — **omit if None**
   - `f"{BPKM}tags"` → `map_labels_to_tags(issue.get("labels", {}).get("nodes", []))` — **omit if empty**
   - `f"{BPKM}effort"` → `EFFORT_MAP.get(issue.get("estimate"), None)` — **omit if None**; for unmapped estimate values, stringify as-is (e.g. `"13"`)
   - `f"{BPKM}externalId"` → `issue["identifier"]` (e.g. "ENG-123")
   - `f"{BPKM}externalUrl"` → `issue["url"]`
   - `f"{BPKM}externalProvider"` → `"linear"`
   - `f"{BPKM}lastSyncedAt"` → current UTC datetime in ISO format (passed as param or computed)
   - `f"{BPKM}syncDirection"` → `"pull"`
   
   **Critical:** Omit any key whose value is None, empty string, or empty list. The platform creates `Literal("")` for empty strings which is incorrect.

7. **Implement `build_issue_query(team_ids: list[str], updated_after: str | None) -> tuple[str, dict]`** — Return a GraphQL query string and variables dict for paginated issue fetching:
   ```graphql
   query($teamIds: [String!]!, $after: String, $updatedAfter: DateTime) {
     issues(
       filter: {
         team: { id: { in: $teamIds } }
         updatedAt: { gte: $updatedAfter }
       }
       first: 100
       after: $after
     ) {
       nodes {
         id identifier title description url trashed
         state { type }
         priority
         dueDate
         completedAt
         labels { nodes { name } }
         estimate
         assignee { id displayName email }
         updatedAt
         createdAt
       }
       pageInfo { hasNextPage endCursor }
     }
   }
   ```
   Variables: `{"teamIds": team_ids, "updatedAfter": updated_after}`. Only include `updatedAfter` in the filter block if not None — use conditional query construction (two query variants or dynamic filter). The `after` variable is left for pagination (LinearClient.query_paginated() handles it).

8. **Create `backend/tests/test_field_mapper.py`** with comprehensive tests:
   - `normalize_status`: all 5 Linear state types map correctly, unknown type defaults to "todo"
   - `normalize_priority`: 0 → None, 1 → critical, 2 → high, 3 → medium, 4 → low, unknown → None
   - `map_labels_to_tags`: multiple labels, empty list, None-safe
   - `compute_issue_slug`: determinism (same input → same output), different inputs → different outputs, format check (`issue-` prefix, 16 hex chars)
   - `build_task_properties`: full issue with all fields, issue with minimal fields (nulls omitted), priority 0 omitted, empty labels omitted, completedDate only when state is completed, dueDate truncated from datetime to date, externalId/externalUrl/externalProvider always present, all keys use full IRIs except dcterms:title
   - `build_issue_query`: query includes team filter, query includes updatedAfter when provided, query omits updatedAfter filter when None, variables dict is correct
   - Effort mapping: known estimates map to effort strings, unknown estimates stringify, estimate 0/None omitted

   Use the importlib pattern from S01 tests to load the module:
   ```python
   import importlib.util, pathlib
   _APP_DIR = pathlib.Path(__file__).resolve().parents[1] / "apps" / "linear-sync"
   spec = importlib.util.spec_from_file_location("field_mapper", _APP_DIR / "services" / "field_mapper.py")
   field_mapper = importlib.util.module_from_spec(spec)
   spec.loader.exec_module(field_mapper)
   ```

## Must-Haves

- [ ] All 6 functions implemented in `field_mapper.py`
- [ ] All property keys use full IRIs (`urn:sempkm:model:basic-pkm:*`) except `dcterms:title`
- [ ] None/empty values omitted from properties dict (never sent as empty strings)
- [ ] Date fields truncated to date-only format for `dueDate`/`completedDate`
- [ ] Slug computation is deterministic via SHA-256
- [ ] GraphQL query handles optional `updatedAfter` filter correctly
- [ ] ~30 unit tests covering all normalization paths and edge cases

## Verification

- `cd backend && python -m pytest tests/test_field_mapper.py -v` — all tests pass
- `python3 -c "import ast; ast.parse(open('apps/linear-sync/services/field_mapper.py').read())"` — syntax valid

## Inputs

- S01's importlib test pattern from `backend/tests/test_linear_client.py` — reuse for loading app modules
- Research doc field mapping specification (inlined in the steps above)
- Ontology property IRIs: `urn:sempkm:model:basic-pkm:{taskStatus,priority,dueDate,completedDate,tags,effort,externalId,externalUrl,externalProvider,lastSyncedAt,syncDirection}`

## Expected Output

- `apps/linear-sync/services/field_mapper.py` — ~150 lines, 6 pure functions + constants
- `backend/tests/test_field_mapper.py` — ~30 tests covering all mapping paths
