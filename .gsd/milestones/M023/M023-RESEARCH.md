# M023 — Jira Sync App — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

The Jira Sync App is the fourth task-provider sync app on the App Platform (after Linear M016, GitHub M017, Google Calendar M018). The codebase has three complete sync apps to use as templates. The Jira-specific challenges are: (1) Atlassian Document Format (ADF) ↔ Markdown conversion for rich text descriptions, (2) OAuth 2.0 via Atlassian Connect for authentication, and (3) statusCategory-based status normalization across arbitrarily customized Jira workflows.

The design doc (`.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §4) provides complete field mapping, status normalization strategy, and API characteristics. The existing sync apps provide a proven architecture: manifest.yaml → app.py (routes + tasks) → services/ (auth, client, field_mapper, person_matcher, sync_engine) → frontend/templates + static. This is a well-understood pattern — the main technical risk is ADF conversion quality, not architectural novelty.

## Recommendation

Follow the M016 Linear Sync pattern exactly — it's the cleanest reference implementation. Use API key (personal access token) auth for v1 (matching D206 GitHub PAT decision), with OAuth 2.0 as a stretch goal. ADF↔Markdown conversion should use a Python library (e.g. `atlassian-adf-builder` or a lightweight custom converter) rather than hand-rolling a full parser. JQL-based filtered sync is Jira's killer feature — expose it in the settings UI as a text field the user can fill with any valid JQL query.

## Implementation Landscape

### Key Files

**Existing patterns to clone from:**
- `apps/linear-sync/manifest.yaml` — app manifest template (permissions, tasks, UI pages)
- `apps/linear-sync/app.py` — route structure (connect, disconnect, settings, sync-now, task handlers)
- `apps/linear-sync/services/field_mapper.py` — pure-function field mapping with STATUS_MAP, PRIORITY_MAP, reverse maps, `build_task_properties()`, `compute_issue_slug()`
- `apps/linear-sync/services/sync_engine.py` — two-phase bulk create pattern, pull_sync/push_sync, SPARQL change detection
- `apps/linear-sync/services/person_matcher.py` — email-based SPARQL lookup with LRU cache, person creation on miss
- `apps/linear-sync/services/auth.py` — credential storage/retrieval via StateClient
- `apps/linear-sync/services/linear_client.py` — API client with error hierarchy, pagination
- `apps/linear-sync/frontend/templates/connect.html` + `connect_status.html` — settings UI
- `apps/github-sync/services/github_client.py` — REST client with Link-header pagination (Jira uses REST, not GraphQL)
- `apps/google-calendar/services/auth.py` — OAuth 2.0 flow (Jira OAuth is similar)
- `apps/google-calendar/services/gcal_client.py` — REST client with 401→refresh→retry pattern

**New files to create:**
- `apps/jira-sync/manifest.yaml`
- `apps/jira-sync/app.py`
- `apps/jira-sync/requirements.txt`
- `apps/jira-sync/services/__init__.py`
- `apps/jira-sync/services/auth.py` — API token storage + optional OAuth helpers
- `apps/jira-sync/services/jira_client.py` — REST v3 client with JQL search, pagination, rate limiting
- `apps/jira-sync/services/field_mapper.py` — statusCategory normalization, priority mapping, ADF↔MD
- `apps/jira-sync/services/adf_converter.py` — ADF JSON ↔ Markdown conversion (isolated module)
- `apps/jira-sync/services/person_matcher.py` — Jira accountId → Person resolution by email
- `apps/jira-sync/services/sync_engine.py` — pull_sync (JQL search), push_sync (issue update), Epic→Milestone
- `apps/jira-sync/frontend/templates/connect.html`
- `apps/jira-sync/frontend/templates/connect_status.html`
- `apps/jira-sync/frontend/static/styles.css`

### Build Order

1. **ADF converter first** — this is the unique technical risk. Build `adf_converter.py` as a pure module with `adf_to_markdown()` and `markdown_to_adf()`. Test with realistic ADF samples (headings, lists, code blocks, mentions, links, tables, inline cards). If a Python library handles this well, use it; otherwise hand-roll covering the ~10 most common ADF node types.

2. **Field mapper + status normalization** — Pure functions, extensively unit-testable. statusCategory.key mapping is the core differentiator (§4 of design doc). Epic→Milestone mapping is configurable (user chooses Epic as Milestone vs Epic as Project).

3. **Jira REST client** — REST v3 with JQL-based search (`POST /rest/api/3/search`), issue detail, issue update. Link-header or `startAt`/`maxResults` pagination. Basic auth (email + API token) header. Error hierarchy matching LinearClient/GitHubClient patterns.

4. **Auth + app scaffold** — API token auth (email + token pair stored via StateClient). Connect/disconnect flow. Manifest with permissions.

5. **Sync engine** — pull_sync with JQL query, push_sync with issue update. Two-phase bulk create pattern from M016. Epic→Milestone sync. Issue link → bpkm:dependsOn edges for "blocks" link type. Sprint → taskGroup, Component → tags.

6. **Settings UI** — Project selection, JQL filter field, sync direction, poll interval, Epic mapping config (Milestone vs Project), Sync Now button.

7. **E2E tests + docs** — Mock Jira REST API server, Playwright E2E test, user guide chapter.

### Verification Approach

- **ADF converter**: Pure unit tests with sample ADF JSON → expected Markdown strings. Cover: headings (1-6), paragraphs, bullet/ordered lists, code blocks (with language), mentions, inline cards/links, tables, nested structures, empty/null input.
- **Field mapper**: Unit tests for all STATUS_MAP entries (statusCategory.key → bpkm:taskStatus), PRIORITY_MAP, reverse maps, `build_task_properties()` with full issue dict, slug computation.
- **Sync engine**: Unit tests with mocked JQL responses. Verify two-phase bulk create, Epic→Milestone creation, issue link → edge creation, Sprint→taskGroup mapping.
- **E2E**: Mock Jira REST API server (similar to mock-github-api pattern) with canned JQL search responses. Playwright test: install app → enter credentials → select project → sync → verify tasks via SPARQL.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| ADF → Markdown | Custom converter covering ~12 common node types | No well-maintained Python ADF↔MD library exists. But the node types are well-documented and finite. A 200-line recursive converter handles the common cases (paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, text with marks, mention, inlineCard, mediaGroup). |
| Markdown → ADF | Simple converter for push-back | Only need to handle the subset of Markdown that SemPKM produces. Paragraphs, headings, lists, code blocks, links. ~150 lines. |
| REST pagination | Adapt GitHubClient pattern | Jira uses `startAt`/`maxResults` offset pagination (not Link headers). Simple while loop. |
| Person matching | Clone from linear-sync/person_matcher.py | Identical SPARQL pattern. Change: Jira uses accountId (not email in API response) — need to call `/rest/api/3/user?accountId=X` to get email. |

## Constraints

- **Jira Cloud REST API v3 only** — no Jira Server/Data Center support (out of scope per CONTEXT)
- **API token auth for v1** — Atlassian API tokens use email + token as Basic auth credentials. Full OAuth 2.0 (3LO via Atlassian Connect) is complex and requires app registration — defer to v2
- **ADF is mandatory** — Jira Cloud v3 API only accepts ADF for description writes. Reading returns ADF JSON. No Markdown option.
- **Rate limit ~100 req/sec burst** — generous for polling. No special handling needed for typical sync volumes.
- **JQL search returns max 100 issues per page** — standard offset pagination with `startAt`/`maxResults`
- **App Platform constraint** — all htmx URLs must include `/app/jira-sync/` proxy prefix (per KNOWLEDGE.md)
- **SDK IRI prefix enforcement** — two-phase bulk create pattern required (D204) because platform-minted Task IRIs use `urn:sempkm:object:` prefix which SDK CommandClient rejects
- **No webhooks for v1** — App Platform doesn't expose external webhook routes (D200, D211). Polling-only via JQL with `updated >= -15m` filter.

## Common Pitfalls

- **ADF complexity underestimation** — ADF has ~30 node types. Don't try to handle all of them. Focus on the ~12 common ones. For unknown node types, emit a placeholder like `[unsupported: {type}]` rather than crashing.
- **Jira statusCategory vs status name** — Status names are custom per project ("In Review", "QA Testing", etc.). Always use `statusCategory.key` (`new`/`indeterminate`/`done`) for normalization. Store the status name in `bpkm:externalStatus` for display.
- **Jira "blocked" has no statusCategory** — The design doc notes this. Map specific status names containing "blocked" to `blocked` as a heuristic, or just let them fall through to `in-progress` (since blocked statuses have `indeterminate` category).
- **Jira Epic is an issue type, not a separate entity** — Epics are queried via JQL `issuetype = Epic`. Their child issues have `parent` or `customfield_10014` (Epic Link). The sync needs to handle this specially.
- **Jira user lookup requires accountId** — Jira v3 API uses opaque `accountId` (not email/username). Getting email requires `GET /rest/api/3/user?accountId=X` — an extra API call per unique assignee. Cache aggressively.
- **Push sync: status transitions require valid transition IDs** — Unlike Linear/GitHub where you can set any status, Jira requires valid workflow transitions. For v1, push title/description/priority changes only. Status push requires `GET /rest/api/3/issue/{key}/transitions` → `POST /rest/api/3/issue/{key}/transitions` pattern. Mark as stretch goal.
- **Markdown → ADF for push** — When user edits description in SemPKM, must convert back to ADF for the Jira API. This is the harder direction. Keep it simple: paragraphs, headings, lists, code blocks, links.

## Open Risks

- **ADF fidelity** — Complex ADF documents (tables with nested lists, media embeds, Jira-specific macros like `{panel}` or `{expand}`) will lose formatting during ADF→MD→ADF round-trip. This is acceptable for v1 but should be documented.
- **Jira Cloud authentication complexity** — Atlassian API tokens (email + token) work for personal use but require the user to generate a token at `id.atlassian.com/manage-profile/security/api-tokens`. OAuth 2.0 (3LO) requires registering a Jira app. API tokens are simpler for v1.
- **Story points custom field** — Jira doesn't have a standard story points field. It's a custom field with an ID that varies per Jira instance (commonly `customfield_10016` or `customfield_10028`). The sync app should either: (a) ask the user which custom field is story points, or (b) search for custom fields named "Story Points"/"Story point estimate" during setup. Start with option (b), fall back to skip.
- **Epic → Milestone mapping ambiguity** — Some users use Epics as projects, others as milestones. The design doc suggests making this configurable. Default to Epic→Milestone (matches CONTEXT scope).

## Candidate Requirements

Based on the design doc analysis and codebase patterns, the following requirements should be registered:

| ID | Requirement | Class | Notes |
|----|-------------|-------|-------|
| JIRA-01 | Jira API token authentication (email + token as Basic auth) | core-capability | Matches D206/GitHub PAT pattern |
| JIRA-02 | Pull sync: Jira issues → bpkm:Task with statusCategory normalization | core-capability | Key differentiator |
| JIRA-03 | ADF → Markdown conversion for issue descriptions | core-capability | Unique technical challenge |
| JIRA-04 | Markdown → ADF conversion for push-back | core-capability | Required for bidirectional |
| JIRA-05 | JQL-based filtered sync | core-capability | Jira's killer feature |
| JIRA-06 | Epic → bpkm:Milestone mapping (configurable) | core-capability | Per design doc |
| JIRA-07 | Issue links ("blocks") → bpkm:dependsOn edges | core-capability | Per design doc |
| JIRA-08 | Sprint → taskGroup, Component → tags | core-capability | Per design doc |
| JIRA-09 | Push sync: title/description/priority changes to Jira | core-capability | Bidirectional |
| JIRA-10 | Settings UI with project selection, JQL filter, sync direction | core-capability | Standard for sync apps |
| JIRA-11 | Person matching: accountId → email → Person resolution | core-capability | Standard pattern |
| JIRA-12 | E2E tests + user guide chapter | quality-attribute | Standing requirement |

**Advisory (not requirements):**
- Status transition push via Jira workflow transitions — defer to v2 (complex, requires per-project transition discovery)
- Story points custom field auto-discovery — nice-to-have, default to skip if not found
- OAuth 2.0 (3LO) — defer to v2 (API token sufficient for personal use)

## Slice Boundary Recommendations

Based on the build order and risk profile, recommended slicing:

1. **S01: ADF converter + field mapper** — Pure functions, no SDK/platform dependency. Proves the hardest technical risk first. ~100 unit tests.
2. **S02: Jira REST client + auth** — JiraClient with JQL search, pagination, auth. App scaffold with manifest + connect/disconnect UI. ~40 unit tests.
3. **S03: Pull sync + settings UI** — Sync engine with pull_sync, Epic→Milestone, issue links, Sprint/Component mapping. Settings UI with project selection and JQL filter. ~60 unit tests.
4. **S04: Push sync** — Reverse field mapping, issue update API, loop prevention. ~30 unit tests.
5. **S05: E2E tests + user guide** — Mock Jira REST API server, Playwright E2E test, Chapter 36 user guide.

## Sources

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §4 — Complete Jira field mapping, statusCategory strategy, ADF conversion notes, API characteristics
- Existing apps: `apps/linear-sync/`, `apps/github-sync/`, `apps/google-calendar/` — Proven sync app architecture
- Decisions D199-D214 — Sync app auth, polling, and conflict resolution patterns
- KNOWLEDGE.md — App template htmx URL proxy prefix requirement, SDK IRI prefix enforcement, two-phase bulk create pattern
