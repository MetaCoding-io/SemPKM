# S02: Security Findings — Configuration, Infrastructure & Supply Chain

**Milestone:** M042 — Security Audit & Hardening
**OWASP Categories:** A05 (Security Misconfiguration), A06 (Vulnerable and Outdated Components), A08 (Software and Data Integrity Failures), A09 (Security Logging and Monitoring Failures)
**Scope:** SemPKM nginx/Caddy configs, Docker build & compose files, CDN dependency chain, federation data integrity, logging/monitoring posture
**Assessment Model:** Cloud deployment with federation enabled (most exposed); localhost mitigations noted where applicable

---

## A05: Security Misconfiguration

### F-021: Missing HTTP Security Headers Across All Reverse Proxy Configs

**Severity:** High
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `frontend/nginx.conf`, `frontend/nginx.demo.conf`, `Caddyfile.cloud`

**Description:**
None of the three reverse proxy configurations set any standard HTTP security headers. The following headers are completely absent from all configs:

| Header | Purpose | Status |
|--------|---------|--------|
| `Content-Security-Policy` | Prevent XSS, data injection, clickjacking | ❌ Missing |
| `X-Frame-Options` | Prevent clickjacking (legacy) | ❌ Missing |
| `X-Content-Type-Options` | Prevent MIME-sniffing attacks | ❌ Missing |
| `Strict-Transport-Security` | Enforce HTTPS connections | ❌ Missing |
| `Referrer-Policy` | Control referrer leakage | ❌ Missing |
| `Permissions-Policy` | Disable unused browser features | ❌ Missing |

Additionally, neither nginx config includes `server_tokens off`, so the nginx version is disclosed in the `Server` response header (e.g., `Server: nginx/1.27.4`). The Caddyfile.cloud does not set these headers either, though Caddy suppresses its own version by default.

**Exploit Scenario:**
1. Without CSP, any successful XSS injection (see S01 injection findings) can load arbitrary external scripts, exfiltrate data via fetch, and execute without restriction.
2. Without `X-Frame-Options` or CSP `frame-ancestors`, the workspace UI can be embedded in an attacker's iframe for clickjacking — tricking a logged-in user into performing actions (creating objects, running SPARQL) by overlaying invisible UI elements.
3. Without `X-Content-Type-Options: nosniff`, the browser may MIME-sniff uploaded RDF content (Turtle files containing HTML fragments) as HTML and execute embedded script.
4. Without HSTS on cloud deployments, a network attacker can perform SSL stripping to intercept the initial HTTP request before the HTTPS redirect.
5. The disclosed nginx version lets attackers target known CVEs for that specific release.

**Localhost Mitigation:** Low risk for single-user localhost — no external attacker can reach the UI. Clickjacking and MIME-sniffing remain possible from malicious websites the user visits.

**Remediation:**
Add a shared `include` file or `map` block to both nginx configs with:
```nginx
server_tokens off;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
# CSP requires careful tuning for CDN script sources and inline event handlers
add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none';" always;
```
For Caddyfile.cloud, add equivalent `header` directives plus `Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"` (Caddy handles TLS, so HSTS is safe to enable).

---

### F-022: CORS Double-Header Risk — nginx and FastAPI Both Emit Access-Control-Allow-Origin

**Severity:** Medium
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `frontend/nginx.conf` (lines 74, 96, 116, 122), `backend/app/main.py` (lines 633–649)

**Description:**
CORS headers are set in two independent layers that are unaware of each other:

1. **nginx** adds `Access-Control-Allow-Origin: *` unconditionally on all `/api/` and `/.well-known/sempkm` responses (lines 74, 96, 116, 122 of `frontend/nginx.conf`).
2. **FastAPI CORSMiddleware** (lines 633–649 of `backend/app/main.py`) adds its own `Access-Control-Allow-Origin` header — either `*` (default when `CORS_ORIGINS` is empty) or a specific origin (when configured).

When `CORS_ORIGINS` is set to a specific domain (e.g., for cloud deployment), the backend emits `Access-Control-Allow-Origin: https://sempkm.example.com`, but nginx *also* appends `Access-Control-Allow-Origin: *`. The response arrives at the browser with two conflicting headers. Browser behavior on duplicate CORS headers is inconsistent — Chrome rejects the response, Firefox may accept the more permissive value.

**Exploit Scenario:**
An administrator configures `CORS_ORIGINS=https://my-app.example.com` expecting strict origin enforcement. The nginx layer silently overrides this to allow `*`, so any website can make credentialless API requests. The administrator believes the API is origin-restricted but it is not.

**Localhost Mitigation:** CORS wildcard is intentional for localhost + browser extension use. The double-header issue is a misconfiguration problem that only manifests when a specific origin is configured.

**Remediation:**
Remove the `add_header Access-Control-Allow-Origin` directives from `frontend/nginx.conf` `/api/` and `/.well-known/` blocks. Let the FastAPI CORSMiddleware handle CORS exclusively. The nginx CORS preflight handler (`if ($request_method = OPTIONS) { return 204; }`) should also be removed or conditioned on a variable, since FastAPI handles OPTIONS responses.

---

### F-023: Docker Containers Run as Root with No Security Constraints

**Severity:** Medium
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.demo.yml`

**Description:**
Both Docker containers run all processes as UID 0 (root):

- `backend/Dockerfile`: No `USER` directive. The uvicorn process runs as root inside the container.
- `frontend/Dockerfile`: No `USER` directive. nginx runs as root (though nginx itself drops to `nginx` user for workers after binding port 80).

Neither `docker-compose.yml` nor `docker-compose.demo.yml` applies any runtime security constraints:

| Constraint | `docker-compose.yml` | `docker-compose.demo.yml` |
|-----------|---------------------|--------------------------|
| `security_opt: no-new-privileges` | ❌ Missing | ❌ Missing |
| `cap_drop: ALL` | ❌ Missing | ❌ Missing |
| `read_only: true` | ❌ Missing | ❌ Missing |
| `user:` directive | ❌ Missing | ❌ Missing |

**Exploit Scenario:**
If an attacker achieves code execution inside the API container (e.g., via SPARQL injection leading to server-side code execution, or a dependency vulnerability), they have root privileges. This makes container escape significantly easier — the attacker can mount host filesystems, modify cgroup settings, or exploit kernel vulnerabilities that require root.

**Localhost Mitigation:** Container escape from a locally-running Docker container is lower risk than cloud, but root-in-container still allows modification of mounted volumes (e.g., `./backend/app:/app/app` is writable) which could persist malicious code changes to the host filesystem.

**Remediation:**
In `backend/Dockerfile`:
```dockerfile
RUN adduser --system --no-create-home appuser
USER appuser
```
In `frontend/Dockerfile`, use the `nginxinc/nginx-unprivileged` base image or add a non-root user.

In both compose files, add:
```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
```

---

### F-024: Uvicorn `--reload` in Production Dockerfile CMD

**Severity:** Low
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `backend/Dockerfile` (line 36)

**Description:**
The Dockerfile CMD is:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]
```

The `--reload` flag enables a filesystem watcher (watchfiles) that monitors `/app/app` for changes and restarts the server automatically. This is appropriate for development but has operational implications:

1. **Memory overhead:** The file watcher maintains an inotify watch on every file under `/app/app`, consuming additional memory.
2. **Unexpected restarts:** In cloud deployments where volume mounts may change (ConfigMap updates, sidecar writes), the server restarts unexpectedly.
3. **Debug mode behavior:** When `--reload` is active, Starlette's default error handler returns detailed HTML stack traces for unhandled exceptions (though the custom `auth_exception_handler` overrides this for `HTTPException`).

The `docker-compose.yml` volume mount `./backend/app:/app/app` is what makes `--reload` useful in development — the Dockerfile CMD shouldn't assume this mount exists.

**Exploit Scenario:**
An attacker who can write files to the container's `/app/app` directory (e.g., via a file upload vulnerability or writable volume mount) can deploy arbitrary Python code that the reload watcher will automatically load and execute.

**Localhost Mitigation:** This is the intended dev behavior — hot-reload is desirable when editing code locally.

**Remediation:**
Use a production-safe default CMD without `--reload`:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Override in `docker-compose.yml` for development:
```yaml
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]
```

---

### F-025: Error Information Disclosure via `detail=str(e)` in Exception Handlers

**Severity:** Low
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:**
- `backend/app/auth/router.py` (line 119)
- `backend/app/workflow/router.py` (lines 257, 293)
- `backend/app/dashboard/router.py` (lines 488, 526)
- `backend/app/task_templates/router.py` (line 168)

**Description:**
Six exception handlers across four routers catch exceptions and return the raw exception message to the API client via `detail=str(e)`:

| File | Line | Endpoint | Exception Type |
|------|------|----------|----------------|
| `auth/router.py` | 119 | `POST /api/auth/setup` | `ValueError` |
| `workflow/router.py` | 257 | `POST /api/workflows` | `ValueError` |
| `workflow/router.py` | 293 | `PUT /api/workflows/{id}` | `ValueError` |
| `dashboard/router.py` | 488 | `POST /api/dashboards` | `ValueError` |
| `dashboard/router.py` | 526 | `PUT /api/dashboards/{id}` | `ValueError` |
| `task_templates/router.py` | 168 | `GET /api/task-templates/{id}/render` | `KeyError` |

The `str(e)` for `ValueError` typically contains validation messages (relatively safe), but `KeyError` exceptions may reveal internal data structure keys and dictionary contents. More importantly, if these catch blocks are ever broadened to catch `Exception` (a common maintenance error), internal stack context leaks to the client.

Additionally, there is no global `Exception` handler in `main.py` — only `HTTPException` and `RateLimitExceeded` have custom handlers (lines 572, 626). Unhandled exceptions fall through to Starlette's default handler, which returns detailed HTML error pages with stack traces when `--reload` is active.

**Exploit Scenario:**
1. An attacker submits malformed workflow/dashboard JSON to `POST /api/workflows` and receives the internal `ValueError` message, which may reveal expected data structure, field names, or validation logic.
2. An attacker triggers an unhandled exception (e.g., via a type confusion in request body) and receives a full Python stack trace including file paths, library versions, and local variable values.

**Remediation:**
1. Replace `detail=str(e)` with generic user-facing messages: `detail="Invalid request data"`.
2. Add a global `Exception` handler to `main.py`:
```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s", request.method, request.url.path, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

---

### F-026: Demo Instance Uses Hardcoded Predictable SECRET_KEY

**Severity:** Medium (demo instance), Info (dev)
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `docker-compose.demo.yml` (line 40)

**Description:**
The demo compose file sets:
```yaml
SECRET_KEY: demo-secret-key-not-for-production
```

This key is used by the auth system to sign session tokens (JWT). Anyone who knows this value (it's in the public repository) can forge valid session tokens for any user on the demo instance.

The demo instance also sets `DEMO_MODE: "true"` which bypasses authentication entirely, making session forging redundant in the current configuration. However, if `DEMO_MODE` is accidentally left `false` while deploying with the demo compose file, the hardcoded key becomes the only authentication secret.

**Exploit Scenario:**
1. Operator deploys a "demo" instance but sets `DEMO_MODE=false` (e.g., for a private preview).
2. Attacker forges a session cookie using the publicly known `demo-secret-key-not-for-production`.
3. Attacker has full authenticated access as any user.

**Localhost Mitigation:** The demo compose file is specifically labeled "not for production." On localhost, the main `docker-compose.yml` uses `SECRET_KEY: ${SECRET_KEY:-}` which falls back to an empty string — the auth system should reject empty keys but this should be verified separately.

**Remediation:**
1. Generate the demo SECRET_KEY at container startup if not provided: `SECRET_KEY: ${SECRET_KEY:-$(openssl rand -hex 32)}`.
2. Add a startup check in `main.py` that refuses to start if `SECRET_KEY` is a known weak value (empty string, `demo-secret-key-not-for-production`, etc.) and `DEMO_MODE` is not explicitly `true`.

---

### F-027: Obsidian Upload Endpoint Has No Request Body Size Limit

**Severity:** Low
**OWASP Category:** A05:2021 — Security Misconfiguration
**Affected Files:** `frontend/nginx.conf` (lines 195–196)

**Description:**
The Obsidian vault upload endpoint is configured with:
```nginx
location /browser/import/upload {
    client_max_body_size 0;
    proxy_request_buffering off;
    ...
}
```

`client_max_body_size 0` disables nginx's body size limit entirely. Combined with `proxy_request_buffering off`, this means arbitrarily large uploads are streamed directly to the FastAPI backend without any size gate. The endpoint requires authentication (session cookie), but an authenticated user can upload multi-gigabyte files that consume server disk and memory.

**Exploit Scenario:**
An authenticated user (or attacker with a stolen session) uploads a multi-GB file, exhausting disk space in the container's temp directory or the volume mount. This is a denial-of-service vector against the hosting infrastructure.

**Localhost Mitigation:** Self-inflicted DoS only — the user is uploading to their own machine.

**Remediation:**
Set a reasonable `client_max_body_size` (e.g., `500m` for large Obsidian vaults) and add server-side size validation in the FastAPI upload handler before writing to disk.

---

## A09: Security Logging and Monitoring Failures

### F-028: Magic Link Authentication Tokens Logged in Plaintext

**Severity:** High
**OWASP Category:** A09:2021 — Security Logging and Monitoring Failures
**Affected Files:** `backend/app/auth/router.py` (lines 155, 163)

**Description:**
The magic link request endpoint logs the full authentication token in plaintext at INFO level:

- Line 155: `logger.info("Magic link token for %s: %s", body.email, token)` — triggered when SMTP delivery fails and falls back to console output.
- Line 163: `logger.info("Magic link token for %s: %s", body.email, token)` — triggered when SMTP is not configured (the common localhost case).

These tokens are single-use bearer credentials that grant full session access. They appear in:
- Docker container stdout (`docker logs sempkm-api-1`)
- Any log aggregation system (ELK, CloudWatch, Datadog) that collects container stdout
- The terminal window running `docker compose up`

**Exploit Scenario:**
1. An operator configures a log aggregation pipeline that ships container logs to a centralized system.
2. A support engineer with log access (but not intended to have SemPKM access) searches logs and finds magic link tokens.
3. The engineer uses a token before it expires to authenticate as any user who requested a login.
4. Alternatively, a log storage breach exposes all historical magic link tokens.

**Localhost Mitigation:** On localhost without SMTP, the token *must* be communicated to the user somehow (it's returned in the API response and displayed in the browser UI). The log output is redundant with the API response. Even on localhost, the log entry persists the token in shell history and Docker logs longer than necessary.

**Remediation:**
1. When SMTP is not configured, remove the `logger.info` call — the token is already returned in the API response.
2. When SMTP fails, log only a masked version: `logger.warning("Magic link fallback for %s (token: %s...)", body.email, token[:8])`.
3. Consider structured logging with a `sensitive: true` field that log aggregators can filter.

---

### F-029: No Security Event Audit Trail

**Severity:** High
**OWASP Category:** A09:2021 — Security Logging and Monitoring Failures
**Affected Files:** `backend/app/auth/router.py`, `backend/app/main.py`, `backend/app/services/models.py`, `backend/app/federation/router.py`

**Description:**
The application has no dedicated security event logging for any of the following operations:

| Security Event | Logged? | Impact |
|----------------|---------|--------|
| Successful login | ❌ No | Cannot detect compromised account usage |
| Failed login attempt | ❌ No | Cannot detect brute-force attacks (see F-030) |
| Session creation/revocation | ❌ No | Cannot audit active sessions |
| API token creation | ❌ No | Cannot detect unauthorized token generation |
| API token revocation | ❌ No | Cannot verify cleanup after compromise |
| Role change (member→owner) | ❌ No | Cannot detect privilege escalation |
| User invitation | ❌ No | Cannot audit membership changes |
| Admin model install/uninstall | ❌ No | Cannot detect ontology tampering |
| Federation sync events | ❌ No | Cannot audit incoming data |
| Configuration changes | ❌ No | Cannot detect settings manipulation |

The RDF event store tracks data mutations (object creates, updates, edge changes) but these are data-level events, not security events. There is no correlation ID system linking a request across nginx → FastAPI → triplestore.

**Exploit Scenario:**
1. An attacker compromises a member account and escalates to owner role.
2. The attacker creates API tokens, modifies federation settings, and installs a malicious model.
3. The legitimate owner discovers the breach days later but cannot determine: when the escalation happened, what tokens were created, what data was accessed, or what federation changes were made.
4. Incident response is limited to "something happened" — no forensic timeline is possible.

**Localhost Mitigation:** Single-user instances have a smaller attack surface, but the absence of login logging means even the owner cannot verify whether their instance was accessed while unattended.

**Remediation:**
1. Create a `SecurityAuditLog` SQL table with columns: `timestamp`, `event_type`, `user_id`, `ip_address`, `user_agent`, `details_json`, `severity`.
2. Add audit logging middleware or explicit log calls for all security-relevant operations.
3. Expose an admin UI for reviewing security events with filtering by event type, user, and time range.
4. Add a structured log format with correlation IDs (request ID propagated from nginx `$request_id` via header to FastAPI).

---

### F-030: Failed Authentication Attempts Not Logged or Monitored

**Severity:** Medium
**OWASP Category:** A09:2021 — Security Logging and Monitoring Failures
**Affected Files:** `backend/app/auth/router.py` (lines 182–186)

**Description:**
The magic link verify endpoint (`POST /api/auth/verify`) handles invalid tokens by returning HTTP 400 without any logging:

```python
email = verify_magic_link_token(body.token)
if email is None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired token",
    )
```

Similarly, API token authentication failures (invalid Bearer tokens) return 401 silently through the `get_current_user` dependency chain — no logging of the failed attempt, the source IP, or the attempted token value (masked).

The rate limiter (`5/minute` on magic-link, `10/minute` on verify) provides basic brute-force protection, but:
- Rate limit events are not logged (no alert when limits are hit)
- There is no cumulative tracking across rate limit windows (an attacker doing 9 attempts/minute stays under the verify limit indefinitely)
- Failed API token attempts have no rate limiting at all

**Exploit Scenario:**
1. An attacker scripts 9 verify attempts per minute (under the 10/min limit) to brute-force magic link tokens.
2. Over 24 hours, this is 12,960 attempts — potentially sufficient for short tokens if the token space is small.
3. The instance owner has no visibility into this activity — no alerts, no logs, no dashboards.

**Assessment:**
Magic link tokens are 32-byte hex (256-bit entropy), so brute-force is computationally infeasible. The real risk is not brute-force success but the *invisibility* of the attack — the operator cannot detect reconnaissance or credential stuffing against the auth endpoints.

**Remediation:**
1. Log every failed verify attempt at WARNING level: `logger.warning("Failed magic link verify from %s", request.client.host)`.
2. Log rate limit triggers at WARNING level.
3. Add cumulative failed-attempt tracking per IP with escalating rate limits (e.g., temporary IP ban after 50 failures in an hour).
4. Log failed API token authentication attempts with the token prefix (first 8 chars) for correlation.

---

<!-- A06 and A08 sections will be added by T02 -->

