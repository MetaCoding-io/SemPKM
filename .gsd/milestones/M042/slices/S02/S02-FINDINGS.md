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

## A06: Vulnerable and Outdated Components

### F-031: Zero Subresource Integrity (SRI) on All CDN-Loaded Dependencies

**Severity:** High
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:**
- `backend/app/templates/base.html` (lines 29–30, 38–51)
- `backend/app/templates/base_embed.html` (lines 17–20)
- `backend/app/templates/browser/map_view.html` (Leaflet CDN URLs)
- `backend/app/templates/browser/timeline_view.html` (Frappe Gantt CDN URLs)
- `backend/app/templates/browser/workspace.html` (dockview CDN URLs)
- `backend/app/templates/admin/model_detail.html` (line 388)
- `backend/app/templates/admin/sparql.html` (lines 11–12)
- `backend/app/templates/errors/403.html` (line 23)
- `frontend/static/js/workspace.js` (line 3432)
- `frontend/static/js/calendar.js` (line 13)
- `frontend/static/js/theme.js` (line 47)

**Description:**
Every CDN-loaded `<script>` and `<link>` tag across the entire codebase is missing the `integrity` attribute. There are zero `integrity=` attributes in any template or JS file. This applies to both always-loaded CDN dependencies (production and dev) and dev-only CDN dependencies.

The full CDN dependency inventory across all templates and JS files:

**Always-CDN — loaded in both production and development:**

| Library | Version Pin | SRI | CDN Host | Loaded From |
|---------|-----------|-----|----------|-------------|
| gridstack | `@10` (major only) | ❌ None | cdn.jsdelivr.net | `base.html` (lines 29–30) |
| fullcalendar | `@6.1.17` (exact) | ❌ None | cdn.jsdelivr.net | `calendar.js` (line 13, lazy) |
| leaflet | `@1.9.4` (exact) | ❌ None | unpkg.com | `map_view.html` (lazy) |
| leaflet.markercluster | `@1.5.3` (exact) | ❌ None | unpkg.com | `map_view.html` (lazy) |
| chart.js | `@4.4` (minor only) | ❌ None | cdn.jsdelivr.net | `workspace.js` (line 3432, lazy) |
| chart.js | `@4.4` (minor only) | ❌ None | cdn.jsdelivr.net | `model_detail.html` (line 388) |
| frappe-gantt | `@1.2.2` (exact) | ❌ None | cdn.jsdelivr.net | `timeline_view.html` (lazy) |
| highlight.js themes | `11.11.1` (exact) | ❌ None | cdnjs.cloudflare.com | `theme.js` (line 47, runtime swap) |

**Dev-only CDN — vendored in production via `frontend/build.js`:**

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

**Three CDN hosts in use:** `unpkg.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`. A compromise of any single CDN host delivers malicious JavaScript to all SemPKM users loading from that host.

**Exploit Scenario:**
1. An attacker compromises the npm registry account for `marked` (or any other dependency) and publishes a malicious version.
2. unpkg.com and cdn.jsdelivr.net immediately serve the compromised package.
3. Because there are no `integrity` attributes, the browser fetches and executes the malicious script without any hash check.
4. The malicious script has full access to the page DOM, including: session cookies (unless HttpOnly), SPARQL query capabilities via the workspace API, all displayed knowledge graph data, and the ability to exfiltrate data via `fetch()` to an attacker-controlled server.
5. Because CSP is also absent (see F-021), there is no browser-level restriction on what the malicious script can do.

**Severity Assessment:**
- For always-CDN deps (gridstack, fullcalendar, leaflet, chart.js, frappe-gantt, hljs themes): **High** — affects all deployments including production.
- For dev-only CDN deps: **Medium** — affects developers only; production uses vendored bundles.
- The combination of zero SRI + zero CSP means a CDN compromise has unrestricted code execution.

**Localhost Mitigation:** The threat model still applies — a CDN compromise serves malicious code regardless of whether the client is localhost or cloud.

**Remediation:**
1. Generate SRI hashes for all CDN-loaded scripts and stylesheets:
```bash
curl -s https://cdn.jsdelivr.net/npm/gridstack@10/dist/gridstack-all.js | openssl dgst -sha384 -binary | openssl base64 -A
```
2. Add `integrity` and `crossorigin="anonymous"` attributes to all `<script>` and `<link>` tags:
```html
<script src="https://cdn.jsdelivr.net/npm/gridstack@10/dist/gridstack-all.js"
        integrity="sha384-<hash>"
        crossorigin="anonymous"></script>
```
3. For dynamically created `<script>` elements (calendar.js, workspace.js, theme.js, map_view.html, timeline_view.html), set `script.integrity` and `script.crossOrigin` before appending to `document.head`.
4. Long-term: extend the M029 vendor pipeline (`frontend/build.js`) to cover the always-CDN deps, eliminating the CDN dependency entirely for production.

---

### F-032: Three CDN Dependencies Loaded Without Any Version Pin

**Severity:** High
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:**
- `backend/app/templates/base.html` (lines 42, 43, 46)
- `backend/app/templates/base_embed.html` (lines 18, 19)

**Description:**
Three libraries are loaded from CDN URLs with no version specifier at all:

| Library | CDN URL | Resolves To |
|---------|---------|-------------|
| marked | `https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js` | Latest published version |
| marked-highlight | `https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js` | Latest published version |
| dompurify | `https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js` | Latest published version |

Additionally, two deps use partial version pins that resolve to the latest matching release:

| Library | CDN URL | Resolves To |
|---------|---------|-------------|
| gridstack | `https://cdn.jsdelivr.net/npm/gridstack@10/...` | Latest 10.x.x |
| chart.js | `https://cdn.jsdelivr.net/npm/chart.js@4.4/...` | Latest 4.4.x |

The fully unpinned deps (`marked`, `marked-highlight`, `dompurify`) change their resolved version every time a new release is published to npm. This means:
- Different users loading the page at different times get different library versions.
- A breaking change in any of these libraries can silently break functionality.
- A malicious npm publish (account takeover, typosquat) is immediately served to all users.

**DOMPurify is particularly critical** — it is the HTML sanitization library that prevents XSS in user-generated markdown content. An attacker who publishes a compromised DOMPurify version effectively disables XSS protection for all SemPKM instances loading from CDN.

**Exploit Scenario:**
1. An attacker gains publish access to the `dompurify` npm package (via account takeover or social engineering).
2. The attacker publishes version 3.99.0 with a subtle modification: the `sanitize()` function returns input unchanged for strings containing a specific trigger pattern.
3. cdn.jsdelivr.net immediately serves the new version because the URL has no version pin.
4. All SemPKM instances in dev mode (and `base_embed.html` in all modes) load the compromised DOMPurify.
5. The attacker creates a knowledge graph object with a body containing the trigger pattern + XSS payload.
6. When rendered, DOMPurify passes the payload through, achieving persistent XSS.

**Localhost Mitigation:** None — unpinned CDN URLs are dangerous regardless of deployment context. The compromise is upstream, not network-level.

**Remediation:**
1. **Immediate:** Pin exact versions for all three libraries:
```html
<script src="https://cdn.jsdelivr.net/npm/marked@15.0.7/lib/marked.umd.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked-highlight@2.2.1/lib/index.umd.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js"></script>
```
2. Pin gridstack and chart.js to exact patch versions.
3. Add SRI hashes (see F-031) after pinning versions.
4. These three libraries are already vendored in production via `frontend/build.js` — this finding primarily affects dev mode and `base_embed.html`.

---

### F-033: Always-CDN Dependencies Not Covered by Vendor Pipeline

**Severity:** Medium
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:**
- `frontend/build.js` — vendor pipeline
- `backend/app/templates/base.html` (gridstack)
- `frontend/static/js/calendar.js` (fullcalendar)
- `backend/app/templates/browser/map_view.html` (leaflet, markercluster)
- `frontend/static/js/workspace.js` (chart.js)
- `backend/app/templates/browser/timeline_view.html` (frappe-gantt)
- `frontend/static/js/theme.js` (highlight.js themes)

**Description:**
The M029 vendor pipeline (`frontend/build.js`) successfully vendors 17 libraries into content-hashed bundles for production use. Templates use `{% if asset_manifest_available %}` to switch between vendored (production) and CDN (dev). However, 7 libraries remain always-CDN — they load from external CDN hosts in both development and production:

| Library | Why Not Vendored | Production Impact |
|---------|-----------------|-------------------|
| gridstack@10 | Comment in base.html: "not yet in vendor bundle" | Loaded on every page with dashboard widgets |
| fullcalendar@6.1.17 | Lazy-loaded via `document.createElement('script')` in calendar.js | Loaded when calendar view opened |
| leaflet@1.9.4 | Lazy-loaded in map_view.html template | Loaded when map view opened |
| leaflet.markercluster@1.5.3 | Lazy-loaded in map_view.html template | Loaded when map view opened |
| chart.js@4.4 | Lazy-loaded in workspace.js (workspace stat widgets) | Loaded when SPARQL stat widget renders |
| frappe-gantt@1.2.2 | Lazy-loaded in timeline_view.html template | Loaded when timeline view opened |
| highlight.js themes | Runtime-swapped in theme.js based on user theme preference | Loaded on every page (CSS only) |

Note: `chart.js@4.4` is vendored for the admin model_detail page (via `build.js` section 6) but separately loaded from CDN in `workspace.js` for the workspace stat widget — the vendored bundle exists but isn't used in the workspace context.

**Exploit Scenario:**
A CDN outage at cdn.jsdelivr.net or unpkg.com causes these views to fail silently. Gridstack is loaded on every page — a jsdelivr outage breaks all dashboard layouts. Calendar, map, timeline views become completely non-functional. The highlight.js theme swap fails, leaving syntax highlighting unstyled.

More critically, without SRI (F-031), a CDN compromise serves malicious code to production users — not just developers.

**Remediation:**
1. Add gridstack to the `vendorJsSources` array in `frontend/build.js` and update `base.html` to use `{{ 'vendor.js' | asset_url }}` for gridstack in production mode.
2. For lazy-loaded libraries (fullcalendar, leaflet, frappe-gantt), create separate content-hashed bundles in `build.js` (similar to the yasgui and chartjs bundles) and update the lazy-load URLs to use `asset_url` when `asset_manifest_available`.
3. For highlight.js themes, the runtime theme swap in `theme.js` already has a production path using `asset_url` — confirm it covers all theme variants.

---

### F-034: No Automated Dependency Vulnerability Scanning

**Severity:** Medium
**OWASP Category:** A06:2021 — Vulnerable and Outdated Components
**Affected Files:**
- `backend/pyproject.toml` — Python dependencies (29 packages with `~=` compatible-release pins)
- `frontend/package.json` / `frontend/package-lock.json` — JavaScript dependencies
- `frontend/Dockerfile` (line 6: `npm ci --no-audit --no-fund`)

**Description:**
No automated CVE scanning or dependency audit pipeline exists for either the Python or JavaScript dependency trees:

| Check | Python | JavaScript |
|-------|--------|------------|
| Lockfile exists | ✅ `uv.lock` (280 packages) | ✅ `package-lock.json` |
| Version pins | ✅ `~=` compatible-release | ✅ Lockfile |
| `pip-audit` / `safety` in CI | ❌ None | N/A |
| `npm audit` in CI | N/A | ❌ None |
| Dependabot / Renovate configured | ❌ None | ❌ None |
| Snyk / Socket / etc. | ❌ None | ❌ None |
| GitHub Advisory Database alerts | ❌ No `.github/workflows/` directory exists | ❌ Same |

The frontend Dockerfile explicitly suppresses npm audit output: `npm ci --no-audit --no-fund` (line 6 of `frontend/Dockerfile`). While `--no-audit` is common in CI to avoid false-positive build failures, without a separate audit step the vulnerability information is never surfaced.

**Notable dependency versions (backend, from `pyproject.toml`):**
- `cryptography~=46.0.5` — frequently has CVEs; no automated update path
- `jinja2~=3.1.6` — template engine with past SSTI vulnerabilities
- `pyjwt~=2.10` — JWT implementation; correctness bugs can be security-critical
- `httpx~=0.28` — HTTP client used for federation sync; TLS bugs matter

**Exploit Scenario:**
1. A CVE is published for `cryptography` (a common occurrence — this package had 8 CVEs in 2024).
2. With no scanning pipeline, the vulnerability goes unnoticed until a developer manually checks.
3. If the CVE affects TLS certificate validation (which `cryptography` handles for `httpx`), federation sync traffic could be silently intercepted.

**Remediation:**
1. Add `pip-audit` to CI: `pip-audit --requirement requirements.txt --strict`
2. Add `npm audit` step in CI: `cd frontend && npm audit --audit-level=moderate`
3. Configure GitHub Dependabot (`.github/dependabot.yml`) for both pip and npm ecosystems
4. Remove `--no-audit` from `frontend/Dockerfile` or add a separate audit step that surfaces the output

---

## A08: Software and Data Integrity Failures

### F-035: ZIP Extraction Without Zip-Bomb or Size-Limit Protection

**Severity:** Medium
**OWASP Category:** A08:2021 — Software and Data Integrity Failures
**Affected Files:**
- `backend/app/obsidian/router.py` (lines 125–126)
- `backend/app/notion/router.py` (lines 152–153)
- `frontend/nginx.conf` (lines 195–196)

**Description:**
Both the Obsidian and Notion import endpoints extract user-uploaded ZIP files without checking total uncompressed size or file count:

```python
# backend/app/obsidian/router.py, line 125-126
with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(extract_path)
```

```python
# backend/app/notion/router.py, line 152-153
with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(extract_path)
```

Before extraction, no validation occurs:
- No check on total uncompressed size (`sum(info.file_size for info in zf.infolist())`)
- No check on file count (`len(zf.infolist())`)
- No check on compression ratio (zip bombs use extreme ratios like 1000:1)
- The Obsidian upload endpoint has `client_max_body_size 0` in nginx (F-027), removing even the compressed-size gate

**Path traversal mitigation:** Python 3.12+ (which this project uses per the Dockerfile's Python 3.12 base image) rejects ZIP entries containing `..` path components by default via the fix for CVE-2024-0450. This eliminates the classic zip-slip vulnerability. The remaining risk is resource exhaustion.

**Exploit Scenario:**
1. An authenticated user uploads a zip bomb — a 10MB compressed file that expands to 10GB of nested XML/text files (readily available as proof-of-concept files).
2. `zf.extractall()` writes 10GB to the container's filesystem, exhausting disk space.
3. The API container becomes unresponsive as disk writes consume all I/O bandwidth.
4. Other users cannot create objects, run SPARQL queries, or access the workspace.
5. If the extraction directory is on a mounted volume shared with the host, host disk space is consumed.

**Localhost Mitigation:** Self-inflicted DoS only. However, even on localhost, an accidentally corrupted ZIP (e.g., from a broken Obsidian backup plugin) could trigger unexpected disk exhaustion.

**Remediation:**
1. Before calling `extractall()`, inspect the ZIP contents:
```python
with zipfile.ZipFile(zip_path, "r") as zf:
    total_size = sum(info.file_size for info in zf.infolist())
    file_count = len(zf.infolist())
    if total_size > MAX_EXTRACT_SIZE:  # e.g., 2GB
        raise ValueError(f"ZIP uncompressed size ({total_size}) exceeds limit")
    if file_count > MAX_FILE_COUNT:  # e.g., 50000
        raise ValueError(f"ZIP file count ({file_count}) exceeds limit")
    zf.extractall(extract_path)
```
2. Set `client_max_body_size` to a reasonable value (e.g., `500m`) on the Obsidian upload nginx location (see F-027).

---

### F-036: Federation Patches Are Not Cryptographically Signed

**Severity:** Medium
**OWASP Category:** A08:2021 — Software and Data Integrity Failures
**Affected Files:**
- `backend/app/federation/router.py` (lines 380–425, `export_patches()`)
- `backend/app/federation/service.py` (lines 600–680, `sync_shared_graph()`)

**Description:**
The federation sync mechanism exports and imports RDF patches between instances over HTTPS without any content-level integrity verification:

**Export side** (`export_patches()`, `federation/router.py`):
- Queries event graphs matching a shared graph IRI
- Serializes matching triples as patch text
- Returns JSON `{"patch_text": "...", "event_count": N}` over HTTPS
- No digital signature, HMAC, or content hash is attached to the patch

**Import side** (`sync_shared_graph()`, `federation/service.py`):
- Fetches patches from the remote instance via `httpx.AsyncClient.get()`
- Optional HTTP Signature authentication for the request (if `private_key_pem` and `key_id` are provided)
- Deserializes the patch and applies it to the local triplestore
- No verification that the patch content matches what the remote instance intended to send
- No content hash or signature validation on the received patch body

The HTTP Signature on the *request* authenticates the *requester*, not the *response content*. A man-in-the-middle who can intercept the HTTPS response (e.g., via a compromised CDN, a TLS-intercepting corporate proxy, or a compromised CA certificate) can modify the patch JSON in transit without detection.

**Exploit Scenario:**
1. Instance A and Instance B federate a shared knowledge graph.
2. An attacker positioned on the network path (corporate TLS inspection proxy, compromised DNS, BGP hijack) intercepts the HTTPS response from Instance B's `/api/federation/patches/{graph_id}` endpoint.
3. The attacker modifies the `patch_text` to inject additional RDF triples — for example, adding a `owl:sameAs` triple that merges two distinct entities, or inserting misleading metadata.
4. Instance A's `sync_shared_graph()` deserializes and applies the modified patch without detecting the tampering.
5. The injected triples persist in Instance A's triplestore and propagate through SPARQL queries and views.

**Localhost Mitigation:** Federation is disabled by default on localhost instances. This finding only applies when federation is explicitly configured between multiple instances.

**Remediation:**
1. Add a content hash to patch exports:
```python
import hashlib
patch_hash = hashlib.sha256(patch_text.encode()).hexdigest()
return {"patch_text": patch_text, "event_count": count, "sha256": patch_hash}
```
2. On the import side, verify the hash before applying:
```python
received_hash = data.get("sha256")
computed_hash = hashlib.sha256(patch_text.encode()).hexdigest()
if received_hash and received_hash != computed_hash:
    errors.append("Patch integrity check failed — content modified in transit")
    return SyncResult(pulled=event_count, applied=0, errors=errors)
```
3. Long-term: implement Ed25519 or RSA signing of patch content, where the exporting instance signs the patch with its private key and the importing instance verifies with the exporting instance's public key (exchanged during federation setup).

---

### F-037: Federation Sync Applies Remote RDF Content Without Semantic Validation

**Severity:** Low
**OWASP Category:** A08:2021 — Software and Data Integrity Failures
**Affected Files:**
- `backend/app/federation/service.py` (lines 670–680, `sync_shared_graph()`)

**Description:**
When `sync_shared_graph()` deserializes a remote patch, the resulting quads are applied to the local triplestore without any content filtering or semantic validation. The only validation is that the patch is syntactically valid RDF (the `deserialize_patch()` call would fail on malformed content).

No checks are performed for:
- **Ontology injection:** The remote patch could contain `owl:Class`, `rdfs:subClassOf`, or SHACL shape triples that modify the local schema.
- **Metadata pollution:** Triples targeting system-managed predicates (`sempkm:*` namespace) could manipulate internal state.
- **Scope violation:** The patch should only contain triples within the shared graph's scope, but there is no enforcement that the patch content is limited to the expected named graph or expected RDF types.
- **Volume:** No limit on the number of triples in a single patch — a remote instance could send millions of triples in one sync.

**Exploit Scenario:**
1. A malicious federated instance (or an attacker who has compromised a federated instance) responds to a sync request with a patch containing thousands of SHACL shape triples.
2. These shapes define `sh:sparql` constraints with embedded SPARQL that queries sensitive named graphs.
3. When the local instance runs SHACL validation (e.g., during the next object edit), the injected SPARQL executes against the local triplestore, potentially extracting data from private graphs.

**Assessment:** This is a defense-in-depth concern. The primary protection is that federation is opt-in and requires explicit trust configuration between instances. The risk materializes only when a trusted federated instance is compromised or when federation is configured carelessly.

**Localhost Mitigation:** Not applicable — federation is a multi-instance feature.

**Remediation:**
1. Filter incoming patch triples to only allow predicates within the shared graph's expected namespace.
2. Reject triples using system-managed predicates (`sempkm:*`, `sh:*`, `owl:*`).
3. Limit the number of triples per sync operation (e.g., 10,000) with pagination for larger syncs.
4. Log the triple count and namespace distribution of each applied patch for audit purposes.

---

## Summary — Findings by Severity

| Severity | Count | Finding IDs |
|---|---|---|
| **High** | 5 | F-021, F-028, F-029, F-031, F-032 |
| **Medium** | 8 | F-022, F-023, F-026, F-030, F-033, F-034, F-035, F-036 |
| **Low** | 4 | F-024, F-025, F-027, F-037 |

**Total: 17 findings across 4 OWASP categories.**

### Findings by OWASP Category

| Category | Count | Severity Breakdown |
|----------|-------|--------------------|
| A05: Security Misconfiguration | 7 (F-021 – F-027) | 1 High, 3 Medium, 3 Low |
| A06: Vulnerable and Outdated Components | 4 (F-031 – F-034) | 2 High, 2 Medium |
| A08: Software and Data Integrity Failures | 3 (F-035 – F-037) | 0 High, 2 Medium, 1 Low |
| A09: Security Logging and Monitoring Failures | 3 (F-028 – F-030) | 2 High, 1 Medium |

### Top Remediation Priorities

1. **F-031 + F-032: Add SRI hashes and pin all CDN dependency versions** — Highest impact supply chain fix; SRI prevents execution of tampered scripts, version pins prevent silent upgrades.
2. **F-028: Redact magic link tokens from log output** — Easy fix, eliminates credential leakage in logs.
3. **F-029: Implement security event audit trail** — Enables forensic analysis of any future breach; currently zero visibility into auth events.
4. **F-033: Extend vendor pipeline to cover always-CDN deps** — Eliminates CDN dependency for production; gridstack is the most impactful since it loads on every page.
5. **F-021: Add HTTP security headers to all reverse proxy configs** — Low effort, high defensive value; CSP alone blocks most XSS exploitation.
6. **F-035: Add zip-bomb protection to import endpoints** — Prevents DoS via resource exhaustion.
7. **F-034: Establish automated CVE scanning pipeline** — Continuous vulnerability visibility for both Python and JavaScript dependency trees.
8. **F-036: Add content hashing to federation patches** — Prevents in-transit tampering of sync data.

