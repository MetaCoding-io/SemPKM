---
estimated_steps: 6
estimated_files: 2
---

# T01: Mock Monday.com GraphQL server + Docker integration

**Slice:** S04 — E2E tests + user guide
**Milestone:** M024

## Description

Create a mock Monday.com GraphQL API server for E2E testing and wire it into the Docker test stack. The mock must handle all query shapes from `monday_client.py` via substring matching against incoming query text (following the Linear mock pattern), return properly structured `{"data": {...}}` wrapped responses, and include a comprehensive selftest mode. Docker compose gets the `mock-monday` service entry and `MONDAY_API_URL` environment variable.

Monday.com uses a single POST endpoint at `/` (not `/graphql` like Linear) — the client posts to whatever `MONDAY_API_URL` resolves to. The mock must accept POST at `/` (the root path). The auth header is bare `Authorization: <api_key>` (no Bearer prefix).

## Steps

1. **Create `e2e/mock-monday-api/server.py`** with the following structure:
   - Import standard library modules (json, sys, io, http.server, urllib.parse)
   - Define PORT = 8080
   - Create canned response data for all 10 query types the MondayClient uses:

   **Canned responses needed (all wrapped in `{"data": {...}}`)**:
   
   a. **`me`** query → `{ me { id name email } }` — returns user profile:
   ```python
   ME_RESPONSE = {"data": {"me": {"id": "12345", "name": "Test User", "email": "test@example.com"}}}
   ```

   b. **`boards(limit`** query → board list:
   ```python
   BOARDS_RESPONSE = {"data": {"boards": [
       {"id": "1001", "name": "Test Board", "state": "active"},
       {"id": "1002", "name": "Design Board", "state": "active"},
   ]}}
   ```

   c. **`boards(ids:` with `columns`** → board columns including `settings_str`:
   ```python
   BOARD_COLUMNS_RESPONSE = {"data": {"boards": [{"columns": [
       {"id": "status", "title": "Status", "type": "status",
        "settings_str": "{\"labels\":{\"1\":\"Working on it\",\"2\":\"Done\",\"3\":\"Stuck\",\"4\":\"Waiting for review\"}}"},
       {"id": "priority", "title": "Priority", "type": "status",
        "settings_str": "{\"labels\":{\"1\":\"Critical\",\"2\":\"High\",\"3\":\"Medium\",\"4\":\"Low\"}}"},
       {"id": "date0", "title": "Due Date", "type": "date", "settings_str": "{}"},
       {"id": "person", "title": "Assignee", "type": "people", "settings_str": "{}"},
       {"id": "text0", "title": "Notes", "type": "text", "settings_str": "{}"},
       {"id": "long_text", "title": "Description", "type": "long_text", "settings_str": "{}"},
       {"id": "numbers0", "title": "Story Points", "type": "numbers", "settings_str": "{}"},
       {"id": "tags0", "title": "Tags", "type": "tag", "settings_str": "{}"},
       {"id": "dropdown0", "title": "Category", "type": "dropdown", "settings_str": "{}"},
       {"id": "dependency0", "title": "Dependencies", "type": "dependency", "settings_str": "{}"},
   ]}]}}
   ```
   **CRITICAL**: `settings_str` values must be JSON **strings** (the value is a string containing JSON), not dicts. This is how Monday.com actually returns them. The mock already has them as Python strings which will be serialized as JSON strings.

   d. **`boards(ids:` with `items_page`** → board items with column_values and group:
   Create 3 items with realistic column_values covering status, priority, date, people, tags, and dependency types. Each item needs `id`, `name`, `group { id title }`, `column_values [{ id text type value }]`. Return `cursor: null` for single-page response.
   
   Items should be:
   - Item 10001 "Fix login page crash" — status "Working on it", priority "High", date "2026-04-15", person user 12345, tags [101], dependency on item 10003. Group: "Sprint 5"
   - Item 10002 "Add dark mode support" — status "Done", priority "Medium", no assignee, no tags. Group: "Sprint 5"  
   - Item 10003 "Platform migration" — status "Stuck", priority "Critical", person user 12345. Group: "Backlog"

   Column values format:
   - Status: `{"text": "Working on it", "type": "status", "value": "{\"index\":1,\"label\":\"Working on it\"}"}`
   - People: `{"text": "Test User", "type": "people", "value": "{\"personsAndTeams\":[{\"id\":12345,\"kind\":\"person\"}]}"}`
   - Date: `{"text": "2026-04-15", "type": "date", "value": "{\"date\":\"2026-04-15\"}"}`
   - Tags: `{"text": "", "type": "tag", "value": "{\"tag_ids\":[101]}"}`
   - Dependency: `{"text": "", "type": "dependency", "value": "{\"linkedPulseIds\":[{\"linkedPulseId\":10003}]}"}`
   - Numbers: `{"text": "5", "type": "numbers", "value": "\"5\""}`

   e. **`items(ids:` with `subitems`** → subitems for parent items:
   ```python
   SUBITEMS_RESPONSE = {"data": {"items": [
       {"id": "10001", "subitems": [
           {"id": "20001", "name": "Subtask: research login libs",
            "group": {"id": "subitems_group", "title": "Subitems"},
            "column_values": [...]},
       ]},
   ]}}
   ```

   f. **`users(ids:`** → user details:
   ```python
   USERS_RESPONSE = {"data": {"users": [
       {"id": "12345", "name": "Test User", "email": "test@example.com"}
   ]}}
   ```

   g. **`tags(ids:`** → tag names:
   ```python
   TAGS_RESPONSE = {"data": {"tags": [
       {"id": "101", "name": "frontend"}
   ]}}
   ```

   h. **`change_multiple_column_values`** mutation → success:
   ```python
   MUTATION_RESPONSE = {"data": {"change_multiple_column_values": {"id": "10001", "name": "Fix login page crash"}}}
   ```

   i. **`create_item`** mutation → success:
   ```python
   CREATE_ITEM_RESPONSE = {"data": {"create_item": {"id": "10099", "name": "New item"}}}
   ```

   j. **`groups`** query → board groups:
   ```python
   GROUPS_RESPONSE = {"data": {"boards": [{"groups": [
       {"id": "sprint_5", "title": "Sprint 5"},
       {"id": "backlog", "title": "Backlog"},
   ]}]}}
   ```

2. **Build the `QUERY_MATCHERS` dispatch list** — order matters, more specific substrings first:
   ```python
   QUERY_MATCHERS = [
       ("change_multiple_column_values", "mutation: change_column_values", MUTATION_RESPONSE),
       ("create_item", "mutation: create_item", CREATE_ITEM_RESPONSE),
       ("subitems", "subitems", SUBITEMS_RESPONSE),
       ("items_page", "items_page", ITEMS_RESPONSE),
       ("columns", "columns", BOARD_COLUMNS_RESPONSE),
       ("groups", "groups", GROUPS_RESPONSE),
       ("users", "users", USERS_RESPONSE),
       ("tags", "tags", TAGS_RESPONSE),
       ("boards(limit", "boards (list)", BOARDS_RESPONSE),
       ("boards(ids", "boards (by id)", BOARD_COLUMNS_RESPONSE),  # fallback for boards(ids: queries
       ("me", "me", ME_RESPONSE),
   ]
   ```
   **Dispatch logic**: Iterate matchers in order. For each, check if the substring appears in the query string. First match wins. The `boards(ids:` queries are tricky — if the query contains `columns`, match columns; if it contains `items_page`, match items; if it contains `groups`, match groups. The ordering above handles this because more specific checks come first.

3. **Create the `MockMondayHandler`** class:
   - `do_GET`: Handle `/health` → `{"status": "ok"}`, else 404
   - `do_POST`: Handle `/` (root path — Monday.com's single endpoint):
     - Read Content-Length and parse JSON body
     - Extract `query` from body
     - Iterate `QUERY_MATCHERS`, return first match
     - Fallback: `{"data": {}}` for unrecognized queries
   - `_json_response` helper: set status, Content-Type, Content-Length, write JSON payload
   - `log_message` override with `[mock-monday]` prefix

4. **Implement selftest mode** — clone Jira's `_FakeRequestFile`/`_FakeWFile`/`_make_fake_handler` infrastructure. The `SilentHandler` overrides `_json_response` to capture status + body. Then add checks:
   - `GET /health` → status ok
   - `POST / (me query)` → has me.id, me.name, me.email
   - `POST / (boards list)` → has boards array with 2 items
   - `POST / (columns query)` → has columns array with 10 items, first has settings_str that parses as JSON containing "labels"
   - `POST / (items_page query)` → has items array with 3 items, first has column_values and group
   - `POST / (subitems query)` → has items array with subitems
   - `POST / (users query)` → has users array
   - `POST / (tags query)` → has tags array
   - `POST / (groups query)` → has groups array
   - `POST / (change_multiple_column_values mutation)` → has success response
   - `POST / (create_item mutation)` → has success response
   - `POST / (unknown query)` → returns empty data dict
   
   Print pass/fail summary and exit with code 0/1.

5. **Add entrypoint** — `if __name__ == "__main__"`: check `--selftest`, else start server on port 8080.

6. **Update `docker-compose.test.yml`**:
   - Add `MONDAY_API_URL: http://mock-monday:8080` to the `api` service environment section (after `JIRA_API_URL`)
   - Add `mock-monday` to `api` service `depends_on` with `condition: service_healthy`
   - Add `mock-monday` service block (same pattern as mock-jira):
     ```yaml
     mock-monday:
       image: python:3.12-slim
       volumes:
         - ./e2e/mock-monday-api:/app:ro
       working_dir: /app
       command: ["python", "server.py"]
       healthcheck:
         test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
         interval: 3s
         timeout: 3s
         retries: 5
       networks:
         - sempkm-test
     ```

## Must-Haves

- [ ] Mock server handles all 10 query shapes from `monday_client.py` via substring dispatch
- [ ] All responses wrapped in `{"data": {...}}` (Monday.com GraphQL convention)
- [ ] `settings_str` is a JSON string value (not a dict) — Monday.com returns it as a string that needs `json.loads()`
- [ ] Items include realistic column_values with status, priority, date, people, tags, dependency columns
- [ ] Items include `group { id title }` metadata
- [ ] At least one subitem with `parent_item_id` augmentation in subitems response
- [ ] `change_multiple_column_values` and `create_item` mutations return success responses
- [ ] Selftest passes 12+ checks verifying all canned responses
- [ ] `mock-monday` Docker service added with healthcheck
- [ ] `MONDAY_API_URL: http://mock-monday:8080` in api environment
- [ ] `mock-monday` in api depends_on

## Verification

- `python e2e/mock-monday-api/server.py --selftest` — all checks pass (12+ passed, 0 failed)
- `docker compose -f docker-compose.test.yml config --quiet` — exits 0 (valid YAML, no errors)
- `python -c "import ast; ast.parse(open('e2e/mock-monday-api/server.py').read())"` — syntax valid

## Inputs

- `e2e/mock-linear-api/server.py` — GraphQL substring-matching dispatch pattern to clone
- `e2e/mock-jira-api/server.py` — Selftest infrastructure (`_FakeRequestFile`, `_FakeWFile`, `_make_fake_handler`) to clone
- `apps/monday-sync/services/monday_client.py` — Query shapes the mock must respond to (lines 240-484 define all queries)
- `docker-compose.test.yml` — Existing test stack structure to extend
- S01 Summary: Auth header is bare `Authorization: <api_key>` (no Bearer prefix)
- S01 Summary: Monday.com user_id (numeric) stored as string
- Research: Monday.com uses single POST endpoint at `/` (not `/graphql`)
- Research: `settings_str` must be a JSON string (double-encoded in canned response)

## Observability Impact

- **New diagnostic command**: `python e2e/mock-monday-api/server.py --selftest` — in-process verification of all canned responses, prints pass/fail summary, exits 0/1
- **New health endpoint**: `GET /health` on `mock-monday:8080` — Docker healthcheck target, returns `{"status": "ok"}`
- **Request dispatch logging**: All POST requests log matched query label (e.g. `[mock-monday] Matched query type: items_page`) or first 120 chars of unrecognized queries to stderr — visible via `docker compose logs mock-monday`
- **Failure visibility**: Unrecognized queries return `{"data": {}}` (not an error) — matches Monday.com GraphQL convention where unknown fields return null data. Log output identifies the unmatched query for debugging.
- **Docker integration**: `docker compose -f docker-compose.test.yml ps mock-monday` shows service health. `MONDAY_API_URL` env var visible in `docker compose config`.

## Expected Output

- `e2e/mock-monday-api/server.py` — ~400 lines, mock GraphQL server with canned responses and selftest
- `docker-compose.test.yml` — Updated with mock-monday service, MONDAY_API_URL env var, and depends_on
