---
estimated_steps: 5
estimated_files: 4
---

# T03: Add Playwright federation project and E2E sync test

**Slice:** S06 — Federation Bug Fix & Dual-Instance Testing
**Milestone:** M002

## Description

This is the integration proof task. It adds a Playwright `federation` project and writes an E2E test that exercises the full invite → accept → sync flow between two real Docker-based SemPKM instances. The test uses the API directly (no browser sessions needed) since federation is an API-level flow.

The test follows the "hybrid approach" from S06 research: real API calls for setup/sync, but direct SPARQL insertion for the invitation delivery step (bypassing HTTP Signatures and the WebFinger HTTPS requirement in local Docker). This tests the accept → sync flow with maximum fidelity while avoiding the complexity of cross-instance cryptographic signing in E2E tests.

## Steps

1. Add a `federation` project to `e2e/playwright.config.ts`:
   - Matches `18-federation/*.spec.ts`
   - Uses `http://localhost:3911` as base URL (instance A)
   - Sequential execution, single worker
   - Separate from the main test projects (doesn't run by default with `chromium`/`firefox`)

2. Extend `e2e/helpers/api-client.ts` with federation helper methods:
   - `setWebIDUsername(username: string)` — POST `/api/webid/username`
   - `publishWebID()` — POST `/api/webid/publish`
   - `getWebIDProfile()` — GET `/api/webid/profile`
   - `createSharedGraph(name: string, model?: string)` — POST `/api/federation/shared-graphs`
   - `getSharedGraphs()` — GET `/api/federation/shared-graphs`
   - `copyObjectToSharedGraph(graphId: string, objectIri: string)` — POST `/api/federation/shared-graphs/{graphId}/copy`
   - `syncSharedGraph(graphId: string)` — POST `/api/federation/shared-graphs/{graphId}/sync`
   - `listSharedGraphObjects(graphId: string)` — GET `/api/federation/shared-graphs/{graphId}/objects`
   - `acceptInvitation(notificationIri: string)` — POST `/api/federation/invitations/accept`
   - `getNotifications(state?: string)` — GET `/api/inbox`

3. Add `readFederationSetupToken(instance: 'a' | 'b')` to `e2e/fixtures/auth.ts`:
   - Reads setup token from `docker compose -f docker-compose.federation-test.yml exec -T api-a cat /app/data/.setup-token` (or `api-b`)
   - Similar pattern to existing `readSetupToken()` but parameterized for federation compose file and service name

4. Write `e2e/tests/18-federation/federation-sync.spec.ts`:
   - **Setup phase:** Create two API request contexts (A at `localhost:3911`, B at `localhost:3912`). Claim both instances via their respective setup tokens. Login as owner on both.
   - **WebID phase:** Set WebID usernames on both instances (`alice` on A, `bob` on B). Publish WebIDs on both.
   - **Shared graph phase:** Instance A creates a shared graph.
   - **Invitation simulation:** Insert an AS:Offer notification directly into instance B's triplestore via B's SPARQL endpoint (POST `/api/sparql`). The notification mirrors the format `send_invitation()` produces: `type: Offer`, `actor: <alice's WebID on A>`, `object: { id: <shared graph IRI>, name: "..." }`, `target: <bob's WebID on B>`. This bypasses HTTP Signatures/WebFinger while testing the full accept → sync path.
   - **Accept phase:** Instance B calls accept-invitation API with the notification IRI. Verify B now has the shared graph in its list.
   - **Content phase:** Instance A creates an object (e.g., a Note) via command API, then copies it to the shared graph.
   - **Sync phase:** Instance B triggers sync on the shared graph. Assert sync result has `pulled > 0` or `applied > 0`.
   - **Verification phase:** Instance B lists shared graph objects and asserts the object from A appears.

5. Run the test against the federation Docker stack and verify it passes end-to-end.

## Must-Haves

- [ ] Playwright `federation` project defined in config (separate from main projects)
- [ ] `ApiClient` extended with federation, WebID, and notification helper methods
- [ ] `readFederationSetupToken` helper reads from correct compose file and service
- [ ] E2E test covers: setup both → publish WebIDs → create shared graph → simulate invitation → accept → copy object → sync → verify
- [ ] Test passes with `npx playwright test tests/18-federation/federation-sync.spec.ts --project=federation`

## Verification

- `cd e2e && npx playwright test tests/18-federation/federation-sync.spec.ts --project=federation` passes
- Test output shows all steps executed: setup, WebID, shared graph, invitation, accept, copy, sync, verify

## Observability Impact

- Signals added/changed: None directly — the test exercises existing API endpoints and inspects their responses
- How a future agent inspects this: test output shows step-by-step progress; on failure, Playwright trace captures the exact API call that failed with request/response details
- Failure state exposed: each test step uses `expect()` with descriptive messages; sync result includes `pulled`/`applied`/`errors` fields for diagnosing partial failures

## Inputs

- `docker-compose.federation-test.yml` — from T02, defines the two instances
- `e2e/scripts/start-federation-env.sh` — from T02, starts the federation stack
- `e2e/fixtures/auth.ts` — existing auth patterns (readSetupToken, ensureSetup, loginViaApi)
- `e2e/helpers/api-client.ts` — existing API client to extend
- `backend/app/federation/router.py` — API endpoint contracts (sync, copy, shared-graphs, invitations/accept)
- `backend/app/federation/inbox.py` — notification format for SPARQL insertion
- `backend/app/webid/router.py` — WebID username/publish endpoints
- T01 summary — bug fix ensures discover works with HTTP members

## Expected Output

- `e2e/playwright.config.ts` — updated with `federation` project
- `e2e/tests/18-federation/federation-sync.spec.ts` — passing E2E federation test
- `e2e/helpers/api-client.ts` — extended with federation/WebID methods
- `e2e/fixtures/auth.ts` — extended with `readFederationSetupToken`
