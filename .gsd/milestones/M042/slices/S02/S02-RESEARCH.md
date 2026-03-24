# S02 Research: Configuration, Infrastructure & Supply Chain Findings (A05, A06, A08, A09)

## Summary

This slice covers four OWASP Top 10 2021 categories through static analysis of nginx configs, Docker setup, CDN dependency inventory, federation data integrity, and logging/monitoring gaps. The codebase has ~40 CDN script/CSS loads across templates and JS files, zero SRI integrity attributes on any of them, zero HTTP security headers in nginx, Docker containers running as root with `--reload` in production Dockerfile CMD, and no security event audit logging. The findings are straightforward to document — most involve comparing config files against known-good baselines.

## Recommendation

Light-to-moderate effort. Three tasks: (1) A05 Security Misconfiguration + A09 Logging findings, (2) A06 Vulnerable Components CDN/dependency inventory, (3) A08 Data Integrity findings. The work is independent per category and mechanically well-defined.

## Implementation Landscape

### A05: Security Misconfiguration

**Zero HTTP security headers — both nginx configs and Caddyfile.cloud:**
- No `Content-Security-Policy` (no CSP at all)
- No `X-Frame-Options` / `X-Content-Type-Options` / `Strict-Transport-Security` / `Referrer-Policy` / `Permissions-Policy`
- No `server_tokens off` in nginx — nginx version disclosed in Server header
- Files: `frontend/nginx.conf`, `frontend/nginx.demo.conf`, `Caddyfile.cloud`

**CORS wildcard in both nginx and FastAPI middleware:**
- nginx: `add_header Access-Control-Allow-Origin "*" always` on `/api/` and `/.well-known/`
- FastAPI: `CORSMiddleware` with `allow_origins=["*"]` when `cors_origins` config is empty (default)
- FastAPI CORS has two modes: if `CORS_ORIGINS` env is set → specific origins + credentials; if empty → wildcard without credentials
- Double CORS header risk: nginx adds `Access-Control-Allow-Origin: *` on proxied responses, AND FastAPI middleware also sets it — could produce duplicate headers
- Files: `frontend/nginx.conf` (lines 76-78, 98-100, 116-118), `backend/app/main.py` (lines 632-649)

**Uvicorn `--reload` in production Dockerfile:**
- `backend/Dockerfile` CMD: `uvicorn ... --reload --reload-dir /app/app`
- `--reload` enables file watching, increases memory usage, and is inappropriate for production
- Volume mounts in docker-compose.yml enable hot-reload for dev, but the Dockerfile itself should have a production-safe default

**Docker containers run as root:**
- Neither `backend/Dockerfile` nor `frontend/Dockerfile` has a `USER` directive
- Both api and frontend containers run as root (PID 1)
- No `read_only`, `security_opt: no-new-privileges`, `cap_drop` in any compose file

**No global 500 error handler:**
- Only `HTTPException` and `RateLimitExceeded` have custom handlers in `main.py`
- Unhandled exceptions use FastAPI/Starlette defaults which include stack traces when `--reload` is active
- `detail=str(e)` in 6 endpoint exception handlers leaks internal error messages to API clients
- Files: `backend/app/workflow/router.py`, `backend/app/dashboard/router.py`, `backend/app/task_templates/router.py`, `backend/app/auth/router.py`, `backend/app/vfs/mount_router.py`

**Demo instance hardcoded secret:**
- `docker-compose.demo.yml`: `SECRET_KEY: demo-secret-key-not-for-production`
- Predictable key enables session forging

**Triplestore not exposed to host (good):**
- RDF4J port 8080 is internal to Docker network only — no `ports:` mapping

### A06: Vulnerable and Outdated Components

**Complete CDN dependency inventory — zero SRI across all loads:**

Always CDN (even in production builds):
1. `gridstack@10` — major-only pin, no SRI — `base.html` lines 29-30 (both modes)
2. `fullcalendar@6.1.17` — lazy-loaded in `calendar.js:13`
3. `leaflet@1.9.4` + `leaflet.markercluster@1.5.3` — lazy-loaded in `map_view.html`
4. `chart.js@4.4` — lazy-loaded in `workspace.js:3432` (major-only pin)
5. `highlight.js` themes — runtime-swapped in `theme.js:47`

CDN in dev mode only (vendored in production):
6. `htmx.org@2.0.4` — `base.html`
7. `split.js@1.6.5` — `base.html`
8. `ninja-keys@1.2.2` — `base.html`
9. `cytoscape@3.33.1` + `layout-base@2.0.1` + `cose-base@2.2.0` + `cytoscape-fcose@2.2.0` + `dagre@0.8.5` + `cytoscape-dagre@2.5.0` — `base.html`
10. `marked` (unpinned) + `marked-highlight` (unpinned) — `base.html`, `base_embed.html`
11. `dompurify` (unpinned) — `base.html`, `base_embed.html`
12. `lucide@0.575.0` — `base.html`, `base_embed.html`, `errors/403.html`
13. `driver.js@1.4.0` — `base.html`
14. `dockview-core@4.11.0` — `workspace.html`
15. `yasgui@4.5.0` — `admin/sparql.html`
16. `chart.js@4.4` — `admin/model_detail.html`

3 CDN hosts used: `unpkg.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`

**Unpinned CDN deps (resolve to "latest" at load time):**
- `marked` — no version in URL
- `marked-highlight` — no version in URL
- `dompurify` — no version in URL
- `gridstack@10` — major-only pin (resolves to latest 10.x)
- `chart.js@4.4` — minor pin (resolves to latest 4.4.x)

**Backend dependencies:**
- `uv.lock` exists with 280 packages — versions frozen via lockfile
- `pyproject.toml` uses `~=` compatible-release pins (good)
- No automated CVE scanning pipeline (no `pip-audit`, `safety`, or Dependabot)
- Notable deps: `cryptography~=46.0.5`, `jinja2~=3.1.6`, `pyjwt~=2.10`

**Frontend dependencies:**
- `package-lock.json` exists — versions frozen
- `npm ci --no-audit --no-fund` in Dockerfile suppresses audit output during build
- No `npm audit` in CI/CD pipeline

**Build pipeline (M029) vendors most CDN deps:**
- `frontend/build.js` vendors deps from `node_modules/` into content-hashed bundles
- Templates use `asset_manifest_available` to switch between vendored and CDN
- Gap: gridstack, fullcalendar, leaflet, and JS-level lazy-loads NOT vendored

### A08: Software and Data Integrity Failures

**ZIP extraction without path traversal protection (mitigated by Python 3.12):**
- `backend/app/obsidian/router.py:126` — `zf.extractall(extract_path)` on user-uploaded Obsidian vault ZIP
- `backend/app/notion/router.py:153` — `zf.extractall(extract_path)` on user-uploaded Notion export ZIP
- Python 3.12+ raises `BadZipFile` on `..` paths by default (CVE-2024-0450 protection)
- No zip bomb protection — no total size check or file count limit before extraction
- `client_max_body_size 0` on the Obsidian upload nginx location removes the size guard

**Unsigned federation patches:**
- `export_patches()` at `federation/router.py:380` returns RDF patch data with session auth only
- Receiving instance `sync_shared_graph()` fetches patches via HTTP and applies them to the triplestore
- Patches are not cryptographically signed — a MITM on the federation link could inject triples
- The fetch uses httpx without certificate pinning (standard TLS only)

**No content signing for model archives:**
- Model installation (`services/models.py`) loads from local `models/` directory
- No hash verification or signature checking on ontology/shapes/rules files
- Low risk for self-hosted (files are on the filesystem) but relevant if model distribution is added

**RDF import has no content validation beyond parsing:**
- `rdf_import/` accepts Turtle/JSON-LD/RDF-XML and loads into triplestore
- No schema validation or content filtering — any valid RDF is accepted
- Could be used to inject misleading ontology triples if import source is untrusted

**`| safe` template usage (low risk):**
- `browser/embed_wrapper.html:4` — `{{ content | safe }}` renders pre-rendered Jinja2 fragment HTML
- Content is server-generated via `_embed_response()` in `views/router.py` — not user input
- Not exploitable but should be documented

### A09: Security Logging and Monitoring Failures

**Magic link tokens logged in plaintext:**
- `backend/app/auth/router.py:155,163` — `logger.info("Magic link token for %s: %s", body.email, token)`
- Auth tokens visible in container logs and any log aggregation system

**No security event audit trail:**
- No logging for: failed auth attempts, privilege escalation attempts, API token creation/revocation, role changes, admin actions (model install/uninstall), federation sync events
- The event store (RDF events) tracks data mutations but not security-relevant operations
- No log correlation IDs for tracing a request across nginx → FastAPI

**No failed auth attempt logging:**
- Magic link verify endpoint returns 400 on invalid token but doesn't log the attempt
- No brute-force detection beyond rate limiting (5/min magic-link, 10/min verify)
- API token auth failures return 401 silently

**No request logging at nginx layer:**
- nginx access logs exist by default but have no structured format for security analysis
- No WAF or request inspection layer

**Error information disclosure in logs:**
- Multiple endpoints use `exc_info=True` which puts full stack traces in logs — fine for debugging but should be at DEBUG level, not WARNING/ERROR in production

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| CDN compromise serves malicious JS to all users | SRI hashes would prevent execution of tampered scripts; vendor remaining CDN deps via build pipeline |
| Unpinned CDN deps (`marked`, `dompurify`) auto-update to potentially malicious version | Pin exact versions in CDN URLs or complete vendoring migration |
| Missing HTTP security headers enable clickjacking, MIME sniffing, XSS | Add headers in nginx config — low effort, high impact |
| Docker root containers → container escape risk higher | Add `USER` directives to Dockerfiles |
| `--reload` in production Dockerfile → file watcher overhead, potential info leak | Separate CMD for dev vs prod, or use compose override |
| Magic link tokens in logs → credential theft from log access | Redact token values or log only a hash/prefix |

## Key Files

| File | Role |
|------|------|
| `frontend/nginx.conf` | Main nginx reverse proxy — security headers, CORS, upload limits |
| `frontend/nginx.demo.conf` | Demo instance nginx — same header gaps |
| `Caddyfile.cloud` | Cloud deployment reverse proxy — no security headers |
| `backend/Dockerfile` | API container — root user, `--reload` in CMD |
| `frontend/Dockerfile` | Frontend container — root user |
| `docker-compose.yml` | Main compose — no security_opt, no cap_drop |
| `docker-compose.demo.yml` | Demo compose — hardcoded SECRET_KEY |
| `docker-compose.cloud.yml` | Cloud compose — inherits api container issues |
| `backend/app/main.py` | CORSMiddleware config, exception handlers |
| `backend/app/templates/base.html` | CDN dependency loads (both modes) |
| `backend/app/templates/browser/calendar_view.html` | Lazy-loaded FullCalendar CDN |
| `backend/app/templates/browser/map_view.html` | Lazy-loaded Leaflet CDN |
| `frontend/static/js/workspace.js` | Lazy-loaded Chart.js CDN |
| `frontend/static/js/calendar.js` | Lazy-loaded FullCalendar CDN |
| `frontend/static/js/theme.js` | Runtime-loaded highlight.js themes CDN |
| `backend/app/obsidian/router.py` | ZIP extractall (Obsidian import) |
| `backend/app/notion/router.py` | ZIP extractall (Notion import) |
| `backend/app/federation/router.py` | Unsigned patch export/sync |
| `backend/app/auth/router.py` | Magic link token logging |
| `backend/pyproject.toml` | Python dependency pins |
| `frontend/package.json` | JS dependency pins |
| `frontend/build.js` | Vendor/build pipeline |

## Natural Task Decomposition

**T01: A05 (Security Misconfiguration) + A09 (Logging & Monitoring) findings**
- Document: missing HTTP security headers (nginx, Caddy), CORS double-header issue, Docker security posture (root containers, `--reload`, no security_opt), error information disclosure (`detail=str(e)`), demo hardcoded secret
- Document: magic link token plaintext logging, absent security event audit trail, no failed auth logging, error level info disclosure
- These two categories share many of the same files and config surfaces, natural to combine

**T02: A06 (Vulnerable Components) CDN/dependency inventory**
- Build the complete CDN dependency table with: library name, version pin status, SRI status, template location, dev-only vs always-loaded
- Document unpinned deps, missing vendor pipeline coverage, absent CVE scanning pipeline
- Assess backend/frontend dependency management posture (lockfiles, pin strategy)

**T03: A08 (Data Integrity) findings**
- Document: ZIP extraction without zip bomb protection (path traversal mitigated by Python 3.12), unsigned federation patches, unvalidated RDF import content, no model archive verification
- Lower severity category — federation patch signing only matters for MITM on federation links

## SPARQL Injection Context from S01

S01 already classified SPARQL injection under A03 — 33 modules analyzed, 5 confirmed-exploitable, 4 likely-exploitable. S02 should NOT duplicate this. The federation router's f-string SPARQL in `export_patches()` was classified in S01. S02 covers the federation's data integrity aspect (unsigned patches over HTTPS).

## Production vs Dev CDN Posture

The build pipeline (M029, `frontend/build.js`) vendors most dependencies into content-hashed bundles. Templates use `{% if asset_manifest_available %}` to switch between vendored (production) and CDN (dev). Key gaps in the vendor pipeline:

**Always CDN even in production:** gridstack, fullcalendar, leaflet+markercluster, chart.js (in workspace.js lazy-load), highlight.js themes (runtime swap)

**CDN only in dev mode:** htmx, split.js, ninja-keys, cytoscape stack, marked, dompurify, lucide, driver.js, dockview, yasgui, chart.js (admin page)

The severity assessment should note that dev-mode CDN loads affect developers only, while always-CDN loads affect all deployments. SRI absence applies to both.
