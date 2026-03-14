# S02: Delete + Instance Warnings — Research

**Date:** 2026-03-14

## Summary

S02 adds delete capability for both user-created classes and properties, with instance-count warnings before class deletion, confirmation dialogs that communicate impact, and clean removal from TBox/RBox views.

The codebase already has a working `delete_class` service method and `DELETE /ontology/delete-class` route — but with no instance count check and only a static `hx-confirm` message. The RBox has no delete capability for properties at all. This slice needs to: (1) add `delete_property()` to `OntologyService`, (2) add a delete-property route, (3) enhance class deletion with instance/subclass count checks and a richer confirmation flow, (4) add delete buttons for user-created properties in the RBox, and (5) ensure TBox/RBox refresh automatically after deletions.

The biggest risk is the confirmation UX — the current `hx-confirm` pattern uses browser-native `window.confirm()` which cannot show dynamic instance counts. We need either a custom htmx confirmation flow or a two-step endpoint (check → confirm → delete).

## Recommendation

Use a **two-step pre-delete check** pattern:

1. **Check endpoint** (`GET /ontology/delete-class-check?class_iri=...`) returns an HTML confirmation fragment with instance count, subclass count, and warning text. Rendered into the existing `class-edit-overlay` modal (repurposed as a generic ontology action modal) or a new dedicated confirm overlay.
2. **Delete endpoint** (existing `DELETE /ontology/delete-class`) performs the actual deletion. Called from a "Confirm Delete" button inside the rendered confirmation fragment.

This follows the existing modal pattern (class creation/edit forms are loaded via htmx into overlays) and avoids fighting `hx-confirm`'s limitations for dynamic content. For property deletion, the same pattern applies but simpler — properties have no instances, so a simple `hx-confirm` is sufficient.

Replace the current `hx-confirm` on TBox delete buttons with an `onclick` handler that fetches the check endpoint into a confirmation modal.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| TBox/RBox auto-refresh after delete | HX-Trigger headers (`classDeleted`, `propertyDeleted`) | Already wired — TBox tree has `hx-trigger="classDeleted from:body"`, RBox has `hx-trigger="propertyCreated from:body"` (add `propertyDeleted`) |
| Instance count query | `get_class_detail()` inst_sparql pattern | Same SPARQL shape — query default graph for `?inst a <class_iri>` |
| Subclass count query | `get_class_detail()` sub_sparql pattern | Same SPARQL shape — query ontology graphs for `?sub rdfs:subClassOf <class_iri>` |
| Delete class triples | `_build_delete_class_sparql()` + `_build_delete_shape_sparql()` | Already working, tested in `test_class_creation.py` |
| Modal overlay pattern | `class-edit-overlay` / `class-creation-overlay` in `ontology_page.html` | Same structure: overlay div + inner container populated via htmx |
| Icon cache cleanup | `_remove_from_icon_cache()` | Already called in delete_class route |

## Existing Code and Patterns

- `backend/app/ontology/service.py` — `delete_class()` exists but does no pre-delete checks. `_build_delete_class_sparql()` and `_build_delete_shape_sparql()` are the SPARQL builders. Need to add `delete_property()` (simple `DELETE WHERE` on property IRI in user-types graph) and `get_delete_class_info()` (instance + subclass counts).
- `backend/app/ontology/router.py` — `DELETE /ontology/delete-class` exists, needs a companion `GET /ontology/delete-class-check` route. Add `DELETE /ontology/delete-property` route. Both routes guard on `USER_TYPES_GRAPH:` prefix.
- `backend/app/templates/browser/ontology/tbox_tree.html` + `tbox_children.html` — Both have delete buttons with `hx-delete` and `hx-confirm`. Replace `hx-confirm`/`hx-delete` with `onclick` calling a JS function that opens a confirmation modal via htmx.
- `backend/app/templates/browser/ontology/rbox_legend.html` — Groups properties by source via `groupby('source')`. User properties have `source='sempkm'` (from `_property_source`). Need to add delete buttons for rows where `source == 'sempkm'` (or better, check `'user-types' in p.iri`).
- `backend/app/templates/browser/ontology/ontology_page.html` — Has three overlay divs for class creation, property creation, and class edit. Add a fourth for delete confirmation, or reuse the class-edit overlay.
- `frontend/static/css/workspace.css` — `.tbox-edit-btn` / `.tbox-delete-btn` CSS exists. Need similar styles for RBox delete buttons (`.rbox-delete-btn`).
- `backend/tests/test_class_creation.py` — `TestDeleteClass` and `TestDeleteClassEndpoint` exist. Add tests for `delete_property()`, `get_delete_class_info()`, and the check endpoint.
- `backend/tests/test_ontology_service.py` — Service-level unit tests with mock `TriplestoreClient`. Follow same `AsyncMock` pattern.
- `_property_source()` — Returns `'sempkm'` for user-types IRIs (not `'user'`). The TBox tree template uses `'user-types' in cls.iri` for source detection instead. RBox template groups by `source` field. Either fix `_property_source()` to return `'user'` for user-types IRIs, or use IRI substring check in the RBox template.

## Constraints

- **User-types namespace guard:** Only classes/properties with IRI prefix `urn:sempkm:user-types:` can be deleted. This is enforced in the route handler, not the service layer. Maintain this pattern.
- **No EventStore for schema ops:** Class/property deletion uses direct `DELETE WHERE` against `urn:sempkm:user-types` graph (D060, D062). No event sourcing.
- **Two separate SPARQL calls for shape deletion:** RDF4J rejects `OPTIONAL` inside `DELETE WHERE` (D064). The existing `_build_delete_shape_sparql()` returns a tuple of two queries executed sequentially.
- **Property deletion is simpler than class deletion:** Properties are just OWL triples (type, label, domain, range, comment) — no SHACL shapes, no blank nodes, no instances to warn about. A single `DELETE WHERE { GRAPH <user-types> { <prop_iri> ?p ?o . } }` suffices.
- **`_property_source` returns `'sempkm'` not `'user'`** for user-type IRIs. The RBox template uses this for grouping. Either update the function to return `'user'` for `urn:sempkm:user-types:` IRIs, or handle the badge display and delete-button logic with an IRI check.
- **htmx hx-trigger on RBox:** Currently `hx-trigger="propertyCreated from:body"`. Must add `propertyDeleted` to this trigger list for auto-refresh after property deletion.
- **Rate-limiting E2E tests:** Ontology viewer E2E test (3 tests) already uses auth. Adding delete tests may need to share auth sessions within test cases to stay under rate limits.

## Common Pitfalls

- **`hx-confirm` cannot show dynamic content** — The static string `"Delete this class? Objects of this type will lose their type."` cannot include instance counts. Must replace with a programmatic flow (fetch check endpoint → render modal → confirm button triggers delete). Don't try to dynamically update `hx-confirm` attributes via JS — htmx reads the attribute at click time but it's still a plain `window.confirm()`.
- **RBox doesn't re-render on `propertyDeleted`** — The RBox pane's `hx-trigger` currently only has `propertyCreated from:body`. If you add the delete endpoint and return `HX-Trigger: propertyDeleted` but forget to update the RBox `hx-trigger`, the table won't refresh.
- **Shape IRI derivation is fragile** — `delete_class()` derives shape IRI from class IRI by inserting "Shape" before the UUID suffix. This convention works for classes created by `create_class()` but would break for manually created shapes. Not a problem for S02 scope (only user-created classes via UI) but worth noting.
- **Lucide icons need re-init after htmx swap** — Any htmx-loaded content with `<i data-lucide="...">` needs `lucide.createIcons()` called after swap. The RBox content is already htmx-loaded; if delete buttons use Lucide icons, ensure the `afterSwap` hook or inline script handles re-init.
- **Property deletion doesn't cascade to SHACL shapes** — If a property is used in a SHACL shape (as `sh:path`), deleting the property definition doesn't remove it from shapes. This is acceptable for S02 — the property disappears from the RBox but shapes that reference it continue to work (the IRI still exists as a path in the shape, even without a definition). Document this as a known limitation.

## Open Risks

- **Orphaned instance data on class delete:** When a class with instances is deleted, the `rdf:type` triple on each instance still points to the deleted class IRI. Instances become effectively "untyped" (their type IRI has no definition). The warning dialog should make this clear to the user. Whether to also clean up instance type triples is a UX decision — for S02, warning is sufficient; cleanup can be deferred.
- **Subclass cascade:** If a user class has subclasses (another user class extends it), deleting the parent orphans the child's `rdfs:subClassOf`. The check endpoint should warn about this. Whether to prevent deletion or cascade is a design choice — recommend warning + allowing delete (the child class becomes a root class).
- **Concurrent modifications:** No locking between the check (count instances) and delete (remove triples). A user could create an instance between check and confirm. This is acceptable for a single-user or low-concurrency system like SemPKM.
- **`_property_source` returning `'sempkm'` instead of `'user'`:** This affects how user properties are grouped in the RBox table. If we fix it to return `'user'`, the CSS class `rbox-group-badge--user` needs to be added. If we leave it as `'sempkm'`, the badge text says "sempkm" which is confusing for end users. Recommend fixing to `'user'` for IRIs starting with `urn:sempkm:user-types:`.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | `mindrally/skills@htmx` (200 installs) | available — not installed |
| FastAPI | `wshobson/agents@fastapi-templates` (6.3K installs) | available — not installed |

Neither skill is essential for this slice — the codebase patterns are well-established and the work is straightforward CRUD with existing conventions. htmx confirmation modals and FastAPI endpoints follow patterns already demonstrated throughout the codebase.

## Sources

- Existing `delete_class()` service method and route (source: `backend/app/ontology/service.py`, `backend/app/ontology/router.py`)
- Existing `hx-confirm` usage on TBox delete buttons (source: `backend/app/templates/browser/ontology/tbox_tree.html`, `tbox_children.html`)
- Instance count query pattern in `get_class_detail()` (source: `backend/app/ontology/service.py` line 820-830)
- D062, D064 decisions on delete patterns (source: `.gsd/DECISIONS.md`)
- Existing unit tests for delete (source: `backend/tests/test_class_creation.py` — `TestDeleteClass`, `TestDeleteClassEndpoint`)
- `_property_source()` source classification logic (source: `backend/app/ontology/service.py` line 106-121)
