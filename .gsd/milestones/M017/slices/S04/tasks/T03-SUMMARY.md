---
id: T03
parent: S04
milestone: M017
provides:
  - Chapter 35 user guide documenting GitHub Sync app with field mapping tables, status mapping, PR-to-issue linking
  - README TOC entry for Chapter 35
  - Glossary entry for GitHub Sync
  - Navigation chain: Ch 34 → Ch 35 → Appendix A
key_files:
  - docs/guide/35-github-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/34-linear-sync.md
key_decisions: []
patterns_established:
  - GitHub Sync chapter mirrors Linear Sync chapter structure with GitHub-specific adaptations (PAT-only auth, repo selection, simpler status model, PR linking section)
observability_surfaces:
  - File existence and heading count verifiable via grep
  - Navigation chain integrity verifiable by checking tail lines of Ch 34, Ch 35, and Appendix A
duration: 8m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T03: Chapter 35 user guide + glossary and navigation updates

**Created Chapter 35 (GitHub Sync) user guide with 33 section headings, field mapping tables from M017-RESEARCH.md, PR-to-issue linking docs, and updated README TOC, glossary, and navigation chain (Ch 34 → Ch 35 → Appendix A).**

## What Happened

Cloned the Chapter 34 (Linear Sync) structure and adapted every section for GitHub specifics:

- **Auth:** PAT-only (no OAuth per D206), with guidance for both classic and fine-grained tokens
- **Selection:** Repository multi-select checkboxes instead of Linear's team selection
- **Field mapping:** 12-field table from M017-RESEARCH.md with transform and direction columns
- **Status mapping:** Dedicated sub-table documenting open/closed × state_reason → bpkm:taskStatus (todo/done/cancelled)
- **Assignee resolution:** Documents the email → login → create fallback chain (GitHub-specific)
- **Push sync:** Documents title + status only support, loop prevention via lastSyncedAt
- **PR-to-Issue Linking:** New section (no equivalent in Ch 34) explaining timeline API cross-references, bpkm:dependsOn edges, same-repo limitation
- **Rate limiting:** New troubleshooting subsection for GitHub's 5000 req/hr limit

Updated README.md TOC, added glossary entry in alphabetical position, and rewired Ch 34's "Next" link from Appendix A to Ch 35.

## Verification

All must-haves verified:
- Chapter 35 exists with 33 section headings (≥10 required) ✅
- Field mapping table matches M017-RESEARCH.md (12 fields with transform and direction) ✅
- Status mapping sub-table documents open/closed/state_reason → bpkm:taskStatus ✅
- PR-to-Issue Linking section explains timeline API, bpkm:dependsOn edges, same-repo scope ✅
- README TOC includes Ch 35 entry ✅
- Glossary has GitHub Sync entry ✅
- Navigation chain: Ch 33 → Ch 34 → Ch 35 → Appendix A ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/35-github-sync.md && echo "exists"` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^##" docs/guide/35-github-sync.md` | 0 | ✅ pass (33) | <1s |
| 3 | `grep "35-github-sync" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 4 | `grep -i "github sync" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 5 | `grep "35-github-sync" docs/guide/34-linear-sync.md` | 0 | ✅ pass | <1s |
| 6 | `python3 e2e/mock-github-api/server.py --selftest` | 0 | ✅ pass | <1s |

## Diagnostics

Documentation-only task. Inspect by:
- `grep -c "^##" docs/guide/35-github-sync.md` — heading count
- `tail -1 docs/guide/34-linear-sync.md` — Ch 34 → Ch 35 link
- `tail -1 docs/guide/35-github-sync.md` — Ch 35 → Appendix A link

## Deviations

- Added "Rate limiting" troubleshooting subsection and "Assignee Resolution" subsection not in the plan — these are GitHub-specific topics with no Ch 34 equivalent that users need documented.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/35-github-sync.md` — Complete Chapter 35 user guide (~300 lines, 33 headings) with field mapping tables, status mapping, PR-to-issue linking, troubleshooting
- `docs/guide/README.md` — Added Ch 35 TOC entry after Ch 34
- `docs/guide/appendix-d-glossary.md` — Added GitHub Sync glossary entry in alphabetical position
- `docs/guide/34-linear-sync.md` — Updated "Next" nav link from Appendix A to Chapter 35
- `.gsd/milestones/M017/slices/S04/tasks/T03-PLAN.md` — Added Observability Impact section (pre-flight fix)
