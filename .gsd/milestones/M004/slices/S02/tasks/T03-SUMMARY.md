---
id: T03
parent: S02
milestone: M004
provides:
  - Delete confirmation modal overlay in ontology_page.html with dynamic instance/subclass counts
  - RBox delete buttons for user-created properties with hx-confirm and auto-refresh
  - TBox delete buttons rewired to use confirmation modal instead of static hx-confirm
  - CSS styles for RBox delete buttons and delete confirmation modal content
key_files:
  - backend/app/templates/browser/ontology/ontology_page.html
  - backend/app/templates/browser/ontology/tbox_tree.html
  - backend/app/templates/browser/ontology/tbox_children.html
  - backend/app/templates/browser/ontology/rbox_legend.html
  - backend/app/templates/browser/ontology/delete_class_confirm.html
  - frontend/static/css/workspace.css
key_decisions:
  - RBox property deletion uses hx-confirm (browser native dialog) since it has no instance-count complexity, while TBox class deletion uses custom confirmation modal with server-fetched counts
  - Delete confirmation modal content CSS added to workspace.css alongside RBox delete button styles
patterns_established:
  - openDeleteClassConfirm(iri) / closeDeleteConfirm() follows same open/close pattern as class-creation, property-creation, and class-edit modals
  - RBox delete button uses same hover-reveal pattern as TBox delete/edit buttons (hidden by default, display on tr:hover)
observability_surfaces:
  - "#delete-confirm-overlay" visibility state inspectable via JS (style.display)
  - RBox hx-trigger includes "propertyDeleted from:body" for auto-refresh monitoring
  - Network tab shows /ontology/delete-class-check fetch on modal open
  - HX-Trigger headers (classDeleted, propertyDeleted) confirm delete completed
duration: 35min
verification_result: passed
completed_at: 2026-03-14
blocker_discovered: false
---

# T03: Wire delete confirmation modal + RBox delete buttons in templates

**Wired TBox delete buttons to open a confirmation modal with dynamic instance/subclass counts, added delete buttons for user-created properties in RBox, and added CSS for both.**

## What Happened

Implemented all 5 steps from the plan:

1. **Delete confirmation overlay** — Added `#delete-confirm-overlay` div to `ontology_page.html` following the existing modal pattern. Added `openDeleteClassConfirm(classIri)` which fetches `/browser/ontology/delete-class-check` into the container and shows the overlay, and `closeDeleteConfirm()` to hide it. Registered in the Escape key handler array (prioritized first so it closes before other overlays).

2. **TBox delete button rewiring** — Replaced `hx-delete`/`hx-confirm` attributes on delete buttons in both `tbox_tree.html` and `tbox_children.html` with `onclick="openDeleteClassConfirm('{{ cls.iri }}')"`. Also added missing delete button for preloaded children (hide-gist mode) in `tbox_tree.html`.

3. **RBox delete buttons** — Added conditional delete button column in the `render_property_table` macro in `rbox_legend.html`. Only the "user" source group gets the Actions column header and delete buttons. Buttons use `hx-delete` with `hx-confirm` for a simple browser confirmation dialog.

4. **RBox hx-trigger update** — Changed `hx-trigger="propertyCreated from:body"` to include `propertyDeleted from:body` so the RBox auto-refreshes after a property deletion.

5. **CSS** — Added `.rbox-delete-btn` styles following the `.tbox-delete-btn` pattern (hidden by default, visible on `tr:hover`, red on hover, flex-shrink: 0 for Lucide SVG). Added `.delete-confirm-content` modal styles including warning boxes, button styles, and layout.

**Bug fix discovered during implementation:** The `delete_class_confirm.html` template from T02 had `hx-delete="/ontology/delete-class?..."` which was missing the `/browser` prefix (the ontology router is mounted under the `/browser` prefix). Fixed to `/browser/ontology/delete-class?...`. Also improved the inline `hx-on::after-request` to only close the modal on success (`if(event.detail.successful)`).

## Verification

### Unit Tests (slice-level)
- `docker compose exec api python -m pytest tests/test_class_creation.py -v -k delete` — **15 passed** (all delete-related tests)
- `docker compose exec api python -m pytest tests/test_ontology_service.py -v` — **44 passed**

### Browser Verification
- ✅ TBox delete button on user class opens confirmation modal showing "Delete 'TestDeleteMe'?" with instance/subclass counts
- ✅ Cancel button closes modal without deletion — class remains in TBox tree
- ✅ Escape key closes modal without deletion
- ✅ Confirm Delete button deletes class and TBox auto-refreshes — class disappears from tree
- ✅ RBox shows delete button (trash icon) on user-created property rows on hover
- ✅ Clicking RBox delete button triggers browser confirm dialog, then deletes property (DELETE 200) and RBox auto-refreshes
- ✅ No console errors after all operations
- ✅ Network logs confirm correct endpoints called: DELETE /browser/ontology/delete-property → 200, GET /browser/ontology/rbox → 200

## Diagnostics

- Inspect `#delete-confirm-overlay` display style to check modal state
- Check htmx `hx-trigger` on `#ontology-rbox` for `propertyDeleted` event
- Network tab shows `/browser/ontology/delete-class-check` requests when modal opens
- HX-Trigger headers (`classDeleted`, `propertyDeleted`) confirm deletion success

## Deviations

- Fixed `delete_class_confirm.html` `hx-delete` URL: was missing `/browser` prefix (would have caused 404 in production)
- Added delete button for preloaded children in `tbox_tree.html` — the pre-existing template had edit buttons but no delete buttons for child nodes in hide-gist mode
- Improved `hx-on::after-request` to only close modal on success (prevents closing on server error)

## Known Issues

- 3 pre-existing test failures in `test_class_creation.py` (TestCreateClassEndpoint tests) — caused by `description.strip()` called on a `Form` object, unrelated to this slice's changes

## Files Created/Modified

- `backend/app/templates/browser/ontology/ontology_page.html` — Added delete-confirm overlay, JS functions, Escape handler, RBox hx-trigger update
- `backend/app/templates/browser/ontology/tbox_tree.html` — Replaced hx-delete/hx-confirm with onclick for confirmation modal, added delete button for preloaded children
- `backend/app/templates/browser/ontology/tbox_children.html` — Same hx-delete/hx-confirm replacement as tbox_tree.html
- `backend/app/templates/browser/ontology/rbox_legend.html` — Added conditional Actions column and delete buttons for user source group
- `backend/app/templates/browser/ontology/delete_class_confirm.html` — Fixed /browser prefix on hx-delete URL, improved after-request handler
- `frontend/static/css/workspace.css` — Added .rbox-delete-btn styles, .delete-confirm-content modal styles
