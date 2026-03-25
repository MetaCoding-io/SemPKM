---
depends_on: [M042]
---

# M045: Security Hardening — OWASP Remediation

**Gathered:** 2026-03-25
**Status:** Planning

## Project Description

Remediation of all 44 security findings from the M042 audit. Addresses all 10 OWASP Top 10 categories: SPARQL injection (9 modules), missing HTTP security headers, CDN supply chain integrity, Docker hardening, security event audit trail, authentication lifecycle improvements, federation integrity, and error disclosure fixes.

## Why This Milestone

M042 produced a comprehensive 44-finding security audit. The user reviewed the findings and decided to remediate all 17 S02 findings (which represent the full infrastructure/config/supply-chain surface) plus all findings from S01 (injection, access control, authentication) and S03 (crypto, design, SSRF). Total: 44 findings across all OWASP categories.

## User-Visible Outcome

When this milestone is complete:
- All SPARQL injection vectors are closed with consistent `_validate_iri()` application
- HTTP security headers (CSP, X-Frame-Options, HSTS, nosniff, etc.) are present on all responses
- All CDN dependencies are vendored for production; dev mode has SRI + exact version pins
- Docker containers run as non-root with security constraints
- Security events (login, token ops, role changes) are logged in the RDF event stream
- Magic link tokens are single-use and redacted from logs
- Federation patches have SHA-256 integrity verification and namespace filtering
- ZIP imports have bomb protection and size limits
- Failed auth attempts are logged with rate limit escalation
- Global exception handler prevents stack trace leakage

## Key Decisions (from user review)

- **D356:** Full vendor pipeline for all 25 CDN deps
- **D357:** Pragmatic CSP with `'unsafe-inline'`, not nonce-based
- **D358:** Security events in RDF event stream, not SQL table
- **D359:** Full Docker hardening with UID 1000 for volume compat
- **D360:** SHA-256 hash + namespace filtering for federation, no Ed25519

## Scope

### In Scope — All 44 M042 findings

**S01 findings (A01, A03, A07):** F-001 through F-020
**S02 findings (A05, A06, A08, A09):** F-021 through F-037
**S03 findings (A02, A04, A10):** F-038 through F-044

### Out of Scope

- Nonce-based CSP (pragmatic CSP chosen per D357)
- Full Ed25519 federation signing (hash-only per D360)
- App platform OS-level sandboxing (F-041 documented-only, current trust model is local installs)
- Multi-tenant object ownership (F-002 documented-only, current model is intentionally shared)
- Fernet key rotation infrastructure (F-039 documented-only, acceptable at current scale)
