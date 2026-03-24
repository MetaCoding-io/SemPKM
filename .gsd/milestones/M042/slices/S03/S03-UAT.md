# S03: Design, Crypto, SSRF & Final Report Assembly — UAT

**Milestone:** M042
**Written:** 2026-03-23

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This is an analysis-only milestone — the deliverable is a documentation artifact (`M042-SECURITY-FINDINGS.md`), not runtime code. Verification is structural (sections present, findings counted, format consistency) and content-quality (actionable findings with exploit scenarios).

## Preconditions

- File `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md` exists on disk
- No running services needed — this is a static document review

## Smoke Test

Open `M042-SECURITY-FINDINGS.md` and confirm the Executive Summary section exists with a severity distribution table showing 44 total findings across 4 severity levels.

```bash
head -30 .gsd/milestones/M042/M042-SECURITY-FINDINGS.md
# Expected: Title, date, scope, framework reference, severity table with High/Medium/Low/Info counts summing to 44
```

## Test Cases

### 1. All 10 OWASP Categories Present

1. Run: `grep "^## A0" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** 10 lines, one for each of A01 through A10, in order

### 2. Finding Count and Completeness

1. Run: `grep -c "^### F-" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** 44
3. Run: `grep "^### F-" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md | head -5`
4. **Expected:** F-001 through F-005 with descriptive titles
5. Run: `grep "^### F-" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md | tail -5`
6. **Expected:** F-040 through F-044 with descriptive titles

### 3. Every Finding Has Severity Annotation

1. Run: `grep -c "Severity:" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** 44 (matches finding count exactly)
3. Run: `grep "Severity:" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md | sort | uniq -c | sort -rn`
4. **Expected:** Four severity levels — High (9), Medium (14), Low (13), Info (8) — summing to 44

### 4. Every Finding Has Required Fields

1. Pick 3 findings at random (e.g., F-006, F-021, F-043) and read each one
2. **Expected:** Each finding contains all of: Severity, OWASP Category, Affected Files, Exploit Scenario (or Description), Remediation guidance
3. Run: `grep -c "OWASP Category:" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
4. **Expected:** 44

### 5. SPARQL Injection Classification Table Present

1. Run: `grep -A2 "SPARQL Injection Classification" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** Section heading followed by introductory text
3. Run: `grep -c "confirmed-exploitable\|likely-exploitable\|safe" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
4. **Expected:** ≥ 33 (one classification per module)

### 6. Prioritized Top 10 Summary

1. Run: `grep -A1 "## Prioritized Top 10" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** Section heading present
3. Scan the section for: finding references (F-NNN), effort estimates (hours), and priority ordering
4. **Expected:** At least 10 findings listed with effort estimates. Top items should be the High-severity findings (F-006, F-007, F-008, F-021, F-028, F-029, F-031, F-032, F-043).

### 7. Backend Hardening Section Completeness

1. Run: `grep -A1 "## Backend Hardening" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** Section heading present
3. Check for subsections covering: Secret Management, Session Lifecycle, API Token Management, Debug/Shell Endpoint Exposure, Federation Authentication, File Upload Handling
4. **Expected:** All 6 subsections present with cross-references to relevant finding numbers

### 8. Infrastructure Section Completeness

1. Run: `grep -A1 "## Infrastructure" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** Section heading present
3. Check for subsections covering: nginx Configuration, Docker Security, Deployment Hardening
4. **Expected:** All 3 subsections present

### 9. CDN Dependency Inventory Appendix

1. Run: `grep -A2 "CDN Dependency" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** Section heading present
3. Scan for a table listing CDN-loaded libraries with columns for library name, version, and SRI status
4. **Expected:** At least 8 CDN dependencies listed (FullCalendar, Leaflet, MarkerCluster, DOMPurify, etc.)

### 10. S01 and S02 Findings Correctly Incorporated

1. Run: `grep "F-001\|F-006\|F-012\|F-020" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
2. **Expected:** All 4 S01 finding references present (A01, A03, A07 boundaries)
3. Run: `grep "F-021\|F-031\|F-035\|F-037" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md`
4. **Expected:** All 4 S02 finding references present (A05, A06, A08, A09 boundaries)

## Edge Cases

### No Source Code Modified

1. Run: `git diff --name-only HEAD` (or check working tree)
2. **Expected:** Only `.gsd/` files modified. Zero changes to `backend/`, `frontend/`, `e2e/`, `models/`, or any other source directory.

### Finding Number Uniqueness

1. Run: `grep "^### F-" .gsd/milestones/M042/M042-SECURITY-FINDINGS.md | sort | uniq -d`
2. **Expected:** Empty output — no duplicate finding numbers

### Severity Distribution Matches Executive Summary

1. Extract the severity table from the Executive Summary
2. Count High/Medium/Low/Info findings by grepping `**Severity:** High` etc.
3. **Expected:** Counts match the Executive Summary table exactly

## Failure Signals

- Any OWASP category (A01–A10) missing from the report
- Finding count < 44 or severity annotation count < 44
- Any finding missing one of: severity, OWASP category, affected files, or remediation
- SPARQL injection classification table missing or listing fewer than 33 modules
- Prioritized Top 10 section missing or lacking effort estimates
- Backend Hardening or Infrastructure section missing subsections
- Duplicate finding numbers
- Source code files modified

## Requirements Proved By This UAT

- SEC-01 through SEC-05 (re-validates M002 security hardening and identifies gaps) — the report documents all identified gaps with structured remediation guidance

## Not Proven By This UAT

- Remediation effectiveness — fixing the findings is a separate future milestone
- Runtime exploit verification — the audit is static analysis, not penetration testing
- Third-party dependency CVE specifics — F-034 identifies the gap in automated scanning but does not run a CVE scan

## Notes for Tester

- The report is ~1190 lines. Skim the Executive Summary and Top 10 first for the high-level picture.
- Severity ratings assume cloud deployment with federation enabled. For localhost-only deployments, effective severity is lower for network-facing findings (SSRF, CORS, session issues).
- The SPARQL injection classification is static analysis — "confirmed-exploitable" means the data flow from HTTP request to unescaped f-string was traced, not that a working exploit was demonstrated.
- The report is designed to be the input for scoping a remediation milestone. Each finding's remediation section should be specific enough to create a task from directly.
