---
estimated_steps: 7
estimated_files: 2
---

# T03: Configurable field mapper with per-column-type transforms and reverse mapping

**Slice:** S01 — Auth + GraphQL client + field mapper + person matcher
**Milestone:** M024

## Description

Build the field mapper for Monday.com — the pure-function data transformation engine that converts between Monday.com column values and bpkm:Task properties. Unlike Jira/GitHub where field positions are fixed, Monday.com columns are fully user-configurable. The mapper accepts a `column_mapping` dict parameter that specifies which Monday.com column maps to which bpkm property.

The key technical challenge is **column value format asymmetry**: Monday.com column values read from queries have one JSON shape (e.g., status reads as `{"label": "Working on it", "index": 1}`) but mutations expect a different shape (e.g., status writes as `{"label": "Done"}`). The mapper must handle both directions correctly for ~8 column types.

## Steps

1. **Define constants and default maps** at the top of `apps/monday-sync/services/field_mapper.py`:
   - `BPKM = "urn:sempkm:model:basic-pkm:"` — full IRI prefix
   - `DEFAULT_STATUS_MAP` — maps common Monday.com status labels to bpkm taskStatus: `{"Done": "done", "Working on it": "in-progress", "Stuck": "blocked", "Not Started": "todo", "": "todo"}`
   - `DEFAULT_PRIORITY_MAP` — maps Monday.com priority labels to bpkm priority: `{"Critical ⚨": "critical", "High": "high", "Medium": "medium", "Low": "low", """: "low"}`
   - `REVERSE_STATUS_MAP` / `REVERSE_PRIORITY_MAP` — inverses for push sync
   - The actual label→value mappings are user-configurable (stored in S02's column mapping UI). These defaults are fallbacks.

2. **Implement column value extractors** — one function per column type that reads the Monday.com column value JSON:
   - `_extract_status(col_value, status_label_mapping) -> str` — reads `col_value` (which is JSON string of `{"label": "Working on it", "index": 1}` or might already be a dict). Returns mapped bpkm status via `status_label_mapping.get(label, "todo")`.
   - `_extract_date(col_value) -> str | None` — reads `{"date": "2025-01-15", "changed_at": "..."}`. Returns date string or None.
   - `_extract_people(col_value) -> int | None` — reads `{"personsAndTeams": [{"id": 12345, "kind": "person"}]}`. Returns first person's numeric ID or None.
   - `_extract_text(col_value) -> str | None` — reads text/long_text value (plain string or `{"text": "...", "value": "..."}`). Returns text or None.
   - `_extract_numbers(col_value) -> str | None` — reads `"42"` or `{"value": "42"}`. Returns string value.
   - `_extract_tags(col_value) -> list[int]` — reads `{"tag_ids": [1, 2, 3]}`. Returns list of tag IDs (to be resolved to names later by caller).
   - `_extract_dropdown(col_value) -> list[str]` — reads `{"ids": [1,2], "labels": ["Label A", "Label B"]}` or similar. Returns list of label strings.
   - Each extractor should handle None/empty input gracefully (return None or empty list).

3. **Implement `build_task_properties(item, column_mapping, status_label_mapping=None, priority_label_mapping=None)`**:
   - `item` is a Monday.com item dict with `id`, `name`, `column_values` (list of `{"id": "col_id", "text": "...", "value": "...json...", "type": "status", ...}`).
   - `column_mapping` is a dict mapping bpkm property names to Monday.com column IDs: `{"taskStatus": "status_col_id", "priority": "priority_col_id", "dueDate": "date4", "assignedTo": "people_col"}`.
   - Build a column ID → column value lookup from `item["column_values"]`.
   - For each entry in `column_mapping`, find the column value by ID and apply the appropriate extractor based on the column's type.
   - Always set: `dcterms:title` (from `item["name"]`), `bpkm:externalId` (from `item["id"]`), `bpkm:externalProvider` ("monday"), `bpkm:lastSyncedAt` (current UTC ISO).
   - The `assignedTo` mapping returns a person user_id (integer) — the caller (sync_engine) uses PersonMatcher to resolve this to a Person IRI.
   - Strip None/empty/[] values except lastSyncedAt.
   - Return raw person_id separately (as `_assignee_user_id` key or second return value) so caller can resolve asynchronously.

4. **Implement `build_reverse_column_values(task_properties, column_mapping, reverse_status_mapping=None, reverse_priority_mapping=None)`**:
   - For push sync: converts bpkm properties back to Monday.com column value JSON.
   - Returns a dict of `{column_id: json_value_string}` ready for `change_multiple_column_values`.
   - Per-column-type serializers:
     - status → `{"label": "Done"}` (JSON string)
     - date → `{"date": "2025-01-15"}` (JSON string)
     - text → `"value text"` (plain string, or JSON string)
     - numbers → `"42"` (plain string)
     - people → `{"personsAndTeams": [{"id": 12345, "kind": "person"}]}` (JSON string)
   - Skip properties not in column_mapping.

5. **Implement `compute_slug(item_name, item_id)`**:
   - Deterministic slug: `monday-{sha256(item_name + "#" + str(item_id))[:16]}`
   - Used for platform IRI minting.

6. **Implement `_extract_external_url(item)`**:
   - Monday.com items don't have a direct URL in the API response. Construct from board_id: `https://monday.com/boards/{board_id}/pulses/{item_id}`. The board_id should be passed as a parameter or extracted from item context.
   - Alternative: accept board_id as parameter to `build_task_properties`.

7. **Write comprehensive tests** in `backend/tests/test_monday_field_mapper.py`:
   - Column type extraction: status (with custom label mapping), date, people, text, long_text, numbers, tags, dropdown — each with valid, empty, None inputs
   - `build_task_properties`: full item with all mapped columns, partial mapping (some columns missing), empty column_values, status/priority label mapping override
   - `build_reverse_column_values`: status reverse, date reverse, text reverse, numbers reverse, people reverse, round-trip (build → reverse → verify)
   - `compute_slug`: deterministic output, different inputs produce different slugs
   - Edge cases: column_mapping references non-existent column ID, column value is null JSON, column_values array is empty

## Must-Haves

- [ ] `build_task_properties()` accepts configurable column_mapping dict (not hardcoded fields)
- [ ] 8+ column type extractors (status, date, people, text, long_text, numbers, tags, dropdown)
- [ ] Status/priority label mapping is configurable via function parameters with sensible defaults
- [ ] `build_reverse_column_values()` produces correct per-column-type JSON for Monday.com mutations
- [ ] `compute_slug()` produces deterministic monday-prefixed slugs
- [ ] All extractors handle None/empty/malformed input gracefully
- [ ] 50+ unit tests pass

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_field_mapper.py -v` — 50+ tests pass
- `python3 -c "import ast; ast.parse(open('apps/monday-sync/services/field_mapper.py').read())"` — no syntax errors

## Inputs

- `apps/jira-sync/services/field_mapper.py` — reference for field mapper pattern (BPKM prefix, status/priority maps, slug computation, property builder, reverse mapping)
- `backend/tests/test_jira_field_mapper.py` — reference for test patterns (importlib loading, comprehensive coverage)
- Monday.com column value JSON formats (documented in task description above)

## Observability Impact

- **No new runtime signals.** This module is pure functions — no logging, no state, no network calls. All functions are side-effect-free.
- **Inspection:** Feed a Monday.com item dict to `build_task_properties()` in a REPL to see the exact bpkm property mapping. Feed bpkm properties to `build_reverse_column_values()` to see the mutation JSON that would be sent.
- **Failure visibility:** Malformed column values silently produce None/empty defaults rather than raising — the caller (sync_engine) decides whether to log or skip. Column mapping misses (column ID not found in item) are silently skipped, not raised.
- **Test runner diagnostic:** `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python -m pytest backend/tests/test_monday_field_mapper.py -v` — 50+ tests verify all extraction and round-trip paths.

## Expected Output

- `apps/monday-sync/services/field_mapper.py` — configurable field mapper (~250-350 lines)
- `backend/tests/test_monday_field_mapper.py` — 50+ passing tests (~400-500 lines)
