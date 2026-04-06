# M051 Research: Workspace UX Improvements

## Summary

M051 is a collection of workspace-level paper-cut fixes. Each issue is small, well-contained, and touches specific files. The codebase already has most of the infrastructure needed — patterns for popover positioning, tree-leaf hover actions, lazy-loaded bottom panels, and dockview tab rendering. The work is primarily frontend (JS + CSS + templates) with one small backend change.

## Issue-by-Issue Analysis

### #10 — Event Log Panel Placeholder

**Status:** 90% already implemented. The lazy-load mechanism exists.

- `workspace.html:183` has a static placeholder: `Event Log Explorer — coming in Phase 16`
- `workspace.js:530` already has a lazy-load handler that replaces `.panel-placeholder` with htmx content from `/browser/events` when the "event-log" tab is clicked
- The `/browser/events` endpoint exists, `event_log.html` template is fully built
- **Fix:** Replace the static placeholder text with a loading spinner + "Loading event log..." so the UX communicates that it's a lazy-load state, not a "not built yet" state. Or simply load it eagerly via `hx-trigger="load"` since this is the default active tab.
- **Risk:** Trivial.

### #11 — Strip " Shape" Suffix from Explorer Type Names

**Status:** Partially implemented client-side, needs backend fix.

- `workspace.js:2094` already strips `" Shape"` for command palette entries
- `nav_tree.html:22` renders `{{ type.label }}` raw — no stripping
- `shapes.py:556` `get_types()` returns `form.label` which comes from `sh:name > rdfs:label > local_name`
- Most SHACL shapes have `sh:name "Project Shape"`, `sh:name "Task Shape"`, etc.
- **Fix:** Strip `" Shape"` suffix in `get_types()` before returning. This fixes both the explorer tree AND the type picker dropdown. The workspace.js client-side strip becomes redundant but harmless.
- **Alternative:** Strip in the template with `{{ type.label | replace(' Shape', '') }}` — less clean, doesn't fix other consumers.
- **Risk:** Low. One-line Python change. Verify no downstream code depends on the " Shape" suffix.

### #12 — Clean Up OBJECTS Dropdown

**Status:** The dropdown works but may show stale/broken VFS mount entries.

- `workspace.html:48-58` defines the static options: "By Type", "Hierarchy", "By Tag"
- `workspace.js:2987` dynamically appends VFS mounts as options via `/api/vfs/mounts`
- "Human-readable model names" likely means the mount labels should use the model's `name` field, not internal IDs
- "Remove broken VFS Mounts entry" may mean mounts whose source model is uninstalled still appear
- **Fix:** Filter mounts in `initExplorerMountOptions()` to exclude mounts that fail to load. Or add server-side validation.
- **Risk:** Low. Need to test with actual mount configurations.

### #24 — Command Palette Scroll Jump

**Status:** Not yet addressed. ninja-keys shadow DOM is the challenge.

- ninja-keys is a web component using shadow DOM
- The scroll jump likely occurs because the palette's internal list scrolls or the page itself scrolls when arrow-key navigating items
- ninja-keys may dispatch `scrollIntoView()` on highlighted items, which bubbles up to the page
- **Fix options:** 
  1. CSS `overscroll-behavior: contain` on the ninja-keys element or its shadow root
  2. Patch the `opened` attribute handling to set `document.body.style.overflow = 'hidden'` while open
  3. If the issue is within the shadow DOM list, inject CSS via `adoptedStyleSheets` or `::part()` selectors
- **Risk:** Medium. Shadow DOM makes debugging and CSS injection harder. May need to inspect ninja-keys source to find the right approach.

### #25 — Autocomplete Dismiss on Click-Outside / Escape

**Status:** Not implemented. Critical UX gap.

- Two autocomplete types: reference fields (`.reference-field`) and tag fields (`.tag-autocomplete-field`)
- Both use `.suggestions-dropdown` positioned `absolute` within `position: relative` parent
- Suggestions appear via htmx `hx-trigger="input changed delay:300ms"` → server → response fills dropdown
- Selection clears dropdown via `innerHTML = ''`
- **No click-outside handler exists** — once suggestions appear, they stay until you select one or change the input
- **No Escape key handler exists**
- **Fix:** Add a document-level click listener that clears all `.suggestions-dropdown` elements when clicking outside. Add an Escape keydown listener on the input fields. Best place: `object_form.html` inline script (runs after form loads) or a shared function in workspace.js.
- **Risk:** Low-medium. Must not conflict with other document click handlers (panel drag-drop, tree selection). Use `event.target.closest('.reference-field, .tag-autocomplete-field')` to check if click was inside.

### #26 — Tag Dropdown Escapes Container Boundary

**Status:** Not implemented. Related to #25.

- `.suggestions-dropdown` uses `position: absolute; z-index: 9999` within a `position: relative` parent
- If the form is inside a dockview panel with `overflow: hidden`, the dropdown gets clipped
- The same pattern that breaks dockview popovers (KNOWLEDGE entry: "Popovers inside dockview panels must escape stacking context via document.body")
- **Fix:** Append the dropdown to `document.body` with `position: fixed`, calculate position from `getBoundingClientRect()`, and add cleanup to remove from body when closed.
- **Risk:** Medium. This is a proven pattern (graph popovers, builder autocomplete), but requires wiring into the htmx lifecycle since suggestions are loaded via htmx. May need to intercept `htmx:afterSwap` to relocate content from the inline div to the body-appended div.

### #33/#34 — Persona Create / Layout Save UX

**Status:** Both use the same antipattern.

- "Persona: Create New" and "Layout: Save" both extract the name from ninja-keys' shadow DOM search input
- The UX is: type a name in the search field → select "Type a persona name above..." item → handler extracts `shadowRoot.querySelector('input[type="text"]').value`
- This is confusing and fragile (depends on ninja-keys internals)
- **Fix:** Replace with a proper `<dialog>` prompt. When "Persona: Create New" is selected, close the command palette and show a native dialog with a text input + Create/Cancel buttons. Same pattern for "Layout: Save".
- Existing pattern: `showConfirmDialog()` in workspace.js already creates `<dialog>` elements — extend it to support input fields.
- **Risk:** Low. The persona/layout API is simple (POST with name). The dialog is straightforward.

### #35 — Persona vs Layout Clarification

**Status:** Conceptual decision needed.

- Personas: server-stored, include workspace state (open tabs, dockview layout, sidebar positions, explorer mode, right pane visibility). API at `/api/personas`.
- Layouts: localStorage-only, include only dockview panel arrangement (no tabs, no sidebar state). `named-layouts.js`.
- They overlap significantly. A persona "saves layout" and a layout "saves arrangement" — confusing.
- **Options:**
  1. **Merge:** Make "Workspaces" that combine both. Drop layouts, enhance personas to be the only concept. Migrate localStorage layouts to server-side.
  2. **Clarify:** Keep both, rename — "Persona" → "Workspace Profile", "Layout" → "Panel Arrangement". Add help text.
  3. **Minimal:** Just improve labels and tooltips in the command palette.
- Context file leans toward merge. This is scope-dependent — the minimal approach fits M051, full merge is a larger effort.
- **Recommendation:** For M051, take option 3 (minimal) — improve labels, add help text, fix the "type above" UX. Defer the merge question to a future milestone.
- **Risk:** Low for minimal approach.

### #42 — Model Detail Graph Popover Positioning

**Status:** Popover exists but positions incorrectly.

- `model_ontology_diagram.html:175-232` handles hover popover positioning
- Uses `evt.renderedPosition` from Cytoscape which gives pixel coords in the canvas viewport
- Position calculation: `(containerRect.left - panelRect.left) + pos.x + 16`
- The issue is likely that when the graph is zoomed/panned, `renderedPosition` is in the zoomed/panned coordinate space but the offset calculation assumes 1:1 mapping
- **Fix:** Use `cy.zoom()` and `cy.pan()` to convert from model to rendered coordinates, or use `evt.renderedPosition` correctly (it's already in rendered coords). More likely: the `.ontology-diagram-panel` has a scroll offset or padding that isn't accounted for. Debug by logging actual positions.
- **Risk:** Low-medium. Requires testing with the actual UI.

### #65 — Refresh Button on Object Tab

**Status:** Not implemented.

- Object tabs use dockview's custom tab renderer in `workspace-layout.js:42-100`
- Tab structure: `iconWrap + content (title) + action (close button)`
- The tab content is loaded via htmx: `htmx.ajax('GET', '/browser/object/' + iri, {target: el, swap: 'innerHTML'})`
- **Fix options:**
  1. Add a refresh button to the tab header (next to close button) — requires modifying `createTabComponentFn`
  2. Add a refresh button in the object tab content (toolbar area) — simpler, doesn't touch dockview tab rendering
  3. Add a keyboard shortcut (Ctrl+R or F5) that reloads the active panel
- Option 2 is simplest and consistent with how the "star" (favorite) button works inside the tab content.
- **Risk:** Low. The htmx reload pattern is well-established.

## Codebase Constraints

1. **ninja-keys shadow DOM:** Issues #24 and #33/#34 both involve ninja-keys internals. The component's shadow DOM limits CSS customization and JS access. `customElements.whenDefined('n-keys')` is used for initialization. The wrapper in workspace.js already patches `.open()` and `.close()` to manage an `opened` attribute.

2. **htmx suggestion lifecycle:** Autocomplete suggestions (#25, #26) are loaded via htmx, which means the DOM is swapped by htmx after fetch completion. Any click-outside/escape handler must either live above the htmx lifecycle or be re-attached after each swap.

3. **Dockview stacking context:** Tag dropdown escape (#26) faces the known dockview popover issue. The body-append pattern from graph.js popovers should be reused.

4. **No existing E2E tests** for autocomplete dismiss, persona creation dialog, or refresh button. New tests will be needed.

5. **The minified workspace bundle** includes workspace.js changes — dev mode uses volume-mounted source files, so no rebuild is needed for development/testing.

## Existing Patterns to Reuse

| Pattern | Source | Applicable To |
|---------|--------|---------------|
| Body-append popover | `graph.js`, `model_ontology_diagram.html` | #26 tag dropdown escape |
| `showConfirmDialog()` | `workspace.js` | #33/#34 persona/layout dialog |
| `.tree-leaf-action` hover CSS | `workspace.css:8878` | #12 explorer hover actions (already exists) |
| htmx lazy-load panel | `workspace.js:530` event log handler | #10 event log (already exists) |
| `apiFetch()` | `api-fetch.js` | All new API calls |
| `registerCleanup()` | `cleanup.js` | Cleanup for body-appended dropdowns |

## Slice Strategy Recommendations

### Prove first: #25 Autocomplete Dismiss

This is the highest-risk UX fix because it needs document-level event listeners that must coexist with the existing click handling (tree selection, panel drag-drop, dockview). Getting this right unlocks #26 (same dismiss mechanism for body-appended dropdowns).

### Natural boundaries:

1. **Autocomplete fixes (#25 + #26)** — Tightly coupled. Click-outside dismiss mechanism is shared. Tag dropdown body-escape builds on the dismiss handler.
2. **Explorer/nav cleanup (#10, #11, #12)** — All touch the explorer sidebar. Backend label fix, dropdown cleanup, placeholder replacement.
3. **Command palette & dialog UX (#24, #33, #34, #35)** — All involve ninja-keys or its replacement UX. Persona and layout creation share the same antipattern.
4. **Object tab features (#65)** — Standalone. Refresh button in tab content.
5. **Admin graph popover (#42)** — Standalone, admin-only page, no interaction with workspace code.

### Order by risk:
1. Autocomplete dismiss (#25 + #26) — highest interaction risk
2. Explorer cleanup (#10, #11, #12) — moderate, touches backend + frontend
3. Persona/Layout dialog (#33, #34, #35) — moderate, ninja-keys shadow DOM
4. Command palette scroll (#24) — medium, shadow DOM debugging
5. Refresh button (#65) — low risk
6. Graph popover (#42) — low risk, isolated

## Requirements Analysis

No active requirements are directly addressed by M051. These are UX polish items. Candidate requirements:

- **Autocomplete dismiss** could become a non-functional requirement: "All dropdown/autocomplete elements must dismiss on Escape and click-outside." This is a standard web UX expectation.
- **Explorer hover actions** and **refresh button** are functional requirements but small enough to be task-level, not requirement-level.

No existing requirements are at risk of regression from this work.

## Technology Notes

- **ninja-keys:** Web component with shadow DOM. No external docs needed — the codebase already uses it extensively. The shadow DOM limitation is well-understood.
- **Cytoscape.js:** Used for the ontology diagram. Popover positioning with zoom/pan is a known complexity. The existing code already handles most edge cases.
- No new libraries or technologies needed. All fixes use existing patterns.

## Skills

No specialized skills needed. The work is vanilla JS/CSS/HTML with htmx patterns. The `frontend-design` skill could be relevant for the dialog UI (#33/#34) but the existing `showConfirmDialog()` pattern is sufficient.
