---
status: resolved
trigger: "Investigate why card view borders are not distinctive enough in both dark and light mode."
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:00:00Z
---

## Current Focus

hypothesis: confirmed — card faces use only `box-shadow: var(--shadow)` with no border, and both light and dark shadow values are too subtle to provide visual separation from the surface behind the card
test: read theme.css token values, views.css card rules, and cards_view.html template
expecting: token values would reveal insufficient contrast between card surface and background
next_action: report findings (goal: find_root_cause_only)

## Symptoms

expected: Cards in card view should have clearly visible, distinctive borders or edges that separate them from the grid background
actual: Cards blend into the background — borders are either absent or too low-contrast to be visually distinctive in both light and dark mode
errors: none (visual/design issue)
reproduction: Open any Cards view in the browser in either light or dark mode
started: always present (structural/design issue, not a regression)

## Eliminated

- hypothesis: cards use `--color-border-subtle` which is known to be very faint
  evidence: card faces do not use border at all — they rely solely on box-shadow
  timestamp: 2026-02-23

## Evidence

- timestamp: 2026-02-23
  checked: views.css lines 715-727 (.flip-card-front, .flip-card-back)
  found: |
    .flip-card-front, .flip-card-back {
        background: var(--color-surface);
        box-shadow: var(--shadow);
        /* NO border property */
    }
  implication: Card faces in the grid have zero explicit border — they depend entirely on box-shadow for visual separation

- timestamp: 2026-02-23
  checked: views.css lines 763-775 (.card-focus-front, .card-focus-back — the focused/enlarged portal version)
  found: |
    .card-focus-front, .card-focus-back {
        background: var(--color-surface);
        box-shadow: var(--shadow-elevated);
        /* NO border property */
    }
  implication: Even the focused card modal uses only shadow — no border

- timestamp: 2026-02-23
  checked: theme.css :root (light mode) shadow tokens
  found: |
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
    --shadow-elevated: 0 4px 12px rgba(0, 0, 0, 0.15);
  implication: Light mode --shadow is extremely faint (8% black, 1px offset, 3px blur). This is barely perceptible on a white card (#ffffff) over a near-white background (#fafafa). The delta between --color-bg (#fafafa) and --color-surface (#ffffff) is only 5 luminosity points.

- timestamp: 2026-02-23
  checked: theme.css html[data-theme="dark"] shadow tokens
  found: |
    --shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    --shadow-elevated: 0 4px 12px rgba(0, 0, 0, 0.4);
  implication: Dark mode shadow is stronger (30% black) but the card surface (#282c34) over body background (#1e2127) is only 7 points of delta. The shadow offset of just 1px/3px at 30% opacity may not read clearly either.

- timestamp: 2026-02-23
  checked: theme.css dark mode border tokens
  found: |
    --color-border: #3e4452;      /* ~14 points above surface #282c34 */
    --color-border-subtle: #2c313a; /* only 2 points above surface — nearly invisible */
  implication: --color-border exists with reasonable contrast in dark mode but is never applied to card faces

- timestamp: 2026-02-23
  checked: theme.css light mode border tokens
  found: |
    --color-border: #e0e0e0;      /* medium-light gray */
    --color-border-subtle: #f0f0f0; /* very faint, nearly same as bg */
  implication: --color-border is available with moderate contrast but is never applied to card faces

- timestamp: 2026-02-23
  checked: style.css lines 94-101 (.card — the generic dashboard card)
  found: |
    .card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius);
        padding: 1.25rem;
        box-shadow: var(--shadow);
    }
  implication: The generic .card class (used on dashboard/admin pages) has BOTH a border AND a shadow. The flip cards in the cards view only have shadow — the border was omitted from the .flip-card-front/.flip-card-back rules.

## Resolution

root_cause: |
  The `.flip-card-front` and `.flip-card-back` elements in `views.css` rely solely on
  `box-shadow: var(--shadow)` for visual separation. No `border` property is set.

  The `--shadow` token in light mode (0 1px 3px rgba(0,0,0,0.08)) is far too faint to
  provide clear card edges against the near-white background (#ffffff surface on #fafafa bg).

  In dark mode the shadow is stronger but still insufficient on its own because:
  1. The shadow only spreads 3px at 30% opacity
  2. The card surface (#282c34) is already close to the page background (#1e2127)

  The generic `.card` class used elsewhere in the app already applies BOTH border + shadow,
  but the card-view flip-card faces never adopted that pattern — they were styled with
  shadow only.

fix: NOT APPLIED (goal: find_root_cause_only — reporting only)

verification: NOT APPLIED

files_changed: []
