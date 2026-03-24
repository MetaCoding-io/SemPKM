---
id: S02
milestone: M041
title: "Frontend Code Quality Audit"
status: done
started: 2026-03-23
completed: 2026-03-23
tasks_completed: 3
tasks_total: 3
---

# S02: Frontend Code Quality Audit — Summary

**Delivered:** A structured findings document (`S02-FRONTEND-FINDINGS.md`) covering 57,405 LOC of frontend code (18,587 JS / 20,495 CSS / 18,323 Jinja2 templates) across 5 quality dimensions with 21 severity-rated, effort-estimated findings — each anchored to specific files and accompanied by reproducible detection commands.

## What This Slice Produced

The primary deliverable is `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — the frontend half of the M041 code quality audit. S03 will consume this alongside S01's backend findings to assemble the final M041-RECOMMENDATIONS.md report.

## Findings by Dimension

### JS Structure & Global State (4 findings)
- **JS-01 (High):** workspace.js is a 5,409-line monolith with 170 functions handling 12+ concerns — the single largest frontend technical debt item
- **JS-02 (Medium):** 222 `window.*` global state assignments (124 in workspace.js alone) — cross-IIFE communication at scale creates invisible dependency graph
- **JS-03 (Low):** 25 IIFE files vs 3 ESM files — documented architectural choice, not a defect, but blocks incremental modernization
- **JS-04 (Low):** 126 `console.*` calls in production code across 19 files

### DOM & Event Patterns (4 findings)
- **DOM-01 (High):** 188 unmatched addEventListener calls (208 add / 20 remove) — memory leak risk in dynamically created dockview panels
- **DOM-02 (Medium):** 48 setTimeout with only 9 clearTimeout; 1 setInterval (federation.js) with no clearInterval and no dedup guard
- **DOM-03 (High):** 67 of 131 fetch() calls (51%) missing `.catch()`, `response.ok` check, or both — network failures silently leave UI inconsistent
- **DOM-04 (Medium):** No centralized fetch wrapper — error handling duplicated ad hoc across 19 files

### CSS Architecture & Theming (5 findings)
- **CSS-01 (Medium):** 84 standalone hardcoded hex colors bypass theme system (out of 499 total — 360 are acceptable var() fallbacks, 55 are theme.css definitions)
- **CSS-02 (Medium):** 202 standalone hardcoded rgba() values — larger untokenized color surface than hex, needs `color-mix()` migration
- **CSS-03 (Low):** 61 `!important` declarations — 30 are necessary vendor overrides (driver.js), 31 are avoidable specificity issues
- **CSS-04 (Low):** 4 different responsive breakpoint values (600/640/768/800px) with no documented standard
- **CSS-05 (Low):** Repeated property patterns (flex+align-items+flex-shrink triplet ~130 times) suggest missing utility classes

### Jinja2 Template Hygiene (4 findings)
- **TPL-01 (Medium):** 23 templates >200 LOC with zero partial extraction
- **TPL-02 (High):** 7 namespace() hacks + 10 .append() side-effects — computation logic that belongs in Python view functions, untestable in templates
- **TPL-03 (Medium):** Notion/Obsidian importers share 9 near-duplicate template files (~800 LOC duplication)
- **TPL-04 (Medium):** Zero url_for() usage — all 349 URLs are hardcoded strings

### htmx Consistency (4 findings)
- **HTMX-01 (Low):** 88% innerHTML swap is consistent but undocumented
- **HTMX-02 (Medium):** 14 unique trigger patterns with inconsistent debounce (200ms vs 300ms) and redundant lazy-load mechanisms
- **HTMX-03 (Low):** 81 near-identical htmx button blocks in guide.html/docs_page.html
- **HTMX-04 (Low):** No hx-put/hx-patch usage — all mutations via hx-post (informational)

## Severity Distribution

| Severity | Count | Key Items |
|----------|-------|-----------|
| High | 4 | workspace.js monolith, unmatched listeners, fetch error handling, template computation logic |
| Medium | 10 | global state, timers, fetch wrapper, hardcoded colors, rgba values, large templates, importer duplication, hardcoded URLs, htmx triggers |
| Low | 7 | module patterns, console.log, !important, breakpoints, CSS utilities, htmx swap convention, htmx button duplication, REST semantics |

## Highest-Impact Items for S03 Top 10

These frontend findings compete for the consolidated Top 10:
1. **DOM-03: 51% of fetch calls lack error handling** — runtime user impact, mechanical fix
2. **JS-01: workspace.js 5,409-line monolith** — largest maintainability burden
3. **DOM-01: 188 unmatched event listeners** — memory leak risk in SPA-like workspace
4. **TPL-02: computation logic in templates** — untestable, fragile, belongs in view functions

## Analysis Patterns Established

- **Three-tier hex classification:** theme definitions / var() fallbacks / standalone hardcoded — only the third tier is a real finding. Without this separation, the color problem appears 6× worse.
- **Importer duplication measurement:** diff line counts between Notion/Obsidian partials quantify extraction ROI.
- **Detection command documentation:** every finding includes the exact rg/fd/grep command for reproduction, making findings re-verifiable after fixes.

## Verification

All three slice-level checks pass:
- `test -f S02-FRONTEND-FINDINGS.md` → exists ✓
- `grep -c "^### " S02-FRONTEND-FINDINGS.md` → 21 (≥5 required) ✓
- `grep -c "Severity:" S02-FRONTEND-FINDINGS.md` → 21 (≥12 required) ✓

## What S03 Needs to Know

- S02's findings file is at `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md`
- 21 findings across 5 dimensions, each with category/severity/effort/file references
- The 4 High-severity items are the strongest candidates for the Top 10 consolidated list
- CSS variable adoption is already at 89.7% — the remaining 84 standalone hex colors + 202 rgba values are the gap
- The workspace.js monolith (JS-01) and fetch error handling gap (DOM-03) are likely the two highest-impact frontend recommendations
