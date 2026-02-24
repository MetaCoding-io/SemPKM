---
status: resolved
trigger: "Investigate why the teal accent on active tabs appears on the left side as well as the bottom, and why the 4px border-radius on tabs isn't visible."
created: 2026-02-23T00:00:00Z
updated: 2026-02-23T00:00:00Z
---

## Current Focus

hypothesis: confirmed — two independent bugs identified
test: static analysis of CSS cascade
expecting: n/a — findings complete
next_action: report to user

## Symptoms

expected: Active tabs show teal accent ONLY on the bottom border; tabs have visible 4px rounded top corners.
actual: Teal accent also appears on the left side of tabs; rounded corners are invisible.
errors: none (visual-only bugs)
reproduction: Open workspace, activate any tab, observe left-side teal stripe and flat top corners.
started: unknown — likely introduced with views.css view-tab rule and tab-bar overflow-y:hidden

## Eliminated

- hypothesis: theme.css transition rule causes the border bleed
  evidence: theme.css only sets transition: background-color, color, border-color — it does not set any border value
  timestamp: 2026-02-23

## Evidence

- timestamp: 2026-02-23
  checked: frontend/static/css/views.css lines 651-657
  found: |
    .workspace-tab.view-tab {
        border-left: 2px solid var(--color-primary);
    }
    .workspace-tab.view-tab.active {
        border-left-color: var(--color-primary);
    }
  implication: |
    Every tab rendered as a "view tab" gets a permanent border-left: 2px solid --color-primary (teal).
    The active rule does not clear or override this — it only re-asserts the same color.
    So when a view-tab is active, it has BOTH border-bottom (accent, from workspace.css) AND
    border-left (also accent, from views.css), producing the visible left-side stripe.

- timestamp: 2026-02-23
  checked: frontend/static/css/workspace.css lines 274-284 (.tab-bar-workspace)
  found: |
    overflow-y: hidden;
    min-height: 36px;
    align-items: flex-end;
  implication: |
    The tab bar is exactly 36px tall (min-height) and clips vertically (overflow-y: hidden).
    Tabs are bottom-aligned (align-items: flex-end).
    The border-radius: 4px 4px 0 0 on .workspace-tab creates rounded top-left and top-right corners
    that protrude ABOVE the tab's own content box — but the tab bar's overflow-y: hidden clips
    anything that extends above the min-height boundary.
    Because align-items: flex-end pushes tabs to the bottom of the bar, the 4px rounded caps at
    the top of each tab are exactly at or above the clip boundary, making them invisible.

## Resolution

root_cause: |
  BUG 1 — Left-side teal accent bleeding:
    File: frontend/static/css/views.css, lines 651-653
    Rule: .workspace-tab.view-tab { border-left: 2px solid var(--color-primary); }
    Cause: Any tab with the .view-tab class gets an unconditional 2px teal border-left. This rule
    exists alongside workspace.css's border-bottom accent for .workspace-tab.active. Both are
    visible simultaneously on an active view-tab, so the accent appears on two sides.

  BUG 2 — Missing border-radius:
    File: frontend/static/css/workspace.css, lines 276-278
    Rule: .tab-bar-workspace { overflow-y: hidden; min-height: 36px; align-items: flex-end; }
    Cause: The tab bar clips vertically at its min-height boundary. Tabs are aligned to the
    bottom of the bar. The top-corner radius (4px top-left, 4px top-right) on .workspace-tab
    sits at or above the clip line, so the browser renders them outside the visible area.

fix: not applied (diagnose-only mode)
verification: n/a
files_changed: []
