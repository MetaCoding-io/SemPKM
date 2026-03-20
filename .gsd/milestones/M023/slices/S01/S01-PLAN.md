# S01: ADF converter + field mapper + Jira client + auth scaffold

**Goal:** All Jira Sync service modules (ADF converter, field mapper, Jira REST client, auth, person matcher) are implemented as unit-tested pure/service modules. The app is installable with a manifest, connect/disconnect UI, and project list display.
**Demo:** `cd backend && python -m pytest tests/test_jira_adf_converter.py tests/test_jira_field_mapper.py tests/test_jira_client.py tests/test_jira_auth.py tests/test_jira_person_matcher.py -v` passes 150+ tests. The `apps/jira-sync/` directory contains a complete app scaffold with manifest.yaml, app.py routes, connect.html + connect_status.html templates, and styles.css.

## Must-Haves

- `adf_to_markdown(adf_doc)` handles 12 common ADF node types: paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, text with marks (strong, em, code, link, strike), mention, inlineCard, mediaGroup, rule
- `markdown_to_adf(md_text)` handles the Markdown subset SemPKM produces: paragraphs, headings, lists, code blocks, links
- Unknown ADF node types emit `[unsupported: {type}]` placeholder — never crash
- `STATUS_MAP` maps statusCategory.key: `new`→`todo`, `indeterminate`→`in-progress`, `done`→`done`
- `PRIORITY_MAP` maps Jira priority names: Highest/Critical/Blocker→`critical`, High→`high`, Medium→`medium`, Low→`low`, Lowest/Trivial→`low`
- `REVERSE_STATUS_MAP` and `REVERSE_PRIORITY_MAP` for push sync support
- `build_task_properties(issue)` builds full bpkm property dict from Jira issue JSON
- `build_milestone_properties(epic)` builds property dict for Epic→Milestone mapping
- `compute_issue_slug(project_key, issue_key)` produces deterministic hash-based slugs
- `JiraClient` with `search_issues(jql, start_at, max_results)`, `get_issue(issue_key)`, `update_issue(issue_key, fields)`, `get_projects()`, `get_user(account_id)` — offset pagination, error hierarchy (JiraAPIError, JiraAuthError)
- Auth module: `store_credentials(state, email, token, site_url)`, `get_credentials(state)`, `clear_credentials(state)`, `get_connection_status(state, client)`, `build_auth_header(email, token)`
- `PersonMatcher.resolve(account_id, display_name, email)` with SPARQL lookup, create-on-miss, LRU cache
- `manifest.yaml` with correct permissions, tasks (poll-tasks, push-changes), and UI page
- `app.py` with connect/disconnect/settings routes using `/app/jira-sync/` proxy prefix in htmx URLs
- `connect.html` with email + API token form, `connect_status.html` with project selection checkboxes
- `styles.css` scoped under `.jira-sync-settings`

## Proof Level

- This slice proves: contract (pure-function unit tests + service module API contracts)
- Real runtime required: no (all tests use mocks)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_jira_adf_converter.py -v` — 60+ tests pass covering all 12 ADF node types, Markdown→ADF reverse, empty/null edge cases
- `cd backend && python -m pytest tests/test_jira_field_mapper.py -v` — 40+ tests pass covering status/priority maps, build_task_properties, build_milestone_properties, slug computation, reverse maps
- `cd backend && python -m pytest tests/test_jira_client.py -v` — 25+ tests pass covering JQL search, pagination, error hierarchy, rate limiting, get_projects, get_user, update_issue
- `cd backend && python -m pytest tests/test_jira_auth.py -v` — 15+ tests pass covering credential storage/retrieval, masking, connection status, disconnect
- `cd backend && python -m pytest tests/test_jira_person_matcher.py -v` — 12+ tests pass covering email lookup, account_id fallback, cache hit, person creation
- `python -c "import yaml; yaml.safe_load(open('apps/jira-sync/manifest.yaml'))"` — manifest is valid YAML
- All 5 test files pass together: 150+ total tests

## Observability / Diagnostics

- Runtime signals: structured logging in auth (credential stored/cleared), client (request/response), person_matcher (cache hit/miss/create)
- Inspection surfaces: `get_connection_status()` returns connection state dict; client error hierarchy provides status_code + response_body
- Failure visibility: JiraAuthError (401), JiraAPIError (4xx/5xx with response body), JiraRateLimitError (429 with retry_after)
- Redaction constraints: API token masked in connection status display (`_mask_token`), never logged raw

## Integration Closure

- Upstream surfaces consumed: App SDK (`sempkm-app-sdk` package for App, AppContext, StateClient, HttpClient, CommandClient, GraphClient), existing sync app patterns (github-sync, linear-sync for structure reference)
- New wiring introduced in this slice: `apps/jira-sync/` directory with full app scaffold (manifest, app.py, services/, frontend/)
- What remains before the milestone is truly usable end-to-end: S02 (pull sync engine + settings UI), S03 (push sync + issue links), S04 (E2E tests + user guide)

## Tasks

- [x] **T01: Build ADF↔Markdown converter with 60+ unit tests** `est:2h`
  - Why: ADF conversion is the unique technical risk for this milestone. Building and testing it first retires the highest-risk item. This is a pure module with no dependencies on any other service.
  - Files: `apps/jira-sync/services/adf_converter.py`, `backend/tests/test_jira_adf_converter.py`
  - Do: Build recursive `adf_to_markdown(adf_doc)` handling 12 node types (paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, text with marks, mention, inlineCard, mediaGroup, rule). Build `markdown_to_adf(md_text)` for the reverse direction handling paragraphs, headings, lists, code blocks, links. Unknown types emit `[unsupported: {type}]`. Create `apps/jira-sync/services/__init__.py`. Tests use importlib loading pattern matching `test_github_field_mapper.py`.
  - Verify: `cd backend && python -m pytest tests/test_jira_adf_converter.py -v` — 60+ tests pass
  - Done when: All 12 ADF node types have at least 2 test cases each (happy path + edge case). Markdown→ADF covers paragraphs, headings, lists, code blocks, links. Null/empty input handled gracefully.

- [x] **T02: Build field mapper with statusCategory normalization and 40+ unit tests** `est:1h30m`
  - Why: Field mapper is the second core component — it encodes the statusCategory.key normalization strategy (D235) and priority mapping. Pure functions, no dependencies. Needed by sync engine in S02.
  - Files: `apps/jira-sync/services/field_mapper.py`, `backend/tests/test_jira_field_mapper.py`
  - Do: Implement STATUS_MAP (statusCategory.key→bpkm), PRIORITY_MAP (Jira name→bpkm), REVERSE_STATUS_MAP, REVERSE_PRIORITY_MAP. `build_task_properties(issue, person_iri, sync_time)` mapping all fields from design doc (title, status via statusCategory, priority, dueDate, assignee, labels, components as tags, sprint as taskGroup, externalId as issue key, externalUrl, externalProvider="jira"). `build_milestone_properties(epic)` for Epic→Milestone. `compute_issue_slug(project_key, issue_key)` with sha256 hash. `build_issue_patch(task_props)` for reverse mapping (push sync). Tests use importlib loading pattern.
  - Verify: `cd backend && python -m pytest tests/test_jira_field_mapper.py -v` — 40+ tests pass
  - Done when: All 3 statusCategory.key values mapped. All 5+ Jira priority names mapped. build_task_properties tested with full issue dict. Reverse maps tested. Slug determinism verified.

- [x] **T03: Build Jira REST client, auth module, and person matcher with tests** `est:2h`
  - Why: These three service modules form the Jira API interaction layer. The client wraps REST v3 with JQL search and offset pagination. Auth stores email+token credentials. Person matcher resolves Jira accountIds to Person IRIs via SPARQL. All follow established patterns from github-sync/linear-sync.
  - Files: `apps/jira-sync/services/jira_client.py`, `apps/jira-sync/services/auth.py`, `apps/jira-sync/services/person_matcher.py`, `backend/tests/test_jira_client.py`, `backend/tests/test_jira_auth.py`, `backend/tests/test_jira_person_matcher.py`
  - Do: **JiraClient** — REST v3 base URL from env or `https://{site}.atlassian.net`, Basic auth header (base64 email:token), `_request()` with error hierarchy (JiraAuthError 401, JiraRateLimitError 429, JiraAPIError 4xx/5xx), `search_issues(jql, start_at, max_results)` with offset pagination (startAt/maxResults/total), `get_issue(issue_key)`, `update_issue(issue_key, fields)`, `get_projects()`, `get_user(account_id)`. Follow GitHubClient pattern for MockResponse tests. **Auth** — `store_credentials(state, email, token, site_url)`, `get_credentials(state)` returns dict with email/token/site_url, `clear_credentials(state)`, `get_connection_status(state, client)` verifies via `get_myself()`, `build_auth_header(email, token)` returns base64 Basic auth, `_mask_token(token)`. Follow github-sync auth.py pattern. **PersonMatcher** — `resolve(account_id, display_name, email)`, SPARQL lookup by email (foaf:mbox, crm:email), fallback by account_id (bpkm:externalId), create-on-miss, LRU cache. Follow github-sync person_matcher.py pattern but adapt for Jira's accountId.
  - Verify: `cd backend && python -m pytest tests/test_jira_client.py tests/test_jira_auth.py tests/test_jira_person_matcher.py -v` — 50+ tests pass
  - Done when: Client handles JQL search with pagination, error hierarchy covers 401/429/4xx. Auth stores/retrieves/clears email+token+site_url credentials. Person matcher resolves by email then account_id with caching.

- [x] **T04: Wire app scaffold with manifest, routes, templates, and CSS** `est:1h30m`
  - Why: This task wires all service modules into an installable Jira Sync app with connect/disconnect UI and project list display. Without this, the services exist but aren't an app.
  - Files: `apps/jira-sync/manifest.yaml`, `apps/jira-sync/app.py`, `apps/jira-sync/requirements.txt`, `apps/jira-sync/frontend/templates/connect.html`, `apps/jira-sync/frontend/templates/connect_status.html`, `apps/jira-sync/frontend/static/styles.css`
  - Do: **manifest.yaml** — appId "jira-sync", permissions (object.create, object.patch, body.set, body.diff, edge.create, sparql read, backgroundTasks, network to *.atlassian.net), tasks (poll-tasks 15m, push-changes 15m), frontend static/css, UI page "settings" with icon "ticket" and nav "apps". **app.py** — routes: `/_fragments/connect` GET (render connect or status), `/_fragments/connect/credentials` POST (store email+token+site_url, verify via get_myself), `/_fragments/connect/disconnect` POST (clear credentials), `/_fragments/settings/projects` POST (save selected projects), `/_fragments/settings/sync-now` POST (placeholder for S02). All htmx URLs use `/app/jira-sync/` prefix per KNOWLEDGE.md. **connect.html** — email input, API token password input, site URL input (e.g., `mycompany.atlassian.net`), Connect button, link to Atlassian API token page. **connect_status.html** — connected badge, email display, masked token, project selection checkboxes, sync config section (direction radios, poll interval dropdown), Sync Now button, disconnect button. **styles.css** — scoped under `.jira-sync-settings`, cloned from github-sync with Jira branding adjustments. **requirements.txt** — comment that SDK is injected, no extra deps.
  - Verify: `python -c "import yaml; yaml.safe_load(open('apps/jira-sync/manifest.yaml'))"` passes. `python -c "import ast; ast.parse(open('apps/jira-sync/app.py').read())"` passes. All template files are valid Jinja2. All service imports in app.py resolve (field_mapper, auth, jira_client, person_matcher, adf_converter).
  - Done when: `apps/jira-sync/` contains all required files. Manifest has correct permissions and task declarations. All htmx URLs use `/app/jira-sync/` proxy prefix. Templates follow github-sync pattern with Jira-specific fields (email, site URL).

## Files Likely Touched

- `apps/jira-sync/services/__init__.py`
- `apps/jira-sync/services/adf_converter.py`
- `apps/jira-sync/services/field_mapper.py`
- `apps/jira-sync/services/jira_client.py`
- `apps/jira-sync/services/auth.py`
- `apps/jira-sync/services/person_matcher.py`
- `apps/jira-sync/manifest.yaml`
- `apps/jira-sync/app.py`
- `apps/jira-sync/requirements.txt`
- `apps/jira-sync/frontend/templates/connect.html`
- `apps/jira-sync/frontend/templates/connect_status.html`
- `apps/jira-sync/frontend/static/styles.css`
- `backend/tests/test_jira_adf_converter.py`
- `backend/tests/test_jira_field_mapper.py`
- `backend/tests/test_jira_client.py`
- `backend/tests/test_jira_auth.py`
- `backend/tests/test_jira_person_matcher.py`
