# S02 Research: Multiple View Instances + Saved Views Fix

**Date:** 2026-03-21  
**Depth:** Targeted — known technology, established patterns, moderate integration complexity  

## Summary

S02 delivers two features: (1) opening multiple instances of the same generic view type as independent dockview tabs, and (2) fixing the "Saved Views" explorer folder so views load/display/create/unpin correctly. Both features build on S01's carousel removal and scope binding.

The codebase has clear patterns for both — tab deduplication uses `dv.panels.find()` with a static `tabKey`, and saved views use the existing promote/demote RDF flow. The main changes are: making tab IDs unique per scope, adding a "Save Current View" UI action, and extending the `PromotedViewData` model to persist type filter and scope metadata alongside the renderer type.

## Requirements Targeted

| ID | Description | Status |
|----|-------------|--------|
| VIEW-10 | Multiple view instances as tabs with different scopes | New (Should-have) |
| VIEW-11 | Saved views load/display/create/unpin correctly | New (Must-have) |

## Recommendation

Three tasks in strict order:

1. **T01: Multiple view instances** — Change `openGenericViewTab()` tab ID scheme from `generic-view:{renderer}` to `generic-view:{renderer}:{scopeQuery}` (or `generic-view:{renderer}:{counter}` for unsaved instances). Update `workspace-layout.js` special-panel init to pass scope through. Add UI affordance to open a new instance (e.g. Shift+click or a "New Instance" option).

2. **T02: Save current view** — Add a "Save View" button to `view_toolbar.html` that opens a name prompt and calls the promote API. Extend `promote_query()` to accept optional `type_filter` and `scope_query` metadata stored as RDF triples on the PromotedView. Extend `PromotedViewData` with those fields. When saving a generic view without a scope query, create a transient saved query representing the current filter state.

3. **T03: Fix saved views display + reopen** — Fix `my_views.html` to show correct icons and handle the new metadata. When clicking a saved view, open it via `openGenericViewTab(renderer, scopeQuery)` instead of `openViewTab(specIri)`. Add unit tests for new promote fields and tab ID uniqueness.

## Implementation Landscape

### 1. Multiple View Instances — Tab Deduplication

**Current behavior (workspace.js:3217-3248):**
```javascript
function openGenericViewTab(renderer, scopeQuery) {
    var tabKey = 'generic-view:' + renderer;  // ← PROBLEM: fixed per renderer
    var existing = dv.panels.find(function(p) { return p.id === tabKey; });
    if (existing) { existing.api.setActive(); return; }  // ← dedup blocks 2nd tab
    // ...addPanel with id: tabKey...
}
```

**Fix:** Change `tabKey` to include scope:
```javascript
var tabKey = 'generic-view:' + renderer + (scopeQuery ? ':' + scopeQuery : '');
```

This allows: "Table View (all)" + "Table View (scope=xyz)" as separate tabs. For truly multiple unscoped instances, add a counter: `'generic-view:' + renderer + ':' + Date.now()`.

**Tab labels** need to differentiate instances. When a scope query is set, append the query name to the label (e.g. "Table View — My Projects Query"). The scope query name can be read from the `<select class="view-scope-select">` option text.

**workspace-layout.js:237-249** — The special-panel init for `generic-view` already passes `renderer`, `selectedType`, and `scopeQuery` from `params.params`. No changes needed to the panel loader itself.

**Risk:** Low. The panel loader already respects `scopeQuery` from params. The only change is tab ID uniqueness.

### 2. Save Current View

**Current promote flow:**
1. User has a saved SPARQL query in SPARQL console
2. User clicks "Promote to view" → `POST /api/sparql/saved/{query_id}/promote` with `display_label` + `renderer_type`
3. Backend creates `PromotedView` RDF triples linked to the saved query via `sempkm:fromQuery`
4. View appears in Saved Views folder

**New "Save Current View" flow (what needs building):**
1. User is in a generic view with type filter + scope query
2. User clicks "Save View" button in toolbar
3. JS prompt asks for a name
4. Frontend calls a new endpoint (or reuses promote) with: `display_label`, `renderer_type`, `scope_query` (query ID if present), `type_filter` (type IRI if selected), `filter_text` (current search text)
5. Backend creates the promoted view — if no scope query exists, saves with just renderer+type metadata

**PromotedViewData extension (query_service.py:132-138):**
Current fields: `id`, `query_id`, `display_label`, `renderer_type`, `query_text`
Need to add: `type_filter: str = ""`, `scope_query_id: str = ""`

**New RDF predicates needed:**
```python
PRED_TYPE_FILTER = VOCAB + "typeFilter"      # type IRI for the view
PRED_SCOPE_QUERY = VOCAB + "scopeQueryId"    # saved query UUID used as scope
```

**promote_query() changes (query_service.py:582-623):**
- Accept optional `type_filter` and `scope_query_id` parameters
- Add corresponding RDF triples to the INSERT DATA
- Update `list_promoted_views()` SPARQL to SELECT these with OPTIONAL
- Update `PromotedViewData` construction

**Alternative: Direct view save without a saved query.** Current flow requires a saved query (`PRED_FROM_QUERY`). For generic views that have no scope query, the promoted view can link to a synthetic "empty" query, or `PRED_FROM_QUERY` can become optional. Making it optional is cleaner — a promoted view with no `fromQuery` is a "view configuration" rather than a "promoted query".

**Endpoint options:**
- Reuse `POST /api/sparql/saved/{query_id}/promote` — awkward because generic views may not have a saved query
- New endpoint `POST /api/views/save` — cleaner, accepts `{name, renderer, type_filter, scope_query_id}`, creates the PromotedView directly

Recommendation: **New endpoint** `POST /api/views/save` in `views/router.py` that calls `query_service.save_promoted_view()` (new method). This avoids the constraint that promote requires an existing saved query.

### 3. Saved Views Display Fix

**my_views.html (current):**
- Renders `specs` (ViewSpec list) with `query_id_map` for demote action
- `onclick` calls `openViewTab(spec_iri, label, renderer_type)`
- `openViewTab` uses `component: 'view-panel'` which routes to `/browser/views/{viewType}/{encodedViewId}`

**Problem:** `openViewTab()` routes to `/browser/views/table/{urn:sempkm:user-view:uuid}` — these are dedicated model-view endpoints, not generic view endpoints. For saved generic views, we need to route through the generic endpoint with the saved scope/type parameters.

**Fix in my_views.html:**
Change `onclick` to call `openGenericViewTab(renderer, scopeQuery)` for generic saved views, passing the stored scope query and type filter. The `openGenericViewTab` function already accepts `scopeQuery` (from S01).

Additionally, `openGenericViewTab` needs to accept `typeFilter` parameter so saved views with a type filter restore correctly:
```javascript
function openGenericViewTab(renderer, scopeQuery, typeFilter) {
    // ...set localStorage selectedType if typeFilter provided...
}
```

**my_views.html rendering fixes:**
- Add renderer-type icon using Lucide (table → `table`, card → `layout-grid`, graph → `share-2`) — already present in current template
- Show scope query name alongside label if the view has a scope
- Pass `scopeQuery` and `typeFilter` as data attributes so onclick can forward them

**views_explorer.html** — The "Saved Views" folder loads lazily via `hx-get="/browser/my-views"` with `hx-trigger="intersect once"`. This works. No changes needed to the folder structure.

### Key Files

| File | Change |
|------|--------|
| `frontend/static/js/workspace.js` | `openGenericViewTab()` — unique tab IDs, accept typeFilter, label differentiation |
| `frontend/static/js/workspace-layout.js` | Pass `typeFilter` in generic-view URL construction |
| `backend/app/templates/browser/view_toolbar.html` | Add "Save View" button (Lucide `bookmark` icon) |
| `backend/app/sparql/query_service.py` | Extend `PromotedViewData`, add `save_promoted_view()` method, new predicates |
| `backend/app/views/router.py` | New `POST /api/views/save` endpoint |
| `backend/app/templates/browser/my_views.html` | Route saved generic views through `openGenericViewTab()`, pass scope/type |
| `backend/app/browser/workspace.py` | Update `my_views()` to pass scope/type metadata from PromotedViewData |
| `frontend/static/css/views.css` | Minor: save button styling in toolbar |
| `backend/tests/test_view_save.py` | New: unit tests for save_promoted_view, list_promoted with new fields |

### Patterns to Follow

1. **Tab ID scheme** — Follows existing patterns like `dashboard:{id}`, `app-page:{appId}:{pageId}`. Use `generic-view:{renderer}:{scope}` for scoped and `generic-view:{renderer}:{timestamp}` for unscoped duplicates.

2. **RDF triple extension** — Follow `promote_query()` pattern: add OPTIONAL triples to INSERT DATA, OPTIONAL clauses to SELECT in `list_promoted_views()`.

3. **Toolbar button** — Follow scope dropdown pattern already in `view_toolbar.html`. New button goes in `.view-toolbar-right`, guarded by `is_generic`.

4. **Lucide icon sizing** — Per CLAUDE.md: always size via CSS with `flex-shrink: 0`, never inline styles. The `.panel-btn svg` block in `workspace.css` is the reference.

### Constraints

- `VALID_RENDERERS = {"table", "card", "graph"}` — new kanban renderer (S04) not yet registered; save view should work with any string in this set
- `PromotedView` RDF triples live in `urn:sempkm:queries` named graph — all changes stay in that graph
- Tab IDs must be unique strings for dockview — duplicate IDs cause silent panel replacement
- `openGenericViewTab` is exported via `window.openGenericViewTab` — HTML onclick handlers depend on this signature; new parameters must be optional/backward-compatible

### Verification

1. **Multiple instances:** Open "Table View" from explorer → table tab appears. Change scope query to "X" → apply. Open "Table View" again from explorer → second tab appears (different scope or empty scope). Both tabs show different data.
2. **Save view:** In a generic table view with type filter "Person" and scope query "My Query", click "Save View" → enter name → confirm. Check `/browser/my-views` — new entry appears with correct icon, label.
3. **Reopen saved view:** Close all tabs. Click saved view in Saved Views folder → generic view opens with correct renderer, type filter, and scope query restored.
4. **Unpin:** Click unpin button on a saved view entry → entry disappears from Saved Views folder. Underlying saved query (if any) remains intact.
5. **Unit tests:** `promote_query`/`save_promoted_view` with type_filter and scope_query; `list_promoted_views` returns new fields; tab key uniqueness logic.
6. **Syntax check:** `python3 -c "import ast; ast.parse(open('backend/app/sparql/query_service.py').read())"` — no errors
7. **Grep check:** `grep -rn "generic-view:" frontend/static/js/workspace.js` — verify new tab ID pattern
