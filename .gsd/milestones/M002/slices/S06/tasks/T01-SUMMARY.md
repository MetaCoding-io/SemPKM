---
id: T01
parent: S06
milestone: M002
provides:
  - discover_remote_instance_url filters to HTTP(S) WebIDs only
  - syncSharedGraph sends clean empty body for auto-discovery
  - unit test suite for federation discovery logic
key_files:
  - backend/app/federation/service.py
  - frontend/static/js/federation.js
  - backend/tests/test_federation_discovery.py
key_decisions:
  - Filter WebIDs in Python after SPARQL query rather than adding FILTER(STRSTARTS()) in SPARQL — keeps the SPARQL simple and the filtering logic testable in Python
patterns_established:
  - AsyncMock-based unit testing pattern for FederationService methods
observability_surfaces:
  - Warning log "No remote HTTP(S) members found for shared graph %s" when discovery finds no usable members
duration: 15m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Fix Sync Now auto-discovery bug and add unit tests

**Fixed `discover_remote_instance_url()` to filter out URN WebIDs that produce nonsense URLs, cleaned up frontend sync body, and added 7 unit tests.**

## What Happened

The root cause of the Sync Now failure was that `discover_remote_instance_url()` accepted any WebID from SPARQL results, including `urn:sempkm:user:{uuid}` local WebIDs. When the only remote member had a URN WebID, the URL derivation logic (`split("/users/")` or `rsplit("/", 1)`) produced `urn:sempkm:user:` — a nonsense string that fails on HTTP fetch.

Fixed by:
1. Removing the `LIMIT 1` from the SPARQL query so all members are returned
2. Filtering the results list to only WebIDs starting with `http://` or `https://`
3. Logging a warning when no HTTP(S) members are found (aids future diagnosis)
4. Picking the first HTTP(S) WebID for URL derivation

Also cleaned up `federation.js` to send `{}` instead of `{ remote_instance_url: '' }` — the backend treats empty string as falsy so this was functionally equivalent, but the clean empty body makes intent explicit.

## Verification

- `cd backend && .venv/bin/pytest tests/test_federation_discovery.py -v` — 7/7 tests pass
- Inspected `federation.js` line 85 — body is `JSON.stringify({})`, confirmed

Slice-level verification (partial — T01 only covers the first check):
- ✅ `cd backend && .venv/bin/pytest tests/test_federation_discovery.py -v` — passes
- ⬜ `docker compose -f docker-compose.federation-test.yml up -d --build` — T02
- ⬜ Playwright federation E2E test — T03

## Diagnostics

- Grep API logs for `"No remote HTTP(S) members"` to diagnose sync discovery failures where all members have local URN WebIDs
- The existing HTTP 400 "No remote members found" response from the sync endpoint now fires correctly for URN-only scenarios instead of producing a silent HTTP fetch failure downstream

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/federation/service.py` — `discover_remote_instance_url()` now filters to HTTP(S) WebIDs, logs warning when none found
- `frontend/static/js/federation.js` — `syncSharedGraph()` sends `{}` body instead of `{ remote_instance_url: '' }`
- `backend/tests/test_federation_discovery.py` — 7 unit tests covering HTTP, URN-only, mixed, empty, and URL derivation edge cases
