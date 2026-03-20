---
id: S01
parent: M023
milestone: M023
provides:
  - "adf_to_markdown(adf_doc) handling 12+ ADF block types, 5 inline types, 7 mark types"
  - "markdown_to_adf(md_text) handling paragraphs, headings, lists, code blocks, links, blockquotes, rules, inline formatting"
  - "STATUS_MAP/PRIORITY_MAP/REVERSE_STATUS_MAP/REVERSE_PRIORITY_MAP for Jira↔bpkm field normalization"
  - "build_task_properties(issue) and build_milestone_properties(epic) for pull sync field mapping"
  - "build_issue_patch(task_props) for push sync reverse mapping (title + priority only per D237)"
  - "compute_issue_slug(project_key, issue_key) for deterministic IRI minting"
  - "JiraClient REST v3 with JQL search, offset pagination, error hierarchy (JiraAPIError, JiraAuthError, JiraRateLimitError)"
  - "Auth module: store/get/clear credentials, connection status, build_auth_header (base64 email:token), token masking"
  - "PersonMatcher.resolve(account_id, display_name, email) with SPARQL lookup, Jira API fallback, create-on-miss, LRU cache"
  - "Installable Jira Sync app scaffold: manifest.yaml, 6 route handlers, connect/status templates, scoped CSS"
requires:
  - slice: none
    provides: "First slice — no upstream dependencies"
affects:
  - S02 (pull sync engine consumes all 5 service modules + app scaffold)
  - S03 (push sync consumes build_issue_patch, reverse maps, JiraClient.update_issue)
key_files:
  - apps/jira-sync/services/adf_converter.py
  - apps/jira-sync/services/field_mapper.py
  - apps/jira-sync/services/jira_client.py
  - apps/jira-sync/services/auth.py
  - apps/jira-sync/services/person_matcher.py
  - apps/jira-sync/services/__init__.py
  - apps/jira-sync/manifest.yaml
  - apps/jira-sync/app.py
  - apps/jira-sync/requirements.txt
  - apps/jira-sync/frontend/templates/connect.html
  - apps/jira-sync/frontend/templates/connect_status.html
  - apps/jira-sync/frontend/static/styles.css
  - backend/tests/test_jira_adf_converter.py
  - backend/tests/test_jira_field_mapper.py
  - backend/tests/test_jira_client.py
  - backend/tests/test_jira_auth.py
  - backend/tests/test_jira_person_matcher.py
key_decisions:
  - "D235: statusCategory.key normalization — new→todo, indeterminate→in-progress, done→done (never use status.name)"
  - "D236: API token (email + token as Basic auth) for v1, no OAuth 2.0 3LO"
  - "D237: Push sync limited to title/priority for v1 — no status transitions (requires transition IDs)"
  - "D238: Jira person resolution requires extra API call per unique accountId (GDPR — email removed from issue response)"
  - "D239: Hand-rolled ADF↔Markdown converter (~400 lines), no external library"
patterns_established:
  - "ADF block node dispatch via type string to dedicated converter functions"
  - "Markdown→ADF line-by-line state machine with regex for inline formatting (no external markdown parser)"
  - "importlib-based test loading for apps/ modules (matches github-sync pattern)"
  - "Jira Basic auth via base64(email:token) — different from GitHub PAT and Linear API key patterns"
  - "Offset pagination (startAt/maxResults/total) with MAX_PAGINATION_PAGES=50 safety limit"
  - "PersonMatcher takes jira_client as 3rd dependency for accountId→email lookup (Jira-specific)"
  - "All htmx URLs in app templates use /app/jira-sync/ proxy prefix per KNOWLEDGE.md"
observability_surfaces:
  - "get_connection_status() returns diagnostic dict (connected, email, display_name, token_preview, site_url, error)"
  - "JiraAuthError (401), JiraRateLimitError (429 with retry_after), JiraAPIError (4xx/5xx with status_code + response_body)"
  - "Structured logging in auth (credential stored/cleared), client (request method+URL), person_matcher (cache hit/miss/create)"
  - "Task stubs return {status: skipped, message: ...} for platform task runner visibility"
drill_down_paths:
  - .gsd/milestones/M023/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M023/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M023/slices/S01/tasks/T03-SUMMARY.md
  - .gsd/milestones/M023/slices/S01/tasks/T04-SUMMARY.md
duration: 1h20m
verification_result: passed
completed_at: 2026-03-19
---

# S01: ADF converter + field mapper + Jira client + auth scaffold

**All 5 Jira Sync service modules implemented and proven by 237 unit tests, plus installable app scaffold with manifest, routes, templates, and CSS — retiring the highest-risk item (ADF conversion) and establishing the full service layer for S02/S03.**

## What Happened

Built the complete Jira Sync service layer across 4 tasks, each producing a pure/service module with comprehensive tests:

**T01 — ADF↔Markdown Converter (95 tests):** Recursive `adf_to_markdown()` handles 12 block node types (paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, rule, mediaGroup, mediaSingle) and 5 inline types (text with 7 marks, mention, inlineCard, hardBreak, emoji). Reverse `markdown_to_adf()` uses a line-by-line state machine parsing paragraphs, headings, lists, code blocks, blockquotes, rules, and inline formatting (bold, italic, code, strikethrough, links). Unknown ADF types emit `[unsupported: {type}]` — never crash. This retires the milestone's primary risk (ADF conversion quality).

**T02 — Field Mapper (74 tests):** Encodes the statusCategory.key normalization strategy (D235): `new→todo`, `indeterminate→in-progress`, `done→done`. Maps 8 Jira priority names to 4 bpkm values. `build_task_properties()` extracts all fields from Jira issue JSON (title, status, priority, dueDate, assignee, labels+components as tags, sprint as taskGroup, external URL/ID/provider). `build_milestone_properties()` maps Epics. `build_issue_patch()` reverses title+priority only per D237. `compute_issue_slug()` produces deterministic `jira-{16 hex}` slugs. Round-trip consistency tests verify bidirectional mapping.

**T03 — Jira Client, Auth, Person Matcher (68 tests):** JiraClient wraps REST v3 with Basic auth (base64 email:token), JQL search via POST, offset pagination (startAt/total loop with 50-page safety), and typed error hierarchy (401→JiraAuthError, 429→JiraRateLimitError with Retry-After, 4xx/5xx→JiraAPIError). Auth module stores email+token+site_url via StateClient with masking and connection verification. PersonMatcher resolves Jira's opaque accountIds to Person IRIs via 5-step cascade: cache → SPARQL by email → Jira API for email → SPARQL by externalId → create-on-miss.

**T04 — App Scaffold (structural verification):** manifest.yaml with ticket icon, `*.atlassian.net` network permission, poll-tasks/push-changes background tasks. 6 route handlers (connect GET, credentials POST, disconnect POST, projects POST, sync-config POST, sync-now POST). Connect form with email + API token + site URL fields. Connected status with project checkboxes, JQL filter, sync direction, poll interval, stats, disconnect. All 5 htmx URLs use `/app/jira-sync/` proxy prefix. CSS scoped under `.jira-sync-settings`.

## Verification

All 237 tests pass across 5 test files in 0.21s:

| Test File | Tests | Status |
|-----------|-------|--------|
| test_jira_adf_converter.py | 95 | ✅ pass |
| test_jira_field_mapper.py | 74 | ✅ pass |
| test_jira_client.py | 34 | ✅ pass |
| test_jira_auth.py | 20 | ✅ pass |
| test_jira_person_matcher.py | 14 | ✅ pass |
| **Total** | **237** | **✅ pass** |

Additional structural checks:
- manifest.yaml: valid YAML with correct appId, permissions, tasks, UI page
- app.py: valid Python AST, all 5 service imports resolve
- Templates: all 5 htmx attributes use `/app/jira-sync/` proxy prefix (100% match)
- CSS: scoped under `.jira-sync-settings`

## Requirements Advanced

- JIRA-01 (ADF→Markdown conversion) — 95 unit tests prove all 12 ADF node types convert correctly
- JIRA-02 (Markdown→ADF reverse) — markdown_to_adf() handles paragraphs, headings, lists, code blocks, links, blockquotes, rules with inline formatting
- JIRA-03 (statusCategory normalization) — STATUS_MAP proven by 5 direct tests + 9 round-trip tests
- JIRA-04 (priority mapping) — PRIORITY_MAP covers 8 Jira names → 4 bpkm values with reverse maps
- JIRA-05 (Jira REST client) — JQL search, pagination, error hierarchy, get/update/projects/user all tested
- JIRA-06 (auth) — email+token credential management with masking and connection verification
- JIRA-07 (person matching) — 5-step resolution cascade with cache and graceful API failure handling
- JIRA-08 (app scaffold) — manifest, routes, templates, CSS — installable app structure

## Requirements Validated

- none (S01 advances requirements but full validation requires S02-S04 integration)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Test counts exceeded targets: 95 (target 60+), 74 (target 40+), 68 (target 50+) — additional coverage for round-trips, edge cases, and lossy mapping verification.
- T03 uses `asyncio.run()` wrapper pattern instead of `@pytest.mark.asyncio` — pytest-asyncio not installed in venv (pre-existing gap, not introduced by this slice).

## Known Limitations

- **Sync Now is a placeholder** — the route re-renders the status template without running actual sync. S02 wires the real pull_sync engine.
- **Task handlers return "skipped"** — poll-tasks and push-changes stubs return `{status: skipped}` until S02/S03 wire real sync engines.
- **JQL filter persists but isn't consumed** — the UI saves JQL filter text to settings, but no sync engine exists yet to use it. S02 passes it to search_all_issues().
- **No E2E verification** — all tests are unit tests with mocks. S04 provides full E2E lifecycle testing.

## Follow-ups

- S02: Wire pull sync engine consuming all 5 service modules + JQL filter + project selection
- S03: Wire push sync consuming build_issue_patch + reverse maps + JiraClient.update_issue + issue link edge creation
- S04: E2E test + mock Jira API server + user guide chapter
- Consider installing pytest-asyncio in backend venv — currently missing despite being in pyproject.toml

## Files Created/Modified

- `apps/jira-sync/services/__init__.py` — empty package init
- `apps/jira-sync/services/adf_converter.py` — ADF↔Markdown bidirectional converter (~400 lines)
- `apps/jira-sync/services/field_mapper.py` — status/priority maps, build_task_properties, slug computation (~280 lines)
- `apps/jira-sync/services/jira_client.py` — REST v3 client with JQL search, pagination, error hierarchy (~250 lines)
- `apps/jira-sync/services/auth.py` — credential management, connection status, token masking (~130 lines)
- `apps/jira-sync/services/person_matcher.py` — accountId→Person IRI resolver with SPARQL + Jira API + cache (~200 lines)
- `apps/jira-sync/manifest.yaml` — app manifest with permissions, tasks, UI page
- `apps/jira-sync/app.py` — 6 route handlers + 2 task stubs + lifecycle hooks (~210 lines)
- `apps/jira-sync/requirements.txt` — SDK-only (no extra deps)
- `apps/jira-sync/frontend/templates/connect.html` — auth form (email + token + site URL)
- `apps/jira-sync/frontend/templates/connect_status.html` — connected state with project list, JQL, sync config, stats
- `apps/jira-sync/frontend/static/styles.css` — scoped CSS under .jira-sync-settings (~310 lines)
- `backend/tests/test_jira_adf_converter.py` — 95 unit tests
- `backend/tests/test_jira_field_mapper.py` — 74 unit tests
- `backend/tests/test_jira_client.py` — 34 unit tests
- `backend/tests/test_jira_auth.py` — 20 unit tests
- `backend/tests/test_jira_person_matcher.py` — 14 unit tests

## Forward Intelligence

### What the next slice should know
- All 5 service modules are pure/service modules with no cross-dependencies except PersonMatcher taking jira_client as a constructor arg. S02's sync engine orchestrates them all.
- `build_task_properties()` supports both nested `{fields: {...}}` and flat dict shapes from Jira API responses. S02 should pass the raw issue dict directly.
- `search_all_issues(jql)` handles pagination internally — S02 just passes the JQL string and gets back all issues.
- The connect_status.html template already has project selection checkboxes, JQL filter, sync direction, poll interval, and Sync Now button — S02 wires these to real sync logic.
- `compute_issue_slug("PROJ", "PROJ-123")` is deterministic — same inputs always produce the same slug. S02 can use this for idempotent upsert.

### What's fragile
- `markdown_to_adf()` uses regex-based inline formatting parsing (not a proper AST) — complex nested formatting like `**bold _italic_ bold**` may not round-trip perfectly. For S02/S03 push sync, this is acceptable since SemPKM produces simple Markdown.
- The `asyncio.run()` test wrapper pattern works but is non-standard — if pytest-asyncio gets installed later, these tests should migrate to `@pytest.mark.asyncio`.

### Authoritative diagnostics
- `get_connection_status(state, client)` — returns full state dict including `error` field. First thing to check when debugging auth issues.
- JiraClient error hierarchy — `JiraAuthError` (bad credentials), `JiraRateLimitError` (429 with `retry_after` seconds), `JiraAPIError` (any other failure with `status_code` + `response_body`).
- PersonMatcher `_cache` dict — inspect for resolved accountId→IRI mappings during sync debugging.

### What assumptions changed
- Test count assumption (150+ total) — actual is 237, significantly exceeding targets across all modules.
- ADF converter complexity — estimated ~300 lines, actual ~400 lines due to comprehensive mark handling and table support. The extra complexity is well-tested.
