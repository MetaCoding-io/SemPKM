---
id: S01
parent: M042
milestone: M042
provides:
  - S01-FINDINGS.md with 20 severity-rated security findings across OWASP A01, A03, A07
  - SPARQL injection classification of all 33 f-string SPARQL modules (5 confirmed-exploitable, 4 likely-exploitable, 24 safe)
  - Systematic auth dependency audit of all 40+ FastAPI routers
  - Non-SPARQL injection assessment (Jinja2, SQLAlchemy, command injection — all safe)
requires: []
affects:
  - S03
key_files:
  - .gsd/milestones/M042/slices/S01/S01-FINDINGS.md
  - .gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md
key_decisions:
  - Classified 33 modules (not the 29 estimated) — IRI interpolation pattern search found 4 additional modules
  - _validate_iri() identified as the critical defense — modules using it are safe, those without are exploitable
  - Three independent _sparql_escape functions with inconsistent coverage need consolidation
  - CORS wildcard confirmed safe for session cookies (SameSite=Lax blocks cross-origin cookie inclusion) but problematic for Bearer tokens
  - Flat authorization model (shared RDF graph) is by-design for current use but becomes a vulnerability if multi-tenant support is added
patterns_established:
  - Auth dependency scan pattern: enumerate all include_router calls in main.py, verify each endpoint for Depends(get_current_user)
  - SPARQL injection data-flow analysis: trace interpolated variable from HTTP parameter through service layer to f-string query construction
  - Severity rating anchored to cloud deployment with federation as the most exposed deployment model
observability_surfaces:
  - none (static analysis artifact, no runtime component)
drill_down_paths:
  - .gsd/milestones/M042/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M042/slices/S01/tasks/T02-SUMMARY.md
duration: 1h25m
verification_result: passed
completed_at: 2026-03-23
---

# S01: Injection, Access Control & Authentication Findings (A01, A03, A07)

**20 severity-rated security findings across the three highest-risk OWASP categories, with SPARQL injection classification of all 33 backend modules and systematic auth/access-control audit.**

## What Happened

**T01 — SPARQL injection triage:** Systematically analyzed every backend module constructing SPARQL via Python f-strings. Found 33 modules (4 more than the 29 estimated, discovered via IRI interpolation pattern `f".*<\{"`). Each module was traced from HTTP input through service layer to query construction. Result: 5 confirmed-exploitable (views/router.py, views/service.py, browser/apps.py, vfs/mount_router.py, sparql/router.py by design), 4 likely-exploitable (browser/events.py, browser/favorites.py, api/ai.py, api/router.py), and 24 safe. The key insight: `_validate_iri()` in `browser/_helpers.py` is the critical defense — it blocks `<>"\{}\n\r\t `, requires a scheme, and rejects unknown schemes. Modules using it are safe; those without are exploitable. Three independent `_sparql_escape` functions exist with inconsistent coverage — a consolidation target. Non-SPARQL vectors (Jinja2 template, SQLAlchemy, command injection) all assessed as safe.

**T02 — Access control + authentication audit:** Enumerated all 40+ routers via `include_router` calls in main.py. Found 6 unauthenticated endpoints on `browser/apps.py` — the most straightforward access control gap. Confirmed IDOR is not a vector because the flat authorization model is intentional (all RDF objects shared). CORS wildcard (`*`) is safe for session cookies (SameSite=Lax prevents cross-origin cookie inclusion) but allows Bearer token use from any origin. Session tokens use adequate entropy (256-bit via `secrets.token_urlsafe(32)`). Magic link tokens are not single-use — replay within the 10-minute window is possible. API tokens are unscoped — they inherit full user role privileges. Rate limiting covers only magic-link and verify endpoints; SPARQL, copilot, commands, and token creation have no limits. Setup endpoint lacks auth guard (narrow first-run window). Federation inbox HTTP Signature verification is adequate.

**Assembly:** All findings merged into `S01-FINDINGS.md` with standardized format per finding: severity, OWASP category, affected files, exploit scenario, localhost mitigation notes, and remediation guidance.

## Verification

All 7 slice-level checks pass:

| # | Check | Result |
|---|-------|--------|
| 1 | `test -f S01-FINDINGS.md` | ✅ pass |
| 2 | `grep -c "^### F-"` returns ≥ 5 | ✅ pass (20) |
| 3 | `grep -c "Severity:"` matches finding count | ✅ pass (20 = 20) |
| 4 | `grep -q "## A01"` — A01 section exists | ✅ pass |
| 5 | `grep -q "## A03"` — A03 section exists | ✅ pass |
| 6 | `grep -q "## A07"` — A07 section exists | ✅ pass |
| 7 | `grep -q "SPARQL Injection Classification"` — table exists | ✅ pass |

## Requirements Advanced

- SEC-01 through SEC-05 — re-validated M002 security hardening; identified gaps in SPARQL input validation, rate limiting coverage, and cookie configuration documentation

## Requirements Validated

- none (this slice produces findings, not fixes)

## New Requirements Surfaced

- none (findings tracked in S01-FINDINGS.md; remediation requirements will be scoped from the complete M042 report in S03)

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Found 33 SPARQL modules instead of the 29 estimated — the IRI interpolation pattern search (`f".*<\{"`) caught 4 additional modules (browser/favorites.py, browser/events.py, copilot/service.py, federation/service.py) that keyword-only search missed
- Produced 20 findings instead of the estimated ≥ 5 — the systematic router scan revealed more access control and auth nuances than anticipated
- Setup endpoint (`POST /api/setup/configure-instance`) discovered without auth guard — not in the original plan but material for A01

## Known Limitations

- This is an analysis-only slice — no code was modified, no vulnerabilities were fixed
- SPARQL injection analysis is based on static code reading, not dynamic testing with a running instance
- The assessment assumes the code as currently committed — any in-flight branches or uncommitted changes are not covered

## Follow-ups

- S03 will consume S01-FINDINGS.md as input for the final assembled report
- Remediation milestone should prioritize: (1) `_validate_iri()` on views/apps/VFS mount, (2) auth on 6 apps endpoints, (3) favorites stored injection, (4) escape function consolidation, (5) magic link single-use, (6) API token scoping

## Files Created/Modified

- `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` — 33-module SPARQL injection classification with exploit scenarios and defense analysis
- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md` — Complete findings document: 20 findings across A01 (5), A03 (6), A07 (9) with severity, exploit scenarios, affected files, remediation

## Forward Intelligence

### What the next slice should know
- S01-FINDINGS.md contains 20 findings in a standardized format — S03 can directly incorporate the A01/A03/A07 sections into the final report
- The SPARQL Injection Classification Summary table and Non-SPARQL Injection Assessment table are ready for inclusion as-is
- Severity ratings are anchored to cloud deployment with federation — S03 should use the same baseline for S02 findings

### What's fragile
- The 33-module count depends on the current codebase — any new module with f-string SPARQL construction should be added to the classification
- Three `_sparql_escape` implementations with different coverage — any fix to one should consolidate all three

### Authoritative diagnostics
- `S01-FINDINGS.md` "Summary — Findings by Severity" table — the definitive severity breakdown
- T01-SPARQL-TRIAGE.md classification table — the definitive per-module SPARQL injection risk rating

### What assumptions changed
- Plan estimated 29 SPARQL modules — actual count is 33 (IRI interpolation pattern caught modules the keyword search missed)
- Plan estimated ≥ 5 findings — actual count is 20 (systematic auth scan was more productive than expected)
