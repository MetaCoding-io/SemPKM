---
estimated_steps: 5
estimated_files: 3
---

# T01: Fix Sync Now auto-discovery bug and add unit tests

**Slice:** S06 — Federation Bug Fix & Dual-Instance Testing
**Milestone:** M002

## Description

The Sync Now button fails because `discover_remote_instance_url()` in `federation/service.py` doesn't validate that discovered member WebIDs are HTTP(S) URLs. When the only other member has a `urn:sempkm:user:{uuid}` local WebID, the URL derivation produces `urn:sempkm:user:` — a nonsense string that fails on HTTP fetch. Additionally, `federation.js` explicitly sends `{ remote_instance_url: '' }` instead of an empty body, which is misleading (though technically works because the backend treats empty string as falsy).

This task fixes both issues and adds unit tests proving the discovery logic works correctly with HTTP, URN, and mixed member scenarios.

## Steps

1. In `backend/app/federation/service.py`, modify `discover_remote_instance_url()`:
   - After querying members, filter the result to only members whose WebID starts with `http://` or `https://`
   - If no HTTP(S) members remain after filtering, log a warning and return `None`
   - Keep the existing `/users/` split and `rsplit("/", 1)` URL derivation for valid HTTP(S) WebIDs

2. In `frontend/static/js/federation.js`, change `syncSharedGraph()`:
   - Replace `body: JSON.stringify({ remote_instance_url: '' })` with `body: JSON.stringify({})`
   - This makes intent clearer: "auto-discover, don't override"

3. Create `backend/tests/test_federation_discovery.py` with unit tests:
   - Test `discover_remote_instance_url` with a mock client returning an HTTP WebID member → should derive correct instance URL
   - Test with only `urn:sempkm:user:{uuid}` members → should return `None`
   - Test with mixed HTTP and URN members → should pick the HTTP one
   - Test with no members at all → should return `None`
   - Test URL derivation: `https://instance-a.example.com/users/alice#me` → `https://instance-a.example.com`

4. Run the unit tests and verify they all pass.

5. Verify the JS change doesn't break the frontend by inspecting the fetch call structure.

## Must-Haves

- [ ] `discover_remote_instance_url()` filters to HTTP(S) WebIDs only
- [ ] `discover_remote_instance_url()` logs warning when no HTTP(S) members found
- [ ] `syncSharedGraph()` sends `{}` body instead of `{ remote_instance_url: '' }`
- [ ] Unit tests cover: HTTP member, URN-only member, mixed, empty results
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/pytest tests/test_federation_discovery.py -v` — all tests pass
- Read `federation.js` line ~85 — body is `{}` not `{ remote_instance_url: '' }`

## Observability Impact

- Signals added/changed: Warning log in `discover_remote_instance_url` when no HTTP(S) members found (`"No remote HTTP(S) members found for shared graph %s"`)
- How a future agent inspects this: grep API logs for "No remote HTTP(S) members" to diagnose sync discovery failures
- Failure state exposed: sync endpoint returns HTTP 400 "No remote members found" when discovery returns None — this already exists but will now fire correctly for URN-only scenarios instead of producing a silent HTTP fetch failure downstream

## Inputs

- `backend/app/federation/service.py` — existing `discover_remote_instance_url()` at line 550
- `frontend/static/js/federation.js` — existing `syncSharedGraph()` at line 75
- `backend/app/federation/router.py` — `sync_shared_graph` endpoint that calls discovery (read-only reference)
- S06-RESEARCH.md — root cause analysis confirming the `urn:` WebID derivation bug

## Expected Output

- `backend/app/federation/service.py` — `discover_remote_instance_url()` filters members to HTTP(S) URLs
- `frontend/static/js/federation.js` — `syncSharedGraph()` sends clean empty body
- `backend/tests/test_federation_discovery.py` — unit tests for discovery logic (all passing)
