---
id: T03
parent: S04
milestone: M022
provides:
  - Chapter 40 user guide documenting Asana Sync with field mapping walkthrough
  - README TOC entry, glossary entry, appendix A env vars, navigation chain update
key_files:
  - docs/guide/40-asana-sync.md
  - docs/guide/README.md
  - docs/guide/appendix-d-glossary.md
  - docs/guide/appendix-a-environment-variables.md
  - docs/guide/39-caldav-calendar-sync.md
key_decisions:
  - Structured Chapter 40 around the 3 status modes as the distinctive content — completed_only, custom_field, section-based — since no prior sync chapter covers configurable field mapping
patterns_established:
  - User guide sync chapter pattern: prerequisites → installing → connecting (auth methods) → selection → field discovery → field mapping → sync config → manual sync → field mapping reference tables → troubleshooting → see also → nav footer
observability_surfaces:
  - none (documentation-only task)
duration: 15m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T03: Write Chapter 40 user guide and update README/glossary/appendix/nav-chain

**Created Chapter 40 (Asana Sync) user guide with 3 status mapping modes, field mapping reference tables, and updated README/glossary/appendix/nav-chain across 5 files.**

## What Happened

Wrote the Chapter 40 user guide (351 lines) following the structure and tone of the CalDAV Calendar Sync chapter (Ch 39). The chapter covers all Asana Sync features from the authoritative source code:

- **Two auth methods**: OAuth 2.0 (with Asana Developer Console setup instructions) and Personal Access Token
- **Project selection**: workspace-grouped checkboxes
- **Field discovery**: scanning selected projects for enum/number custom fields and sections
- **Three status mapping modes**: completed_only (simplest), custom_field (enum dropdown values), section-based (board columns) — each with pull and push behavior documented
- **Priority mapping**: optional enum field mapping with reverse mapping for bidirectional sync
- **Story points**: optional number field selection
- **Sync configuration**: pull-only vs bidirectional direction, 4 poll interval options
- **Field mapping reference tables**: Core Properties (13 rows with Asana field → SemPKM property + transform + direction) and Status Modes (3 rows with mode → source → pull/push behavior)
- **Subtask nesting**: up to 5 levels via dcterms:isPartOf hierarchy
- **Troubleshooting**: rate limiting, missing fields, expired tokens, status mapping issues

Updated 4 cross-reference files: README TOC line 40, glossary "Asana Sync" entry (alphabetically between API Token and App Contribution), appendix A env vars (ASANA_API_URL and ASANA_TOKEN_URL after OUTLOOK entries), and Ch 39 nav footer pointing to Ch 40.

## Verification

All 7 task-level checks passed:
- Chapter 40 file exists (351 lines)
- 17 occurrences of status mode keywords (completed_only/custom_field/section)
- README has "40-asana-sync" entry
- Glossary has "Asana Sync" entry
- Appendix A has ASANA_API_URL and ASANA_TOKEN_URL rows
- Ch 39 nav footer points to Chapter 40
- Ch 40 nav footer points to Appendix A

All slice-level checks passed:
- Mock selftest: 14 passed, 0 failed
- Docker compose config: valid
- asanaSync selectors: present
- E2E spec: exists with phases 0-6
- Ch 40: field mapping tables and 3 status modes present
- Cross-references: all present and correct

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f docs/guide/40-asana-sync.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "completed_only\|custom_field\|section" docs/guide/40-asana-sync.md` | 0 | ✅ pass (17) | <1s |
| 3 | `grep "40-asana-sync" docs/guide/README.md` | 0 | ✅ pass | <1s |
| 4 | `grep "Asana Sync" docs/guide/appendix-d-glossary.md` | 0 | ✅ pass | <1s |
| 5 | `grep "ASANA_API_URL" docs/guide/appendix-a-environment-variables.md` | 0 | ✅ pass | <1s |
| 6 | `grep "Chapter 40" docs/guide/39-caldav-calendar-sync.md` | 0 | ✅ pass | <1s |
| 7 | `grep "Appendix A" docs/guide/40-asana-sync.md` | 0 | ✅ pass | <1s |
| 8 | `python3 e2e/mock-asana-api/server.py --selftest` | 0 | ✅ pass (14/14) | 1s |
| 9 | `docker compose -f docker-compose.test.yml config --quiet` | 0 | ✅ pass | 1s |

## Diagnostics

Documentation-only task — no runtime diagnostics. Verify nav chain integrity with:
```
grep -n "Previous\|Next" docs/guide/39-caldav-calendar-sync.md docs/guide/40-asana-sync.md
```

## Deviations

Chapter is 351 lines instead of the planned 400-450 — the content is complete but more concise than the CalDAV chapter (368 lines) which has extensive server-specific notes and RSVP push-back details not applicable to Asana.

## Known Issues

None.

## Files Created/Modified

- `docs/guide/40-asana-sync.md` — new Chapter 40 user guide (351 lines)
- `docs/guide/README.md` — added line 40 entry to TOC
- `docs/guide/appendix-d-glossary.md` — added "Asana Sync" glossary entry
- `docs/guide/appendix-a-environment-variables.md` — added ASANA_API_URL and ASANA_TOKEN_URL rows
- `docs/guide/39-caldav-calendar-sync.md` — updated nav footer Next → Chapter 40
