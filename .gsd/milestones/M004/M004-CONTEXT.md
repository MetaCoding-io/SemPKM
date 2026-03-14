# M004 Context: Ontology & Type System Completion

## Theme

Round out the in-app type authoring story. M003 shipped class creation — M004 adds property creation, edit/delete for types and properties, a "Custom" section on Mental Models for managing user-created types, and fixes the create-new-object tab behavior.

## Source Queue Items

1. **In-App Relationship (Property) Creation** — "+ Create Property" on RBox tab
2. **Full CRUD for Custom Types & Relationships** — Edit, delete, manage user-created classes/properties
3. **"Custom" section on Mental Models page** — Three-tier: Upper Ontology → Installed Models → Custom
4. **"Create New Object" opens in new tab** — Bug: currently overwrites active tab

## Existing Code Surface

- `backend/app/ontology/service.py` — `OntologyService` with `create_class()`, `delete_class()`, `get_class_detail()`, TBox/RBox queries
- `backend/app/ontology/router.py` — `/browser/ontology/*` routes, `POST /browser/ontology/create-class`
- `backend/app/templates/browser/ontology/` — `ontology_page.html`, `create_class_form.html`, `tbox_tree.html`, `rbox_legend.html`
- `frontend/static/js/workspace.js` — `openTab()`, `handleTreeLeafClick()`, ontology viewer handlers
- `frontend/static/css/workspace.css` — `.ccf-*` modal classes, `.tbox-*` tree classes, `.rbox-*` table classes
- `backend/app/admin/router.py` — `/admin/models` and `/admin/models/{model_id}` routes
- `backend/app/templates/admin/models.html` — Mental Models page with gist card + installed models table
- Named graphs: `urn:sempkm:user-types` (user classes/properties), `urn:sempkm:ontology:gist` (gist), `urn:sempkm:ontology:{model}` (installed models)

## Key Constraints

- All CRUD operations on `urn:sempkm:user-types` graph — direct INSERT DATA / DELETE DATA (not EventStore)
- SHACL shapes must be updated when editing class properties
- Delete must warn if instances exist (query default graph for instance count)
- Property creation generates OWL ObjectProperty or DatatypeProperty triples + optional domain/range
- Mental Models page must not break existing gist card or installed models table
- Create-new-object fix must preserve dockview tab state management
