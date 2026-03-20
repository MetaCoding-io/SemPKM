# M023: Jira Sync App

**Vision:** Jira Cloud bidirectional sync app — Jira issues sync to bpkm:Task objects with ADF→Markdown description conversion, statusCategory-based status normalization, JQL-based filtered sync, and Epic→Milestone mapping.

## Success Criteria

- User installs Jira Sync app, enters email + API token, and verifies connection to their Jira Cloud instance
- User selects Jira projects to sync and optionally enters a JQL filter query
- Jira issues appear as bpkm:Task objects with Markdown-converted descriptions (from ADF), correct status (via statusCategory.key), priority, assignee, labels, sprint, and components
- Jira Epics appear as bpkm:Milestone objects with linked child tasks
- Issue links of type "blocks" create bpkm:dependsOn edges between tasks
- User edits task title/description/priority in SemPKM, changes push back to Jira via REST API
- 200+ unit tests pass covering ADF conversion, field mapping, client, person matching, and sync engine
- Mock Jira REST API server passes selftest
- Playwright E2E test exercises full install → configure → sync → verify → push lifecycle
- User guide chapter documents Jira sync with field mapping tables and ADF conversion notes

## Key Risks / Unknowns

- **ADF ↔ Markdown conversion quality** — Jira Cloud v3 uses Atlassian Document Format exclusively for rich text. No well-maintained Python ADF library exists. A custom recursive converter handling ~12 common node types is needed. If the converter doesn't handle real-world ADF documents well, descriptions will be garbled or lost.
- **Markdown → ADF for push-back** — The reverse direction (SemPKM Markdown → Jira ADF JSON) is needed for description push. This is the harder direction because Markdown parsing produces an AST that must be mapped to ADF node types. Limiting to the subset SemPKM produces (paragraphs, headings, lists, code, links) keeps it tractable.

## Proof Strategy

- ADF conversion quality → retire in S01 by building `adf_converter.py` with comprehensive unit tests covering all ~12 common ADF node types (headings, paragraphs, lists, code blocks, blockquotes, tables, text with marks, mentions, inline cards, media groups) plus Markdown→ADF reverse direction. If unit tests pass on realistic ADF samples, the converter is proven.

## Verification Classes

- Contract verification: pytest unit tests for ADF converter, field mapper, client, auth, person matcher, sync engine (~200+ tests). Mock Jira REST API server with selftest.
- Integration verification: Playwright E2E test through Docker Compose stack with mock Jira API
- Operational verification: Structured logging on sync operations, StateClient persistence for sync stats
- UAT / human verification: none (automated tests cover full lifecycle)

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 4 slice deliverables are complete with passing unit tests
- ADF ↔ Markdown converter handles the 12 common node types with round-trip fidelity
- statusCategory-based status normalization maps all 3 categories correctly
- JQL-based filtered sync works with user-provided JQL queries
- Epic → bpkm:Milestone mapping creates linked task hierarchies
- Issue link "blocks" type → bpkm:dependsOn edges
- Push sync updates title/description/priority in Jira
- Mock Jira REST API server passes selftest
- Playwright E2E test passes against Docker Compose stack
- User guide chapter published with field mapping tables
- All JIRA requirements validated with test evidence

## Requirement Coverage

- Covers: JIRA-01, JIRA-02, JIRA-03, JIRA-04, JIRA-05, JIRA-06, JIRA-07, JIRA-08, JIRA-09, JIRA-10, JIRA-11, JIRA-12
- Partially covers: none
- Leaves for later: Status transition push (requires per-project transition discovery — stretch), Story points custom field auto-discovery (nice-to-have), OAuth 2.0 3LO (API token sufficient for v1)
- Orphan risks: none

## Slices

- [x] **S01: ADF converter + field mapper + Jira client + auth scaffold** `risk:high` `depends:[]`
  > After this: User can install the Jira Sync app, enter email + API token, verify connection, see project list with selection checkboxes. ADF→Markdown and Markdown→ADF conversion proven by 60+ unit tests. Field mapper with statusCategory normalization and priority mapping proven by 40+ unit tests.
- [x] **S02: Pull sync + settings UI** `risk:medium` `depends:[S01]`
  > After this: User triggers sync and Jira issues appear as bpkm:Task objects with Markdown descriptions, correct status/priority/assignee, sprint as taskGroup, components and labels as tags. Epic→Milestone mapping creates linked hierarchies. Settings UI has project selection, JQL filter field, sync direction, poll interval, and Sync Now button.
- [x] **S03: Push sync + issue links** `risk:low` `depends:[S02]`
  > After this: User edits task title/description/priority in SemPKM and changes push back to Jira. Issue links of type "blocks" create bpkm:dependsOn edges. Full bidirectional sync loop works with loop prevention.
- [x] **S04: E2E tests + user guide** `risk:low` `depends:[S03]`
  > After this: Mock Jira REST API server passes selftest. Playwright E2E test exercises full install → configure → sync → verify lifecycle. Chapter 41 user guide published with field mapping tables, statusCategory explanation, and ADF conversion notes.

## Boundary Map

### S01 → S02

Produces:
- `apps/jira-sync/services/adf_converter.py` — `adf_to_markdown(adf_doc)` and `markdown_to_adf(md_text)` pure functions
- `apps/jira-sync/services/field_mapper.py` — `STATUS_MAP`, `PRIORITY_MAP`, `REVERSE_STATUS_MAP`, `REVERSE_PRIORITY_MAP`, `build_task_properties(issue)`, `compute_issue_slug(project_key, issue_key)`, `build_milestone_properties(epic)`
- `apps/jira-sync/services/jira_client.py` — `JiraClient` with `search_issues(jql, start_at, max_results)`, `get_issue(issue_key)`, `update_issue(issue_key, fields)`, `get_projects()`, `get_user(account_id)`, pagination, error hierarchy
- `apps/jira-sync/services/auth.py` — `store_credentials(state, email, token, site_url)`, `get_credentials(state)`, `clear_credentials(state)`, `get_connection_status(state)`, `build_auth_header(email, token)`
- `apps/jira-sync/services/person_matcher.py` — `PersonMatcher` with `resolve(account_id, display_name, email)` using SPARQL lookup + create-on-miss + LRU cache
- `apps/jira-sync/app.py` — route handlers for connect, disconnect, settings fragment rendering
- `apps/jira-sync/manifest.yaml` — app manifest with permissions and task declarations
- `apps/jira-sync/frontend/templates/connect.html` + `connect_status.html` — auth UI
- `apps/jira-sync/frontend/static/styles.css` — scoped CSS

Consumes:
- nothing (first slice)

### S02 → S03

Produces:
- `apps/jira-sync/services/sync_engine.py` — `pull_sync(ctx, state, jira, field_mapper, person_matcher)` with two-phase bulk create, Epic→Milestone, Sprint→taskGroup, Component→tags
- Settings UI with project selection, JQL filter, sync direction, poll interval, Sync Now trigger
- `poll-issues` task handler wired to real pull_sync

Consumes:
- S01 ADF converter, field mapper, Jira client, auth, person matcher, app scaffold

### S03 → S04

Produces:
- `push_sync(ctx, state, jira)` with SPARQL change detection, reverse field mapping, issue update, loop prevention
- Issue link "blocks" → bpkm:dependsOn edge creation during pull sync
- Full bidirectional sync loop

Consumes:
- S02 pull sync engine, settings UI, sync state

### S04

Produces:
- `e2e/mock-jira-api/server.py` — mock Jira REST API server with selftest
- `e2e/tests/41-jira-sync/jira-sync.spec.ts` — Playwright E2E test
- `docs/guide/41-jira-sync.md` — user guide chapter

Consumes:
- S03 complete Jira sync app (all services, routes, templates, CSS)

---

## Decisions

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D233 | M023 | arch | Jira sync authentication — API token (email + token as Basic auth) for v1, no OAuth 2.0 3LO | API token only. User generates token at id.atlassian.com/manage-profile/security/api-tokens. Stored as email + token pair via StateClient. Basic auth header: base64(email:token). | Atlassian OAuth 2.0 (3LO) requires registering a Jira app with Atlassian developer console, managing client_id/secret, handling complex callback routing, and scope negotiation. API token is simpler and matches D206 (GitHub PAT) pattern. Sufficient for self-hosted single-user use. OAuth can be added in v2. | Yes — add OAuth 2.0 3LO for multi-user production |
| D234 | M023 | tech | ADF ↔ Markdown conversion — custom recursive converter, not library | Hand-roll a ~300-line recursive converter covering ~12 common ADF node types (paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, text with marks, mention, inlineCard, mediaGroup, rule). Unknown node types emit `[unsupported: {type}]` placeholder. | No well-maintained Python ADF↔MD library exists. The node types are well-documented and finite. A focused converter covering common types is more reliable than depending on an unmaintained package. The reverse direction (MD→ADF) only needs to handle the Markdown subset SemPKM produces. | Yes — switch to library if a well-maintained one appears |
| D235 | M023 | tech | Jira status normalization via statusCategory.key, not status name | Always use `statusCategory.key` (new/indeterminate/done) for status mapping, never `status.name` (which is custom per project). Store `status.name` in `bpkm:externalStatus` for display. | Status names are arbitrarily customizable per Jira project ("In Review", "QA Testing", etc.). statusCategory.key is the only reliable normalization point — it maps every custom status to exactly one of three categories. This is Jira's designed abstraction for cross-project status comparison. | No |
| D236 | M023 | scope | Jira requirement IDs use JIRA- prefix | Requirements numbered JIRA-01 through JIRA-12. | Follows D209 (GH- for GitHub) and D230 (ASANA- for Asana) pattern — provider-specific prefix avoids collision and makes requirements identifiable by provider. | No |
| D237 | M023 | scope | Push sync limited to title/description/priority for v1 — no status transitions | Status push requires discovering valid workflow transitions per issue via GET /transitions then POST /transitions with transition ID. This per-project workflow discovery adds significant complexity. Defer to v2. | Jira requires valid transition IDs for status changes (unlike Linear/GitHub where you set any status directly). Per-project transition discovery and validation is a separate concern from basic field sync. Title/description/priority PATCH is sufficient for v1 bidirectional capability. | Yes — add status transition push in v2 |
| D238 | M023 | tech | Jira person resolution requires extra API call per unique accountId | Jira v3 API uses opaque accountId (not email). Getting email requires GET /rest/api/3/user?accountId=X. Cache aggressively via PersonMatcher LRU cache. | Jira's GDPR-compliant API removed email from issue response data. The extra API call is unavoidable but the LRU cache (same pattern as all other sync apps) means each unique user is looked up only once per sync run. | No |
