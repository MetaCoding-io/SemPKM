---
id: T03
parent: S02
milestone: M041
provides:
  - Jinja2 Template Hygiene section of S02-FRONTEND-FINDINGS.md
  - htmx Consistency section of S02-FRONTEND-FINDINGS.md
key_files:
  - .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md
key_decisions: []
patterns_established:
  - "Importer template duplication measurement: diff line counts between Notion/Obsidian partials quantify shared-template extraction ROI"
observability_surfaces:
  - "Detection commands in each finding block — re-run to verify finding status"
duration: 20m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Jinja2 template hygiene and htmx consistency audit

**Audited 18,323 LOC across 165 Jinja2 templates, producing 8 findings across 2 dimensions covering template logic density, partial reuse, URL hardcoding, htmx swap/trigger consistency, and importer duplication.**

## What Happened

Ran systematic pattern-based detection across all `backend/app/templates/` files covering:

1. **Jinja2 Template Hygiene** (4 findings):
   - TPL-01: 23 templates >200 LOC with zero partial extraction (Medium)
   - TPL-02: 7 namespace() hacks + 10 .append() side-effects — computation logic that belongs in Python view functions (High)
   - TPL-03: Notion/Obsidian importers share 9 near-duplicate template files (~800 LOC of duplication) (Medium)
   - TPL-04: Zero url_for() usage — all 349 URLs are hardcoded strings (Medium)

2. **htmx Consistency** (4 findings):
   - HTMX-01: 88% innerHTML swap usage is consistent but undocumented as a convention (Low)
   - HTMX-02: 14 unique trigger patterns with inconsistent debounce (200ms vs 300ms), redundant lazy-load mechanisms (revealed vs intersect), and ad-hoc custom event names (Medium)
   - HTMX-03: guide.html and docs_page.html contain 81 near-identical htmx button blocks that could be a loop (Low)
   - HTMX-04: No hx-put or hx-patch usage — all mutations via hx-post (Low, informational)

The highest-impact finding is TPL-02: template-level computation using namespace() workarounds and .append() side-effects. These patterns are untestable and fragile — the object_read.html template has 45 logic statements in 284 lines performing property filtering, path comparison, and source attribution that should be precomputed in the view function.

## Verification

- `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → exists ✅
- `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → 21 (need ≥5) ✅
- `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` → 21 (need ≥12) ✅
- Logic-heavy templates with namespace() examples → documented ✅
- htmx swap/trigger patterns cataloged → documented ✅
- Hardcoded URL count (349) vs url_for count (0) → documented ✅

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 2 | `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 (returns 21, ≥5) | ✅ pass | <1s |
| 3 | `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 (returns 21, ≥12) | ✅ pass | <1s |
| 4 | `grep -q "namespace()" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 5 | `grep -q "innerHTML.*230" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |
| 6 | `grep -q "Zero url_for" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` | 0 | ✅ pass | <1s |

## Diagnostics

Each finding in the output document includes a "Detection command" block that can be re-run at any time to verify the finding still applies. For example:
- `rg "namespace\(" backend/app/templates/ -n` — should return 7 matches for template-level computation
- `rg "\.append\(" backend/app/templates/ -n` — should return 10 matches for side-effect list building
- `rg "url_for" backend/app/templates/ --count` — should return empty (0 usage)
- `rg 'hx-trigger="([^"]*)"' backend/app/templates/ -or '$1' | sed 's/.*://' | sort | uniq -c | sort -rn` — shows trigger distribution

## Deviations

Added the Notion/Obsidian importer duplication finding (TPL-03) beyond the plan's scope. The plan asked for partial reuse analysis and these 9 near-duplicate template pairs were the most concrete instance of missing reuse.

## Known Issues

None.

## Files Created/Modified

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — appended Jinja2 Template Hygiene section (4 findings: TPL-01 through TPL-04) and htmx Consistency section (4 findings: HTMX-01 through HTMX-04), updated header with template stats
