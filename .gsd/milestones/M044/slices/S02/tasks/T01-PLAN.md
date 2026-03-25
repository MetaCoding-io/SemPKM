---
estimated_steps: 16
estimated_files: 2
skills_used: []
---

# T01: Wire dockview panel dispose() to cleanup registry

The cleanup.js IIFE exports `registerCleanup()` to window but keeps `runCleanup()` private. Dockview's content renderers in workspace-layout.js lack `dispose()` methods, so when panels are closed via dockview's tab close button, registered cleanup functions never fire. This task fixes both sides of the gap.

**cleanup.js changes:**
- Export `runCleanup` to `window.runCleanup` alongside the existing `window.registerCleanup`

**workspace-layout.js changes:**
1. Add `dispose()` to the **object-editor** renderer (the one returning `{ element: el, init: function(params) { ... } }` for `options.name === 'object-editor'`). The dispose should:
   - Call `window.runCleanup(el.id)` if el has an id
   - Iterate `el.querySelectorAll('[id]')` and call `window.runCleanup(childId)` for each
   
2. Add `dispose()` to the **view-panel** renderer (same pattern)

3. Add `dispose()` to the **special-panel** renderer (same pattern)

4. Remove the dead `_cytoscapeInstances` code in the view-panel renderer's `onDidVisibilityChange` handler (lines ~198-199 reference `window._cytoscapeInstances` which is never populated anywhere)

**Important constraints:**
- The dispose() function is called synchronously by dockview — do not use async operations
- The `el` variable from the closure is accessible inside dispose() (same scope as init())
- Keep the existing `init` and `element` properties unchanged
- The tab renderer already has a `dispose()` — don't touch that one (it's for tab chrome, not panel content)

## Inputs

- `frontend/static/js/cleanup.js`
- `frontend/static/js/workspace-layout.js`

## Expected Output

- `frontend/static/js/cleanup.js`
- `frontend/static/js/workspace-layout.js`

## Verification

1. `rg 'window.runCleanup' frontend/static/js/cleanup.js` — shows the export line
2. `rg 'dispose' frontend/static/js/workspace-layout.js` — shows dispose on all 3 content renderers plus the existing tab dispose (4+ matches)
3. `rg '_cytoscapeInstances' frontend/static/js/` — returns zero results (dead code removed)
4. `node -e "const fs=require('fs'); const c=fs.readFileSync('frontend/static/js/cleanup.js','utf8'); if(!c.includes('window.runCleanup')) { process.exit(1); }"` — exits 0
5. `node -e "const fs=require('fs'); const c=fs.readFileSync('frontend/static/js/workspace-layout.js','utf8'); const d=c.match(/dispose:\s*function/g); if(!d||d.length<3) { console.error('Expected 3+ dispose in content renderers, found', d?d.length:0); process.exit(1); }"` — exits 0
