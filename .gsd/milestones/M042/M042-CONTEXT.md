---
depends_on: []
---

# M042: Security Audit — OWASP Web Security & Backend Hardening

**Gathered:** 2026-03-23
**Status:** Queued — pending auto-mode execution

## Project Description

A systematic security audit of the SemPKM platform against the OWASP Top 10 Web Application Security Risks and backend hardening best practices. The sole deliverable is a prioritized security finding report. No fixes are made — the report feeds a subsequent remediation milestone where the user reviews and approves which findings to address.

The audit covers the full attack surface: the FastAPI backend (60k LOC, 233 modules), nginx reverse proxy configuration, frontend JavaScript (19k LOC), Jinja2 templates (165 files), authentication and session management, SPARQL query construction patterns, API token management, Docker deployment configuration, and the federation/WebDAV subsystems.

## Why This Milestone

SemPKM has shipped 40 milestones prioritizing feature velocity. Security was addressed tactically in M002 (rate limiting, token logging, SPARQL regex escaping, owner-only endpoints) but never systematically audited against a standard framework. Preliminary investigation reveals significant gaps:

- **Zero HTTP security headers** — nginx serves no `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Referrer-Policy`, or `Permissions-Policy` headers. The app is fully frameable and has no CSP.
- **No CSRF protection** — No CSRF tokens anywhere in the codebase. All state-mutating POST/PUT/DELETE endpoints rely solely on session cookies with `SameSite=Lax`, which mitigates most cross-site POST attacks but does not protect against same-site exploitation or subdomain attacks.
- **CORS wildcard on all API routes** — `Access-Control-Allow-Origin: *` on every `/api/` and `/.well-known/` response. Any website can make authenticated requests to the API if the user has an active session (mitigated by SameSite cookie, but Bearer token endpoints have no origin restriction).
- **SPARQL injection surface** — 24 backend modules construct SPARQL queries via f-string interpolation with user-controlled input. `escape_sparql_regex()` exists but only covers the regex escaping case, not general SPARQL literal injection.
- **Shell and debug endpoints exposed** — `backend/app/shell/router.py` and `backend/app/debug/router.py` are registered on the production router. Shell endpoints could allow arbitrary command execution if not properly gated.
- **Federation auth gap** — The federation patches endpoint requires session auth but is called server-to-server without credentials. HTTP Signature verification is partially implemented but not enforced.
- **Cookie secure=False noted as tech debt** — documented in PROJECT.md but never addressed systematically.

A self-hosted tool used for personal knowledge management is lower-risk than a public SaaS, but SemPKM now has a hosted demo instance (M025), cloud deployment guidance (M033), and federation between instances (v2.6). The attack surface has grown beyond "localhost only."

## User-Visible Outcome

### When this milestone is complete, the user can:

- Read a structured security finding report mapping each finding to OWASP Top 10 categories
- See severity ratings (Critical, High, Medium, Low, Informational) for each finding
- See exploit scenarios explaining how each vulnerability could be exploited in practice
- See remediation guidance for each finding (what to fix, approximate effort)
- See a prioritized top-10 list of the most critical findings across all categories
- Use the report to scope a remediation milestone with informed risk/effort tradeoffs

### Entry point / environment

- Entry point: `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` — the primary deliverable
- Environment: Development (static analysis of source code and configuration, no penetration testing)
- Live dependencies involved: None — pure code and config review

## Completion Class

- Contract complete means: every OWASP Top 10 category examined against the codebase with findings documented; backend hardening areas assessed; the finding report exists with severity-rated, OWASP-mapped entries with exploit scenarios and remediation guidance
- Integration complete means: N/A — this is analysis only
- Operational complete means: N/A — this is analysis only

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- The finding report covers all 10 OWASP Top 10 2021 categories (A01–A10) with per-category assessment
- Backend hardening areas are assessed: secret management, session lifecycle, API token storage, debug endpoint exposure, federation auth, file upload handling
- Infrastructure security is assessed: nginx configuration, Docker security, deployment hardening
- Every finding has: OWASP category, severity, exploit scenario, affected files, and remediation guidance
- The report includes a prioritized summary of the top 10 most critical findings

## Risks and Unknowns

- **No dynamic testing** — This is a static code/config review, not a penetration test. Some vulnerabilities (timing attacks, race conditions, complex multi-step exploits) may not be visible from code alone. Mitigation: acceptable — static analysis catches the structural issues that matter most for remediation planning.
- **SPARQL injection assessment complexity** — Determining which of the 24 f-string SPARQL modules are actually exploitable (user input reaches the query) vs safe (only internal values interpolated) requires tracing data flow through each call chain. Mitigation: classify each module as confirmed-exploitable, likely-exploitable, or safe with reasoning.
- **Self-hosted vs cloud context** — Severity ratings depend on deployment context. A CSRF vulnerability is less critical on localhost than on a cloud instance with federation. Mitigation: rate findings for the most exposed deployment model (cloud with federation enabled).

## Existing Codebase / Prior Art

- `backend/app/auth/dependencies.py` — Authentication dependency chain: `get_current_user` (session cookie), `get_current_user_or_api` (cookie + Bearer token), `require_role`/`require_role_or_api` factories. Cookie settings: httpOnly=True, sameSite=lax, secure=settings.cookie_secure. Verified on main.
- `backend/app/auth/router.py` — Magic link auth flow, session creation, rate limiting (5/min magic-link, 10/min verify via slowapi). Cookie set on successful verify. Verified on main.
- `backend/app/auth/models.py` — User, UserSession, ApiToken SQLAlchemy models. Sessions are opaque token-based (no JWT). ApiToken stores SHA-256 hash, not plaintext. Verified on main.
- `backend/app/sparql/utils.py` — `escape_sparql_regex()` for SPARQL regex metacharacter escaping. Only covers regex context, not general literal injection. Verified on main.
- `backend/app/sparql/client.py` — `scope_to_current_graph()` with `_strip_sparql_strings()` for keyword detection. `check_member_query_safety()` for read-only enforcement. Verified on main.
- `frontend/nginx.conf` — Reverse proxy config. CORS headers (`Access-Control-Allow-Origin: *`), gzip compression, cache headers. Zero security headers (no CSP, no X-Frame-Options, no HSTS). Verified on main.
- `frontend/nginx.demo.conf` — Demo instance nginx with POST/PUT/DELETE/PATCH blocking via error_page 495 pattern. Same absence of security headers. Verified on main.
- `backend/app/shell/router.py` — Shell endpoints. Needs role-gate verification. Verified present on main.
- `backend/app/debug/router.py` — Debug endpoints including event console. Owner-role gated per SEC-03. Verified on main.
- `backend/app/federation/` — Federation service with HTTP Signatures (partial implementation). Patches endpoint auth gap documented in PROJECT.md tech debt. Verified on main.
- `backend/app/services/llm.py` — LLM API key storage with Fernet symmetric encryption. Key derivation documented in D-series decisions. Verified on main.
- `backend/app/webid/service.py` — Ed25519 key generation and storage for WebID, Fernet-encrypted. Verified on main.
- `.gsd/DECISIONS.md` — D007 (slowapi rate limiting), D008 (SPARQL regex escaping), D161 (CORS `*` on all API routes), D165 (require_role_or_api for external clients). All verified.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- SEC-01 through SEC-05 — previously validated in M002 (rate limiting, token logging, debug endpoint gating, SPARQL regex escaping, deployment docs). This audit re-validates these and identifies what M002 missed.
- No new requirements created by this milestone — the finding report will inform requirement creation in the remediation milestone.

## Scope

### In Scope

**OWASP Top 10 2021 Assessment (A01–A10):**

- **A01: Broken Access Control** — role enforcement gaps, missing auth on endpoints, IDOR (IRI-based object access without ownership checks), privilege escalation paths, CORS misconfiguration
- **A02: Cryptographic Failures** — Fernet key derivation, secret storage, API token hashing, session token entropy, TLS configuration
- **A03: Injection** — SPARQL injection via f-string construction (24 modules), SQL injection via SQLAlchemy (lower risk with ORM), template injection via Jinja2, command injection via shell endpoints
- **A04: Insecure Design** — federation trust model, demo mode bypass logic, app platform sandbox escape potential, permission model completeness
- **A05: Security Misconfiguration** — missing HTTP security headers, CORS wildcard, debug endpoints in production, default configurations, Docker security
- **A06: Vulnerable and Outdated Components** — dependency versions, known CVEs in pinned versions, CDN-loaded libraries
- **A07: Identification and Authentication Failures** — magic link token lifecycle, session management, API token lifecycle, rate limiting coverage, credential enumeration
- **A08: Software and Data Integrity Failures** — unsigned federation patches, untrusted RDF import, app installation from disk without verification
- **A09: Security Logging and Monitoring Failures** — security event logging coverage, audit trail completeness, failure detection gaps
- **A10: Server-Side Request Forgery (SSRF)** — SPARQL federation SERVICE clause, app SDK HttpClient network restrictions, feed URL fetching, OAuth callback URLs

**Backend Hardening:**
- Secret management: encryption key derivation, storage, rotation
- Session lifecycle: creation, expiry, revocation, concurrent sessions
- API token management: creation, storage (hashing), revocation, scope
- Debug/shell endpoint exposure and role gating
- Federation authentication and signature verification
- File upload handling and validation
- Error information disclosure in responses
- Dependency security (known CVEs in pinned versions)

**Infrastructure Security:**
- nginx configuration hardening (security headers, TLS, rate limiting)
- Docker security (container privileges, volume permissions, network isolation)
- Deployment hardening (cloud compose, Caddy config, demo instance)

### Out of Scope / Non-Goals

- Penetration testing or dynamic application security testing (DAST)
- App Platform apps (`apps/` directory) — app sandbox security is covered under A04
- Frontend-only XSS (Jinja2 autoescape handles most cases — covered in A03 for template injection)
- Performance-related security (DoS resilience) beyond rate limiting assessment
- Implementing any fixes — the finding report is the only deliverable
- Compliance frameworks (SOC 2, ISO 27001) — this is OWASP-focused, not compliance-focused
- Mobile app security (`mobile/` directory) — React Native security is a different domain

## Technical Constraints

- Analysis uses `rg`, `ast-grep`, `fd`, and manual code review — no automated SAST/DAST tools (though findings may recommend adding them)
- The audit agent reads code and configuration but does not modify any files except the finding report
- Findings should be reproducible — include the search commands and reasoning used
- Severity ratings anchored to the most exposed deployment model (cloud with federation)

## Integration Points

- `.gsd/DECISIONS.md` — Security-relevant decisions (D007, D008, D161, D165, etc.) that explain current design choices
- `.gsd/PROJECT.md` — Known tech debt section includes security items (cookie secure=False, federation auth gap)
- `.gsd/KNOWLEDGE.md` — May contain security-relevant patterns or lessons
- `CLAUDE.md` — Project conventions that may have security implications
- M002 milestone summary — Previous security hardening work to cross-reference

## Open Questions

- **Severity context** — Should findings be rated for localhost-only deployment or cloud deployment with federation? Current thinking: rate for cloud with federation (the most exposed model). Add a "localhost mitigation" note where the severity would be lower for local-only use.
- **SPARQL injection depth** — Should the audit trace every f-string SPARQL path to determine exploitability, or flag all f-string SPARQL as a category finding? Current thinking: categorize all 24 modules, then trace the top 5-10 most likely exploitable paths in detail.
