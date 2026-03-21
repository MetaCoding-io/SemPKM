# S06 — Dashboard & Workflow Builder UX — Research

**Date:** 2026-03-21
**Depth:** Light research — straightforward application of existing patterns to existing code.

## Summary

S06 adds contextual help text, autocomplete for IRI fields, a simplified workflow "view" step, and sample seed data to the dashboard and workflow builders. The codebase already has all the patterns needed: `field-help` CSS classes, SHACL helptext rendering in `_field.html`, reference search endpoints (`/browser/search`), the `/browser/views/available` JSON API, and the `/api/dashboard` JSON API. This is primarily template enhancement work with one new endpoint (type/class search for autocomplete) and one seed data script.

## Requirements Covered

| Req | Description | Notes |
|-----|-------------|-------|
| DBUIX-01 | Dashboard/workflow builder help text | Add `<small class="field-help">` elements following the pattern in `_field.html` |
| DBUIX-02 | Autocomplete for object/type references in builders | Dashboard: target_class, object_iri, spec_iri fields. Workflow: target_class, spec_iri fields. Use existing `/browser/search` + new class search endpoint. |
| DBUIX-03 | Workflow view step simplification | Replace renderer dropdown with a saved-view picker. `/browser/views/available` already returns renderer_type per spec — no separate dropdown needed. |
| DBUIX-04 | Sample dashboard and workflow seed data | New script/endpoint to create sample DashboardSpec + WorkflowSpec rows in SQLite for first-install. |

## Recommendation

Four independent tasks, no ordering dependencies between them:

1. **Help text** — add `<small class="field-help">` to every builder form field. Pure template change.
2. **Autocomplete** — replace raw IRI text inputs with search-as-you-type for target_class and object_iri fields. Reuse existing search patterns.
3. **View step simplification** — replace the "View Spec + Renderer" two-dropdown pattern with a single saved-view/promoted-view picker that includes renderer info.
4. **Seed data** — create a management script or startup hook that inserts sample dashboard + workflow specs if none exist.

## Implementation Landscape

### Key Files

| File | Role | Changes Needed |
|------|------|----------------|
| `backend/app/templates/browser/dashboard_builder.html` | Dashboard builder form + JS | Add help text to all fields; replace raw IRI inputs with autocomplete widgets |
| `backend/app/templates/browser/workflow_builder.html` | Workflow builder form + JS | Add help text; simplify view step config; replace raw IRI inputs with autocomplete |
| `frontend/static/css/workspace.css` | Builder CSS (lines 7733–8033) | Minor: ensure `.field-help` inside `.dashboard-builder` / `.workflow-builder` inherits correctly (already defined at line 2588). May need `.reference-field` and `.suggestions-dropdown` styling inside builder context. |
| `frontend/static/css/forms.css` | Base form CSS | `.field-help` already defined at line 50. No changes needed. |
| `backend/app/browser/search.py` | `/browser/search` endpoint | Already handles `type`+`q` reference search. Already returns HTML suggestions. Can be reused as-is for object_iri autocomplete. |
| `backend/app/ontology/service.py` | `search_classes()` at line 931 | Already exists — searches classes by query string. Needed for target_class autocomplete. |
| `backend/app/ontology/router.py` | Ontology routes | May need a thin JSON endpoint wrapping `search_classes()` for builder autocomplete, or reuse existing endpoint that returns HTML suggestions. |
| `backend/app/views/router.py` | `/browser/views/available` at line 70 | Already returns JSON `[{spec_iri, label, renderer_type, target_class}]`. Perfect for the simplified view step picker. |
| `backend/app/dashboard/service.py` | Dashboard CRUD | No changes needed for help/autocomplete. Seed data will call `create()`. |
| `backend/app/workflow/service.py` | Workflow CRUD | No changes needed for help/autocomplete. Seed data will call `create()`. |
| `backend/app/main.py` | App startup, lines 335/339 | Seed data hook attaches here — after `dashboard_service`/`workflow_service` are created. |
| `backend/app/templates/forms/_field.html` | SHACL field macro | **Reference pattern** — shows how help text, helptext toggles, and reference-search autocomplete are rendered. Do NOT modify — copy the pattern. |

### Existing Patterns to Reuse

#### Help Text Pattern (from `_field.html`)
```html
<small class="field-help">A short description or summary.</small>
```
CSS is already defined in `workspace.css` line 2588:
```css
.field-help { display: block; font-size: 0.76rem; color: var(--color-text-muted); margin-bottom: 6px; line-height: 1.45; }
```

The dashboard builder already uses `<span class="field-help">` in two places (emits_context checkbox and context variable field). Extend this to all fields.

#### Reference Search Autocomplete (from `_field.html`)
For `sh:class` reference fields, the SHACL form uses:
```html
<div class="reference-field">
  <input type="text" autocomplete="off"
         hx-get="/browser/search?type={{ target_class }}"
         hx-trigger="input changed delay:300ms"
         hx-target="#suggestions-{{ field_id }}"
         hx-swap="innerHTML">
  <input type="hidden" name="{{ input_name }}" value="{{ current_value }}">
  <div id="suggestions-{{ field_id }}" class="suggestions-dropdown"></div>
</div>
```
This pattern works with htmx and returns HTML suggestions from `/browser/search`. The dashboard/workflow builder currently uses vanilla JS `fetch()` for everything — the autocomplete fields should use the same htmx pattern for consistency with the rest of the app.

**However**: The builder forms use JavaScript-generated DOM (via `getTypeConfigHTML()` returning HTML strings). htmx `hx-get` on dynamically inserted elements requires `htmx.process()` to be called after insertion. The builder already calls `lucide.createIcons()` after insertion — add `htmx.process()` in the same spot.

#### Available Views JSON Endpoint
`GET /browser/views/available` returns:
```json
[{"spec_iri": "...", "label": "...", "renderer_type": "table", "target_class": "..."}]
```
The workflow builder already fetches this for the view step. The simplification replaces two dropdowns (spec + renderer) with one dropdown that shows `label (renderer_type)` and stores both values.

### Help Text Content

#### Dashboard Builder
| Field | Help Text |
|-------|-----------|
| Name | A short, descriptive name for your dashboard. |
| Description | Optional notes about what this dashboard shows or who it's for. |
| Layout | Choose how blocks are arranged. Each layout has named slots where blocks appear. |
| Block Type | The kind of content this block displays. |
| Block Slot | Which area of the layout this block occupies. |
| View Spec (view-embed) | The view definition to embed. It determines what data and columns appear. |
| Renderer (view-embed) | How the view is rendered: as a table, cards, or graph. |
| Emits context (view-embed) | When checked, clicking a row in this view sets a context IRI that other blocks can react to. |
| Context variable (view-embed) | The SPARQL variable name that will be bound to the context IRI from another block. Leave empty if this block doesn't consume context. |
| Content (markdown) | Text content in Markdown format. Supports paragraphs and basic formatting. |
| Target Class IRI (create-form) | The RDF type IRI for the object creation form (e.g. a class from your model). |
| Object IRI (object-embed) | The IRI of a specific object to display in this block. |
| SPARQL Query (sparql-result) | A SELECT query whose first result value is displayed as a metric. |
| Label (sparql-result) | A short label shown above the query result value. |

#### Workflow Builder
| Field | Help Text |
|-------|-----------|
| Name | A short name for this workflow. |
| Description | Optional notes about when to use this workflow or what it accomplishes. |
| Step Label | A short label shown in the stepper bar. Defaults to "Step N" if empty. |
| Step Type | What this step shows: a view of objects, an existing dashboard, or a form to create an object. |
| View (view step) | Choose a view to display. The view's own renderer (table/cards/graph) will be used. |
| Dashboard (dashboard step) | Choose an existing dashboard to embed as this step. |
| Target Class IRI (form step) | The RDF type IRI for the create form. |

### Autocomplete Fields

Three IRI input fields in the builders need autocomplete:

1. **Target Class IRI** (dashboard create-form block, workflow form step) — needs class/type search. Use `OntologyService.search_classes(query)` which already exists at line 931 of `ontology/service.py`. Need a thin JSON endpoint (or HTML suggestion endpoint) that the builder can call. Pattern: `hx-get="/browser/class-search?q=..."` returning suggestion items.

2. **Object IRI** (dashboard object-embed block) — needs object search across all types. The existing `/browser/search` endpoint requires a `type` parameter. For the builder, we either (a) add a type picker first, then search within that type, or (b) create a general `/browser/search-all?q=...` endpoint that searches across all types. Option (b) is simpler UX — search by label across all objects.

3. **View Spec** (dashboard view-embed block, workflow view step) — already uses a `<select>` populated from `/browser/views/available`. This works well as-is for small numbers of views. Could enhance with a filterable select (type-ahead) but the current dropdown is adequate.

**Recommendation for autocomplete scope:** Implement target_class autocomplete (high value — users must know exact IRIs today). Enhance object_iri with a two-step "pick type, then search" or a universal search. Keep spec_iri as the current dropdown (adequate UX, low risk).

### View Step Simplification (DBUIX-03)

**Current state:** The workflow builder's "view" step renders two dropdowns:
1. "View Spec" — a `<select>` populated from `/browser/views/available`
2. "Renderer" — a hardcoded `<select>` with table/card/graph options

**Problem:** The renderer dropdown is redundant because each ViewSpec already has a `renderer_type`. Choosing "Projects Table" and then "graph" renderer makes no sense.

**Fix:** Remove the "Renderer" dropdown. The view spec selection is sufficient — `renderer_type` comes from the spec. In `getTypeConfigHTML('view', ...)`:
- Remove the renderer `<select>`
- The save logic already collects `data-key="renderer_type"` from a select — instead, set `renderer_type` automatically from the selected view spec's metadata.

**Implementation:** When a view is selected from the dropdown, look up its `renderer_type` from `_cachedViews` and store it in a hidden field. The save function reads the hidden field's `data-key="renderer_type"`.

Alternatively (simpler): show the renderer as a read-only badge/text after selection, not as a dropdown. E.g., selecting "Projects Table" shows "(table)" next to it.

### Seed Data (DBUIX-04)

**Approach:** Add a function `seed_sample_data(dashboard_service, workflow_service)` called during app startup if no dashboards/workflows exist for the system user.

**Sample dashboard:** "Getting Started"
- Layout: `sidebar-main`
- Blocks:
  - sidebar slot: markdown block with welcome text
  - main slot: view-embed with the default "All Objects — Table" view

**Sample workflow:** "Create & Review"
- Steps:
  1. form step: create a Note (if basic-pkm model is installed)
  2. view step: show all Notes table

**Guard:** Only insert if `list_for_user(system_user_id)` returns empty. This makes it idempotent.

**Challenge:** Need a known user ID. Options:
- Use the first user from the users table
- Create a "system" seed that runs per-user on first login
- Add a startup migration that uses a well-known admin user

The per-user-on-first-login approach is cleanest — add a check in the dashboard/workflow explorer endpoints: if `list_for_user` returns empty AND user hasn't dismissed the sample data, auto-create samples. This avoids needing a specific user ID at startup.

Simpler alternative: just seed for all existing users at startup if they have 0 dashboards. Since `create()` is idempotent (UUID-based), this is safe.

### Natural Seams (Task Decomposition)

**Task 1: Help Text** — Pure template changes to `dashboard_builder.html` and `workflow_builder.html`. Add `<small class="field-help">` elements after labels. No backend changes. No CSS changes needed (styles already exist).

**Task 2: Autocomplete for Target Class IRI** — Add a `/browser/class-search` endpoint (or reuse ontology router) that returns HTML suggestion items matching `OntologyService.search_classes()`. Update `getTypeConfigHTML('create-form')` in dashboard builder and `getTypeConfigHTML('form')` in workflow builder to use `hx-get` + suggestions dropdown instead of a plain text input. Call `htmx.process()` after inserting the HTML. CSS may need `.reference-field` and `.suggestions-dropdown` to work inside `.block-config-fields`.

**Task 3: Object IRI Autocomplete** — Similar to Task 2, but for the `object-embed` block type. Needs a general-purpose object search. Could reuse `/browser/search` with an optional `type` parameter (if type is empty, search all).

**Task 4: Workflow View Step Simplification** — Modify `getTypeConfigHTML('view')` in `workflow_builder.html` to remove the renderer dropdown. Store `renderer_type` from the selected view spec automatically. Update `render_step()` in `workflow/router.py` to use the stored renderer_type from config (it already does — `config.get("renderer_type", "table")`).

**Task 5: Seed Data** — New file `backend/app/dashboard/seed.py` (or similar) with sample data definitions. Hook into startup in `main.py` after services are initialized.

### Verification

- **Help text:** Visual — open dashboard builder (`/browser/dashboard/new`) and workflow builder (`/browser/workflow/new`), confirm help text appears below each field label.
- **Autocomplete:** Open dashboard builder, add a create-form block, type in "Target Class IRI" field → suggestions appear. Select one → IRI is set.
- **View step simplification:** Open workflow builder, add a "view" step → see one dropdown (view picker) not two (view + renderer).
- **Seed data:** Fresh user with no dashboards → explorer shows "Getting Started" dashboard.
