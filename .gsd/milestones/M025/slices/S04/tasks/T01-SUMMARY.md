---
id: T01
parent: S04
milestone: M025
provides:
  - Caddyfile for automatic HTTPS reverse proxy to demo Docker stack
  - reset-demo.sh for periodic clean-state restoration via cron
  - DNS/SSL setup instructions and cron documentation in deploy-demo.sh
key_files:
  - Caddyfile
  - scripts/reset-demo.sh
  - scripts/deploy-demo.sh
key_decisions:
  - Health wait loop in reset script has 120s timeout with explicit failure message (vs. deploy-demo.sh which waits indefinitely)
patterns_established:
  - Reset scripts use 5-phase pattern: down -v → up --build → health wait → seed → verify
observability_surfaces:
  - Reset script stdout labels each step for cron log debugging
  - Cron log at /var/log/sempkm-demo-reset.log captures all output
  - Health endpoint at /api/health used by both scripts and uptime monitoring
duration: 10m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Caddy reverse proxy config, reset script, and deploy script update

**Created Caddyfile with automatic HTTPS reverse proxy, reset-demo.sh for periodic clean-state cron resets, and added DNS/SSL setup + cron + uptime monitoring documentation to deploy-demo.sh**

## What Happened

Created three deployment infrastructure artifacts for the hosted demo:

1. **Caddyfile** at repository root — configures Caddy as a host-level reverse proxy to Docker's nginx on port 3902. Uses `demo.sempkm.app` as a placeholder domain with a comment to change it. Caddy handles TLS automatically via Let's Encrypt. Adds `X-Robots-Tag: noindex, nofollow` header to prevent search engine indexing.

2. **scripts/reset-demo.sh** — executable bash script for periodic clean-state restoration. Runs 5 phases: tear down with volumes (`down -v`), rebuild (`up -d --build`), health wait loop with 120s timeout, re-seed demo data, and verify. Matches deploy-demo.sh's style with clear step labels. The timeout improvement over deploy-demo.sh (which waits indefinitely) ensures cron runs don't hang.

3. **scripts/deploy-demo.sh** updated — added a DNS/SSL setup instruction block at the top (Caddy install steps, domain config, systemctl reload) and two documentation sections at the bottom: cron setup for 6-hourly resets, and health check endpoint for uptime monitoring services.

## Verification

All 7 task-level checks pass:
- Both scripts pass `bash -n` syntax validation
- Caddyfile contains domain placeholder, reverse_proxy, and X-Robots-Tag
- reset-demo.sh is executable
- deploy-demo.sh has 14 matches for Caddy/SSL/HTTPS keywords (need ≥3)
- deploy-demo.sh contains cron and reset-demo references
- reset-demo.sh has strict error handling (`set -euo pipefail`)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `bash -n scripts/reset-demo.sh` | 0 | ✅ pass | <1s |
| 2 | `bash -n scripts/deploy-demo.sh` | 0 | ✅ pass | <1s |
| 3 | `cat Caddyfile` (contains domain, reverse_proxy, X-Robots-Tag) | 0 | ✅ pass | <1s |
| 4 | `test -x scripts/reset-demo.sh` | 0 | ✅ pass | <1s |
| 5 | `grep -c "caddy\|Caddy\|SSL\|HTTPS" scripts/deploy-demo.sh` → 14 | 0 | ✅ pass | <1s |
| 6 | `grep "cron\|reset-demo" scripts/deploy-demo.sh` | 0 | ✅ pass | <1s |
| 7 | `grep -q "set -euo pipefail" scripts/reset-demo.sh` | 0 | ✅ pass | <1s |

### Slice-level checks (T01 scope):

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `bash -n scripts/reset-demo.sh` | 0 | ✅ pass | <1s |
| 2 | `bash -n scripts/deploy-demo.sh` | 0 | ✅ pass | <1s |
| 3 | `cat Caddyfile` — has domain, reverse_proxy | 0 | ✅ pass | <1s |
| 4 | `grep -q "set -euo pipefail" scripts/reset-demo.sh` | 0 | ✅ pass | <1s |

Remaining slice checks (T02/T03 scope): E2E Playwright test, docs navigation, appendix entries — not yet applicable.

## Diagnostics

- **Caddyfile:** `cat Caddyfile` to inspect config; domain placeholder visible at top
- **Reset script logging:** When run via cron, output goes to `/var/log/sempkm-demo-reset.log` — each step is labeled `[1/5]` through `[5/5]` with timestamps
- **Health check:** `curl -sf http://localhost:3902/api/health` returns 200 when stack is healthy
- **Failure mode:** reset-demo.sh exits non-zero on any step failure (strict bash mode) with a specific error message for health timeout

## Deviations

- Added a 120s health wait timeout to reset-demo.sh (not in original deploy-demo.sh pattern which waits indefinitely). This prevents cron jobs from hanging if the stack fails to start.
- Added Caddy install instructions from the official Cloudsmith repository (more complete than just `apt install caddy` which may not be in default repos).

## Known Issues

None.

## Files Created/Modified

- `Caddyfile` — new: Caddy reverse proxy config with automatic HTTPS, domain placeholder, noindex header
- `scripts/reset-demo.sh` — new: executable 5-phase reset script for cron (down → build → health → seed → verify)
- `scripts/deploy-demo.sh` — modified: added DNS/SSL setup instructions block and cron/health monitoring documentation sections
- `.gsd/milestones/M025/slices/S04/S04-PLAN.md` — updated: added Observability/Diagnostics section, diagnostic verification step, marked T01 done
- `.gsd/milestones/M025/slices/S04/tasks/T01-PLAN.md` — updated: added Observability Impact section
