# M042: Security Audit - OWASP Web Security & Backend Hardening

**Vision:** Produce a comprehensive, severity-rated security finding report covering all 10 OWASP Top 10 2021 categories plus backend/infrastructure hardening — giving the user a prioritized remediation roadmap with exploit scenarios, affected files, and effort estimates for each finding.

## Success Criteria

- The finding report (`M042-SECURITY-FINDINGS.md`) covers all OWASP Top 10 2021 categories (A01–A10) with per-category assessment
- Every finding has: OWASP category, severity (Critical/High/Medium/Low/Info), exploit scenario, affected files, and remediation guidance
- Backend hardening areas are assessed: secret management, session lifecycle, API token storage, debug/shell endpoint exposure, federation auth, file upload/ZIP handling
- Infrastructure security is assessed: nginx headers, Docker config, deployment hardening
- A prioritized Top 10 summary of the most critical findings exists with effort estimates
- SPARQL injection modules are classified as confirmed-exploitable, likely-exploitable, or safe with reasoning
- Severity ratings are anchored to cloud deployment with federation (the most exposed model)

## Key Risks / Unknowns

- SPARQL injection triage requires tracing 26 modules to determine which have user-controlled input reaching f-string query construction — this is the most time-intensive analysis
- Some findings require cross-referencing multiple files (auth middleware mount patterns, cookie settings, endpoint exposure) — easy to miss gaps with grep alone

## Proof Strategy

- SPARQL injection triage → retire in S01 by tracing the top 10 highest-risk modules' data flow from HTTP request to SPARQL query
- Cross-file auth gap detection → retire in S01 by systematic scan of router mounts vs. auth dependency injection

## Verification Classes

- Contract verification: `test -f M042-SECURITY-FINDINGS.md`; grep for all 10 OWASP categories A01–A10; grep for severity annotations; grep for Top 10 summary section
- Integration verification: none (analysis-only milestone)
- Operational verification: none (analysis-only milestone)
- UAT / human verification: user reviews the finding report for actionability and completeness before scoping remediation

## Milestone Definition of Done

This milestone is complete only when all are true:

- `M042-SECURITY-FINDINGS.md` exists with per-category OWASP assessment
- All 10 OWASP categories (A01–A10) are covered with at least a "reviewed, no findings" or specific findings
- Backend hardening section covers secret management, session lifecycle, API tokens, debug endpoints, federation auth, file handling
- Infrastructure section covers nginx, Docker, deployment configs
- Every finding has severity, OWASP mapping, exploit scenario, affected files, and remediation guidance
- Prioritized Top 10 most critical findings summary exists
- SPARQL injection modules are individually classified
- No source code was modified (analysis-only)

## Requirement Coverage

- Covers: SEC-01 through SEC-05 (re-validates M002 security hardening and identifies gaps)
- Partially covers: none
- Leaves for later: Remediation implementation (future milestone scoped from this report)
- Orphan risks: none — this milestone produces the finding report that creates requirements for the remediation milestone

## Slices

- [x] **S01: Injection, Access Control & Authentication Findings (A01, A03, A07)** `risk:high` `depends:[]`
  > After this: findings for the three highest-risk OWASP categories exist — SPARQL injection modules individually classified, broken access control gaps documented with exploit scenarios, authentication/session management weaknesses identified
- [x] **S02: Configuration, Infrastructure & Supply Chain Findings (A05, A06, A08, A09)** `risk:medium` `depends:[]`
  > After this: findings for security misconfiguration (headers, CORS, debug endpoints), vulnerable components (CDN SRI, dependency CVEs), data integrity (federation patches, ZIP handling), and logging gaps documented with affected files and remediation
- [x] **S03: Design, Crypto, SSRF & Final Report Assembly (A02, A04, A10 + Top 10)** `risk:low` `depends:[S01,S02]`
  > After this: the complete `M042-SECURITY-FINDINGS.md` exists with all OWASP categories covered, backend/infrastructure hardening assessed, every finding severity-rated with exploit scenarios, and a prioritized Top 10 summary — ready for user review and remediation scoping

## Boundary Map

### S01 → S03

Produces:
- `S01-FINDINGS.md` — structured findings for A01 (Broken Access Control), A03 (Injection), A07 (Auth Failures) with severity, OWASP mapping, exploit scenarios, affected files, remediation per finding
- SPARQL injection classification table: each of 26 modules rated as confirmed-exploitable / likely-exploitable / safe

Consumes:
- nothing (first slice, parallel-eligible with S02)

### S02 → S03

Produces:
- `S02-FINDINGS.md` — structured findings for A05 (Security Misconfiguration), A06 (Vulnerable Components), A08 (Data Integrity Failures), A09 (Logging & Monitoring Failures)
- CDN dependency inventory with SRI status
- nginx header gap analysis

Consumes:
- nothing (parallel-eligible with S01)

### S03 (consumes S01 + S02)

Produces:
- `M042-SECURITY-FINDINGS.md` — final assembled report covering all A01–A10 categories plus backend/infrastructure hardening, with prioritized Top 10 summary

Consumes:
- S01-FINDINGS.md (A01, A03, A07 findings)
- S02-FINDINGS.md (A05, A06, A08, A09 findings)
