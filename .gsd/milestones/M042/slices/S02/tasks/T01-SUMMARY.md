---
id: T01
parent: S02
milestone: M042
provides:
  - S02-FINDINGS.md with A05 (Security Misconfiguration) and A09 (Logging & Monitoring) findings F-021 through F-030
key_files:
  - .gsd/milestones/M042/slices/S02/S02-FINDINGS.md
key_decisions: []
patterns_established: []
observability_surfaces:
  - none (analysis-only task, no runtime changes)
duration: 30m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T01: Document A05 (Security Misconfiguration) and A09 (Logging & Monitoring) findings

**Wrote 10 security findings (F-021–F-030) for OWASP A05 and A09 into S02-FINDINGS.md, all verified against actual source files with exact line numbers**

## What Happened

Verified each research finding against the actual source files before documenting. Key verifications:

- **A05 missing headers**: Confirmed zero security headers (`CSP`, `X-Frame-Options`, `HSTS`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `server_tokens off`) across all three proxy configs (`nginx.conf`, `nginx.demo.conf`, `Caddyfile.cloud`).
- **A05 CORS double-header**: Confirmed nginx adds `Access-Control-Allow-Origin: *` on lines 74, 96, 116, 122 of `nginx.conf`, while FastAPI CORSMiddleware (lines 633–649 of `main.py`) also adds its own header.
- **A05 Docker root**: Confirmed neither Dockerfile has a `USER` directive, and neither compose file has `security_opt`, `cap_drop`, or `read_only`.
- **A05 `--reload`**: Confirmed `backend/Dockerfile` line 36 CMD includes `--reload`.
- **A05 `detail=str(e)`**: Found 6 occurrences across 4 routers (auth, workflow, dashboard, task_templates). Research listed `vfs/mount_router.py` but it has no `detail=str(e)` — dropped from findings.
- **A05 demo secret**: Confirmed `docker-compose.demo.yml` line 40 `SECRET_KEY: demo-secret-key-not-for-production`.
- **A05 upload size**: Documented `client_max_body_size 0` on Obsidian upload endpoint.
- **A09 magic link logging**: Confirmed `logger.info("Magic link token for %s: %s", ...)` at lines 155 and 163 of `auth/router.py`.
- **A09 absent audit trail**: Searched backend for security event logging patterns — confirmed absence across all security-relevant operations.
- **A09 failed auth logging**: Confirmed verify endpoint (lines 182–186) returns 400 without logging.

## Verification

All four task-level checks pass. Slice-level checks: 3 of 7 pass (A05, A09, file exists); remaining 4 (A06, A08, finding count ≥12, summary table) are pending T02.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M042/slices/S02/S02-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c '^### F-' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md` (10, need ≥6) | 0 | ✅ pass | <1s |
| 3 | `grep -q '## A05:' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md` | 0 | ✅ pass | <1s |
| 4 | `grep -q '## A09:' .gsd/milestones/M042/slices/S02/S02-FINDINGS.md` | 0 | ✅ pass | <1s |

## Diagnostics

This is an analysis-only task — no runtime changes. The findings document at `.gsd/milestones/M042/slices/S02/S02-FINDINGS.md` can be inspected directly. T02 will append A06 and A08 sections plus the severity summary table.

## Deviations

- Research listed `backend/app/vfs/mount_router.py` as having `detail=str(e)`, but a grep of the actual file found zero occurrences. Dropped from the findings. The remaining 6 occurrences across 4 files are confirmed.
- Added F-027 (Obsidian upload `client_max_body_size 0`) which was mentioned in the research but not explicitly listed as a T01 finding — it's a clear A05 misconfiguration in `nginx.conf`.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M042/slices/S02/S02-FINDINGS.md` — Created with A05 (7 findings: F-021–F-027) and A09 (3 findings: F-028–F-030) sections. Placeholder comment for T02's A06/A08 sections.
- `.gsd/milestones/M042/slices/S02/S02-PLAN.md` — Marked T01 as complete
