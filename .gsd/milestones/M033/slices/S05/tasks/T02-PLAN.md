---
estimated_steps: 4
estimated_files: 4
skills_used: []
---

# T02: Frontend integration — JS, CSS, explorer entry

**Slice:** S05 — App Catalog Pages
**Milestone:** M033

## Description

Wire the catalog into the workspace UI. Add the tab-opening JS function, the special-panel routing for htmx loading, the "App Catalog" entry in the APPS explorer sidebar section, and CSS styling for the catalog cards and detail page.

## Steps

1. **Add `openCatalogTab()` to `frontend/static/js/workspace.js`**:
   - Follow the exact pattern of `openDocsTab()` (lines 712-730):
     ```javascript
     function openCatalogTab() {
       var tabKey = 'special:catalog';
       var dv = window._dockview;
       if (!dv) return;
       var existing = dv.panels.find(function(p) { return p.id === tabKey; });
       if (existing) { existing.api.setActive(); return; }
       if (!window._tabMeta) window._tabMeta = {};
       window._tabMeta[tabKey] = { label: 'App Catalog', dirty: false };
       dv.api.addPanel({
         id: tabKey,
         component: 'special-panel',
         params: { specialType: 'catalog', isView: false, isSpecial: true },
         title: 'App Catalog'
       });
     }
     window.openCatalogTab = openCatalogTab;
     ```
   - Place it after `openDocsTab()` / `openCanvasTab()` block (around line 755)

2. **Verify `workspace-layout.js` routing** — The default special-panel init logic already computes `url = '/browser/' + st`, so `specialType: 'catalog'` → `/browser/catalog` automatically. No code change needed UNLESS the catalog detail needs in-tab navigation. Since the catalog templates use `hx-target="closest .group-editor-area"` for navigation (same as docs), the default routing is sufficient. Add a comment if helpful but no functional change required.

3. **Add "App Catalog" entry in `backend/app/templates/browser/workspace.html`**:
   - In the APPS explorer section (around line 132), add a static tree-leaf entry BEFORE the `hx-get="/browser/apps/explorer"` div:
     ```html
     <div class="tree-leaf catalog-entry"
          onclick="openCatalogTab()">
       <i data-lucide="layout-grid" class="tree-icon"></i>
       <span class="tree-label">App Catalog</span>
     </div>
     ```
   - This goes inside the `explorer-section-body` div (`id="apps-tree"`), but as a static element before the htmx-loaded content. Alternatively, add it between the section header and the section body as a persistent element. Check the existing structure and pick whichever keeps the catalog entry always visible regardless of htmx load state.

4. **Add `.catalog-*` CSS rules to `frontend/static/css/workspace.css`**:
   - Reuse `.docs-page` / `.docs-cards` / `.docs-card` patterns but with catalog-specific classes:
     - `.catalog-page` — page container with padding and overflow-y auto
     - `.catalog-page-header` — title and subtitle
     - `.catalog-cards` — CSS grid, 3-column on wide, 2-column on medium, 1-column on narrow
     - `.catalog-card` — card with border, border-radius, hover effect, cursor pointer, padding
     - `.catalog-card-icon` — Lucide icon with `flex-shrink: 0`, `stroke: currentColor`
     - `.catalog-card-body` — name + description text
     - `.catalog-card-status` — status badge (small pill): green for "running", blue for "installed", gray for "available"
   - Detail page styles:
     - `.catalog-detail` — detail container with padding
     - `.catalog-detail-header` — back button + app name + version
     - `.catalog-detail-section` — section blocks (permissions, dependencies, tasks, settings)
     - `.catalog-detail-meta` — metadata items (author, license)
     - `.catalog-btn-install`, `.catalog-btn-uninstall` — action buttons
   - Follow CLAUDE.md rules: Lucide SVGs sized via CSS not inline, `flex-shrink: 0`, `stroke: currentColor`

## Must-Haves

- [ ] `openCatalogTab()` exposed on `window` in workspace.js
- [ ] "App Catalog" entry visible in APPS explorer section
- [ ] Clicking entry opens a dockview tab that loads catalog page
- [ ] CSS card grid responsive (3 → 2 → 1 columns)
- [ ] Status badges visually distinguish running/installed/available
- [ ] Lucide icons follow CLAUDE.md conventions

## Verification

- `rg -c "openCatalogTab" frontend/static/js/workspace.js` returns >= 2
- `rg "App Catalog" backend/app/templates/browser/workspace.html` returns at least 1 match
- `rg -c "\.catalog-card" frontend/static/css/workspace.css` returns >= 1

## Inputs

- `frontend/static/js/workspace.js` — existing special-panel tab functions to follow pattern
- `frontend/static/js/workspace-layout.js` — special-panel routing (verify default URL works)
- `backend/app/templates/browser/workspace.html` — APPS explorer section to add catalog entry
- `frontend/static/css/workspace.css` — existing `.docs-*` CSS patterns to mirror
- `backend/app/templates/browser/catalog_page.html` — T01 output, catalog grid template (to match CSS class names)
- `backend/app/templates/browser/catalog_detail.html` — T01 output, detail template (to match CSS class names)

## Expected Output

- `frontend/static/js/workspace.js` — modified with `openCatalogTab()` function
- `backend/app/templates/browser/workspace.html` — modified with "App Catalog" tree-leaf entry
- `frontend/static/css/workspace.css` — modified with `.catalog-*` CSS rules

## Observability Impact

- **`openCatalogTab()` tab creation** — uses the standard dockview `special-panel` component with `specialType: 'catalog'`, so the same panel lifecycle logging (if any) applies. No new JS-level logging added; tab creation failures would manifest as a missing panel in dockview.
- **Explorer sidebar entry** — static HTML, always visible in the APPS section. If the entry doesn't appear, check that `workspace.html` was served (not cached) and that the APPS section is expanded.
- **CSS class matching** — catalog templates from T01 use `.catalog-card`, `.catalog-status-badge`, `.catalog-detail`, etc. If cards render unstyled, verify that `workspace.css` is loaded (check network tab for 200 on the CSS file).
