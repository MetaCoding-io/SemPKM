# Phase 33: Named Layouts and VFS Settings Restore - Research

**Researched:** 2026-03-03
**Domain:** dockview-core layout serialization, ninja-keys command palette nested commands, localStorage persistence, VFS Settings UI restoration
**Confidence:** HIGH (based on direct codebase analysis of all critical files + Phase 30 research already confirmed dockview toJSON/fromJSON patterns)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Save full workspace snapshot: dockview panel geometry + open tabs/content per panel
- Auto-persist last layout on close/reload (unnamed, automatic) -- this is the "current state" that survives refresh
- Named saves are separate explicit snapshots on top of auto-save
- Naming via text input inline in Command Palette (no modal)
- Restore replaces current layout entirely, no confirmation dialog
- Best-effort restore for stale data: restore geometry always, open tabs that still exist, show brief toast listing any skipped objects
- Flat "Layout: ..." commands as top-level palette items: "Layout: Save As...", "Layout: Restore...", "Layout: Delete..."
- Selecting Restore or Delete replaces palette contents with list of saved layout names
- User picks from the list and action happens immediately
- Access points: Command Palette (primary), lower-left user menu (secondary) -- layout management submenu for discoverability
- localStorage only (consistent with existing `sempkm_` key patterns like carousel view persistence)
- Key namespace: `sempkm_layouts` for named saves, `sempkm_layout_current` for auto-save
- No hard limit on saved layouts (localStorage budget is ample for JSON layout data)
- VFS Settings UI: token generation, masked token display, revocation -- matching success criteria
- Token shown in full only on creation (copy-to-clipboard), masked after (e.g., `sk-...abc3`)
- Placement and section naming within Settings page -- Claude picks based on existing layout

### Claude's Discretion
- Delete confirmation UX (inline confirm vs no confirm)
- Whether to show active layout name indicator anywhere
- Overwrite behavior when saving with an existing name (prompt vs silent replace)
- Exact toast duration and styling for stale-data warnings
- Connection status display -- Claude decides based on what's feasible with current backend

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOCK-02 | User can save named workspace layouts and restore them via the Command Palette; layouts persist across sessions | dockview `toJSON()`/`fromJSON()` already live in workspace-layout.js; ninja-keys `parent` property supports nested sub-menus; localStorage `sempkm_layouts` key for persistence; auto-save via `onDidLayoutChange` handler |
| BUG-02 | User can access and use VFS mount configuration from the Settings page | All backend routes (`/api/auth/tokens` POST/GET/DELETE), templates (`_vfs_settings.html`), and CSS (`settings.css`) already exist and are verified correct; issue is Lucide icon inline style violations per CLAUDE.md and potential `lucide.createIcons()` not being called after dockview panel mount |
</phase_requirements>

---

## Summary

Phase 33 has two independent workstreams: (1) Named layout save/restore via the Command Palette and user menu, and (2) VFS Settings UI restoration.

**Named Layouts** builds on the existing dockview infrastructure from Phase 30. The `toJSON()`/`fromJSON()` round-trip is already live in `workspace-layout.js` (lines 145, 187) using `sessionStorage`. The key change is migrating auto-save from `sessionStorage` to `localStorage` (key: `sempkm_layout_current`) so layouts survive browser close, and adding a separate `sempkm_layouts` key that stores a JSON object of `{ name: SerializedDockview }` entries for named saves. The ninja-keys command palette already supports dynamic data manipulation (FTS search items are added/removed at runtime), and the `parent` property on action items enables nested sub-menus for "Layout: Restore..." and "Layout: Delete..." where the palette shows a filtered list of saved layout names. The secondary access point (user popover menu in the sidebar) can use simple DOM-appended items that call the same layout management functions.

**VFS Settings UI** is a straightforward restoration. All backend code is verified working: the `/browser/settings` route passes `api_tokens` and `webdav_endpoint` to the template, `_vfs_settings.html` renders token generation/revocation UI, and the API endpoints (`/api/auth/tokens` CRUD) are fully functional. The template has two CLAUDE.md violations (inline Lucide icon styles on lines 13 and 84) that may cause invisible icons in flex containers. The fix is to move icon sizing to CSS and add `flex-shrink: 0`. Additionally, after dockview renders a special-panel, `lucide.createIcons()` may need to be called to hydrate the icon placeholders.

**Primary recommendation:** Implement named layouts as a pure-frontend localStorage module (`named-layouts.js`) with ninja-keys integration; fix VFS Settings icon violations in the same phase.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| dockview-core | 4.11.0 (existing) | `toJSON()`/`fromJSON()` for layout serialization | Already live; confirmed round-trip working in Phase 30 |
| ninja-keys | existing (CDN) | Command palette with parent/children nested sub-menus | Already integrated; `parent` property supports hierarchical command navigation |
| localStorage API | native | Persist named layouts and auto-save across sessions | CONTEXT.md locked decision; consistent with `sempkm_` namespace pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| htmx | 2.0.4 (existing) | Settings page content loading into dockview panels | Existing; `htmx.process()` for re-init after panel DOM mount |
| lucide | 0.575.0 (existing) | Icons in VFS settings UI | Must call `lucide.createIcons()` after dockview panel renders settings content |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| localStorage | Backend API (REST) | CONTEXT.md locks localStorage; backend API adds complexity for single-user local-first PKM |
| ninja-keys `parent` property | Custom modal dialog | CONTEXT.md locks inline palette flow; modals add DOM complexity |

**Installation:** No new packages. All libraries are already loaded.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/static/js/
  workspace-layout.js        # MODIFY: auto-save to localStorage, expose save/restore/delete API
  workspace.js               # MODIFY: add Layout: commands to ninja-keys, wire user menu items
  named-layouts.js           # NEW: layout manager module (save, restore, delete, list, auto-save)

backend/app/templates/
  browser/_vfs_settings.html  # FIX: remove inline Lucide icon styles
  components/_sidebar.html    # MODIFY: add layout submenu items to user popover

frontend/static/css/
  workspace.css               # MODIFY: add toast notification styles
  settings.css                # MODIFY: add .btn-icon svg sizing rule for VFS copy buttons
```

### Pattern 1: Layout Manager Module (named-layouts.js)

**What:** A self-contained IIFE that manages localStorage read/write for named layouts and auto-save.
**When to use:** Loaded in workspace.html, exposes API on `window.SemPKMLayouts`.

```javascript
// Source: direct codebase analysis of existing localStorage patterns
(function() {
  'use strict';
  var LAYOUTS_KEY = 'sempkm_layouts';       // { "name": { layout: <SerializedDockview>, savedAt: <iso> } }
  var CURRENT_KEY = 'sempkm_layout_current'; // auto-save: <SerializedDockview>

  function _readLayouts() {
    try { return JSON.parse(localStorage.getItem(LAYOUTS_KEY)) || {}; }
    catch(e) { return {}; }
  }

  function _writeLayouts(obj) {
    localStorage.setItem(LAYOUTS_KEY, JSON.stringify(obj));
  }

  // Auto-save current layout (replaces sessionStorage approach)
  function autoSave() {
    var dv = window._dockview;
    if (!dv) return;
    try {
      localStorage.setItem(CURRENT_KEY, JSON.stringify(dv.toJSON()));
    } catch(e) {}
  }

  // Save named layout
  function save(name) {
    var dv = window._dockview;
    if (!dv || !name) return false;
    var layouts = _readLayouts();
    layouts[name] = { layout: dv.toJSON(), savedAt: new Date().toISOString() };
    _writeLayouts(layouts);
    return true;
  }

  // Restore named layout with best-effort stale handling
  function restore(name) {
    var layouts = _readLayouts();
    var entry = layouts[name];
    if (!entry || !entry.layout) return { success: false, skipped: [] };
    var dv = window._dockview;
    if (!dv) return { success: false, skipped: [] };
    try {
      dv.fromJSON(entry.layout);
      return { success: true, skipped: [] };
    } catch(err) {
      // Best-effort: geometry restored, some panels may have failed
      return { success: false, skipped: ['Layout partially restored'] };
    }
  }

  // Restore auto-saved current layout
  function restoreCurrent() {
    try {
      var raw = localStorage.getItem(CURRENT_KEY);
      if (raw) return JSON.parse(raw);
    } catch(e) {}
    return null;
  }

  function remove(name) {
    var layouts = _readLayouts();
    if (!layouts[name]) return false;
    delete layouts[name];
    _writeLayouts(layouts);
    return true;
  }

  function list() {
    var layouts = _readLayouts();
    return Object.keys(layouts).map(function(name) {
      return { name: name, savedAt: layouts[name].savedAt };
    });
  }

  window.SemPKMLayouts = {
    save: save,
    restore: restore,
    remove: remove,
    list: list,
    autoSave: autoSave,
    restoreCurrent: restoreCurrent
  };
})();
```

### Pattern 2: ninja-keys Nested Sub-menus via `parent` Property

**What:** Top-level "Layout: Restore..." opens a sub-menu showing saved layout names.
**When to use:** In `initCommandPalette()` when adding layout commands.

```javascript
// Source: github.com/ssleptsov/ninja-keys README
// ninja-keys supports parent/children hierarchy:
// - Parent item: { id: 'layout-restore', title: 'Layout: Restore...', children: [...] }
// - Child items: { id: 'layout-restore-myname', title: 'My Layout', parent: 'layout-restore', handler: fn }
// Using `parent` property on child items makes them appear when user selects parent

// Dynamic update pattern (already used for FTS results):
function _refreshLayoutPaletteItems(ninja) {
  // Remove old layout-restore-* and layout-delete-* items
  var baseData = ninja.data.filter(function(d) {
    return !d.id.startsWith('layout-restore-') && !d.id.startsWith('layout-delete-');
  });

  var layouts = window.SemPKMLayouts.list();
  layouts.forEach(function(l) {
    baseData.push({
      id: 'layout-restore-' + l.name,
      title: l.name,
      parent: 'layout-restore',
      handler: function() {
        var result = window.SemPKMLayouts.restore(l.name);
        if (result.skipped.length > 0) {
          showToast('Layout restored with ' + result.skipped.length + ' skipped item(s)');
        }
      }
    });
    baseData.push({
      id: 'layout-delete-' + l.name,
      title: l.name,
      parent: 'layout-delete',
      handler: function() {
        window.SemPKMLayouts.remove(l.name);
        _refreshLayoutPaletteItems(ninja);
      }
    });
  });

  ninja.data = baseData;
}
```

### Pattern 3: "Layout: Save As..." with Inline Text Input

**What:** The "Save As..." command opens a text input in the palette for naming.
**When to use:** When user selects "Layout: Save As..." from palette.

ninja-keys does not have a built-in text input mode. The implementation should use the existing search input: when the user selects "Layout: Save As...", open the palette to a parent that shows a prompt, and use the `selected` event with the search text as the layout name. Alternative: the handler closes the palette, prompts via `window.prompt()` (simple, reliable), or appends a small inline form.

**Recommended approach:** Use `window.prompt()` for the name input. It is simple, reliable, and consistent with the "no modal" constraint (browser prompt is not a DOM modal). If the project prefers a more polished approach, a tiny inline input can be appended to the palette's parent menu.

```javascript
// Simple approach that works reliably:
{
  id: 'layout-save-as',
  title: 'Layout: Save As...',
  section: 'Layout',
  handler: function() {
    var name = prompt('Layout name:');
    if (!name || !name.trim()) return;
    window.SemPKMLayouts.save(name.trim());
    showToast('Layout "' + name.trim() + '" saved');
    _refreshLayoutPaletteItems(ninja);
  }
}
```

**Note:** CONTEXT.md says "Naming via text input inline in Command Palette (no modal)." The `prompt()` approach is a fallback if inline text input proves too complex. The preferred implementation is to use ninja-keys' search input field: when the user navigates to the "Save As..." parent, the search text becomes the layout name. This can be achieved by listening to the `selected` event when parent is `layout-save-as` and using `e.detail.search` as the name.

### Pattern 4: Toast Notification for Stale Data Warnings

**What:** Lightweight toast notification that auto-dismisses.
**When to use:** After restoring a layout that has stale/missing panels.

```javascript
// Source: no existing toast system in codebase; create minimal implementation
function showToast(message, duration) {
  duration = duration || 3000;
  var toast = document.createElement('div');
  toast.className = 'sempkm-toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  // Trigger animation
  requestAnimationFrame(function() { toast.classList.add('sempkm-toast--visible'); });
  setTimeout(function() {
    toast.classList.remove('sempkm-toast--visible');
    setTimeout(function() { toast.remove(); }, 300);
  }, duration);
}
```

```css
/* Toast styles */
.sempkm-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  background: var(--color-bg-panel);
  color: var(--color-text-normal);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 13px;
  z-index: 10000;
  opacity: 0;
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.sempkm-toast--visible {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
```

### Pattern 5: User Popover Layout Submenu

**What:** Add layout management items to the existing user popover (`_sidebar.html`).
**When to use:** Secondary access point per CONTEXT.md decision.

The user popover in `_sidebar.html` (line 123-154) uses a `<div popover="auto" id="user-popover">` with simple anchor/button items. Layout items should follow the same DOM pattern:

```html
<div class="popover-divider"></div>
<button class="popover-item" onclick="openLayoutMenu(); document.getElementById('user-popover').hidePopover();">
  <i data-lucide="layout-dashboard" class="popover-icon"></i>
  <span>Layouts</span>
</button>
```

The `openLayoutMenu()` function opens the command palette directly to the layout sub-menu using `ninja.open({ parent: 'layout-restore' })`.

### Anti-Patterns to Avoid

- **Using sessionStorage for named layouts:** sessionStorage is tab-scoped and cleared on browser close. Named layouts must use localStorage per CONTEXT.md decision.
- **Building a custom layout picker dialog:** CONTEXT.md locks the interaction to the Command Palette with inline naming. Don't create a separate dialog/modal.
- **Storing panel content (HTML) in layout snapshots:** dockview `toJSON()` captures geometry, component names, and params -- NOT rendered content. Content is re-loaded via `createComponent.init()` on restore. Do not attempt to cache HTML.
- **Silently dropping stale panels on restore:** CONTEXT.md requires a toast listing skipped objects. Track which panel IDs fail during `fromJSON()` restore.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Layout serialization format | Custom JSON schema for panel positions/sizes | `dockview.toJSON()` / `dv.fromJSON()` | dockview's native format captures groups, sash sizes, panel positions, active states automatically |
| Nested command palette navigation | Custom dropdown/menu component | ninja-keys `parent` property | Already in use; `parent` creates hierarchical sub-menus natively |
| Tab bar rendering for restored layouts | Manual DOM recreation | dockview `fromJSON()` + existing `createComponent` | dockview rebuilds all UI from serialized state; `createComponent` re-fetches content via htmx |
| Token CRUD API | New endpoints | Existing `/api/auth/tokens` POST/GET/DELETE | All three endpoints verified working in Phase 27 |

**Key insight:** The heavy lifting (layout serialization, panel rendering, token API) is already implemented. This phase is pure integration work: wiring existing capabilities to new UX touch points.

---

## Common Pitfalls

### Pitfall 1: sessionStorage to localStorage Migration Race

**What goes wrong:** The current auto-save writes to `sessionStorage` key `sempkm_workspace_layout_dv` via `onDidLayoutChange`. If the migration to `localStorage` key `sempkm_layout_current` is not atomic, users could lose their current layout on the first page load after the update.
**Why it happens:** The old sessionStorage key is read at init time in `workspace-layout.js` line 181. If the new code only reads localStorage but the old sessionStorage still has the latest state, the layout is lost.
**How to avoid:** On init, check BOTH `localStorage.getItem('sempkm_layout_current')` and `sessionStorage.getItem('sempkm_workspace_layout_dv')`. Prefer localStorage if it exists; fall back to sessionStorage; migrate the sessionStorage value to localStorage on first load; then clear the sessionStorage key.
**Warning signs:** After deploying, user refreshes and sees empty workspace instead of their previous tabs.

### Pitfall 2: ninja-keys `parent` Children Not Refreshed After Save/Delete

**What goes wrong:** After saving a new layout or deleting one, the "Layout: Restore..." sub-menu still shows the old list of names.
**Why it happens:** ninja-keys `data` is a property that must be reassigned (not mutated) to trigger re-render. The existing FTS search code demonstrates this: it creates a new array with `ninja.data.slice()`, modifies it, and reassigns `ninja.data = newData`.
**How to avoid:** After every save/delete operation, call `_refreshLayoutPaletteItems(ninja)` which rebuilds the full data array. Use the same slice-and-reassign pattern as the FTS integration.
**Warning signs:** User saves "My Layout", opens Restore submenu, doesn't see it. Works after page reload.

### Pitfall 3: dockview `fromJSON()` Fails on Stale Component Names

**What goes wrong:** A saved layout references a component name (e.g., `object-editor`) with params (e.g., `{ iri: "http://example.org/deleted-object" }`). When restored, `createComponent` fires `htmx.ajax('GET', '/browser/object/...')` which returns 404. The panel renders but shows an error.
**Why it happens:** `fromJSON()` successfully restores geometry and calls `createComponent` for each panel. The component factory doesn't know the object no longer exists until the htmx request completes.
**How to avoid:** This is expected behavior per CONTEXT.md ("best-effort restore... open tabs that still exist, show brief toast listing any skipped objects"). The implementation should: (a) let `fromJSON()` restore all geometry, (b) each panel's htmx request naturally handles 404 (show empty/error state), (c) optionally, pre-validate panel IRIs before restore to build the skip list for the toast.
**Warning signs:** Restored layout shows panels with "Failed to load" messages.

### Pitfall 4: Lucide Icons Invisible in VFS Settings Flex Containers

**What goes wrong:** The copy buttons in `_vfs_settings.html` use inline Lucide icon styles (`style="width:14px;height:14px;"`) inside flex containers. Per CLAUDE.md, the icons render as 0px width.
**Why it happens:** Lucide replaces `<i data-lucide="copy">` with `<svg>` which becomes a flex item. Without `flex-shrink: 0`, the browser compresses the SVG to 0px width.
**How to avoid:** Remove inline `style` attributes from Lucide icons in `_vfs_settings.html`. Add CSS rule `.btn-icon svg { width: 14px; height: 14px; flex-shrink: 0; stroke: currentColor; }` to `settings.css`. Also fix the JavaScript-generated icons in `vfsSubmitTokenForm` (line 84).
**Warning signs:** Copy buttons show no visible icon, just empty clickable area.

### Pitfall 5: `lucide.createIcons()` Not Called After Dockview Panel Mount

**What goes wrong:** When the Settings tab is opened as a dockview `special-panel`, the content is loaded via `htmx.ajax()`. The Lucide `<i data-lucide="...">` elements are in the HTML response but not yet converted to SVGs.
**Why it happens:** `lucide.createIcons()` runs on DOMContentLoaded but not automatically after htmx swaps into dockview panels. The settings_page.html template does call `lucide.createIcons()` at the bottom of its script block, but this only runs when the template is first parsed.
**How to avoid:** The existing `htmx:afterSwap` handler in workspace.js (line 1613-1617) already calls `lucide.createIcons({ root: target })` for swapped content. Verify this fires correctly for settings panel content. If not, add a call in the `special-panel` branch of `createComponent.init()`.
**Warning signs:** Settings page shows text labels but no icons (search, copy, etc.).

### Pitfall 6: Layout Names with Special Characters in localStorage Keys

**What goes wrong:** If a user names a layout with characters like quotes, brackets, or emoji, the JSON serialization of the layouts object could corrupt or fail to parse.
**Why it happens:** The layout name is used as a JSON object key. JSON.stringify/parse handle arbitrary string keys correctly, so this is actually safe. However, the ninja-keys display could render incorrectly if the title contains HTML-special characters.
**How to avoid:** Sanitize the layout name for display in ninja-keys (escape `<`, `>`, `&`). Use the raw string as the localStorage key (JSON handles it). Trim whitespace and reject empty strings.
**Warning signs:** Layout name with `<script>` tag causes XSS in command palette.

---

## Code Examples

### Auto-Save Migration: sessionStorage to localStorage

```javascript
// Source: workspace-layout.js lines 142-145 (current), modified for localStorage
// Replace the current onDidLayoutChange handler:

// CURRENT (sessionStorage - loses state on browser close):
dv.onDidLayoutChange(function () {
  try {
    sessionStorage.setItem(DV_LAYOUT_KEY, JSON.stringify(dv.toJSON()));
  } catch (e) {}
  // ... htmx re-process ...
});

// NEW (localStorage - survives browser close):
dv.onDidLayoutChange(function () {
  try {
    localStorage.setItem('sempkm_layout_current', JSON.stringify(dv.toJSON()));
  } catch (e) {}
  // ... htmx re-process unchanged ...
});
```

### Init Migration: Read from Both Storage Locations

```javascript
// Source: workspace-layout.js lines 179-196 (current), modified for migration
var saved = null;
try {
  // Prefer localStorage (new)
  var rawLS = localStorage.getItem('sempkm_layout_current');
  if (rawLS) {
    saved = JSON.parse(rawLS);
  } else {
    // Fall back to sessionStorage (old) for first-load migration
    var rawSS = sessionStorage.getItem('sempkm_workspace_layout_dv');
    if (rawSS) {
      saved = JSON.parse(rawSS);
      // Migrate to localStorage
      localStorage.setItem('sempkm_layout_current', rawSS);
      sessionStorage.removeItem('sempkm_workspace_layout_dv');
    }
  }
} catch (e) {}
```

### ninja-keys Layout Commands Registration

```javascript
// Source: workspace.js initCommandPalette(), following existing pattern
// These are top-level items added to ninja.data alongside existing commands:

// Parent items (top-level palette)
{ id: 'layout-save-as', title: 'Layout: Save As...', section: 'Layout', handler: layoutSaveAsHandler },
{ id: 'layout-restore', title: 'Layout: Restore...', section: 'Layout', children: [] },
{ id: 'layout-delete', title: 'Layout: Delete...', section: 'Layout', children: [] },

// Children are added dynamically by _refreshLayoutPaletteItems()
// Each child uses parent property:
{ id: 'layout-restore-myname', title: 'My Layout', parent: 'layout-restore', handler: fn }
```

### VFS Settings Icon Fix

```css
/* Source: settings.css - fix CLAUDE.md violation */
/* Add to settings.css after existing .btn-icon styles */
.vfs-endpoint-display .btn-icon svg,
.vfs-token-value-row .btn-icon svg,
.vfs-token-reveal .btn-icon svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  stroke: currentColor;
}
```

```html
<!-- Source: _vfs_settings.html - remove inline styles -->
<!-- BEFORE (broken in flex): -->
<i data-lucide="copy" style="width:14px;height:14px;"></i>

<!-- AFTER (CSS handles sizing): -->
<i data-lucide="copy"></i>
```

### User Popover Layout Item

```html
<!-- Source: _sidebar.html - add before the logout divider -->
<div class="popover-divider"></div>
<button class="popover-item" onclick="document.querySelector('ninja-keys').open({parent: 'layout-restore'}); document.getElementById('user-popover').hidePopover();">
  <i data-lucide="layout-dashboard" class="popover-icon"></i>
  <span>Layouts</span>
</button>
```

---

## Existing Codebase Inventory

### Files That Change

| File | Change Type | What Changes |
|------|-------------|------------|
| `frontend/static/js/workspace-layout.js` | MODIFY | Auto-save target changes from sessionStorage to localStorage; init reads both for migration; old sessionStorage key cleared |
| `frontend/static/js/workspace.js` | MODIFY | Add layout commands to `initCommandPalette()`; add `_refreshLayoutPaletteItems()`; add `showToast()` utility; wire user menu |
| `backend/app/templates/components/_sidebar.html` | MODIFY | Add "Layouts" item to user popover menu |
| `backend/app/templates/browser/_vfs_settings.html` | FIX | Remove inline Lucide icon styles (lines 13, 84); fix JavaScript-generated icon HTML |
| `frontend/static/css/settings.css` | FIX | Add `.btn-icon svg` sizing rule for VFS copy buttons |
| `frontend/static/css/workspace.css` | MODIFY | Add toast notification CSS |

### New Files

| File | Purpose |
|------|---------|
| `frontend/static/js/named-layouts.js` | Layout manager module: save, restore, delete, list, auto-save |

### Files That Do NOT Change

| File | Why |
|------|-----|
| `backend/app/browser/router.py` | Settings route already passes VFS data; no new backend routes needed |
| `backend/app/auth/router.py` | Token CRUD endpoints already complete |
| `backend/app/templates/browser/settings_page.html` | VFS section already wired; template structure unchanged |
| `frontend/static/css/dockview-sempkm-bridge.css` | No layout-specific CSS needed in bridge |

### Key Existing Code Patterns

**localStorage namespace:** All frontend state uses `sempkm_` prefix:
- `sempkm_theme` (theme.js)
- `sempkm_pane_sizes` (workspace.js)
- `sempkm_bottom_panel` (workspace.js)
- `sempkm_fts_fuzzy` (workspace.js)
- `sempkm_carousel_view` (workspace.js)
- `sempkm_sidebar_collapsed` (sidebar.js)
- `sempkm_sidebar_sections` (sidebar.js)
- `sempkm_props_collapsed` (workspace.js, Phase 31)

New keys follow convention: `sempkm_layouts`, `sempkm_layout_current`.

**ninja-keys dynamic data pattern:** Already demonstrated by FTS search integration (workspace.js lines 1037-1120):
1. Build new array from `ninja.data.slice()` or `.filter()`
2. Push/concat new items
3. Reassign `ninja.data = newData`

**dockview auto-save:** Current handler (workspace-layout.js line 143-146) fires on every `onDidLayoutChange`. The same handler will use localStorage instead of sessionStorage.

---

## Discretion Recommendations

### Delete Confirmation: No Confirm (with undo toast)

**Recommendation:** Skip the confirmation dialog. Show a 5-second "Layout deleted" toast with an "Undo" button. This is faster for intentional deletes and recoverable for accidental ones.

Rationale: The user deliberately navigated to "Layout: Delete..." > selected a name. Requiring an additional confirmation adds friction. The undo-toast pattern is standard in modern UIs (Gmail, Slack).

### Active Layout Name Indicator: Yes, Subtle

**Recommendation:** Show the active layout name in the status bar area or as a subtitle in the user popover. After restoring a named layout, set `window._activeLayoutName = name`. Display it in the user popover as a small text under the Layouts button: "Active: My Layout". Clear it when the user makes changes (any `onDidLayoutChange` after a restore sets it to null).

### Overwrite Behavior: Silent Replace with Toast

**Recommendation:** If the user saves with an existing name, silently overwrite the old snapshot and show a toast: "Layout 'name' updated". No prompt. Rationale: the user typed the exact same name -- they intend to update.

### Toast Duration: 3 Seconds (Standard), 5 Seconds (with Undo)

**Recommendation:** Standard informational toasts (saved, restored) auto-dismiss after 3 seconds. Toasts with undo action (delete) stay for 5 seconds. All toasts can be manually dismissed by clicking.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sessionStorage auto-save (tab-scoped) | localStorage auto-save (persists across sessions) | Phase 33 (this phase) | Layout survives browser close; consistent with CONTEXT.md decision |
| No named layouts | Named save/restore via Command Palette + user menu | Phase 33 (this phase) | DOCK-02 requirement fulfilled |
| VFS Settings UI with inline icon styles | CSS-only icon sizing per CLAUDE.md | Phase 33 (this phase) | BUG-02 resolved; icons visible in flex containers |

---

## Open Questions

1. **ninja-keys inline text input for "Save As..."**
   - What we know: CONTEXT.md says "Naming via text input inline in Command Palette (no modal)." ninja-keys has a search input at the top but no built-in "prompt for input" mode.
   - What's unclear: Whether the search input text can be captured as the layout name when a "Save" sub-command is selected. The `selected` event provides `{ search: string }` which could be the name.
   - Recommendation: Implement as a `parent` sub-menu: "Layout: Save As..." opens a sub-view with a single item "Type a name above and press Enter." The search field value is captured from `e.detail.search` on the `selected` event. If this proves unreliable, fall back to `prompt()`. Research confidence: MEDIUM (ninja-keys event payload not fully verified for this use case).

2. **dockview `fromJSON()` error granularity**
   - What we know: Official docs say "the dock will throw an Error and reset gracefully." The Phase 30 research confirms try/catch is the right pattern.
   - What's unclear: Whether `fromJSON()` provides per-panel error reporting (which specific panels failed) or only throws a single error for the whole layout.
   - Recommendation: Wrap `fromJSON()` in try/catch. On error, compare the restored panels (`dv.panels`) against the saved layout's panel list to determine which were skipped. This delta becomes the toast message.

3. **beforeunload auto-save timing**
   - What we know: The current `onDidLayoutChange` handler fires on every layout mutation. For named layouts, the auto-save to `sempkm_layout_current` should also fire on `beforeunload` to capture the very latest state.
   - What's unclear: Whether `dv.toJSON()` is safe to call synchronously in a `beforeunload` handler (it must complete within the browser's unload timeout).
   - Recommendation: `dv.toJSON()` is a synchronous operation that returns a plain object. `JSON.stringify()` + `localStorage.setItem()` are also synchronous. This should be safe in `beforeunload`. Add the handler as a belt-and-suspenders measure alongside the `onDidLayoutChange` save.

---

## Sources

### Primary (HIGH confidence)

- SemPKM `frontend/static/js/workspace-layout.js` -- direct analysis: `toJSON()`/`fromJSON()` at lines 145/187, `sessionStorage` key `sempkm_workspace_layout_dv`, `DockviewComponent` init at line 137
- SemPKM `frontend/static/js/workspace.js` -- direct analysis: `initCommandPalette()` at line 835, ninja-keys dynamic data pattern at lines 985-1003, FTS search integration at lines 1037-1120, `openSettingsTab()` at line 610
- SemPKM `backend/app/templates/browser/_vfs_settings.html` -- direct analysis: all 117 lines; inline icon style violations at lines 13, 84
- SemPKM `backend/app/templates/browser/settings_page.html` -- direct analysis: VFS section at lines 85-92
- SemPKM `backend/app/templates/components/_sidebar.html` -- direct analysis: user popover at lines 123-154
- SemPKM `backend/app/auth/router.py` -- direct analysis: token CRUD at lines 236-305
- SemPKM `backend/app/browser/router.py` -- direct analysis: settings route at lines 88-127
- SemPKM `.planning/phases/30-dockview-phase-a-migration/30-RESEARCH.md` -- HIGH confidence for dockview API patterns, toJSON/fromJSON, onDidLayoutChange
- [ninja-keys GitHub README](https://github.com/ssleptsov/ninja-keys) -- `parent` property, `open({ parent })` method, `selected` event payload, `children` array structure
- [dockview saving state docs](https://dockview.dev/docs/core/state/save/) -- `toJSON()` returns `SerializedDockview`
- [dockview loading state docs](https://dockview.dev/docs/core/state/load/) -- `fromJSON()` error handling, graceful reset

### Secondary (MEDIUM confidence)

- ninja-keys `selected` event `search` property for inline naming -- inferred from event API docs, not directly tested with this use case

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use; no new dependencies
- Architecture: HIGH -- based on direct codebase analysis of all 7 affected files; localStorage pattern confirmed across 8 existing keys
- Pitfalls: HIGH -- CLAUDE.md icon violations confirmed at exact line numbers; sessionStorage migration pattern derived from existing code; ninja-keys data refresh pattern confirmed from FTS implementation
- VFS Settings: HIGH -- all backend code verified working; template and CSS exist; issue is purely frontend icon styling

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (all libraries are pinned versions; patterns are stable)