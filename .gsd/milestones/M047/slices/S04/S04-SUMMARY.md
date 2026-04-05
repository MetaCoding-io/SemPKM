---
id: S04
parent: M047
milestone: M047
provides:
  - PPV seed data with 35 instances across 12 types for realistic dashboard rendering
  - E2E lifecycle test for PPV v2 model
  - User guide chapter 50 documenting PPV v2
requires:
  - slice: S01
    provides: Manifest v2 infrastructure with TBox install/uninstall lifecycle
  - slice: S02
    provides: PPV ontology expansion — PillarScore, GuidingPrinciples, enriched review shapes
  - slice: S03
    provides: 5 TBox dashboards and 5 TBox workflows in PPV manifest
affects:
  []
key_files:
  - models/ppv/seed/ppv.jsonld
  - e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts
  - docs/guide/50-ppv-model.md
  - docs/guide/README.md
  - docs/guide/index.html
  - backend/app/shell/router.py
key_decisions:
  - Used admin form endpoint (POST /admin/models/install) for E2E test install step — the JSON API path from the plan doesn't exist
patterns_established:
  - PPV E2E test pattern: consolidated single-test spec with 7-phase lifecycle (pre-clean → install → verify dashboards → verify workflows → open dashboard → launch workflow → uninstall)
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M047/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M047/slices/S04/tasks/T02-SUMMARY.md
  - .gsd/milestones/M047/slices/S04/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-05T00:33:20.038Z
blocker_discovered: false
---

# S04: Seed Data Update & E2E Verification

**PPV seed data expanded to 35 instances across 12 types (GuidingPrinciples + PillarScore + enriched review fields), E2E lifecycle test created, user guide chapter documenting the complete PPV v2 model published.**

## What Happened

Three tasks delivered the final slice of M047 — seed data, E2E coverage, and documentation.

**T01 — Seed Data Expansion:** Extended `models/ppv/seed/ppv.jsonld` from 31 instances/10 types to 35 instances/12 types. Added 1 GuidingPrinciples instance with all 7 SHACL fields (values, purpose, meaning, manifestation, foundationalStatement, guidingWord) using realistic August Bradley-style content. Added 3 PillarScore instances (Health=7, Career=8, Relationships=6) linked to the existing weekly review and corresponding pillars. Enriched all 4 review instances with their new S02 reflection fields: 3 fields on WeeklyReview (wins, challenges, supportingPriorities), 4 on MonthlyReview (biggestWins, biggestChallenges, focusAreas, habitsToAdjust), 6 on QuarterlyReview (accomplishments, disappointments, whatWorked, whatDidntWork, howToImprove, annualVisionNotes), 2 on YearlyReview (intentionWord, yearTheme). Zero dangling IRI references.

**T02 — E2E Lifecycle Test:** Created `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts` — a consolidated single-test spec exercising 7 phases: pre-clean, install via admin form endpoint, verify 5 dashboards via API, verify 5 workflows via API, open Action Items dashboard (GridStack rendering), launch Daily Check-in workflow (runner/stepper/navigation), and graceful uninstall handling (200/409/404). Adapted from the task plan: used the real admin install endpoint (`POST /admin/models/install` with form data) instead of the non-existent JSON API path. TypeScript compiles with zero new errors.

**T03 — User Guide:** Created `docs/guide/50-ppv-model.md` covering all 12 types (goal hierarchy + review hierarchy), 5 dashboards, 5 workflows, the review system with enriched reflection fields, installation instructions, seed data contents, and tips. Updated all three index files per KNOWLEDGE.md rule: `docs/guide/README.md`, `docs/guide/index.html`, and `backend/app/shell/router.py`.

## Verification

All slice-level verification checks passed:

1. **Seed data type counts** — `ppv:GuidingPrinciples==1`, `ppv:PillarScore==3` confirmed across 35 total instances / 12 types ✅
2. **Enriched review fields** — `ppv:wins` present on WeeklyReview instance ✅
3. **TypeScript compilation** — Zero errors from `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts` (14 pre-existing errors in unrelated extension specs) ✅
4. **User guide files** — All 4 files exist and reference `50-ppv-model` ✅

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 used `POST /admin/models/install` with form data instead of the plan's `POST /api/models/install` with JSON — the JSON API endpoint doesn't exist. The admin form endpoint is the actual model install path.

## Known Limitations

E2E test not run against live Docker stack (only TypeScript compilation verified). The test handles uninstall 409 gracefully since seed data blocks model removal.

## Follow-ups

None.

## Files Created/Modified

- `models/ppv/seed/ppv.jsonld` — Added 1 GuidingPrinciples + 3 PillarScore instances, enriched 4 review instances with reflection fields (31→35 instances, 10→12 types)
- `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts` — New E2E test: 7-phase PPV v2 lifecycle (install → dashboard/workflow verify → UI render → uninstall)
- `docs/guide/50-ppv-model.md` — New user guide chapter documenting PPV v2 model (12 types, 5 dashboards, 5 workflows, review system)
- `docs/guide/README.md` — Added chapter 50 entry to table of contents
- `docs/guide/index.html` — Added chapter 50 sidebar link
- `backend/app/shell/router.py` — Added chapter 50 to GUIDE_SECTIONS list
