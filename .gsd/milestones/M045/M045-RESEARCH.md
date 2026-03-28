# M045 Research: Security Hardening — OWASP Remediation

## 1. Findings Triage: Already Resolved vs Remaining

M043 ("Security Hardening — Injection, Auth & Access Control Fixes") and M044 ("Frontend Code Quality Execution") already resolved the majority of M042 findings. The M045 roadmap was written before these milestones completed, so most of its planned slices are now redundant. This research identifies the **actual remaining work**.

### Already Resolved (M043)

| Finding | Status | Resolved By |
|---------|--------|-------------|
| **F-001** Missing auth on 6 app endpoints | ✅ Fixed | M043/S02 — all endpoints have `Depends(get_current_user)` |
| **F-003** CORS wildcard/double-header | ✅ Fixed | M043/S02 — nginx CORS removed, FastAPI CORSMiddleware sole authority |
| **F-004** Setup endpoint lacks auth guard | ✅ Fixed | M043/S02 — setup_mode check added |
| **F-006** SPARQL injection via views `type` param | ✅ Fixed | M043/S01 — `safe_iri()` applied in views/router.py and views/service.py |
| **F-007** SPARQL injection via apps `iri` param | ✅ Fixed | M043/S01 — `safe_iri()` in browser/apps.py |
| **F-008** SPARQL write injection via VFS mount | ✅ Fixed | M043/S01 — `safe_iri()` on all IRI fields in mount_router.py |
| **F-009** Stored SPARQL injection via favorites | ✅ Fixed | M043/S01 — `safe_iri()` in browser/favorites.py |
| **F-010** Incomplete SPARQL string escaping | ✅ Fixed | M043/S01 — all local escape functions eliminated, unified `sparql_escape_string()` in builder.py |
| **F-012** Magic link tokens not single-use | ✅ Fixed | M043/S03 — `UsedMagicToken` model, check_and_consume via DB |
| **F-013** Unlimited concurrent sessions | ✅ Fixed | M043/S03 — 10-session cap, revoke-all endpoint, periodic cleanup |
| **F-016** API tokens unscoped | ✅ Fixed | M043/S03 — `scope` field, `scope_required()` dependency, migration 023 |
| **F-017** Rate limiting gaps | ✅ Fixed | M043/S04 — rate limits on SPARQL (60/min), copilot (20/min), commands (20/min), context (12/min) |
| **F-021** Missing HTTP security headers | ✅ Fixed | M043/S02 — CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, server_tokens off on all 3 proxy configs |
| **F-022** CORS double-header | ✅ Fixed | M043/S02 — nginx CORS removed entirely |
| **F-025** Error information disclosure | ✅ Fixed | M043/S04 — global exception handler returns generic 500; no `detail=str(e)` remaining |
| **F-027** Upload size limit (partial) | ✅ Fixed | M043/S02 — Obsidian capped at 500MB (D364) |
| **F-028** Magic link tokens logged in plaintext | ✅ Fixed | M043/S03 — only first 8 chars logged |
| **F-029** No security event audit trail (partial) | ⚠️ Partial | M043/S04 — SecurityAuditLog table + `log_security_event()` helper exist; auth events (login_success/failed, session_revoked_all, token_created/revoked) are logged. Model install, federation, role change, config events are NOT yet audited |
| **F-030** Failed auth not logged | ✅ Fixed | M043/S04 — _audit() on login_failed events with IP |
| **F-038** Secret key file permissions | ✅ Fixed | tokens.py has `os.chmod(key_path, 0o600)` |

### Already Resolved (M044 + vendor pipeline evolution)

| Finding | Status | Resolved By |
|---------|--------|-------------|
| **F-031** Zero SRI on CDN deps | ✅ Resolved differently | All CDN dependencies vendored — no CDN `<script>` tags remain; SRI unnecessary when serving from self |
| **F-032** Unpinned CDN deps (incl. DOMPurify) | ✅ Resolved differently | Everything vendored from npm with exact version pins in package.json |
| **F-033** Always-CDN deps not in vendor pipeline | ✅ Fixed | build.js now covers all 25 deps: gridstack, fullcalendar, leaflet+markercluster, chart.js, frappe-gantt, hljs — zero CDN refs in templates or JS |

### Not Actionable (documented as designed)

| Finding | Status | Notes |
|---------|--------|-------|
| **F-002** No object-level ownership | ℹ️ By design | Flat shared-data model is intentional |
| **F-005** PostHog API key exposed | ℹ️ By design | Write-only ingestion key, standard client-side pattern |
| **F-011** User-submitted SPARQL | ℹ️ By design | Defenses adequate (scope, role check, keyword filter). Query timeout/pagination are nice-to-have |
| **F-014** Session token entropy | ℹ️ Adequate | 256-bit tokens via `secrets.token_urlsafe(32)` |
| **F-019** Demo mode guest access | ℹ️ By design | Guest role correctly restricts mutations |
| **F-020** Federation inbox HTTP Signatures | ℹ️ Adequate | No finding per M042 audit |
| **F-039** No Fernet key rotation | ℹ️ Documented | Acceptable at current scale per M045 context; MultiFernet upgrade possible but not scoped |
| **F-040** Cookie secure flag risk | ℹ️ Low risk | Correct default; documenting in deployment guide sufficient |
| **F-041** App platform no OS isolation | ℹ️ Documented | Current trust model is local installs; per M045 context, this is out of scope |

### Remaining Unresolved Findings

| Finding | Severity | What's Needed | Effort |
|---------|----------|---------------|--------|
| **F-023** Docker containers run as root | Medium | Non-root user in Dockerfiles, `no-new-privileges` + `cap_drop` in compose | 2-3h |
| **F-024** Uvicorn `--reload` in production | Low | Remove from Dockerfile CMD, override in compose for dev | 15min |
| **F-026** Hardcoded demo SECRET_KEY | Medium | Generate at startup if weak/known, refuse to start in non-demo mode | 30min |
| **F-029** Audit trail for model/federation/role events | Medium | Extend `_audit()` pattern to models, federation, admin routers | 2-3h |
| **F-034** No dependency vulnerability scanning | Medium | Add pip-audit to CI; document npm audit; configure Dependabot | 1h |
| **F-035** ZIP extraction without bomb protection | Medium | Size/count check before extractall in both Obsidian + Notion importers | 1-2h |
| **F-036** Federation patches not signed | Medium | SHA-256 content hash on export, verify on import | 2-3h |
| **F-037** Federation no namespace filtering | Low | Filter incoming triples to expected namespaces | 1-2h |
| **F-042** App JWT tokens share platform secret | Medium | Per-app key derivation via HMAC(secret, app_id) | 1-2h |
| **F-043** Federation SSRF | High | IP blocklist (loopback, private, link-local) + scheme restriction | 1-2h |
| **F-044** Webhook SSRF | Low | Apply same IP blocklist to webhook dispatch | 30min |
| **CSP stale** Caddyfile.cloud CSP references CDN domains | Low | Remove CDN domains from CSP script-src (everything vendored now) | 15min |
| **HSTS missing** No Strict-Transport-Security on cloud config | Low | Add HSTS header to Caddyfile.cloud (Caddy auto-TLS handles the rest) | 15min |
| **PostHog CSP** PostHog blocked by current CSP | Info | Document: PostHog needs CSP exceptions when enabled; disabled by default, acceptable | 15min |
| **F-015/F-018** Cookie/credential misc | Low | Startup warnings for insecure configs; deployment guide updates | 30min |

## 2. Codebase Patterns to Reuse

### SPARQL Safety — `app.sparql.builder`
All IRI validation and string escaping is centralized (Pattern #12 in KNOWLEDGE.md). `safe_iri()` wraps rdflib `URIRef.n3()` with pre-validation regex. `sparql_escape_string()` handles `\ " ' \n \r \t`. Any new SPARQL-touching code must import from this module.

### Security Audit Logging — `app.auth.audit`
The `log_security_event()` helper creates its own session, catches all exceptions internally, and is fire-and-forget (Pattern from KNOWLEDGE.md). The `_audit()` wrapper in `router.py` shows the calling pattern: `await _audit(request, "event_type", user_id=..., detail={...})`. Extending audit coverage to model/federation/admin routers follows the same pattern.

### Rate Limiting — `app.auth.rate_limit`
slowapi with custom handler (`_rate_limit_exceeded_handler_with_logging`). `headers_enabled=False` to avoid Pydantic response crashes. Retry-After set manually.

### nginx Security Headers
All security headers live in the server block of `nginx.conf` (lines 9-13). nginx.demo.conf mirrors the same block. Caddyfile.cloud has a `header` block.

### ZIP Upload Safety Pattern
Obsidian upload already has `client_max_body_size 500m` in nginx. The missing piece is server-side zip bomb protection — check `ZipFile.infolist()` total uncompressed size and file count before calling `extractall()`.

## 3. Technical Approach for Remaining Work

### Docker Non-Root (F-023, F-024)
**Backend Dockerfile:** Add `RUN useradd -r -u 1000 -g root sempkm` and `USER sempkm`. The UID 1000 choice (per D359) avoids volume mount permission issues. `RUN mkdir -p /app/data && chown sempkm:root /app/data` before USER directive. Remove `--reload --reload-dir` from CMD — set it in compose `command:` override for dev.

**Frontend Dockerfile:** nginx-stable-alpine runs as root by default for binding to port 80. Options: (1) configure nginx to listen on 8080 and run as non-root, or (2) keep root but add `no-new-privileges`. Option 1 requires compose port mapping change. Option 2 is simpler and still improves posture.

**Compose:** Add `security_opt: [no-new-privileges:true]` and `cap_drop: [ALL]` to both services. For API, add `cap_add: [NET_BIND_SERVICE]` if needed (not needed — uvicorn binds 8000, not 80).

**Risk:** Volume mount permissions. Existing `data/` directory owned by root:root. The container user needs write access to `data/` (SQLite, secret key). The workaround: `chown -R 1000:0 data/` in entrypoint or init container. This is the primary risk for this change.

### Federation SSRF (F-043) + Webhook SSRF (F-044)
Create a shared `app.security.url_validator` module with a `validate_outbound_url()` function:
1. Parse URL — require `https://` scheme (or `http://` for localhost dev)
2. Resolve hostname via `socket.getaddrinfo()`
3. Check all resolved IPs against blocklists: `ipaddress.is_loopback`, `is_private`, `is_link_local`, `is_reserved`
4. Return validated URL or raise `ValueError`

Apply to: `federation/router.py` (sync endpoint), `services/webhooks.py` (dispatch).

### Federation Integrity (F-036, F-037)
**SHA-256 hashing (F-036):** In sync export, compute `hashlib.sha256(json.dumps(patch, sort_keys=True).encode()).hexdigest()` and include in response. In sync import, verify hash before applying. Breaking change for existing peers — needs versioned protocol.

**Namespace filtering (F-037):** Define allowed namespace prefixes for incoming federation triples. Reject triples with predicates in `urn:sempkm:` namespace (system-managed). Reject SHACL/OWL vocabulary injections. Log rejected triples.

### ZIP Bomb Protection (F-035)
Shared utility function `validate_zip_contents(zip_path, max_uncompressed_mb=2048, max_files=50000)`:
```python
def validate_zip_contents(zip_path, max_uncompressed_mb=2048, max_files=50000):
    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = zf.infolist()
        if len(infos) > max_files:
            raise ValueError(f"ZIP contains {len(infos)} files (limit: {max_files})")
        total_size = sum(info.file_size for info in infos)
        if total_size > max_uncompressed_mb * 1024 * 1024:
            raise ValueError(f"ZIP uncompressed size {total_size} exceeds limit")
```
Apply to both `obsidian/router.py` and `notion/router.py` before `extractall()`.

### Extended Audit Logging (F-029 completion)
The infrastructure exists (SecurityAuditLog table, `log_security_event()` helper, `_audit()` wrapper). Remaining work is wiring `_audit()` calls into:
- `admin/router.py` — model install/uninstall
- `federation/router.py` — sync events, invitation accept/reject
- `auth/router.py` — role changes (if an endpoint exists; check `/api/auth/users/{id}/role`)
- `services/models.py` — model operations

Each is a 2-3 line addition: import `_audit` pattern, add `await _audit(request, "model_installed", ...)` after the operation succeeds.

### Per-App JWT Key Derivation (F-042)
Change `tokens.py` `get_secret()` to `get_app_secret(app_id)`:
```python
import hmac
def get_app_secret(app_id: str) -> str:
    platform_secret = _get_secret_key()
    return hmac.new(platform_secret.encode(), app_id.encode(), 'sha256').hexdigest()
```
Update `AppManager` to pass `get_app_secret(app_id)` instead of `get_secret()`. Update `validate_app_token()` to accept `app_id` and derive the key.

### Demo SECRET_KEY (F-026)
Add startup check in `main.py` lifespan:
```python
KNOWN_WEAK_KEYS = {"demo-secret-key-not-for-production", "changeme", "secret"}
if settings.secret_key in KNOWN_WEAK_KEYS and not settings.demo_mode:
    logger.error("Refusing to start with known weak SECRET_KEY outside demo mode")
    raise SystemExit(1)
```

## 4. Risk Assessment

### What Should Be Proven First
**Federation SSRF (F-043)** is the highest-severity remaining finding — an authenticated user can make the server fetch arbitrary internal URLs. This should be in the first slice along with Docker hardening.

### Known Failure Modes
1. **Docker non-root volume permissions** — the primary risk. Existing deployments have `data/` owned by root. Switching to UID 1000 breaks write access. Needs an entrypoint script or migration note.
2. **Federation hash verification is a breaking change** — existing federation peers won't include hashes. Needs backward compat: verify if present, warn if absent.
3. **CSP + PostHog incompatibility** — PostHog is disabled by default so this is documentation-only, but anyone enabling it will need CSP exceptions.

### What's Not Worth a Separate Slice
Many remaining findings are small, isolated fixes (F-024 15min, F-026 30min, CSP stale 15min). These should be batched into a single infrastructure slice rather than getting individual slices.

## 5. Recommended Slice Structure

Given that M043/M044 already resolved ~30 of 44 findings, the remaining work is significantly smaller than the M045 roadmap assumes. The original 7-slice plan is over-engineered for what remains.

### Recommended: 3 Slices

**S01: SSRF Guards + Federation Integrity** `risk:high`
- F-043: Federation SSRF protection (shared URL validator)
- F-044: Webhook SSRF protection (reuse same validator)
- F-036: Federation patch SHA-256 hashing
- F-037: Federation namespace filtering
- F-042: Per-app JWT key derivation
- Audit logging extension (F-029 completion — model install, federation, role changes)

**S02: Docker Hardening + Infrastructure** `risk:medium`
- F-023: Non-root Docker user (UID 1000)
- F-024: Remove --reload from Dockerfile CMD
- F-026: Demo SECRET_KEY startup check
- F-035: ZIP bomb protection (Obsidian + Notion)
- F-034: Document dependency scanning (pip-audit command, npm audit command)
- CSP stale CDN domains in Caddyfile.cloud
- HSTS header for cloud config
- Startup warnings for insecure cookie/config combinations (F-015, F-018, F-040)

**S03: Verification + Documentation** `risk:low`
- Run SPARQL injection regression tests to confirm M043 fixes hold
- Run E2E suite against hardened Docker stack
- Update security-model.md with remaining fixes
- Document PostHog CSP requirements
- Final audit checklist against all 44 findings

### Why 3, Not 7
- S01-S04 from old roadmap are already done (M043)
- S03 (CDN vendor pipeline) is done (M044 + build.js evolution)
- The remaining findings cluster naturally around: network/federation security, Docker/infra, and verification
- E2E regression (old S07) should be part of the verification slice, not standalone

## 6. Boundary Contracts

### S01 → S02 Dependency
S01 produces the `app.security.url_validator` module. S02 doesn't use it (Docker/infra concerns are orthogonal). The slices are **independent** and could run in parallel.

### S02 → S03 Dependency
S03 (verification) depends on both S01 and S02 being complete before running the full regression.

### External Contract: Volume Permissions
The Docker non-root change (S02) requires existing deployments to adjust volume ownership. This is a **user-facing breaking change** that needs documentation in release notes and/or an automated entrypoint fix.

### External Contract: Federation Protocol
The SHA-256 hash verification (S01) is a **protocol-level change**. Existing federation peers won't send hashes. The implementation must be backward compatible: verify if `content_hash` field is present, log a warning if absent, and include hash in all outgoing patches.

## 7. Requirements Analysis

### Existing Requirements Coverage
M045 extends the validated M002 security hardening (SEC-01 through SEC-05). No new formal requirements are needed — this is remediation of audit findings, not new feature development.

### Candidate Requirements
- **SEC-06 (candidate):** All outbound HTTP requests from backend validate target URL against IP blocklist (no loopback, private, link-local, reserved). Covers federation sync and webhooks.
- **SEC-07 (candidate):** Docker containers run as non-root with `no-new-privileges` and `cap_drop: ALL`.
- **SEC-08 (candidate):** ZIP imports validate uncompressed size (≤2GB) and file count (≤50,000) before extraction.

These are security hygiene items that should be requirements if the project tracks them formally. Advisory only — not auto-binding.

## 8. Skill Discovery

The core technologies are Python/FastAPI, Docker, nginx/Caddy, and standard security practices. No specialized skills needed beyond what's already available. The `best-practices` and `debug-like-expert` skills are relevant if complex issues arise during Docker permission testing.
