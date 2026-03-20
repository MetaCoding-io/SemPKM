# M019 — Todoist Sync App — Research

**Date:** 2026-03-19
**Status:** Complete

## Summary

Todoist Sync is the fourth sync app on the App Platform (after Linear M016, GitHub M017, Google Calendar M018). Todoist's REST API v2 is straightforward — simple bearer auth, JSON responses, no pagination complexity (cursor or Link headers). The data model maps cleanly: Todoist tasks → `bpkm:Task`, projects → `bpkm:taskProject`, labels → `bpkm:tags`, priority (1–4) → `bpkm:priority`. Two auth paths are viable: OAuth 2.0 (matches Google Calendar M018 pattern) and personal API token (matches GitHub M017 PAT pattern). Both should be supported.

The codebase has three prior sync apps with identical architecture: `services/` directory with `auth.py`, `field_mapper.py`, `{provider}_client.py`, `person_matcher.py`, `sync_engine.py`, plus `app.py` routes and `frontend/templates/`. This is a copy-and-adapt job — the GitHub sync is the closest template (REST API, PAT auth). The main implementation risk is near zero given established patterns.

**Note:** Todoist's REST API v2 is marked as deprecated in favor of their new "Todoist API v1" (confusingly named — it's a unified API replacing both REST v2 and Sync v9). The new v1 API has the same REST endpoints but lives under `api.todoist.com/api/v1/`. For this milestone, we should use the REST v2 endpoints since they're well-documented and still functional, but be aware the eventual migration path is to v1.

## Recommendation

Clone the GitHub sync app structure (simplest REST-based sync) with these adaptations:

1. **Auth:** Support both personal API token (from Todoist integration settings) and OAuth 2.0 (client_id/secret from Todoist App Management Console). API token path first (simpler to test), OAuth as secondary auth method. Follow D206/D210 patterns.
2. **Client:** Simple REST client wrapping SDK HttpClient — `GET /rest/v2/tasks`, `GET /rest/v2/projects`, `GET /rest/v2/labels`, `POST /rest/v2/tasks/{id}/close`, `POST /rest/v2/tasks/{id}/reopen`, `POST /rest/v2/tasks`. No pagination complexity — Todoist returns all items in a single response for personal accounts.
3. **Field mapping:** Direct 1:1 mapping for most fields. Priority 1–4 inverted (Todoist 1=normal, 4=urgent → bpkm low/medium/high/critical). Due dates come as `{date, datetime, timezone, is_recurring, string}` — extract `date` field.
4. **Sync:** Polling-only (same as all prior sync apps). No sync_token or delta mechanism in REST v2 — fetch all active tasks, compare with existing by external ID. Completed tasks need separate endpoint or filter.
5. **Push:** Close/reopen tasks, update content/description/priority/labels/due. Todoist REST API has specific `POST /tasks/{id}/close` and `POST /tasks/{id}/reopen` rather than PATCH for completion state.

## Implementation Landscape

### Key Files (to clone from GitHub sync)

- `apps/github-sync/manifest.yaml` → `apps/todoist-sync/manifest.yaml` (change appId, name, icon, network domains)
- `apps/github-sync/app.py` → `apps/todoist-sync/app.py` (same route structure, different service imports)
- `apps/github-sync/services/auth.py` → adapt for Todoist PAT + OAuth
- `apps/github-sync/services/github_client.py` → `todoist_client.py` (REST v2 endpoints, simpler — no pagination)
- `apps/github-sync/services/field_mapper.py` → `field_mapper.py` (Todoist field → bpkm:Task mapping)
- `apps/github-sync/services/sync_engine.py` → `sync_engine.py` (same two-phase bulk pattern)
- `apps/github-sync/services/person_matcher.py` → copy as-is (same SPARQL email lookup)
- `apps/github-sync/frontend/templates/connect.html` → adapt for PAT input
- `apps/github-sync/frontend/templates/connect_status.html` → adapt for project selection

### Todoist REST API v2 Endpoints Needed

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /rest/v2/tasks` | GET | Fetch all active tasks (optional `?project_id=` filter) |
| `GET /rest/v2/projects` | GET | Fetch all projects (for selection UI) |
| `GET /rest/v2/labels` | GET | Fetch all labels (for tag mapping) |
| `POST /rest/v2/tasks` | POST | Create a new task |
| `POST /rest/v2/tasks/{id}` | POST | Update task fields |
| `POST /rest/v2/tasks/{id}/close` | POST | Mark task complete |
| `POST /rest/v2/tasks/{id}/reopen` | POST | Reopen completed task |
| `DELETE /rest/v2/tasks/{id}` | DELETE | Delete task (probably not needed) |

**Base URL:** `https://api.todoist.com`  
**Auth header:** `Authorization: Bearer {token}`  
**Rate limit:** 1000 requests per user per 15 minutes.

### Todoist Task JSON Shape (from REST v2)

```json
{
  "id": "2995104339",
  "project_id": "2203306141",
  "section_id": "7025",
  "content": "Buy Milk",
  "description": "Low-fat milk from the store",
  "is_completed": false,
  "labels": ["grocery", "errands"],
  "priority": 1,
  "due": {
    "date": "2024-01-15",
    "is_recurring": false,
    "datetime": "2024-01-15T12:00:00",
    "string": "Jan 15",
    "timezone": "America/New_York"
  },
  "parent_id": null,
  "creator_id": "123",
  "assignee_id": "456",
  "url": "https://todoist.com/showTask?id=2995104339"
}
```

### Field Mapping: Todoist → bpkm:Task

| Todoist Field | bpkm Property | Transform | Direction |
|---------------|---------------|-----------|-----------|
| `content` | `dcterms:title` | Direct | ↔ |
| `description` | body (markdown) | Direct | ↔ |
| `is_completed` | `bpkm:taskStatus` | false→"todo", true→"done" | ↔ (via close/reopen) |
| `priority` | `bpkm:priority` | 1→"low", 2→"medium", 3→"high", 4→"critical" | ↔ |
| `due.date` | `bpkm:dueDate` | Direct (xsd:date) | ↔ |
| `labels` | `bpkm:tags` | Direct (string array) | ↔ |
| `project_id` | `bpkm:taskProject` | Resolve project name via lookup | ← |
| `url` | `bpkm:externalUrl` | Direct | ← |
| `id` | `bpkm:externalId` | Direct | ← |
| `assignee_id` | `bpkm:assignedTo` | User ID → Person IRI (limited — Todoist personal API has no user lookup) | ← |
| `parent_id` | `bpkm:parentTask` | ID → Task IRI (out of scope per CONTEXT — one level max) | ← |
| `is_completed` + close/reopen | completion state | close/reopen endpoints for push | → |

**Priority mapping (inverted from Todoist convention):**

| Todoist Priority | Todoist Meaning | bpkm:priority |
|-----------------|-----------------|---------------|
| 1 | Normal (default) | low |
| 2 | Medium | medium |
| 3 | High | high |
| 4 | Urgent (red !!!) | critical |

### Build Order

1. **S01: Auth + Client + Basic Pull** — Prove the API connection works. PAT auth, TodoistClient, field mapper, pull sync creating bpkm:Task objects. This retires the primary integration risk.
2. **S02: Push Sync + Settings UI** — Bidirectional: detect local changes, push via close/reopen/update. Settings page with project selection, sync direction, poll interval.
3. **S03: E2E Tests + User Guide** — Mock Todoist API server, Playwright E2E test, Chapter 37 user guide.

### Verification Approach

- **Unit tests:** `backend/tests/test_todoist_*.py` using importlib pattern from M016/M017/M018. Mock SDK clients. ~150+ tests covering auth, client, field_mapper, sync_engine.
- **Mock API server:** `e2e/mock-todoist-api/server.py` — canned task/project/label responses. Self-test. Docker service in docker-compose.test.yml.
- **E2E test:** `e2e/tests/37-todoist-sync/todoist-sync.spec.ts` — install → connect → select projects → sync → verify tasks via SPARQL → push completion → cleanup.
- **User guide:** `docs/guide/37-todoist-sync.md` — Chapter 37 with field mapping tables, OAuth setup, troubleshooting.

## Constraints

- **Todoist REST v2 has no delta sync.** No `since` parameter like GitHub, no `syncToken` like Google Calendar. Must fetch all active tasks and compare. For personal accounts this is fine (typically <500 tasks). The Sync API v9 has incremental sync via `sync_token` but it's a completely different API surface — not worth the complexity for v1.
- **Assignee resolution is limited.** Todoist's `assignee_id` is a user ID but the REST API v2 has no `GET /users/{id}` endpoint for personal accounts (collaborators endpoint is project-scoped). Person matching will work for shared projects where collaborator data is available; for personal tasks the field is typically empty.
- **Close/reopen vs PATCH for completion.** Unlike GitHub (PATCH state field) or Linear (mutation), Todoist requires separate `POST /tasks/{id}/close` and `POST /tasks/{id}/reopen` endpoints for completion state changes. The push sync must branch on status change direction.
- **App proxy query-param forwarding** was fixed in M018 (for OAuth callbacks). This fix is in the codebase and available for Todoist OAuth.
- **htmx template URLs must use `/app/todoist-sync/` prefix** per knowledge base entry (App template htmx URLs must use proxy prefix).

## Common Pitfalls

- **Priority inversion** — Todoist's numbering is counterintuitive: 1 is normal/lowest, 4 is urgent/highest. Easy to map backwards. Unit test with explicit assertions for all 4 levels.
- **Due date format** — Todoist's `due` is an object with `date`, `datetime`, `timezone`, `string`, and `is_recurring` fields. Extract `due.date` (YYYY-MM-DD) for bpkm:dueDate. When `datetime` is present, it includes time — but bpkm:dueDate is xsd:date only. Don't lose the datetime for future use.
- **Completed tasks** — `GET /rest/v2/tasks` returns only active (incomplete) tasks by default. To sync completed tasks, need `GET /rest/v2/tasks?filter=@complete` or the separate completed tasks endpoint. For v1, pulling only active tasks is sufficient — completed tasks on the SemPKM side that aren't in the active list can be marked done.
- **X-Request-Id for idempotency** — Todoist supports `X-Request-Id` header for POST/PUT requests. Should include this for create/update operations to prevent duplicate tasks on retry.
- **Pre-existing app subprocess startup issue** — M017 and M018 E2E tests have been blocked by a pre-existing subprocess 500 error on app startup. The E2E test should be structurally complete but may hit the same issue. Document it.

## Open Risks

- **REST API v2 deprecation timeline** — Todoist marks REST v2 as deprecated in favor of their new "v1" unified API. Migration should be straightforward (same concepts, different URL prefix) but if v2 is removed during development, we'd need to adjust endpoints. Low risk for a self-hosted app.
- **Pre-existing app subprocess startup bug** — Same as M017/M018: E2E tests may fail at app startup phase. Not a Todoist-specific defect.

## Candidate Requirements

Per D209, Todoist sync requirements should use `TD-` prefix.

| ID | Requirement | Class | Notes |
|----|-------------|-------|-------|
| TD-01 | Todoist API token authentication | core-capability | PAT from integration settings |
| TD-02 | Pull sync: Todoist tasks → bpkm:Task | core-capability | All active tasks from selected projects |
| TD-03 | Push sync: SemPKM changes → Todoist | core-capability | Close/reopen + field updates |
| TD-04 | Project selection in settings UI | core-capability | Checkboxes for which projects to sync |
| TD-05 | Priority mapping (1-4 → low/medium/high/critical) | core-capability | Inverted from Todoist convention |
| TD-06 | Label → tag mapping | core-capability | Direct array mapping |
| TD-07 | Settings UI: sync direction, poll interval, Sync Now | core-capability | Same pattern as M016/M017 |
| TD-08 | E2E tests + user guide | quality-attribute | Mock API server, Playwright E2E, Chapter 37 |

**Not proposed (out of scope per CONTEXT):**
- Todoist comments, sections, filters
- Todoist Karma/productivity stats
- Sub-task nesting beyond one level
- OAuth 2.0 (could be added but PAT is simpler and matches individual user focus)

## Sources

- Todoist REST API v2 reference (source: [developer.todoist.com/rest/v2](https://developer.todoist.com/rest/v2/))
- Todoist OAuth guide (source: [developer.todoist.com/guides](https://developer.todoist.com/guides/))
- Todoist unified API v1 (source: [developer.todoist.com/api/v1](https://developer.todoist.com/api/v1/))
- Existing codebase: `apps/github-sync/` (primary template), `apps/google-calendar/` (OAuth reference), `apps/linear-sync/` (first sync app)
- Integration domain mapping: `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` (Todoist field mapping table)
