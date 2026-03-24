# M042: SemPKM Security Audit — Complete Findings Report

**Date:** 2026-03-23
**Scope:** SemPKM full stack — FastAPI backend, nginx/Caddy reverse proxies, Docker deployment, RDF triplestore, CDN dependency chain, federation subsystem, app platform, browser extension
**Assessment Model:** Cloud deployment with federation enabled (most exposed configuration). Localhost mitigations noted per-finding where applicable.
**Framework:** OWASP Top 10:2021
**Total Findings:** 44

---

## Executive Summary

This report documents a comprehensive security audit of SemPKM against all 10 OWASP Top 10:2021 categories. The assessment covers the FastAPI backend, nginx/Caddy reverse proxy configurations, Docker deployment files, the RDF triplestore interface, CDN dependency chain, federation sync protocol, app platform subprocess model, and the browser extension integration surface.

The audit identified **44 findings** across all 10 OWASP categories:

| Severity | Count | Finding IDs |
|----------|-------|-------------|
| **High** | 9 | F-006, F-007, F-008, F-021, F-028, F-029, F-031, F-032, F-043 |
| **Medium** | 14 | F-001, F-003, F-009, F-012, F-016, F-022, F-023, F-026, F-030, F-033, F-034, F-035, F-036, F-041 |
| **Low** | 13 | F-002, F-004, F-010, F-013, F-015, F-017, F-018, F-024, F-025, F-027, F-037, F-039, F-044 |
| **Info** | 8 | F-005, F-011, F-014, F-019, F-020, F-038, F-040, F-042 |

**Key themes:**

1. **SPARQL injection is the dominant injection vector** — 5 confirmed-exploitable modules, 4 likely-exploitable, across views, apps, VFS mounts, favorites, and events. The existing `_validate_iri()` function is comprehensive but not uniformly applied.
2. **Zero supply chain integrity** — No SRI hashes on any CDN dependency, 3 completely unpinned libraries (including DOMPurify, the XSS sanitizer), and no automated CVE scanning for either Python or JavaScript dependencies.
3. **Missing HTTP security headers** — No CSP, no X-Frame-Options, no HSTS across all reverse proxy configurations, leaving XSS exploitation unrestricted and clickjacking possible.
4. **No security event audit trail** — Login, token creation, role changes, and federation events are not logged. Incident response is impossible without forensic data.
5. **Federation SSRF** — The sync endpoint accepts arbitrary URLs from authenticated users without IP blocklist or scheme validation.

The top 10 prioritized remediation items (see dedicated section below) can be addressed in approximately 20–40 hours of engineering effort, with the three SPARQL injection fixes (F-006, F-007, F-008) and HTTP security headers (F-021) offering the highest security return per hour invested.

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
| `GET /browser/apps/right-pane-sections` | **None** | SPARQL injection vector (see F-007) + leaks object type info |
| `GET /browser/apps/views/explorer` | **None** | Leaks app view manifest entries |
| `GET /browser/apps/{app_id}/view/{view_id}` | **None** | Renders app view tab content |
| `GET /browser/apps/commands` | **None** | Leaks command palette entries from running apps |
| `GET /browser/apps/catalog` | ✅ `get_current_user` | OK |
| `GET /browser/apps/catalog/{app_id}` | ✅ `get_current_user` | OK |

**Exploit Scenario:**
An unauthenticated attacker can enumerate running apps, their page structures, and view manifests. The `right-pane-sections` endpoint additionally takes an `iri` query parameter that is used in unvalidated SPARQL (see F-007), compounding the access control gap with an injection vector.

**Remediation:**
Add `user: User = Depends(get_current_user)` to all six unprotected endpoint signatures.

---

### F-002: No Object-Level Ownership Enforcement (Flat Authorization Model)

**Severity:** Low (single-user/small-team), Medium (multi-tenant)
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `backend/app/browser/objects.py`, `backend/app/sparql/router.py`, `backend/app/views/router.py`, `backend/app/browser/events.py`

**Description:**
SemPKM uses a flat authorization model: all authenticated users share the same triplestore data. There is no per-object ownership, and no IDOR protection is needed in the current design because all objects are intentionally shared.

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

**Remediation:**
Document the shared-data model clearly. If multi-tenant support is added, implement per-graph or per-namespace data isolation with ownership checks on all CRUD endpoints.

---

### F-003: CORS Wildcard on API Endpoints via nginx

**Severity:** Medium (cloud with federation), Low (localhost)
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `frontend/nginx.conf`, `backend/app/main.py`

**Description:**
The nginx configuration adds `Access-Control-Allow-Origin: *` on all `/api/` responses. The FastAPI CORS middleware defaults to `allow_origins=["*"]` with `allow_credentials=False` when `CORS_ORIGINS` is empty (the default).

**Security interaction:**
- **Session cookies:** `SameSite=Lax` prevents cross-origin cookie inclusion for non-navigation POST requests. The `*` CORS origin does NOT allow `credentials: include` in fetch — browsers enforce this.
- **Bearer tokens:** Any website can issue `fetch()` requests with a Bearer token to the SemPKM API, and the `*` CORS policy will allow the response to be read. If an attacker obtains an API token, they can use it from any origin.

**Exploit Scenario:**
A user creates an API token. A malicious site the user visits makes `fetch('https://my-sempkm.example.com/api/sparql', {headers: {'Authorization': 'Bearer <stolen-token>'}})` — CORS wildcard allows reading the response. This is only exploitable if the attacker already has the token.

**Remediation:**
When `CORS_ORIGINS` is configured (cloud deployment), ensure nginx does NOT override with `*`. Fix nginx to not add its own CORS headers when the backend already handles it.

---

### F-004: Setup Endpoint Lacks Authentication Guard

**Severity:** Low
**OWASP Category:** A01:2021 — Broken Access Control
**Affected Files:** `backend/app/api/setup_routes.py`

**Description:**
`POST /api/setup/configure-instance` has no auth dependency. It is guarded only by a check: `if await _check_user_data_exists(request)` which returns 409 if triplestore data exists. Before any data is created (first-run), anyone who can reach the API can set the instance's deployment mode, BASE_NAMESPACE, and APP_BASE_URL.

**Exploit Scenario:**
During the narrow window between Docker startup and owner account creation, an attacker who can reach the API could configure the instance with a malicious BASE_NAMESPACE. This window is typically seconds on localhost but could be longer on cloud deployments.

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
An attacker could use the exposed ingestion key to send bogus analytics events, polluting analytics data. No data exfiltration is possible.

**Remediation:**
By design for client-side analytics. No action needed unless analytics data integrity is critical.

---

## A02: Cryptographic Failures

### F-038: Secret Key File Written Without Restrictive Permissions

**Severity:** Medium (cloud), Low (single-user Docker)
**OWASP Category:** A02:2021 — Cryptographic Failures
**Affected Files:** `backend/app/auth/tokens.py` (lines 33–39)

**Description:**
The `_get_secret_key()` function auto-generates `data/.secret-key` via `key_path.write_text(key)` with no `os.chmod()` call. The file inherits umask-default permissions (typically `0o644` — world-readable). This file is the root secret for all Fernet encryption (LLM API keys, WebID private keys) and all token signing (sessions, magic links, invitations).

The same issue applies to the setup token file at `data/.setup-token`.

**Exploit Scenario:**
In a shared hosting or cloud container environment where multiple processes or users share a filesystem:
1. The secret key file is readable by any process with the same UID or by any process if umask is permissive.
2. An attacker with read access to the container filesystem (e.g., via a different vulnerability, a sidecar container, or a log aggregation agent with volume access) reads `data/.secret-key`.
3. With the secret key, the attacker can: forge session tokens for any user, decrypt all stored LLM API keys, decrypt all stored WebID private keys, forge magic link tokens.

**Remediation:**
After writing the secret key file, restrict permissions:
```python
key_path.write_text(key)
os.chmod(key_path, 0o600)  # Owner read/write only
```
Apply the same to `data/.setup-token`. Consider also setting the file ownership to match the application user.

---

### F-039: No Key Rotation Mechanism for Fernet Encryption Keys

**Severity:** Low
**OWASP Category:** A02:2021 — Cryptographic Failures
**Affected Files:** `backend/app/services/llm.py`, `backend/app/webid/service.py`, `backend/app/auth/tokens.py`

**Description:**
The secret key is generated once and never rotated. PBKDF2 salts are hardcoded strings (`sempkm-llm-config-v1`, `sempkm-webid-keys-v1`). If the secret key is compromised, all encrypted LLM API keys and WebID private keys are immediately recoverable with no ability to rotate without manually re-encrypting all stored secrets.

Fernet supports `MultiFernet` for key rotation (decrypt with any key, encrypt with newest), but this is not implemented.

**Exploit Scenario:**
1. The secret key is leaked (see F-038 for one vector).
2. The administrator discovers the leak and generates a new key.
3. All existing encrypted data (LLM config, WebID keys) becomes undecryptable — there's no migration path.
4. The administrator must re-enter all LLM API keys and regenerate all WebID keypairs.

**Remediation:**
Implement `MultiFernet` with a key file that supports multiple versioned keys. On rotation: add new key as primary, keep old keys for decryption. Periodically re-encrypt stored secrets with the newest key and retire old keys.

---

### F-040: Cookie `secure` Flag Misconfiguration Risk

**Severity:** Info
**OWASP Category:** A02:2021 — Cryptographic Failures
**Affected Files:** `backend/app/config.py` (line 56), `backend/app/auth/router.py` (line 52)

**Description:**
`config.py` defaults `cookie_secure: bool = True`. Docker-compose files for local dev set `COOKIE_SECURE=false` for HTTP. This is correct behavior (secure cookies don't work over HTTP), but there is no runtime warning when `secure=False` is used with a non-localhost `APP_BASE_URL`, meaning a cloud deployment could accidentally run with insecure cookies.

**Exploit Scenario:**
An operator deploys to a cloud VM with HTTP (no TLS termination) and sets `COOKIE_SECURE=false` to make login work. Session cookies are transmitted in cleartext, enabling session hijacking via network sniffing.

**Remediation:**
Add a startup warning when `cookie_secure=False` and `app_base_url` starts with `https://` or points to a non-localhost domain.

---

## A03: Injection

### F-006: SPARQL Injection via `type` Query Parameter in Views

**Severity:** High
**OWASP Category:** A03:2021 — Injection
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

This becomes `?s rdf:type <x> . ?s ?p ?o } #> .` — closing the WHERE block and commenting out the rest. The `scope_to_current_graph` defense limits exposure to `urn:sempkm:current` but all data within that graph is extractable. Approximately 10–15 endpoints in views/router.py share this vector.

**Remediation:**
Add `_validate_iri(type_iri)` check in `generic_view()` and all view endpoints that accept a `type` query parameter, before passing to `build_dynamic_query()`.

---

### F-007: SPARQL Injection via `iri` Query Parameter in Apps

**Severity:** High
**OWASP Category:** A03:2021 — Injection
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

**Remediation:**
Add `_validate_iri(iri)` before SPARQL construction. Add authentication dependency. Add `scope_to_current_graph()`.

---

### F-008: SPARQL Write Injection via VFS Mount IRI Fields

**Severity:** High
**OWASP Category:** A03:2021 — Injection
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

**Remediation:**
Apply `_validate_iri()` to all IRI-typed fields in mount creation/update body.

---

### F-009: Stored SPARQL Injection via Favorites

**Severity:** Medium
**OWASP Category:** A03:2021 — Injection
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

**Remediation:**
Add `_validate_iri(object_iri)` in `toggle_favorite()` before SQL storage.

---

### F-010: Incomplete SPARQL String Escaping Across Multiple Modules

**Severity:** Low
**OWASP Category:** A03:2021 — Injection
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

## A04: Insecure Design

### F-041: App Platform Subprocesses Run Without OS-Level Isolation

**Severity:** Medium (current model: trusted local installs), High (if marketplace model added)
**OWASP Category:** A04:2021 — Insecure Design
**Affected Files:** `backend/app/apps/manager.py` (lines 204–210), `backend/sdk/sempkm_app_sdk/clients/http.py`

**Description:**
The app platform runs third-party (user-installed) Python applications as unsandboxed subprocesses via `asyncio.create_subprocess_exec()`. Apps run with the same OS user and filesystem access as the main backend process:

- No seccomp, AppArmor, namespace isolation, capability dropping, or chroot
- Apps communicate via Unix domain sockets (`/tmp/sempkm-app-{app_id}.sock`)
- The SDK provides `HttpClient` with domain enforcement (`allowed_domains` via fnmatch), but this is advisory — an app can import `httpx` directly and bypass the SDK
- An app can read the secret key file (`data/.secret-key`), access the SQLite database, read environment variables, and make arbitrary network requests

**Exploit Scenario:**
1. A user installs a seemingly benign app from a shared repository.
2. The app's `on_startup` hook reads `data/.secret-key` and `data/sempkm.db`.
3. The app exfiltrates the secret key and database contents to an external server via raw `httpx` (bypassing the SDK's domain allowlist).
4. The attacker uses the secret key to forge session tokens and decrypt all stored credentials.

**Remediation:**
For the current trust model (owner installs from local disk), document the trust boundary clearly. For any future marketplace: run apps in separate containers or namespaces with mounted UDS-only network access, no host filesystem visibility, and a dedicated signing key per app.

---

### F-042: App JWT Tokens Share Platform Secret — Cross-App Forgery Possible

**Severity:** Medium (coupled with F-041)
**OWASP Category:** A04:2021 — Insecure Design
**Affected Files:** `backend/app/apps/tokens.py`

**Description:**
All app JWT tokens are signed with the same `get_secret()` key — the platform's main secret. An app that extracts the secret key (trivial given F-041's lack of filesystem isolation) can forge valid JWT tokens for any other app, impersonating the platform itself.

**Exploit Scenario:**
1. App A reads `data/.secret-key` from the shared filesystem.
2. App A creates a JWT token with `sub: "app-B"` and `aud: "sempkm-platform"`.
3. App A uses this forged token to call platform APIs as App B, accessing App B's data and permissions.

**Remediation:**
Generate per-app signing keys derived from the platform secret plus a unique app identifier. Use HMAC(platform_secret, app_id) as the per-app key. Validate the `sub` claim matches the app presenting the token.

---

## A05: Security Misconfiguration

### F-021: Missing HTTP Security Headers Across All Reverse Proxy Configs

**Severity:** High
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `frontend/nginx.conf`, `frontend/nginx.demo.conf`, `Caddyfile.cloud`

**Description:**
None of the three reverse proxy configurations set any standard HTTP security headers:

| Header | Purpose | Status |
|--------|---------|--------|
| `Content-Security-Policy` | Prevent XSS, data injection, clickjacking | ❌ Missing |
| `X-Frame-Options` | Prevent clickjacking (legacy) | ❌ Missing |
| `X-Content-Type-Options` | Prevent MIME-sniffing attacks | ❌ Missing |
| `Strict-Transport-Security` | Enforce HTTPS connections | ❌ Missing |
| `Referrer-Policy` | Control referrer leakage | ❌ Missing |
| `Permissions-Policy` | Disable unused browser features | ❌ Missing |

Additionally, neither nginx config includes `server_tokens off`, so the nginx version is disclosed in the `Server` response header.

**Exploit Scenario:**
1. Without CSP, any successful XSS injection can load arbitrary external scripts and exfiltrate data without restriction.
2. Without `X-Frame-Options` or CSP `frame-ancestors`, the workspace UI can be embedded in an attacker's iframe for clickjacking.
3. Without `X-Content-Type-Options: nosniff`, the browser may MIME-sniff uploaded RDF content as HTML and execute embedded script.
4. Without HSTS on cloud deployments, a network attacker can perform SSL stripping.

**Remediation:**
Add a shared security headers block to all nginx/Caddy configs:
```nginx
server_tokens off;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none';" always;
```

---

### F-022: CORS Double-Header Risk — nginx and FastAPI Both Emit Access-Control-Allow-Origin

**Severity:** Medium
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `frontend/nginx.conf` (lines 74, 96, 116, 122), `backend/app/main.py` (lines 633–649)

**Description:**
CORS headers are set in two independent layers:
1. **nginx** adds `Access-Control-Allow-Origin: *` unconditionally on all `/api/` responses.
2. **FastAPI CORSMiddleware** adds its own `Access-Control-Allow-Origin` header — either `*` (default) or a specific origin (when configured).

When `CORS_ORIGINS` is set to a specific domain, the response arrives with two conflicting `Access-Control-Allow-Origin` headers. Browser behavior on duplicates is inconsistent — Chrome rejects, Firefox may accept the more permissive value.

**Exploit Scenario:**
An administrator configures `CORS_ORIGINS=https://my-app.example.com` expecting strict origin enforcement. The nginx layer silently overrides to `*`, so any website can make credentialless API requests.

**Remediation:**
Remove the `add_header Access-Control-Allow-Origin` directives from nginx `/api/` blocks. Let FastAPI CORSMiddleware handle CORS exclusively.

---

### F-023: Docker Containers Run as Root with No Security Constraints

**Severity:** Medium
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.demo.yml`

**Description:**
Both Docker containers run all processes as UID 0 (root). Neither compose file applies security constraints:

| Constraint | Status |
|-----------|--------|
| `security_opt: no-new-privileges` | ❌ Missing |
| `cap_drop: ALL` | ❌ Missing |
| `read_only: true` | ❌ Missing |
| `user:` directive | ❌ Missing |

**Exploit Scenario:**
If an attacker achieves code execution inside the API container (e.g., via SPARQL injection leading to code execution, or a dependency vulnerability), root privileges make container escape significantly easier and allow modification of mounted volumes to persist malicious code.

**Remediation:**
Add a non-root user to both Dockerfiles. Add `security_opt: no-new-privileges` and `cap_drop: ALL` to compose files.

---

### F-024: Uvicorn `--reload` in Production Dockerfile CMD

**Severity:** Low
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `backend/Dockerfile` (line 36)

**Description:**
The Dockerfile CMD includes `--reload` and `--reload-dir /app/app`. This enables a filesystem watcher appropriate for development but with operational implications in production: memory overhead, unexpected restarts on ConfigMap changes, and automatic loading of any code written to the monitored directory.

**Exploit Scenario:**
An attacker who can write files to `/app/app` (e.g., via a file upload vulnerability or writable volume mount) can deploy arbitrary Python code that the reload watcher automatically loads and executes.

**Remediation:**
Use a production-safe default CMD without `--reload`. Override in `docker-compose.yml` for development.

---

### F-025: Error Information Disclosure via `detail=str(e)` in Exception Handlers

**Severity:** Low
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `backend/app/auth/router.py`, `backend/app/workflow/router.py`, `backend/app/dashboard/router.py`, `backend/app/task_templates/router.py`

**Description:**
Six exception handlers across four routers catch exceptions and return the raw exception message to the API client via `detail=str(e)`. Additionally, there is no global `Exception` handler — unhandled exceptions fall through to Starlette's default handler, which returns detailed HTML error pages with stack traces when `--reload` is active.

**Exploit Scenario:**
An attacker submits malformed data to trigger an unhandled exception and receives a full Python stack trace including file paths, library versions, and local variable values.

**Remediation:**
Replace `detail=str(e)` with generic messages. Add a global `Exception` handler that logs the error and returns `{"detail": "Internal server error"}`.

---

### F-026: Demo Instance Uses Hardcoded Predictable SECRET_KEY

**Severity:** Medium (demo instance), Info (dev)
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `docker-compose.demo.yml` (line 40)

**Description:**
The demo compose file sets `SECRET_KEY: demo-secret-key-not-for-production`. This key is in the public repository. Anyone who knows it can forge valid session tokens for any user on instances deployed with this compose file.

**Exploit Scenario:**
An operator deploys a "demo" instance but sets `DEMO_MODE=false`. An attacker forges a session cookie using the publicly known key and gains full authenticated access.

**Remediation:**
Generate the demo SECRET_KEY at container startup if not provided. Add a startup check that refuses to start with known weak SECRET_KEY values when DEMO_MODE is not explicitly true.

---

### F-027: Obsidian Upload Endpoint Has No Request Body Size Limit

**Severity:** Low
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `frontend/nginx.conf` (lines 195–196)

**Description:**
The Obsidian vault upload endpoint is configured with `client_max_body_size 0` (no limit) and `proxy_request_buffering off`, allowing arbitrarily large uploads to stream directly to the backend.

**Exploit Scenario:**
An authenticated user uploads a multi-GB file, exhausting disk space in the container's temp directory or the volume mount — denial of service against the hosting infrastructure.

**Remediation:**
Set `client_max_body_size 500m` and add server-side size validation in the FastAPI upload handler.

---

## A06: Vulnerable and Outdated Components

### F-031: Zero Subresource Integrity (SRI) on All CDN-Loaded Dependencies

**Severity:** High
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:** `backend/app/templates/base.html`, `backend/app/templates/base_embed.html`, `backend/app/templates/browser/map_view.html`, `backend/app/templates/browser/timeline_view.html`, `backend/app/templates/browser/workspace.html`, `backend/app/templates/admin/model_detail.html`, `backend/app/templates/admin/sparql.html`, `frontend/static/js/workspace.js`, `frontend/static/js/calendar.js`, `frontend/static/js/theme.js`

**Description:**
Every CDN-loaded `<script>` and `<link>` tag across the entire codebase is missing the `integrity` attribute. There are zero `integrity=` attributes in any template or JS file. Three CDN hosts are in use: `unpkg.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`. A compromise of any single host delivers malicious JavaScript to all SemPKM users.

**Exploit Scenario:**
1. An attacker compromises an npm registry account for any CDN-loaded dependency.
2. CDN hosts immediately serve the compromised package.
3. Without `integrity` attributes, the browser executes the malicious script without hash verification.
4. Combined with absent CSP (F-021), the malicious script has unrestricted access to the DOM, session data, and API.

**Remediation:**
Generate SRI hashes for all CDN-loaded scripts and stylesheets. Add `integrity` and `crossorigin="anonymous"` attributes. For dynamically created `<script>` elements, set `script.integrity` and `script.crossOrigin` before appending. Long-term: extend the vendor pipeline to eliminate CDN dependencies in production.

---

### F-032: Three CDN Dependencies Loaded Without Any Version Pin

**Severity:** High
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:** `backend/app/templates/base.html` (lines 42, 43, 46), `backend/app/templates/base_embed.html` (lines 18, 19)

**Description:**
Three libraries are loaded from CDN URLs with no version specifier:

| Library | CDN URL | Risk |
|---------|---------|------|
| marked | `cdn.jsdelivr.net/npm/marked/lib/marked.umd.js` | Latest version auto-resolved |
| marked-highlight | `cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js` | Latest version auto-resolved |
| dompurify | `cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js` | Latest version auto-resolved |

**DOMPurify is particularly critical** — it is the HTML sanitization library that prevents XSS. An attacker who publishes a compromised DOMPurify version effectively disables XSS protection for all SemPKM instances loading from CDN.

Two additional deps use partial version pins: gridstack (`@10`) and chart.js (`@4.4`).

**Exploit Scenario:**
An attacker publishes a compromised DOMPurify version that passes through XSS payloads for specific trigger patterns. All SemPKM instances loading from CDN immediately receive the compromised version. The attacker creates a knowledge graph object with a body containing the trigger + XSS payload, achieving persistent XSS.

**Remediation:**
Pin exact versions for all three libraries. Pin gridstack and chart.js to exact patch versions. Add SRI hashes after pinning.

---

### F-033: Always-CDN Dependencies Not Covered by Vendor Pipeline

**Severity:** Medium
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:** `frontend/build.js`, `backend/app/templates/base.html`, `frontend/static/js/calendar.js`, `backend/app/templates/browser/map_view.html`, `frontend/static/js/workspace.js`, `backend/app/templates/browser/timeline_view.html`, `frontend/static/js/theme.js`

**Description:**
The vendor pipeline (`frontend/build.js`) vendors 17 libraries for production, but 7 remain always-CDN:

| Library | Production Impact |
|---------|-------------------|
| gridstack@10 | Loaded on every page with dashboard widgets |
| fullcalendar@6.1.17 | Calendar view |
| leaflet@1.9.4 | Map view |
| leaflet.markercluster@1.5.3 | Map view |
| chart.js@4.4 | SPARQL stat widgets |
| frappe-gantt@1.2.2 | Timeline view |
| highlight.js themes | Every page (CSS) |

A CDN outage breaks these views entirely. Combined with absent SRI (F-031), a CDN compromise serves malicious code to production users.

**Remediation:**
Extend the vendor pipeline to cover always-CDN dependencies, eliminating CDN dependency for production.

---

### F-034: No Automated Dependency Vulnerability Scanning

**Severity:** Medium
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:** `backend/pyproject.toml`, `frontend/package.json`, `frontend/Dockerfile`

**Description:**
No automated CVE scanning exists for either dependency tree:

| Check | Python | JavaScript |
|-------|--------|------------|
| `pip-audit` / `safety` in CI | ❌ None | N/A |
| `npm audit` in CI | N/A | ❌ None |
| Dependabot / Renovate | ❌ None | ❌ None |

The frontend Dockerfile explicitly suppresses npm audit: `npm ci --no-audit --no-fund`.

**Exploit Scenario:**
A CVE is published for `cryptography` (8 CVEs in 2024). With no scanning pipeline, the vulnerability goes unnoticed until manual discovery. If it affects TLS validation, federation sync traffic could be intercepted.

**Remediation:**
Add `pip-audit` and `npm audit` to CI. Configure GitHub Dependabot for both ecosystems.

---

## A07: Identification and Authentication Failures

### F-012: Magic Link Tokens Not Single-Use

**Severity:** Medium
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/tokens.py`, `backend/app/auth/router.py`

**Description:**
Magic link tokens are signed with `itsdangerous.URLSafeTimedSerializer` and expire after 600 seconds (10 minutes). They are not single-use — the same token can be verified multiple times within the expiry window. No server-side revocation or usage tracking exists.

**Exploit Scenario:**
1. User requests a magic link.
2. Token is intercepted (email MITM, shoulder surfing, shared computer).
3. Attacker uses the token within 10 minutes — creates a valid session.
4. Original user also uses it — both sessions coexist without detection.

**Remediation:**
Track used magic link tokens in a server-side set (Redis/SQLite table with TTL matching the 600s expiry). Reject tokens already consumed.

---

### F-013: Unlimited Concurrent Sessions

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/service.py`

**Description:**
`create_session()` creates a new session token without limiting concurrent sessions per user. No cap exists on active sessions. The `revoke_all_sessions()` method exists but is not wired to any endpoint. `cleanup_expired_sessions()` runs only on startup, not periodically.

**Exploit Scenario:**
Attacker obtains a session token. Even if the legitimate user logs out (revoking their own session), the attacker's session remains valid for up to 30 days.

**Remediation:**
Wire `revoke_all_sessions()` to a "Log out all devices" UI button. Consider capping concurrent sessions. Run cleanup periodically.

---

### F-014: Session Token Entropy Assessment — Adequate

**Severity:** Info (positive finding)
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/service.py`

**Description:**
Session tokens use `secrets.token_urlsafe(32)` — 256 bits of entropy. API tokens use `secrets.token_hex(32)` stored as SHA-256 hash. The itsdangerous secret key uses `secrets.token_urlsafe(64)` — 512 bits. All token generation uses adequate entropy sources.

---

### F-015: Cookie Security Configuration

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/router.py`, `backend/app/config.py`

**Description:**
Cookie configuration is mostly sound:

| Flag | Value | Assessment |
|---|---|---|
| `httponly` | `True` | ✅ Prevents JS access |
| `samesite` | `"lax"` | ✅ Prevents CSRF for POST |
| `secure` | `settings.cookie_secure` (default `True`) | ⚠️ See F-040 |
| `max_age` | 30 days | ℹ️ Long but acceptable with sliding window |

The gap is that `COOKIE_SECURE=false` for local HTTP development creates a misconfiguration risk if used in production.

**Remediation:**
Add a startup warning when `cookie_secure=False` and `app_base_url` is non-localhost. Document `COOKIE_SECURE` in deployment guide.

---

### F-016: API Tokens Are Unscoped — Full User Privileges

**Severity:** Medium
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/service.py`, `backend/app/auth/dependencies.py`

**Description:**
API tokens inherit the full role permissions of the creating user. No scope restriction exists. An owner-role user's token created for WebDAV sync can also: execute arbitrary SPARQL, manage users, install models, access admin endpoints.

**Exploit Scenario:**
A leaked API token with owner privileges grants full administrative access to the instance.

**Remediation:**
Add a scope field to the `ApiToken` model (e.g., `"read"`, `"sparql"`, `"admin"`). Enforce scope in the auth dependency chain.

---

### F-017: Rate Limiting Coverage Gaps

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/rate_limit.py`, `backend/app/auth/router.py`

**Description:**
Rate limiting covers only magic-link (5/min) and verify (10/min). Missing coverage:

| Endpoint | Rate Limit | Gap |
|----------|-----------|-----|
| `POST /api/auth/setup` | None | Setup token guessing |
| `POST /api/sparql` | None | DoS via expensive queries |
| `POST /api/copilot/chat` | None | LLM cost amplification |
| `POST /api/commands` | None | Batch command abuse |

**Remediation:**
Add rate limits to SPARQL (30/min), copilot (10/min), API token creation (5/min), batch commands (20/min).

---

### F-018: Credential Enumeration via Magic Link Flow

**Severity:** Low
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/router.py`

**Description:**
When SMTP is configured, the endpoint returns a generic message for both registered and unregistered emails — good practice. When SMTP is not configured (common localhost case), the token is returned directly and any email can create a member account.

**Exploit Scenario:**
On a cloud deployment without SMTP, any network-reachable client can request a magic link for any email, get the token directly, verify it, and gain member access to all shared data.

**Remediation:**
When SMTP is not configured, limit magic link requests to existing or invited users.

---

### F-019: Demo Mode Grants Guest Access to All Read Endpoints

**Severity:** Info
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/auth/dependencies.py`, `backend/app/config.py`

**Description:**
When `DEMO_MODE=true`, all `get_current_user` calls return a synthetic guest user without authentication. The guest role correctly restricts mutations. By design for the hosted demo.

**Residual risk:** If `DEMO_MODE=true` is accidentally set in production, all data becomes publicly readable.

**Remediation:**
Add a startup warning when `demo_mode=True` and `app_base_url` is non-localhost.

---

### F-020: Federation Inbox HTTP Signature Verification — Adequate but Limited

**Severity:** Info
**OWASP Category:** A07:2021 — Identification and Authentication Failures
**Affected Files:** `backend/app/federation/inbox.py`, `backend/app/federation/signatures.py`

**Description:**
The `POST /api/inbox` endpoint uses HTTP Signature verification: header present and well-formed, key fetched from sender's WebID, signature covers expected headers, `actor` field matches verified `sender_webid`. Inbox notification types restricted to `{"Offer", "Announce", "Update", "Note"}`.

**Assessment:** Adequate for the federation use case. No finding.

---

## A08: Software and Data Integrity Failures

### F-035: ZIP Extraction Without Zip-Bomb or Size-Limit Protection

**Severity:** Medium
**OWASP Category:** A08:2021 — Software and Data Integrity Failures
**Affected Files:** `backend/app/obsidian/router.py` (lines 125–126), `backend/app/notion/router.py` (lines 152–153), `frontend/nginx.conf` (lines 195–196)

**Description:**
Both the Obsidian and Notion import endpoints extract user-uploaded ZIP files without checking total uncompressed size or file count:
```python
with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(extract_path)
```
No validation: no total uncompressed size check, no file count check, no compression ratio check. Path traversal is mitigated by Python 3.12+'s CVE-2024-0450 fix.

**Exploit Scenario:**
An authenticated user uploads a zip bomb (10MB compressed → 10GB uncompressed), exhausting disk space and making the API container unresponsive.

**Remediation:**
Inspect ZIP contents before extraction: check total uncompressed size (e.g., 2GB limit) and file count (e.g., 50,000 limit). Set `client_max_body_size` on the upload endpoint.

---

### F-036: Federation Patches Are Not Cryptographically Signed

**Severity:** Medium
**OWASP Category:** A08:2021 — Software and Data Integrity Failures
**Affected Files:** `backend/app/federation/router.py` (lines 380–425), `backend/app/federation/service.py` (lines 600–680)

**Description:**
Federation sync exports and imports RDF patches over HTTPS without content-level integrity verification. No digital signature, HMAC, or content hash is attached to the patch. The HTTP Signature on the request authenticates the requester, not the response content.

**Exploit Scenario:**
A man-in-the-middle (compromised CDN, TLS-intercepting proxy, compromised CA) modifies the patch JSON in transit, injecting additional RDF triples. The importing instance applies the modified patch without detecting tampering.

**Remediation:**
Add SHA-256 content hash to patch exports. Verify hash on import before applying. Long-term: implement Ed25519 signing of patch content.

---

### F-037: Federation Sync Applies Remote RDF Content Without Semantic Validation

**Severity:** Low
**OWASP Category:** A08:2021 — Software and Data Integrity Failures
**Affected Files:** `backend/app/federation/service.py` (lines 670–680)

**Description:**
Remote patches are applied without content filtering. No checks for ontology injection (`owl:Class`, SHACL shapes), metadata pollution (`sempkm:*` predicates), scope violation, or volume limits.

**Exploit Scenario:**
A compromised federated instance sends a patch containing SHACL shapes with embedded `sh:sparql` constraints. When the local instance runs SHACL validation, the injected SPARQL executes against the local triplestore.

**Remediation:**
Filter incoming triples to expected namespaces. Reject system-managed predicates. Limit triples per sync. Log namespace distribution for audit.

---

## A09: Security Logging and Monitoring Failures

### F-028: Magic Link Authentication Tokens Logged in Plaintext

**Severity:** High
**OWASP Category:** A09:2021 — Security Logging and Monitoring Failures
**Affected Files:** `backend/app/auth/router.py` (lines 155, 163)

**Description:**
The magic link endpoint logs the full authentication token at INFO level in two code paths (SMTP failure fallback and no-SMTP-configured). These tokens appear in Docker container stdout, log aggregation systems, and terminal windows.

**Exploit Scenario:**
A log aggregation pipeline ships container logs to a centralized system. A support engineer with log access finds magic link tokens and authenticates as any user. Alternatively, a log storage breach exposes all historical tokens.

**Remediation:**
Remove the `logger.info` token log when SMTP is not configured (token is already in the API response). When SMTP fails, log only a masked version: `token[:8]...`. Consider structured logging with a `sensitive: true` field.

---

### F-029: No Security Event Audit Trail

**Severity:** High
**OWASP Category:** A09:2021 — Security Logging and Monitoring Failures
**Affected Files:** `backend/app/auth/router.py`, `backend/app/main.py`, `backend/app/services/models.py`, `backend/app/federation/router.py`

**Description:**
No dedicated security event logging exists for any security-relevant operation:

| Security Event | Logged? |
|----------------|---------|
| Successful login | ❌ |
| Failed login attempt | ❌ |
| Session creation/revocation | ❌ |
| API token creation/revocation | ❌ |
| Role change | ❌ |
| User invitation | ❌ |
| Admin model install/uninstall | ❌ |
| Federation sync events | ❌ |
| Configuration changes | ❌ |

**Exploit Scenario:**
An attacker compromises an account, escalates to owner, creates API tokens, modifies federation settings, and installs a malicious model. The legitimate owner discovers the breach days later but cannot determine what happened — no forensic timeline is possible.

**Remediation:**
Create a `SecurityAuditLog` SQL table. Add audit logging for all security-relevant operations. Expose an admin UI for reviewing security events. Add structured logging with correlation IDs.

---

### F-030: Failed Authentication Attempts Not Logged or Monitored

**Severity:** Medium
**OWASP Category:** A09:2021 — Security Logging and Monitoring Failures
**Affected Files:** `backend/app/auth/router.py` (lines 182–186)

**Description:**
Invalid token verification returns HTTP 400 without logging. API token authentication failures return 401 silently. Rate limit events are not logged. No cumulative tracking across rate limit windows.

**Exploit Scenario:**
An attacker scripts 9 verify attempts per minute (under the 10/min limit). Over 24 hours: 12,960 attempts. The operator has zero visibility into this activity.

**Remediation:**
Log every failed verify attempt at WARNING level with source IP. Log rate limit triggers. Add cumulative failed-attempt tracking per IP with escalating rate limits. Log failed API token attempts with token prefix.

---

## A10: Server-Side Request Forgery

### F-043: Federation Sync Endpoint Allows Arbitrary Outbound HTTP Requests (SSRF)

**Severity:** High
**OWASP Category:** A10:2021 — Server-Side Request Forgery
**Affected Files:** `backend/app/federation/router.py` (line 230), `backend/app/federation/service.py` (line 658)

**Description:**
`POST /federation/{graph_id}/sync` accepts `remote_instance_url` from the JSON request body. This URL is passed directly to `httpx.AsyncClient.get()` with no validation: no IP blocklist, no scheme restriction, no internal network guard. The IndieAuth service has proper SSRF guards (`ipaddress.is_loopback` check) but federation does not use them.

**Exploit Scenario:**
1. An authenticated user sends a sync request with `remote_instance_url: "http://169.254.169.254/latest/meta-data/"` (AWS metadata service).
2. The backend fetches the URL and returns the response content (or includes it in the error message).
3. The attacker extracts cloud instance credentials, IAM role tokens, or other sensitive metadata.
4. Alternatively: `remote_instance_url: "http://localhost:8000/api/auth/..."` probes internal services.

**Remediation:**
Apply the same SSRF guards used in IndieAuth: resolve the hostname, check against `ipaddress.is_loopback`, `is_private`, `is_link_local`, `is_reserved`. Restrict scheme to `https://` only. Add an optional allowlist of trusted federation peers.

---

### F-044: Webhook Dispatch Sends POST to Owner-Configured URLs Without IP Validation

**Severity:** Low
**OWASP Category:** A10:2021 — Server-Side Request Forgery
**Affected Files:** `backend/app/services/webhooks.py`

**Description:**
Webhook `target_url` is stored by an owner and the `dispatch()` method sends HTTP POST to this URL with no IP blocklist check. Owner-only configuration mitigates the risk (the owner is attacking their own instance), but in a multi-user scenario an owner could configure webhooks to probe internal networks.

**Exploit Scenario:**
An owner configures a webhook with `target_url: "http://10.0.0.5:6379/"` to probe internal Redis/database services on the Docker network.

**Remediation:**
Add IP blocklist validation (same as IndieAuth) before dispatching webhooks. Log all webhook dispatch attempts with target URL and response status.

---

## Backend Hardening Assessment

This section provides a cross-cutting analysis of backend security posture, synthesizing findings from the OWASP categories above.

### Secret Management

The secret key (`data/.secret-key`) is the root of all cryptographic operations — Fernet encryption, token signing, app JWT issuance. Two weaknesses:

- **File permissions (F-038):** Written with umask-default permissions (typically world-readable). Any process with filesystem access can read it.
- **No rotation (F-039):** Generated once, never rotated. Compromise of this single key exposes all encrypted data with no migration path.

The PBKDF2 key derivation for Fernet uses hardcoded salts (`sempkm-llm-config-v1`, `sempkm-webid-keys-v1`), which is acceptable given the salts serve only to domain-separate derived keys.

### Session Lifecycle

- **Magic links not single-use (F-012):** Replay window of 10 minutes.
- **Unlimited concurrent sessions (F-013):** No cap, no "log out everywhere" UI.
- **Cookie config (F-015):** Mostly sound; `SameSite=Lax` prevents CSRF. The `COOKIE_SECURE` flag is correctly defaulted but documentation risk exists for cloud deployments.

### API Token Management

- **Unscoped tokens (F-016):** Full user privileges regardless of intended use.
- **No rate limit on creation (F-017):** An authenticated attacker can create unlimited tokens.
- **Token storage:** SHA-256 hashed — good. But no token expiry mechanism — tokens are valid until manually revoked.

### Debug/Shell Endpoint Exposure

No debug endpoints were found exposed in production configurations. The admin panel (`/admin/*`) is properly gated behind `require_role("owner")`. The SPARQL console is intentionally exposed to members with safety checks.

### Federation Authentication

- **Inbox (F-020):** HTTP Signature verification is adequate.
- **Sync SSRF (F-043):** Arbitrary outbound requests without IP validation — the most critical federation finding.
- **Patch integrity (F-036):** No content signing — MITM can tamper with sync data.
- **Content validation (F-037):** No semantic filtering — remote patches can inject ontology or system triples.

### File Upload Handling

- **No upload size limit (F-027):** nginx `client_max_body_size 0` on Obsidian upload.
- **No zip-bomb protection (F-035):** Both Obsidian and Notion import extract ZIPs without size validation.
- Path traversal is mitigated by Python 3.12+ (CVE-2024-0450 fix).

---

## Infrastructure Security Assessment

### nginx Configuration

- **Missing security headers (F-021):** No CSP, X-Frame-Options, HSTS, X-Content-Type-Options, Referrer-Policy, or Permissions-Policy across all three configs (nginx.conf, nginx.demo.conf, Caddyfile.cloud). Server version disclosed.
- **CORS double-header (F-022):** nginx and FastAPI both emit `Access-Control-Allow-Origin`, creating conflicting headers that can silently override intended origin restrictions.
- **Upload endpoint (F-027):** No body size limit on Obsidian import.

### Docker Security

- **Root containers (F-023):** Both containers run as UID 0. No `cap_drop`, `no-new-privileges`, or `read_only` constraints. Writable volume mounts allow code persistence.
- **Reload in production (F-024):** Filesystem watcher in Dockerfile CMD enables auto-loading of written code.

### Deployment Hardening

- **Hardcoded demo secret (F-026):** Publicly known SECRET_KEY in demo compose file.
- **No CVE scanning (F-034):** Neither Python nor JavaScript dependencies are automatically audited.
- **Error disclosure (F-025):** Raw exception messages returned to clients; no global exception handler.

---

## SPARQL Injection Classification Summary

Systematic triage of all 33 backend modules using f-string SPARQL construction. See the main findings (F-006 through F-011) for detailed exploit scenarios.

### Sanitization Functions

| Function | Location | `\` | `"` | `\n` | `\r` | `\t` |
|---|---|---|---|---|---|---|
| `_validate_iri()` | `browser/_helpers.py` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `_sparql_escape` | search.py, workspace.py | ✓ | ✓ | ✓ | ✗ | ✗ |
| `_sparql_escape_str` | api/router.py, api/ai.py | ✓ | ✓ | ✓ | ✗ | ✗ |
| `_escape_sparql` | vfs/mount_service.py | ✓ | ✓ | ✓ | ✓ | ✗ |

### Module Classification Table

| # | Module | Classification | f-string Count | Input Source | Sanitization |
|---|--------|---------------|----------------|-------------|-------------|
| 1 | `sparql/router.py` | **confirmed-exploitable** | ~10 | HTTP direct (user SPARQL) | `check_member_query_safety` + `scope_to_current_graph` |
| 2 | `views/service.py` | **confirmed-exploitable** | ~101 | HTTP indirect (`type` param) | None on `type_iri` |
| 3 | `views/router.py` | **confirmed-exploitable** | ~31 | HTTP direct (`type` param) | `_validate_iri` only on calendar move |
| 4 | `browser/objects.py` | **safe** | ~25 | HTTP direct (path param) | `_validate_iri()` on all entry points |
| 5 | `browser/search.py` | **safe** | ~3 | HTTP direct (`type`, `q` params) | `_validate_iri()` on `type`; `_sparql_escape()` on `q` |
| 6 | `browser/comments.py` | **safe** | ~16 | HTTP direct (path param) | `_validate_iri()` on all entry points |
| 7 | `browser/apps.py` | **confirmed-exploitable** | ~20 | HTTP direct (`iri` param) | None |
| 8 | `browser/events.py` | **likely-exploitable** | ~5 | HTTP direct (`q` param) | Partial: `replace('"', '\\"')` only |
| 9 | `browser/workspace.py` | **safe** | ~15 | HTTP direct (path params, tags) | `_validate_iri()` + `_sparql_escape()` |
| 10 | `browser/favorites.py` | **likely-exploitable** | ~2 | HTTP indirect (stored `object_iri`) | None on storage or retrieval |
| 11 | `admin/router.py` | **safe** | ~57 | HTTP direct (`model_id` path) | Owner-only; path params URL-safe |
| 12 | `ontology/service.py` | **safe** | ~95 | Internal IRI | N/A |
| 13 | `services/models.py` | **safe** | ~61 | Internal IRI | N/A |
| 14 | `services/ops_log.py` | **safe** | ~60 | Internal IRI | N/A |
| 15 | `services/validation.py` | **safe** | ~12 | Internal IRI | N/A |
| 16 | `services/shapes.py` | **safe** | ~4 | Internal IRI | N/A |
| 17 | `services/webhooks.py` | **safe** | ~12 | Internal IRI | N/A |
| 18 | `services/icons.py` | **safe** | ~1 | Internal IRI | N/A |
| 19 | `models/registry.py` | **safe** | ~19 | Internal IRI | N/A |
| 20 | `events/store.py` | **safe** | ~12 | Internal IRI | N/A |
| 21 | `events/query.py` | **safe** | ~13 | Internal IRI | N/A |
| 22 | `inference/service.py` | **safe** | ~15 | Internal IRI | N/A |
| 23 | `rdf_import/executor.py` | **safe** | ~6 | Internal IRI | N/A |
| 24 | `vfs/strategies.py` | **safe** | ~21 | Internal IRI | N/A |
| 25 | `vfs/mount_router.py` | **confirmed-exploitable** | ~41 | HTTP direct (JSON body) | `_escape_sparql` for strings only |
| 26 | `vfs/mount_collections.py` | **safe** | ~19 | Internal IRI | N/A |
| 27 | `sparql/mirror.py` | **safe** | ~21 | Internal IRI | N/A |
| 28 | `sparql/query_service.py` | **safe** | ~148 | Internal IRI (UUIDs) | N/A |
| 29 | `sparql/migrate_queries.py` | **safe** | ~25 | Internal IRI | N/A |
| 30 | `api/ai.py` | **likely-exploitable** | ~32 | HTTP direct (`body.url`) | `_sparql_escape_str` |
| 31 | `api/router.py` | **likely-exploitable** | ~5 | HTTP direct (`body.url`) | `_sparql_escape_str` |
| 32 | `task_templates/service.py` | **safe** | ~12 | Internal IRI | N/A |
| 33 | `sparql/client.py` | **safe** | ~5 | Internal (constants) | N/A |

### Classification Summary

| Classification | Count | Modules |
|---|---|---|
| **confirmed-exploitable** | 5 | `views/service.py`, `views/router.py`, `browser/apps.py`, `vfs/mount_router.py`, `sparql/router.py` (by design) |
| **likely-exploitable** | 4 | `browser/events.py`, `browser/favorites.py`, `api/ai.py`, `api/router.py` |
| **safe** | 24 | All others (see table above) |

### Defense Analysis

- **`_validate_iri()`:** Comprehensive for the IRI-in-angle-bracket pattern — blocks `<>"\{}\n\r\t `, requires scheme, rejects unknown schemes. The problem is inconsistent application, not inadequate implementation.
- **`scope_to_current_graph()`:** Correctly limits graph access via `FROM <urn:sempkm:current>` injection with brace-depth-aware parsing.
- **`check_member_query_safety()`:** Blocks FROM/GRAPH/SERVICE with case normalization and string-literal stripping — no bypass found.
- **Non-SPARQL injection (Jinja2, SQLAlchemy, command injection):** All assessed as safe.

---

## Prioritized Top 10 Findings

Ranked by severity × exploitability × blast radius. Cloud deployment baseline.

| Rank | ID | Title | Severity | OWASP | Effort | Rationale |
|------|----|-------|----------|-------|--------|-----------|
| 1 | F-006 | SPARQL injection via views `type` param | High | A03 | 2–4h | Broadest attack surface (~15 endpoints), confirmed exploitable, full graph read access |
| 2 | F-007 | SPARQL injection via apps `iri` param | High | A03 | 1–2h | No auth + no graph scoping = unauthenticated data extraction |
| 3 | F-008 | SPARQL write injection via VFS mount | High | A03 | 2–3h | Write injection — can modify knowledge graph data |
| 4 | F-021 | Zero HTTP security headers | High | A05 | 1–2h | Low effort, high defensive value; CSP blocks XSS exploitation chains |
| 5 | F-043 | Federation SSRF — arbitrary outbound HTTP | High | A10 | 2–4h | Cloud metadata extraction, internal service probing |
| 6 | F-031 | Zero SRI on all CDN dependencies | High | A06 | 4–8h | Supply chain integrity; CDN compromise = arbitrary code execution |
| 7 | F-032 | Unpinned CDN deps (incl. DOMPurify) | High | A06 | 1–2h | DOMPurify compromise disables XSS protection entirely |
| 8 | F-028 | Magic link tokens logged in plaintext | High | A09 | 30min | Credential leakage in logs; trivial fix |
| 9 | F-029 | No security event audit trail | High | A09 | 4–8h | Enables incident response; currently zero forensic capability |
| 10 | F-001 | Missing auth on 6 browser app endpoints | Medium | A01 | 30min | Easy fix, eliminates unauthenticated access to app metadata |

**Total estimated effort for Top 10:** 19–35 hours

---

## Appendix: CDN Dependency Inventory

Complete inventory of all CDN-loaded dependencies across templates and JavaScript files.

### Always-CDN — Loaded in Both Production and Development

| Library | Version Pin | SRI | CDN Host | Loaded From |
|---------|-----------|-----|----------|-------------|
| gridstack | `@10` (major only) | ❌ None | cdn.jsdelivr.net | `base.html` |
| fullcalendar | `@6.1.17` (exact) | ❌ None | cdn.jsdelivr.net | `calendar.js` (lazy) |
| leaflet | `@1.9.4` (exact) | ❌ None | unpkg.com | `map_view.html` (lazy) |
| leaflet.markercluster | `@1.5.3` (exact) | ❌ None | unpkg.com | `map_view.html` (lazy) |
| chart.js | `@4.4` (minor only) | ❌ None | cdn.jsdelivr.net | `workspace.js` (lazy) |
| chart.js | `@4.4` (minor only) | ❌ None | cdn.jsdelivr.net | `model_detail.html` |
| frappe-gantt | `@1.2.2` (exact) | ❌ None | cdn.jsdelivr.net | `timeline_view.html` (lazy) |
| highlight.js themes | `11.11.1` (exact) | ❌ None | cdnjs.cloudflare.com | `theme.js` (runtime swap) |

### Dev-Only CDN — Vendored in Production via `frontend/build.js`

| Library | Version Pin | SRI | CDN Host | Loaded From |
|---------|-----------|-----|----------|-------------|
| htmx.org | `@2.0.4` (exact) | ❌ None | unpkg.com | `base.html` |
| split.js | `@1.6.5` (exact) | ❌ None | unpkg.com | `base.html` |
| ninja-keys | `@1.2.2` (exact) | ❌ None | unpkg.com | `base.html` |
| cytoscape | `@3.33.1` (exact) | ❌ None | unpkg.com | `base.html` |
| layout-base | `@2.0.1` (exact) | ❌ None | unpkg.com | `base.html` |
| cose-base | `@2.2.0` (exact) | ❌ None | unpkg.com | `base.html` |
| cytoscape-fcose | `@2.2.0` (exact) | ❌ None | unpkg.com | `base.html` |
| dagre | `@0.8.5` (exact) | ❌ None | unpkg.com | `base.html` |
| cytoscape-dagre | `@2.5.0` (exact) | ❌ None | unpkg.com | `base.html` |
| marked | **unpinned** | ❌ None | cdn.jsdelivr.net | `base.html`, `base_embed.html` |
| marked-highlight | **unpinned** | ❌ None | cdn.jsdelivr.net | `base.html` |
| highlight.js | `@11.11.1` (exact) | ❌ None | cdnjs.cloudflare.com | `base.html` |
| dompurify | **unpinned** | ❌ None | cdn.jsdelivr.net | `base.html`, `base_embed.html` |
| lucide | `@0.575.0` (exact) | ❌ None | unpkg.com | `base.html`, `base_embed.html`, `errors/403.html` |
| driver.js | `@1.4.0` (exact) | ❌ None | cdn.jsdelivr.net | `base.html` |
| dockview-core | `@4.11.0` (exact) | ❌ None | cdn.jsdelivr.net | `workspace.html` |
| @zazuko/yasgui | `@4.5.0` (exact) | ❌ None | unpkg.com | `admin/sparql.html` |

### CDN Host Summary

| CDN Host | Dependencies | Risk |
|----------|-------------|------|
| unpkg.com | 12 | npmjs.com mirror — compromise of npm account serves malicious code |
| cdn.jsdelivr.net | 10 | Multi-CDN; mirrors npm and GitHub — same npm compromise vector |
| cdnjs.cloudflare.com | 2 | Cloudflare-hosted; separate from npm but still an external dependency |

---

*Report generated as part of M042: Security Audit. All findings assessed against cloud deployment with federation enabled as the baseline threat model. Localhost mitigations are noted where applicable but are not considered sufficient for cloud deployments.*
