---
estimated_steps: 42
estimated_files: 4
skills_used: []
---

# T02: Add refresh button to object tab toolbar

Add a refresh button to both object tab templates and the supporting JS function.

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

## Inputs

- ``frontend/static/js/workspace.js` — loadObjectContent function at line 224, SemPKM exports at line 3818+`
- ``backend/app/templates/browser/object_tab.html` — toolbar-actions div at line 14`
- ``backend/app/templates/browser/object_tab_app.html` — toolbar-actions div at line 18`
- ``frontend/static/css/workspace.css` — .star-btn and .delete-btn CSS blocks at lines 2342-2394`

## Expected Output

- ``frontend/static/js/workspace.js` — refreshObjectTab function added and exported to window.SemPKM`
- ``backend/app/templates/browser/object_tab.html` — refresh button in toolbar after star button`
- ``backend/app/templates/browser/object_tab_app.html` — refresh button in toolbar after star button`
- ``frontend/static/css/workspace.css` — .refresh-btn CSS rules following star-btn/delete-btn pattern`

## Verification

rg 'refreshObjectTab' frontend/static/js/workspace.js && rg 'refresh-btn' backend/app/templates/browser/object_tab.html backend/app/templates/browser/object_tab_app.html && rg 'refresh-btn' frontend/static/css/workspace.css
