# Phase 39: Edit Form Helptext + Type Accent Colors - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Edit forms show contextual help text from SHACL annotations at both form-level and field-level. Tab accent bars display type-specific colors declared in the Mental Model manifest. BUG-05 through BUG-09 are already fixed and move to Phase 40 for E2E verification only.

**Active requirements:** HELP-01, BUG-04
**Verification-only (deferred to Phase 40):** BUG-05, BUG-06, BUG-07, BUG-08, BUG-09

</domain>

<decisions>
## Implementation Decisions

### Helptext annotation model
- Single property: `sempkm:editHelpText` used on both `sh:NodeShape` (form-level) and `sh:PropertyShape` (field-level)
- Content is full markdown, rendered via marked.js (same pipeline as object body)
- Collapsed by default at both levels; user clicks to expand

### Helptext placement — form level
- Collapsible section at top of form, below the form title/header, above the first field
- Similar pattern to the Phase 31 properties toggle (badge/toggle in header area)
- Expands to show a rendered markdown block

### Helptext placement — field level
- Small `?` icon (Lucide `help-circle`) positioned next to the field label
- Clicking expands helptext inline below the field
- Collapsed by default

### Helptext seed content
- All fields on the Note NodeShape get field-level helptext as a complete example
- Note NodeShape also gets form-level helptext
- Other shapes (Project, Concept, Person) get form-level helptext only (minimum)
- Total: at least 3 representative fields annotated (satisfies HELP-01)

### Type-aware accent colors (BUG-04)
- Manifest-declared per type: Mental Model manifest declares an accent color per NodeShape
- Fallback when no manifest color specified: current teal (`--color-accent`)
- Applied to tab accent bar only (2px bottom border on active dockview tab)
- Inactive tabs remain neutral (no type color)

### Color palette for basic-pkm types
- Warm/cool split palette: Notes=teal, Projects=indigo, Concepts=amber, Persons=rose
- Colors must work well in both light and dark themes
- Manifest property format: Claude's discretion (hex, CSS token name, etc.)

### Already-fixed bugs (verification only)
- BUG-05 (card borders): Already fixed — verify in Phase 40 E2E
- BUG-06 (Firefox Ctrl+K): Already fixed — verify in Phase 40 E2E
- BUG-07 (tab accent bleed): Already fixed — verify in Phase 40 E2E
- BUG-08 (dark chevrons): Already fixed — verify in Phase 40 E2E
- BUG-09 (concept search): Already fixed — verify in Phase 40 E2E

### Claude's Discretion
- Exact CSS for the help-circle icon sizing and positioning
- Collapse/expand animation timing
- Manifest property name and format for type accent color declaration
- How accent color flows from manifest → backend → frontend (CSS custom property, data attribute, inline style, etc.)
- localStorage key for helptext collapse state (if persisted)

</decisions>

<specifics>
## Specific Ideas

- The `?` icon for field-level helptext should feel native to the form — not a separate widget, but part of the label row
- Form-level helptext follows the Phase 31 collapsible section pattern (similar to properties toggle)
- Accent color warm/cool split: Notes=teal, Projects=indigo, Concepts=amber, Persons=rose — chosen for high contrast between types

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/shapes.py`: ShapesService.get_form_for_type() — entry point for loading shape data into forms
- `backend/app/templates/forms/object_form.html`: Edit form template — where helptext rendering will be added
- `orig_specs/models/starter-basic-pkm/shapes.ttl`: SHACL shapes for basic-pkm model — where helptext annotations go
- `marked.js`: Already used for object body markdown rendering — reuse for helptext
- Phase 31 properties toggle pattern: collapsible section with badge in header toolbar

### Established Patterns
- Lucide icons via `data-lucide` attributes with CSS sizing (`flex-shrink: 0`, `stroke: currentColor`)
- Dockview tab styling via `dockview-sempkm-bridge.css` token bridge (--dv-* → SemPKM tokens)
- Tab active border: `--tab-active-border: 2px solid var(--color-accent)` in theme.css
- Mental Model manifest declares icons per type (IconService pattern) — accent colors follow the same pattern

### Integration Points
- Manifest schema: needs new optional `accentColor` field per type declaration
- `backend/app/services/shapes.py`: needs to extract `sempkm:editHelpText` from shapes
- `frontend/static/css/theme.css`: tab accent border token needs to support per-type override
- `frontend/static/js/workspace.js`: dockview tab creation needs to apply type-specific accent color

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 39-edit-form-helptext-and-bug-fixes*
*Context gathered: 2026-03-05*
