---
id: T03
parent: S04
milestone: M020
provides:
  - Chapter 38 user guide documenting Outlook Calendar Sync with Azure AD setup, field mapping tables, recurrence matrix, and troubleshooting
  - README TOC entry, glossary entry, 3 appendix A env var rows, navigation chain (Ch 37 → Ch 38 → Appendix A)
key_files:
  - docs/guide/38-outlook-calendar-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/37-todoist-sync.md
key_decisions: []
patterns_established:
  - "Chapter 38 follows Chapter 36 (Google Calendar) structural template — same section order adapted for Outlook-specific concepts (Azure AD vs Google Cloud, delta queries vs syncToken, structured recurrence vs RRULE)"
observability_surfaces:
  - none (documentation-only task)
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Write Chapter 38 user guide and update README, glossary, appendix, navigation

**Added Chapter 38 (Outlook Calendar Sync) user guide with Azure AD setup, 18-combination recurrence matrix, showAs/sensitivity/response status mapping tables, and updated README TOC, glossary, appendix A env vars, and navigation chain**

## What Happened

Wrote `docs/guide/38-outlook-calendar-sync.md` (~380 lines) following Chapter 36's structure with Outlook-specific content. Key sections: Azure AD app registration (step-by-step Azure Portal instructions with redirect URI), field mapping tables covering all source mappings from `field_mapper.py` (showAs 5-value enum, sensitivity→visibility, response status 6→4 mapping, recurrence 6 pattern types × 3 range types with relative index mapping), RSVP push-back with reverse mapping table, delta query incremental sync, HTML body conversion via markdownify, and troubleshooting (expired client secret, 410 Gone recovery, rate limiting).

Updated four surrounding docs: README TOC (line after Ch 37), glossary (alphabetical insertion before "Todoist Sync"), appendix A (3 `OUTLOOK_*` env var rows), and Ch 37 navigation footer (now points to Ch 38 instead of Appendix A).

The htmx prefix audit found 16 matches for non-URL `hx-` attributes (`hx-target`, `hx-swap`, `hx-indicator`, `hx-confirm`) which are purely client-side directives. The meaningful check — URL-bearing attributes (`hx-get`, `hx-post`, etc.) bypassing the proxy — returned 0 violations.

## Verification

All 8 task-level verification checks pass. All slice-level checks relevant to T03 pass. Mock selftest (T01) still passes 13/13.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/38-outlook-calendar-sync.md` | 0 | ✅ pass | <1s |
| 2 | `grep "38.*Outlook" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 3 | `grep "Outlook Calendar Sync" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 4 | `grep -c "OUTLOOK_" docs/guide/appendix-a-environment-variables.md` → 3 | 0 | ✅ pass | <1s |
| 5 | `grep "Chapter 38" docs/guide/37-todoist-sync.md` | 0 | ✅ pass | <1s |
| 6 | `grep "Chapter 37" docs/guide/38-outlook-calendar-sync.md` | 0 | ✅ pass | <1s |
| 7 | `grep "Appendix A" docs/guide/38-outlook-calendar-sync.md` | 0 | ✅ pass | <1s |
| 8 | `grep -rn "hx-(get\|post\|put\|delete\|patch)" apps/outlook-calendar/ \| grep -v "/app/outlook-calendar/" \| wc -l` → 0 | 0 | ✅ pass | <1s |
| 9 | `python3 e2e/mock-outlook-api/server.py --selftest` → 13/13 | 0 | ✅ pass | 1s |

## Diagnostics

Documentation-only task — no runtime signals. Verify docs with the grep commands above or by reading the files directly.

## Deviations

The htmx prefix audit as specified (`grep -rn "hx-" ... | grep -v "/app/outlook-calendar/"`) returns 16 results because non-URL htmx attributes like `hx-target="#connect-content"` and `hx-swap="innerHTML"` don't contain the proxy prefix (and don't need to — they're page-internal selectors). The meaningful audit checking only URL-bearing attributes (`hx-get`, `hx-post`, etc.) returns 0 violations.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/38-outlook-calendar-sync.md` — new Chapter 38 user guide (~380 lines)
- `docs/guide/README.md` — added TOC entry for Chapter 38
- `docs/guide/appendix-d-glossary.md` — added "Outlook Calendar Sync" glossary entry
- `docs/guide/appendix-a-environment-variables.md` — added 3 `OUTLOOK_*` env var rows
- `docs/guide/37-todoist-sync.md` — updated navigation footer to point to Chapter 38
- `.gsd/milestones/M020/slices/S04/tasks/T03-PLAN.md` — added Observability Impact section
