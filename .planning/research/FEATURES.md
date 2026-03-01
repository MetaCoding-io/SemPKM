# Feature Research: v2.3 Shell, Navigation & Views

**Domain:** IDE-style PKM workspace — object view redesign, carousel views, named layouts, fuzzy FTS
**Researched:** 2026-03-01
**Confidence:** MEDIUM-HIGH (Obsidian/Notion/LuceneSail patterns verified via web search; dockview API confirmed via official docs; carousel UX inferred from Notion tab patterns + VS Code model)

---

## Scope

This file covers only the **new features in v2.3**. The general PKM feature landscape (table stakes vs. differentiators for the whole product) lives in `.planning/milestones/research/FEATURES.md`. The four feature areas researched here:

1. **Object view redesign** — markdown-first, properties hidden by default
2. **Carousel views** — per-type manifest-declared view rotation
3. **Named layouts** — save/restore panel arrangements
4. **FTS fuzzy search** — approximate-match on top of existing LuceneSail FTS

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that users of mature PKM tools assume exist. Missing these makes v2.3 feel incomplete or regressive.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Properties hidden/collapsed by default in object view | Notion (2024 Layout Builder) puts properties in optional hidden-by-default side panel. Obsidian users overwhelmingly request default-collapsed properties — it's the top properties UX complaint (active forum thread 2023-2025, still unimplemented natively). Content should be visible without scrolling past metadata. | LOW | Toggle link: "N hidden properties / Show". State persists per-session or per-object via `localStorage`. Pure CSS + JS toggle; no backend changes. |
| Single-click reveal for collapsed properties | Users expect one click to expand the properties section inline. Two-step flows (modal, separate page) are rejected in every tool. | LOW | `<details>/<summary>` or custom expand chevron. No animation required — instant show/hide is acceptable and matches Notion's approach. |
| View switcher for object-level views | Notion database view tabs (Table / Board / Calendar) are the dominant mental model. Users expect to switch between "markdown view" and "diagram view" without leaving the object. Tab-based (not animated) is the universal standard. | MEDIUM | Tab bar above content area. Notion, Obsidian (Reading/Editing toggle), and VS Code all use instant tab switches without animation. |
| Layout persistence across sessions | VS Code restores the last-used layout on reopen. Users expect workspace arrangement to survive page reload. | LOW | dockview `toJSON()`/`fromJSON()` + `localStorage`. Confirmed available in dockview-core API. |
| Fuzzy/approximate matching in search | Every modern search (Obsidian file switcher, Notion search) expects "roam" to find "roaming". Exact-only keyword search frustrates users who mistype. | LOW | LuceneSail supports `term~` tilde syntax natively (Levenshtein distance, configurable). No new infrastructure — query transformation only in `SearchService`. |

### Differentiators (Competitive Advantage)

Features that go beyond what any single competitor offers. These justify the v2.3 milestone.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Manifest-declared carousel views per type | No consumer PKM lets Mental Model authors declare "this type supports these three view modes." Notion has database views but they're user-configured, not type-schema-declared. This is a new UX primitive — Mental Model authors curate the view experience. | HIGH | Requires `sempkm:showInCarousel` + `sempkm:carouselOrder` on ViewSpec. Backend must serve ordered view list per type. Frontend renders tab bar from that list. |
| Model-provided named layouts | VS Code has per-workspace layouts (one per project, no names). SemPKM can offer model-provided defaults: "The Research model opens with Graph on left, Object detail on right." No PKM tool has this as a model-declared default. | MEDIUM | dockview `fromJSON()` with model-bundled JSON layout object. The manifest `exports.dashboards` array already has a slot for this — extend or repurpose as `exports.layouts`. |
| User-named saved layouts with Command Palette restore | VS Code extensions (Restore Editors) do this; VS Code native does not (open GitHub issue #156160). SemPKM can have it natively, integrated into the existing ninja-keys Command Palette. | MEDIUM | `localStorage` array of `{id, name, layout: SerializedDockview}`. Save via "Save Layout As..." in Command Palette, restore via "Restore layout: [name]". |
| LuceneSail wildcard + fuzzy composing | `alice~ smith~` to find approximate multi-word names in one pass. Standard Lucene supports this but no PKM tool exposes it meaningfully. | LOW | Pure query transformation in `SearchService`. Expose as "Fuzzy" toggle in Ctrl+K palette. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Animated cube-flip / 3D carousel between views | "Looks cool" — Notion-style smooth view transitions, or extending the existing CSS 3D flip to view switching. | HIGH implementation cost for zero functional gain. CSS 3D transforms break on resize, dark mode, and embedded iframes. The existing read/edit flip is already a maintenance burden — expanding it would compound the problem. | Tab-based switcher, instant show/hide. This is what Notion, Obsidian, and VS Code all use. |
| Per-note property visibility stored in RDF | "I want this note's properties always visible" — per-object persistent preference in the triplestore. | Adds a new triple per object per user preference. Pollutes the data graph with UI state. Requires event-sourcing even for UI prefs, or a separate non-RDF store with more complexity. | Session-local `localStorage` keyed by object IRI. Resets on cache clear, which is acceptable for a UI preference. |
| Auto-detected view type from content | "If the body looks like a Mermaid diagram, show diagram view automatically." | Content inspection is unreliable. False positives frustrate users. Requires heuristics or ML. All reference tools use explicit user selection. | User manually selects view. Mental Model authors declare which views are available for each type — user picks from the carousel. |
| Global layout overriding all workspaces | "One layout for all projects, like a default template." | VS Code itself doesn't have this natively (open GitHub issue #156160) because it creates conflicts between workspace-specific needs. Zed also has no global named layouts. | Per-workspace layout persistence. Model-provided layouts as sensible starting points for new workspaces. |

---

## Feature Dependencies

```
[Object view redesign: markdown-first]
    └──depends on──> [Existing read-only object view (v2.0 CSS 3D flip)]
    └──uses──> [CSS token system (v2.2 108-token architecture)]
    └──independent of──> [DOCK-01 (no dockview required for this feature)]

[Carousel views (VIEW-02)]
    └──requires schema change──> [ViewSpec: sempkm:showInCarousel, sempkm:carouselOrder]
    └──requires new endpoint──> [GET /api/objects/{iri}/views returning ordered view list]
    └──requires frontend work──> [Tab bar component in object view header]
    └──affects existing model──> [basic-pkm.jsonld ViewSpecs need carousel metadata]
    └──fixes as side effect──> [BUG-03: broken view switch buttons]
    └──conflicts with──> [Animated cube-flip anti-feature]

[Named layouts: user-saved (DOCK-02 part A)]
    └──requires first──> [DOCK-01: dockview Phase A must be live to have api.toJSON()]
    └──uses──> [dockview api.toJSON() / api.fromJSON() — confirmed in official docs]
    └──integrates with──> [Ctrl+K command palette (ninja-keys infrastructure)]

[Named layouts: model-provided (DOCK-02 part B)]
    └──requires first──> [DOCK-01]
    └──requires schema change──> [manifest.schema.json: exports.layouts array]
    └──requires backend work──> [Mental Model loader: extract and store layout JSON on install]

[FTS fuzzy search (FTS-04)]
    └──requires existing──> [FTS-01/02/03 (v2.2 LuceneSail) — already shipped]
    └──no new infrastructure──> [Tilde syntax is native Lucene QueryParser pass-through]
    └──integrates with──> [Ctrl+K palette fuzzy toggle, SearchService.search() parameter]
    └──independent of──> [DOCK-01, VIEW-02, VIEW-01]
```

### Dependency Notes

- **Carousel views require manifest schema changes.** `sempkm:showInCarousel` and `sempkm:carouselOrder` must be added to the ViewSpec vocabulary and the basic-pkm model. This is a minor but breaking change to the model format — all existing ViewSpecs that should appear in the carousel need these properties added. The manifest JSON schema (`orig_specs/spec/mental-model/manifest.schema.json`) does not need changes since these are ViewSpec-level properties, not manifest-level.

- **Named layouts require dockview Phase A first.** `api.toJSON()` is the dockview serialization method. Until dockview replaces Split.js (DOCK-01), there is no serializable layout object. Named layouts (DOCK-02) cannot ship before DOCK-01 completes.

- **FTS fuzzy is fully independent.** The tilde operator (`roam~`) is native Apache Lucene query parser syntax, which LuceneSail passes through unchanged. Only `SearchService.search()` needs a `fuzzy` parameter. This can ship in any phase order — even before DOCK-01.

- **Object view redesign is the lowest-risk feature.** Pure frontend CSS/HTML change to `object_view.html`. No backend API changes, no manifest changes, no infrastructure. Can ship first as a standalone phase.

---

## MVP Definition for v2.3

### Ship With (v2.3 Core)

- [x] **Markdown-first object view (VIEW-01)** — properties collapsed by default, single-click reveal, `localStorage` persistence per object IRI. Zero backend changes. Unblocked immediately.
- [x] **FTS fuzzy search (FTS-04)** — `fuzzy` parameter in `SearchService.search()`, "Fuzzy" toggle in Ctrl+K palette. Zero new infrastructure. Unblocked immediately.
- [x] **Dockview Phase A (DOCK-01)** — prerequisite for named layouts. High effort but already committed in DEC-04.
- [x] **Named layouts: user-saved (DOCK-02)** — `localStorage` layout array, save/restore via Command Palette. Requires DOCK-01.

### Add If DOCK-01 Completes Early

- [ ] **Carousel views: frontend tab switcher (VIEW-02)** — tab bar reads from ViewSpec data, instant switch, no animation. Requires manifest schema + backend endpoint.
- [ ] **Model-provided default layouts** — manifest `exports.layouts`, applied on model install.

### Defer to v2.4+

- [ ] **Named layouts: model-provided (full manifest integration)** — requires manifest schema extension + model loader. Medium complexity, lower immediate user value than user-saved layouts.
- [ ] **Carousel views: advanced composition** — cross-model view carousels, user-added views to carousel. Needs design review.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Markdown-first object view (properties hidden) | HIGH | LOW | P1 |
| FTS fuzzy search (tilde operator) | HIGH | LOW | P1 |
| Dockview Phase A (DOCK-01) | HIGH | HIGH | P1 (prerequisite for layout features) |
| Named layouts: user-saved | MEDIUM | MEDIUM | P2 (after DOCK-01) |
| Bug fixes (BUG-01, BUG-03) | MEDIUM | LOW | P1 (fold into VIEW-02 or standalone) |
| Carousel views: manifest + tab switcher | MEDIUM | MEDIUM | P2 |
| Named layouts: model-provided | LOW | MEDIUM | P3 |
| Bug fix BUG-02 (VFS Settings UI) | MEDIUM | LOW | P2 (independent, restore only) |

---

## Competitor Feature Analysis

### Property Drawer UX Patterns

| Tool | Default State | Reveal Mechanism | Persistence |
|------|--------------|-----------------|-------------|
| Notion 2024 (Layout Builder) | Properties in optional right side panel, **hidden by default** | Toggle panel button top-right of page | Per-database, user preference |
| Notion classic | All properties visible; individual properties hideable | "X hidden properties / Show" link at bottom of list | Per-database-view setting |
| Obsidian v1.4+ | Properties shown at top of note; **no collapse-by-default setting** (active unimplemented feature request 2023-2025) | Manual click on chevron per-note only | Per-note, resets on reopen |
| Logseq | Inline `key:: value` block properties; system props hidden by `:block-hidden-properties` config | Config-based or CSS; no UX toggle | Global config only |

**Takeaway for SemPKM:** Notion's "X hidden properties / Show" link (classic) is the right pattern for the object view — simpler than a side panel (no dockview required), fits the single-panel object view, and is the most recognizable progressive disclosure pattern in the space. Show 0-1 "pinned" properties always; hide the rest under the reveal link.

### View Switcher UX Patterns

| Tool | Trigger | Animation | State Persistence |
|------|---------|-----------|------------------|
| Notion database views | Tab bar above content | None (instant) | Per-database, per-user |
| VS Code editors | Tab bar, "Open to Side" context menu | None (instant) | Per-workspace file |
| Obsidian (Reading/Editing toggle) | Toggle button in tab header | None (instant) | Per-file |
| Obsidian plugins (e.g., Kanban) | Right-click tab context menu | None (instant) | Per-file, per plugin |

**Takeaway for SemPKM:** Tab bar is the universal approach. No tool in the space uses animated view rotation in production. Tabs: show view names (e.g., "Markdown", "Graph", "Diagram"); active tab uses accent color matching existing tab styling; tab bar sits in the object view header above the body content.

### Named Layout UX Patterns

| Tool | Mechanism | Scope | User-Named? |
|------|-----------|-------|-------------|
| VS Code native | Auto-save/restore per `.code-workspace` file | Per workspace file | No (one layout per workspace) |
| VS Code Restore Editors extension | Command Palette "Save/Restore Saved Layout" | Per workspace folder | Yes |
| VS Code Profiles | Full profile creation with layout | Global | Yes (profile name) |
| Zed editor | `~/.config/zed/` workspace serialization | Per workspace | No |
| dockview `api.toJSON()` | Returns `SerializedDockview` JSON object | Per instance | No native names — caller manages |

**Takeaway for SemPKM:** VS Code native is the mental model users have (auto-restore last layout). The Restore Editors extension pattern (named + Command Palette) is the upgrade that users want but VS Code doesn't provide natively (confirmed via open GitHub issue). SemPKM can deliver this natively with minimal effort since ninja-keys is already integrated.

### FTS Fuzzy Syntax (LuceneSail)

| Syntax | Meaning | Example Match |
|--------|---------|---------------|
| `roam~` | Fuzzy, edit distance ≤ 2 (default) | roam, foam, roams, roaming |
| `roam~1` | Fuzzy, edit distance ≤ 1 (tighter) | roam, roams, foam |
| `alic*` | Prefix wildcard | alice, alicia, alicent |
| `"hotel airport"~5` | Proximity: within 5 words | "hotel near the airport" |
| `alice~ smith~` | Fuzzy on each word | alise smyth, alica smit |

**Takeaway for SemPKM:** Auto-append `~1` (not `~2`) to each term when fuzzy mode is enabled — edit distance 1 reduces false positives while still catching common typos ("aliec" → "alice"). Do not use decimal similarity values (legacy Lucene; causes ParseException in newer versions). The `SearchService` transformation: split on whitespace, skip tokens that already contain `~`, `*`, `?`, or are quoted phrases, append `~1` to the rest.

---

## Implementation Notes by Feature

### Feature 1: Markdown-First Object View (VIEW-01)

**What to build:** In `object_view.html` (read-only mode), reorder layout to show body Markdown content prominently first. Move properties into a collapsible `<details>` section above or below the title with a `<summary>` showing the count. Default: closed.

**Key behaviors:**
- Properties section `open` state stored in `localStorage` as `sempkm_props_open_{base64IRI}` = `true|false`
- Default: `false` (body-first on first load for any object)
- The existing CSS 3D flip to edit mode is unaffected — this changes only the read-only view layout
- "N properties" badge visible in the `<summary>` even when collapsed, so users know content exists
- "Pinned" properties (title, type) remain always visible above the collapsible block — they are the object identity, not detail

**Affected files:** `backend/app/templates/workspace/object_view.html`, `frontend/static/css/workspace.css`

**Confidence:** HIGH — pure template + CSS change, well-understood from Notion/Obsidian research

### Feature 2: Carousel Views (VIEW-02)

**What to build:**
1. Extend ViewSpec vocabulary: add `sempkm:showInCarousel` (boolean) and `sempkm:carouselOrder` (integer) to the sempkm ontology
2. Update `models/basic-pkm/views/basic-pkm.jsonld` to mark ViewSpecs with these properties
3. Add backend method: `ViewSpecService.get_carousel_views(type_iri)` returning ordered list of `{id, label, rendererType}`
4. In `object_view.html`, add a tab bar above the body that shows available carousel views; htmx-swaps the content area on tab click
5. Active view state stored in `localStorage` as `sempkm_active_view_{typeIRI}` = `"{viewSpecId}"`

**Key behaviors:**
- Only ViewSpecs with `sempkm:showInCarousel: true` appear in the tab bar
- The "default" view (lowest `sempkm:carouselOrder`) loads first unless `localStorage` has a saved preference
- At most 5 tabs shown (Mental Model author responsibility to curate; more than 5 is an anti-pattern)
- Tab styling uses existing `.tab`, `.tab-active` CSS classes for consistency

**Risk:** The 3D flip edit toggle sits in the same object view header. The carousel tab bar must coexist without visual clutter. Design must be validated before implementation.

**Confidence:** MEDIUM — backend and vocabulary are straightforward; the frontend interaction with the flip toggle needs prototyping

### Feature 3: Named Layouts (DOCK-02)

**What to build (after DOCK-01):**
- `localStorage` key `sempkm_layouts`: `Array<{id: string, name: string, layout: SerializedDockview, savedAt: ISO8601}>`
- ninja-keys actions: "Layout: Save as...", "Layout: Restore [name]", "Layout: Delete [name]"
- Error recovery: if `fromJSON()` throws (e.g., panel component names changed after model uninstall), catch the error, remove the broken entry from `sempkm_layouts`, and load the default layout
- Model-provided layouts stored separately in `sempkm_model_layouts`: `Array<{modelId, name, layout}>` populated on model install, cleared on model uninstall

**dockview API (confirmed):**
```javascript
// Save
const layout = api.toJSON(); // returns SerializedDockview
// Restore
api.fromJSON(layout); // throws if invalid, clears state
// Listen for changes
api.onDidLayoutChange(() => { /* auto-save if needed */ });
```

**Confidence:** HIGH for user-saved layouts. MEDIUM for model-provided layouts (manifest schema extension needed).

### Feature 4: FTS Fuzzy Search (FTS-04)

**What to build:**
- Add `fuzzy: bool = False` parameter to `SearchService.search(query, type_filter, limit, fuzzy=False)`
- When `fuzzy=True`: split query on whitespace, for each token that does not contain `~`, `*`, `?`, or start/end with `"`, append `~1`
- Add "Fuzzy" toggle to the Ctrl+K palette search UI (checkbox or button); persist toggle state in `localStorage` as `sempkm_fts_fuzzy`
- Default `fuzzy=False` to preserve existing exact-keyword behavior

**Query transformation examples:**
```
Input: "alice smith"          → fuzzy off: "alice smith"
Input: "alice smith"          → fuzzy on:  "alice~1 smith~1"
Input: "alice*"               → fuzzy on:  "alice*"  (wildcard, no change)
Input: "\"alice smith\"~5"    → fuzzy on:  "\"alice smith\"~5"  (proximity phrase, no change)
Input: "alice smith~"         → fuzzy on:  "alice~1 smith~"  (already has ~, no double-append)
```

**Confidence:** HIGH — LuceneSail passes query strings directly to Apache Lucene QueryParser. Tilde syntax confirmed via rdf4j.org official docs and rdf4j-users Google Groups.

---

## Bug Fix Context

The following v2.2 bugs affect or are adjacent to features being redesigned in v2.3:

| Bug | Affected Feature | Recommended Fix |
|-----|-----------------|-----------------|
| BUG-03: Graph/card/table view switch buttons broken | Carousel views (VIEW-02) | Remove broken buttons as part of adding proper carousel tab bar. The carousel tab bar replaces them. |
| BUG-01: Group-by in concept cards view broken | Carousel views (VIEW-02) | Likely a SPARQL query or renderer config issue in `view-concept-card`. Fix concurrently with VIEW-02 basic-pkm model updates. |
| BUG-02: VFS Settings UI lost during debugging | Independent | Restore as a standalone bug-fix phase. Not related to view redesign or carousel. |

---

## Sources

- [Obsidian Properties — official help](https://help.obsidian.md/properties) — MEDIUM confidence, official current docs
- [Add setting to collapse Properties by default — Obsidian Forum](https://forum.obsidian.md/t/add-setting-to-collapse-fold-properties-across-all-notes-by-default/67943) — confirms native collapse-by-default does NOT exist as of 2025; HIGH confidence (multiple active community threads)
- [Notion Layout Builder 2024 — Notion layouts guide](https://www.simonesmerilli.com/life/notion-layouts) — MEDIUM confidence (third-party tutorial, 2024)
- [Hide Notion Properties tutorial 2024](https://templatesfornotion.com/post/hide-notion-properties) — MEDIUM confidence; confirms "X hidden properties / Show" UX pattern
- [Notion database views guide](https://www.notion.com/help/guides/using-database-views) — HIGH confidence (official Notion docs); tab-based instant switching
- [Full-Text Indexing With the Lucene SAIL — rdf4j.org](https://rdf4j.org/documentation/programming/lucene/) — HIGH confidence (official RDF4J docs); tilde fuzzy syntax
- [LuceneSail GitHub doc](https://github.com/eclipse-rdf4j/rdf4j-doc/blob/master/site/content/documentation/programming/lucene.md) — HIGH confidence (official source); wildcard + fuzzy syntax
- [Saving State — dockview.dev](https://dockview.dev/docs/core/state/save/) — HIGH confidence (official dockview docs); `api.toJSON()` confirmed
- [Loading State — dockview.dev](https://dockview.dev/docs/core/state/load/) — HIGH confidence; `fromJSON()` error handling
- [VS Code Custom Layout docs](https://code.visualstudio.com/docs/configure/custom-layout) — HIGH confidence (official); layout save behavior
- [Option to save panel layouts globally — VS Code issue #156160](https://github.com/microsoft/vscode/issues/156160) — HIGH confidence; confirms VS Code has NO native global named layouts
- [Restore Editors VS Code extension](https://marketplace.visualstudio.com/items?itemName=amodio.restore-editors) — MEDIUM confidence; named layout UX reference
- SemPKM `.planning/PROJECT.md` — HIGH confidence; existing feature inventory and v2.3 requirements
- SemPKM `.planning/DECISIONS.md` — HIGH confidence; DEC-04 dockview migration plan, CSS token architecture
- SemPKM `models/basic-pkm/views/basic-pkm.jsonld` — HIGH confidence (first-party); existing ViewSpec structure
- SemPKM `orig_specs/spec/mental-model/manifest.schema.json` — HIGH confidence (first-party); manifest schema

---

*Feature research for: v2.3 Shell, Navigation & Views*
*Researched: 2026-03-01*
