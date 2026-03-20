---
estimated_steps: 6
estimated_files: 2
---

# T02: Graph API REST client

**Slice:** S01 — Microsoft OAuth + Graph API Client
**Milestone:** M020

## Description

Build OutlookClient REST wrapper for Microsoft Graph API with authenticated requests, 401→refresh→retry, @odata.nextLink pagination, delta query support, and patch_event for RSVP updates.

## Steps

1. Build `services/outlook_client.py` with OutlookClient class: authenticated requests (Bearer token), get_calendar_list() with pagination, get_events_delta() with deltaLink/nextLink, patch_event()
2. 401→refresh→retry pattern matching M018's GCalClient
3. OUTLOOK_API_URL env var for base URL override
4. Write `backend/tests/test_outlook_client.py` with 15+ tests

## Must-Haves

- [ ] Delta query pagination handles @odata.nextLink and @odata.deltaLink correctly
- [ ] 401→refresh→retry works
- [ ] 15+ unit tests pass

## Verification

- `cd backend && python -m pytest tests/test_outlook_client.py -v` — all pass

## Inputs

- `apps/outlook-calendar/services/auth.py` — token refresh helper from T01
- `apps/google-calendar/services/gcal_client.py` — reference client to adapt

## Observability Impact

- **New logger:** `outlook.sync.client` — DEBUG for each REST request (method + URL), INFO on token refresh events
- **Error diagnosis:** Catch `OutlookAPIError` (or subclasses `OutlookAuthError`, `OutlookRateLimitError`) and inspect `.status_code` and `.response_body` for structured failure info
- **Token refresh visibility:** 401→refresh→retry logged at INFO level; refresh failures logged and wrapped as `OutlookAuthError`
- **Test isolation:** Set `OUTLOOK_API_URL` env var to override the base URL for testing

## Expected Output

- `apps/outlook-calendar/services/outlook_client.py`
- `backend/tests/test_outlook_client.py`
