# SemPKM Security Model

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

## Authentication

SemPKM uses **passwordless authentication** via magic link tokens:

1. User requests a magic link for their email address
2. A signed token (itsdangerous `URLSafeTimedSerializer`, 600s TTL) is sent via email (or returned directly for localhost instances without SMTP)
3. User verifies the token, which creates a session
4. Session is stored in SQLite with a random 256-bit token (`secrets.token_urlsafe(32)`)
5. Session cookie is `httpOnly`, `SameSite=Lax`, `Secure` (configurable for HTTP dev)
6. Magic link tokens are single-use (tracked in `used_magic_tokens` table)

### API Tokens

Long-lived API tokens are available for non-browser clients (WebDAV, CLI tools, extensions):

- Tokens use `secrets.token_hex(32)` — only the SHA-256 hash is stored
- Tokens support scoped permissions (e.g., `sparql:read`, `objects:write`, `commands:execute`)
- Wildcard scope (`*`) grants full user permissions
- Bearer token authentication via `Authorization: Bearer <token>` header

## Security Event Audit Trail

All security-relevant operations are logged to the `security_audit_log` SQL table:

| Event Type | Trigger |
|-----------|---------|
| `login_success` | Successful magic link verification |
| `login_failed` | Invalid/expired token or token replay attempt |
| `token_created` | New API token created |
| `token_revoked` | API token deleted |
| `session_revoked_all` | User revoked all active sessions |
| `role_changed` | User role modified (future) |
| `model_installed` | Mental Model installed (future) |
| `model_uninstalled` | Mental Model uninstalled (future) |

Each audit entry records: event type, user ID (when known), source IP, timestamp, and a JSON detail blob with event-specific data.

## Rate Limiting

Endpoints are rate-limited to prevent abuse:

| Endpoint Group | Limit |
|---------------|-------|
| Magic link request | 5/minute |
| Token verification | 10/minute |
| SPARQL queries | 60/minute |
| AI copilot chat | 20/minute |
| API token creation | 5/minute |
| Batch commands | 20/minute |

Rate limit exceeded responses return HTTP 429 with a `Retry-After` header.

## SPARQL Security

The SPARQL console (`/api/sparql`) is an intentional user-facing query interface with these defenses:

- **Guest role blocked entirely** — no SPARQL access for unauthenticated users
- **Member queries restricted** — `check_member_query_safety()` blocks `FROM`, `GRAPH`, `SERVICE` keywords (case-insensitive, comment-aware, string-literal-aware)
- **Graph scoping** — all queries automatically scoped via `scope_to_current_graph()` to `urn:sempkm:current`
- **Read-only** — only SELECT/ASK/CONSTRUCT/DESCRIBE queries; no SPARQL UPDATE
- **Query timeout** — 30-second timeout on triplestore queries (504 on timeout)

## Federation

Federation enables cross-instance knowledge sharing:

- Outbound sync uses HTTP Signatures for authentication
- Inbound inbox verifies HTTP Signatures against sender's WebID public key
- Federation is opt-in per instance (requires WebID setup)
- Sync patches contain RDF data scoped to specific named graphs

## Secret Management

- Instance secret key stored at `data/.secret-key` (auto-generated on first run)
- Used for Fernet encryption (LLM API keys, WebID private keys) and token signing
- Session cookies signed with the instance secret
- Secret key file permissions should be restricted to owner-only (`0o600`)

## App Platform Trust Model

The app platform runs user-installed Python applications as subprocesses:

- Apps communicate with the platform via Unix domain sockets
- Apps run with the same OS user as the backend process
- The SDK provides domain-allowlisted HTTP clients, but apps can bypass this
- **Current trust model:** Apps are trusted (installed by the instance owner from local disk)
- **For future marketplace:** Apps would need container-level isolation
