---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T01: JavaScript structure, global state, and DOM/event audit

**Slice:** S02 — Frontend Code Quality Audit
**Milestone:** M041

## Description

Audit JS file structure (IIFE monoliths, module boundaries, global state), DOM event patterns (listener leaks, timer cleanup), and error handling in fetch calls.

## Steps

1. `fd -e js . frontend/static/js/ | xargs wc -l | sort -rn` — rank all JS files by size.
2. For files >500 LOC, count functions and assess whether the IIFE contains multiple unrelated responsibilities.
3. `rg "window\.\w+ =" frontend/static/js/ -n --count` — catalog all global state assignments.
4. `rg "addEventListener" frontend/static/js/ -n --count` and `rg "removeEventListener" frontend/static/js/ -n --count` — quantify the listener imbalance per file.
5. `rg "setInterval|setTimeout" frontend/static/js/ -n` — find all timers. Check for matching clearInterval/clearTimeout.
6. `rg "fetch\(" frontend/static/js/ -A8 -n` — sample 10 fetch calls and check for missing error handling (.catch, try/catch, response.ok check).
7. Check for console.log/console.error left in production code: `rg "console\." frontend/static/js/ --count`.
8. Write JS Structure & Global State and DOM & Event Patterns sections to S02-FRONTEND-FINDINGS.md.

## Must-Haves

- [ ] All JS files >500 LOC identified with function counts
- [ ] Event listener imbalance quantified per file
- [ ] Fetch calls without error handling identified

## Verification

- `test -f .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md && grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 2

## Inputs

- `frontend/static/js/` — all JavaScript source files

## Expected Output

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — created with JS Structure and DOM/Event sections
