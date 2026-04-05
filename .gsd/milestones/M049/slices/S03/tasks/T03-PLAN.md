---
estimated_steps: 15
estimated_files: 2
skills_used: []
---

# T03: Lazy-load inbox and collaboration panels on reveal (R001)

## Description

Change the inbox and collaboration right-pane panels from `hx-trigger="load"` to `hx-trigger="revealed"` so they only fire HTTP requests when scrolled into view / expanded, not on every page load. This delivers requirement R001.

## Steps

1. Read `backend/app/templates/browser/partials/inbox_panel.html`. Change `hx-trigger="load, every 60s"` to `hx-trigger="revealed, every 60s"`. The `revealed` trigger fires when the element enters the viewport via IntersectionObserver. The `every 60s` continues independently after first reveal to keep the inbox fresh.
2. Read `backend/app/templates/browser/partials/collaboration_panel.html`. Change `hx-trigger="load"` to `hx-trigger="revealed"`.
3. Verify the changes are correct by grepping for the old and new patterns.

## Must-Haves

- [ ] Inbox panel: `hx-trigger="revealed, every 60s"` (not `load`)
- [ ] Collaboration panel: `hx-trigger="revealed"` (not `load`)
- [ ] No other htmx attributes changed

## Verification

- `grep 'hx-trigger' backend/app/templates/browser/partials/inbox_panel.html` — shows `revealed, every 60s`
- `grep 'hx-trigger' backend/app/templates/browser/partials/collaboration_panel.html` — shows `revealed`
- `! grep 'hx-trigger="load' backend/app/templates/browser/partials/inbox_panel.html` — no load trigger
- `! grep 'hx-trigger="load' backend/app/templates/browser/partials/collaboration_panel.html` — no load trigger

## Inputs

- ``backend/app/templates/browser/partials/inbox_panel.html` — current hx-trigger="load, every 60s"`
- ``backend/app/templates/browser/partials/collaboration_panel.html` — current hx-trigger="load"`

## Expected Output

- ``backend/app/templates/browser/partials/inbox_panel.html` — changed to hx-trigger="revealed, every 60s"`
- ``backend/app/templates/browser/partials/collaboration_panel.html` — changed to hx-trigger="revealed"`

## Verification

grep 'revealed' backend/app/templates/browser/partials/inbox_panel.html && grep 'revealed' backend/app/templates/browser/partials/collaboration_panel.html && ! grep 'hx-trigger="load' backend/app/templates/browser/partials/inbox_panel.html && ! grep 'hx-trigger="load' backend/app/templates/browser/partials/collaboration_panel.html
