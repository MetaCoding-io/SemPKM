# S03: Custom Section on Mental Models + Property Edit — Research

**Date:** 2026-03-14

## Summary

S03 adds two features: (1) a "Custom" section on the Mental Models admin page showing all user-created types and properties from `urn:sempkm:user-types`, and (2) an `edit_property` capability (rename, change domain/range) accessible from both the Custom section and the RBox tab. Both features follow well-established patterns in the codebase — the Mental Models page already has two sections (Upper Ontology, Installed Models) with clear CSS conventions, and class editing (S01) provides the exact template for property editing.

The scope is low-risk. The service layer already has `create_property`, `delete_property`, and `get_properties()` (which returns source labels including `'user'`). The main work is: (a) a new `list_user_types()` service method to query user-created classes and properties from the user-types graph, (b) `get_property_for_edit()` + `edit_property()` service methods following the class edit pattern (delete-then-reinsert), (c) a new HTML section in `models.html` rendered from the new service method, (d) an edit property form template + route, and (e) edit buttons in the RBox table for user properties.

## Recommendation

**Approach: Thin service methods + template-driven UI, following existing patterns exactly.**

1. **`list_user_types()`** — Single SPARQL query against `FROM <urn:sempkm:user-types>` to get classes (with label, icon, color, parent label) and properties (with label, type, domain, range). Return as `{"classes": [...], "object_properties": [...], "datatype_properties": [...]}`. Reuse `_property_source` logic is unnecessary since everything in this graph is `'user'` by definition.

2. **`get_property_for_edit()`** — Query property metadata from user-types graph: label, type (ObjectProperty vs DatatypeProperty), domain IRI/label, range IRI/label, description. Same pattern as `get_class_for_edit()`.

3. **`edit_property()`** — Delete-then-reinsert pattern matching `edit_class()`. Delete all triples where `<prop_iri> ?p ?o` in user-types graph, then reinsert with `_generate_property_triples()`. Property IRI is preserved (not re-minted).

4. **Custom section in `models.html`** — New `<h3 class="section-label">Custom</h3>` section after Installed Models. Show classes as a table (name, icon, parent, property count, actions: edit/delete) and properties as a second table (name, type, domain, range, actions: edit/delete). Edit/delete buttons link to existing ontology viewer modals or trigger htmx requests.

5. **Edit property form** — New `edit_property_form.html` template following `create_property_form.html` but pre-populated. Name is editable; prop_type radio is read-only (cannot switch between object/datatype after creation since it changes the IRI semantics); domain and range use the same class-search picker.

6. **RBox edit button** — Add an edit button alongside the existing delete button in `rbox_legend.html` for user-source properties.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Property triple generation | `_generate_property_triples()` | Already generates correct OWL triples for both object and datatype properties |
| Delete-then-reinsert edit | `edit_class()` pattern | Proven pattern — delete old triples, re-insert with new values, preserve IRI |
| Class search picker | `tbox/search` endpoint + `ccf-search-results` JS | Same search picker used in create-property and edit-class forms |
| Source badge CSS | `.rbox-group-badge--user` | Already styled in workspace.css |
| Modal overlay pattern | `ccf-overlay` / `ccf-modal` | Used by class create, property create, class edit, delete confirm |
| Property type radio | `cpf-type-radios` in create_property_form | Existing radio button styling for object/datatype |

## Existing Code and Patterns

- `backend/app/ontology/service.py` — `create_property()` / `_generate_property_triples()` / `delete_property()` provide the building blocks for edit; `get_class_for_edit()` is the template for `get_property_for_edit()`
- `backend/app/ontology/router.py` — `edit_class_form()` / `edit_class()` route handlers are the pattern for `edit_property_form()` / `edit_property()` routes; namespace guard (`USER_TYPES_GRAPH:` prefix check) already standardized
- `backend/app/templates/admin/models.html` — Mental Models page with Upper Ontology card + Installed Models table; Custom section slots in after Installed Models
- `backend/app/templates/browser/ontology/create_property_form.html` — Full property form with domain/range pickers; basis for edit form (pre-populate values, make type read-only)
- `backend/app/templates/browser/ontology/rbox_legend.html` — RBox table with conditional delete button column for user source; add edit button alongside delete
- `backend/app/templates/browser/ontology/ontology_page.html` — Modal overlay system (4 modals already); add property-edit overlay
- `frontend/static/css/style.css` — `.upper-ontology-*` and `.section-label` CSS classes for admin page layout
- `frontend/static/css/workspace.css` — `.rbox-delete-btn` hover-reveal pattern for RBox action buttons; extend for edit button
- `backend/app/admin/router.py` — `admin_models()` handler passes `gist_summary` to template; extend to also pass `custom_types` from `list_user_types()`

## Constraints

- **User-types graph only** — `edit_property()` must guard against editing non-user properties (gist, model). Same `USER_TYPES_GRAPH:` prefix check as other endpoints.
- **Property type immutable** — Switching between ObjectProperty and DatatypeProperty after creation is dangerous (existing SHACL shapes may reference it with specific datatype expectations). The edit form should show the type as read-only.
- **No property IRI change** — Property IRI is preserved on edit. Only label, domain, range, and description can change. This is critical because SHACL shapes reference properties by IRI.
- **SHACL shapes NOT updated on property edit** — When a property's domain/range changes, existing SHACL shapes that reference it are NOT automatically updated. This is acceptable because SHACL shapes reference properties by IRI, and the shape's `sh:path` still points to the same IRI. Domain/range are OWL-level constraints, not SHACL-level.
- **Admin page requires owner role** — `admin_models()` already uses `require_role("owner")`. The custom section inherits this.
- **htmx trigger events for auto-refresh** — The Mental Models page doesn't use htmx triggers for auto-refresh (it's a full-page render). Edit/delete actions from the Custom section should either redirect back to the page or use htmx partials for the Custom section.

## Common Pitfalls

- **`_property_source` for edit buttons** — The RBox table already computes `source` per property. The edit button should only appear when `source == 'user'`, matching the delete button's existing conditional `{% if is_user %}`.
- **Domain/range label resolution on edit form** — When pre-populating the edit form, domain/range IRIs need human-readable labels. These may come from gist, installed models, or user-types. Use the same cross-graph label resolution as `get_class_for_edit()` (query with UNION across `skos:prefLabel` and `rdfs:label`).
- **htmx form processing for dynamically loaded modals** — Must call `htmx.process(form)` after injecting the edit form via htmx (see D063 and create_property_form.html pattern).
- **Range field toggling** — The property creation form toggles between a class picker (object) and a datatype dropdown (datatype) based on prop_type. The edit form must initialize the correct field as visible and the other as hidden, based on the property's current type.
- **Custom section data freshness** — If the user creates/edits/deletes types from the Ontology Viewer, then navigates to Mental Models, the Custom section should show current data. Since it's a full page load, this is automatic. But if we add htmx partial refresh, we need to consider cross-page event triggers (unlikely — different pages).

## Open Risks

- **Custom section empty state** — If no user-created types or properties exist, the Custom section should show an encouraging message directing users to the Ontology Viewer's Create buttons. Need to handle the zero-state gracefully.
- **Large number of user types** — If a power user creates many classes (>20), the Custom section table could get long. Not a launch concern but may need pagination later.
- **Property edit from Custom section vs RBox tab** — Both surfaces need to open the same edit form. The Custom section is on the admin page (`/admin/models`), while the RBox is in the workspace (`/browser/#ontology-viewer`). The edit form modal can't be shared across pages. Solution: Custom section edit links navigate to the Ontology Viewer with the RBox tab active, OR render the edit form inline/modal on the admin page itself. Recommend: Custom section provides simple edit/delete actions directly (htmx modal on the admin page), while RBox provides edit buttons that open the ontology page's modal.

## Architecture: Custom Section Rendering

Two options:

**Option A: Server-rendered in admin_models()** — Extend `admin_models()` to call `ontology_service.list_user_types()` and pass the result to `models.html`. The template renders the Custom section. Edit/delete actions are htmx calls that return updated partial HTML. Simplest approach, consistent with how the page works today.

**Option B: htmx lazy-load Custom section** — Add `hx-get="/admin/models/custom"` on a placeholder div that loads the Custom section asynchronously. Avoids slowing down initial page load if the SPARQL query is slow. More complex.

**Recommendation: Option A.** The `list_user_types()` query is against a single small graph (user-types). It will be fast (<100ms). Adding htmx lazy-load is unnecessary complexity.

## Architecture: Edit Property Location

The edit property form needs to be accessible from both:
1. The Custom section on the Mental Models page
2. The RBox tab in the Ontology Viewer

**Approach:** Create a single `edit_property_form.html` template and `GET /ontology/edit-property-form` + `POST /ontology/edit-property` routes (under the browser/ontology router). Both pages can use these endpoints — the admin page can open a modal overlay with htmx fetching the form, and the ontology page can add a property-edit overlay similar to the class-edit overlay.

This keeps the form template DRY and the routes centralized in the ontology router.

## Task Breakdown Estimate

1. **Service methods** — `list_user_types()`, `get_property_for_edit()`, `edit_property()` + unit tests (~45 min)
2. **Routes** — `GET /ontology/edit-property-form`, `POST /ontology/edit-property` + route tests (~20 min)
3. **Custom section template** — New section in `models.html` with classes table, properties table, edit/delete buttons, empty state (~30 min)
4. **Edit property form template** — `edit_property_form.html` based on create_property_form (~25 min)
5. **RBox + Ontology page edit button wiring** — Edit button in rbox_legend, modal overlay in ontology_page, CSS (~20 min)
6. **Admin router integration** — Call `list_user_types()` in `admin_models()`, pass to template (~10 min)
7. **Browser verification** — Full round-trip testing of create → edit → verify → delete property flow (~20 min)

**Total estimate:** ~3 hours across 4-5 tasks

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | `mindrally/skills@htmx` (200 installs) | available — not installed (low priority, patterns already well-established in codebase) |
| SPARQL/RDF | `letta-ai/skills@sparql-university` (37 installs) | available — not installed (low install count, codebase has comprehensive SPARQL patterns) |
| Frontend design | `frontend-design` | installed — available if needed for CSS polish |

## Sources

- Existing `edit_class()` / `get_class_for_edit()` pattern in `service.py` (lines 1757-1938)
- Existing `create_property_form.html` template for form structure
- Existing `rbox_legend.html` macro with conditional user-source actions column
- S02 T01/T02/T03 summaries for delete button patterns and modal wiring
- D070 (two-step delete confirmation) and D072 (property delete uses simple hx-confirm) decisions
