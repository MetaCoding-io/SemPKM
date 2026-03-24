---
id: S02
parent: M042
milestone: M042
provides:
  - S02-FINDINGS.md — 17 security findings across OWASP A05 (Security Misconfiguration), A06 (Vulnerable Components), A08 (Data Integrity Failures), A09 (Logging & Monitoring Failures)
  - CDN dependency inventory table with version pin and SRI status for all CDN-loaded libraries
  - Severity summary table (5 High, 8 Medium, 4 Low) with per-category breakdown and top remediation priorities
consumes: []
key_decisions: []
duration: 55m
completed_at: 2026-03-23
---

# S02: Configuration, Infrastructure & Supply Chain Findings (A05, A06, A08, A09)

**Produced 17 severity-rated security findings across 4 OWASP categories with verified source file references, a complete CDN dependency inventory, and prioritized remediation guidance.**

## What This Slice Delivered

`S02-FINDINGS.md` contains structured findings for the four "operational security" OWASP categories — the ones about how the system is configured, what it depends on, how it handles external data, and what it logs. Every finding was verified against actual source files with line numbers before documenting.

### A05: Security Misconfiguration (F-021 – F-027, 7 findings)

The biggest gap is **F-021**: zero HTTP security headers across all three reverse proxy configs (nginx.conf, nginx.demo.conf, Caddyfile.cloud) — no CSP, X-Frame-Options, HSTS, X-Content-Type-Options, Referrer-Policy, or Permissions-Policy. Other findings: CORS double-header from nginx + FastAPI both emitting `Access-Control-Allow-Origin` (F-022), Docker containers running as root with no `security_opt`/`cap_drop` (F-023), `--reload` in production Dockerfile CMD (F-024), `detail=str(e)` leaking internal state in 6 exception handlers across 4 routers (F-025), hardcoded `SECRET_KEY` in demo compose (F-026), and unlimited upload body size on Obsidian endpoint (F-027).

**Deviation from research:** `vfs/mount_router.py` was listed as having `detail=str(e)` but grep confirmed zero occurrences — dropped from findings.

### A06: Vulnerable Components (F-031 – F-034, 4 findings)

Built a complete CDN dependency inventory: 25+ libraries across 3 CDN hosts. Key findings: **zero SRI attributes** across the entire codebase (F-031, High), 3 completely unpinned CDN dependencies including DOMPurify — the XSS sanitizer (F-032, High), 7 always-CDN libraries not covered by the M029 vendor pipeline (F-033), and no automated CVE scanning for either Python or JavaScript dependency trees (F-034).

### A08: Data Integrity (F-035 – F-037, 3 findings)

Both ZIP import endpoints (Obsidian and Notion) call `zf.extractall()` with no size/count checks — zip-bomb DoS risk (F-035). Federation patches have no cryptographic signing (F-036) and no semantic content filtering beyond RDF parsing (F-037).

### A09: Logging & Monitoring (F-028 – F-030, 3 findings)

Magic link tokens logged in plaintext at INFO level (F-028, High) — an attacker with log access gets valid auth tokens. Zero security event audit trail across the entire backend (F-029, High). Failed authentication attempts not logged (F-030).

### Severity Distribution

| Severity | Count | Finding IDs |
|----------|-------|-------------|
| High | 5 | F-021, F-028, F-029, F-031, F-032 |
| Medium | 8 | F-022, F-023, F-026, F-030, F-033, F-034, F-035, F-036 |
| Low | 4 | F-024, F-025, F-027, F-037 |

## What S03 Needs to Know

- S02-FINDINGS.md is ready for assembly. Finding numbers F-021 through F-037 continue from S01's F-001–F-020 range.
- The severity summary table at the end of S02-FINDINGS.md includes a "Top Remediation Priorities" section — S03 should use this when building the final report's prioritized Top 10.
- The CDN dependency inventory table in F-031 is the most detailed artifact — it maps every CDN-loaded library to its template file, version pin status, and SRI status. S03 should reference it rather than rebuilding.
- No source code was modified — this is analysis-only.

## Verification

All 7 slice-level checks passed:

| # | Check | Result |
|---|-------|--------|
| 1 | `test -f S02-FINDINGS.md` | ✅ |
| 2 | Finding count ≥ 12 | ✅ (17) |
| 3 | A05 section present | ✅ |
| 4 | A06 section present | ✅ |
| 5 | A08 section present | ✅ |
| 6 | A09 section present | ✅ |
| 7 | Summary section present | ✅ |
