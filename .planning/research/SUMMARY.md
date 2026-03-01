# Project Research Summary

**Project:** SemPKM v2.3 — Shell, Navigation & Views
**Domain:** IDE-style semantic PKM workspace — dockview migration, carousel views, named layouts, FTS fuzzy
**Researched:** 2026-03-01
**Confidence:** HIGH (primary findings from direct codebase analysis, official docs, and committed decisions)

## Executive Summary

SemPKM v2.3 is a focused milestone that upgrades the workspace shell and object view UX without changing the core semantic data model. The work divides cleanly into four independent-to-sequentially-dependent features: fuzzy FTS (fully independent, 2-file change), dockview Phase A migration (largest single change, replaces the Split.js editor-group system with dockview-core), carousel view switching per object type (backend-independent, frontend wires in after dockview stabilizes), and named workspace layouts (depends on dockview being live for `toJSON()`). The recommended approach is to ship these in dependency order starting with the lowest-risk independent items — FTS fuzzy ships first for immediate user value, then dockview Phase A which unblocks layouts and carousel frontend, then both remaining features in parallel.

The critical architectural commitment is the dockview-core migration (DEC-04, already committed). All new workspace panel management flows through dockview's public API; htmx remains the content delivery mechanism inside panels. The dockview `createComponent` → `htmx.ajax()` → `htmx.process()` pattern is the integration seam. The CSS bridge file (`dockview-sempkm-bridge.css`) created in v2.2 maps `--dv-*` variables to SemPKM's token system and is already in place. No new Python packages are required; no database migrations are needed.

The dominant risks are in the dockview integration layer: htmx attributes silenced after panel DOM reparenting (solved by `htmx.process()` in `onDidLayoutChange`), CodeMirror and Cytoscape rendering at zero-size when panels are hidden and re-shown (solved by `onDidVisibilityChange` + `refresh()`/`resize()` calls), and layout deserialization failures when named layouts reference uninstalled model components (solved by `try/catch` + `buildDefaultLayout()` fallback with no `api.clear()`). The manifest schema risk for carousel views is the other critical pitfall: all new `ManifestSchema` fields must be optional with defaults, or every installed model fails validation simultaneously on startup.

## Key Findings

### Recommended Stack

The existing stack (FastAPI, RDF4J + LuceneSail, htmx, Split.js outer panes, SQLite, wsgidav) is unchanged for v2.3. The only additions are activating dockview-core 4.11.0 for the editor pane area (already committed in DEC-04, loaded via CDN at jsDelivr) and exposing the Lucene `term~1` fuzzy operator already built into LuceneSail. CSS scroll-snap is the carousel rendering approach — zero new dependencies, native browser API, works identically to the existing no-framework pattern.

**Core technologies (new or version-clarified for v2.3):**
- **dockview-core 4.11.0** — replace Split.js editor-group splits with dockview panels — committed DEC-04, zero deps, `createComponent` + `params.containerElement` integrates with htmx.ajax exactly
- **CSS scroll-snap (native)** — carousel view rotation — `scroll-snap-type: x mandatory` is sufficient; avoids adding Swiper.js (~25KB gz) for what amounts to a button-triggered slide
- **LuceneSail `term~1` fuzzy syntax** — already ships with RDF4J 5.x; no new infrastructure; pure query-string change in `SearchService`
- **localStorage debounce + fetch() async** — named layout fast-path cache with optional server persist; avoids cold-load latency; matches existing panel position pattern

**What NOT to use:** Swiper.js (unnecessary dependency), GoldenLayout 2 (DOM reparenting breaks htmx, already ruled out DEC-04), `::scroll-button()` CSS pseudo-elements (Chrome 135+ flag only, no Firefox/Safari), pgvector (requires PostgreSQL migration not yet done), leading wildcard `*term` in LuceneSail (full index scan).

### Expected Features

**Must have (table stakes) — these make v2.3 feel complete:**
- Properties hidden/collapsed by default in object view — Notion's "N hidden properties / Show" pattern is the universal standard; single-click reveal required
- View switcher for object-level views — tab bar is universal (Notion, VS Code, Obsidian); no animation required; instant switch
- Layout persistence across sessions — VS Code restores last-used layout; users expect workspace arrangement to survive reload
- Fuzzy/approximate matching in search — every modern search expects "roam" to find "roaming"; Obsidian and Notion both do this

**Should have (competitive advantages for v2.3):**
- Manifest-declared carousel views per type — no consumer PKM lets model authors declare the view experience for a type; novel UX primitive
- User-named saved layouts with Command Palette restore — VS Code native doesn't have this (open GitHub issue #156160); SemPKM can deliver it natively with ninja-keys already integrated
- LuceneSail wildcard + fuzzy composing — `alice~ smith~` for approximate multi-word names; standard Lucene, no PKM exposes it meaningfully

**Defer to v2.4+:**
- Named layouts: model-provided full manifest integration — requires manifest schema extension + model loader; lower immediate user value than user-saved layouts
- Carousel views: cross-model view composition and user-added views — needs design review
- Per-note property visibility stored in RDF — pollutes data graph with UI state; `localStorage` per-IRI is acceptable

**Anti-features to avoid:** Animated cube-flip / 3D carousel (HIGH cost, zero functional gain, maintenance burden); auto-detected view type from content (unreliable heuristics); global layout overriding all workspaces (VS Code itself doesn't have this for good reason).

### Architecture Approach

The three-layer architecture (browser htmx + vanilla JS / FastAPI / RDF4J) is unchanged. Phase A scopes the dockview migration to the inner editor-pane area only — the outer three-column Split.js split (nav / editor / right pane) is untouched in v2.3. The key integration seam is `workspace-layout.js`'s `recreateGroupSplit()` function, which is replaced wholesale by a dockview initialization call. `WorkspaceLayout` is retained as a tab metadata registry (label, dirty, typeIcon); dockview owns the layout geometry. SemPKM custom events (`sempkm:tab-activated`, `sempkm:tabs-empty`) are dispatched from dockview event callbacks, preserving the event contract for all consumers unchanged.

**Major components and their v2.3 changes:**

1. **`workspace-layout.js` (MODIFIED)** — replace `recreateGroupSplit()` and HTML5 drag-drop with dockview API; keep `WorkspaceLayout` as metadata registry; wire events to dockview callbacks
2. **`workspace.js` (MODIFIED)** — `openTab()`, `openViewTab()`, `splitRight()` call `dockview.api.addPanel()` instead of `layout.addTabToGroup()`; add `loadCarouselBar()`; add named layout command palette entries
3. **`named-layouts.js` (NEW)** — `saveNamedLayout()`, `loadNamedLayout()`, auto-save debounce, localStorage persistence; fetch() to `POST /api/layouts`
4. **`backend/app/layouts/` (NEW)** — `router.py` + `service.py` for CRUD on named layouts stored as `sempkm:WorkspaceLayout` in triplestore user graph
5. **`ViewSpecService` (MODIFIED)** — add `view_order` and `is_default_view` to `ViewSpec` dataclass; new `GET /browser/views/carousel/{type_iri}` endpoint; new `carousel_bar.html` template
6. **`SearchService` (MODIFIED)** — add `_normalize_query()` with length-conditional fuzzy: tokens ≥5 chars get `~1` appended; tokens <5 chars stay exact; `fuzzy` parameter defaults to False

**Build order (dependency graph):**
```
FTS-04 (2 files, independent)
    ↓
DOCK-01 (Phase A — largest change, unblocks everything)
    ↓
    ├── VIEW-02 (Carousel — backend independent, frontend after DOCK-01 stabilizes)
    └── DOCK-02 (Named layouts — requires dockview.toJSON() available)
```

### Critical Pitfalls

1. **htmx attributes silenced after dockview panel init/reparent** — call `htmx.process(params.containerElement)` in `onDidLayoutChange` for panels with ancestor-scoped selectors; use `htmx.ajax()` for content loading (htmx processes its own swaps); audit all `closest`-based `hx-target` selectors and replace with ID-based targets; verify via DevTools network tab after drag-to-new-group

2. **CodeMirror / Cytoscape render at zero-size under `onlyWhenVisible` mode** — subscribe to `params.api.onDidVisibilityChange`; call `editor.requestMeasure()` / `cy.resize()` + `cy.fit()` on becoming visible; alternatively use `always` rendering mode for panels with complex visualizations (acceptable at PKM scale of 1-4 panels)

3. **`fromJSON()` broken state when named layout references uninstalled model component** — wrap `fromJSON()` in `try/catch` inside `onReady` callback; on catch, remove invalid key from sessionStorage and call `buildDefaultLayout()`; never call `api.clear()` after a failed `fromJSON()` (causes second "Invalid grid element" error); validate `_layoutVersion` and all component names before calling `fromJSON()`

4. **Manifest schema break on carousel fields if any new field is required** — all new `ManifestSchema` fields MUST be optional with `Field(default_factory=list)` or `= None`; add a unit test that validates existing `basic-pkm/manifest.yaml` still passes `ManifestSchema.model_validate()` after the schema change; run this test in CI before any carousel rendering code

5. **Named layout stale IRIs causing silent panel failures** — serialize only panel structure (component type + position) in named layouts, not content (open IRIs); keep tab content in sessionStorage under existing `sempkm_workspace_layout` key; content state and layout state are separate concerns

6. **Fuzzy FTS noise on short tokens** — apply `~1` only to tokens ≥5 characters; use exact match for tokens <5 chars; set `fuzzyPrefixLength=2` in LuceneSail config; expose fuzzy as a user-controlled toggle defaulting to off; never apply `~2` edit distance (near-full-dictionary scan for short tokens)

7. **Dual drag-and-drop conflict** — remove the existing HTML5 tab drag implementation from `workspace-layout.js` in the same commit that adds dockview; do not run both systems in parallel even briefly

## Implications for Roadmap

Based on combined research, the natural phase structure follows the dependency graph exactly. Each phase has a clear deliverable and clean handoff to the next.

### Phase 1: FTS Fuzzy Search (FTS-04)

**Rationale:** Fully independent of all other v2.3 features. Two-file change (`search.py` + search endpoint). Ships immediately for user value while DOCK-01 preparation begins. Lowest risk. If this phase surfaces unexpected LuceneSail behavior, it is completely isolated from the layout work.

**Delivers:** Typo-tolerant search; "knowlege" finds "knowledge"; multi-word fuzzy `alice~ smith~`; fuzzy toggle in Ctrl+K palette with localStorage persistence.

**Addresses:** Table-stakes fuzzy matching; resolves user frustration with exact-keyword-only search.

**Avoids:** Pitfall 6 (short-token noise) — length-conditional fuzzy logic (`len ≥ 5` threshold) must be in `_normalize_query()` from the start.

---

### Phase 2: Dockview Phase A — Editor Pane Migration (DOCK-01)

**Rationale:** This is the prerequisite for named layouts (DOCK-02) and the carousel frontend. It is the largest and highest-risk change in v2.3. Tackle it as a dedicated phase to allow thorough testing before building features on top. The CSS bridge and CDN plan are already in place from v2.2.

**Delivers:** dockview-core replaces Split.js for the editor-group area; tab drag-to-reorder and group splitting via dockview natively; `sempkm:tab-activated` and `sempkm:tabs-empty` events from dockview callbacks with same shape; workspace layout auto-saved via `dockview.toJSON()`; old HTML5 drag system removed.

**Addresses:** The highest-dependency prerequisite; removes the custom drag system; reduces `recreateGroupSplit()` complexity.

**Avoids:** Pitfall 1 (htmx silenced) — `htmx.process()` in `onDidLayoutChange`; Pitfall 2 (CodeMirror/Cytoscape zero-size) — `onDidVisibilityChange` handlers in `panel-utils.js`; Pitfall 7 (drag conflict) — old drag system removed in same commit.

---

### Phase 3: Object View Redesign — Markdown First (VIEW-01)

**Rationale:** Pure frontend template + CSS change with zero backend dependencies. Grouped as Phase 3 because it is the lowest-risk frontend change and provides a quick user-visible win after the large DOCK-01 change. Also unblocks the carousel bar design validation (VIEW-02 must coexist visually with the 3D flip toggle).

**Delivers:** Properties collapsed by default in `object_view.html`; "N properties" badge in `<summary>`; title and type always visible; `localStorage` persistence per object IRI; single-click reveal; existing CSS 3D flip to edit mode unaffected.

**Addresses:** Table-stakes "properties hidden by default"; Notion's "N hidden properties / Show" pattern; top Obsidian UX complaint.

---

### Phase 4: Carousel Views (VIEW-02) + Bug Fixes (BUG-01, BUG-03)

**Rationale:** Backend work (ViewSpec vocabulary, new endpoint, new template) is independent of DOCK-01 but the frontend carousel bar wires into dockview panels — complete DOCK-01 first. BUG-03 (broken view switch buttons) is fixed as a side effect of adding the carousel bar; fold BUG-01 (group-by in concept cards) into this phase since it touches the same ViewSpec code.

**Delivers:** `sempkm:viewOrder` and `sempkm:isDefaultView` on ViewSpec; `GET /browser/views/carousel/{type_iri}` endpoint; `carousel_bar.html` partial; tab bar above object view body; active view persisted in `localStorage` per type IRI; BUG-03 removed; BUG-01 fixed.

**Addresses:** Differentiator "manifest-declared carousel views per type"; fixes two v2.2 bugs as side effects.

**Avoids:** Pitfall 4 (manifest schema break) — all new fields optional with defaults; backward-compat unit test added before any rendering code; Pitfall 6 (carousel animation over-engineering) — tab-based instant switch, no animation unless trivially added; `prefers-reduced-motion` respected.

---

### Phase 5: Named Workspace Layouts (DOCK-02) + BUG-02 (VFS Settings UI)

**Rationale:** Strictly depends on DOCK-01 (needs `dockview.toJSON()`). Groups BUG-02 (VFS Settings UI restore) as an independent fix in the same deployment window.

**Delivers:** `localStorage` + backend API named layouts; ninja-keys actions "Layout: Save as...", "Layout: Restore [name]", "Layout: Delete [name]"; `backend/app/layouts/` router + service; `named-layouts.js` with auto-save debounce; BUG-02 VFS Settings UI restored.

**Addresses:** Table-stakes "layout persistence"; differentiator "user-named saved layouts with Command Palette restore".

**Avoids:** Pitfall 3 (fromJSON broken state) — `try/catch` in `onReady`, no `api.clear()`, `buildDefaultLayout()` fallback; Pitfall 5 (stale IRI serialization) — serialize only panel structure, not open object IRIs.

---

### Phase Ordering Rationale

- **FTS-04 first** — fully independent, immediate user value, negligible risk; validates LuceneSail fuzzy on real data before the milestone is occupied with DOCK-01.
- **DOCK-01 second** — critical-path prerequisite for DOCK-02 and carousel frontend; isolated as a dedicated phase for focused testing before layering features on top.
- **VIEW-01 third** — pure frontend, unblocks carousel header layout design, quick win after the large DOCK-01 change.
- **VIEW-02 fourth** — backend can start in parallel with DOCK-01; full integration test needs DOCK-01 stable; bug fixes (BUG-01, BUG-03) fall naturally here.
- **DOCK-02 last** — strictest dependency (DOCK-01 must be live); highest design complexity (layout vs. content separation, triplestore user preferences pattern).

### Research Flags

Phases likely needing `/gsd:research-phase` during planning:
- **Phase 4 (VIEW-02 Carousel):** Frontend carousel bar + 3D flip toggle coexistence needs a visual prototype before implementation. The carousel tab bar must work within the object view header without clutter — prototype the layout before committing to a full implementation plan.
- **Phase 5 (DOCK-02 Named Layouts):** The layout/content separation design and the triplestore user preferences storage pattern (`urn:sempkm:user:{id}:layouts` named graph) are first-use in this codebase. A design doc with SPARQL examples should precede implementation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (FTS-04):** LuceneSail `term~1` syntax is HIGH confidence from official docs. Two-file change. No design ambiguity.
- **Phase 2 (DOCK-01):** dockview API is fully documented; committed in DEC-04; prior phase-23 RESEARCH.md covers htmx integration in detail.
- **Phase 3 (VIEW-01):** Pure template + CSS. Notion/Obsidian pattern is well-understood. No backend changes.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | dockview-core 4.11.0 API confirmed via official docs + TypeDocs; LuceneSail fuzzy confirmed via RDF4J official javadoc; CSS scroll-snap browser support confirmed via MDN; no new Python packages required |
| Features | MEDIUM-HIGH | Obsidian/Notion patterns verified via web search; dockview API confirmed via official docs; carousel UX inferred from Notion tab patterns + VS Code model; first-party SemPKM manifest structure analyzed directly |
| Architecture | HIGH | Based on direct codebase analysis of `workspace-layout.js` (1074 lines), `workspace.js`, `ViewSpecService`, `SearchService`, `ManifestSchema`, `dockview-sempkm-bridge.css`; prior phase-23 RESEARCH.md; DECISIONS.md DEC-04 |
| Pitfalls | HIGH | dockview htmx silencing and fromJSON broken state confirmed via GitHub issues #341, #718, #996 and official dockview docs; LuceneSail fuzzy noise from Apache Lucene FuzzyQuery docs; manifest schema pitfall from direct Pydantic analysis |

**Overall confidence: HIGH**

### Gaps to Address

- **Carousel bar + 3D flip toggle visual coexistence:** The existing CSS 3D flip to edit mode sits in the same object view header where the carousel tab bar must appear. The exact layout is unresolved. Prototype before committing to VIEW-02 implementation.
- **Dockview rendering mode inventory:** The full list of panel types that need `always` mode vs. `onlyWhenVisible` is not inventoried. Do this inventory at the start of DOCK-01.
- **LuceneSail fuzzy on real SemPKM data:** The 5-character threshold and `~1` edit distance are theoretically correct but untested against the actual `basic-pkm` dataset. Run spot-checks during FTS-04 development and adjust thresholds before exposing the fuzzy UI toggle.
- **User preference storage in triplestore:** Named layouts (DOCK-02) require storing user preferences as RDF in a user-specific named graph. This is the first such pattern in SemPKM. Validate the SPARQL UPDATE + SELECT pattern for this graph before committing to the `LayoutService` design.

## Sources

### Primary (HIGH confidence)

- [dockview.dev official docs](https://dockview.dev/docs/) — `createComponent`, `addPanel`, `toJSON`/`fromJSON`, `onDidLayoutChange`, `onDidActivePanelChange`, `onDidVisibilityChange`, rendering modes
- [dockview TypeDocs v4.13.1](https://dockview.dev/typedocs/modules/dockview_core.html) — type-level API reference
- [dockview GitHub Issue #341](https://github.com/mathuo/dockview/issues/341) — `fromJSON()` broken state after `api.clear()` in catch block
- [dockview GitHub Issue #718](https://github.com/mathuo/dockview/issues/718) — `always` rendering mode use case
- [dockview GitHub Issue #996](https://github.com/mathuo/dockview/issues/996) — panel content loss on DOM reparenting
- [RDF4J LuceneSail Javadoc 5.1.3](https://rdf4j.org/javadoc/latest/org/eclipse/rdf4j/sail/lucene/LuceneSail.html) — `fuzzyPrefixLength`, confirmed parameters
- [RDF4J LuceneSail documentation](https://rdf4j.org/documentation/programming/lucene/) — fuzzy `term~`, wildcard `term*`, proximity search syntax
- [htmx `htmx.process()` docs](https://htmx.org/api/) — canonical re-init call for external DOM mutations
- [VS Code Custom Layout docs](https://code.visualstudio.com/docs/configure/custom-layout) — layout save behavior reference
- [Notion database views guide](https://www.notion.com/help/guides/using-database-views) — tab-based instant switching (official docs)
- SemPKM `.planning/DECISIONS.md` — DEC-04 dockview migration plan, Phase A/B/C scope
- SemPKM `.planning/research/phase-23-ui-shell/RESEARCH.md` — htmx integration patterns, layout storage design
- SemPKM codebase: `workspace-layout.js`, `workspace.js`, `views/service.py`, `search.py`, `manifest.py`, `dockview-sempkm-bridge.css` — direct analysis

### Secondary (MEDIUM confidence)

- [MDN: Creating CSS Carousels](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Overflow/Carousels) — scroll-snap carousel pattern
- [Notion Layout Builder 2024](https://www.simonesmerilli.com/life/notion-layouts) — properties hidden-by-default UX (third-party tutorial)
- [Obsidian Properties collapse request thread](https://forum.obsidian.md/t/add-setting-to-collapse-fold-properties-across-all-notes-by-default/67943) — confirms native collapse-by-default does not exist; active 2023-2025
- [Lucene fuzzy syntax rdf4j-users thread](https://groups.google.com/g/rdf4j-users/c/k04xjxM_wBI) — edit distance integer 0-2, not fractional similarity
- [VS Code named layout issue #156160](https://github.com/microsoft/vscode/issues/156160) — confirms VS Code has no native global named layouts

### Tertiary (LOW confidence)

- Carousel UX inferred from Notion tab patterns + VS Code model — no direct PKM precedent for manifest-declared per-type view carousels; this is a novel UX primitive

---
*Research completed: 2026-03-01*
*Ready for roadmap: yes*
