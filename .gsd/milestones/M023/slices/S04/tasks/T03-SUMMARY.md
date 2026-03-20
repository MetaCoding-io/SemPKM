---
id: T03
parent: S04
milestone: M023
provides:
  - User guide Chapter 36 documenting Jira sync for end users
  - Cross-reference updates across README TOC, glossary, appendix-a, and navigation chain
key_files:
  - docs/guide/36-jira-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/35-github-sync.md
key_decisions:
  - Added App-Specific Variables section to appendix-a for GITHUB_API_URL and JIRA_API_URL (was missing)
patterns_established:
  - Sync app chapters follow the same structural template — future sync app docs (Ch 37+) should clone Ch 36's section order
observability_surfaces:
  - none (documentation-only task)
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Write user guide Chapter 36 and update cross-references

**Wrote Chapter 36 (Jira Sync) user guide with field mapping tables, statusCategory explanation, ADF conversion notes, and updated all cross-references (README TOC, glossary, appendix-a, navigation chain)**

## What Happened

Wrote `docs/guide/36-jira-sync.md` (383 lines) following Chapter 35's structure but covering Jira-specific concepts. The chapter includes: prerequisites (Jira Cloud + API token + site URL), 3-field connection flow, project selection, JQL filter with examples, sync configuration, complete field mapping table, status mapping table (3 statusCategory.key values), priority mapping table (all 8 Jira priority names), statusCategory explanation paragraph, assignee resolution via accountId, ADF conversion notes with full supported node type list, push sync section (title/description/priority only — no status transitions per D237), Epic→Milestone mapping, issue links (Blocks→dependsOn with inward-only dedup), and troubleshooting.

Updated 4 supporting files: README.md TOC (added Ch 36 entry), glossary (3 entries: Atlassian Document Format, Jira Sync, statusCategory), appendix-a (added App-Specific Variables section with GITHUB_API_URL and JIRA_API_URL), and Ch 35 navigation footer (Next→Ch 36 instead of Appendix A).

## Verification

All 9 task-level verification commands pass. All slice-level verification checks pass — this is the final task in S04, completing the slice.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/36-jira-sync.md` | 0 | ✅ pass | <1s |
| 2 | `grep "36.*Jira" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 3 | `grep -ci "jira sync" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass (4 matches) | <1s |
| 4 | `grep -ci "statusCategory" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass (2 matches) | <1s |
| 5 | `grep -ci "atlassian document format" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass (1 match) | <1s |
| 6 | `grep "JIRA_API_URL" docs/guide/appendix-a-environment-variables.md` | 0 | ✅ pass | <1s |
| 7 | `grep "Chapter 36" docs/guide/35-github-sync.md` | 0 | ✅ pass | <1s |
| 8 | `grep "Appendix A" docs/guide/36-jira-sync.md` | 0 | ✅ pass | <1s |
| 9 | `grep "Chapter 35" docs/guide/36-jira-sync.md` | 0 | ✅ pass | <1s |
| 10 | `python3 e2e/mock-jira-api/server.py --selftest` | 0 | ✅ pass (12/12) | <1s |

## Diagnostics

Documentation-only task — no runtime diagnostics. Cross-references can be verified with grep commands above. Broken links would manifest as 404s in any docs-serving tool.

## Deviations

- Added `GITHUB_API_URL` to appendix-a alongside `JIRA_API_URL` in a new "App-Specific Variables" section. The existing appendix had no entry for GITHUB_API_URL despite Ch 35's "See Also" section referencing it. This provides a proper home for both env vars.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/36-jira-sync.md` — new Chapter 36 (383 lines) covering Jira sync end-to-end
- `docs/guide/README.md` — added Ch 36 entry to TOC
- `docs/guide/appendix-d-glossary.md` — added 3 entries (ADF, Jira Sync, statusCategory)
- `docs/guide/appendix-a-environment-variables.md` — added App-Specific Variables section with GITHUB_API_URL and JIRA_API_URL
- `docs/guide/35-github-sync.md` — updated navigation footer Next link to Ch 36
