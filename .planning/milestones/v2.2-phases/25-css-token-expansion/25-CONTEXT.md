# Phase 25: CSS Token Expansion - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Pure infrastructure refactor: expand the CSS custom property token system from ~40 to ~91 tokens using a two-tier primitive/semantic architecture. Replace all hardcoded values in workspace/style/forms/views CSS with token references. Create a `dockview-sempkm-bridge.css` pattern file mapping `--dv-*` variables to SemPKM tokens for the v2.3 dockview migration. No user-visible behavior changes.

</domain>

<decisions>
## Implementation Decisions

### Token Architecture
- Two tiers: primitive tokens (`--_color-*`, `--_spacing-*`) and semantic tokens (`--color-*`, `--tab-*`, `--panel-*`, `--spacing-*`, `--font-size-*`, `--sidebar-*`, `--graph-*`)
- Primitive tokens: raw values, never change between themes
- Semantic tokens: reference primitives, overridden in dark mode
- Dark mode `[data-theme="dark"]` overrides ONLY touch semantic tokens

### Scope of Replacement
- All hardcoded color, spacing, and typography values in:
  - `frontend/static/css/workspace.css`
  - `frontend/static/css/style.css`
  - `frontend/static/css/forms.css`
  - `frontend/static/css/views.css`
- Pure refactor — no behavior or visual changes allowed

### Token Count Target
- ~91 tokens total (from DECISIONS.md DEC-04 commitment)
- Expands from current ~35 tokens in `theme.css`

### Dockview Bridge File
- Create `frontend/static/css/dockview-sempkm-bridge.css`
- Maps `--dv-*` Dockview CSS variables to SemPKM semantic tokens
- Not loaded yet — pattern file only, consumed by v2.3 Phase A dockview migration

### Claude's Discretion
- Exact token naming conventions (follow existing patterns in theme.css)
- Which CSS files to tackle first (can be done in any order)
- Whether to split into sub-plans by CSS file or by token category

</decisions>

<specifics>
## Specific Ideas

- Current theme.css already has ~35 tokens — this phase extends it, doesn't replace it
- DECISIONS.md (DEC-04) specifies this as a v2.2-eligible prerequisite for v2.3 dockview work
- The bridge file pattern: `--dv-tab-active-background: var(--color-accent)` etc.

</specifics>

<deferred>
## Deferred Ideas

- Full dockview-core Phase A migration — v2.3 (this phase only creates the bridge file)
- User-selectable themes / model-contributed themes — v2.3 CSS-01
- Full theming system — future

</deferred>

---

*Phase: 25-css-token-expansion*
*Context gathered: 2026-02-28*
