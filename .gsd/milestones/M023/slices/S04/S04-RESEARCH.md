# S04 — E2E Tests + User Guide — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

S04 is straightforward pattern-following work. The codebase has two complete sync app E2E implementations (Linear M016/S04 and GitHub M017/S04) that provide exact templates for all three deliverables: mock API server, Playwright E2E test, and user guide chapter. The Jira sync app (S01–S03) is fully built with all routes, templates, and services in place.

The mock Jira REST API server needs ~7 endpoints matching `JiraClient`'s method calls (GET `/rest/api/3/myself`, GET `/rest/api/3/project`, POST `/rest/api/3/search`, GET `/rest/api/3/user`, PUT `/rest/api/3/issue/{key}`, plus `/health`). The E2E test follows the exact same phase structure as the Linear/GitHub tests (cleanup → install basic-pkm → install app → open workspace → connect → select projects → configure sync → Sync Now → verify via SPARQL → admin check → cleanup). The user guide is Chapter 36, following Ch 35 (GitHub Sync), and covers the same sections with Jira-specific content (statusCategory explanation, ADF conversion notes, JQL filter documentation, Epic→Milestone mapping).

## Recommendation

Clone the mock-github-api server pattern (REST, not GraphQL), adapt the E2E test from github-sync.spec.ts (closest match — both REST-based, similar UI elements), and write Chapter 36 following the exact structure of Chapter 35 with Jira-specific field mapping tables and notes. No new libraries or unfamiliar technology needed.

## Implementation Landscape

### Key Files

**Templates to clone from:**
- `e2e/mock-github-api/server.py` — REST mock server pattern (URL-path matching, selftest mode, fake handler for selftest). Clone this, not mock-linear-api (which is GraphQL-based).
- `e2e/tests/32-github-sync/github-sync.spec.ts` — E2E test with 12 phases. Jira test will be nearly identical but with Jira-specific selectors and 3 fields for connect (email + token + site_url) instead of 1 (PAT).
- `e2e/helpers/selectors.ts` — Needs `jiraSync` selector block added alongside `githubSync` and `linearSync`.
- `docs/guide/35-github-sync.md` — User guide structure to follow. Chapter 36 with Jira-specific content.
- `docs/guide/README.md` — TOC needs Chapter 36 entry.
- `docs/guide/appendix-d-glossary.md` — Needs Jira Sync, Atlassian Document Format, statusCategory glossary entries.

**Existing app code (consumed, not modified):**
- `apps/jira-sync/app.py` — Routes: `/_fragments/connect` (GET), `/_fragments/connect/credentials` (POST), `/_fragments/connect/disconnect` (POST), `/_fragments/settings/projects` (POST), `/_fragments/settings/sync-config` (POST), `/_fragments/settings/sync-now` (POST)
- `apps/jira-sync/services/jira_client.py` — `JIRA_API_URL` env var override for testing. Endpoints to mock: `GET /rest/api/3/myself`, `GET /rest/api/3/project`, `POST /rest/api/3/search`, `GET /rest/api/3/user?accountId=X`, `PUT /rest/api/3/issue/{key}`
- `apps/jira-sync/frontend/templates/connect.html` — Form IDs: `#jira-email`, `#jira-token`, `#jira-site-url`. Form class: `.credentials-form`. Button: `.credentials-form button[type="submit"]`.
- `apps/jira-sync/frontend/templates/connect_status.html` — `.connection-status`, `.project-checkbox-item input[type="checkbox"]`, `.projects-section button[type="submit"]`, `input[name="sync_direction"]`, `.sync-config-form`, `#sync-now-btn`, `.sync-stats`
- `apps/jira-sync/services/field_mapper.py` — STATUS_MAP, PRIORITY_MAP, tag extraction (labels + components), Sprint→taskGroup mapping tables needed for user guide.
- `apps/jira-sync/manifest.yaml` — App name "Jira Sync", icon "ticket", tasks poll-tasks/push-changes.

**Docker config to modify:**
- `docker-compose.test.yml` — Add `mock-jira` service (same pattern as mock-linear/mock-github) and `JIRA_API_URL: http://mock-jira:8080` env var on the api container.

### Build Order

1. **Mock Jira REST API server** — Build `e2e/mock-jira-api/server.py` first. Must be runnable and pass `--selftest` before integrating with Docker. The mock needs to respond to the 6 endpoints JiraClient calls. Canned data should include: 2 projects (PROJ/DESIGN), 3 issues (1 in-progress with assignee, 1 to-do unassigned, 1 done epic), 1 user response, 1 search response with those issues, 1 issue update echo-back. Include one issue with `issuelinks` containing a Blocks inward entry so the E2E can verify `bpkm:dependsOn` edge creation.

2. **Docker integration** — Add `mock-jira` service to `docker-compose.test.yml` and `JIRA_API_URL` env var to the api container. Add `mock-jira` to the api's `depends_on` with `condition: service_healthy`.

3. **E2E test selectors** — Add `jiraSync` block to `e2e/helpers/selectors.ts` with selectors matching the Jira template IDs: `emailInput: '#jira-email'`, `tokenInput: '#jira-token'`, `siteUrlInput: '#jira-site-url'`, `connectBtn: '.credentials-form button[type="submit"]'`, `connectStatus: '.connection-status'`, `siteUrl: '.site-url'`, `projectCheckbox: '.project-checkbox-item input[type="checkbox"]'`, `saveProjectsBtn: '.projects-section button[type="submit"]'`, `syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]'`, `saveConfigBtn: '.sync-config-form button[type="submit"]'`, `syncNowBtn: '#sync-now-btn'`, `syncStats: '.sync-stats'`.

4. **Playwright E2E test** — `e2e/tests/41-jira-sync/jira-sync.spec.ts` following the 12-phase pattern from github-sync.spec.ts. Key differences from GitHub test: (a) connect form has 3 fields (email, token, site_url) not 1, (b) project selection instead of repo selection, (c) SPARQL verification queries use `bpkm:externalProvider "jira"` to filter, (d) Epic→Milestone ASK query, (e) dependsOn edge ASK query for issue links.

5. **User guide Chapter 36** — `docs/guide/36-jira-sync.md`. Same structure as Ch 35 but with: statusCategory explanation, ADF conversion notes, JQL filter section, Epic→Milestone mapping table, Sprint→taskGroup, Component→tags. Update README.md TOC, glossary, appendix-a (JIRA_API_URL env var), navigation chain (Ch 35 → Ch 36 → Appendix A).

### Verification Approach

- **Mock server:** `python e2e/mock-jira-api/server.py --selftest` must exit 0 with all endpoint checks passing.
- **E2E test:** `npx playwright test e2e/tests/41-jira-sync/jira-sync.spec.ts` against Docker test stack. Must complete all phases (install → connect → sync → SPARQL verify → cleanup).
- **User guide:** File exists at `docs/guide/36-jira-sync.md` with expected sections (Prerequisites, Installing, Connecting, Project Selection, JQL Filter, Sync Configuration, Field Mapping, Status Mapping, Push Sync, Epic→Milestone, Issue Links, Troubleshooting). README.md TOC has Ch 36 entry. Navigation chain links verified.
- **Selectors:** `jiraSync` block present in `e2e/helpers/selectors.ts`.

## Constraints

- **JiraClient uses `JIRA_API_URL` env var** — when set, it overrides the site_url from state. The mock server URL must be set via this env var in docker-compose.test.yml. The connect form still requires a site_url value, but all actual API requests go to `JIRA_API_URL`.
- **Connect form has 3 fields** (email + token + site_url) unlike Linear (1 API key) and GitHub (1 PAT). The E2E test must fill all three.
- **Mock search uses POST not GET** — `JiraClient.search_issues()` uses `POST /rest/api/3/search` with a JSON body containing `jql`, `startAt`, `maxResults`, `fields`. The mock must handle POST on this path.
- **Issue update uses PUT not PATCH** — `JiraClient.update_issue()` uses `PUT /rest/api/3/issue/{key}` with `{"fields": {...}}` body. Different from GitHub's PATCH.
- **Workspace sections start collapsed** (KNOWLEDGE.md) — the E2E test must expand the APPS section header before clicking the Jira Sync leaf.
- **htmx URLs use proxy prefix** (KNOWLEDGE.md) — templates already have `/app/jira-sync/` prefix. No modification needed.
- **Chapter numbering** — Next available chapter is 36 (after Ch 35 GitHub Sync). The user guide naming follows `{NN}-{slug}.md`.
- **Navigation chain** — Ch 35's "Next" link currently points to Appendix A. Must update Ch 35's footer to point to Ch 36, and Ch 36's footer points to Appendix A.

## Common Pitfalls

- **Mock search must return nested `fields` structure** — The Jira REST API returns issues with `{"key": "PROJ-1", "id": "10001", "fields": {"summary": "...", "status": {"statusCategory": {"key": "new"}}, ...}}`. The field_mapper reads from `issue["fields"]`. The mock must use this nested structure, not flat fields.
- **Epicissuetype detection is case-insensitive** — `sync_engine.py` checks `type_name == "epic"` after lowercasing. Mock epic must have `fields.issuetype.name = "Epic"` (capitalized — sync engine lowercases it).
- **Issue links structure** — The mock must include `issuelinks` in the correct Jira format: `[{"type": {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"}, "inwardIssue": {"key": "PROJ-1", ...}}]`. The sync engine processes only inward entries per D240.
- **The `get_user` endpoint needs `accountId` query parameter** — The mock must parse the accountId from the query string, not from the URL path.
