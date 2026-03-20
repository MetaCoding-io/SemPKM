# M022: Asana Sync App — Research

**Date:** 2026-03-19

## Summary

Asana Sync is the seventh bidirectional sync app on the App Platform, mapping Asana tasks to `bpkm:Task` objects. The established 6-service architecture (auth, client, field_mapper, person_matcher, sync_engine, app.py) translates directly. The primary novelty is **configurable field mapping** — Asana has no native status or priority fields, so the user must designate custom fields or section names during setup. This "configure before sync" pattern is new to the platform and drives most of the complexity.

The INTEGRATION-DOMAIN-MAPPING.md design doc covers Asana comprehensively: entity mapping (task, subtask up to 5 levels, milestone via `resource_subtype`, project, section, tags, custom fields), field mapping (~20 fields), status normalization (3 modes: completed-only, custom enum field, section-based), priority mapping (custom enum field), and custom field strategy (6 types). The Asana REST API uses cost-based rate limiting (~1500 req/min), pagination with `opt_fields` for efficiency, and project-scoped webhooks with GID-only payloads.

The key risk is the **configurable mapping UI** — the settings flow must discover the user's custom fields, present them for mapping, and persist the configuration before sync can run. This is a new UX pattern not present in Linear/GitHub/Todoist/Google/Outlook/CalDAV sync apps which all have fixed field mappings.

## Recommendation

Follow the established sync app architecture exactly (6 services + manifest + templates + tests + docs), layering the custom field mapping as a setup step between authentication and sync configuration. Build in this order:

1. **OAuth + workspace/project selection** (prove API access, list projects)
2. **Custom field discovery + mapping UI** (the novel, risky slice — prove before sync)
3. **Pull sync with configurable mapping** (use stored field config to drive transforms)
4. **Push sync + subtask nesting** (push with section/custom-field reverse mapping, subtask recursion)
5. **E2E tests + user guide** (mock Asana REST API server, Playwright test, Chapter 40)

## Implementation Landscape

### Key Files

**Existing patterns to clone from (6 prior sync apps):**
- `apps/linear-sync/` — closest task-provider analog (app.py ~280 lines, manifest.yaml, services/ with 6 modules, frontend/ with connect.html + connect_status.html + styles.css)
- `apps/linear-sync/services/auth.py` — API key auth pattern (Asana supports PAT too, but design doc specifies OAuth)
- `apps/google-calendar/services/auth.py` — full OAuth 2.0 pattern with code exchange, token refresh, expiry buffer, store/clear/status helpers (~260 lines)
- `apps/linear-sync/services/sync_engine.py` — two-phase bulk create pattern, SPARQL task lookup, loop prevention via `lastSyncedAt`, push via `_find_changed_tasks` SPARQL (~340 lines)
- `apps/linear-sync/services/field_mapper.py` — `build_task_properties()` pure function, status/priority normalization maps, `compute_issue_slug()`, reverse mapping for push (~360 lines)
- `apps/linear-sync/services/person_matcher.py` — SPARQL email lookup with create-on-miss and LRU cache (~140 lines)
- `apps/linear-sync/services/linear_client.py` — REST/GraphQL client with auth header injection, pagination, error hierarchy (~395 lines)
- `apps/todoist-sync/services/todoist_client.py` — REST client pattern for REST-only APIs (Asana is REST-only, no GraphQL)

**New files to create:**
- `apps/asana-sync/` — full app directory
- `apps/asana-sync/manifest.yaml` — appId "asana-sync", network: ["app.asana.com"], OAuth permissions
- `apps/asana-sync/app.py` — route handlers including field mapping config endpoints
- `apps/asana-sync/services/auth.py` — Asana OAuth 2.0 (authorize URL, code exchange, refresh)
- `apps/asana-sync/services/asana_client.py` — REST client with `opt_fields`, pagination, rate limit headers
- `apps/asana-sync/services/field_mapper.py` — configurable status/priority mapping, section-based mapping
- `apps/asana-sync/services/sync_engine.py` — pull/push with subtask recursion
- `apps/asana-sync/services/person_matcher.py` — standard SPARQL email lookup (clone from prior)
- `apps/asana-sync/frontend/templates/` — connect.html, connect_status.html (extended with field mapping UI)
- `apps/asana-sync/frontend/static/styles.css`
- `backend/tests/test_asana_*.py` — unit tests (5+ files following prior pattern)
- `e2e/tests/40-asana-sync/` — Playwright E2E spec
- `e2e/mocks/asana/` — mock Asana REST API server
- `docs/guide/40-asana-sync.md` — user guide Chapter 40

### Asana API Specifics

**Authentication:** Asana OAuth 2.0 — `https://app.asana.com/-/oauth_authorize` for authorize, `https://app.asana.com/-/oauth_token` for token exchange/refresh. Scopes are implicit (no explicit scope parameter). Access tokens expire after 1 hour. Refresh tokens are long-lived. Alternative: Personal Access Token (PAT) via `Authorization: Bearer {pat}` — simpler for local dev, same as Linear API key pattern.

**REST API pattern:** All resources at `https://app.asana.com/api/1.0/`. Responses wrapped in `{"data": ...}`. Pagination via `offset` token in response. **`opt_fields` is critical** — without it, responses return minimal fields. Must specify `opt_fields=name,notes,completed,due_on,assignee.email,custom_fields,...` on every request.

**Rate limiting:** Cost-based, not count-based. Each request costs 1-10 units depending on complexity. ~1500 cost units per minute. Headers: `X-Asana-Rate-Limit-Enforced`, `Retry-After`. The client must read `Retry-After` and back off on 429.

**Subtasks:** `GET /tasks/{gid}/subtasks` returns direct children. Recursion needed for nested subtasks (up to 5 levels per design doc). Each level is a separate API call per parent — this is the most expensive operation. Use `opt_fields` aggressively.

**Custom fields:** Returned on task objects when `opt_fields=custom_fields,custom_fields.name,custom_fields.enum_options,...`. Each custom field has `gid`, `name`, `resource_subtype` (text/number/enum/multi_enum/date/people), and value. Enum fields have `enum_value.name` for single select, `multi_enum_value[].name` for multi-select.

**Sections:** `GET /projects/{gid}/sections` returns all sections in a project. Tasks belong to sections via `memberships[].section.gid`. Section names map to Kanban columns.

**Webhooks (out of scope for v1):** Project-scoped, payload contains only changed resource GID + action type. Follow-up GET required for data. Same polling-only pattern as M016-M021 (D200).

### Configurable Field Mapping — The Novel Pattern

This is the key differentiator from prior sync apps. The settings flow must:

1. After OAuth, user selects workspace → project(s)
2. App discovers custom fields on selected project(s) via `GET /projects/{gid}/custom_fields`
3. App presents discovered fields with mapping dropdowns:
   - "Which field represents **Status**?" → dropdown of enum custom fields + "Use sections" + "None"
   - "Which field represents **Priority**?" → dropdown of enum custom fields + "None"
   - "Which field represents **Story Points**?" → dropdown of number custom fields + "None"
4. For status enum mapping: show discovered enum option names with bpkm:taskStatus value dropdowns
5. For section-based status: show discovered section names with bpkm:taskStatus value dropdowns
6. Configuration stored as JSON in StateClient

**State shape example:**
```json
{
  "status_source": "custom_field",       // "custom_field" | "section" | "completed_only"
  "status_field_gid": "1234567890",
  "status_mapping": {
    "To Do": "todo",
    "In Progress": "in-progress",
    "Done": "done",
    "Blocked": "blocked"
  },
  "priority_field_gid": "9876543210",
  "priority_mapping": {
    "Low": "low",
    "Medium": "medium",
    "High": "high",
    "Urgent": "critical"
  },
  "story_points_field_gid": "5555555555"
}
```

The field mapper must read this configuration at sync time and use it to transform custom field values into bpkm properties. Reverse mapping for push sync uses the inverse of the stored maps.

### Build Order

1. **S01: OAuth + workspace/project selection** — Proves API access. Clone Google Calendar OAuth pattern. Asana OAuth has slightly different endpoints but same code-exchange flow. Add workspace list (`GET /workspaces`), project list (`GET /workspaces/{gid}/projects`), selection UI.

2. **S02: Custom field discovery + mapping UI** — The novel, highest-risk slice. This must work before sync can run. Discover custom fields per project, present mapping UI, persist configuration. No actual sync yet — just prove the configuration flow.

3. **S03: Pull sync** — Standard two-phase bulk with configurable field transforms. Subtask recursion (up to 5 levels). Section membership lookup. HTML→Markdown for notes field. All field mapping reads from S02's stored configuration.

4. **S04: Push sync** — Reverse mapping for status/priority using stored config. Section-based push requires `POST /sections/{gid}/addTask` instead of field PATCH. Subtask parent linking on push.

5. **S05: E2E + docs** — Mock Asana REST API server (like prior mocks), Playwright E2E test, Chapter 40 user guide.

### Verification Approach

- **Unit tests:** importlib-loaded from `apps/asana-sync/services/` into `backend/tests/test_asana_*.py`. Pure function tests for field mapper (configurable transforms), sync engine (mock clients), auth (OAuth flow), client (pagination, opt_fields, rate limit). Target: 200+ tests.
- **Mock server:** `e2e/mocks/asana/server.py` — canned responses for workspaces, projects, sections, tasks, subtasks, custom fields, users. Selftest checks.
- **E2E test:** `e2e/tests/40-asana-sync/asana-sync.spec.ts` — install → OAuth → configure fields → sync → verify → push lifecycle.
- **User guide:** `docs/guide/40-asana-sync.md` — Asana setup, custom field mapping walkthrough, section-based status, troubleshooting.

## Constraints

- **Asana REST API only** — no GraphQL. All requests via `https://app.asana.com/api/1.0/`.
- **`opt_fields` required** — without explicit field lists, API returns minimal data. Client must construct opt_fields strings for each endpoint.
- **Cost-based rate limiting** — `Retry-After` header on 429. Client must implement backoff. ~1500 units/min is generous for polling.
- **Subtask recursion costs** — Each subtask level requires a separate API call per parent task. 100 tasks × 5 levels = worst case 500 API calls. Must be bounded.
- **App Platform SDK IRI prefix enforcement** — Same D204 workaround: bypass CommandClient via `ctx.commands._client` for bulk commands on platform-minted IRIs.
- **htmx template URLs must use `/app/asana-sync/` prefix** — per KNOWLEDGE.md "App template htmx URLs must use proxy prefix".

## Common Pitfalls

- **Subtask API returns different fields than task list** — subtask endpoint may need its own `opt_fields` string. Test with real API or thorough mocks.
- **Custom field GIDs are project-specific** — a "Priority" custom field in Project A has a different GID than in Project B. The mapping configuration must be per-project or handle the case where the same-named field has different GIDs across projects.
- **Section membership is per-project** — a task in multiple projects can be in different sections in each. The design doc says "First project's section" for `bpkm:taskGroup`.
- **Asana `notes` field is HTML** — must use HTML→Markdown conversion (same as Outlook's `markdownify` approach, D220).
- **Milestone tasks** — `resource_subtype: "milestone"` should map to `bpkm:Milestone`, not `bpkm:Task`. Field mapper must check this.
- **PAT vs OAuth** — Supporting both (like Linear D199) simplifies local dev. PAT is just `Authorization: Bearer {pat}` with no refresh flow.

## Open Risks

- **Custom field discovery across multiple projects** — if user selects 3 projects with different custom field sets, the mapping UI must handle the union or require per-project configuration. Recommend: union of custom fields across selected projects, with a note about which projects use each field.
- **Section-to-status mapping stability** — section names can change. If a user renames a section, the mapping breaks silently. May need section GID-based mapping with name as display label.
- **Subtask depth explosion** — 5 levels × many parents could hit rate limits on initial sync. May need depth limiting or batched recursion with progress reporting.
- **Push sync for section-based status** — moving a task between sections requires `POST /sections/{gid}/addTask`, not a field PATCH. This is a different API pattern than prior sync apps' push.

## Candidate Requirements

Based on the CONTEXT and design doc, these should be registered as requirements during roadmap planning:

| ID | Description | Class |
|----|-------------|-------|
| ASANA-01 | Asana OAuth 2.0 authentication (+ optional PAT) | core-capability |
| ASANA-02 | Workspace and project selection | core-capability |
| ASANA-03 | Custom field discovery and configurable status mapping | core-capability |
| ASANA-04 | Custom field configurable priority mapping | core-capability |
| ASANA-05 | Pull sync (Asana tasks → bpkm:Task) with configurable field transforms | core-capability |
| ASANA-06 | Subtask nesting up to 5 levels via bpkm:parentTask | core-capability |
| ASANA-07 | Section-based status mapping (alternative to custom field) | core-capability |
| ASANA-08 | Push sync (bpkm:Task → Asana) with reverse field mapping | core-capability |
| ASANA-09 | Person matching (assignee/follower email resolution) | core-capability |
| ASANA-10 | E2E tests + mock Asana REST API server | quality-attribute |
| ASANA-11 | User guide Chapter 40 | quality-attribute |

## Sources

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §1 — complete Asana entity/field/status/priority/custom-field mapping tables
- Asana REST API documentation (https://developers.asana.com/reference) — endpoint patterns, pagination, opt_fields, rate limiting, OAuth
- 6 prior sync apps (M016-M021) — established architecture pattern, each with 6 services + manifest + templates + tests + docs
