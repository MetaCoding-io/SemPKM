---
estimated_steps: 3
estimated_files: 2
---

# T02: Milestone-level end-to-end verification

**Slice:** S07 — Workflow Builder UI & Final Integration
**Milestone:** M006

## Description

Verify all 12 M006 success criteria against live Docker behavior. Some criteria (PROV-O, explorer grouping, VFS scope) were completed in S01/S02 and need regression checks. This task also includes a Docker restart persistence test and conflict marker scan. Results documented in S07-UAT.md.

## Steps

1. Start Docker stack (`docker compose up -d`), wait for readiness. Walk through each of the 12 success criteria in the browser, documenting pass/fail for each.
2. Test persistence: `docker compose down && docker compose up -d`, verify dashboards and workflows survive restart.
3. Write S07-UAT.md with results. Mark S07 complete in roadmap. Run `grep -rn "^<<<<<<< "` conflict marker check.

## Must-Haves

- [ ] All 12 M006 success criteria documented as passing in S07-UAT.md
- [ ] Docker restart persistence verified
- [ ] Zero conflict markers in committed files
- [ ] S07 marked `[x]` in M006-ROADMAP.md

## Verification

- S07-UAT.md documents all 12 criteria as "pass"
- `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — zero results
- M006-ROADMAP.md shows `[x]` for S07

## Observability Impact

This task is verification-only — it doesn't change runtime behavior. The output artifact `S07-UAT.md` is the primary observability surface: a structured pass/fail matrix of all 12 M006 success criteria. A future agent can read S07-UAT.md to see what was verified, when, and whether any criteria had caveats. The conflict marker grep and Docker restart test results are also documented there.

## Inputs

- T01 output — all builder/explorer/delete code working
- M006-ROADMAP.md — 12 success criteria to verify
- Prior slice summaries — know what was built and where to check

## Expected Output

- `.gsd/milestones/M006/slices/S07/S07-UAT.md` — milestone verification results
- `.gsd/milestones/M006/M006-ROADMAP.md` — S07 marked complete
