# S02: Pull Sync — Linear Issues to bpkm:Task — Research

**Date:** 2026-03-18

## Summary

S02 builds the pull sync pipeline: `poll-tasks` fetches Linear issues via GraphQL, maps fields to `bpkm:Task` properties, and creates/updates objects via the command API. The integration design doc (`.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §3 Linear) provides authoritative field mapping. The bpkm:Task type already has all the integration properties needed (`externalId`, `externalUrl`, `externalProvider`, `lastSyncedAt`, `syncDirection`), plus standard fields (`taskStatus`, `priority`, `dueDate`, `completedDate`, `assignedTo`, `tags`, `dependsOn`, `taskProject`). Linear's `state.type` enum maps cleanly to `bpkm:taskStatus` without user configuration.

Three new modules: `field_mapper.py` (pure mapping functions), `sync_engine.py` (orchestrator: query → diff → create/update), and `person_matcher.py` (email-based Person lookup/creation). The field mapper is fully unit-testable as pure functions. The sync engine coordinates LinearClient pagination, field mapping, SPARQL lookups for existing objects, and bulk command submission.

One significant constraint: the SDK `CommandClient` enforces IRI prefix checking (`urn:sempkm:app:linear-sync:`) on `object.patch`, `body.set`, and `body.diff` commands. But Task objects are created by the platform with IRIs under the platform's base namespace (e.g. `https://example.org/data/Task/issue-abc123`), not the app prefix. The sync engine must bypass the SDK's client-side permission check by posting command payloads directly to `/api/commands/bulk` via the platform HTTP client. The server doesn't enforce IRI prefixes.

## Recommendation

Build bottom-up: field mapper (pure, testable) → person matcher (SPARQL-dependent) → sync engine (orchestrates everything) → wire into `poll-tasks` handler. Unit tests for the mapper cover all normalization logic. The sync engine test mocks the LinearClient, GraphClient, and HTTP client.

Use deterministic slugs for IRI stability: `issue-{sha256(workspace_id + issue_id)[:16]}`. This makes the platform-minted IRI predictable (`{base_namespace}/Task/issue-{hash16}`), enabling the sync engine to construct patch IRIs without querying for them first.

Delta sync via `updatedAt` filter on the GraphQL query. First sync has no cursor (fetches all). Subsequent syncs use the stored `last_sync_at` timestamp. Store the cursor in StateClient.

## Implementation Landscape

### Key Files

**Existing (read, no changes):**
- `apps/linear-sync/services/linear_client.py` — `LinearClient` with `query_paginated()`, `get_teams()`, typed exceptions. S02 uses `query_paginated()` for issue fetching.
- `apps/linear-sync/services/auth.py` — `get_connection_status()` to check auth before syncing.
- `apps/linear-sync/manifest.yaml` — Already declares all needed permissions: `object.create`, `object.patch`, `body.set`, `body.diff`, `edge.create`, `sparql.read`, network `api.linear.app`.
- `backend/sdk/sempkm_app_sdk/clients/commands.py` — `CommandClient` with `bulk()` context manager. **Note:** `BulkAccumulator.add()` enforces IRI prefix check — sync engine must bypass this for `object.patch`/`body.set` commands on platform-minted IRIs.
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — `GraphClient.query()` posts SPARQL to `/api/sparql` (scoped to `urn:sempkm:current`).
- `backend/app/commands/schemas.py` — Wire format: `{"command": "object.create", "params": {"type": "...", "properties": {...}}}`.
- `backend/app/commands/handlers/object_create.py` — `_resolve_predicate()` handles full IRIs (`urn:...`) and compact IRIs with known prefixes. `bpkm:` prefix is NOT in COMMON_PREFIXES — must use full IRIs like `urn:sempkm:model:basic-pkm:taskStatus`.
- `models/basic-pkm/ontology/basic-pkm.jsonld` — Task type with all integration properties.
- `models/basic-pkm/shapes/basic-pkm.jsonld` — TaskShape with SHACL constraints (status enum: todo/in-progress/done/blocked/cancelled; priority enum: low/medium/high/critical).

**New files to create:**
- `apps/linear-sync/services/field_mapper.py` — Pure functions: `map_issue_to_task()`, `normalize_status()`, `normalize_priority()`, `map_labels_to_tags()`, `build_issue_query()`. All Linear→bpkm mapping logic.
- `apps/linear-sync/services/sync_engine.py` — `pull_sync(ctx)`: fetch issues, diff against existing tasks, create new / update changed, store sync cursor. ~200-300 lines.
- `apps/linear-sync/services/person_matcher.py` — `match_or_create_person(ctx, email, name)`: SPARQL lookup by `foaf:mbox`, create via command API if not found.
- `backend/tests/test_field_mapper.py` — Unit tests for all field mapping and normalization functions.
- `backend/tests/test_sync_engine.py` — Unit tests for sync engine with mocked clients.
- `backend/tests/test_person_matcher.py` — Unit tests for person matching with mocked SPARQL.

**Modified:**
- `apps/linear-sync/app.py` — Replace `poll_tasks` noop with real sync logic: check auth → call `pull_sync(ctx)` → return sync result summary.

### Build Order

**1. Field mapper first** — pure functions, zero dependencies, fully unit-testable. This is the foundation everything else depends on. Covers:
- `normalize_status(state_type: str) -> str` — Linear state.type (backlog/unstarted/started/completed/cancelled) → bpkm:taskStatus (todo/in-progress/done/cancelled). Map `backlog` and `unstarted` to `todo`, `started` to `in-progress`.
- `normalize_priority(priority: int) -> str | None` — Linear 0-4 → bpkm priority. 0 → None (omit), 1 → critical, 2 → high, 3 → medium, 4 → low.
- `map_labels_to_tags(labels: list[dict]) -> list[str]` — Extract label names.
- `build_task_properties(issue: dict, workspace_id: str) -> dict` — Build the full properties dict for `object.create`/`object.patch`. Keys are full IRIs.
- `build_issue_query(team_ids: list[str], updated_after: str | None) -> tuple[str, dict]` — Construct the GraphQL query and variables for paginated issue fetching.
- `compute_issue_slug(workspace_id: str, issue_id: str) -> str` — Deterministic `issue-{sha256[:16]}` for IRI stability.

**2. Person matcher second** — depends on SPARQL via GraphClient. Small module:
- SPARQL query: `SELECT ?person WHERE { { ?person foaf:mbox ?email } UNION { ?person crm:email ?email } } LIMIT 1` scoped to `urn:sempkm:current` (automatic via GraphClient).
- On miss: create a `bpkm:Person` via command API with `foaf:name` and `foaf:mbox`.
- Cache matches in-memory during a single sync run to avoid repeated SPARQL queries.

**3. Sync engine third** — orchestrates LinearClient, field mapper, person matcher, and command submission:
- Check auth status (skip if disconnected)
- Read `last_sync_at` and `sync_teams` from StateClient
- Build GraphQL query with team filter and `updatedAt` cursor
- Paginate through all issues via `LinearClient.query_paginated()`
- For each issue: compute deterministic slug → check if task exists via SPARQL → create or update
- For new issues: `object.create` + `body.set` (description as markdown body) + `edge.create` (assignee, project, parent links)
- For existing issues: compare properties → `object.patch` only if changed + `body.diff` if description changed
- All commands accumulated and submitted as a single bulk batch
- Update `last_sync_at` in StateClient on success
- Return sync result: created count, updated count, unchanged count, errors

**4. Wire into poll-tasks** — modify `app.py` to call `pull_sync(ctx)` from the task handler.

### Verification Approach

**Unit tests (pure functions — no mocks needed for field mapper):**
- `test_field_mapper.py`: status normalization (all 5 Linear state types), priority normalization (0-4 + edge cases), label-to-tag extraction, full property dict construction, GraphQL query construction, slug computation determinism and uniqueness.
- Target: ~30+ tests covering all mapping paths.

**Unit tests (mocked SDK clients):**
- `test_sync_engine.py`: mock LinearClient returning issue fixtures, mock GraphClient returning SPARQL results, mock HTTP client for command submission. Test: new issue creates task, existing issue patches task, unchanged issue skips, description diff triggers body.diff, assignee creates edge, delta cursor filters correctly, bulk batch submitted with correct payloads.
- `test_person_matcher.py`: mock GraphClient for SPARQL lookup. Test: existing person returns IRI, new person creates via command, cache prevents duplicate SPARQL queries.
- Target: ~25+ tests.

**Run:** `cd backend && python -m pytest tests/test_field_mapper.py tests/test_sync_engine.py tests/test_person_matcher.py -v`

## Constraints

- **IRI prefix enforcement bypass:** The SDK's `CommandClient` checks that `iri` params on `object.patch`/`body.set`/`body.diff` start with `urn:sempkm:app:linear-sync:`. But platform-minted Task IRIs use `{base_namespace}/Task/{slug}`. The sync engine must post command payloads directly to `/api/commands/bulk` using `ctx.commands._client` (the shared platform httpx.AsyncClient), bypassing the SDK's client-side check. The server does not enforce IRI prefixes.
- **`bpkm:` prefix not in COMMON_PREFIXES:** The `_resolve_predicate()` function in `object_create.py` does not know the `bpkm` prefix. All property keys in command params must use full IRIs (e.g. `urn:sempkm:model:basic-pkm:taskStatus`), not compact form (`bpkm:taskStatus`). `dcterms:title` and `foaf:mbox` work because `dcterms` and `foaf` are in COMMON_PREFIXES.
- **SPARQL scoped to current graph:** `GraphClient.query()` posts to `/api/sparql` which `scope_to_current_graph()` rewrites to `GRAPH <urn:sempkm:current>`. All task lookup queries see only current state — no event history access. This is correct for sync.
- **StateClient empty-string-as-None:** `StateClient.set()` cannot delete keys; `clear_auth_state` sets them to `""`. `get()` returns `""` not `None` for cleared keys. Sync engine must use `bool()` checks on state values like `last_sync_at`.
- **Bulk batch size limit:** EventStore `commit_bulk()` has a 1000-operation limit per batch. A large initial sync (hundreds of issues, each needing create + body.set + edges) will exceed this. Sync engine must chunk into multiple batches.
- **Task handler return value discarded:** The SDK's `run_task` endpoint returns `{"status": "ok"}` regardless of handler return value. Sync results (counts, errors) should be logged and optionally stored in StateClient for admin UI display (S03).
- **Missing ontology properties:** The design doc mentions `storyPoints`, `externalStatus`, `parentTask`, `startDate`, and `followers` but these do NOT exist in the current `bpkm:Task` ontology or SHACL shapes. S02 maps only to existing properties. Available: `taskStatus`, `priority`, `dueDate`, `completedDate`, `assignedTo`, `taskProject`, `dependsOn`, `tags`, `externalId`, `externalUrl`, `externalProvider`, `lastSyncedAt`, `syncDirection`, `effort`, `milestone`. Linear `estimate` (story points) maps to `effort` as a string ("trivial"/"small"/"medium"/"large"/"epic") — lossy but acceptable. Linear `startedAt` has no bpkm property — omit.
- **SDK `CommandClient.execute()` wire format bug:** The `execute()` method builds `{"type": command_type, ...params}` which overwrites the type key when params contain `"type"`. Use `bulk()` (correct format) or direct HTTP posting.

## Common Pitfalls

- **Pagination variable mutation:** LinearClient's `query_paginated()` already copies the variables dict (fixed in S01). But sync engine code building query variables should also be careful not to mutate shared dicts.
- **Date format mismatch:** Linear returns ISO 8601 datetime strings (e.g. `"2026-03-18T14:30:00.000Z"`). SHACL shape constrains `bpkm:dueDate` to `xsd:date`, not `xsd:dateTime`. The field mapper must truncate to date-only format (`"2026-03-18"`) for date fields. `lastSyncedAt` is `xsd:dateTime` so full ISO format is correct there. See Knowledge K002.
- **Trashed/archived issues:** Linear has a `trashed` boolean on issues. The sync engine should skip trashed issues entirely (not create cancelled tasks for them). If a previously-synced issue gets trashed, the next delta sync will see it in results — update status to `cancelled`.
- **Assignee as edge not property:** `bpkm:assignedTo` is an `owl:ObjectProperty` (range: Person IRI), not a datatype property. It should be set via `edge.create` from Task IRI to Person IRI, not as a string value in `object.create` properties. Same for `taskProject`, `dependsOn`, `milestone`.
- **Empty string properties:** The `_to_rdf_value()` function creates `Literal("")` for empty strings. Sync engine should omit properties with null/empty values rather than setting them to empty string.

## Open Risks

- **Large initial sync performance:** A workspace with 1000+ issues means 1000+ object.create commands, plus body.set and edge.create for each. Even with bulk batching (1000 ops/batch), this could take 30+ seconds. No progress indicator exists in the current admin UI. The sync engine should log progress periodically.
- **Person matching quality:** Email-based SPARQL lookup queries both `foaf:mbox` and `crm:email`. False negatives occur if Person objects don't have emails. The sync engine creates new Person objects on miss — users may need to merge duplicates later.
- **Linear API rate limits:** 1500 requests/hour. Paginated queries (100 issues/page) mean 10 requests for 1000 issues. Well within limits for a single sync run. But combined with viewer/teams queries and token refresh, a rapid poll interval could approach limits. The 15-minute default interval is safe.

## Sources

- Linear GraphQL API: `issues(filter: {team: {id: {in: [...]}}, updatedAt: {gte: "..."}})` for delta sync, paginated with `after` cursor
- Integration design doc: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §3 Linear — authoritative field mapping
- basic-pkm ontology: `models/basic-pkm/ontology/basic-pkm.jsonld` — Task type with 20+ properties
- basic-pkm shapes: `models/basic-pkm/shapes/basic-pkm.jsonld` — TaskShape with SHACL constraints
- SDK CommandClient: `backend/sdk/sempkm_app_sdk/clients/commands.py` — bulk() for batch command submission
- Command API: `backend/app/commands/router.py` — `/api/commands/bulk` endpoint accepts `{commands: [...], summary, source}`
