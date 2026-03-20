---
id: T02
parent: S01
milestone: M020
provides:
  - OutlookClient REST wrapper for Microsoft Graph API with authenticated requests, pagination, delta queries, and patch
key_files:
  - apps/outlook-calendar/services/outlook_client.py
  - backend/tests/test_outlook_client.py
key_decisions:
  - Delegate token refresh to auth.py's refresh_if_expired instead of inline refresh logic (unlike GCalClient which does inline refresh) — keeps token lifecycle in one module
  - Use @odata.nextLink as full URL for pagination (Microsoft pattern) vs GCalClient's nextPageToken query param approach
patterns_established:
  - Microsoft Graph delta queries: get_events_delta() returns (events, delta_link) tuple; pass delta_link back for incremental sync
  - Test module loading: register auth module in sys.modules before loading outlook_client so the deferred import in _handle_token_refresh resolves
observability_surfaces:
  - "outlook.sync.client" logger — DEBUG for each REST request (method + URL), INFO on token refresh
  - OutlookAuthError / OutlookRateLimitError / OutlookAPIError carry status_code and response_body for structured diagnosis
duration: 12m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T02: Graph API REST client

**Built OutlookClient REST wrapper for Microsoft Graph API with 401→refresh→retry, @odata.nextLink pagination, delta query support, and 24 unit tests**

## What Happened

Adapted the GCalClient pattern from M018's google-calendar app to Microsoft Graph API conventions. Key adaptations:

1. **Pagination:** Microsoft Graph uses `@odata.nextLink` (a full URL) instead of Google's `nextPageToken` (a query parameter). The client follows `@odata.nextLink` directly rather than appending parameters.

2. **Delta queries:** `get_events_delta()` accepts an optional `delta_link` for incremental sync. On first call, hits `/me/calendars/{id}/events/delta?$top=50`. Paginates via `@odata.nextLink` and returns the final `@odata.deltaLink` for subsequent calls. Deleted events pass through with `@removed` key intact.

3. **Token refresh delegation:** Instead of duplicating the token endpoint call (like GCalClient does inline), `_handle_token_refresh` delegates to `auth.refresh_if_expired` from T01's auth module. This keeps all token lifecycle logic in one place.

4. **Exception hierarchy:** `OutlookAPIError` → `OutlookAuthError` (401/403) and `OutlookRateLimitError` (429), matching the GCalClient pattern with Microsoft-specific naming.

## Verification

- `cd backend && python -m pytest tests/test_outlook_client.py -v` — 24/24 passed
- `cd backend && python -m pytest tests/test_outlook_auth.py tests/test_outlook_client.py -v` — 65/65 passed (slice-level)
- `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ | grep -v '/app/outlook-calendar/'` — empty (no hardcoded htmx URLs)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_outlook_client.py -v` | 0 | ✅ pass | 0.06s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_outlook_auth.py tests/test_outlook_client.py -v` | 0 | ✅ pass | 0.09s |
| 3 | `grep -rn 'hx-\(get\|post\|put\|delete\)="/' apps/outlook-calendar/ \| grep -v '/app/outlook-calendar/'` | 1 | ✅ pass (no matches) | <0.01s |

## Diagnostics

- **Logger:** `outlook.sync.client` at DEBUG for each REST request (method + URL), INFO for token refresh lifecycle
- **Error diagnosis:** Catch `OutlookAPIError` and inspect `.status_code` and `.response_body` for structured failure info
- **Exception subclasses:** `OutlookAuthError` for 401/403, `OutlookRateLimitError` for 429 (includes `.retry_after` seconds)
- **Test isolation:** Set `OUTLOOK_API_URL` env var to override the Graph API base URL

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/outlook-calendar/services/outlook_client.py` — OutlookClient REST wrapper with get_calendar_list, get_events_delta, patch_event, and 401→refresh→retry
- `backend/tests/test_outlook_client.py` — 24 unit tests covering auth headers, calendar list, delta queries, patch, 401→refresh→retry, error handling, and exception hierarchy
- `.gsd/milestones/M020/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
