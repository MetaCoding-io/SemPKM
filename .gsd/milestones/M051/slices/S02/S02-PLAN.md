# S02: Explorer & Nav Cleanup + Object Tab Refresh

**Goal:** Fix four workspace paper-cuts: explorer type labels show clean names without "Shape" suffix, event log placeholder shows useful text, VFS mount dropdown shows human-readable model names, and object tabs have a refresh button.
**Demo:** After this: Explorer shows 'Project' not 'Project Shape'. Event Log tab shows actual event content. VFS mount dropdown has clean labels. Object tab has a refresh button that reloads content.

## Tasks
- [x] **T01: Added .removesuffix(' Shape') to backend type labels, replaced stale event log placeholder, and enriched VFS mount SPARQL with dcterms:title for human-readable model names** — Three small backend/template fixes:

1. **Strip ' Shape' suffix from type labels** (D391): In `backend/app/services/shapes.py` `get_types()` method (line 556), add `.removesuffix(' Shape')` to the label when building the types list. Do NOT modify `_resolve_label()` — PropertyGroup labels like 'Relationships' don't have ' Shape'. The existing client-side strip in `workspace.js` line 2094-2095 (`typeLabel.replace(/\s+Shape$/, '')`) becomes redundant but leave it as a harmless no-op.

2. **Fix event log placeholder text**: In `backend/app/templates/browser/workspace.html` line 183, change `Event Log Explorer — coming in Phase 16` to `Loading event log...`. The lazy-load handler in workspace.js already replaces this content via htmx GET to `/browser/events` on first panel open.

3. **Add `dcterms:title` to VFS mount SPARQL**: In `backend/app/vfs/mount_router.py` `list_mounts()` function (around line 269), modify the model mounts SPARQL query to also fetch `dcterms:title`:
```sparql
SELECT DISTINCT ?modelId ?title FROM <urn:sempkm:models>
WHERE {
  ?model a <urn:sempkm:MentalModel> ;
         <urn:sempkm:modelId> ?modelId .
  OPTIONAL { ?model <http://purl.org/dc/terms/title> ?title }
}
ORDER BY ?modelId
```
Then in the dict construction (around line 282), use `title` with `model_id` as fallback:
```python
title = b.get('title', {}).get('value', '')
mounts.append({
    ...
    'name': title if title else model_id,
    ...
})
```
  - Estimate: 20m
  - Files: backend/app/services/shapes.py, backend/app/templates/browser/workspace.html, backend/app/vfs/mount_router.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5
- [x] **T02: Added refresh button with refresh-cw icon to both object tab templates, backed by refreshObjectTab() JS function** — Add a refresh button to both object tab templates and the supporting JS function.

1. **Add `refreshObjectTab` function to workspace.js**: Near the other tab utility functions (around line 224 where `loadObjectContent` lives), add:
```javascript
function refreshObjectTab(objectIri) {
    loadObjectContent(objectIri);
}
```
Export it: `window.SemPKM.refreshObjectTab = refreshObjectTab;` (add near the other SemPKM exports around line 3818+).

2. **Add refresh button to `object_tab.html`**: In `backend/app/templates/browser/object_tab.html`, add a refresh button inside `.object-toolbar-actions` right after the star button (after the `</button>` closing tag of star-btn, before the delete-btn). Use the same structural pattern as star-btn:
```html
<button class="refresh-btn"
        onclick="SemPKM.refreshObjectTab('{{ object_iri }}')"
        title="Refresh">
  <i data-lucide="refresh-cw"></i>
</button>
```

3. **Add refresh button to `object_tab_app.html`**: Same button in the same position (after star-btn, before mode-toggle) in `backend/app/templates/browser/object_tab_app.html`.

4. **Add CSS for `.refresh-btn`**: In `frontend/static/css/workspace.css`, add a `.refresh-btn` rule block right after the `.delete-btn svg` block (around line 2394). Follow the same pattern as `.star-btn` and `.delete-btn`:
```css
.refresh-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    border-radius: 4px;
    transition: color 0.2s;
}
.refresh-btn:hover {
    color: var(--color-primary);
}
.refresh-btn svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    stroke: currentColor;
}
```
Note: Per CLAUDE.md rules — Lucide icons must be sized via CSS with `flex-shrink: 0` and `stroke: currentColor`. No inline styles on the `<i>` tag.
  - Estimate: 15m
  - Files: frontend/static/js/workspace.js, backend/app/templates/browser/object_tab.html, backend/app/templates/browser/object_tab_app.html, frontend/static/css/workspace.css
  - Verify: rg 'refreshObjectTab' frontend/static/js/workspace.js && rg 'refresh-btn' backend/app/templates/browser/object_tab.html backend/app/templates/browser/object_tab_app.html && rg 'refresh-btn' frontend/static/css/workspace.css
