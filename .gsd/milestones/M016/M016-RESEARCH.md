# M016: Linear Sync App — Research

**Date:** 2026-03-18

## Summary

M016 builds the first task provider sync app on the M009 App Platform, connecting Linear's GraphQL API to SemPKM's `bpkm:Task` type via bidirectional sync. The foundation is solid: the App Platform SDK (M009) provides scoped clients (commands, graph, state, http, settings), task scheduling, and 3-level frontend integration — all battle-tested by the RSS Reader app (M010). The `bpkm:Task` type (basic-pkm v2.0 from M011) already ships integration properties (`externalId`, `externalUrl`, `externalProvider`, `lastSyncedAt`, `syncDirection`, `externalStatus`, `storyPoints`, `dependsOn`, `parentTask`, `taskProject`). The integration design doc (`.gsd/design/INTEGRATION-DOMAIN-MAPPING.md`) has complete field mapping, status normalization, and API characteristics for Linear.

Linear is the right first sync target. Its `state.type` enum (backlog/unstarted/started/completed/cancelled) maps cleanly to `bpkm:taskStatus` without user configuration. Its GraphQL API supports `updatedAt` filtering for delta sync. Its webhook payloads include full changed data (unlike Asana/Monday which send IDs only). Priority is a clean 0–4 numeric mapping. This means the Linear app can establish the sync pattern with minimal normalization ambiguity — subsequent providers (GitHub, Todoist, Asana, Jira) will need user-configurable mapping that adds scope.

The main risks are: OAuth redirect flow in Docker (localhost callback must be reachable), webhook delivery to local instances (polling-only for local dev), and push-back conflict resolution (field-level comparison needed when both sides change). The RSS Reader app provides the structural pattern (manifest, pure helpers, importlib testing, HX-Trigger state sync, CSS scoping) but sync apps introduce new patterns: OAuth flow, delta sync cursor, external→internal IRI mapping, bidirectional change detection, and conflict resolution.

## Recommendation

Build in this order: (1) OAuth + basic manifest/skeleton, (2) pull sync (poll-tasks fetching issues into bpkm:Task), (3) push sync (detecting SemPKM changes and writing back to Linear), (4) settings UI for team/project selection and sync controls, (5) admin detail page with sync history, (6) E2E tests + user guide. OAuth first because nothing works without credentials. Pull sync second because it's the core value prop and validates the full field mapping. Push sync third because it depends on pull sync's IRI mapping infrastructure. Defer webhook processing — polling covers the core UX and webhooks can't reach localhost anyway.

## Implementation Landscape

### Key Files

**Existing platform infrastructure (no changes needed):**
- `backend/sdk/sempkm_app_sdk/` — App SDK with all 5 clients (commands, graph, state, http, settings), task/route/lifecycle decorators, template rendering
- `backend/app/apps/manager.py` — AppManager with install/start/stop/restart/uninstall, crash recovery, auto-start
- `backend/app/apps/scheduler.py` — AppScheduler with interval triggers, concurrency guard, retry
- `backend/app/apps/proxy.py` — AppProxy forwarding HTTP to app UDS with query-string fix (M010)
- `backend/app/apps/admin_router.py` — Admin portal (list, detail, install/start/stop/restart/uninstall)
- `apps/test-app/` — Reference implementation showing manifest structure and all SDK integration points

**Model already exists (no changes needed):**
- `models/basic-pkm/ontology/basic-pkm.jsonld` — Task type with all integration properties (externalId, externalUrl, externalProvider, lastSyncedAt, syncDirection, externalStatus, storyPoints, dependsOn, parentTask, taskProject, assignedTo)
- `models/basic-pkm/shapes/basic-pkm.jsonld` — TaskShape with SHACL constraints (status enum: todo/in-progress/done/blocked/cancelled; priority enum: low/medium/high/critical)
- `models/basic-pkm/views/basic-pkm.jsonld` — Task table/cards/graph views

**New files to create:**
- `apps/linear-sync/manifest.yaml` — App manifest with permissions, tasks, UI declarations
- `apps/linear-sync/app.py` — Core app: OAuth callback route, poll-tasks handler, push-changes handler, settings/admin fragments
- `apps/linear-sync/services/linear_client.py` — Linear GraphQL API client wrapper (auth, query builder, pagination, rate limit handling)
- `apps/linear-sync/services/sync_engine.py` — Bidirectional sync engine: pull (Linear→SemPKM), push (SemPKM→Linear), IRI mapping, conflict resolution
- `apps/linear-sync/services/field_mapper.py` — Field mapping between Linear issue fields and bpkm:Task properties, status/priority normalization
- `apps/linear-sync/requirements.txt` — httpx (for GraphQL), maybe gql
- `apps/linear-sync/frontend/templates/` — Settings page, admin detail, OAuth callback landing
- `apps/linear-sync/frontend/static/styles.css` — Scoped CSS
- `models/basic-pkm/` — May need minor additions if any sync-specific properties are missing (e.g. `bpkm:externalStatus` display in task views)

**Design reference (read-only):**
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Linear — complete field mapping, status normalization (state.type → taskStatus), priority mapping (0–4 → enum), API characteristics

### Build Order

**Prove OAuth + manifest first.** The app is useless without Linear API credentials. OAuth is a new pattern for the platform — the RSS Reader used API keys (simpler). OAuth involves: user clicks "Connect" → redirect to Linear authorization URL → Linear redirects back with code → app exchanges code for access token → store token in app state. This validates that the platform's route handling can support OAuth callback URLs and that token storage via StateClient works for credentials.

**Pull sync second — it's the core value.** Once OAuth works, implement `poll-tasks` as a scheduled task: query Linear's `issues` via GraphQL with `updatedAt` filter, map fields to bpkm:Task properties via field_mapper, create/update objects via CommandClient (bulk for initial sync, standard for incremental). This exercises the full data pipeline and proves the field mapping. The IRI mapping table (Linear issue ID → SemPKM task IRI) is established here and reused by push sync.

**Push sync third — depends on pull infrastructure.** Detect changes to Linear-synced tasks by querying tasks with `bpkm:externalProvider "linear"` and comparing `dcterms:modified` against `bpkm:lastSyncedAt`. For changed tasks, use field_mapper in reverse to build a Linear mutation, then call the Linear API. Conflict resolution logic lives here.

**Settings + admin UI last.** These are important for usability but don't affect core sync correctness. Settings page for team/project selection, sync direction toggle, poll interval. Admin detail shows sync run history, last sync time, object counts.

### Verification Approach

**Unit tests (pure functions):** field_mapper (status normalization, priority mapping, field round-trip), sync_engine (IRI mapping CRUD, change detection, conflict resolution), linear_client (GraphQL query construction, pagination, error handling). Target: 100+ unit tests following M010 pattern (importlib.util.spec_from_file_location for app module loading).

**E2E test:** Install basic-pkm model → install linear-sync app → configure OAuth (mock or test credentials) → trigger poll → verify tasks appear with correct properties → modify a task → verify push-back. Docker-based, following M010's 15-phase pattern. May need to mock the Linear API for reliable CI.

**Manual verification:** OAuth flow with a real Linear workspace in the Docker dev stack.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| GraphQL HTTP requests | `httpx` (already in SDK) | SDK's HttpClient wraps httpx with domain enforcement. Linear's GraphQL API is just POST to `https://api.linear.app/graphql` — no special client needed. Avoid `gql` library to keep dependencies minimal. |
| OAuth 2.0 code exchange | Manual httpx POST | OAuth code exchange is a single POST — no library needed. `authlib` is overkill for one provider. |
| Markdown ↔ Markdown | None needed | Linear stores description as Markdown, bpkm uses Markdown body. Direct mapping, no conversion. |
| Field mapping | Custom pure functions | No library exists for RDF↔GraphQL field mapping. Pure functions are testable and provider-specific. |
| IRI minting | SHA-256 hash pattern from M010 | `urn:sempkm:app:linear-sync:issue-{sha256(workspace_id + issue_id)[:16]}` — deterministic, collision-resistant, follows RSS Reader article IRI pattern (D180). |
| Delta sync cursor | StateClient key-value | `ctx.state.set("last_sync_at", timestamp)` — simple, persistent, app-scoped. |

## Constraints

- **SDK IRI prefix enforcement (D179):** All IRIs created by the app must start with `urn:sempkm:app:linear-sync:` for subject/object IRIs within the app namespace. References to model types (e.g., `urn:sempkm:model:basic-pkm:Task`) pass through unchecked.
- **SDK CommandClient permission model:** App manifest must declare all command types used (object.create, object.patch, body.set/body.diff, edge.create). IRI params on patch/edge commands are prefix-checked.
- **HttpClient domain enforcement:** Manifest must list `api.linear.app` in `network.domains`.
- **StateClient uses SPARQL UPDATE:** The `/api/sparql` endpoint only supports SELECT for apps (Knowledge: "SPARQL API Does Not Support UPDATE/DELETE"). StateClient uses a separate internal graph API route for updates — confirm this works for OAuth token storage.
- **No webhook endpoint exposed:** The App Platform doesn't expose app routes to external traffic — only platform-proxied internal routes (`/app/{appId}/_fragments/*`). Linear webhooks would need a new platform feature (external webhook routing). Defer to polling-only for v1.
- **Bulk EventStore (D145):** Use `ctx.commands.bulk()` for initial sync (potentially hundreds of issues). Standard `ctx.commands.execute()` for incremental updates.
- **Task scheduler concurrency guard:** Only one `poll-tasks` run at a time — if a poll is still running when the next interval fires, it's skipped. Good for preventing duplicate sync.
- **browserVisible consideration:** Linear sync may create internal bookkeeping objects (sync cursors, team metadata). Consider `browserVisible: false` for these types if they're added — but initially all data will be `bpkm:Task` objects which are already browser-visible.

## Common Pitfalls

- **OAuth state parameter:** Linear OAuth requires a `state` parameter for CSRF protection. The app must generate a random state, store it (in StateClient or in-memory), and verify it on callback. Without this, the callback is vulnerable to CSRF.
- **Token refresh:** Linear OAuth tokens expire. The app must handle 401 responses by refreshing the token using the refresh_token. Store both access_token and refresh_token in StateClient.
- **Rate limiting:** Linear allows 1500 requests/hour with complexity-based GraphQL limits. Initial sync of a large workspace could exhaust this. Implement exponential backoff on 429 responses and page results (100 issues per page).
- **Deleted issues:** Linear soft-deletes issues (they have a `trashed` boolean). The sync engine needs to detect trashed issues and update the SemPKM task status to "cancelled" (or leave as-is with an `archived` flag). Don't delete SemPKM objects — data should be preserved.
- **Assignee matching by email:** Linear users have email addresses. The sync engine should look up existing `bpkm:Person` objects by email via SPARQL. If not found, create a new Person. This is a cross-type reference — ensure IRI prefix allows it (D179 confirms model type IRIs pass through).
- **Push-back loop prevention:** When the sync app pushes a change to Linear, the next poll will see that change as "updated." The sync engine must track which changes it pushed (by comparing `lastSyncedAt` timestamps or maintaining a `pending_pushes` set) to avoid re-importing its own changes.
- **GraphQL query complexity:** Fetching all issue fields in one query (issue + labels + assignee + project + parent + relations) is efficient but may hit complexity limits for large result sets. Start with essential fields, add relations in a follow-up query if needed.

## Open Risks

- **OAuth redirect in Docker:** The OAuth callback URL `http://localhost:3000/app/linear-sync/_fragments/oauth-callback` must be registered with Linear. Linear may reject `localhost` as a redirect URI in production OAuth apps — but personal API tokens (not OAuth) might be a simpler v1 alternative. Research needed during execution.
- **StateClient for secrets:** OAuth tokens stored via StateClient are in the RDF triplestore as plain string literals. They're in a per-app named graph (not in `urn:sempkm:current`), but there's no encryption at rest. This is acceptable for a self-hosted local instance but should be flagged for future hardening.
- **Person matching quality:** Email-based lookup may produce false negatives if SemPKM Person objects don't have email addresses, or false positives if emails are shared across contacts. V1 can accept this — create new Person objects on miss and let the user merge duplicates.
- **Large workspace initial sync:** A workspace with 5000+ issues will take multiple paginated queries and a large bulk commit. The platform's bulk EventStore has a 1000-ops-per-batch limit — initial sync may need multiple batches. Progress indication in admin UI would be nice but is non-trivial.
- **Push-back scope:** Should ALL changes to synced tasks be pushed back, or only specific fields? The integration design doc says status=provider-wins, title/description=last-write-wins. Implementing field-level conflict resolution requires storing the last-known provider state for comparison — adds complexity.

## Candidate Requirements

Based on the milestone context and integration design doc, these are the natural requirements:

| ID | Description | Priority | Notes |
|----|-------------|----------|-------|
| SYNC-01 | Linear OAuth authentication flow | Must | App connects to Linear workspace via OAuth or API key. Token stored securely. |
| SYNC-02 | Pull sync — Linear issues → bpkm:Task | Must | Scheduled task fetches issues, maps fields, creates/updates tasks. Delta sync via updatedAt. |
| SYNC-03 | Push sync — bpkm:Task changes → Linear | Should | Detect changes to synced tasks, push back to Linear API. Field-level conflict resolution. |
| SYNC-04 | Settings UI — team/project selection, sync controls | Must | User selects which Linear teams/projects to sync. Configure sync direction and poll interval. |
| SYNC-05 | Admin sync history — run status, counts, errors | Should | Admin detail page shows sync run history with success/failure, objects synced, errors. |
| SYNC-06 | Person matching — assignee email → bpkm:Person | Should | Look up or create Person objects for Linear assignees. |
| SYNC-07 | Linear provider icon and external link on synced tasks | Should | Tasks show Linear icon badge and clickable link to Linear issue. |

**Recommendation:** SYNC-01, SYNC-02, and SYNC-04 are table stakes — without them there's no usable app. SYNC-03 (push sync) is the differentiator for "bidirectional" but could be a separate slice if scope pressure requires. SYNC-05–07 are quality-of-life that round out the experience.

**Deferred from v1 (per milestone context "Out of Scope"):**
- Linear comments sync
- Linear project/cycle as dashboard
- Linear attachments
- Linear custom views
- Multiple Linear workspace support
- Webhook processing (no platform support for external webhook routing)

## Sources

- Linear GraphQL API: schema supports `issues(filter: {updatedAt: {gte: "..."}})` for delta sync, `issueUpdate(id, input)` for push-back
- Linear OAuth: standard code flow with `https://linear.app/oauth/authorize` and `https://api.linear.app/oauth/token`
- Integration design doc: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Linear — authoritative field mapping reference
- RSS Reader app (M010): reference pattern for SDK app development — pure helpers, importlib testing, HX-Trigger sync, CSS scoping
- Test app (`apps/test-app/`): manifest structure reference showing all SDK integration points
- SDK source (`backend/sdk/sempkm_app_sdk/`): 5 clients (commands, graph, state, http, settings), AppContext with lazy init, permission enforcement
