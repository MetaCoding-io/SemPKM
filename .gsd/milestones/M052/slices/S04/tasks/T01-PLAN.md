---
estimated_steps: 19
estimated_files: 1
skills_used: []
---

# T01: Add accent bar to form section headers and tighten help text spacing

## Description

Add visual prominence to form section headers (`.form-group-summary`) and tighten the spacing on help text (`.field-help`). Both are CSS-only edits in `workspace.css`.

## Steps

1. Read `frontend/static/css/workspace.css` around line 2788 to see the current `.form-group-summary` rules.
2. Add `border-left: 3px solid var(--color-primary)` to `.form-group-summary`.
3. Add `background: var(--color-surface-raised)` and increase font size to `0.88rem`.
4. Add subtle `border-radius: 4px` for polish.
5. Read `.field-help` around line 2656. Reduce `margin-bottom` from `6px` to `3px`. Reduce `line-height` from `1.45` to `1.35`.
6. Verify with grep that the accent bar and spacing changes are present.

## Must-Haves

- [ ] `.form-group-summary` has `border-left` with `--color-primary`
- [ ] `.form-group-summary` has `background: var(--color-surface-raised)`
- [ ] `.field-help` `margin-bottom` is 3px or less
- [ ] `.field-help` `line-height` is 1.35 or less
- [ ] Zero hardcoded hex values in the edited rules

## Verification

- `rg 'border-left.*primary' frontend/static/css/workspace.css | grep -q form-group-summary` exits 0
- `rg 'surface-raised' frontend/static/css/workspace.css | grep -q form-group-summary` exits 0
- `rg 'margin-bottom.*3px' frontend/static/css/workspace.css | grep -q field-help` exits 0

## Inputs

- ``frontend/static/css/workspace.css` — current form-group-summary (line ~2788) and field-help (line ~2656) rules`

## Expected Output

- ``frontend/static/css/workspace.css` — updated .form-group-summary with accent bar + background, updated .field-help with tighter spacing`

## Verification

rg 'border-left.*primary' frontend/static/css/workspace.css | grep -q form-group-summary && rg 'surface-raised' frontend/static/css/workspace.css | grep -q form-group-summary && rg 'margin-bottom.*3px' frontend/static/css/workspace.css | grep -q field-help
