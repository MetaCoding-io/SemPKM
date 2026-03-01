# Pitfalls Research

**Domain:** v2.3 Shell, Navigation & Views — dockview-core migration, manifest-driven carousel views, named layouts, LuceneSail fuzzy FTS
**Researched:** 2026-03-01
**Confidence:** HIGH for dockview-core lifecycle and htmx integration (codebase analysis + GitHub issues); HIGH for LuceneSail fuzzy API (official javadoc); MEDIUM for carousel schema patterns (synthesized from manifest structure analysis); MEDIUM for named layout invalidation patterns (dockview issue tracker + general serialization research)

---

## Critical Pitfalls

### Pitfall 1: htmx Attributes Silenced After Dockview Panel Init

**What goes wrong:**
When dockview creates a panel, its `init(params)` hook fires and you inject HTML via `params.containerElement.innerHTML = ...` or via `htmx.ajax()`. Any `hx-*` attributes in that HTML are dead — htmx was not involved in the injection and never processed the new nodes. Clicks, triggers, and boosts all silently do nothing.

**Why it happens:**
htmx attaches event listeners during `htmx:load`, which fires only for content that htmx itself swaps in via its request cycle. DOM mutations performed by third-party code (including dockview's internal DOM reparenting during drag-to-dock) are invisible to htmx. HTMX does not use a MutationObserver; it only processes nodes it controls.

Additionally, when a user drags a panel to a new group, dockview physically moves `params.containerElement` to a new position in the DOM. Any htmx state bound to that element's ancestors (e.g., `hx-boost`, `hx-indicator` climbing to a parent) may now point to a different ancestor or none at all. The htmx internal state for the moved element is not invalidated — it stays bound to the old ancestor chain.

**How to avoid:**
Call `htmx.process(params.containerElement)` at the end of every panel `init()` hook that injects `hx-*` markup. This is the canonical re-init call. In the `onDidLayoutChange` handler (fired after any drag-reorder), also call `htmx.process()` on the moved panel's container element. For panels loaded via `htmx.ajax()`, htmx processes the swapped content itself — no extra call needed, but verify via integration test.

Audit `workspace-layout.js` for any `hx-target` selectors that climb an ancestor chain using `closest`. These will break after panel reparenting. Replace them with ID-based targets or `hx-target="this"`.

```javascript
// Panel component init — re-register htmx on injected content
return {
  init: function(params) {
    htmx.ajax('GET', url, {
      target: params.containerElement,
      swap: 'innerHTML'
    });
    // htmx.ajax swaps via htmx — no extra process() needed here.
    // But for any innerHTML set directly:
    // params.containerElement.innerHTML = someHtml;
    // htmx.process(params.containerElement);
  }
};
```

**Warning signs:**
- htmx-powered buttons in panels do nothing after drag-to-dock
- `hx-get` links that work when panel first opens but stop working after moving panel to a new group
- No network requests visible in DevTools when clicking htmx elements in moved panels

**Phase to address:**
DOCK-01 Phase A. Verify with an integration test: open a panel, drag it to a new group, click an htmx element, confirm a network request fires.

---

### Pitfall 2: CodeMirror and Cytoscape Render as Zero-Width Under Dockview's Default Rendering Mode

**What goes wrong:**
Dockview's default rendering mode is `onlyWhenVisible`. When a panel is hidden (e.g., user switches to another tab in the same group), dockview removes the panel's container element from the DOM tree. The element still exists in memory but is detached. CodeMirror and Cytoscape both measure the container dimensions at initialization and cache them. When the panel becomes visible again and the container is reattached, CodeMirror shows an unstyled textarea or a 0px-height editor; Cytoscape shows a blank white box. Both components need an explicit re-measure call after reattach.

**Why it happens:**
Both CodeMirror (5 and 6) and Cytoscape.js compute their viewport dimensions from the DOM at init time and do not automatically re-layout on reattachment. `ResizeObserver` callbacks fire with `contentRect.width = 0` and `contentRect.height = 0` while the container is detached, which some observers interpret as "nothing to do." When the container is reattached at its true size, many observers do not re-fire unless the size actually changes from the last observed value.

**How to avoid:**
Use dockview's `onDidVisibilityChange` event on each panel's API to detect the moment the panel becomes visible:

```javascript
return {
  init: function(params) {
    var editor = initCodeMirror(params.containerElement);

    var disposable = params.api.onDidVisibilityChange(function(event) {
      if (event.isVisible) {
        // CodeMirror 6
        editor.requestMeasure();
        // CodeMirror 5
        // editor.refresh();
      }
    });
    // Store disposable for cleanup in dispose()
    params._disposables = [disposable];
  },
  dispose: function(params) {
    (params._disposables || []).forEach(function(d) { d.dispose(); });
  }
};
```

For Cytoscape: call `cy.resize()` in the same `onDidVisibilityChange` handler. For the graph view specifically, also call `cy.fit()` unless the user has explicitly panned — track pan state with a flag.

Alternatively, switch the rendering mode to `always` for panels known to contain CodeMirror or Cytoscape. This keeps them in the DOM but hidden with `display: none`. The trade-off is slightly higher memory use; acceptable for the typical 1-4 open panels in SemPKM.

**Warning signs:**
- CodeMirror editor appears blank or as a single line when panel is re-focused after being hidden
- Cytoscape graph is blank white on first show after switching back to a graph tab
- Gutter/line numbers in CodeMirror are misaligned
- `cy.width()` or `cy.height()` returns 0 in the graph view component

**Phase to address:**
DOCK-01 Phase A. Document the `onDidVisibilityChange` + refresh pattern in a shared `panel-utils.js` helper so it is not forgotten for future panel types.

---

### Pitfall 3: Dockview `fromJSON()` Broken State When a Panel Component Name No Longer Exists

**What goes wrong:**
Named layouts are serialized with `api.toJSON()` and restored with `api.fromJSON()`. The serialized JSON contains component names (strings) that must match registered panel factories. If a component name in a saved layout no longer exists — because the panel was renamed, removed from the codebase, or the layout was saved with a Mental Model-contributed panel that was subsequently uninstalled — `fromJSON()` throws an error. In versions of dockview prior to approximately v4.x, calling `api.clear()` inside the `catch` block then threw a second error ("Invalid grid element"), leaving the API in an unrecoverable state requiring a full page reload and manual localStorage clear.

**Why it happens:**
The dockview serialization format stores component names as strings with no schema version. There is no built-in migration or graceful degradation. The most common trigger in SemPKM will be: a Mental Model is uninstalled, its model-provided default layout is deleted from the backend, but the user's session storage still has a persisted named layout referencing panel components from that model. On next load, `fromJSON()` fails.

**How to avoid:**
Wrap `fromJSON()` in a `try/catch` inside the `onReady` callback (not outside it). On catch, discard the saved layout and build the default layout programmatically. Do not call `api.clear()` after a failed `fromJSON()` — rely on the graceful reset behavior in current dockview versions.

```javascript
dockview.ready(function(event) {
  var saved = null;
  try {
    saved = JSON.parse(sessionStorage.getItem('sempkm_workspace_layout_dv'));
  } catch (e) { /* corrupted JSON */ }

  if (saved) {
    try {
      event.api.fromJSON(saved);
      return;
    } catch (err) {
      console.warn('SemPKM: saved layout incompatible, rebuilding default.', err);
      sessionStorage.removeItem('sempkm_workspace_layout_dv');
      // Do NOT call event.api.clear() here — rely on dockview's graceful reset.
    }
  }
  buildDefaultLayout(event.api);
});
```

Add a `_layoutVersion` field to every serialized layout blob. Before calling `fromJSON()`, validate that the version matches the current schema version AND that all component names in the blob are registered. Reject and rebuild if either check fails.

For model-provided default layouts, the backend should validate component names against the installed Mental Models before serving the layout JSON. A layout that references an uninstalled model's panel components must be flagged as invalid.

**Warning signs:**
- Workspace renders as a blank white area on load (dockview in broken state)
- Console shows "Invalid grid element" or similar dockview internal errors
- Users report workspace not loading after uninstalling a Mental Model

**Phase to address:**
DOCK-02 (Named layouts). The validation and fallback logic must be in place before any named layout feature ships. Pair with a Playwright test: install a model, create a named layout referencing model panels, uninstall the model, reload, verify workspace renders correctly.

---

### Pitfall 4: Carousel Manifest Schema Break Without a Migration Path

**What goes wrong:**
VIEW-02 (Carousel views) requires adding new fields to the Mental Model manifest — specifically, a `views` block on type declarations in manifest.yaml that lists the carousel rotation slots. If this schema addition is not backward-compatible (i.e., if the Pydantic model makes the new field required rather than optional), then all existing installed Mental Models (including `basic-pkm`) fail manifest validation on load. The model manager raises a validation error for every installed model, rendering the entire app unusable until models are manually re-archived with the new fields.

**Why it happens:**
`ManifestSchema` is a Pydantic `BaseModel`. Adding a required field to it causes `ManifestSchema.model_validate(raw)` to raise `ValidationError` for any manifest.yaml that does not include the new field. Existing on-disk archives (already extracted into `~/.sempkm/models/`) are not automatically re-validated — they are validated at load time on every startup. A breaking schema change therefore breaks every existing installation simultaneously.

**How to avoid:**
All new manifest fields that implement carousel views MUST be optional with a default value. Example:

```python
class ManifestTypeViewDef(BaseModel):
    type: str
    carousel: list[str] = Field(default_factory=list)  # ordered list of view IDs
    defaultView: str | None = None

class ManifestSchema(BaseModel):
    # ... existing fields ...
    typeViews: list[ManifestTypeViewDef] = Field(default_factory=list)  # NEW — optional
```

Never add a required field to `ManifestSchema` without simultaneously creating a migration script that rewrites all installed manifests. The migration script path should be `backend/migrations/manifests/` and run as part of the application startup manifest re-validation step.

Test the schema change by loading the existing `basic-pkm` manifest.yaml (which will NOT have the new fields) and verifying it still passes validation. Add this as a unit test in `tests/test_manifest.py`.

**Warning signs:**
- `ManifestSchema.model_validate(raw)` raises `ValidationError` for `basic-pkm` after adding the new field
- Admin portal shows all models as "validation error" on the Models page
- Object explorer shows no types (models failed to load)

**Phase to address:**
VIEW-02 (Carousel views). Add a manifest schema backward-compatibility test before writing any carousel rendering code. Run the test in CI against the shipped `basic-pkm` manifest.yaml.

---

### Pitfall 5: Named Layout Stale References to Session-Only Tab IDs

**What goes wrong:**
Named layouts saved by the user include tab content state — specifically, the IRI of the object open in each panel. When a named layout is restored in a new session, those IRIs may reference objects that have since been deleted, objects the current user does not have permission to view, or views contributed by an uninstalled Mental Model. The workspace restores successfully in dockview terms (component names are valid), but individual panels fail to load their content, showing error states or blank panels. The user cannot tell if the named layout itself is broken or if the objects are just gone.

**Why it happens:**
dockview's `toJSON()` serializes both the panel structure AND any params passed to each panel at creation time. If panel params include the IRI of the currently-open object, those IRIs are persisted verbatim. On restore, `htmx.ajax()` is called with the stale IRI and hits the backend, which returns a 404 or 403. The panel loads an error partial, but the layout structure itself is valid from dockview's perspective.

**How to avoid:**
Named layouts should serialize only the panel type (e.g., `object-editor`, `relations-panel`, `graph-view`) and the panel's position/size, NOT the content (IRI). Content is session state; layout is persistent state. These are two different things.

Store content state (open tabs and their IRIs) separately in sessionStorage under the existing `sempkm_workspace_layout` key, exactly as today. The named layout blob stores only the structural shape of the workspace. When a named layout is applied, it sets up the panel structure and then loads the session's last-known content into each panel.

If a user explicitly wants to save "layout + content" (a named snapshot that remembers which objects were open), make this a deliberate second feature called a "workspace snapshot" — not the default named layout behavior.

**Warning signs:**
- Named layout restores show blank panels instead of the last-open objects
- Console shows 404 errors for IRIs after applying a named layout
- User reports "my layout is broken" but the actual problem is deleted objects

**Phase to address:**
DOCK-02 (Named layouts). Define the separation between structural layout state and content state in the design doc before implementation. Validate with a test: save a named layout with objects A and B open, delete object A from the triplestore, restore the named layout, verify panel for object A shows a "not found" placeholder rather than a workspace error.

---

## Moderate Pitfalls

### Pitfall 6: Carousel Animation Over-Engineering

**What goes wrong:**
The "cube-flip style" carousel described in the milestone context implies a 3D CSS transform animation (perspective, rotateY, translateZ). Implementing this correctly requires: a wrapper element for perspective context, individual face elements for "front" (current view) and "back" (incoming view), careful `backface-visibility: hidden` rules, and coordinating the animation duration with the htmx content swap lifecycle. Over-engineered implementations add 200-400ms of animation time during which the panel is non-interactive, break when panels are resized mid-animation, and cause visual glitches in Firefox when `transform-style: preserve-3d` is combined with `overflow: hidden` on any ancestor.

**How to avoid:**
Start with a simpler, working animation before adding 3D effects. A fade crossfade or a vertical slide (translateY) is sufficient for v2.3 and avoids the `preserve-3d` / `overflow: hidden` ancestor conflict. Use CSS transitions, not keyframe animations, so the browser can optimize with `will-change: transform`.

Constrain the animation: the carousel should only animate on user-initiated view rotation (clicking a cycle button), not on panel resize or tab switch. Guard with a flag:

```javascript
var _isAnimating = false;
function rotateCarousel(panelEl, direction) {
  if (_isAnimating) return;
  _isAnimating = true;
  // ... apply class, swap content, remove class ...
  panelEl.addEventListener('transitionend', function() {
    _isAnimating = false;
  }, { once: true });
}
```

Cap animation duration at 150ms. Respect `prefers-reduced-motion`: if the media query is active, skip the animation entirely and swap content immediately.

**Warning signs:**
- Panel content is visible through the "back" of the flip (missing `backface-visibility: hidden`)
- Animation stutter when panel width is less than ~300px
- Firefox shows a blank white flash during the flip

**Phase to address:**
VIEW-02 (Carousel views). Keep the animation implementation in a single CSS class pair (`carousel-flip-out` / `carousel-flip-in`) so it can be swapped out without touching the carousel logic.

---

### Pitfall 7: LuceneSail Fuzzy Query Applied to Short Tokens Produces Noise

**What goes wrong:**
Adding the `~` fuzzy operator to every search term (e.g., `knowledge~1`) causes LuceneSail to match a significant portion of the Lucene term dictionary for short words. A 3-letter token like `rdf~1` matches any token within 1 edit distance — including `pdf`, `rdg`, `adf`, `sdf`, etc. For a PKM with technical vocabulary (IRIs, prefixes, ontology terms), this produces results that look like random noise, making fuzzy search feel broken.

Lucene's FuzzyQuery maxes out at edit distance 2. Setting `~2` on any term shorter than 5 characters degrades to a near-full-dictionary scan.

**How to avoid:**
Apply the fuzzy operator conditionally based on token length. Only append `~1` for tokens of 5+ characters; leave shorter tokens as exact matches. This mirrors Elasticsearch's default behavior (`fuzziness: AUTO`):

```python
def _build_fuzzy_query(raw_query: str) -> str:
    """Apply fuzzy operator only to tokens >= 5 characters."""
    tokens = raw_query.strip().split()
    parts = []
    for tok in tokens:
        # Strip existing operators before measuring
        clean = tok.rstrip('~*?')
        if len(clean) >= 5 and not any(c in tok for c in ['~', '*', '?', '"']):
            parts.append(tok + '~1')
        else:
            parts.append(tok)
    return ' '.join(parts)
```

Expose the fuzzy toggle as a user-controlled option (e.g., a toggle in the search UI), defaulting to off. Let users opt into fuzzy when they know they are making typos, rather than applying it automatically to all queries.

Also set `fuzzyPrefixLength` in the LuceneSail config to 2 or 3. This requires the first 2-3 characters to match exactly, preventing the extreme noise case where a 5-character token matches unrelated 5-character tokens by pure edit-distance coincidence.

**Warning signs:**
- FTS returns 50+ results for a 4-letter search term with fuzzy enabled
- Results include object titles with no apparent relationship to the query
- Search for a known object title returns the wrong object first

**Phase to address:**
FTS-04 (Fuzzy search). Implement the length-conditional fuzzy logic in `SearchService` before exposing any fuzzy UI. Validate with a test dataset: search for `note~1` should not match `nome`, `node`, `note`, `nope`, `mote` all at the same score.

---

### Pitfall 8: LuceneSail Index Out of Sync After Docker Volume Manipulation

**What goes wrong:**
The Lucene index is stored in a separate Docker volume (`lucene_index`) that is mounted into the RDF4J container. If the `rdf4j_data` volume (the NativeStore) is restored from a backup but the `lucene_index` volume is not restored from the same backup point, the FTS index is out of sync with the triplestore data. Searches return IRIs for objects that have been deleted, or fail to return IRIs for objects that were added after the backup date of the Lucene index.

**How to avoid:**
Document the two-volume backup requirement explicitly. Both `rdf4j_data` and `lucene_index` volumes must be backed up and restored together — they are not independent.

Add an index health check on startup: execute `SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?o } }` and compare the count against a cached count stored in the Lucene index directory's metadata. A significant discrepancy (>10%) should log a warning and optionally trigger a reindex.

If a reindex is needed, it can be triggered programmatically via the RDF4J REST API or by calling `LuceneSail.reindex()`. Document the procedure in `docs/admin/backup-restore.md`.

**Warning signs:**
- FTS returns stale results (deleted objects appear in search)
- FTS misses recently added objects
- After restoring from backup, search returns half the expected results

**Phase to address:**
FTS-04 (Fuzzy search). The backup documentation and health check should be added as part of the fuzzy search phase since that phase requires verifying the LuceneSail configuration in detail.

---

### Pitfall 9: Dockview Drag-and-Drop Conflicts with Existing HTML5 Tab Drag

**What goes wrong:**
SemPKM's current workspace-layout.js implements a full custom HTML5 drag-and-drop system for tab reordering: `dragstart`, `dragend`, `dragover`, `dragleave`, `drop` events on `.workspace-tab` elements. After migrating to dockview-core, the workspace will have TWO drag-and-drop systems active: dockview's internal drag system (for panel group splitting and reordering) and the existing HTML5 tab drag system. These systems conflict on `dragover` and `drop` events, causing: dropped tabs that create new dockview groups unexpectedly, the existing insertion indicator appearing in wrong positions, and `isDragging` state getting stuck when dockview intercepts a drag event the custom system was tracking.

**How to avoid:**
During Phase A migration, completely remove the existing HTML5 tab drag implementation from workspace-layout.js. Do not attempt to run both systems in parallel. Dockview provides its own tab drag-and-drop with group splitting out of the box — there is no benefit to maintaining the custom implementation.

Before removing the custom drag system, audit which behaviors it provides that dockview does not: specifically, the insertion indicator (vertical line showing where the tab will land). Verify dockview's built-in drag indicator meets the SemPKM visual design, or add a CSS override for `--dv-drag-over-background-color` and `--dv-drag-over-border-color` in `dockview-sempkm-bridge.css` to match the existing design.

The `isDragging` global flag in workspace-layout.js (used to guard tab click handlers) must be removed along with the custom drag system — dockview handles the click-vs-drag distinction internally.

**Warning signs:**
- Dragging a tab creates a new group unexpectedly (dockview intercepted the drop)
- Dropping a tab causes it to disappear (both systems handled the drop)
- Console shows `DataTransfer.getData` returning empty string (dockview prevented the default)

**Phase to address:**
DOCK-01 Phase A. Remove the custom drag system in the same commit that adds dockview. Do not leave a transitional state where both systems coexist, even briefly.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep Split.js for bottom panel resize during Phase A | Avoids scope creep; Phase A focuses on editor groups only | Split.js and dockview both run simultaneously in the same page, with different drag systems | Acceptable for Phase A only; Phase B must remove Split.js entirely |
| Serialize tab content (IRIs) in named layouts | Simpler implementation — one blob stores everything | Stale IRIs in restored layouts cause silent panel load failures; breaks after object deletion | Never acceptable for named layouts; use session/layout separation |
| Apply `~1` fuzzy to all query tokens unconditionally | One-line implementation; no per-token logic | Catastrophic noise for short tokens (3-4 chars); makes search feel broken | Never acceptable; minimum 5-character threshold required |
| Optional manifest fields with no schema version | Backward-compatible without migrations | Accumulation of legacy fields; no way to know which manifest version a model uses | Acceptable for v2.3 additions; add a `schemaVersion` field to manifest before v3.0 |
| `always` rendering mode for all dockview panels | Eliminates CodeMirror/Cytoscape visibility refresh bugs | Higher memory use when many panels are open; hidden panels continue running JS | Acceptable for PKM-scale (typically 1-4 panels); reassess if user testing shows >8 panels common |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| dockview-core + htmx | Setting `innerHTML` directly in `init()` without calling `htmx.process()` | Use `htmx.ajax()` for content loading (htmx processes its own swaps), or call `htmx.process(containerElement)` after any direct innerHTML set |
| dockview-core + CodeMirror | Initializing the editor in `init()` without a visibility change handler | Subscribe to `params.api.onDidVisibilityChange`, call `editor.requestMeasure()` / `editor.refresh()` on becoming visible |
| dockview-core + Cytoscape.js | Calling `cy.layout().run()` in `init()` when panel may be hidden | Defer `cy.layout().run()` to `onDidVisibilityChange` with `isVisible: true`; also call `cy.resize()` first |
| LuceneSail + fuzzy operator | Appending `~` to short tokens (< 5 chars) | Implement `_build_fuzzy_query()` with length-conditional fuzzy; set `fuzzyPrefixLength=2` in LuceneSail config |
| dockview `fromJSON` + Mental Model uninstall | Calling `api.clear()` in the catch block after `fromJSON()` fails | Rely on dockview's graceful reset; remove invalid layout from storage and call `buildDefaultLayout()` |
| Carousel + htmx swap | Triggering the CSS animation class and the htmx content swap independently | Start the CSS transition, then swap content on `transitionend`; or swap first and fade in — never both simultaneously |
| Named layouts + session content | Saving open IRIs into the named layout blob | Keep panel structure (layout) separate from tab content (session); only serialize structure in named layout |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| LuceneSail `~2` fuzzy on 3-char tokens | Search returns hundreds of results; UI unresponsive for 2-3s | Apply fuzzy only to tokens >= 5 chars; cap at `~1` | Immediately — even with < 100 objects |
| dockview `onlyWhenVisible` + ResizeObserver | ResizeObserver fires with 0px; panels never get correct size | Use `always` rendering mode for panels with complex visualizations, or refresh on `onDidVisibilityChange` | Any panel that has a chart, graph, or editor |
| Large serialized layout blob in sessionStorage | sessionStorage write slow; exceeding 5MB quota | Serialize only panel structure, not content; compress with JSON | At approximately 50+ named layouts with IRI content |
| Wildcard `*` queries in LuceneSail | Full index scan; no score ordering | Educate users; restrict wildcard to suffix position only (`term*`); never leading wildcard (`*term`) | Immediately on any dataset |

---

## "Looks Done But Isn't" Checklist

- [ ] **Dockview Phase A migration**: htmx-powered elements in panels work after the panel is dragged to a new group — verify by checking DevTools network tab shows requests after drag.
- [ ] **CodeMirror in dockview panel**: Editor renders correctly after being hidden and re-shown (switch to another tab and back). Gutter line numbers align with content.
- [ ] **Cytoscape in dockview panel**: Graph renders at correct size after being hidden and re-shown. Nodes are not invisible or overlapping in the top-left corner.
- [ ] **Named layout save/restore**: A saved layout restores the panel structure but does NOT restore the open object content (content comes from session state, not layout state).
- [ ] **Named layout + model uninstall**: After uninstalling a Mental Model, a previously saved layout that referenced model-specific panels falls back to the default layout gracefully, without a blank workspace or console errors.
- [ ] **Carousel manifest schema backward compatibility**: The existing `basic-pkm/manifest.yaml` (with no carousel fields) still passes `ManifestSchema.model_validate()` without errors after adding carousel schema fields.
- [ ] **Fuzzy FTS with short tokens**: A search for `rdf~1` does not return hundreds of noise results. A search for `project~1` returns objects containing "project" first, then near-matches.
- [ ] **Carousel animation respects prefers-reduced-motion**: With `@media (prefers-reduced-motion: reduce)` active, the carousel view rotation happens instantly with no animation.
- [ ] **Bottom panel preserved during dockview Phase A**: The existing bottom panel (SPARQL/Event Log/Copilot) is not disrupted by the editor-groups-area dockview migration. The vertical resize handle between editor area and bottom panel still works.
- [ ] **Dockview drag-and-drop replaces custom system**: After Phase A, no `dragstart`/`dragend`/`dragover` event listeners from the old workspace-layout.js are still active. Verify with browser DevTools event listener inspector.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| htmx silenced in dockview panels | LOW (once diagnosed) | Add `htmx.process(containerElement)` calls; hard to diagnose without knowing to look for it |
| CodeMirror/Cytoscape zero-size in panels | LOW | Add `onDidVisibilityChange` handler; or switch to `always` rendering mode globally |
| fromJSON broken state on startup | LOW (via fallback) | Remove corrupted layout key from sessionStorage; implement `try/catch` with `buildDefaultLayout()` fallback |
| Manifest schema break on new required field | HIGH | Roll back the Pydantic change; convert field to optional; write a migration script if on-disk manifests need updating |
| Fuzzy FTS noise | LOW | Disable fuzzy via feature flag; fix `_build_fuzzy_query()` to apply length threshold |
| Named layout stale IRI references | MEDIUM | Remove IRI storage from layout serialization format; existing saved layouts may need migration script to strip content |
| Drag-and-drop conflict during migration | MEDIUM | Rollback to pre-Phase A if both systems coexist; commit removal of old drag system in same PR as dockview addition |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| htmx silenced after panel init/reparent | DOCK-01 Phase A | Playwright test: drag panel to new group, click htmx button, verify network request fires |
| CodeMirror/Cytoscape zero-size | DOCK-01 Phase A | Manual test: switch away from editor tab and back; screenshot comparison |
| fromJSON broken state on model uninstall | DOCK-02 Named layouts | Playwright test: save named layout, uninstall referenced model, reload, verify default layout loads |
| Manifest schema break on carousel fields | VIEW-02 Carousel views | Unit test: validate existing basic-pkm manifest.yaml passes after schema change |
| Named layout stale IRI serialization | DOCK-02 Named layouts | Test: save layout with object A open, delete object A, restore layout, verify panel shows "not found" not error |
| Carousel animation over-engineering | VIEW-02 Carousel views | Test with `prefers-reduced-motion: reduce`; test at narrow panel width (< 300px) |
| Fuzzy FTS noise on short tokens | FTS-04 Fuzzy search | Unit test: `_build_fuzzy_query('rdf notes')` does not append `~` to `rdf` |
| Lucene index out of sync after backup restore | FTS-04 Fuzzy search | Document backup procedure; add startup health check log message |
| Drag system conflict during migration | DOCK-01 Phase A | Code review gate: no `dragstart` listeners in workspace-layout.js after merge |

---

## Sources

- [dockview-core Rendering Panels documentation](https://dockview.dev/docs/core/panels/rendering/) — `onlyWhenVisible` vs `always` rendering modes, DOM removal behavior; HIGH confidence
- [dockview GitHub Issue #341 — fromJSON broken state](https://github.com/mathuo/dockview/issues/341) — confirmed broken state when `api.clear()` called after failed `fromJSON()`; HIGH confidence
- [dockview GitHub Issue #718 — keep alive panels](https://github.com/mathuo/dockview/issues/718) — use case for `always` mode with iFrames and stateful panels; HIGH confidence
- [dockview GitHub Issue #996 — components disappear after addFloatingGroup/moveTo](https://github.com/mathuo/dockview/issues/996) — panel content loss on DOM reparenting; HIGH confidence
- [dockview Loading State documentation](https://dockview.dev/docs/core/state/load/) — official `fromJSON()` error recovery pattern; HIGH confidence
- [dockview Saving State documentation](https://dockview.dev/docs/core/state/save/) — `toJSON()` / `onDidLayoutChange` patterns; HIGH confidence
- [htmx `htmx.process()` documentation](https://htmx.org/api/) — official API for re-initializing htmx on external DOM mutations; HIGH confidence
- [htmx external DOM mutation article](https://www.bennadel.com/blog/4799-what-happens-when-you-mutate-the-dom-outside-of-htmx.htm) — htmx does not observe external mutations; HIGH confidence
- [RDF4J LuceneSail 5.1.3 JavaDoc](https://rdf4j.org/javadoc/latest/org/eclipse/rdf4j/sail/lucene/LuceneSail.html) — `fuzzyPrefixLength`, `defaultNumDocs`, `LUCENE_DIR_KEY` parameters; HIGH confidence
- [RDF4J LuceneSail documentation](https://rdf4j.org/documentation/programming/lucene/) — fuzzy syntax, wildcard support, reindex procedure; HIGH confidence
- [Lucene fuzzy search percentage thread (rdf4j-users)](https://groups.google.com/g/rdf4j-users/c/k04xjxM_wBI) — edit distance integer 0-2, not fractional similarity; HIGH confidence (confirmed by multiple replies)
- [Apache Lucene FuzzyQuery](https://lucene.apache.org/core/7_3_1/core/org/apache/lucene/search/FuzzyQuery.html) — max edit distance 2, prefixLength semantics; HIGH confidence
- [RDF4J 4.0 release notes](https://rdf4j.org/release-notes/4.0.0/) — Lucene library upgrade 7.7 → 8.5, reindex requirement on version upgrade; HIGH confidence
- SemPKM codebase analysis: `workspace-layout.js` (1074 lines), `dockview-sempkm-bridge.css`, `manifest.py`, `search.py` — direct inspection; HIGH confidence
- SemPKM `DECISIONS.md` DEC-04 section — dockview Phase A scope, htmx integration prerequisites, `containerElement` pattern; HIGH confidence

---
*Pitfalls research for: v2.3 Shell, Navigation & Views (SemPKM)*
*Researched: 2026-03-01*
