# S02: Frontend Code Quality Audit

**Goal:** Systematically audit 58k LOC of frontend code (JS, CSS, Jinja2 templates) across 5 quality dimensions using pattern-based detection, producing a structured findings document.
**Demo:** The user reads S02-FRONTEND-FINDINGS.md and sees categorized, severity-rated findings with file:line references and reproducible detection commands.

## Must-Haves

- Findings for all 5 frontend dimensions: JS structure & global state, CSS architecture & theming, Jinja2 template hygiene, DOM/event patterns, htmx consistency
- Every finding has: category, severity, effort, file:line reference
- Detection commands are documented for each finding category

## Verification

- `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md`
- `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 5 (5+ dimension sections)
- `grep -c "Severity:" .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 12 (12+ individual findings)

## Tasks

- [x] **T01: JavaScript structure, global state, and DOM/event audit** `est:45m`
  - Why: workspace.js at 5409 LOC is the highest-impact frontend finding. Event listener imbalance (197 add vs 20 remove) signals memory leak risk.
  - Files: `frontend/static/js/workspace.js`, all `frontend/static/js/*.js` files
  - Do: (1) `fd -e js . frontend/static/js/ | xargs wc -l | sort -rn` to rank JS files by size. (2) Count functions per file. (3) Identify IIFE vs module pattern usage. (4) `rg "window\." frontend/static/js/` to find global state. (5) `rg "addEventListener" --count` vs `rg "removeEventListener" --count` per file. (6) `rg "setInterval|setTimeout" frontend/static/js/` to find timer usage without cleanup. (7) Check for error handling in fetch calls — `rg "fetch\(" -A5` looking for missing .catch or try/catch. (8) Write "JS Structure & Global State" and "DOM & Event Patterns" sections to S02-FRONTEND-FINDINGS.md.
  - Verify: `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md && grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 2
  - Done when: JS Structure and DOM/Event sections exist with specific findings

- [x] **T02: CSS architecture and theme consistency audit** `est:35m`
  - Why: 201 hardcoded hex colors alongside 1205 var() references means the theming system is 85% adopted but inconsistently applied. CSS at 9203 lines may have significant duplication.
  - Files: `frontend/static/css/workspace.css`, all `frontend/static/css/*.css` files
  - Do: (1) `fd -e css . frontend/static/css/ | xargs wc -l | sort -rn` to rank CSS files. (2) `rg "#[0-9a-fA-F]{3,8}" frontend/static/css/ --count` to count hardcoded colors per file. (3) `rg "var(--" frontend/static/css/ --count` to count variable usage per file. (4) `rg "!important" frontend/static/css/ --count` to find specificity overrides. (5) Check selector complexity — look for selectors >3 levels deep. (6) Check for duplicate property blocks. (7) Check responsive breakpoints — `rg "@media" frontend/static/css/` for consistency. (8) Write "CSS Architecture & Theming" section.
  - Verify: `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 3
  - Done when: CSS Architecture section exists with specific findings including hardcoded color count and theming gap analysis

- [x] **T03: Jinja2 template hygiene and htmx consistency audit** `est:35m`
  - Why: 165 templates is a large surface. Logic-heavy templates and inconsistent htmx patterns increase maintenance cost.
  - Files: `backend/app/templates/**/*.html`
  - Do: (1) `fd -e html . backend/app/templates/ | xargs wc -l | sort -rn` to rank templates by size. (2) `rg "{% if|{% for|{% set|{% macro" backend/app/templates/ --count` to measure logic density per template. (3) Look for Python expressions in templates (`rg "\|int\b|\|float\b|\|round" backend/app/templates/`). (4) Check partial reuse — `rg "{% include" --count` vs inline duplication. (5) htmx audit: `rg "hx-post|hx-get|hx-put|hx-delete|hx-patch" backend/app/templates/ --count` for consistency. (6) Check for hardcoded URLs vs url_for. (7) `rg "hx-trigger" backend/app/templates/` to audit trigger patterns. (8) Write "Jinja2 Template Hygiene" and "htmx Consistency" sections.
  - Verify: `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 5
  - Done when: All 5 frontend dimension sections exist with specific, actionable findings

## Observability / Diagnostics

- **Detection reproducibility:** Every finding includes the exact `rg`/`fd`/`grep` command used to detect it — any agent can re-run to verify the finding still exists or has been resolved.
- **Findings staleness:** Re-running the detection commands after code changes validates which findings are still active; stale findings will produce lower counts or no matches.
- **Failure path:** If a detection command exits non-zero or returns empty, the finding section notes "0 matches — pattern may have changed" rather than silently omitting.

## Files Likely Touched

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` (created)
