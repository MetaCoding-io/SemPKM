# S02 Research: Explorer & Nav Cleanup + Object Tab Refresh

## Summary

Four well-scoped fixes touching backend (1 file), templates (4 files), JS (1 file), and CSS (1 file). All use established patterns already in the codebase. No new libraries, no risky integration, no ambiguous requirements. This is light research — the work is straightforward.

## Scope Items

| Issue | What | Risk |
|-------|------|------|
| #11 | Strip " Shape" suffix from explorer type labels | Trivial — 1-line backend change |
| #10 | Replace event log placeholder with lazy-loaded content | Trivial — the lazy-load already works; just fix the placeholder text |
| #12 | VFS mount dropdown shows human-readable model names | Low — add `dcterms:title` to SPARQL query |
| #65 | Add refresh button to object tab toolbar | Low — reuse `loadObjectContent()` pattern |

## Implementation Landscape

### #11 — Strip " Shape" Suffix (D391)

**Root cause:** All SHACL NodeShapes in model shapes files have `rdfs:label` values like "Project Shape", "Task Shape", etc. There is no `sh:name` on any NodeShape — `_resolve_label()` falls through to `rdfs:label`.

**Files:**
- `backend/app/services/shapes.py` — `get_types()` at line 556. Strip suffix here per D391.
- The template `backend/app/templates/browser/nav_tree.html` line 23 renders `{{ type.label }}` raw — no change needed there once backend strips.
- `frontend/static/js/workspace.js` line 2094-2095 already has a client-side strip for the command palette — becomes redundant but harmless.

**Change:** In `get_types()`, after building the types list, strip trailing " Shape" from each label:
```python
{"iri": form.target_class, "label": form.label.removesuffix(" Shape")}
```

**Verification:** Check that the nav tree shows "Project" not "Project Shape". Check that no downstream code depends on the " Shape" suffix (grep for `" Shape"` in templates/JS — the only consumer is the workspace.js regex which becomes a no-op).

### #10 — Event Log Placeholder

**Current state:** `backend/app/templates/browser/workspace.html` line 180-184:
```html
<div class="panel-pane active" id="panel-event-log">
  <div class="panel-placeholder">
    <i data-lucide="activity" ...></i>
    Event Log Explorer — coming in Phase 16
  </div>
</div>
```

The lazy-load handler in `frontend/static/js/workspace.js` line 534 already replaces `.panel-placeholder` content with htmx GET to `/browser/events` when the tab is clicked. The `/browser/events` endpoint and `event_log.html` template are fully built.

**Issue:** The static text says "coming in Phase 16" — gives the impression of an unbuilt feature. The lazy-load replaces it on first click, so the user only sees this briefly.

**Fix:** Change the placeholder text to "Loading event log..." or use `hx-trigger="load"` on the pane itself for eager loading (event-log is the default active tab). The simplest fix: just update the placeholder text since the lazy-load fires immediately when the bottom panel opens.

**Files:** `backend/app/templates/browser/workspace.html` — line 183 only.

### #12 — VFS Mount Dropdown Labels

**Current state:** `backend/app/vfs/mount_router.py` line 270-288:
- The `list_mounts()` SPARQL for model mounts only fetches `?modelId`
- Mount `name` is set to raw `model_id` (e.g., "basic-pkm")
- Frontend renders `m.name + ' (' + m.strategy + ')'` → "basic-pkm (by-type)"

**Fix:** Add `dcterms:title` to the model mount SPARQL query:
```sparql
SELECT DISTINCT ?modelId ?name FROM <urn:sempkm:models>
WHERE {
  ?model a <urn:sempkm:MentalModel> ;
         <urn:sempkm:modelId> ?modelId .
  OPTIONAL { ?model <http://purl.org/dc/terms/title> ?name }
}
ORDER BY ?modelId
```
Then use `?name` (with `?modelId` as fallback) for the mount's `name` field. This gives "Basic PKM (by-type)" in the dropdown.

**Files:**
- `backend/app/vfs/mount_router.py` — `list_mounts()` SPARQL and dict construction (lines 270-288)

**Verification:** Open workspace → OBJECTS dropdown → VFS mounts optgroup shows human-readable names.

### #65 — Object Tab Refresh Button

**Current state:** Object tabs have a toolbar with: star, delete, properties toggle, Edit, Save. No refresh. The tab content is loaded via `loadObjectContent(objectIri, mode)` (workspace.js line 224) which uses `htmx.ajax('GET', '/browser/object/' + iri, ...)`.

**Plan:**
1. Add a `refreshObjectTab(objectIri)` function that calls `loadObjectContent()` for the active panel's IRI
2. Export it to `window.SemPKM.refreshObjectTab`
3. Add a refresh button (lucide `refresh-cw` icon) to the toolbar in both `object_tab.html` and `object_tab_app.html`, positioned after the star button
4. The button calls `SemPKM.refreshObjectTab('{{ object_iri }}')`
5. Style: same as `.star-btn` — small icon button in the toolbar actions area

**Files:**
- `backend/app/templates/browser/object_tab.html` — add button after star-btn (around line 24)
- `backend/app/templates/browser/object_tab_app.html` — add button after star-btn (around line 24)
- `frontend/static/js/workspace.js` — add `refreshObjectTab()` function + export
- `frontend/static/css/workspace.css` — style the refresh button (can reuse `.star-btn` styling or create a `.refresh-btn` class following the same pattern)

**CSS note (CLAUDE.md rule):** Lucide icon inside the button needs `flex-shrink: 0; stroke: currentColor;` on the SVG, sized via CSS not inline styles.

## Task Decomposition Recommendation

**Natural split into 2 tasks:**

**T01 — Backend fixes + template updates:** Strip " Shape" in `get_types()`, update event log placeholder text, add `dcterms:title` to VFS mount SPARQL query. All backend/template changes.
- Files: `backend/app/services/shapes.py`, `backend/app/templates/browser/workspace.html`, `backend/app/vfs/mount_router.py`
- Verify: Run existing backend tests, grep for regressions

**T02 — Object tab refresh button:** Add JS function, template buttons, CSS. Pure frontend.
- Files: `frontend/static/js/workspace.js`, `backend/app/templates/browser/object_tab.html`, `backend/app/templates/browser/object_tab_app.html`, `frontend/static/css/workspace.css`
- Verify: Open an object tab → see refresh icon → click → content reloads

Both tasks are independent — no ordering constraint.

## Constraints & Gotchas

1. **`get_types()` is cached** via `get_node_shapes()` which uses `TTLCache`. The " Shape" strip happens on the output of cached data, so it's fine — no cache invalidation needed.
2. **`_resolve_label()` is also used for PropertyGroups** (line 302). The strip should NOT be in `_resolve_label()` — only in `get_types()`. PropertyGroup labels like "Relationships" don't have " Shape".
3. **Two object tab templates** exist: `object_tab.html` (standard) and `object_tab_app.html` (app-rendered). Both need the refresh button.
4. **The refresh button must call `loadObjectContent()` which also reloads the right pane** via `loadRightPane()`. This is the right behavior — a full refresh should update everything.
5. **`loadObjectContent` is NOT exported** to `window.SemPKM`. Either export it or create a small wrapper `refreshObjectTab` that is exported.

## Verification Strategy

- Backend: `cd backend && .venv/bin/python -m pytest tests/ -x -q` (confirm no regressions from shape label strip or mount query change)
- Template: grep for `" Shape"` in nav_tree output (should be gone)
- Browser: Open workspace → check explorer labels, event log tab, VFS dropdown, object refresh button
- E2E: Existing nav-tree E2E tests should pass with the cleaned labels
