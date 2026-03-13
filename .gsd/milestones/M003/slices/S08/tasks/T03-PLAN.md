---
estimated_steps: 5
estimated_files: 6
---

# T03: Class creation form UI with icon picker and property editor

**Slice:** S08 — In-App Class Creation
**Milestone:** M003

## Description

Build the user-facing form for creating a new class. The form lives in the ontology viewer, accessed via a "Create Class" button in the TBox tab header. It includes: text input for class name, a searchable icon picker with curated Lucide icons, a parent class selector that searches the TBox hierarchy, and a dynamic property editor where users add/remove property definitions (name, predicate, datatype).

## Steps

1. **Create `create_class_form.html` template** in `backend/app/templates/browser/ontology/`:
   - Form with `hx-post="/browser/ontology/create-class"` and `hx-swap="innerHTML"` targeting a result container
   - **Name field**: text input with `name="name"`, required
   - **Icon picker**: Grid of ~40 curated Lucide icon buttons (the most commonly useful: file-text, book, lightbulb, user, calendar, tag, folder, star, heart, globe, code, database, layers, map, music, image, video, link, mail, phone, home, briefcase, shopping-cart, clock, bell, flag, bookmark, award, zap, compass, cpu, feather, gift, key, lock, settings, shield, target, tool, truck). Each is a clickable cell that sets a hidden `icon` input. Selected icon gets a visual highlight. Include a text search filter to narrow the grid.
   - **Icon color**: Simple color picker (dropdown or input) with preset options (CSS variable tokens from the theme)
   - **Parent class selector**: Text input with `hx-get="/browser/ontology/tbox/search?q={query}"` for search-as-you-type. Results render as a dropdown of class labels with IRIs. Hidden input `parent_iri` stores the selected IRI. Default to owl:Thing if no parent selected.
   - **Property editor**: Dynamic list of property rows. Each row has: property name (text input), predicate selector (dropdown of common predicates: dcterms:title, dcterms:description, dcterms:date, schema:name, schema:url, schema:startDate, schema:endDate, foaf:name, skos:note + custom IRI input), datatype selector (dropdown: xsd:string, xsd:integer, xsd:decimal, xsd:boolean, xsd:date, xsd:dateTime, xsd:anyURI). "Add Property" button appends a new row. "Remove" button per row. Properties serialized as JSON in a hidden input.
   - **Submit button**: "Create Class" button. Show loading state during submission.
   - **Success state**: After successful creation, show confirmation with class name and a link to refresh the TBox tree.

2. **Add TBox search endpoint** — `GET /browser/ontology/tbox/search?q={query}` on ontology_router. Queries class labels across ontology graphs with case-insensitive FILTER CONTAINS. Returns HTML list of matching classes (label + IRI) for the parent class picker dropdown. Add `search_classes()` method to OntologyService.

3. **Modify `ontology_page.html`** — add a "Create Class" button in the TBox tab header area that shows/hides the creation form (htmx swap or toggle). Add `hx-trigger="classCreated from:body"` on the TBox content pane to auto-reload the tree when a class is created.

4. **Add CSS for form components** in `workspace.css`:
   - `.class-creation-form` layout (card style, consistent with existing form patterns)
   - `.icon-picker-grid` — grid of icon cells with hover/selected states
   - `.icon-picker-search` — filter input above grid
   - `.property-editor` — row layout with inputs and remove button
   - `.parent-class-picker` — search input with dropdown results
   - All Lucide SVG icons sized via CSS with `flex-shrink: 0` per CLAUDE.md rules

5. **Add JS for form interactions** in `workspace.js`:
   - `initIconPicker()` — handles icon selection, search filtering, hidden input update
   - `initPropertyEditor()` — handles add/remove property rows, serializes to JSON hidden input on form submit
   - `initParentClassPicker()` — handles search-as-you-type selection, stores IRI in hidden input
   - Wire `classCreated`/`classDeleted` events to trigger TBox tree reload

## Must-Haves

- [ ] Class creation form renders with all fields (name, icon, parent, properties)
- [ ] Icon picker shows curated Lucide icons with search filter and selection highlight
- [ ] Parent class selector searches TBox classes via htmx and stores selected IRI
- [ ] Property editor supports add/remove rows with predicate and datatype dropdowns
- [ ] Form submits via htmx POST and shows success/error feedback
- [ ] TBox tree auto-refreshes on classCreated event
- [ ] CSS follows existing conventions (Lucide SVG sizing, flex-shrink: 0, CSS variables for theming)

## Verification

- Start Docker stack, navigate to ontology viewer TBox tab
- Click "Create Class" button → form appears
- Fill in name, select icon, pick parent class, add 2 properties → submit
- Class appears in TBox tree with "user" badge and correct icon
- Navigate to "New Object" → new type appears in type picker

## Observability Impact

- Signals added/changed: None (UI-only task, backend already logs from T02)
- How a future agent inspects this: Browser devtools Network tab shows POST to /browser/ontology/create-class; htmx events visible in browser console
- Failure state exposed: Form validation errors shown inline; htmx error states on failed POST

## Inputs

- `backend/app/ontology/router.py` — POST endpoint from T02
- `backend/app/ontology/service.py` — `create_class()` from T01
- `backend/app/templates/browser/ontology/ontology_page.html` — existing three-tab layout from S07
- `backend/app/templates/browser/ontology/tbox_tree.html` — existing TBox tree with badge logic
- `frontend/static/css/workspace.css` — existing workspace styles
- `frontend/static/js/workspace.js` — existing workspace JS

## Expected Output

- `backend/app/templates/browser/ontology/create_class_form.html` — complete form template
- `backend/app/templates/browser/ontology/ontology_page.html` — modified with "Create Class" button and classCreated trigger
- `backend/app/templates/browser/ontology/tbox_tree.html` — added classCreated/classDeleted refresh listeners
- `backend/app/ontology/router.py` — added TBox search endpoint
- `backend/app/ontology/service.py` — added `search_classes()` method
- `frontend/static/css/workspace.css` — class creation form styles
- `frontend/static/js/workspace.js` — icon picker, property editor, parent picker JS
