# Stack Research: SemPKM v2.3 — Shell, Navigation & Views

**Domain:** Dockview Phase A migration, markdown-first object view with carousel, named workspace layouts, FTS fuzzy search
**Researched:** 2026-03-01
**Confidence:** HIGH for dockview-core and LuceneSail fuzzy; MEDIUM for carousel approach and manifest schema (SemPKM-specific, no external precedent)

---

## Scope Note

This is a **subsequent milestone** research document. The existing validated stack (FastAPI, RDF4J LuceneSail, htmx, Split.js, SQLite, wsgidav, Yasgui CDN, dockview-core DEC-04 committed) is not re-researched. This document covers only what changes or is added for v2.3 features.

---

## Recommended Stack

### Core Technologies (new or version-clarified for v2.3)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| dockview-core | **4.11.0** (latest as of 2026-03-01) | Replace Split.js editor-pane area with dockview panels (Phase A) | Already committed DEC-04; zero deps; `createComponent` + `params.containerElement` integrates with htmx.ajax pattern exactly; `toJSON()`/`fromJSON()` for named layouts |
| CSS scroll-snap | Native browser API | Carousel view rotation (VIEW-02) | No library needed; `scroll-snap-type: x mandatory` + `scroll-snap-align: start` is sufficient for a tab-like multi-view switcher; avoids adding Swiper.js (~25KB gz) for what amounts to a button-triggered slide |
| LuceneSail fuzzy query syntax | Ships with RDF4J 5.x (no new dep) | FTS-04 approximate-match support | `term~` and `term~1` Lucene fuzzy syntax already supported by the existing LuceneSail; `fuzzyPrefixLength` SAIL parameter tunes behavior; no new library required |
| localStorage | Browser native | Named layout fast-path cache | Debounced auto-save to localStorage + async server persist via `fetch()`; avoids cold-load latency; already used for SPARQL tabs and panel positions |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dockview-core CSS | `dist/styles/dockview.css` via CDN | Dockview default chrome styles | Load after `theme.css` then `dockview-sempkm-bridge.css` overrides `--dv-*` variables; bridge file already created in v2.2 |
| htmx.process() | Built into htmx (existing) | Re-process htmx bindings after panel reparent | Call on `onDidLayoutChange` for any panel that has `closest`-scoped `hx-target`; existing htmx, no version change |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Node.js (local only) | `npm pack dockview-core` to check bundle size, then vendor | No build pipeline; vendor to `frontend/static/vendor/dockview/` if bundle > 400KB gz; CDN otherwise |
| Browser DevTools | Validate htmx handler survival on panel reparent | Test with `htmx.logAll()` enabled; confirm `hx-trigger` fires after drag-to-new-group |

---

## Installation

```bash
# No new npm packages for production; dockview-core loaded via CDN or vendored

# To measure bundle size before deciding CDN vs vendor:
npm pack dockview-core@4.11.0
# Check gzipped size of dist/cjs/index.js or dist/esm/index.js

# CDN load order in workspace.html (Phase A):
# <link rel="stylesheet" href="/static/css/theme.css">
# <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/styles/dockview.css">
# <link rel="stylesheet" href="/static/css/dockview-sempkm-bridge.css">
# <script src="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/cjs/index.js"></script>
```

No new Python packages required for v2.3. The existing `pyproject.toml` is unchanged.

---

## Alternatives Considered

### Carousel / View Rotation

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| CSS scroll-snap (native) | Swiper.js v11 | Only if carousel needs touch momentum, lazy loading, or 3D cube transitions — none of which VIEW-02 requires |
| CSS scroll-snap (native) | CSS 3D flip (existing, used for view/edit flip) | 3D flip works for two-state toggle (read/edit); does not generalize cleanly to N>2 views because cube geometry gets complex |
| CSS scroll-snap (native) | Tab-button switcher (pure JS show/hide) | Simpler for exactly 2-3 views if animation is not needed; valid if the carousel metaphor is dropped in favor of explicit buttons |

**Recommendation is CSS scroll-snap** because:
- Zero new dependencies
- Works identically to current Split.js pattern (no framework)
- `scroll-snap-type: x mandatory` with overflow:hidden on the container = invisible to users; navigation via prev/next buttons or indicator dots
- Falls back gracefully in environments that disable scrollbar (the snap behavior is pure CSS)

### Named Layout Storage

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| localStorage fast-path + fetch() async server persist | RDF triplestore storage (user preferences graph) | Use RDF storage when named layouts need to be named, shareable, or model-provided (Phase C); for Phase A anonymous auto-save, localStorage is sufficient |
| localStorage fast-path + fetch() async server persist | Cookie-only | Cookie size limit (4KB) is insufficient for a full dockview `toJSON()` payload (~1-5KB per layout) |

For **named layouts (DOCK-02)**, the Phase C design (documented in DECISIONS.md) stores layout JSON as a `sempkm:WorkspaceLayout` preference in the RDF triplestore with `sempkm:layoutConfig` as a literal. Use `POST /api/layouts` endpoint. Model-provided layouts ship in the manifest `layouts:` key (see Manifest Schema section below).

### FTS Fuzzy

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Lucene `term~` / `term~1` fuzzy syntax in existing LuceneSail | N-gram tokenization at index time | Use n-gram if queries are very short (1-3 chars) and performance is critical; n-gram trades index size (~3x larger) for query speed; not warranted at PKM scale |
| Lucene `term~` / `term~1` fuzzy syntax | PostgreSQL `pg_trgm` similarity | Requires PostgreSQL migration (not yet done); `pg_trgm` is the better long-term option but blocked |
| `term~` tilde syntax | Wildcard `term*` prefix search | Wildcard only matches prefixes; fuzzy matches transpositions and substitutions; `term~` is strictly better for typo tolerance |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Swiper.js | 25KB gz for what CSS scroll-snap handles natively; adds JS initialization, touch event listeners, and markup requirements that conflict with htmx AJAX-loaded content | CSS scroll-snap with `overflow: hidden` on container, `overflow-x: scroll` on track |
| GoldenLayout 2 | Already ruled out in DEC-04; DOM reparenting breaks htmx handlers; LESS-based themes incompatible with CSS token system | dockview-core (committed) |
| `::scroll-button()` CSS pseudo-elements for carousel navigation | Chrome 135+ only (flag required as of 2026-03-01); no Firefox/Safari support | Standard `<button>` elements with JS click handlers that call `scrollBy()` on the snap container |
| pgvector for FTS-04 | Requires PostgreSQL migration (not yet done); overkill for approximate keyword matching | LuceneSail `term~` syntax which is already operational |
| `search:property` restriction for FTS | Narrowing to specific predicates reduces recall; FTS-04 is about improving approximate match, not narrowing fields | Keep field-agnostic search (all literals indexed); use `rdf:type` filter for type scoping |
| `useramdir=true` LuceneSail config | RAM-only index is discarded on restart; breaks FTS on container restart | `lucenedir=/var/rdf4j/lucene-index` with Docker volume mount (already the committed pattern) |

---

## Stack Patterns by Variant

**For dockview Phase A (editor pane only — DOCK-01):**
- `new DockviewComponent(editorAreaElement, { createComponent })` replaces the 4-group HTML grid
- `createComponent` calls `htmx.ajax('GET', url, { target: params.containerElement, swap: 'innerHTML' })`
- Call `htmx.process(containerElement)` in `onDidLayoutChange` for any panel with ancestor-scoped `hx-target`
- Disable `popoutSupport` and `floatingGroupBounds` for Phase A — floating panels are Phase C scope
- Layout auto-save: `onDidLayoutChange` → debounced `localStorage.setItem('sempkm_layout')` → no server persist yet (Phase A; server persist is DOCK-02 scope)

**For carousel view rotation (VIEW-02):**
- Carousel container: `overflow: hidden` on outer wrapper, `display: flex; overflow-x: scroll; scroll-snap-type: x mandatory; scroll-behavior: smooth` on inner track
- Each view slide: `flex: 0 0 100%; scroll-snap-align: start`
- Navigation: standard `<button>` elements with `onclick="track.scrollBy({ left: ±containerWidth, behavior: 'smooth' })"` — no Intersection Observer needed for 2-4 view slots
- View indicators: `<span class="dot" data-view-index="0">` updated on `scroll` event with `scrollLeft / containerWidth`
- htmx content: each slide is an `hx-get` target loaded lazily on first scroll into view (use `IntersectionObserver` for lazy loading if more than 3 views)

**For manifest-declared views (VIEW-02 manifest schema):**
- Add `objectViews` key to manifest YAML alongside existing `icons` key
- Per-type entry: `{ type, views: [{ id, renderer, label, icon, default }] }`
- `renderer` values: `"markdown"` (new default for object body), `"properties"` (explicit reveal), `"relations"` (existing relations panel inline), `"custom"` (model-provided template)
- `default: true` marks which view slot loads first (should be `"markdown"` for notes, `"properties"` for structured types)
- Example:
  ```yaml
  objectViews:
    - type: "bpkm:Note"
      views:
        - { id: "markdown", renderer: "markdown", label: "Note", icon: "file-text", default: true }
        - { id: "properties", renderer: "properties", label: "Properties", icon: "sliders" }
    - type: "bpkm:Person"
      views:
        - { id: "properties", renderer: "properties", label: "Profile", icon: "user", default: true }
        - { id: "relations", renderer: "relations", label: "Connections", icon: "network" }
  ```
- If `objectViews` is absent for a type, fall back to the current single-view object page (no carousel shown)
- The `ManifestService` reads this key; the object view template checks `has_carousel` flag set from the loaded spec

**For FTS fuzzy (FTS-04):**
- Change `search:query` binding in `SearchService._build_search_query()` from `"${term}"` to `"${term}~"` for single-term queries
- For multi-token queries (spaces), apply `~` per-token: `"word1~ word2~"` — Lucene parses each token independently
- Keep the existing `term*` wildcard for prefix completions (fast, no edit distance cost) alongside `term~` for typo tolerance
- `fuzzyPrefixLength` SAIL config parameter (default 0) controls how many initial characters must match exactly before fuzzy kicks in; set to `1` or `2` to reduce false positives and improve performance
- Expose `fuzzyPrefixLength` in the LuceneSail Turtle config (`config/rdf4j/sempkm-repo.ttl`) alongside the existing `luceneDir` parameter
- No new SPARQL endpoint; `GET /api/search?q=` continues to call `SearchService.search()`; the change is purely in the query string construction

**For named layouts (DOCK-02) — Phase C scope but design now:**
- `GET /api/layouts` returns user's saved layouts (names + metadata from RDF triplestore)
- `POST /api/layouts` saves current `dockview.toJSON()` snapshot with user-given name
- `PUT /api/layouts/{name}/activate` switches active layout
- Model-provided default layouts in manifest `layouts:` key:
  ```yaml
  layouts:
    - name: "Research Mode"
      description: "Two-column: explorer left, editor+relations right"
      config: layouts/research-mode.json
      default: false
  ```
- Layout JSON files are relative paths inside the model archive; loaded at install time and stored as `sempkm:WorkspaceLayout` with `sempkm:isModelProvided: true`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| dockview-core 4.11.0 | `dockview-sempkm-bridge.css` (created v2.2) | Bridge maps `--dv-*` to `--color-*`/`--tab-*`/`--panel-*` tokens; confirmed `--dv-*` variable names match 4.x API |
| dockview-core 4.11.0 | htmx 1.x (existing) | `htmx.ajax()` + `htmx.process()` are stable 1.x APIs; no version change needed |
| LuceneSail fuzzy `term~` | RDF4J 5.0.1 (existing, operational) | Lucene fuzzy query syntax is stable across Lucene 7-9; RDF4J 5.0.1 ships with Lucene 9; `term~` with edit distance 0-2 works as documented |
| CSS scroll-snap | All modern browsers (Firefox 68+, Chrome 69+, Safari 11+) | No polyfill needed; `::scroll-button()` (Chrome 135+ only) is explicitly excluded |
| manifest `objectViews` key | ManifestService (existing Python YAML loader) | New optional key; existing YAML parsing is permissive; no schema version bump required for optional additions |

---

## dockview-core API Reference (Phase A)

The key APIs needed for Phase A migration:

```javascript
// Instantiation
const dockview = new DockviewComponent(containerElement, {
  createComponent: (options) => ({
    init: (params) => {
      // params.containerElement is the DOM target for htmx
      htmx.ajax('GET', buildUrl(options.params), {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    },
    update: (params) => {
      // Called when panel params change (e.g., navigate to different object)
      htmx.ajax('GET', buildUrl(params.params), {
        target: params.containerElement,
        swap: 'innerHTML'
      });
    }
  }),
  // Phase A: disable advanced features not yet needed
  disableFloatingGroups: true,
});

// Panel management
dockview.addPanel({ id, component, params, title, position });
dockview.removePanel(panel);

// Layout serialization (for DOCK-02 later)
const snapshot = dockview.toJSON();
dockview.fromJSON(snapshot);

// Events
dockview.onDidLayoutChange(() => {
  // Re-process htmx on panels with ancestor-scoped selectors
  dockview.panels.forEach(panel => htmx.process(panel.view.content.element));
});

// Active panel tracking (for sempkm:tab-activated event dispatch)
dockview.onDidActivePanelChange((panel) => {
  const isObjectTab = panel?.params?.iri != null;
  document.dispatchEvent(new CustomEvent('sempkm:tab-activated', {
    detail: { isObjectTab, iri: panel?.params?.iri }
  }));
});
```

CSS load order for workspace template:
```html
<link rel="stylesheet" href="/static/css/theme.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/dockview-core@4.11.0/dist/styles/dockview.css">
<link rel="stylesheet" href="/static/css/dockview-sempkm-bridge.css">
```

---

## LuceneSail Fuzzy Configuration Reference

Changes to `config/rdf4j/sempkm-repo.ttl` for FTS-04:

```turtle
# Add fuzzyPrefixLength to the LuceneSail configuration block
config:sail.impl [
   config:sail.type "openrdf:LuceneSail" ;
   config:lucene.luceneDir "/var/rdf4j/lucene-index" ;
   config:lucene.fuzzyPrefixLength "2" ;    # NEW: require first 2 chars to match exactly
   config:sail.delegate [
      config:sail.type "openrdf:NativeStore" ;
      config:native.tripleIndexes "spoc,posc,cspo" ;
      config:sail.defaultQueryEvaluationMode "STANDARD"
   ]
] .
```

Changes to `SearchService._build_search_query()` in `backend/app/services/search.py`:

```python
def _build_fts_query_string(self, term: str, fuzzy: bool = True) -> str:
    """Build a Lucene query string with optional fuzzy matching."""
    tokens = term.strip().split()
    if not tokens:
        return term
    if fuzzy and len(term) > 3:
        # Apply fuzzy tilde to each token; keep prefix wildcard for short tokens
        parts = []
        for t in tokens:
            if len(t) <= 3:
                parts.append(f"{t}*")   # prefix wildcard for short tokens
            else:
                parts.append(f"{t}~1")  # edit distance 1 for longer tokens
        return " ".join(parts)
    else:
        # Exact prefix matching (fast, existing behavior)
        return " ".join(f"{t}*" for t in tokens)
```

---

## Sources

- [dockview-core npm page](https://www.npmjs.com/package/dockview-core) — version 4.11.0 confirmed, weekly downloads ~18K, 0 dependencies
- [dockview.dev official docs](https://dockview.dev/docs/api/dockview/overview/) — `createComponent`, `addPanel`, `toJSON`/`fromJSON`, `onDidLayoutChange`, `onDidActivePanelChange` API
- [dockview TypeDocs v4.13.1](https://dockview.dev/typedocs/modules/dockview_core.html) — type-level API reference
- [dockview Phase 23 RESEARCH.md](.planning/research/phase-23-ui-shell/RESEARCH.md) — full comparative analysis, htmx integration patterns, layout persistence design (HIGH confidence — prior project research)
- [DECISIONS.md DEC-04](.planning/DECISIONS.md) — committed dockview-core decision with Phase A/B/C plan
- [dockview-sempkm-bridge.css](frontend/static/css/dockview-sempkm-bridge.css) — CSS token bridge already created, `--dv-*` variable mapping confirmed
- [RDF4J LuceneSail Javadoc 5.1.3](https://rdf4j.org/javadoc/latest/org/eclipse/rdf4j/sail/lucene/LuceneSail.html) — `fuzzyPrefixLength`, `indexedfields`, `reindexQuery` parameters confirmed
- [RDF4J LuceneSail documentation](https://rdf4j.org/documentation/programming/lucene/) — fuzzy `term~`, wildcard `term*`, proximity search syntax
- [MDN: Creating CSS Carousels](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Overflow/Carousels) — scroll-snap carousel pattern
- [Chrome Developers: Carousels with CSS](https://developer.chrome.com/blog/carousels-with-css) — `::scroll-button()` browser support status (Chrome 135+ flag only — excluded)
- [jsDelivr dockview-core](https://www.jsdelivr.com/package/npm/dockview-core) — CDN availability confirmed

---
*Stack research for: SemPKM v2.3 Shell, Navigation & Views milestone*
*Researched: 2026-03-01*
