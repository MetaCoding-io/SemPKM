---
estimated_steps: 30
estimated_files: 1
skills_used: []
---

# T01: Fix calendar dark mode nav icon visibility via FC6 custom properties

## Description

The FullCalendar 6.1.17 prev/next nav buttons use an icon font (`fcicons`) where the icon color is inherited from the button's `color` property. In dark mode, FC6's `.fc .fc-button-primary { color: var(--fc-button-text-color) }` wins the specificity battle over the direct `color` override in `[data-theme="dark"] .fc .fc-button`. The fix is to set FC6's custom properties (`--fc-button-text-color`, `--fc-button-bg-color`, etc.) in the existing dark mode block, then simplify or remove the now-redundant direct-property overrides.

## Steps

1. Read `frontend/static/css/views.css` lines 1376–1412 (the dark mode FC block).
2. Add FC6 button custom properties to the `[data-theme="dark"] .fc` block (lines ~1376):
   ```css
   --fc-button-text-color: var(--color-text);
   --fc-button-bg-color: var(--color-bg-secondary);
   --fc-button-border-color: var(--color-border);
   --fc-button-hover-bg-color: var(--color-bg-hover);
   --fc-button-hover-border-color: var(--color-border);
   --fc-button-active-bg-color: var(--color-accent);
   --fc-button-active-border-color: var(--color-accent);
   --fc-button-active-text-color: var(--color-on-accent);
   ```
3. Remove the now-redundant direct-property override blocks:
   - `[data-theme="dark"] .fc .fc-button` (lines ~1388–1392) — custom properties handle bg, border, color
   - `[data-theme="dark"] .fc .fc-button:hover` (lines ~1394–1396) — custom property handles hover bg
   - `[data-theme="dark"] .fc .fc-button-active` (lines ~1398–1402) — custom property handles active state
4. Verify with grep that the custom properties are set and the direct overrides are gone.

## Must-Haves

- [ ] `--fc-button-text-color` set in dark mode `.fc` block
- [ ] `--fc-button-bg-color` set in dark mode `.fc` block
- [ ] `--fc-button-active-bg-color` set in dark mode `.fc` block
- [ ] No remaining `[data-theme="dark"] .fc .fc-button {` direct-property block (custom properties replace it)

## Verification

- `grep -c 'fc-button-text-color' frontend/static/css/views.css` returns >= 1
- `grep -c 'fc-button-bg-color' frontend/static/css/views.css` returns >= 1
- `grep -c 'fc-button-active-text-color' frontend/static/css/views.css` returns >= 1
- The `[data-theme="dark"] .fc` block contains all 8 button custom properties

## Inputs

- ``frontend/static/css/views.css` — existing dark mode FullCalendar override block at lines 1376–1412`

## Expected Output

- ``frontend/static/css/views.css` — dark mode block updated with FC6 button custom properties, redundant direct-property overrides removed`

## Verification

grep -c 'fc-button-text-color' frontend/static/css/views.css && grep -c 'fc-button-bg-color' frontend/static/css/views.css && grep -c 'fc-button-active-text-color' frontend/static/css/views.css
