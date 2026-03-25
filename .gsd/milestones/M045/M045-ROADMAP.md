# M045: Security Hardening - OWASP Remediation

**Vision:** Remediate all 44 M042 security audit findings — closing SPARQL injection vectors, adding HTTP security headers, eliminating CDN supply chain risk, hardening Docker containers, establishing a security event audit trail, and fixing authentication/federation/infrastructure gaps.

## Success Criteria

- All 9 SPARQL injection vectors (F-006 through F-010) closed with consistent `_validate_iri()` and unified `sparql_escape_string()`
- All 6 missing auth endpoints (F-001) have `get_current_user` dependency
- HTTP security headers present on all nginx/Caddy responses (F-021)
- CSP blocks non-allowlisted script sources in dev; `'self'`-only in production
- All 25 CDN dependencies vendored for production via extended `frontend/build.js` (F-031/F-032/F-033)
- Dev-mode CDN tags have SRI hashes and exact version pins
- Docker containers run as non-root with `no-new-privileges` and `cap_drop: ALL` (F-023)
- Security events (login, failed auth, token ops, role changes) logged in RDF event stream (F-029)
- Magic link tokens are single-use (F-012) and redacted from logs (F-028)
- Federation patches have SHA-256 integrity hashes (F-036) and namespace filtering (F-037)
- Federation sync endpoint has SSRF protection (F-043)
- ZIP imports have size/count validation (F-035)
- Global exception handler prevents stack trace leakage (F-025)
- `docker compose up` works with existing volume data after hardening

## Key Risks / Unknowns

- Non-root Docker user may break volume mount permissions on existing host data
- CSP `'unsafe-inline'` may still be too restrictive if any template uses eval() patterns
- Vendoring 7 new always-CDN libraries (gridstack, fullcalendar, leaflet, etc.) may require build.js architectural changes for lazy-loaded bundles
- Federation hash verification is a breaking change for existing federation peers

## Proof Strategy

- SPARQL injection closure → retire in S01 by running the same exploit payloads from the M042 triage
- CSP effectiveness → retire in S02 by verifying browser DevTools shows no CSP violations on workspace load
- Vendor pipeline completeness → retire in S03 by building production assets and confirming zero CDN `<script>` tags in production HTML
- Docker non-root → retire in S04 by verifying `docker compose up` starts cleanly and volume data survives
- Security audit trail → retire in S05 by triggering login events and querying them via SPARQL

## Verification Classes

- Contract verification: all 44 findings have corresponding code changes; automated tests pass
- Integration verification: workspace loads without errors with security headers active; vendor pipeline produces complete bundles; Docker stack starts with non-root user
- Operational verification: security events visible in event log; federation sync with hash verification succeeds
- UAT: user confirms no functional regression in workspace, views, federation, import flows

## Milestone Definition of Done

- All 44 M042 findings have corresponding remediation (code change, config change, or documented-as-designed with risk acceptance)
- `docker compose up` starts cleanly with hardened containers
- Workspace loads without CSP violations or missing vendor assets
- SPARQL injection payloads from M042 triage return errors (not data)
- Security events appear in the RDF event stream when triggered
- No functional regression in E2E test suite

## Requirement Coverage

- Covers: SEC-01 through SEC-05 (re-validates and extends M002 security hardening)
- Creates: new security requirements for CDN integrity, audit trail, Docker hardening

## Slices

- [ ] **S01: SPARQL Injection Closure & Access Control Fixes** `risk:high` `depends:[]`
  > After this: all 9 SPARQL injection vectors closed with consistent _validate_iri(); unified sparql_escape_string() replaces 4 inconsistent functions; 6 unauth'd endpoints have auth; CORS double-header fixed; favorites stored-injection blocked; SSRF guards on federation sync and webhooks
- [ ] **S02: HTTP Security Headers & Error Hardening** `risk:medium` `depends:[]`
  > After this: all nginx/Caddy configs emit CSP, X-Frame-Options, HSTS, nosniff, Referrer-Policy, Permissions-Policy; server_tokens off; global exception handler prevents stack trace leakage; startup guards for weak SECRET_KEY and insecure cookie config; rate limits on SPARQL/copilot/commands endpoints
- [ ] **S03: CDN Supply Chain — Full Vendor Pipeline & SRI** `risk:high` `depends:[]`
  > After this: all 25 CDN dependencies vendored for production; 7 always-CDN libs (gridstack, fullcalendar, leaflet, chart.js, frappe-gantt, hljs themes) added to build.js; dev-mode CDN tags have SRI hashes and exact version pins; zero CDN script tags in production HTML
- [ ] **S04: Docker Hardening & Infrastructure** `risk:medium` `depends:[]`
  > After this: both containers run as non-root (UID 1000); no-new-privileges + cap_drop in compose; --reload moved to compose override; upload size limits on Obsidian/Notion endpoints; zip-bomb protection; secret key file permissions restricted; dependency scanning documented
- [ ] **S05: Security Event Audit Trail & Auth Lifecycle** `risk:medium` `depends:[S01]`
  > After this: security events (login, failed auth, token create/revoke, role changes, model install, federation sync) logged in RDF event stream; magic link tokens single-use; token logging redacted; failed auth logged with IP; session management improvements
- [ ] **S06: Federation Integrity & Remaining Fixes** `risk:low` `depends:[S01]`
  > After this: federation patches have SHA-256 content hashes; namespace filtering rejects system predicates; triple count limits; app platform trust boundary documented; per-app JWT key derivation; cookie secure warning; remaining Info-level findings addressed or documented

## Boundary Map

### S01 (Injection + Access Control)
Produces: unified `sparql_escape_string()` in `sparql/client.py`; consistent `_validate_iri()` on all HTTP-facing SPARQL paths; SSRF guard utility
Consumes: nothing (independent)

### S02 (Headers + Error Hardening)  
Produces: nginx security headers include file; global exception handler; startup validation
Consumes: nothing (independent)

### S03 (Vendor Pipeline)
Produces: extended `frontend/build.js` with all 25 deps; content-hashed lazy bundles for view-specific libs; SRI hash constants
Consumes: nothing (independent)

### S04 (Docker + Infrastructure)
Produces: hardened Dockerfiles; updated compose files; zip validation utility
Consumes: nothing (independent)

### S05 (Audit Trail + Auth) → depends S01
Produces: security event logging service using RDF event store; single-use magic link tracking; redacted token logging
Consumes: S01's auth endpoint fixes (F-001 auth deps must be in place before audit logging is meaningful)

### S06 (Federation + Remaining) → depends S01
Produces: federation patch hashing; namespace filter; per-app JWT derivation; documentation updates
Consumes: S01's SSRF guard utility for federation endpoint
