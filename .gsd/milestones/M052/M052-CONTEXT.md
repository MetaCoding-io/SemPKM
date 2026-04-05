---
depends_on: [M048, M050]
---

# M052: UI Design System & Polish Pass

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Systemic visual quality pass across the entire Object Browser. Establish a design system with consistent styling for all panels, forms, views, and popovers. Address the "bland/generic" feel and give SemPKM a distinctive visual identity.

## Why This Milestone

The current UI is functional but has no visual personality. Property labels and values are indistinguishable. Panels lack borders and separators. Kanban cards show only a title. The body editor looks like a code editor, not a writing surface. Type badges show raw namespace IRIs. Every panel and view has the same flat gray/white appearance. Fixing this after the functional bugs (M048) and view rework (M050) ensures we're polishing a working product.

## User-Visible Outcome

### When this milestone is complete, the user can:

- See type-colored accents throughout the UI (object headers, explorer entries, view cards)
- Distinguish property labels from values at a glance (bolder labels, muted values, zebra striping)
- See styled type pills with icons instead of raw namespace IRIs
- Edit notes in a body editor that feels like a writing surface
- See kanban cards with priority, due date, assignee, and type icon
- See kanban columns with color-coded headers from the Mental Model
- Distinguish active vs inactive tabs clearly

### Entry point / environment

- Entry point: http://localhost:4000/browser/
- Environment: Docker Compose dev stack
- Live dependencies involved: none

## Completion Class

- Contract complete means: visual regression screenshots showing before/after for key surfaces
- Integration complete means: consistent styling across all views, both light and dark mode
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Object read view: labels are visually distinct from values, zebra striping on properties, tooltip icons present
- Object edit form: inputs fill available width, section headers are prominent
- Kanban view: cards show type icon + priority + due date, column headers have colors
- Graph view: hover popover has aligned properties with borders
- Type badge shows "Note" with icon, not "sempkm:model:basic-pkm:Note"
- Dark mode renders correctly for all styled elements
- Tab bar: active tab clearly distinguishable from inactive

## Risks and Unknowns

- **Scope creep** — "polish" is subjective. Need clear before/after criteria per item.
- **Dark mode interactions** — new colors and borders need dark mode variants. Use color-mix() pattern from M044.
- **Performance** — additional CSS/DOM shouldn't measurably impact render time.

## Existing Codebase / Prior Art

- `frontend/static/css/theme.css` — CSS custom properties with dark mode overrides, ~91 tokens, color-mix() pattern established in M044
- `frontend/static/css/workspace.css` — workspace panel styling
- `frontend/static/css/forms.css` — SHACL form styling
- `frontend/static/css/views.css` — view renderer styling
- M044 established the CSS token system and eliminated standalone hex/rgba values

## Scope

### In Scope

- **#13, #14** Object view — type-colored accent, styled type pill with icon
- **#15** Body editor — reduce code-editor feel, make it a writing surface (softer line numbers, better font)
- **#16** "2 properties" link — better labeling
- **#17** Right panel — smarter empty states (collapse when empty, or show helpful prompts)
- **#18** Form helptext spacing — tighter vertical rhythm
- **#19, #20** Read view properties — label/value visual distinction, tooltips in read mode
- **#21, #22** Edit form — responsive width, stronger section headers
- **#23** Systemic zebra striping / borders across ALL panels and lists
- **#31** Tab styling — more prominent active/inactive distinction
- **#40** View icons in explorer — brighter colors
- **#43** Graph/view popovers — aligned properties, borders
- **#44, #45, #46** Kanban — richer cards, column colors, hover actions
- **#51** Timeline bars — status colors, progress indicators
- **#59** View names — remove inconsistent underline

### Out of Scope / Non-Goals

- Functional fixes (broken views, missing features) — those are M048/M050
- New UI components or layouts
- Mobile/responsive design

## Open Questions

- Should we create a formal design system document (component library) or just establish patterns through implementation?
- What type-color palette? One color per model, per type, or per category?
