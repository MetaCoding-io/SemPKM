# Phase 41: Gap Closure -- Rules Wiring, Flip Fix, VFS Browser - Research

**Researched:** 2026-03-05
**Domain:** Backend gap closure (inference pipeline), CSS 3D flip bug fix, htmx VFS browser view
**Confidence:** HIGH

## Summary

Phase 41 addresses three distinct workstreams: (1) wiring the rules graph into model install and adding validation enqueue after promote_triple, (2) permanently fixing the CSS 3D flip card bleed-through bug that has recurred three times, and (3) adding an in-app VFS browser view as a dockview tab accessible from the sidebar.

All three are well-understood from code inspection. The rules graph gap is a ~5-line addition to `models.py` install_model. The promote_triple gap is a single `validation_queue.enqueue()` call. The flip card fix requires switching from `backface-visibility: hidden` alone to `display: none` on the hidden face after animation completes. The VFS browser reuses the existing special-panel dockview pattern and VFS collection SPARQL queries.

**Primary recommendation:** Three independent plans -- (1) backend gap closure (rules graph + promote enqueue), (2) flip card permanent fix + CLAUDE.md docs, (3) VFS browser view with sidebar entry.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INF-02 | SHACL-AF rules: rules graph written to triplestore during model install | Rules graph is loaded by `load_archive()` into `archive.rules` but `install_model()` skips writing it to `urn:sempkm:model:{id}:rules`. Fix: add write block after views block at line ~238 |
| VFS-01 | In-app VFS browser view as dockview tab accessible from sidebar | Existing special-panel pattern (settings/docs/canvas) + VFS collection SPARQL queries provide complete implementation path |
| BUG-10 | Flip card bleed-through permanent fix | CSS `backface-visibility: hidden` is unreliable across browsers; add `display: none` as bulletproof fallback after animation completes |
</phase_requirements>

## Standard Stack

### Core (existing -- no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| htmx | existing | VFS browser tree interaction (lazy-load children) | Project standard for all DOM updates |
| Lucide | existing | VFS browser icons (folder-tree, file, folder) | Project icon library |
| dockview | existing | VFS browser as special-panel tab | Project tab/panel system |

### Supporting

No new libraries needed. All three workstreams use existing infrastructure.

## Architecture Patterns

### Pattern 1: Rules Graph Write in Model Install

**What:** Add `archive.rules` write to `install_model()` in `backend/app/services/models.py`
**Where:** After the views graph write block (line ~238), before model metadata registration
**Example:**
```python
# After views block (~line 238), before register_sparql:
if archive.rules is not None and len(archive.rules) > 0:
    sparql = _build_insert_data_sparql(graphs.rules, archive.rules)
    await self._client.transaction_update(txn_url, sparql)
```

**Why this works:** `ModelGraphs.rules` already returns `urn:sempkm:model:{id}:rules`. `_load_rules_graphs()` in InferenceService already queries this graph. The archive loader already loads rules into `archive.rules`. The only missing piece is the write during install.

### Pattern 2: Validation Enqueue After Promote

**What:** Call `validation_queue.enqueue()` after `EventStore.commit()` in `promote_triple()`
**Where:** `backend/app/inference/service.py`, line ~379 (after `await self._event_store.commit([operation])`)
**Challenge:** `InferenceService` does not currently hold a reference to `AsyncValidationQueue`. Need to inject it via constructor or pass it from the router.

**Option A (preferred):** Add `validation_queue` parameter to `promote_triple()` method -- keeps InferenceService focused, router passes queue from dependency injection.

**Option B:** Add `validation_queue` to InferenceService constructor -- couples inference to validation more tightly.

The router at `backend/app/inference/router.py` already has access to both services via FastAPI dependency injection. Option A is cleaner.

### Pattern 3: Special Panel Tab (VFS Browser)

**What:** Add VFS browser as a `special:vfs` panel following the settings/docs/canvas pattern
**Files involved:**
1. `frontend/static/js/workspace.js` -- add `openVfsTab()` function (copy openSettingsTab pattern)
2. `frontend/static/js/workspace-layout.js` -- no changes needed (generic `special-panel` handler resolves `/browser/{specialType}`)
3. `backend/app/browser/router.py` -- add `@router.get("/vfs")` endpoint returning VFS tree template
4. `backend/app/templates/browser/vfs_browser.html` -- new template with tree UI
5. `backend/app/templates/components/_sidebar.html` -- add VFS Browser nav link in Apps section

**Tab registration pattern:**
```javascript
function openVfsTab() {
    var tabKey = 'special:vfs';
    var dv = window._dockview;
    if (!dv) return;
    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) { existing.api.setActive(); return; }
    if (!window._tabMeta) window._tabMeta = {};
    window._tabMeta[tabKey] = { label: 'VFS Browser', dirty: false };
    dv.api.addPanel({
        id: tabKey,
        component: 'special-panel',
        params: { specialType: 'vfs', isView: false, isSpecial: true },
        title: 'VFS Browser'
    });
}
window.openVfsTab = openVfsTab;
```

**Backend route resolves via existing mechanism:**
`workspace-layout.js` line 112: `htmx.ajax('GET', '/browser/' + st, { target: el, swap: 'innerHTML' })`
So `special:vfs` -> `GET /browser/vfs`.

### Pattern 4: Permanent Flip Card Fix

**What:** Replace unreliable `backface-visibility: hidden` with `display: none` on the hidden face after animation completes
**Where:** `frontend/static/css/workspace.css` (lines 1462-1510) + `frontend/static/js/workspace.js` (lines 542-615)
**Root cause:** `backface-visibility: hidden` is browser-dependent and breaks with certain compositing conditions, GPU acceleration quirks, and stacking context interactions.

**The bulletproof approach:**
1. Keep `backface-visibility: hidden` as the primary mechanism (it works during animation)
2. After animation completes (600ms), set `display: none` on the hidden face
3. Before starting animation, set `display: block` on the target face first
4. This provides a two-layer defense: CSS 3D during animation + `display: none` after

**CSS changes:**
```css
.object-face-read.face-hidden {
    visibility: hidden;
    z-index: 0;
    display: none;  /* bulletproof: completely remove from rendering */
}

.object-face-edit.face-visible {
    visibility: visible;
    display: block;  /* ensure visible before animation */
}
```

**JS changes (workspace.js toggleObjectMode):**
```javascript
// Switching read -> edit:
// 1. Make edit face display:block BEFORE adding .flipped
if (editFace) editFace.style.display = 'block';
flipInner.classList.add('flipped');
// 2. After animation (600ms), hide read face completely
setTimeout(function () {
    if (readFace) readFace.classList.add('face-hidden');
    if (editFace) editFace.classList.add('face-visible');
}, 600);  // full 600ms, not 300ms midpoint

// Switching edit -> read:
// 1. Make read face display:block BEFORE removing .flipped
if (readFace) { readFace.style.display = ''; readFace.classList.remove('face-hidden'); }
flipInner.classList.remove('flipped');
// 2. After animation (600ms), hide edit face completely
setTimeout(function () {
    if (editFace) editFace.classList.remove('face-visible');
}, 600);  // full 600ms
```

### Anti-Patterns to Avoid

- **Relying solely on `backface-visibility: hidden`:** This is the root cause of the recurring bug. It is a CSS hint, not a guarantee. Different browser versions, GPU drivers, and compositing layers can ignore it.
- **Using 300ms midpoint timeout for face swaps:** The current 300ms timeout races with the 600ms animation. Wait for the full animation duration or use `transitionend` event.
- **Not documenting CSS 3D flip pitfalls in CLAUDE.md:** This bug has recurred 3 times. Documentation prevents a 4th occurrence.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VFS tree data | Custom SPARQL queries | Reuse VFS collection queries from `backend/app/vfs/collections.py` | Same SPARQL patterns (models -> types -> objects) already tested |
| Tab management | Custom tab registration | Existing `special-panel` dockview pattern | Proven pattern used by settings, docs, canvas tabs |

## Common Pitfalls

### Pitfall 1: Rules Graph Not Cleared on Uninstall
**What goes wrong:** If rules graph is written during install but not cleared during uninstall, stale rules persist after model removal.
**How to avoid:** `ModelGraphs.all_graphs` already includes `rules` (line 57 of registry.py). The uninstall logic likely iterates `all_graphs` to clear them. Verify this is the case during implementation.

### Pitfall 2: Flip Animation Timing Race
**What goes wrong:** Setting `display: none` too early (before animation completes) causes the face to disappear mid-flip.
**How to avoid:** Use 600ms timeout (matching the CSS transition duration) or `transitionend` event. Never hide a face before the 3D rotation is complete.

### Pitfall 3: VFS Browser Assumes Models Installed
**What goes wrong:** VFS browser crashes or shows error if no models are installed.
**How to avoid:** Handle empty state gracefully -- show "No mental models installed" message when SPARQL returns zero bindings.

### Pitfall 4: promote_triple Missing Validation Queue Reference
**What goes wrong:** `InferenceService.promote_triple()` needs access to `AsyncValidationQueue` which it doesn't currently have.
**How to avoid:** Pass the queue as a parameter from the router handler, not as a constructor dependency. The router already has both services via DI.

### Pitfall 5: VFS Browser Nav Link With htmx Full-Page Swap
**What goes wrong:** Sidebar nav links use `hx-target="#app-content"` which replaces the entire content area, but VFS browser should open as a dockview tab, not replace the workspace.
**How to avoid:** Use `onclick="openVfsTab(); return false;"` pattern (like the Settings link in the user popover) instead of htmx navigation. The sidebar link should call the JS function, not do an htmx swap.

## Code Examples

### Rules Graph Write Block (insert after views block in models.py)
```python
if archive.rules is not None and len(archive.rules) > 0:
    sparql = _build_insert_data_sparql(graphs.rules, archive.rules)
    await self._client.transaction_update(txn_url, sparql)
```

### Promote Triple Validation Enqueue (inference router)
```python
# In the promote endpoint handler:
result = await inference_service.promote_triple(triple_hash)
if result:
    # Enqueue validation after promotion commits to EventStore
    await validation_queue.enqueue(
        event_iri=f"urn:sempkm:inference:promote:{triple_hash}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        trigger_source="inference_promote"
    )
```

### VFS Browser Backend Route
```python
@router.get("/vfs")
async def vfs_browser(
    request: Request,
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """VFS browser tree view as a dockview tab."""
    # Query installed models (same pattern as VFS RootCollection)
    result = await client.query("""
        SELECT DISTINCT ?modelId FROM <urn:sempkm:models>
        WHERE {
            ?model a <urn:sempkm:MentalModel> ;
                   <urn:sempkm:modelId> ?modelId .
        }
    """)
    models = [b["modelId"]["value"] for b in result["results"]["bindings"]]
    return templates.TemplateResponse(
        "browser/vfs_browser.html",
        {"request": request, "models": models}
    )
```

### VFS Browser Sidebar Entry
```html
<!-- In Apps section of _sidebar.html, after Object Browser -->
<a href="#" class="nav-link" data-tooltip="VFS Browser"
   onclick="if(typeof openVfsTab==='function'){openVfsTab();}return false;">
    <i data-lucide="hard-drive" class="nav-icon"></i>
    <span class="nav-label">VFS Browser</span>
</a>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `backface-visibility: hidden` alone | `display: none` after animation + `backface-visibility` during | Phase 41 | Eliminates recurring bleed-through bug |
| External WebDAV clients only | In-app VFS browser + external WebDAV | Phase 41 | VFS accessible without third-party tools |

## Open Questions

1. **VFS tree expand/collapse: htmx or inline JS?**
   - What we know: The nav tree (`nav_tree.html`) uses htmx `hx-trigger="click once"` for lazy-loading children
   - What's unclear: Should VFS tree follow same pattern or load all data upfront (simpler for small datasets)?
   - Recommendation: Use htmx lazy-load for consistency and to handle large object sets. Each model folder expands via `GET /browser/vfs/{model_id}/types`, each type folder via `GET /browser/vfs/{model_id}/{type_label}/objects`

2. **Should VFS browser items be clickable to open object tabs?**
   - What we know: VFS resources map to object IRIs via the file map
   - Recommendation: Yes -- clicking an object file in the VFS tree should call `openTab(iri, label)` to open it in the workspace. This provides discoverability value.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (via `npx playwright test`) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `npx playwright test --project=chromium -g "pattern"` |
| Full suite command | `npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INF-02 | Rules graph written during model install; inference produces rule-derived triples | integration | Existing inference tests in `e2e/tests/09-inference/` cover rule execution | Partial -- rules wiring is backend-only, verified via inference output |
| VFS-01 | VFS browser opens as tab, shows model/type/object tree | e2e | `npx playwright test --project=chromium e2e/tests/XX-vfs-browser/` | No -- Wave 0 |
| BUG-10 | No bleed-through after flip to edit mode | e2e | `npx playwright test --project=chromium e2e/tests/12-bug-fixes/` | Partial -- existing flip tests may not check for bleed-through |

### Sampling Rate
- **Per task commit:** `npx playwright test --project=chromium -g "relevant pattern" --reporter=dot`
- **Per wave merge:** `npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- Note: E2E tests cannot be added/modified per project constraints ("test files cannot be modified"). The existing E2E suite in phase 40 should already cover inference behavior. VFS browser testing relies on manual verification or future E2E additions.
- Backend validation: inference run after model reinstall should now produce rule-derived triples (verifiable via SPARQL console or inference panel)

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `backend/app/services/models.py` lines 220-260 -- confirmed rules graph write is missing
- Direct code inspection of `backend/app/inference/service.py` lines 342-398 -- confirmed promote_triple lacks validation enqueue
- Direct code inspection of `backend/app/models/registry.py` lines 24-57 -- confirmed ModelGraphs.rules exists and is in all_graphs
- Direct code inspection of `backend/app/models/loader.py` lines 166-178 -- confirmed archive.rules is loaded
- Direct code inspection of `frontend/static/css/workspace.css` lines 1462-1510 -- confirmed current flip CSS
- Direct code inspection of `frontend/static/js/workspace.js` lines 542-615 -- confirmed current flip JS
- Direct code inspection of `frontend/static/js/workspace-layout.js` lines 107-114 -- confirmed special-panel resolution
- Direct code inspection of `backend/app/vfs/collections.py` -- confirmed VFS SPARQL patterns
- Direct code inspection of `backend/app/templates/components/_sidebar.html` -- confirmed sidebar structure

## Metadata

**Confidence breakdown:**
- Rules graph gap closure: HIGH -- exact code location identified, ~5 lines to add
- Promote triple validation enqueue: HIGH -- exact location identified, clear injection path
- Flip card fix: HIGH -- root cause understood (3rd recurrence), `display: none` is bulletproof
- VFS browser: HIGH -- follows established special-panel pattern used by 3 existing tabs
- Architecture patterns: HIGH -- all patterns reuse existing project conventions

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable codebase, no external dependency changes)