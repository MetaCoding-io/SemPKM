# S01: Security Findings — Injection, Access Control & Authentication

**Milestone:** M042 — Security Audit & Hardening
**OWASP Categories:** A01 (Broken Access Control), A03 (Injection), A07 (Identification and Authentication Failures)
**Scope:** SemPKM backend (FastAPI + nginx), all routers, auth subsystem, session management
**Assessment Model:** Cloud deployment with federation enabled (most exposed); localhost mitigations noted where applicable

---

## A01: Broken Access Control

### F-001: Missing Authentication on 6 Browser App Endpoints

**Severity:** Medium
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `backend/app/browser/apps.py`

**Description:**
Six of eight endpoints on the `apps_router` and `app_commands_router` lack any authentication dependency. These endpoints serve HTML fragments and JSON for the workspace UI:

| Endpoint | Auth | Risk |
|---|---|---|
| `GET /browser/apps/explorer` | **None** | Leaks list of running apps, nav pages, status |
| `GET /browser/apps/{app_id}/page/{page_id}` | **None** | Renders app page content for any app |
| `GET /browser/apps/right-pane-sections` | **None** | SPARQL injection vector (see F-A03-02 in A03 section) + leaks object type info |
| `GET /browser/apps/views/explorer` | **None** | Leaks app view manifest entries |
| `GET /browser/apps/{app_id}/view/{view_id}` | **None** | Renders app view tab content |
| `GET /browser/apps/commands` | **None** | Leaks command palette entries from running apps |
| `GET /browser/apps/catalog` | ✅ `get_current_user` | OK |
| `GET /browser/apps/catalog/{app_id}` | ✅ `get_current_user` | OK |

**Exploit Scenario:**
An unauthenticated attacker can enumerate running apps, their page structures, and view manifests. The `right-pane-sections` endpoint additionally takes an `iri` query parameter that is used in unvalidated SPARQL (see F-A03-02), compounding the access control gap with an injection vector.

**Localhost Mitigation:** Low risk when running locally — no external access. In Docker with port 3000 exposed, nginx proxies all `/browser/` paths to the backend.

**Remediation:**
Add `user: User = Depends(get_current_user)` to all six unprotected endpoint signatures.

---

### F-002: No Object-Level Ownership Enforcement (Flat Authorization Model)

**Severity:** Low (single-user/small-team), Medium (multi-tenant)
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `backend/app/browser/objects.py`, `backend/app/sparql/router.py`, `backend/app/views/router.py`, `backend/app/browser/events.py`

**Description:**
SemPKM uses a flat authorization model: all authenticated users share the same triplestore data. There is no per-object ownership, and no IDOR protection is needed in the current design because all objects are intentionally shared.

However, this means:
- Any authenticated member can read/write any object via `GET/POST /browser/objects/{iri}`
- Any authenticated member can read all events via `/browser/events/`
- The SPARQL console gives members read access to all data in `urn:sempkm:current`
- Owners can query ALL graphs (including event, inbox, federation)

**Data isolation analysis:**

| Resource | Owner Access | Member Access | Guest Access | Ownership Check |
|---|---|---|---|---|
| Objects (RDF) | Full | Full read/write | Read-only (demo) | None — shared graph |
| Canvas sessions | User-scoped ✅ | User-scoped ✅ | None | `user_id` filter in SQL |
| Dashboards | User-scoped ✅ | User-scoped ✅ | None | `user_id` filter in SQL |
| Workflows | User-scoped ✅ | User-scoped ✅ | None | `user_id` filter in SQL |
| Saved SPARQL queries | User-scoped ✅ | User-scoped ✅ | None | `owner_id` in RDF |
| API tokens | User-scoped ✅ | User-scoped ✅ | None | `user_id` filter in SQL |
| IndieAuth tokens | User-scoped ✅ | User-scoped ✅ | None | `user_id` filter in SQL |

**Exploit Scenario:**
A member-role user creates objects, adds edges, or modifies data belonging to another user. This is by design for the current collaborative model, but becomes a vulnerability if SemPKM adds multi-tenant support.

**Localhost Mitigation:** Non-issue for single-user instances.

**Remediation:**
Document the shared-data model clearly. If multi-tenant support is added, implement per-graph or per-namespace data isolation with ownership checks on all CRUD endpoints.

---

### F-003: CORS Wildcard on API Endpoints via nginx

**Severity:** Medium (cloud with federation), Low (localhost)
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `frontend/nginx.conf`, `backend/app/main.py`

**Description:**
The nginx configuration adds `Access-Control-Allow-Origin: *` on all `/api/` responses. The FastAPI CORS middleware defaults to `allow_origins=["*"]` with `allow_credentials=False` when `CORS_ORIGINS` is empty (the default).

nginx additionally adds these headers unconditionally:
```
add_header Access-Control-Allow-Origin "*" always;
add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept" always;
add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
```

**Security interaction:**
- **Session cookies:** `SameSite=Lax` prevents cross-origin cookie inclusion for non-navigation POST requests. The `*` CORS origin does NOT allow `credentials: include` in fetch — browsers enforce this. So session-cookie-authenticated endpoints are protected against CSRF via the SameSite policy.
- **Bearer tokens:** Any website can issue `fetch()` requests with a Bearer token in the `Authorization` header to the SemPKM API, and the `*` CORS policy will allow the response to be read. If an attacker obtains or guesses an API token, they can use it from any origin.
- **The /.well-known/sempkm endpoint** also has `Access-Control-Allow-Origin: *` — intentional for browser extension discovery.

**Exploit Scenario:**
1. User creates an API token at `https://my-sempkm.example.com`
2. User visits a malicious site `https://evil.com`
3. Malicious JS on evil.com makes `fetch('https://my-sempkm.example.com/api/sparql', {headers: {'Authorization': 'Bearer <stolen-token>'}})` — CORS wildcard allows reading the response
4. This is only exploitable if the attacker already has the token. The CORS wildcard does NOT allow token theft — it allows token *use* from any origin.

**Localhost Mitigation:** Non-issue — attacker cannot reach localhost from a remote origin (unless the user has port forwarding). nginx CORS headers are needed for the browser extension.

**Remediation:**
- When `CORS_ORIGINS` is configured (cloud deployment), ensure nginx does NOT override with `*`. Currently the nginx config always adds `*` regardless of backend CORS settings — the nginx `add_header` directive appends a second `Access-Control-Allow-Origin` header even when the backend already sends one.
- For cloud deployments with federation: set `CORS_ORIGINS` to the actual deployment domain, and fix nginx to not add its own CORS headers when the backend already handles it.

---

### F-004: Setup Endpoint Lacks Authentication Guard

**Severity:** Low
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `backend/app/api/setup_routes.py`

**Description:**
`POST /api/setup/configure-instance` has no auth dependency. It is guarded only by a check: `if await _check_user_data_exists(request)` which returns 409 if triplestore data exists. Before any data is created (first-run), anyone who can reach the API can set the instance's deployment mode, BASE_NAMESPACE, and APP_BASE_URL.

**Exploit Scenario:**
During the narrow window between Docker startup and owner account creation, an attacker who can reach the API could configure the instance with a malicious BASE_NAMESPACE (e.g., pointing to their own domain). This window is typically seconds on localhost but could be longer on cloud deployments.

**Localhost Mitigation:** The window is negligible for local instances. The `POST /api/auth/setup` endpoint (owner creation) has a setup-token guard, so the attacker cannot create an owner account even if they misconfigure the namespace.

**Remediation:**
Add a check that `setup_mode` is active (similar to the `/api/auth/setup` endpoint) before allowing namespace configuration.

---

### F-005: Monitoring Config Endpoint Exposes PostHog API Key Without Auth

**Severity:** Info
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `backend/app/monitoring/router.py`

**Description:**
`GET /api/monitoring/config` returns the PostHog API key, host, and enabled flag with no authentication. The PostHog project API key is a write-only ingestion key (not a read/admin key), so exposure is by design per PostHog's client-side initialization pattern.

**Exploit Scenario:**
An attacker could use the exposed ingestion key to send bogus analytics events to the PostHog project, polluting analytics data. No data exfiltration is possible.

**Remediation:**
This is by design for client-side analytics. No action needed unless analytics data integrity is critical.

---

## A03: Injection

*Findings in this section are from T01's systematic SPARQL injection triage of 33 backend modules. See the full classification table below.*

### F-006: SPARQL Injection via `type` Query Parameter in Views

**Severity:** High
**OWASP Category:** A03:2021 — Injection
**Classification:** confirmed-exploitable
**Affected Files:** `backend/app/views/router.py`, `backend/app/views/service.py`

**Data Flow:**
```
HTTP GET /browser/views/generic/table?type=PAYLOAD
  → views/router.py generic_view() → type_iri = type (no validation)
  → views/service.py build_dynamic_query(type_iri, ...)
  → _build_default_select() → f"  ?s rdf:type <{type_iri}> .\n"
  → scope_to_current_graph() → triplestore.query()
```

**Exploit Scenario:**
A user crafts the `type` parameter to break out of the angle-bracket IRI:
```
GET /browser/views/generic/table?type=x>%20.%20%3Fs%20%3Fp%20%3Fo%20}%20%23
```
Decoded: `type=x> . ?s ?p ?o } #`

This becomes `?s rdf:type <x> . ?s ?p ?o } #> .` — closing the WHERE block and commenting out the rest. The `scope_to_current_graph` defense limits exposure to `urn:sempkm:current` but all data within that graph is extractable. Approximately 10-15 endpoints in views/router.py share this vector.

**Localhost Mitigation:** Requires authenticated access (member or owner role), so attacker must have a valid session.

**Remediation:**
Add `_validate_iri(type_iri)` check in `generic_view()` and all view endpoints that accept a `type` query parameter, before passing to `build_dynamic_query()`.

---

### F-007: SPARQL Injection via `iri` Query Parameter in Apps

**Severity:** High
**OWASP Category:** A03:2021 — Injection
**Classification:** confirmed-exploitable
**Affected Files:** `backend/app/browser/apps.py`

**Data Flow:**
```
HTTP GET /browser/apps/right-pane-sections?iri=PAYLOAD
  → apps.py right_pane_sections() → iri (no validation)
  → f"SELECT ?type WHERE {{ <{iri}> a ?type }}"
  → triplestore.query()
```

**Exploit Scenario:**
Identical breakout pattern as F-006. The query has no `FROM` scoping and the endpoint has no authentication (see F-001), compounding the risk.

**Localhost Mitigation:** Partially mitigated by network isolation.

**Remediation:**
Add `_validate_iri(iri)` before SPARQL construction. Add authentication dependency. Add `scope_to_current_graph()`.

---

### F-008: SPARQL Write Injection via VFS Mount IRI Fields

**Severity:** High
**OWASP Category:** A03:2021 — Injection
**Classification:** confirmed-exploitable
**Affected Files:** `backend/app/vfs/mount_router.py`

**Data Flow:**
```
HTTP POST /browser/vfs/mounts (JSON body)
  → body.group_by_property, body.date_property, body.scope_query, body.type_filter[]
  → INSERT DATA { GRAPH <...> { <mount> <pred> <{body.group_by_property}> } }
  → triplestore.update()
```

**Exploit Scenario:**
A user creates a mount with a crafted `group_by_property`:
```json
{"name": "test", "path": "/test", "strategy": "flat",
 "group_by_property": "x> . } } ; INSERT DATA { GRAPH <urn:sempkm:current> { <urn:evil> <urn:p> <urn:o> } } #"}
```
This is a **write injection** — the attacker can insert arbitrary triples into any graph.

**Localhost Mitigation:** Requires authenticated access.

**Remediation:**
Apply `_validate_iri()` to all IRI-typed fields in mount creation/update body.

---

### F-009: Stored SPARQL Injection via Favorites

**Severity:** Medium
**OWASP Category:** A03:2021 — Injection
**Classification:** likely-exploitable
**Affected Files:** `backend/app/browser/favorites.py`

**Data Flow:**
```
HTTP POST /browser/favorites (Form: object_iri=PAYLOAD)
  → stored in SQL UserFavorite table (no validation)

HTTP GET /browser/ (workspace load)
  → values_clause = " ".join(f"(<{iri}>)" for iri in favorite_iris)
  → SPARQL SELECT with VALUES clause
```

**Exploit Scenario:**
Attacker stores a malicious IRI via the favorites form, then the workspace page load triggers the injection on every subsequent visit. Two-hop stored injection.

**Localhost Mitigation:** Requires authenticated access.

**Remediation:**
Add `_validate_iri(object_iri)` in `toggle_favorite()` before SQL storage.

---

### F-010: Incomplete SPARQL String Escaping Across Multiple Modules

**Severity:** Low
**OWASP Category:** A03:2021 — Injection
**Classification:** likely-exploitable
**Affected Files:** `backend/app/browser/events.py`, `backend/app/browser/search.py`, `backend/app/api/router.py`, `backend/app/api/ai.py`

**Description:**
Three different `_sparql_escape` functions exist with inconsistent escape coverage:

| Function | Location | `\` | `"` | `\n` | `\r` | `\t` |
|---|---|---|---|---|---|---|
| `_sparql_escape` | search.py, workspace.py | ✓ | ✓ | ✓ | ✗ | ✗ |
| `_sparql_escape_str` | api/router.py, api/ai.py | ✓ | ✓ | ✓ | ✗ | ✗ |
| `_escape_sparql` | vfs/mount_service.py | ✓ | ✓ | ✓ | ✓ | ✗ |

The `events.py` module additionally uses only `q.replace('"', '\\"')` — a single-character escape that misses backslash, enabling breakout via `\"`.

**Exploit Scenario:**
In `events.py`, input `\" )) . ?s ?p ?o } #` produces `\\"` after escape, which SPARQL interprets as literal-backslash + string-terminator, breaking out of the string context. Practical impact is low (read-only SELECT on event IRIs).

**Remediation:**
Consolidate all escape functions into a single `sparql_escape_string()` in `sparql/client.py` handling `\`, `"`, `'`, `\n`, `\r`, `\t`. Import everywhere.

---

### F-011: User-Submitted SPARQL via `/api/sparql` (By Design)

**Severity:** Medium (member role), Info (owner role)
**OWASP Category:** A03:2021 — Injection
**Classification:** confirmed-exploitable (by design)
**Affected Files:** `backend/app/sparql/router.py`, `backend/app/sparql/client.py`

**Description:**
The SPARQL console is an intentional user-facing query interface. Defenses are sound:
- Guest role blocked entirely
- Member role restricted: `check_member_query_safety()` blocks FROM/GRAPH/SERVICE keywords (case-insensitive, comment-aware, string-literal-aware)
- All queries scoped via `scope_to_current_graph()` injecting `FROM <urn:sempkm:current>`
- Only read queries supported (triplestore query endpoint, not update)

**Residual risks:**
- No query complexity limits — expensive CARTESIAN JOINs could cause DoS
- No result size limits — large dataset exfiltration possible within the current graph
- Owners can query ALL graphs including event, inbox, and federation graphs

**Remediation:**
Add query timeout at triplestore level. Consider result size pagination. Document the intentional exposure.

---

### SPARQL Injection Classification Summary

| Classification | Count | Modules |
|---|---|---|
| **confirmed-exploitable** | 5 | `views/service.py`, `views/router.py`, `browser/apps.py`, `vfs/mount_router.py`, `sparql/router.py` (by design) |
| **likely-exploitable** | 4 | `browser/events.py`, `browser/favorites.py`, `api/ai.py`, `api/router.py` |
| **safe** | 24 | `browser/objects.py`, `browser/comments.py`, `browser/search.py`, `browser/workspace.py`, `admin/router.py`, `ontology/service.py`, `services/models.py`, `services/ops_log.py`, `services/validation.py`, `services/shapes.py`, `services/webhooks.py`, `services/icons.py`, `models/registry.py`, `events/store.py`, `events/query.py`, `inference/service.py`, `rdf_import/executor.py`, `vfs/strategies.py`, `vfs/mount_collections.py`, `sparql/mirror.py`, `sparql/query_service.py`, `sparql/migrate_queries.py`, `sparql/client.py`, `task_templates/service.py` |

**Defense analysis summary:**
- `_validate_iri()` in `browser/_helpers.py` is comprehensive for the IRI-in-angle-bracket pattern — blocks `<>"\{}\n\r\t `, requires scheme, rejects unknown schemes
- `scope_to_current_graph()` correctly limits graph access via `FROM <urn:sempkm:current>` injection with brace-depth-aware parsing
- `check_member_query_safety()` blocks FROM/GRAPH/SERVICE with case normalization and string-literal stripping — no bypass found
- Non-SPARQL injection (Jinja2 template, SQLAlchemy, command injection) — all assessed as safe

### Non-SPARQL Injection Assessment

| Vector | Status | Detail |
|---|---|---|
| **Jinja2 template injection** | Safe | `autoescape=True`, no `\|safe` filter usage, no `Markup()` calls |
| **SQLAlchemy injection** | Safe | ORM only, no `text()` with user input, no `execute(f"...")` |
| **Command injection** | Safe | `create_subprocess_exec()` with argument list, no `shell=True`, no `eval()`/`exec()` |

---

## A07: Identification and Authentication Failures

### F-012: Magic Link Tokens Not Single-Use

**Severity:** Medium
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/tokens.py`, `backend/app/auth/router.py`

**Description:**
Magic link tokens are signed with `itsdangerous.URLSafeTimedSerializer` and expire after 600 seconds (10 minutes). However, they are **not single-use** — the same token can be verified multiple times within the expiry window. The `verify_magic_link_token()` function only checks the signature and timestamp, with no server-side revocation or usage tracking.

**Exploit Scenario:**
1. User requests magic link for their email
2. Token is intercepted (email MITM, shoulder surfing, shared computer browser history)
3. Attacker uses the token within 10 minutes — creates a valid session
4. Original user also uses the token — creates another valid session
5. Both sessions coexist without detection

**Localhost Mitigation:** When SMTP is not configured, the token is returned directly in the API response and logged to the terminal. Interception risk is lower on localhost.

**Remediation:**
Track used magic link tokens in a server-side set (Redis/SQLite table with TTL matching the 600s expiry). Reject tokens that have already been consumed. On successful verification, mark the token as used.

---

### F-013: Unlimited Concurrent Sessions

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/service.py`

**Description:**
`create_session()` creates a new session token without limiting concurrent sessions per user. There is no cap on how many active sessions a user can have. Session expiry is server-side (30 days default, with sliding window renewal at 50% mark).

**Security implications:**
- A stolen session token can be used alongside legitimate sessions without detection
- No "log out everywhere" ability exposed in the UI (the `revoke_all_sessions()` method exists in the service but is not wired to any endpoint)
- `cleanup_expired_sessions()` runs only on startup, not periodically

**Exploit Scenario:**
Attacker obtains a session token. Even if the legitimate user logs out (revoking their own session), the attacker's session remains valid for up to 30 days.

**Localhost Mitigation:** Low risk for single-user instances.

**Remediation:**
- Wire `revoke_all_sessions()` to a "Log out all devices" button in Settings
- Consider capping concurrent sessions (e.g., max 5 per user)
- Run `cleanup_expired_sessions()` periodically (e.g., daily cron or background task)

---

### F-014: Session Token Entropy Assessment — Adequate

**Severity:** Info (positive finding)
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/service.py`

**Description:**
Session tokens are generated via `secrets.token_urlsafe(32)` — 32 bytes of OS-level randomness encoded as URL-safe base64, yielding ~43 characters with 256 bits of entropy. This is cryptographically strong and collision-resistant.

API tokens use `secrets.token_hex(32)` — 32 bytes as hex, yielding 64 characters with 256 bits of entropy. Stored as SHA-256 hash.

The secret key for `itsdangerous` token signing is generated via `secrets.token_urlsafe(64)` and persisted to file.

**Assessment:** All token generation uses adequate entropy sources. No findings.

---

### F-015: Cookie Security Configuration

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/router.py`, `backend/app/config.py`

**Description:**
Cookie configuration:

| Flag | Value | Assessment |
|---|---|---|
| `httponly` | `True` | ✅ Prevents JS access |
| `samesite` | `"lax"` | ✅ Prevents CSRF for POST requests |
| `secure` | `settings.cookie_secure` (default `True`) | ⚠️ See below |
| `max_age` | 30 days (2,592,000 seconds) | ℹ️ Long but acceptable with sliding window |
| `path` | Not set (defaults to `/`) | ℹ️ OK for single-app domain |
| `domain` | Not set | ✅ Scoped to exact origin |

**`cookie_secure` gap:**
The `COOKIE_SECURE=false` setting for local HTTP development is functional but creates a misconfiguration risk. If deployed to production with HTTP (no TLS), cookies would be transmitted in cleartext. The `COOKIE_SECURE` env var is not documented in the deployment guide.

**Remediation:**
Add a startup warning when `cookie_secure=False` and `app_base_url` starts with `https://`. Document `COOKIE_SECURE` in the deployment guide.

---

### F-016: API Tokens Are Unscoped — Full User Privileges

**Severity:** Medium
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/service.py`, `backend/app/auth/dependencies.py`

**Description:**
API tokens (`POST /api/auth/tokens`) are scoped only to the user — they inherit the full role permissions of the user who created them. There is no scope restriction (e.g., read-only, specific endpoints, specific models).

The `verify_api_token()` function returns the full `User` object, and `get_current_user_or_api()` treats Bearer-authenticated requests identically to session-authenticated requests.

**Exploit Scenario:**
An owner-role user creates an API token for a narrow purpose (e.g., WebDAV file sync). That token can also:
- Execute arbitrary SPARQL (including `all_graphs=true`)
- Create/delete objects
- Install/uninstall models
- Manage users (invite, etc.)
- Access admin endpoints

**Localhost Mitigation:** Lower risk when tokens don't leave the local network.

**Remediation:**
Add token scope field to `ApiToken` model (e.g., `scope: str` with values like `"read"`, `"sparql"`, `"admin"`). Enforce scope in `get_current_user_or_api()` or via a middleware that checks the token's scope against the endpoint's requirements.

---

### F-017: Rate Limiting Coverage Gaps

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/rate_limit.py`, `backend/app/auth/router.py`

**Description:**
Rate limiting is applied via `slowapi` decorators on individual endpoints:

| Endpoint | Rate Limit | Purpose |
|---|---|---|
| `POST /api/auth/magic-link` | 5/minute | Brute-force magic link requests |
| `POST /api/auth/verify` | 10/minute | Brute-force token verification |
| All other endpoints | **None** | — |

**Missing coverage:**
- `POST /api/auth/setup` — no rate limit on setup token guessing (mitigated by high entropy)
- `POST /api/auth/tokens` — no rate limit on API token creation
- `POST /api/commands` — no rate limit on batch command execution
- `POST /api/sparql` — no rate limit on SPARQL queries (DoS via expensive queries)
- `POST /api/copilot/chat` — no rate limit on LLM API calls (cost amplification)
- All `GET /browser/*` endpoints — no rate limit (information gathering)

**Exploit Scenario:**
An authenticated user sends expensive SPARQL CARTESIAN JOINs to `/api/sparql` in a tight loop, consuming triplestore CPU and memory.

**Localhost Mitigation:** Non-issue for single-user instances. The in-memory rate limiter resets on server restart.

**Remediation:**
Add rate limits to: SPARQL execution (e.g., 30/minute), copilot chat (e.g., 10/minute), API token creation (e.g., 5/minute), and batch commands (e.g., 20/minute).

---

### F-018: Credential Enumeration via Magic Link Flow

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/router.py`

**Description:**
When SMTP is configured, the magic link endpoint returns the same generic message ("If this email is registered, a login link has been sent.") for both registered and unregistered emails — good practice.

However, when SMTP is **not** configured (the common localhost case), the endpoint returns the token directly and creates a new user account on verify if the email doesn't exist. This means any email can be used to create a member account.

**Exploit Scenario (cloud without SMTP):**
If someone deploys SemPKM without SMTP configured, any network-reachable client can:
1. Request a magic link for any email — gets the token directly
2. Verify the token — auto-creates a member account
3. Access all shared data in the triplestore

**Localhost Mitigation:** When running locally without SMTP, the API must be network-reachable for this to matter.

**Remediation:**
When SMTP is not configured, limit magic link requests to emails belonging to existing users or invited users. Add a startup warning if SMTP is not configured and the instance is network-accessible.

---

### F-019: Demo Mode Grants Guest Access to All Read Endpoints

**Severity:** Info
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/dependencies.py`, `backend/app/config.py`

**Description:**
When `DEMO_MODE=true`, all `get_current_user` calls return a synthetic guest user without any authentication. The guest role restricts write access (blocked by `require_role("owner", "member")` on mutation endpoints), but all read endpoints are accessible without credentials.

**Assessment:**
This is by design for the hosted demo. The guest role correctly restricts mutations. The demo user gets a deterministic UUID (`00000000-0000-0000-0000-000000000000`) — SQL queries scoped by `user_id` return empty results for canvas, dashboards, etc. The demo mode is documented and opt-in.

**Residual risk:** If `DEMO_MODE=true` is accidentally set in production, all data becomes publicly readable.

**Remediation:**
Add a startup warning when `demo_mode=True` and `app_base_url` points to a non-localhost domain.

---

### F-020: Federation Inbox HTTP Signature Verification — Adequate but Limited

**Severity:** Info
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/federation/inbox.py`, `backend/app/federation/signatures.py`

**Description:**
The `POST /api/inbox` endpoint uses `Depends(VerifyHTTPSignature())` which verifies:
1. HTTP Signature header is present and well-formed
2. The key is fetched from the sender's WebID document
3. The signature covers the expected headers

Additional validation: the `actor` field in the JSON-LD body must match the verified `sender_webid`.

**Assessment:**
HTTP Signature verification is the standard approach for ActivityPub/LDN federation. It prevents unauthenticated POST of notifications and ensures the sender is who they claim. The verification is adequate for the federation use case.

**Note:** The inbox notification types are restricted to `{"Offer", "Announce", "Update", "Note"}` — arbitrary types are rejected.

---

## Summary — Findings by Severity

| Severity | Count | Finding IDs |
|---|---|---|
| **High** | 3 | F-006, F-007, F-008 |
| **Medium** | 5 | F-001, F-003, F-009, F-012, F-016 |
| **Low** | 5 | F-002, F-004, F-010, F-015, F-017 |
| **Info** | 4 | F-005, F-014, F-019, F-020 |
| **Low-Medium** | 1 | F-013 |
| **Low** | 1 | F-018 |

### Top Remediation Priorities

1. **F-006 + F-007 + F-008: Add `_validate_iri()` to views, apps, VFS mount** — Highest impact, blocks the three confirmed-exploitable SPARQL injection vectors
2. **F-001: Add authentication to 6 apps endpoints** — Easy fix, eliminates unauthenticated access
3. **F-009: Add `_validate_iri()` to favorites** — Prevents stored injection
4. **F-010: Consolidate escape functions** — Eliminate inconsistency across 4 modules
5. **F-012: Make magic link tokens single-use** — Standard auth hardening
6. **F-016: Add scope to API tokens** — Principle of least privilege
7. **F-003: Fix nginx CORS for cloud deployments** — Prevent header duplication
