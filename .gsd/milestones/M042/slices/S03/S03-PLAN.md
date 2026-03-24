# S03: Design, Crypto, SSRF & Final Report Assembly (A02, A04, A10 + Top 10)

**Goal:** Produce the complete `M042-SECURITY-FINDINGS.md` covering all 10 OWASP Top 10 2021 categories, backend/infrastructure hardening, and a prioritized Top 10 remediation summary.
**Demo:** The final report file exists at `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` with all OWASP categories A01–A10, 44 severity-rated findings, SPARQL injection classification table, CDN dependency inventory, and prioritized Top 10 summary — self-contained and ready for user review.

## Must-Haves

- All 10 OWASP categories (A01–A10) present with per-category assessment
- Every finding has: severity, OWASP category, exploit scenario, affected files, remediation guidance
- S01 findings (F-001–F-020) incorporated from `S01-FINDINGS.md`
- S02 findings (F-021–F-037) incorporated from `S02-FINDINGS.md`
- New findings (F-038–F-044) for A02, A04, A10 written from S03-RESEARCH.md
- Backend hardening section: secret management, session lifecycle, API tokens, debug endpoints, federation auth, file handling
- Infrastructure section: nginx config, Docker security, deployment hardening
- SPARQL injection classification summary table from S01
- Prioritized Top 10 findings with effort estimates
- CDN dependency inventory appendix from S02
- Executive summary with severity distribution
- No source code modifications — analysis-only artifact

## Verification

```bash
# File exists
test -f .gsd/milestones/M042/M042-SECURITY-FINDINGS.md

# All 10 OWASP categories present
grep -q "## A01" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A02" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A03" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A04" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A05" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A06" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A07" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A08" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A09" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "## A10" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md

# Finding count (~44)
COUNT=$(grep -c "^### F-" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md)
test "$COUNT" -ge 40

# Every finding has severity annotation
SEV=$(grep -c "Severity:" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md)
test "$SEV" -ge 40

# Structural sections present
grep -q "Top 10" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "SPARQL Injection Classification" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "Backend Hardening" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "Infrastructure" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "CDN Dependency" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
grep -q "Executive Summary" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
```

## Tasks

- [ ] **T01: Assemble complete M042-SECURITY-FINDINGS.md from S01, S02, and S03 research** `est:1h30m`
  - Why: This is the sole deliverable for both S03 and the entire M042 milestone — a self-contained security finding report covering all OWASP Top 10 categories with prioritized remediation guidance
  - Files: `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
  - Do: (1) Read S01-FINDINGS.md, S02-FINDINGS.md, and S03-RESEARCH.md as inputs. (2) Write the complete report with these sections in order: Executive Summary (severity distribution, coverage statement), OWASP A01–A10 (one `## A0N` section per category — incorporate S01 findings for A01/A03/A07, S02 findings for A05/A06/A08/A09, write new findings F-038–F-044 for A02/A04/A10 from S03-RESEARCH.md), Backend Hardening Assessment (cross-cutting: secret management, session lifecycle, API tokens, debug endpoints, federation auth, file handling — referencing relevant findings), Infrastructure Security Assessment (nginx headers, Docker config, deployment hardening — referencing relevant findings), SPARQL Injection Classification Summary (incorporate the 33-module table from S01's T01-SPARQL-TRIAGE.md), Prioritized Top 10 Findings (rank by severity × exploitability × blast radius, include effort estimates per the research's candidate list), CDN Dependency Inventory appendix (from S02). (3) Ensure every finding has: finding number (F-NNN), severity, OWASP category, affected files, exploit scenario, remediation guidance. (4) Run all verification commands from the slice plan.
  - Verify: All verification commands from slice plan pass — file exists, 10 OWASP categories present, ≥40 findings with severity annotations, structural sections present
  - Done when: `M042-SECURITY-FINDINGS.md` exists with all 10 OWASP categories, ~44 findings, backend/infrastructure hardening sections, SPARQL classification table, Top 10 summary, and CDN inventory — all verification grep checks pass

## Files Likely Touched

- `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
