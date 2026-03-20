# M024: Monday.com Sync App — Research

**Date:** 2026-03-19

## Summary

Monday.com Sync is the final task-provider sync app on the App Platform, mapping Monday.com items to `bpkm:Task` objects. The established 6-service architecture (auth, client, field_mapper, person_matcher, sync_engine, app.py) translates directly, but Monday.com introduces two novel challenges beyond all prior sync apps:

1. **User-configurable column→property mapping** — Monday.com's fully customizable column-based data model means every board has different columns. Unlike Jira (fixed fields + statusCategory normalization) or Linear (fixed GraphQL schema), Monday.com requires the user to tell the sync app which column maps to which property. This is the same "configure before sync" pattern planned for Asana (M022/D228), making M024 the second app to implement it.

2. **LoopGuard for webhook echo prevention** — Monday.com has no webhook suppression mechanism. API-originated changes re-trigger webhooks, causing infinite sync loops. The INTEGRATION-DOMAIN-MAPPING.md design specifies a TTL-based `pending_changes` set that tracks `(item_id, column_id, timestamp)` tuples and skips incoming webhook events that match recently-pushed changes within a time window. However, since the App Platform doesn't expose external webhook routes (D200), v1 will use polling-only sync like all prior apps. The LoopGuard is still needed for push→poll echo prevention (same pattern as `lastSyncedAt` in prior apps, but with a tighter window because Monday.com has no delta query).

The Monday.com GraphQL API uses a single endpoint (`https://api.monday.com/v2`) with complexity-based rate limiting. Nested queries consume complexity exponentially — deeply nested board→group→item→column_values queries can easily exceed the 5M per-query limit. The client must use pagination (`limit`/`cursor`) and request only needed fields.

## Recommendation

Follow the established sync app architecture exactly (6 services + manifest + templates + tests + docs), with the column mapping configuration as a setup step between authentication and sync configuration. Since this mirrors the Asana configurable mapping pattern (D228), the same state shape and UI approach applies.

**Authentication:** API token only for v1 (matching D206/D236 pattern). Monday.com personal API tokens are available to admins and members via Avatar > Developers. OAuth 2.0 deferred — it requires registering a Monday.com app and is unnecessary for self-hosted single-user use.

**Sync mechanism:** Polling-only (matching D200/D211 pattern). No webhook endpoint in v1. Monday.com has no delta query or `updatedAt` filter equivalent, so each poll fetches all items from selected boards and uses `lastSyncedAt` comparison for loop prevention.

**GraphQL client:** Hand-crafted queries over httpx via SDK HttpClient (matching D201 Linear pattern). No monday.com SDK — it's JavaScript-only. The Python client sends POST requests with `query` JSON body to `https://api.monday.com/v2`.

Build order:
1. **S01: Auth + board/column discovery** — API token auth, board listing, column schema discovery. Proves API access and column introspection. Field mapper + person matcher stubs.
2. **S02: Column mapping configuration + pull sync** — Column→property mapping UI (the novel, risky slice). Pull sync with configurable transforms. Board groups as taskGroup. Subitems via parentTask.
3. **S03: Push sync + LoopGuard** — Reverse column value mutations, dependency edges, LoopGuard TTL for echo prevention on push→poll cycle.
4. **S04: E2E tests + user guide** — Mock Monday.com GraphQL server, Playwright E2E test, Chapter 37 user guide.

## Implementation Landscape

### Key Files

**Existing patterns to clone (7 prior sync apps):**
- `apps/jira-sync/` — most recent reference (app.py ~280 lines, manifest.yaml, services/ with 7 modules)
- `apps/jira-sync/services/jira_client.py` — REST client with error hierarchy, auth header injection, pagination (~280 lines). Monday.com client will be similar but POST GraphQL instead of REST verbs.
- `apps/jira-sync/services/field_mapper.py` — `build_task_properties()` pure function, status/priority maps, reverse mapping for push (~300 lines). Monday.com version must read mapping config from state instead of using hardcoded maps.
- `apps/jira-sync/services/sync_engine.py` — two-phase bulk create, SPARQL task lookup, loop prevention via `lastSyncedAt`, push via `_find_changed_tasks` SPARQL (~500 lines). Directly reusable pattern.
- `apps/jira-sync/services/person_matcher.py` — SPARQL email lookup with create-on-miss and LRU cache (~100 lines). Clone directly — Monday.com users have emails.
- `apps/jira-sync/services/auth.py` — credential storage/verification via StateClient (~80 lines). Adapt for API token (simpler than Jira's email+token+site_url).

**New files to create:**
- `apps/monday-sync/` — full app directory
- `apps/monday-sync/manifest.yaml` — appId "monday-sync", network: ["api.monday.com"]
- `apps/monday-sync/app.py` — route handlers including column mapping config endpoints
- `apps/monday-sync/services/auth.py` — API token storage/verification
- `apps/monday-sync/services/monday_client.py` — GraphQL client with complexity tracking, pagination, error hierarchy
- `apps/monday-sync/services/field_mapper.py` — configurable column→property mapping, status label mapping
- `apps/monday-sync/services/sync_engine.py` — pull/push with LoopGuard echo prevention
- `apps/monday-sync/services/person_matcher.py` — standard SPARQL email lookup (clone)
- `apps/monday-sync/services/loop_guard.py` — TTL-based pending_changes tracker (new pattern)
- `apps/monday-sync/frontend/templates/` — connect.html, connect_status.html (extended with column mapping UI)
- `apps/monday-sync/frontend/static/styles.css`
- `backend/tests/test_monday_*.py` — unit tests (5+ files)
- `e2e/tests/37-monday-sync/` — Playwright E2E spec
- `e2e/mocks/monday/` — mock Monday.com GraphQL server
- `docs/guide/37-monday-sync.md` — user guide Chapter 37

### Monday.com GraphQL API Specifics

**Endpoint:** Single POST endpoint at `https://api.monday.com/v2`. All requests are JSON with `{"query": "...", "variables": {...}}` body.

**Authentication:** `Authorization: <API_TOKEN>` header (no "Bearer" prefix per Monday.com docs). API version header recommended: `API-Version: 2026-01` (current stable).

**Key queries needed:**
- `{ boards { id name } }` — list boards for selection
- `{ boards(ids: [ID]) { columns { id title type settings_str } groups { id title } } }` — column schema + groups for a board
- `{ boards(ids: [ID]) { items_page(limit: 100) { cursor items { id name group { id title } column_values { id type text value ... on StatusValue { label } ... on PeopleValue { persons_and_teams { id } } } } } } }` — paginated items with column values
- `{ users(ids: [ID]) { id name email } }` — user details for person matching

**Key mutations:**
- `mutation { change_multiple_column_values(board_id: ID, item_id: ID, column_values: JSON) { id } }` — update multiple columns in one call (per optimization docs)
- `mutation { create_item(board_id: ID, group_id: String, item_name: String, column_values: JSON) { id } }` — create item

**Rate limiting:** Complexity-based. Per-minute budget is 10M points (paid accounts), 5M per single query. Nested queries (board→items→column_values) consume exponentially. Must paginate items (limit 100-200) and avoid deep nesting. Add `complexity { query before after }` to queries for tracking. On `ComplexityException`, wait per `retry_in_seconds` field.

**Column value types relevant to sync:**
| Monday Column Type | GraphQL Fragment | bpkm Property | Notes |
|---|---|---|---|
| `name` (item name) | Direct on item | `dcterms:title` | Always present |
| `long_text` / `text` | `TextValue { text }` | `dcterms:description` | Direct |
| `status` | `StatusValue { label index }` | `bpkm:taskStatus` | Custom labels, user maps to enum |
| `date` | `DateValue { date }` | `bpkm:dueDate` | ISO date string |
| `timeline` | `TimelineValue { from to }` | `bpkm:startDate` + `bpkm:dueDate` | Split |
| `people` | `PeopleValue { persons_and_teams { id } }` | `bpkm:assignedTo` | User IDs → Person IRIs |
| `numbers` | `NumbersValue { number }` | `bpkm:storyPoints` | If column is "Points"/"Estimate" |
| `tags` | `TagValue { tag_ids }` | `bpkm:tags` | Tag IDs need resolution |
| `dependency` | `DependencyValue { linked_items }` | `bpkm:dependsOn` | Item IDs → Task IRIs |
| `checkbox` | `CheckboxValue { checked }` | `bpkm:taskStatus` | checked → "done" |
| `color` (priority) | `StatusValue { label }` | `bpkm:priority` | Label mapping |
| `link` | `LinkValue { url text }` | `bpkm:externalUrl` | URL extraction |

### Column Mapping Configuration — The Novel Pattern

This is the key differentiator shared with Asana (D228). The settings flow must:

1. After API token auth, user selects board(s) to sync
2. App queries board column schema: `{ boards(ids: [ID]) { columns { id title type } } }`
3. App presents discovered columns with mapping dropdowns:
   - "Which column represents **Status**?" → dropdown of `status` type columns + "None"
   - "Which column represents **Priority**?" → dropdown of `status` type columns + "None"
   - "Which column represents **Due Date**?" → dropdown of `date` type columns + "None"
   - "Which column represents **Assignee**?" → dropdown of `people` type columns + "None"
   - "Which column represents **Story Points**?" → dropdown of `numbers` type columns + "None"
   - "Which column represents **Description**?" → dropdown of `text`/`long_text` columns + "None"
   - "Which column represents **Tags**?" → dropdown of `tags` type columns + "None"
4. For status mapping: show discovered status labels with bpkm:taskStatus value dropdowns
5. For priority mapping: show discovered priority labels with bpkm:priority value dropdowns
6. Configuration stored as JSON in StateClient

**State shape:**
```json
{
  "column_mapping": {
    "status": "status_col_id",
    "priority": "priority_col_id",
    "due_date": "date_col_id",
    "assignee": "people_col_id",
    "story_points": "numbers_col_id",
    "description": "long_text_col_id",
    "tags": "tags_col_id",
    "dependency": "dependency_col_id"
  },
  "status_label_mapping": {
    "": "todo",
    "Working on it": "in-progress",
    "Done": "done",
    "Stuck": "blocked"
  },
  "priority_label_mapping": {
    "Low": "low",
    "Medium": "medium",
    "High": "high",
    "Critical": "critical"
  }
}
```

### LoopGuard — Echo Prevention

The INTEGRATION-DOMAIN-MAPPING.md design specifies a LoopGuard mechanism for Monday.com's webhook echo problem. While v1 uses polling-only (no webhooks), the push→poll echo prevention is still needed:

**Problem:** Push sync updates a Monday.com item via API. Next poll fetches that item with updated values. Without guard, pull sync treats it as an external change and re-imports, potentially triggering another push cycle.

**Solution (for v1 polling):** The existing `lastSyncedAt` pattern from all prior sync apps handles this adequately — push updates `lastSyncedAt`, pull skips items whose Monday.com `updated_at` ≤ `lastSyncedAt`. However, Monday.com items don't have a reliable `updated_at` field in the items query. Alternative: maintain an in-memory set of `(item_id, column_id)` tuples pushed in the current cycle, skip matching items in the same sync run. For cross-run prevention, rely on content comparison (compare current Monday values with stored bpkm values — skip if identical).

**LoopGuard module (`loop_guard.py`):** A simple TTL cache class:
```python
class LoopGuard:
    def __init__(self, ttl_seconds: int = 10):
        self._pending: dict[str, float] = {}  # key → timestamp
        self._ttl = ttl_seconds

    def mark_pushed(self, item_id: str, column_id: str): ...
    def is_echo(self, item_id: str, column_id: str) -> bool: ...
    def cleanup(self): ...  # remove expired entries
```

This is a lightweight, testable pure-Python module. For v1 polling-only, the simpler `lastSyncedAt` approach may suffice, with LoopGuard deferred to when webhooks are added.

### Build Order

1. **S01: Auth + board/column discovery + field mapper + person matcher** — Proves API access. API token stored via StateClient. Board listing query. Column schema query (introspects all columns on a board). Field mapper with configurable maps (reads from state, not hardcoded). Person matcher (clone from Jira). 150+ unit tests target.

2. **S02: Column mapping UI + pull sync** — The novel, highest-risk slice. Column mapping configuration UI in connect_status.html (dropdowns populated from column schema, status/priority label mapping). Pull sync with configurable transforms reading from stored mapping config. Board groups as taskGroup. Subitem→parentTask linking. Two-phase bulk create. 150+ unit tests target.

3. **S03: Push sync + dependency edges** — Reverse column value mutations (`change_multiple_column_values`). Status/priority reverse label mapping from stored config. Dependency column→bpkm:dependsOn edges. LoopGuard for echo prevention (or simpler content-comparison approach). 100+ unit tests target.

4. **S04: E2E tests + user guide** — Mock Monday.com GraphQL server (canned responses for boards, columns, items, users, mutations). Playwright E2E test (install → auth → configure columns → sync → verify → push lifecycle). Chapter 37 user guide documenting column mapping walkthrough.

### Verification Approach

- **Unit tests:** importlib-loaded from `apps/monday-sync/services/` into `backend/tests/test_monday_*.py`. Pure function tests for field mapper (configurable transforms), sync engine (mock clients), auth (token flow), client (GraphQL construction, pagination, complexity handling), loop guard (TTL expiry). Target: 350+ tests across 6 files.
- **Mock server:** `e2e/mocks/monday/server.py` — canned GraphQL responses for boards, columns, items, groups, users, mutations. Selftest checks.
- **E2E test:** `e2e/tests/37-monday-sync/monday-sync.spec.ts` — install → auth → configure column mapping → sync → verify → push lifecycle.
- **User guide:** `docs/guide/37-monday-sync.md` — Monday.com setup, column mapping walkthrough, status label mapping, troubleshooting.

## Constraints

- **GraphQL-only API** — single endpoint at `https://api.monday.com/v2`. No REST alternative.
- **Complexity-based rate limiting** — 10M points/min (paid), 5M per query. Nested board→items→column_values queries consume heavily. Must paginate and flatten queries.
- **No delta query** — no `updatedAt` filter. Each poll fetches all items. Content comparison needed for change detection.
- **Column values are JSON strings** — `change_column_value` and `change_multiple_column_values` mutations accept column values as JSON-encoded strings, not typed values. The exact JSON shape varies by column type.
- **App Platform SDK IRI prefix enforcement** — Same D204 workaround as all prior sync apps.
- **htmx template URLs must use `/app/monday-sync/` prefix** — per KNOWLEDGE.md.
- **API versioning** — Monday.com has quarterly API versions. Pin to `2026-01` (current stable) via `API-Version` header.

## Common Pitfalls

- **Column IDs are board-specific** — A "Status" column on Board A has a different ID than on Board B. Column mapping must be stored per-board or validated when boards change.
- **Status column labels are fully custom** — Unlike Jira's statusCategory or Linear's state.type, Monday.com status columns have arbitrary user-defined labels with custom colors. There is no normalization layer — the user must manually map each label to a bpkm:taskStatus value.
- **Nested query complexity explosion** — Querying `boards { items { column_values } }` with nested groups can exceed 5M complexity per query. Must paginate items (limit 100-200) and possibly query items separately from board metadata.
- **Column value write format differs from read format** — The JSON format for reading column values (from query responses) differs from the format for writing (in mutations). Status reads as `{label, index}` but writes as `{index: N}` or `{label: "Done"}`. Must handle both.
- **People column returns user IDs, not emails** — Need a follow-up `{ users(ids: [...]) { email } }` query to resolve person emails for PersonMatcher. Cache aggressively.
- **Subitems are on a separate board** — Monday.com subitems live on an auto-generated "subitems board", not the parent board. Querying subitems requires a separate query. This adds API complexity cost.
- **Tags column returns tag IDs, not names** — Need `{ tags(ids: [...]) { name } }` to resolve tag names. Or use `text` representation from column_values.

## Open Risks

- **Column mapping UI complexity** — If a user selects 3 boards with different column schemas, the mapping UI must handle the union or require per-board configuration. Recommend: per-board mapping stored as `{board_id: {column_mapping, status_mapping, priority_mapping}}`.
- **No updated_at for change detection** — Without a server-side timestamp filter, every poll fetches all items. For large boards (1000+ items), this could be slow and consume significant API complexity budget. May need to implement client-side change detection (hash current values, compare with stored hashes).
- **Subitem depth on non-Enterprise** — Subitems are limited to 1 level on standard plans, up to 5 on Enterprise. The sync app should handle whatever depth is available gracefully.
- **Monday.com API version deprecation** — Quarterly releases with 6-month deprecation. Must document which API version the app targets and plan for updates.

## Candidate Requirements

| ID | Description | Class |
|----|-------------|-------|
| MON-01 | Monday.com API token authentication (store/verify/disconnect) | core-capability |
| MON-02 | Board selection with column schema discovery | core-capability |
| MON-03 | User-configurable column→property mapping (status, priority, date, assignee, etc.) | core-capability |
| MON-04 | Status label→bpkm:taskStatus configurable mapping | core-capability |
| MON-05 | Priority label→bpkm:priority configurable mapping | core-capability |
| MON-06 | Pull sync (Monday items → bpkm:Task) with configurable field transforms | core-capability |
| MON-07 | Board groups as taskGroup values | core-capability |
| MON-08 | Subitem → bpkm:parentTask linking | core-capability |
| MON-09 | Push sync (bpkm:Task → Monday items) with reverse column value mutations | core-capability |
| MON-10 | LoopGuard echo prevention for push→poll cycle | core-capability |
| MON-11 | Dependency column → bpkm:dependsOn edges | core-capability |
| MON-12 | Tag column → bpkm:tags mapping | core-capability |
| MON-13 | Person matching (Monday user IDs → Person objects via email) | core-capability |
| MON-14 | E2E tests + mock Monday.com GraphQL server | quality-attribute |
| MON-15 | User guide Chapter 37 | quality-attribute |

## Sources

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §2 — complete Monday.com entity/field/status mapping tables, LoopGuard design, API characteristics
- Monday.com GraphQL API docs — single endpoint, complexity-based rate limits, column value types, versioning
- Monday.com webhook ecosystem research — no webhook suppression, fire-and-forget delivery, challenge verification, minimal payloads requiring follow-up queries
- M022 (Asana) research — configurable field mapping pattern (D228) directly applicable
- 7 prior sync apps (M016-M023) — established architecture, each with 6 services + manifest + templates + tests + docs
