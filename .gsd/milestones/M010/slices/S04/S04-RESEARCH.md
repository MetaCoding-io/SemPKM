# S04: Workspace contributions + custom renderer — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

S04 wires the RSS Reader into the workspace integration layer: workspace views in the explorer sidebar, a right pane "Related Articles" section, command palette entries, and a custom `rss:Article` object renderer. All infrastructure exists from M009 (validated via test-app), and S03 already created the fragment endpoints and templates that S04's contributions will surface. The work is largely manifest configuration + 2 new fragment endpoints + 1 navigate-action fix + unit tests.

The biggest discovery is that the "Open RSS Reader" command palette entry uses `actionType: navigate` which does `window.location.href = path` — this navigates **away** from the workspace SPA. The fix is to extend the JS handler to recognize app page paths and call `openAppPageTab()` instead, or to add a new `openPage` action type in the manifest schema and JS handler. The simpler fix is to enhance the `commands_list` API to include `appId`/`pageId` for navigate entries that match app pages, then have the JS handler check for those fields and call `openAppPageTab()`.

The custom object renderer is straightforward: add `objectRenderers` to the manifest with type `urn:sempkm:model:rss-feeds:Article` and a `read` mode pointing to a new fragment. The fragment reuses the existing reading pane query and template pattern from S03.

## Recommendation

### Build in three tasks:

1. **Manifest + right pane + renderer fragment** — Update `manifest.yaml` with rightPane contribution, objectRenderers declaration, and "Mark All as Read" command palette entry. Create two new fragment endpoints: `related-articles` (right pane) and `article-read-renderer` (object renderer). Create corresponding templates.

2. **Navigate action fix** — Fix the `_loadAppCommandEntries()` JS handler and the `commands_list` API to handle "Open RSS Reader" correctly (open as dockview tab, not full page navigate). This is a platform-side fix that benefits all apps.

3. **Unit tests** — Tests for the two new fragment handlers, manifest changes, and the navigate action fix.

## Implementation Landscape

### Key Files

**Manifest (modify):**
- `apps/rss-reader/manifest.yaml` — Add `rightPane` contribution (related-articles), `objectRenderers` (Article read mode), and `commandPalette` entry for mark-all-read. The "open-reader" entry's `navigate` action already works via the JS fix.

**App backend (modify):**
- `apps/rss-reader/app.py` — Add two new fragment routes: `/_fragments/related-articles` and `/_fragments/article-read-renderer`. Both follow S03's SPARQL-query → template-render pattern.

**App templates (create):**
- `apps/rss-reader/frontend/templates/related-articles.html` — Right pane fragment showing articles related to the focused object (articles that share tags or link to the same concepts).
- `apps/rss-reader/frontend/templates/article-read-renderer.html` — Custom renderer for Article objects in the object browser. Reuses the reading pane layout from `article-reading-pane.html` but without the fire-and-forget mark-read trigger.

**Platform JS (modify):**
- `frontend/static/js/workspace.js` — Fix `_loadAppCommandEntries()` to call `openAppPageTab()` for navigate commands that target app pages instead of `window.location.href`.

**Platform API (modify):**
- `backend/app/browser/apps.py` — Enhance `commands_list` endpoint to include `appId` and `pageId` fields for navigate commands whose path matches an app page. This allows the JS handler to dispatch correctly.

**Tests (create/modify):**
- `backend/tests/test_rss_reader_ui.py` — Add tests for the two new fragment handlers.
- `backend/tests/test_app_views_commands.py` — Add test for navigate command JSON structure with appId/pageId.

### What's already done (S03 provides)

The views that appear in the workspace sidebar (`unread-articles`, `starred-articles`) are **already declared** in the manifest and **already have fragment endpoints and templates** from S03. They will appear automatically in the App Views explorer group because `views_explorer.html` lazy-loads from `GET /browser/apps/views/explorer`, which reads `manifest.ui.contributions.views`. **No work needed for views**.

Similarly, `subscribe-feed` and `open-reader` command palette entries are **already declared** in the manifest. They are surfaced via `GET /api/apps/commands` → `_loadAppCommandEntries()`. The subscribe-dialog fragment exists from S02. **Only mark-all-read needs to be added to the manifest**.

### Manifest changes needed

Current `ui.contributions` has `views` and `commandPalette`. Must add:

```yaml
ui:
  contributions:
    rightPane:
      - id: "related-articles"
        label: "Related Articles"
        icon: "newspaper"
        fragment: "related-articles"
        targetTypes:
          - "*"
        priority: 60
    commandPalette:
      # Existing: subscribe-feed, open-reader
      - id: "mark-all-read"
        label: "Mark All as Read"
        keywords: ["rss", "mark", "read", "unread"]
        actionType: "post"
        endpoint: "/_fragments/mark-all-read"
  objectRenderers:
    - type: "urn:sempkm:model:rss-feeds:Article"
      modes:
        read: "article-read-renderer"
```

### Related Articles right pane fragment

The right pane fragment receives `?iri=<encoded_iri>` as query param. It should query articles that share concepts/tags with the focused object, or articles from the same feed if the focused object is an Article. SPARQL pattern:

```sparql
# Find articles that share tags or are from the same feed source
SELECT ?article ?title ?created WHERE {
    ?article a <urn:sempkm:model:rss-feeds:Article> .
    ?article <http://purl.org/dc/terms/title> ?title .
    OPTIONAL { ?article <http://purl.org/dc/terms/created> ?created }
    {
        # Same feed source
        <{focused_iri}> <urn:sempkm:model:rss-feeds:feedSource> ?feed .
        ?article <urn:sempkm:model:rss-feeds:feedSource> ?feed .
    } UNION {
        # Shared tags
        <{focused_iri}> <urn:sempkm:model:basic-pkm:tags> ?tag .
        ?article <urn:sempkm:model:basic-pkm:tags> ?tag .
    }
    FILTER(?article != <{focused_iri}>)
} ORDER BY DESC(?created) LIMIT 10
```

### Article read renderer fragment

The custom renderer replaces the default SHACL form when opening an `rss:Article` from the object browser. The platform dispatches to it via `object_tab_app.html` when `_get_renderer_override()` finds a match. The fragment endpoint pattern follows the test-app's `read-renderer` — receives `?iri=<iri>` and returns the rendered HTML.

The renderer should reuse the reading pane SPARQL query and template structure from S03's `article-reading-pane.html`, but:
- No fire-and-forget mark-read trigger (that's reader-specific)
- Include the star button
- Use `data-md-source`/`data-md-target` for markdown rendering (same as reading pane)
- The platform's `object_tab_app.html` provides the toolbar (label, type badge, favorite, edit toggle) — the fragment only needs the article content area

### Navigate action fix

Current behavior in `workspace.js`:
```javascript
} else if (cmd.actionType === 'navigate') {
    window.location.href = cmd.actionUrl;
}
```

For "Open RSS Reader" with `path: /reader`, this navigates away from the workspace SPA. The fix:

1. In `commands_list()` API (`backend/app/browser/apps.py`): when `actionType == "navigate"`, check if the path matches an app page. If so, include `appId` and `pageId` in the JSON response.

2. In `_loadAppCommandEntries()` JS: when `actionType === 'navigate'` and `cmd.appId` exists, call `openAppPageTab(cmd.appId, cmd.pageId, cmd.title)` instead of `window.location.href`.

The API change: for navigate actions, `commands_list()` can match the path against `manifest.ui.pages[].path` to find the corresponding `appId` and `pageId`. If matched, include them in the JSON entry alongside `actionUrl`.

### Build Order

1. **Manifest + fragments + templates first** — These are the core deliverables. All patterns are established. Fragment handlers follow S03's `_sparql_bool()`, `_format_date()`, `ctx.graph.query()` → `ctx.render_template()` pipeline.

2. **Navigate fix second** — Small platform-side fix. Only the JS handler and API need changes.

3. **Tests last** — All code is synchronous template logic testable with mocked SDK context using S03's `_make_mock_request()` pattern.

### Verification Approach

- `cd backend && .venv/bin/python -m pytest tests/test_rss_reader_ui.py -v` — all tests pass (S03's 43 + new S04 tests)
- `cd backend && .venv/bin/python -m pytest tests/test_app_views_commands.py -v` — all tests pass (existing + new navigate fix test)
- `ast.parse` on modified `app.py` — syntax OK
- Manifest YAML is valid (existing manifest tests cover schema validation)
- `objectRenderers[0].type` is the full IRI `urn:sempkm:model:rss-feeds:Article` (per D165)
- Related articles template renders with proper `data-article-iri` attributes for testability
- Article read renderer template uses `data-md-source`/`data-md-target` for markdown rendering

## Constraints

- **objectRenderers type must be full IRI** (D165): `urn:sempkm:model:rss-feeds:Article`, not `rss:Article`. Registry does exact string comparison.
- **Right pane fragment receives `?iri=<encoded_iri>`**: The IRI is URL-encoded by the platform template (`right_pane_sections.html`). The fragment handler must `unquote()` or handle URL-encoded IRIs.
- **Right pane `hx-trigger="toggle once"`**: The platform only loads right pane app sections when the `<details>` is toggled open, and only once. The fragment must return complete HTML.
- **Command palette `post` action sends POST to endpoint**: The `mark-all-read` route already handles POST at `/_fragments/mark-all-read`. The command palette will POST to `/app/rss-reader/_fragments/mark-all-read` (proxied via AppProxy). The response renders into `#modal-container`.
- **Mark-all-read via command palette targets `#modal-container`**: The current mark-all-read handler returns updated feed-sidebar HTML, which won't render correctly in the modal container. Need to return a success/confirmation message instead when called from command palette context (detect via Accept header or query param).

## Common Pitfalls

- **Mark-all-read response mismatch** — The existing `mark_all_read_route()` returns feed sidebar HTML for the reader UI. When triggered from the command palette, the response goes into `#modal-container`. Should detect the context (e.g., check for `HX-Target` header) and return an appropriate confirmation message instead. Alternatively, the route could always return a short success message with `HX-Trigger: feedsChanged, articleStateChanged` headers, and the reader UI refreshes via those triggers.

- **Right pane SPARQL for non-Article objects** — The related articles query assumes the focused object might share tags or be an article itself. For non-Article objects (e.g., a Concept), the "same feed" UNION branch will return nothing, which is fine. The "shared tags" branch will find articles with the same tags, which is the desired behavior. For objects with no tags, the result will be empty — render an empty state.

- **Import fallback in app.py** — S02 established the `try/except ImportError` pattern for importing from `services.feed_service`. If S04 adds no new service imports, no changes needed. The new fragment handlers only use existing functions (`_sparql_bool`, `_format_date`, `_sparql_int`) already defined in `app.py`.

## Sources

- `backend/app/browser/apps.py` — Platform endpoints for right pane sections, views explorer, app view tabs, command palette API
- `backend/app/browser/objects.py` — `_get_renderer_override()` dispatches to app renderer fragments
- `backend/app/apps/registry.py` — `get_renderer()` matches type IRI against manifest objectRenderers
- `backend/app/templates/browser/object_tab_app.html` — App renderer tab template (toolbar + flip container + htmx fragment load)
- `backend/app/templates/browser/right_pane_sections.html` — Platform + app right pane sections template
- `apps/test-app/manifest.yaml` — Reference manifest with all contribution types including objectRenderers
- `apps/test-app/app.py` — Reference renderer fragment handler (`read_renderer_fragment`)
- `apps/rss-reader/app.py` — Current S03 fragment handlers (patterns to follow)
- `frontend/static/js/workspace.js` — `_loadAppCommandEntries()`, `openAppPageTab()`, `openAppViewTab()`
