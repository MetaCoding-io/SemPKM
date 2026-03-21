---
id: T02
parent: S05
milestone: M029
provides:
  - QUIC/HTTP/3 deferral decision (D277) in DECISIONS.md
  - 9 PERF requirements (PERF-02 through PERF-10) registered in REQUIREMENTS.md with validated status
key_files:
  - .gsd/DECISIONS.md
  - .gsd/REQUIREMENTS.md
key_decisions:
  - D277 — QUIC/HTTP/3 deferred for self-hosted Docker deployment
patterns_established:
  - none
observability_surfaces:
  - DECISIONS.md: grep 'QUIC' .gsd/DECISIONS.md to verify D277 entry
  - REQUIREMENTS.md: grep -c 'PERF-' .gsd/REQUIREMENTS.md returns 20 (10 long-form + 10 summary table rows)
duration: 10m
verification_result: passed
completed_at: 2026-03-20T21:05:00Z
blocker_discovered: false
---

# T02: Record QUIC/HTTP/3 decision and register PERF-02 through PERF-10 requirements

**Recorded QUIC/HTTP/3 deferral as D277 and registered 9 PERF requirements (PERF-02 through PERF-10) in REQUIREMENTS.md with validated status and slice-specific evidence proofs including Lighthouse score 80.**

## What Happened

Recorded the QUIC/HTTP/3 deferral decision via `gsd_save_decision` — assigned D277. The rationale covers nginx:stable-alpine lacking HTTP/3 module, minimal QUIC benefit for self-hosted single-user tool, and Caddy as an existing alternative for the demo instance (D246).

Then registered all 9 PERF requirements directly in REQUIREMENTS.md (both long-form entries in the Validated section and summary table rows). Each requirement has status=validated with specific validation proofs referencing the originating slice:

- **PERF-02, PERF-03** → M029/S01 (vendor bundling, build pipeline)
- **PERF-04, PERF-05** → M029/S02 (gzip compression, immutable caching)
- **PERF-06** → M029/S03 (CSS code-splitting)
- **PERF-07** → M029/S05 with actual Lighthouse score: median 80 (range 74-81), FCP 984ms, LCP 2585ms, TBT 15ms, CLS 0.094
- **PERF-08, PERF-09** → M029/S04 (timing middleware, conditional-get middleware)
- **PERF-10** → M029/S05 referencing decision D277

Updated the Coverage Summary from 222 to 231 validated requirements, adding "9 from M029" to the breakdown.

Also applied pre-flight observability fixes: added a diagnostic verification step to S05-PLAN.md and an Observability Impact section to T02-PLAN.md.

## Verification

- `grep 'QUIC' .gsd/DECISIONS.md` — D277 entry present with full rationale ✅
- `grep -c 'PERF-' .gsd/REQUIREMENTS.md` — returns 20 (PERF-01 from M002 + 9 new × 2 appearances each) ✅
- `grep 'PERF-07' .gsd/REQUIREMENTS.md` — shows "Lighthouse desktop 80 (range 74-81)" ✅
- `grep 'PERF-10' .gsd/REQUIREMENTS.md` — shows "D277 QUIC/HTTP/3 defer" ✅
- `grep 'PERF-02' .gsd/REQUIREMENTS.md` — shows long-form and summary table entries ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep 'QUIC' .gsd/DECISIONS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c 'PERF-' .gsd/REQUIREMENTS.md` (≥10) | 0 | ✅ pass (20) | <1s |
| 3 | `grep 'PERF-07' .gsd/REQUIREMENTS.md` | 0 | ✅ pass | <1s |
| 4 | `grep 'PERF-10' .gsd/REQUIREMENTS.md` | 0 | ✅ pass | <1s |
| 5 | `grep 'PERF-02' .gsd/REQUIREMENTS.md` | 0 | ✅ pass | <1s |
| SV1 | `ls .gsd/milestones/M029/slices/S05/lighthouse-after.report.json` | 0 | ✅ pass (T01) | <1s |
| SV2 | `grep 'PERF-02' .gsd/REQUIREMENTS.md` | 0 | ✅ pass | <1s |
| SV3 | `grep 'QUIC' .gsd/DECISIONS.md` | 0 | ✅ pass | <1s |
| SV4 | `ls .gsd/milestones/M029/slices/S05/S05-SUMMARY.md` | 2 | ❌ fail (T03 scope) | <1s |
| SV5 | `python3 ... assert '/browser' in finalDisplayedUrl` | 0 | ✅ pass | <1s |
| SV6 | `grep -c 'PERF-' .gsd/REQUIREMENTS.md` (≥10) | 0 | ✅ pass (20) | <1s |

## Diagnostics

- **DECISIONS.md**: `grep 'D277' .gsd/DECISIONS.md` to find the QUIC/HTTP/3 decision row.
- **REQUIREMENTS.md**: `grep 'PERF-0[2-9]\|PERF-10' .gsd/REQUIREMENTS.md` to list all 9 new PERF requirements. Check long-form entries exist with `grep -c '### PERF-' .gsd/REQUIREMENTS.md` (should be 10 including PERF-01).
- **Coverage Summary accuracy**: The validated count was updated from 222 to 231 (+9 from M029). Verify with `grep 'Validated:' .gsd/REQUIREMENTS.md`.

## Deviations

- `gsd_update_requirement` only works for existing requirements, so PERF-02 through PERF-10 were added by direct file edit to REQUIREMENTS.md rather than via the GSD tool. Both long-form entries and summary table rows were added manually.

## Known Issues

None.

## Files Created/Modified

- `.gsd/DECISIONS.md` — D277 added via gsd_save_decision (QUIC/HTTP/3 deferral)
- `.gsd/REQUIREMENTS.md` — 9 long-form PERF-02 through PERF-10 entries added to Validated section, 9 summary table rows added, Coverage Summary updated from 222 to 231
- `.gsd/milestones/M029/slices/S05/S05-PLAN.md` — Pre-flight: added diagnostic verification step; marked T02 done
- `.gsd/milestones/M029/slices/S05/tasks/T02-PLAN.md` — Pre-flight: added Observability Impact section
