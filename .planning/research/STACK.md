# Stack Research: SemPKM v2.0 Tighten Web UI

## Summary

Only 4 new JS libraries needed for all v2.0 features. Total new payload: ~61kb gzipped globally + ~15kb lazy-loaded for event log. No new backend dependencies.

## Key Decisions

### Driver.js replaces Shepherd.js
Shepherd.js switched to AGPL-3.0 and requires a commercial license. Driver.js is MIT, 5kb, zero-dep.
- CDN: `https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.js.iife.js`
- CSS: `https://cdn.jsdelivr.net/npm/driver.js@1.3.1/dist/driver.css`

### Dark mode requires zero libraries
The v1.0 CSS already uses custom properties with fallbacks everywhere. Dark mode is a `[data-theme="dark"]` CSS block + ~20 lines of JS.

### VS Code-style split panes is the hardest feature
Dockview (ideal library) requires a bundler with no UMD bundle. Must be built as custom code on Split.js + SortableJS.

### No new backend dependencies needed
LLM proxy uses existing httpx. Settings validation uses existing jsonschema (transitive dep).

## Library Recommendations

| Feature | Library | Size (gzip) | CDN | Rationale |
|---------|---------|-------------|-----|-----------|
| Tab drag between groups | SortableJS 1.15 | ~10kb | `cdn.jsdelivr.net/npm/sortablejs@1.15.3/Sortable.min.js` | Proven drag-drop, works with vanilla DOM |
| Guided tours | Driver.js 1.3 | ~5kb | See above | MIT, zero-dep, replaces AGPL Shepherd.js |
| Icons | Lucide 0.460 | ~45kb | `unpkg.com/lucide@0.460.0/dist/umd/lucide.min.js` | 1500+ icons, `lucide.createIcons()` for htmx |
| Event diffs | jsondiffpatch 0.6 | ~15kb | `esm.sh/jsondiffpatch@0.6.0` (ESM only) | Lazy-loaded for event log only |
| Split panes | Split.js (existing) | 0 | Already loaded | Reuse for bottom panel + nested splits |
| Dark mode | Vanilla CSS | 0 | N/A | CSS custom properties already in place |
| Collapsible sidebar | Vanilla CSS/JS | 0 | N/A | Pure CSS transition |
| Settings system | Server-rendered Jinja2 | 0 | N/A | Existing patterns |
| LLM proxy | httpx (existing) | 0 | N/A | SSE streaming built-in |
| Bottom panel | Split.js (existing) | 0 | N/A | Vertical split instance |

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Dark mode | HIGH | Existing CSS custom properties + well-established pattern |
| Icons (Lucide) | HIGH | Verified CDN, vanilla JS API, htmx-compatible createIcons() |
| Guided tours (Driver.js) | HIGH | MIT licensed, 5kb, verified IIFE CDN bundle |
| Tab drag (SortableJS) | MEDIUM | SortableJS is proven, but editor-group-splitting logic is custom |
| Event diff (jsondiffpatch) | MEDIUM | ESM-only introduces second CDN (esm.sh); RDF-to-JSON serialization needs design |
| LLM config | HIGH | No new dependencies, straightforward httpx usage |
| Bottom panel | HIGH | Reuses existing Split.js patterns |
| Collapsible sidebar | HIGH | Pure CSS, pattern exists in responsive breakpoint |
| Settings system | HIGH | Server-rendered forms, existing pattern |

## Roadmap Implications

1. Dark mode and collapsible sidebar are low-hanging fruit — can ship early, zero new libraries
2. VS Code split panes should be its own phase — highest complexity, custom editor-group model
3. Lucide icons should be added early — enhances explorer tree and graph view simultaneously
4. Event log explorer depends on backend diff endpoint design — jsondiffpatch needs RDF-to-JSON serialization format
5. Driver.js tours should come last — tours reference UI elements that need to exist first

## Open Questions

- Lucide bundle size: 180kb uncompressed (45kb gzip) for 1500+ icons. Could cherry-pick ~20 SVGs as static files if too large.
- esm.sh as second CDN: jsondiffpatch requires it since it dropped UMD. Acceptable? Or bundle locally?
- SortableJS split-zone detection: How to detect tab drag toward editor edge to trigger split. Needs custom dropzone overlays.
- ninja-keys version pin: Currently unpinned (`unpkg.com/ninja-keys?module`). Should pin in v2.0.
