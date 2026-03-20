---
id: T03
parent: S04
milestone: M025
provides:
  - User guide Chapter 38 documenting the hosted demo deployment
  - DEMO_MODE entry in environment variable reference (Appendix A)
  - Demo Mode and Hosted Demo glossary entries (Appendix D)
  - Complete navigation chain Ch 37 → Ch 38 → Appendix A
key_files:
  - docs/guide/38-hosted-demo.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/templates/guide.html
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/37-monday-sync.md
key_decisions: []
patterns_established:
  - Three-file sync rule (README.md, index.html, guide.html) followed for adding guide chapters
observability_surfaces:
  - "grep -c '38-hosted-demo' docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html — all three must return 1+"
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: User guide Chapter 38 and documentation updates

**Created Chapter 38 (Hosted Demo Instance) with full deployment documentation, updated all three navigation files, added DEMO_MODE to Appendix A, and added Demo Mode/Hosted Demo glossary entries**

## What Happened

Created `docs/guide/38-hosted-demo.md` (~250 lines) covering the full hosted demo deployment: DEMO_MODE configuration, docker-compose.demo.yml usage, read-only nginx enforcement, seed script operation (4 models, 74+ objects, cross-model edges), the 7-step Driver.js tour, demo dashboard, CTA banner customization, Caddy SSL termination, periodic reset via cron, health monitoring, quick start, and troubleshooting.

Updated all six supporting files per the plan:
1. **Ch 37 nav footer** — "Next" now points to Ch 38 instead of Appendix A
2. **README.md** — added Ch 38 TOC entry after Ch 37
3. **index.html** — added sidebar `<li>` with `data-file="38-hosted-demo.md"`
4. **guide.html** — added htmx `<button>` with `globe` Lucide icon between Monday.com and Appendix A
5. **Appendix A** — added `DEMO_MODE` row to the environment variable table (between POSTHOG_HOST and DEBUG, matching existing table ordering)
6. **Appendix D** — added "Demo Mode" (after "Deal") and "Hosted Demo" (after "GitHub Sync") glossary entries in alphabetical order

## Verification

All 10 task-level verification checks pass:
- Chapter file exists, TOC/sidebar/button entries present
- DEMO_MODE documented in Appendix A
- Both glossary entries present
- Navigation chain intact: Ch 37 → Ch 38 → Appendix A (forward and back links)

All 11 slice-level verification checks pass (Playwright E2E requires live stack, verified by T02).

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/38-hosted-demo.md` | 0 | ✅ pass | <1s |
| 2 | `grep "38.*Hosted Demo" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 3 | `grep "38-hosted-demo" docs/guide/index.html` | 0 | ✅ pass | <1s |
| 4 | `grep "38-hosted-demo" backend/app/templates/guide.html` | 0 | ✅ pass | <1s |
| 5 | `grep "DEMO_MODE" docs/guide/appendix-a-environment-variables.md` | 0 | ✅ pass | <1s |
| 6 | `grep -i "demo mode" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 7 | `grep -i "hosted demo" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 8 | `grep "Chapter 38" docs/guide/37-monday-sync.md` | 0 | ✅ pass | <1s |
| 9 | `grep "Appendix A" docs/guide/38-hosted-demo.md` | 0 | ✅ pass | <1s |
| 10 | `grep "Chapter 37" docs/guide/38-hosted-demo.md` | 0 | ✅ pass | <1s |
| 11 | `bash -n scripts/reset-demo.sh` | 0 | ✅ pass | <1s |
| 12 | `bash -n scripts/deploy-demo.sh` | 0 | ✅ pass | <1s |
| 13 | `grep -q "set -euo pipefail" scripts/reset-demo.sh` | 0 | ✅ pass | <1s |

## Diagnostics

Documentation-only task — no runtime signals. Verify documentation integrity with:
- `grep -c "38-hosted-demo" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all must return 1+
- Navigation chain: `grep "Chapter 38" docs/guide/37-monday-sync.md` and `grep "Chapter 37\|Appendix A" docs/guide/38-hosted-demo.md`

## Deviations

The plan specified inserting DEMO_MODE "after DATABASE_URL, before DEBUG" alphabetically, but the existing table is not alphabetically ordered (DATABASE_URL is followed by SECRET_KEY, etc.). Inserted DEMO_MODE between POSTHOG_HOST and DEBUG, keeping it near where DEBUG is and maintaining local ordering consistency.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/38-hosted-demo.md` — new: Chapter 38 documenting hosted demo deployment (~250 lines)
- `docs/guide/README.md` — added Ch 38 TOC entry in Part VIII
- `docs/guide/index.html` — added Ch 38 sidebar `<li>` entry
- `backend/app/templates/guide.html` — added Ch 38 htmx button with globe icon
- `docs/guide/appendix-a-environment-variables.md` — added DEMO_MODE row to env var table
- `docs/guide/appendix-d-glossary.md` — added "Demo Mode" and "Hosted Demo" glossary entries
- `docs/guide/37-monday-sync.md` — updated nav footer Next link from Appendix A to Ch 38
- `.gsd/milestones/M025/slices/S04/tasks/T03-PLAN.md` — added Observability Impact section (pre-flight fix)
- `.gsd/milestones/M025/slices/S04/S04-PLAN.md` — marked T03 as done
