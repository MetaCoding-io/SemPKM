# SemPKM Security Model

Comprehensive security reference covering authorization, authentication, injection defenses, infrastructure hardening, and the complete disposition of the M042 security audit.

---

## Authorization Architecture

SemPKM uses a **shared-data, role-based authorization model**. All authenticated users share the same RDF triplestore data. SQL-backed resources are user-scoped.

### Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **owner** | Instance administrator | Full access: all data, user management, model install/uninstall, instance configuration |
| **member** | Regular user | Read/write objects and views, use copilot, run SPARQL (read-only, scoped to current graph) |
| **guest** | Demo/anonymous visitor | Read-only access to objects and views. No writes, no SPARQL, no admin |

### Data Ownership Model

SemPKM intentionally uses a **collaborative shared-data model** — all authenticated users share the same knowledge graph. This is by design for small-team and personal knowledge management.

| Resource Type | Storage | Ownership | Access Model |
|---------------|---------|-----------|--------------|
| **RDF Objects** (notes, contacts, tasks, etc.) | Triplestore (`urn:sempkm:current` graph) | Shared — no per-object ownership | All authenticated users read/write |
| **RDF Edges** (relationships between objects) | Triplestore (`urn:sempkm:current` graph) | Shared | All authenticated users read/write |
| **Canvas sessions** | SQLite | User-scoped (`user_id` column) | Only the creating user can access |
| **Dashboards** | SQLite | User-scoped (`user_id` column) | Only the creating user can access |
| **Workflows** | SQLite | User-scoped (`user_id` column) | Only the creating user can access |
| **Saved SPARQL queries** | Triplestore (user namespace) | User-scoped (`owner_id` in RDF) | Only the creating user can access |
| **API tokens** | SQLite | User-scoped (`user_id` column) | Only the creating user can manage |
| **AI conversations** | SQLite | User-scoped (`user_id` column) | Only the creating user can access |
| **User settings** | SQLite | User-scoped (`user_id` column) | Only the creating user can access |

### Implications

1. **No IDOR protection on RDF objects.** Any authenticated member can read/write any object in the shared graph. This is intentional for collaborative knowledge management.
2. **SQL resources are properly isolated.** Canvas, dashboards, workflows, queries, and tokens are filtered by `user_id` in all queries.
3. **Multi-tenant deployment is not supported.** If you need per-user data isolation on RDF objects, you would need per-user named graphs with access control — this is not currently implemented.

---

## Authentication

SemPKM uses **passwordless authentication** via magic link tokens:

1. User requests a magic link for their email address
2. A signed token (itsdangerous `URLSafeTimedSerializer`, 600s TTL) is sent via email (or returned directly for localhost instances without SMTP)
3. User verifies the token, which creates a session
4. Session is stored in SQLite with a random 256-bit token (`secrets.token_urlsafe(32)`)
5. Session cookie is `httpOnly`, `SameSite=Lax`, `Secure` (configurable for HTTP dev)
6. Magic link tokens are **single-use** — consumed tokens are tracked via SHA-256 hash in the `used_magic_tokens` table and rejected on replay

### Magic Link Hardening

- **Single-use enforcement:** After successful verification, the token's SHA-256 hash is stored in `UsedMagicToken`. Replay attempts within the 10-minute window return 401.
- **No-SMTP restriction:** When SMTP is not configured, magic link requests are restricted to existing users or users with pending invitations. Unknown emails receive a generic response with no information leakage.
- **Token logging:** Magic link tokens are truncated to the first 8 characters in log output to prevent credential leakage via log aggregation systems.

### API Tokens

Long-lived API tokens are available for non-browser clients (WebDAV, CLI tools, extensions):

- Tokens use `secrets.token_hex(32)` — only the SHA-256 hash is stored
- Tokens support **fine-grained scoped permissions**: `sparql:read`, `objects:write`, `commands:execute`, `copilot:use`
- Wildcard scope (`*`) grants full user permissions
- `scope_required()` dependency factory enforces scope at the endpoint level — SPARQL requires `sparql:read`, commands require `commands:execute`, copilot requires `copilot:use`
- Bearer token authentication via `Authorization: Bearer <token>` header

### Session Management

- **Maximum 10 concurrent sessions per user.** When the cap is reached, the oldest session is evicted.
- **Revoke-all endpoint:** `POST /api/auth/sessions/revoke-all` invalidates all active sessions for the current user.
- **Daily cleanup:** An async background task runs daily to remove expired sessions from the database.

---

## Security Event Audit Trail

All security-relevant operations are logged to the `security_audit_log` SQL table:

| Event Type | Trigger |
|-----------|---------|
| `login_success` | Successful magic link verification |
| `login_failed` | Invalid/expired token or token replay attempt |
| `token_created` | New API token created |
| `token_revoked` | API token deleted |
| `session_revoked_all` | User revoked all active sessions |
| `role_changed` | User role modified |
| `model_installed` | Mental Model installed via admin panel |
| `model_uninstalled` | Mental Model uninstalled via admin panel |

Each audit entry records: event type, user ID (when known), source IP, timestamp, and a JSON detail blob with event-specific data.

The audit logging uses a fire-and-forget pattern — audit failures never block the parent operation. The helper catches all exceptions internally and logs to stderr on failure.

---

## Rate Limiting

Endpoints are rate-limited via slowapi decorators to prevent abuse:

| Endpoint Group | Limit |
|---------------|-------|
| Magic link request | 5/minute |
| Token verification | 10/minute |
| SPARQL queries | 60/minute |
| AI copilot chat | 20/minute |
| API token creation | 5/minute |
| Batch commands | 20/minute |

Rate limit exceeded responses return HTTP 429 with a `Retry-After` header set via a custom handler (slowapi's built-in header injection is incompatible with Pydantic-model-returning endpoints). Rate limit triggers are logged at WARNING level with source IP.

---

## SPARQL Security

The SPARQL console (`/api/sparql`) is an intentional user-facing query interface with these defenses:

- **Guest role blocked entirely** — no SPARQL access for unauthenticated users
- **Member queries restricted** — `check_member_query_safety()` blocks `FROM`, `GRAPH`, `SERVICE` keywords (case-insensitive, comment-aware, string-literal-aware)
- **Graph scoping** — all queries automatically scoped via `scope_to_current_graph()` to `urn:sempkm:current`
- **Read-only** — only SELECT/ASK/CONSTRUCT/DESCRIBE queries; no SPARQL UPDATE
- **Query timeout** — 30-second timeout on triplestore queries (504 on timeout)
- **Scope enforcement** — API tokens require `sparql:read` scope

### SPARQL Injection Prevention

All SPARQL construction uses the centralized `backend/app/sparql/builder.py` module:

| Function | Purpose |
|----------|---------|
| `safe_iri()` | IRI validation via rdflib `URIRef.n3()` with pre-validation regex — blocks `<>"\{}\n\r\t` and rejects unknown schemes |
| `safe_literal()` | Safe literal construction for SPARQL string values |
| `sparql_escape_string()` | Escapes `\`, `"`, `'`, `\n`, `\r`, `\t` for SPARQL string contexts |
| `values_clause()` | Safe VALUES block construction from IRI lists |
| `triple_pattern()` | Safe triple pattern construction |

**Defense-in-depth:** IRI validation happens at the HTTP router boundary (returning 400 with WARNING log) AND in the service layer via `safe_iri()`. All 17 modules across the codebase were migrated from 9 scattered local escape functions to this single authoritative implementation. Zero local escape functions remain.

Verification: `rg '\bfetch\(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch' | grep -v vendor.js` returns zero results, confirming no unprotected API call paths.

---

## SSRF Protection

Outbound HTTP requests are validated against internal network access via `validate_outbound_url()` in `backend/app/security/ssrf.py`:

### Validation Steps

1. **URL parsing** — Rejects malformed URLs and non-http(s) schemes
2. **Hostname blocklist** — Blocks `localhost`, `0.0.0.0`, `::1`, and common loopback aliases
3. **DNS resolution** — Resolves the hostname to IP addresses
4. **IP category checking** — Rejects resolved IPs that are loopback, link-local, multicast, private, or reserved (checked in that order for specific error messages)

### Protected Code Paths

| Code Path | File | Protection |
|-----------|------|-----------|
| Federation sync (outbound GET) | `backend/app/federation/service.py` | `validate_outbound_url()` before `httpx.get()` |
| Federation inbox POST | `backend/app/federation/service.py` | `validate_outbound_url()` before `httpx.post()` |
| Federation inbox discovery | `backend/app/federation/service.py` | `validate_outbound_url()` before profile fetch |
| Webhook dispatch | `backend/app/services/webhooks.py` | `validate_outbound_url()` before `httpx.post()` |

SSRF blocks are logged at WARNING level with the rejection reason and blocked URL. Federation sync returns HTTP 400 for SSRF-blocked URLs.

**Known limitation:** DNS rebinding attacks could return a safe IP during validation and a private IP during the actual HTTP request. Mitigation would require pinning the resolved IP for the connection, which httpx does not support natively. Documented as acceptable risk for the current threat model.

---

## Federation Integrity

Federation enables cross-instance knowledge sharing with content integrity and namespace filtering:

### Content Hash Verification

- **Export:** SHA-256 hash of `patch_text` is computed and included in the `PatchExportResponse` as `content_hash`
- **Import:** When `content_hash` is present, the importing instance verifies the hash matches the received content. Mismatches are rejected with an ERROR-level log.
- **Backward compatibility:** Hashless patches from older instances are accepted with a WARNING-level log (per D372 — never reject hashless patches to maintain federation interoperability)

### Namespace Filtering

`filter_federation_triples()` in `backend/app/federation/namespace_filter.py` validates incoming RDF triples on both inserts and deletes:

| Filter | Action |
|--------|--------|
| `urn:sempkm:*` namespace (except `urn:sempkm:shared:*`) | **Rejected** — prevents system namespace pollution |
| `owl:*` class assertions | **Rejected** — prevents ontology injection |
| `sh:*` (SHACL) class assertions | **Rejected** — prevents SHACL shape injection (blocks embedded `sh:sparql` execution) |
| `rdf:type` assertions for 9 OWL/SHACL class IRIs | **Rejected** — prevents type-level ontology manipulation |

Filtered triples are logged at WARNING level with a count of rejected triples per sync operation.

### Authentication

- Outbound sync uses HTTP Signatures for authentication
- Inbound inbox verifies HTTP Signatures against sender's WebID public key
- Federation is opt-in per instance (requires WebID setup)

---

## ZIP Upload Protection

User-uploaded ZIP files (Obsidian vaults, Notion exports) are validated before extraction via `validate_zip_contents()` in `backend/app/security/zip_validator.py`:

| Check | Default Limit | Purpose |
|-------|--------------|---------|
| Total uncompressed size | 2,048 MB (2 GB) | Prevents disk exhaustion from zip bombs |
| File count | 50,000 | Prevents inode exhaustion |
| Per-entry compression ratio | 100:1 | Detects zip bomb signatures |

Validation inspects the ZIP central directory via `infolist()` without extracting any files. Both the Obsidian and Notion importer routers call `validate_zip_contents()` before `extractall()`, catching `ValueError` and returning a styled 400 error page.

Additionally, the Obsidian upload endpoint has a 500 MB request body limit enforced by nginx (`client_max_body_size 500m`).

Compression ratios exceeding 50:1 (but below the 100:1 rejection threshold) are logged at WARNING level for monitoring.

---

## Docker Hardening

All Docker containers run with security constraints:

### Container User

The backend Dockerfile creates a `sempkm` system user (UID 1000) and runs all processes as this non-root user via the `USER sempkm` directive. The `/app/data` directory is owned by this user for runtime data persistence.

### Security Constraints

Applied to every `api` and `frontend` service across all 6 compose files:

| Constraint | Value | Purpose |
|-----------|-------|---------|
| `security_opt` | `no-new-privileges:true` | Prevents privilege escalation inside container |
| `cap_drop` | `ALL` | Drops all Linux capabilities |

### Production vs Development

- **Production CMD:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` — no `--reload`, no filesystem watcher
- **Development override:** `docker-compose.yml` specifies a `command:` override that restores `--reload --reload-dir /app/app` for hot-reloading during development

---

## Weak Key Rejection

On startup, the backend checks `SECRET_KEY` against a set of known weak values:

```
changeme, secret, password, admin, demo-secret-key-not-for-production,
test-secret-key, dev-secret-key, ...
```

If the secret key matches any weak value and `DEMO_MODE` is not `True`, the server logs an ERROR and exits with `SystemExit(1)`. Demo and E2E test configurations explicitly use known keys but set `DEMO_MODE=True` to bypass the check.

---

## Cloud Security Headers

The Caddyfile for cloud deployment (`Caddyfile.cloud`) includes:

### HSTS (HTTP Strict Transport Security)

```
Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
```

2-year max-age with `includeSubDomains` and HSTS preload list eligibility.

### Content Security Policy

The CSP directive restricts script and style sources to `'self'` and `'unsafe-inline'` only — stale CDN domains (`unpkg.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`) have been removed from the cloud CSP. Local development nginx configs retain CDN domains in CSP for development-time CDN loading.

### Additional Headers (All Proxy Configs)

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `server_tokens` | `off` (nginx) |

### CORS

CORS is handled exclusively by FastAPI's `CORSMiddleware` — all proxy-layer CORS headers have been removed from nginx configs to prevent double-header conflicts. A dedicated `_WellKnownCORSMiddleware` overrides CORS for the `/.well-known/sempkm` browser extension discovery endpoint.

---

## App Platform Trust Model

The app platform runs user-installed Python applications as subprocesses:

- Apps communicate with the platform via Unix domain sockets
- Apps run with the same OS user as the backend process (UID 1000 in Docker)
- The SDK provides domain-allowlisted HTTP clients, but apps can bypass this via direct imports
- **Current trust model:** Apps are trusted (installed by the instance owner from local disk)
- **For future marketplace:** Apps would need container-level isolation

### Per-App JWT Key Isolation

App JWT tokens are signed with **per-app derived keys** using HMAC-SHA256:

```python
app_key = HMAC-SHA256(platform_secret_key, app_id)
```

This means:
- Each app gets a unique signing key deterministically derived from the platform secret and the app's ID
- A compromised app token **cannot** forge tokens for other apps — the signing key differs per app
- No additional key storage is needed — keys are derived on demand
- Platform-level token validation uses the same derivation to verify tokens

Implementation: `get_app_secret(app_id)` in `backend/app/apps/tokens.py`.

---

## Secret Management

- Instance secret key stored at `data/.secret-key` (auto-generated on first run)
- Used for Fernet encryption (LLM API keys, WebID private keys) and token signing
- Session cookies signed with the instance secret
- Secret key file permissions restricted to owner-only (`0o600`)
- Setup token file (`data/.setup-token`) also restricted to `0o600`

---

## Startup Warnings

The backend logs WARNING-level messages for potentially dangerous configurations:

| Condition | Warning |
|-----------|---------|
| `DEMO_MODE=true` with non-localhost `APP_BASE_URL` | Demo mode exposes all data as read-only to unauthenticated users |
| `COOKIE_SECURE=false` with non-localhost `APP_BASE_URL` | Session cookies transmitted in cleartext |
| `COOKIE_SECURE=false` with HTTPS `APP_BASE_URL` | Mismatch between cookie security and transport security |

---

## Dependency Scanning

SemPKM does not currently have a CI pipeline. Dependency vulnerability scanning should be run manually and integrated into any future CI/CD setup.

### Python Dependencies

```bash
# Install pip-audit (one-time)
pip install pip-audit

# Run audit against installed packages
cd backend
pip-audit
```

`pip-audit` checks installed Python packages against the OSV (Open Source Vulnerabilities) database and reports known CVEs with severity and fix versions.

### JavaScript Dependencies

```bash
# Run npm audit against frontend dependencies
cd frontend
npm audit
```

`npm audit` checks the `node_modules` tree against the npm advisory database. Note: the frontend Dockerfile uses `npm ci --no-audit` to suppress audit during builds — run the audit separately.

### Recommended: GitHub Dependabot

For automated scanning, add `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
```

This creates automated pull requests when vulnerabilities are found in either dependency tree.

---

## M042 Security Audit — Finding Disposition

Complete disposition of all 44 findings from the M042 security audit (conducted 2026-03-23). Findings are addressed across three milestones: M043 (injection, auth, access control), M044 (frontend code quality), and M045 (infrastructure hardening).

| ID | Severity | OWASP | Description | Status | Resolution |
|----|----------|-------|-------------|--------|------------|
| F-001 | Medium | A01 | Missing auth on 6 browser app endpoints | **Fixed (M043/S02)** | Added `Depends(get_current_user)` to all 6 endpoints |
| F-002 | Low | A01 | No object-level ownership (flat authz model) | **By Design** | Documented — shared-data model is intentional for collaborative PKM |
| F-003 | Medium | A01 | CORS wildcard on API endpoints via nginx | **Fixed (M043/S02)** | Removed nginx CORS headers; FastAPI CORSMiddleware is single source of truth |
| F-004 | Low | A01 | Setup endpoint lacks auth guard | **Fixed (M043/S02)** | Added setup_mode check before allowing namespace configuration |
| F-005 | Info | A01 | Monitoring config exposes PostHog API key | **By Design** | PostHog project API key is write-only ingestion key; client-side exposure is expected |
| F-006 | High | A03 | SPARQL injection via views `type` param | **Fixed (M043/S01)** | All view endpoints validate `type_iri` via `safe_iri()` at router boundary |
| F-007 | High | A03 | SPARQL injection via apps `iri` param | **Fixed (M043/S01+S02)** | `_validate_iri()` added + auth dependency added (also fixes F-001) |
| F-008 | High | A03 | SPARQL write injection via VFS mount IRI fields | **Fixed (M043/S01)** | All IRI fields validated via `safe_iri()` before SPARQL construction |
| F-009 | Medium | A03 | Stored SPARQL injection via favorites | **Fixed (M043/S01)** | `_validate_iri()` applied on favorite storage |
| F-010 | Low | A03 | Incomplete SPARQL string escaping | **Fixed (M043/S01)** | All 9 local escape functions consolidated into `sparql_escape_string()` |
| F-011 | Info | A03 | User-submitted SPARQL via `/api/sparql` | **By Design** | Intentional query interface with graph scoping, safety checks, and scope enforcement |
| F-012 | Medium | A07 | Magic link tokens not single-use | **Fixed (M043/S03)** | SHA-256 hash tracking in `used_magic_tokens` table; replay returns 401 |
| F-013 | Low | A07 | Unlimited concurrent sessions | **Fixed (M043/S03)** | 10-session cap with oldest eviction; revoke-all endpoint; daily cleanup |
| F-014 | Info | A07 | Session token entropy — adequate | **No Action** | Positive finding — 256-bit entropy is sufficient |
| F-015 | Low | A07 | Cookie security configuration | **Fixed (M043/S04)** | Startup warning when `cookie_secure=False` on non-localhost |
| F-016 | Medium | A07 | API tokens unscoped — full user privileges | **Fixed (M043/S03)** | Fine-grained scope field; `scope_required()` enforced on SPARQL, commands, copilot |
| F-017 | Low | A07 | Rate limiting coverage gaps | **Fixed (M043/S04)** | Added limits to SPARQL (60/min), copilot (20/min), token creation (5/min), commands (20/min) |
| F-018 | Low | A07 | Credential enumeration via magic link flow | **Fixed (M043/S03)** | No-SMTP requests restricted to existing/invited users |
| F-019 | Info | A07 | Demo mode grants guest read access | **By Design** | Intentional for hosted demo; startup warning added for non-localhost |
| F-020 | Info | A07 | Federation inbox HTTP signature verification | **No Action** | Positive finding — verification is adequate |
| F-021 | High | A05 | Missing HTTP security headers | **Fixed (M043/S02)** | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy added to all proxy configs |
| F-022 | Medium | A05 | CORS double-header (nginx + FastAPI) | **Fixed (M043/S02)** | Removed all nginx CORS headers; FastAPI CORSMiddleware handles exclusively |
| F-023 | Medium | A05 | Docker containers run as root | **Fixed (M045/S02)** | Non-root UID 1000, `no-new-privileges`, `cap_drop: ALL` across all compose files |
| F-024 | Low | A05 | Uvicorn `--reload` in production CMD | **Fixed (M045/S02)** | Removed from Dockerfile CMD; dev compose restores via command override |
| F-025 | Low | A05 | Error info disclosure via `detail=str(e)` | **Fixed (M043/S04)** | Global exception handler returns generic 500; traceback logged server-side only |
| F-026 | Medium | A05 | Demo instance hardcoded predictable SECRET_KEY | **Fixed (M045/S02)** | Startup guard rejects known weak keys when `DEMO_MODE=False` |
| F-027 | Low | A05 | Obsidian upload no body size limit | **Fixed (M043/S02)** | `client_max_body_size 500m` on upload endpoint |
| F-028 | High | A09 | Magic link tokens logged in plaintext | **Fixed (M043/S03)** | Token truncated to first 8 characters in log output |
| F-029 | High | A09 | No security event audit trail | **Fixed (M043/S04 + M045/S01)** | `SecurityAuditLog` table with `log_security_event()` for 8 event types including model install/uninstall |
| F-030 | Medium | A09 | Failed auth attempts not logged | **Fixed (M043/S04)** | Failed verification logged at WARNING with source IP; rate limit triggers logged |
| F-031 | High | A06 | Zero SRI on CDN dependencies | **Open** | Requires SRI hash generation for all CDN-loaded scripts; tracked for future work |
| F-032 | High | A06 | Three CDN deps loaded without version pin | **Open** | marked, marked-highlight, DOMPurify need exact version pins + SRI hashes |
| F-033 | Medium | A06 | Always-CDN deps not covered by vendor pipeline | **Open** | 7 libraries remain CDN-only in production; vendor pipeline extension tracked |
| F-034 | Medium | A06 | No automated dependency vulnerability scanning | **Documented** | Manual `pip-audit` and `npm audit` commands documented; Dependabot config provided |
| F-035 | Medium | A08 | ZIP extraction without zip-bomb protection | **Fixed (M045/S02)** | `validate_zip_contents()` checks size (2GB), count (50k), ratio (100:1) before extraction |
| F-036 | Medium | A08 | Federation patches not cryptographically signed | **Fixed (M045/S01)** | SHA-256 content hash on exports; verification on imports |
| F-037 | Low | A08 | Federation sync applies remote RDF without semantic validation | **Fixed (M045/S01)** | Namespace filtering rejects `urn:sempkm:*`, OWL, SHACL class injections |
| F-038 | Medium | A02 | Secret key file written without restrictive permissions | **Fixed (M043/S03)** | `os.chmod(0o600)` applied to `data/.secret-key` and `data/.setup-token` |
| F-039 | Low | A02 | No key rotation mechanism for Fernet keys | **Open** | MultiFernet rotation not implemented; documented as future enhancement |
| F-040 | Info | A02 | Cookie secure flag misconfiguration risk | **Fixed (M043/S04)** | Startup warning when `cookie_secure=False` on non-localhost |
| F-041 | Medium | A04 | App platform subprocesses without OS-level isolation | **By Design** | Current trust model: owner-installed local apps. Container isolation needed for future marketplace |
| F-042 | Medium | A04 | App JWT tokens share platform secret | **Fixed (M045/S02)** | Per-app keys via HMAC-SHA256(platform_key, app_id); cross-app forgery prevented |
| F-043 | High | A10 | Federation SSRF — arbitrary outbound HTTP | **Fixed (M045/S01)** | `validate_outbound_url()` on all 4 outbound HTTP paths; DNS resolution + IP category checking |
| F-044 | Low | A10 | Webhook dispatch to owner-configured URLs without IP validation | **Fixed (M045/S01)** | `validate_outbound_url()` applied before webhook dispatch |

### Disposition Summary

| Status | Count | Finding IDs |
|--------|-------|-------------|
| **Fixed** | 33 | F-001, F-003, F-004, F-006–F-010, F-012, F-013, F-015–F-018, F-021–F-030, F-035–F-038, F-040, F-042–F-044 |
| **By Design / Documented** | 5 | F-002, F-005, F-011, F-019, F-041 |
| **No Action (Positive)** | 2 | F-014, F-020 |
| **Open** | 4 | F-031, F-032, F-033, F-039 |

The 4 open findings (F-031, F-032, F-033, F-039) are all in the supply chain integrity category (SRI hashes, version pinning, vendor pipeline coverage) and Fernet key rotation. These require CDN dependency management infrastructure and are tracked as future work.
