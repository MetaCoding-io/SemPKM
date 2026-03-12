# S06: Federation Bug Fix & Dual-Instance Testing — Research

**Date:** 2026-03-12

## Summary

S06 delivers three requirements: FED-11 (Sync Now auto-discovery bug fix), FED-12 (dual-instance docker-compose), and FED-13 (Playwright E2E test for invite → accept → sync). The Sync Now bug is straightforward — the frontend sends an empty `remote_instance_url` and the backend already has `discover_remote_instance_url()` which works correctly when the body is empty/absent. The real fix is minimal: stop sending the empty string from JS (or make it truly omit empty). The harder work is the dual-instance compose file and the E2E test, which require two complete SemPKM stacks that can reach each other's APIs and have distinct WebID identities.

The federation flow is complex: it involves WebID profiles, Ed25519 key pairs, HTTP Signatures (RFC 9421), LDN inbox posting, WebFinger discovery, and RDF Patch sync. The E2E test must orchestrate all of this between two instances. The most practical approach is an API-driven test that sets up both instances programmatically, bypassing the UI for setup steps and using Playwright's API request context rather than two browser sessions for the invite/accept/sync flow.

## Recommendation

### FED-11: Sync Now Bug Fix
The bug is in `federation.js` line 85: `body: JSON.stringify({ remote_instance_url: '' })`. The backend router at `sync_shared_graph` already handles the empty case correctly — when `remote_url` is empty, it calls `service.discover_remote_instance_url()`. But the frontend always sends `{ remote_instance_url: '' }` which means `body.get("remote_instance_url", "")` returns `""` — a falsy string. This triggers the auto-discover path correctly.

**Wait — re-reading the router:** the code already handles this! If `remote_url` is empty string (falsy), it falls through to `discover_remote_instance_url()`. So the backend already auto-discovers. The actual bug must be that `discover_remote_instance_url` fails because there are no remote members stored in the federation graph, OR the WebID derivation logic (`"/users/" in webid` → split) doesn't produce a valid instance URL from `urn:sempkm:user:{uuid}` local WebIDs.

**Root cause analysis:** When user A creates a shared graph, their member entry is `urn:sempkm:user:{uuid}` (the `_get_user_webid()` fallback). When user B on instance B accepts the invitation, the `accept_invitation()` method stores both members: `<{user_webid}>` (user B's local WebID) and `<{sender_webid}>` (user A's WebID from the notification). For `discover_remote_instance_url()` to work, the remote member's WebID must be an `https://` URL, not a `urn:sempkm:user:` local ID. If the sender published a WebID profile (e.g. `https://instance-a:3000/users/alice#me`), that URL is what gets stored. The instance URL derivation (`webid.split("/users/")[0]`) would then correctly produce `https://instance-a:3000`.

So the full flow works IF the inviting user has published their WebID. If they haven't, the stored member is `urn:sempkm:user:{uuid}`, and `discover_remote_instance_url()` returns a useless `urn:sempkm:user:{uuid}` minus the last path segment = `urn:sempkm:user:`. This is the actual bug: the discovery doesn't validate that the derived URL is a proper HTTP(S) URL.

**Fix plan:**
1. In `federation.js`: remove the explicit empty `remote_instance_url` from the POST body (just send `{}` or no body) — cleaner intent.
2. In `discover_remote_instance_url()`: filter members to only those with `http://` or `https://` WebID URLs (skip `urn:` local IDs).
3. Consider logging a warning when no remote HTTP members are found.

### FED-12: Dual-Instance Docker Compose
Create `docker-compose.federation-test.yml` with two full SemPKM stacks (instance A on ports 3911/8911, instance B on ports 3912/8912) sharing a single Docker network so they can reach each other. Each instance needs:
- Its own RDF4J triplestore
- Its own SQLite database volume
- Its own API backend
- Its own nginx frontend
- Different `BASE_NAMESPACE` values
- `APP_BASE_URL` set to the nginx frontend URL that the other instance can reach (critical for WebID/WebFinger)

Key networking insight: the instances need to reach each other via their Docker service names, but `APP_BASE_URL` must be set to a URL that's resolvable from the other instance's API container. Since both are on the same Docker network, service names work. But WebID URLs must also be fetchable — the remote instance needs to GET the WebID profile. So `APP_BASE_URL` for instance A should be `http://frontend-a:80` (the nginx service name) or `http://api-a:8000` (direct backend access).

Actually, the simpler approach: since federation HTTP requests go from one API container to the other's nginx (or API directly), we should use the API container's internal URLs. The `APP_BASE_URL` for instance A should be `http://frontend-a:80` and for B `http://frontend-b:80`. This way WebFinger discovery and profile fetching route through nginx.

### FED-13: E2E Test
Write a Playwright test that:
1. Uses API request contexts (no browser needed for most steps) against both instances
2. Sets up both instances (claim with setup tokens)
3. Sets up WebID profiles on both instances (username, publish)
4. Instance A creates a shared graph
5. Instance A invites instance B's user (via WebFinger handle or WebID URL)
6. Instance B accepts the invitation
7. Instance A copies an object to the shared graph
8. Instance B triggers sync
9. Verify B has the object

The test needs a separate Playwright config or a parameterized project pointing to the federation compose file.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| E2E test auth setup | `e2e/fixtures/auth.ts` | Has `loginViaApi`, `ensureSetup`, `readSetupToken` patterns |
| Docker stack management | `e2e/scripts/start-test-env.sh` | Existing pattern for compose teardown/rebuild/wait |
| Playwright API calls | `e2e/helpers/api-client.ts` | Extend with federation methods rather than raw fetch |
| HTTP Signature signing | `federation/signatures.py` | Already implements RFC 9421 sign/verify |
| RDF Patch serialization | `federation/patch.py` | Already has serialize/deserialize |

## Existing Code and Patterns

- `backend/app/federation/router.py` — All federation API endpoints. `sync_shared_graph` already handles auto-discovery when `remote_instance_url` is empty. The `_get_user_webid()` helper falls back to `urn:sempkm:user:{id}` when no published WebID exists — this fallback is the root cause of discovery failures.
- `backend/app/federation/service.py` — `discover_remote_instance_url()` queries federation graph for non-local members but doesn't validate the derived URL is HTTP(S). `accept_invitation()` stores the sender WebID from the notification. `sync_shared_graph()` fetches patches from remote, deserializes, and applies via EventStore.
- `frontend/static/js/federation.js` — `syncSharedGraph()` sends `{ remote_instance_url: '' }` in POST body. Should send empty body or omit the field.
- `docker-compose.test.yml` — Template for isolated test stacks. Uses separate volumes, ports (3901/8901), network (`sempkm-test`).
- `e2e/playwright.config.ts` — Tests run against port 3901, sequential, single worker. Federation test will need a separate project or config pointing to federation ports.
- `e2e/fixtures/auth.ts` — `readSetupToken()` reads from Docker container. Federation test will need to read from two different compose services.
- `backend/app/webid/router.py` — WebID profile endpoints: `/api/webid/username`, `/api/webid/publish`. Profile served at `/users/{username}` with content negotiation (Turtle, JSON-LD, HTML). LDN inbox link header included.
- `backend/app/federation/inbox.py` — LDN inbox at `/api/inbox`. Verifies HTTP Signatures via `VerifyHTTPSignature()` dependency. Stores notifications as named graphs.
- `backend/app/config.py` — `app_base_url` setting controls how WebID URIs are constructed. Must be set for federation so remote instances can resolve the URL.

## Constraints

- **WebID publication required:** The inviting user MUST have a published WebID with an HTTP(S) URL for federation to work. `urn:sempkm:user:{uuid}` local IDs cannot be resolved by remote instances.
- **HTTP Signatures required for inbox:** The LDN inbox endpoint (`POST /api/inbox`) requires a valid HTTP Signature verified against the sender's WebID public key. The E2E test must either: (a) set up real key pairs and sign requests, or (b) bypass signature verification for testing.
- **APP_BASE_URL must be set:** For federation, `app_base_url` must be a URL reachable by the remote instance. In Docker, this means the service name URL (e.g., `http://frontend-a:80`).
- **Same Docker network:** Both instances must be on the same Docker network for cross-instance HTTP communication.
- **Sequential test execution:** Federation E2E test must be sequential — each step depends on the prior step's state. The existing Playwright config already enforces `fullyParallel: false`.
- **Separate compose file for federation:** Must not conflict with the existing `docker-compose.test.yml` (ports, volumes, network).

## Common Pitfalls

- **WebID URL derivation from URN fails silently:** `discover_remote_instance_url()` tries `webid.split("/users/")[0]` on `urn:sempkm:user:{uuid}`, which doesn't contain `/users/`, so it falls through to `webid.rsplit("/", 1)[0]` = `urn:sempkm:user:` — a nonsense URL that would fail on HTTP fetch. Fix: filter for HTTP(S) URLs only.
- **Invitation delivery requires reachable inbox:** `send_invitation()` discovers the recipient's inbox via WebFinger, then POSTs a signed notification. If the recipient's instance isn't reachable, the invitation silently fails (logged but not raised to user). The E2E test must verify the invitation was actually received.
- **APP_BASE_URL vs request-derived URL mismatch:** If `app_base_url` is empty, the WebID service derives it from the request. In Docker, internal requests may produce `http://api:8000` while external requests produce `http://localhost:3911`. Federation URLs must be consistent — set `APP_BASE_URL` explicitly.
- **HTTP Signature timing:** The `sign_request` function uses RFC 9421 with Ed25519. The test must decrypt the private key from the database (encrypted with Fernet derived from `SECRET_KEY`). Alternatively, the test can call the WebID API to get the public key and use the backend's signing infrastructure.
- **RDF4J repository auto-creation:** The test compose must ensure repositories exist. The existing backend handles repository creation on startup, so this should work automatically if the triplestore is healthy before the API starts.

## Open Risks

- **HTTP Signature complexity in E2E test:** The full federation flow requires HTTP Signatures for inbox delivery. The E2E test either needs to replicate signing (complex) or the invitation step may need to be done via direct SPARQL insertion on instance B (simulating receipt). A pragmatic alternative: add a test-mode flag that bypasses signature verification on the inbox endpoint, but this reduces test fidelity.
- **WebFinger cross-instance discovery:** Instance A needs to resolve `user@instance-b` via WebFinger. This requires instance B's `/.well-known/webfinger` endpoint to be reachable from A's API container at the domain in the handle. The handle format must match the `APP_BASE_URL` hostname. E.g., if B's `APP_BASE_URL` is `http://frontend-b:80`, the WebFinger handle would be `bob@frontend-b` and discovery goes to `https://frontend-b/.well-known/webfinger` — but this uses HTTPS! WebFinger discovery in `webfinger.py` hardcodes `https://`. For Docker testing we may need `http://`.
- **WebFinger HTTPS requirement:** `discover_webid()` constructs `https://{domain}/.well-known/webfinger` — hardcoded HTTPS. In a local Docker test environment, there's no TLS. Options: (a) modify discovery to try HTTP as fallback, (b) add a setting to control the scheme, (c) bypass WebFinger and use direct WebID URLs in invitations, (d) use direct SPARQL to simulate invitation receipt.
- **Port mapping complexity:** Two full stacks = 6 containers (2× triplestore, api, frontend). Port allocation must avoid conflicts with dev stack (3000/8001) and test stack (3901/8901).

## Implementation Strategy

Given the HTTP Signature and WebFinger HTTPS constraints, the recommended E2E test strategy is a **hybrid approach**:

1. **API-driven setup:** Use Playwright's `request.newContext()` to set up both instances (claim, create users, publish WebIDs).
2. **Direct invitation simulation:** Instead of going through WebFinger + HTTP Signatures for the invitation, directly insert the invitation notification into instance B's triplestore via instance B's API (or use a test-only endpoint). This avoids the HTTPS/signing complexity while still testing the accept → sync flow.
3. **Full sync verification:** The sync pull (instance B pulling patches from A) goes through a normal HTTP GET with auth — this is simpler than inbox POST because the patch export endpoint uses session auth, not HTTP Signatures.

**OR** the cleaner alternative: fix `discover_webid()` to support HTTP for local/test environments, and implement real cross-instance invitation. This has higher fidelity but more risk.

**Recommended approach:** Start with the hybrid (direct SPARQL notification insertion), get the full flow working end-to-end, then evaluate if upgrading to real cross-instance signing is worth the additional complexity.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Playwright E2E | `bobmatnyc/claude-mpm-skills@playwright-e2e-testing` (1.2K installs) | available |
| Docker Compose | `manutej/luxor-claude-marketplace@docker-compose-orchestration` (397 installs) | available |

Neither is critical — the existing E2E infrastructure and compose patterns in the repo provide sufficient templates.

## Sources

- Sync Now bug analysis: `frontend/static/js/federation.js:85`, `backend/app/federation/router.py:sync_shared_graph`, `backend/app/federation/service.py:discover_remote_instance_url`
- Federation flow: `backend/app/federation/service.py` (full service), `backend/app/federation/inbox.py` (LDN receiver), `backend/app/federation/signatures.py` (HTTP Signatures)
- Docker compose pattern: `docker-compose.test.yml` (isolated test stack template)
- E2E test infra: `e2e/playwright.config.ts`, `e2e/fixtures/auth.ts`, `e2e/helpers/api-client.ts`
- WebID profile: `backend/app/webid/router.py`, `backend/app/webid/service.py`
- WebFinger: `backend/app/federation/webfinger.py` (HTTPS hardcoded at line ~82)
