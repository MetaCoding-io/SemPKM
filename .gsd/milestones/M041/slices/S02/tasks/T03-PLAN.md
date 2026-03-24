---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T03: Jinja2 template hygiene and htmx consistency audit

**Slice:** S02 — Frontend Code Quality Audit
**Milestone:** M041

## Description

Audit Jinja2 templates for logic density, partial reuse opportunities, and Python expression leakage. Audit htmx attribute patterns for consistency (trigger patterns, URL conventions, swap strategies).

## Steps

1. `fd -e html . backend/app/templates/ | xargs wc -l | sort -rn | head -20` — rank templates by size.
2. `rg "{% if|{% for|{% set|{% macro" backend/app/templates/ --count | sort -t: -k2 -rn | head -20` — find most logic-heavy templates.
3. For the top 5 logic-heavy templates, assess whether logic belongs in the Python view function instead.
4. `rg "{% include" backend/app/templates/ --count` — measure partial reuse. Look for templates >200 LOC with zero includes (candidate for extraction).
5. Check for hardcoded URLs: `rg 'href="/|action="/|hx-get="/|hx-post="/' backend/app/templates/ -n --count` vs `rg "url_for" backend/app/templates/ --count`.
6. htmx audit: `rg "hx-swap=" backend/app/templates/ -on` to catalog swap strategies. Check for consistency (innerHTML vs outerHTML vs none).
7. `rg "hx-trigger=" backend/app/templates/ -on` — audit trigger patterns. Check for non-standard or complex triggers.
8. Append Jinja2 Template Hygiene and htmx Consistency sections to S02-FRONTEND-FINDINGS.md.

## Must-Haves

- [ ] Most logic-heavy templates identified with specific examples of misplaced logic
- [ ] htmx swap/trigger patterns cataloged for consistency analysis
- [ ] Hardcoded URL count vs url_for count documented

## Verification

- `grep -c "^### " .gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` returns >= 5

## Inputs

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — append to existing findings doc
- `backend/app/templates/` — all Jinja2 template files

## Expected Output

- `.gsd/milestones/M041/S02-FRONTEND-FINDINGS.md` — complete with all 5 frontend dimension sections
