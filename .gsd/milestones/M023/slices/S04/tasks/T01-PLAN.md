---
estimated_steps: 6
estimated_files: 1
---

# T01: Build mock Jira REST API server with selftest

**Slice:** S04 — E2E Tests + User Guide
**Milestone:** M023

## Description

Build a mock Jira REST API server that returns canned responses for all endpoints the `JiraClient` calls. This server runs inside Docker during E2E tests, allowing the Jira sync app to execute its full sync lifecycle against known data. The `--selftest` mode validates all endpoints without needing Docker.

Clone the pattern from `e2e/mock-github-api/server.py` — it's a single-file stdlib HTTP server (~426 lines) with canned data, URL routing, and a selftest harness that simulates requests via fake handler objects.

**Relevant skills:** None needed — standard Python stdlib HTTP server.

## Steps

1. **Create `e2e/mock-jira-api/server.py`** with the same structure as `e2e/mock-github-api/server.py`:
   - Imports: `http.server`, `json`, `sys`, `io`, `urllib.parse`
   - `PORT = 8080`
   - Canned response data constants (see step 2)
   - `MockJiraHandler(BaseHTTPRequestHandler)` with `do_GET`, `do_POST`, `do_PUT`
   - `_json_response()` helper
   - `_log_request()` helper with `[mock-jira]` prefix
   - `selftest()` function
   - `_FakeRequestFile`, `_FakeWFile`, `_make_fake_handler()` — copy the selftest harness pattern exactly from mock-github-api
   - `__main__` entrypoint with `--selftest` flag check

2. **Define canned response data:**
   - `MYSELF_RESPONSE`: `{"accountId": "user-abc-123", "displayName": "Test User", "emailAddress": "test@example.com", "active": true}`
   - `PROJECTS_RESPONSE`: list of 2 projects:
     - `{"id": "10000", "key": "PROJ", "name": "Test Project", "projectTypeKey": "software"}`
     - `{"id": "10001", "key": "DESIGN", "name": "Design Team", "projectTypeKey": "software"}`
   - `USER_RESPONSE`: `{"accountId": "user-abc-123", "displayName": "Test User", "emailAddress": "test@example.com", "active": true}` (same as MYSELF for this mock)
   - `SEARCH_RESPONSE`: `{"startAt": 0, "maxResults": 50, "total": 3, "issues": [ISSUE_1, ISSUE_2, ISSUE_3]}` where each issue uses the nested `fields` format:
     - **ISSUE_1 (PROJ-1)**: In-progress, assigned, has issue link
       ```python
       {
           "id": "10001", "key": "PROJ-1", "self": "...",
           "fields": {
               "summary": "Fix login page crash on mobile",
               "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "The login page throws an error on iOS Safari."}]}]},
               "status": {"name": "In Progress", "statusCategory": {"key": "indeterminate"}},
               "issuetype": {"name": "Bug"},
               "priority": {"name": "High"},
               "assignee": {"accountId": "user-abc-123", "displayName": "Test User"},
               "labels": ["bug", "mobile"],
               "components": [{"name": "Frontend"}],
               "created": "2026-03-01T10:00:00.000+0000",
               "updated": "2026-03-15T14:30:00.000+0000",
               "sprint": {"name": "Sprint 5", "state": "active"},
               "issuelinks": [
                   {
                       "type": {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"},
                       "inwardIssue": {"key": "PROJ-3", "id": "10003", "fields": {"summary": "Platform migration epic", "issuetype": {"name": "Epic"}}}
                   }
               ]
           }
       }
       ```
     - **ISSUE_2 (PROJ-2)**: Todo, unassigned
       ```python
       {
           "id": "10002", "key": "PROJ-2", "self": "...",
           "fields": {
               "summary": "Add dark mode support",
               "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Users want dark mode."}]}]},
               "status": {"name": "To Do", "statusCategory": {"key": "new"}},
               "issuetype": {"name": "Story"},
               "priority": {"name": "Medium"},
               "assignee": None,
               "labels": [],
               "components": [],
               "created": "2026-03-02T09:00:00.000+0000",
               "updated": "2026-03-14T11:00:00.000+0000",
               "sprint": None,
               "issuelinks": []
           }
       }
       ```
     - **ISSUE_3 (PROJ-3)**: Done Epic — used for Epic→Milestone mapping
       ```python
       {
           "id": "10003", "key": "PROJ-3", "self": "...",
           "fields": {
               "summary": "Platform migration epic",
               "description": None,
               "status": {"name": "Done", "statusCategory": {"key": "done"}},
               "issuetype": {"name": "Epic"},
               "priority": {"name": "Highest"},
               "assignee": {"accountId": "user-abc-123", "displayName": "Test User"},
               "labels": ["epic", "migration"],
               "components": [{"name": "Backend"}],
               "created": "2026-03-01T08:00:00.000+0000",
               "updated": "2026-03-18T10:00:00.000+0000",
               "sprint": None,
               "issuelinks": []
           }
       }
       ```

3. **Implement `do_GET` routing:**
   - `/health` → `{"status": "ok"}`
   - `/rest/api/3/myself` → `MYSELF_RESPONSE`
   - `/rest/api/3/project` → `PROJECTS_RESPONSE`
   - `/rest/api/3/user` → Parse `accountId` from query string (`parse_qs`). If matches "user-abc-123", return `USER_RESPONSE`. Else 404.
   - `/rest/api/3/issue/{key}` → Look up by key in `_ISSUES_BY_KEY` dict. Return full issue object. 404 if not found.
   - Default → 404

4. **Implement `do_POST` routing:**
   - `/rest/api/3/search` → Read JSON body, extract `jql`, `startAt`, `maxResults`. Return `SEARCH_RESPONSE` (ignoring JQL filtering — mock always returns all 3 issues). Must handle `Content-Length` header and `json.loads()`.
   - Default → 404

5. **Implement `do_PUT` routing:**
   - `/rest/api/3/issue/{key}` → Read JSON body with `{"fields": {...}}`. Look up base issue by key. Merge patch fields into a copy. Return merged result with updated timestamp. 404 if key not found.
   - Default → 404

6. **Implement selftest:**
   - `GET /health` → status "ok"
   - `GET /rest/api/3/myself` → accountId "user-abc-123"
   - `GET /rest/api/3/project` → list of 2 projects
   - `POST /rest/api/3/search` → 3 issues with correct keys
   - `GET /rest/api/3/user?accountId=user-abc-123` → displayName "Test User"
   - `GET /rest/api/3/issue/PROJ-1` → key "PROJ-1" with issuelinks
   - `PUT /rest/api/3/issue/PROJ-1` with `{"fields": {"summary": "Updated"}}` → merged summary
   - `GET /unknown → 404`
   - Print pass/fail summary, exit 0 on all pass

## Must-Haves

- [ ] Server responds to all 7 endpoint patterns (health, myself, projects, search, user, issue get, issue update)
- [ ] Search uses POST method (not GET) with JSON body parsing
- [ ] Issue update uses PUT method (not PATCH) with fields merge
- [ ] Issue data uses nested `fields` structure matching Jira REST API v3 format
- [ ] PROJ-1 has `issuelinks` with a Blocks type and `inwardIssue` key pointing to PROJ-3
- [ ] PROJ-3 has `issuetype.name = "Epic"` (capitalized — sync engine lowercases)
- [ ] User endpoint parses `accountId` from query string (not URL path)
- [ ] `--selftest` mode exits 0 with all checks passing

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M023 && python e2e/mock-jira-api/server.py --selftest` exits 0
- All selftest checks show `✓`

## Inputs

- `e2e/mock-github-api/server.py` — reference implementation to clone structure from (canned data, handler class, selftest harness with _FakeRequestFile/_FakeWFile/_make_fake_handler)
- `apps/jira-sync/services/jira_client.py` — defines the endpoints the mock must serve: `GET /rest/api/3/myself`, `GET /rest/api/3/project`, `POST /rest/api/3/search`, `GET /rest/api/3/user?accountId=X`, `PUT /rest/api/3/issue/{key}`
- `apps/jira-sync/services/field_mapper.py` — defines the field structure the mock data must match (statusCategory.key, priority.name, issuetype.name, labels array, components array, sprint object, issuelinks)
- `apps/jira-sync/services/sync_engine.py` — processes `issuelinks` in Phase 4, checks `issuetype.name.lower() == "epic"` for Milestone mapping

## Observability Impact

- **New runtime signal:** `[mock-jira]` log prefix on stderr for every request — enables filtering Docker logs.
- **Inspection surface:** `GET /health` returns `{"status": "ok"}` for liveness checks. `--selftest` mode validates all 7 endpoints offline.
- **Failure visibility:** 404 with structured JSON `{"message": "Not Found"}` for unrecognized paths. 400 with `{"message": "Invalid JSON"}` for malformed POST/PUT bodies. All routes log method+path+status to stderr.
- **No redaction needed:** Mock ignores auth headers entirely. All data is synthetic.

## Expected Output

- `e2e/mock-jira-api/server.py` — complete mock server (~400-500 lines) with canned data, HTTP handler, and selftest mode
