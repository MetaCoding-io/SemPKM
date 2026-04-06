# M052 Research: UI Design System & Polish Pass

## Current State Assessment

### CSS Architecture (Established)
The CSS infrastructure is solid — M044 established a mature two-tier token system in `theme.css`:
- **Primitives** (`--_color-*`, `--_spacing-*`, `--_font-size-*`): raw values, never overridden per-theme
- **Semantics** (`--color-*`, `--shadow-*`, `--tab-*`, `--panel-*`): reference primitives, overridden in dark mode
- **Zero standalone hex/rgba** outside `theme.css` (verified by M044 audit)
- All decorative colors use `color-mix(in srgb, var(--_color-*) N%, transparent)`
- Dark mode via `html[data-theme="dark"]` override block
- 611 lines in `theme.css` — well-organized, ~91 semantic tokens

### CSS File Map
| File | Lines | Purpose |
|------|-------|---------|
| `workspace.css` | 9199 | Main workspace (object view, tab bar, explorer, panels, properties) |
| `views.css` | 1779 | View renderers (table, kanban, graph, calendar, timeline, map) |
| `forms.css` | 455 | SHACL form styling (edit mode) |
| `theme.css` | 611 | Token system + dark mode overrides |
| `dockview-sempkm-bridge.css` | 100 | Dockview CSS variable bridge |
| Specialized: `bmc.css`, `okr.css`, `quadrant.css`, `decision-matrix.css` | ~1094 | Custom renderer styling |

### What Exists vs. What's Missing

**✅ Already working:**
- Type-colored icons in explorer tree (`tree_children.html` uses `type_icon.color`)
- Type-colored tab accent bar (dockview bridge: `--tab-accent-color` on active tab)
- Type badge in object toolbar (`.object-toolbar-type`) — human-readable label
- Property table with grid layout, label/value columns, rounded borders
- Ref-pill popovers (hover-loaded via `/browser/tooltip/`)
- Graph popovers with header, type badge, prop list, footer
- Dark mode token infrastructure
- Icon service (`backend/app/services/icons.py`) resolves per-type icons from manifest `icons:` sections

**❌ Missing / needs improvement:**
- No zebra striping anywhere (grep for "zebra|stripe|alternating" = zero results)
- No property tooltips in read mode (prop names have no hover info)
- Type badge is plain gray pill — no icon, no type color accent
- Kanban cards show only title (no priority, due date, assignee, type icon)
- Kanban column headers have no color differentiation
- Body editor uses CodeMirror 6 with inline theme objects (hardcoded colors, not tokens) — feels like a code editor
- Tab bar active/inactive distinction is only a 2px bottom border (subtle)
- View icons in explorer are Unicode characters (&#9638;, &#9672;), muted gray color
- No consistent vertical rhythm in form help text
- Right panel has no smart empty states (no collapse, no helpful prompts)
- Timeline bars have no status colors or progress indicators

## Surface-by-Surface Analysis

### 1. Object Read View — Properties (#19, #20, #23)
**Current:** Two-column CSS grid (`.property-table`). Labels are `font-weight: 600` on `--color-surface-raised` bg. Values on white. Separated by `border-bottom`. No zebra striping.

**Gap:** Labels and values have the same font-size (0.85rem). The visual weight difference is only bold vs normal, which isn't enough for fast scanning. No hover info on property labels. No row highlighting on hover.

**Approach:** Add alternating row background (`nth-child(even)` via `.property-row:nth-child(even) .property-label, .property-row:nth-child(even) .property-value`), add `title` attributes to labels via Jinja, add hover highlight. Labels already have `background: var(--color-surface-raised)` which creates some distinction — enhance with slightly bolder sizing and muted value color.

### 2. Type Badge / Type Pill (#13, #14)
**Current:** `.object-toolbar-type` is a plain gray pill (0.7rem, `--color-surface-recessed` bg, `--color-text-muted` text). Displays human-readable label (e.g. "Note") — NOT raw IRI (M051 stripped the " Shape" suffix). No icon.

**Gap:** No type color, no Lucide icon. The badge blends into the toolbar.

**Approach:** Backend already passes `type_icon` with `.icon` and `.color` from the IconService. The template has this data available. Inject a Lucide `<i data-lucide="...">` into the badge span and set `style="border-color: {color}"` or use a CSS variable. Keep the badge compact.

### 3. Body Editor (#15)
**Current:** CodeMirror 6 with vendored bundle (`codemirror-markdown.min.js`). Theme is defined as inline JS `EditorView.theme({...})` with hardcoded hex values (`#282c34`, `#21252b`). Line numbers show code-style gutters. Font is whatever CM6 default is.

**Gap:** Feels like a code editor, not a writing surface. Line numbers are prominent. No soft styling.

**Approach:** Override CM6 theme to: softer gutter colors (use token system), optional line number hiding (or muted), add left padding for breathing room, use a proportional font stack for Markdown (not monospace), lighten the border. Keep the existing dark/light theme toggle mechanism but replace hardcoded hex with CSS variable references. This is cosmetic — the CM6 theme objects accept CSS strings, so `var(--color-surface)` works.

### 4. Kanban Cards & Columns (#44, #45, #46)
**Current:** Cards show only `.kanban-card-title`. Columns have a plain `border-bottom` header. The SPARQL query (`_build_kanban_select`) only fetches `?s ?label ?statusValue`.

**Gap:** No priority, due date, assignee, or type icon on cards. Columns are visually identical.

**Approach — Backend:** Expand the kanban SPARQL query with OPTIONAL clauses for well-known fields: `bpkm:priority`, `bpkm:dueDate`, `bpkm:assignedTo`. These are SHACL-introspectable — use `_detect_status_field()` as precedent to find common enrichment fields. Return them as extra fields in the item dicts.

**Approach — Frontend:** Kanban card template adds optional rows: priority badge (color-coded), due date (formatted), assignee pill. Column headers get a left border accent color — map status values to semantic colors (todo=blue, in-progress=amber, done=green, blocked=red, cancelled=gray). This mapping can be generic (keyword-based) or derived from a new manifest field.

**Risk:** The SPARQL enrichment adds query complexity. OPTIONAL clauses shouldn't break existing functionality but may slow results. The enrichment fields are type-specific — a general approach needs to degrade gracefully when fields aren't present.

### 5. Tab Styling (#31)
**Current:** Dockview tabs use bridge CSS variables. Active tab has `border-bottom: 2px solid var(--tab-accent-color, var(--color-accent))` and slightly different background. Inactive tabs are `--color-text-muted` on `--tab-inactive-bg`.

**Gap:** The distinction is subtle. Active and inactive tabs look very similar in both light and dark mode.

**Approach:** Increase contrast: active tab gets `font-weight: 600`, slightly elevated shadow, maybe `--color-surface` background. Inactive tabs get more muted text (`--color-text-faint`). The accent bar could be thicker (3px). This is CSS-only, no template changes.

### 6. View Explorer Icons (#40)
**Current:** Views explorer uses Unicode glyphs (&#9638;, &#9672;, &#128197;) in `--color-text-muted`. Looks generic.

**Approach:** Replace Unicode glyphs with Lucide icons and assign per-view-type colors. Table=blue, Graph=green, Kanban=amber, Calendar=purple, etc. Template change in `views_explorer.html` + CSS.

### 7. Graph/View Popovers (#43)
**Current:** `.graph-popover` has header (label + type badge), props section, footer. Props use flex layout with `gap: 6px`. No internal borders. No alternating row colors.

**Gap:** Properties aren't visually separated. Long prop lists run together.

**Approach:** Add `border-bottom: 1px solid var(--color-border-subtle)` between props. Add alternating row backgrounds. The popover is JS-generated HTML in `graph.js` — needs class additions there.

### 8. Form Sections (#18, #21, #22)
**Current:** Forms have `form-section-required` (no special styling beyond margin) and `form-advanced` (collapsible `<details>`). Form field width is `width: 100%` inside `.object-form-container` which has `max-width: 700px`.

**Gap:** Section headers could be more prominent. Help text spacing is generic.

**Approach:** Stronger section header styling (larger font, colored accent bar, uppercase label). Tighter help text margin. The `max-width: 700px` constraint on `.object-form-container` seems fine — responsive width (#21) may mean removing it on narrow panels so fields fill available space. CSS-only changes.

### 9. Timeline (#51)
**Current:** Uses Frappe Gantt (CDN-loaded). The timeline container is just a `<div>`. Frappe Gantt renders its own SVG bars. The template provides a `patchTimelineTask` function for drag-to-reschedule.

**Gap:** Frappe Gantt styles its own bars. Adding status colors requires overriding Frappe CSS or passing color data. Progress indicators may need Frappe's `progress` field.

**Approach:** Pass `bpkm:taskStatus` (or equivalent) value in the timeline data endpoint. Map status→color in the JS init code. Frappe Gantt supports `custom_class` per task — use CSS classes like `.gantt-bar--done`, `.gantt-bar--blocked`. Check if Frappe supports progress bars natively.

### 10. View Name Underline (#59)
**Current:** No text-decoration underline found anywhere in views.css for view names. The `.view-label` has `font-weight: 600` only. This issue may refer to hover underline on view titles in the explorer — which `.kanban-card-title:hover` does have `text-decoration: underline`. Need visual inspection to confirm what "#59 View names — remove inconsistent underline" refers to.

**Approach:** Low-risk CSS fix once identified. Likely a single `text-decoration: none` override.

### 11. Right Panel Empty States (#17)
**Current:** Right panel (`#right-pane`) shows sections (PROPERTIES, RELATIONSHIPS, etc.) that are always visible even when empty. No collapse-when-empty behavior. No helpful prompts.

**Approach:** Add JS logic: when all sections in the right pane are empty (no content), either collapse the panel or show a prompt like "Select an object to view its details". This is a behavior change, not just CSS.

## Natural Slice Boundaries

The work divides along rendering surfaces with clear CSS/template scoping:

1. **Property & Read View Polish** — property table zebra striping, label/value distinction, tooltips, hover highlights. Scope: `workspace.css` property-table rules + `object_read.html`.

2. **Type System Polish** — type badge with icon + color, type-colored accents on headers. Scope: `object_tab.html` + `workspace.css` `.object-toolbar-type` + dockview bridge.

3. **Body Editor Writing Surface** — CM6 theme overhaul, font stack, gutter softening. Scope: `editor.js` theme objects + `workspace.css` `.codemirror-container`.

4. **Kanban Enrichment** — rich cards (priority/date/assignee), column colors. Scope: `service.py` kanban SPARQL + `kanban_view.html` + `views.css` kanban rules. This is the highest-risk slice (backend SPARQL changes).

5. **Tab & Navigation Polish** — tab active/inactive contrast, view explorer icons, view name underline fix. Scope: `dockview-sempkm-bridge.css` + `views_explorer.html` + `workspace.css` tab rules.

6. **Popover & Panel Polish** — graph popover prop borders, right panel empty states. Scope: `views.css` popover rules + `graph.js` + right-pane JS.

7. **Timeline & Form Polish** — timeline status colors, form section headers, help text spacing. Scope: `views.css` timeline + `forms.css` + `timeline_view.html`.

## Key Constraints

1. **color-mix() pattern is mandatory** (K014). All new decorative colors must use `color-mix(in srgb, var(--_color-*) N%, transparent)` referencing primitives in `theme.css`. No standalone hex/rgba.

2. **Lucide icons in flex containers** need `flex-shrink: 0` and CSS-based sizing, not inline styles (CLAUDE.md rule).

3. **SVG icon stroke inheritance** requires `stroke: currentColor` (CLAUDE.md rule).

4. **Dark mode** for every new CSS rule. Use token references — if they all reference semantic tokens that are already overridden in dark mode, no extra dark-mode blocks are needed. Only new primitive colors require dark-mode entries in `theme.css`.

5. **Dockview stacking context** — any popovers inside dockview panels must be appended to `document.body` with `position:fixed` (K: Dockview stacking context escape).

6. **No functional changes** — this is purely visual. Don't change data models, API contracts, or behavior. The kanban enrichment is the exception — it expands the SPARQL query but doesn't change the API shape.

7. **Workspace.css is 9199 lines** — surgical edits only. Use `edit` tool precisely.

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Kanban SPARQL enrichment breaks existing kanban | Medium | OPTIONAL clauses only; test with basic-pkm Task type |
| Dark mode regressions (new colors) | Medium | Every new primitive gets a dark-mode entry; use semantic tokens where possible |
| Body editor CM6 theme change breaks editing | Low | Theme is cosmetic; don't touch keybindings or save logic |
| Timeline Frappe Gantt CSS overrides don't stick | Low | Frappe uses `custom_class`; CSS specificity is controllable |
| Scope creep ("just one more thing") | Medium | Strict slice boundaries; each slice has specific before/after CSS targets |

## Candidate Requirements

None identified. The CONTEXT.md scope items (#13-#59) are already well-specified acceptance criteria. This work doesn't surface new functional requirements — it's visual refinement of existing surfaces.

## Skills Assessment

Two installed skills are directly relevant:
- **`make-interfaces-feel-better`** — Design engineering principles for micro-interactions, shadows, borders, typography. Load for all CSS-heavy slices.
- **`frontend-design`** — Production-grade frontend interfaces. Useful for kanban card redesign and type badge.

No external skills needed. The work is vanilla CSS + Jinja2 templates with one backend SPARQL change.

## Recommended Proof-First Ordering

1. **Kanban enrichment** (highest risk — backend SPARQL change, template expansion)
2. **Property/read view polish** (high impact, CSS-only, establishes zebra pattern)
3. **Type system polish** (type badge icon+color, broad visual impact)
4. **Tab & navigation polish** (CSS-only, broad impact)
5. **Body editor** (self-contained CM6 theme change)
6. **Popover & panel polish** (targeted, low risk)
7. **Timeline & form polish** (lowest risk, smallest surface)
