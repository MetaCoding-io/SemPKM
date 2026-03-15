# S04: Tag Autocomplete — Research

**Date:** 2026-03-14  
**Status:** Ready for planning

## Summary

This slice adds autocomplete to tag input fields in edit forms. The codebase already has a battle-tested pattern for search-as-you-type in `sh:class` reference fields: htmx `hx-get` with `delay:300ms` trigger, server-side SPARQL query, HTML suggestion dropdown rendered as htmx partial. Tag autocomplete follows the same pattern but is simpler — no IRI resolution, no hidden inputs, just plain string values.

The primary design question is how to detect tag fields in the `_field.html` macro and render an autocomplete-enabled input vs a plain `<input type="text">`. The existing `'tags' in prop.path or 'keywords' in prop.path` heuristic (used in both `_field.html` and `object_read.html`) is the natural dispatch point. The backend needs a single new endpoint that queries distinct tag values from the triplestore, filtered by a user-typed prefix string.

The approach is low-risk: one new endpoint, one new Jinja2 template, a small CSS addition, and a conditional branch in the existing `_field.html` macro. No JS framework needed — htmx handles the request/response cycle, and a small inline script handles value selection.

## Recommendation

**Follow the existing reference-field pattern** (`_field.html` → `search.py` → `search_suggestions.html`) but simplified for tag strings:

1. **New endpoint:** `GET /browser/tag-suggestions?q=<prefix>` on the workspace router (or search router). Runs a SPARQL query with `CONTAINS` or `STRSTARTS` filter against both `bpkm:tags` and `schema:keywords`, returns distinct tag values matching the query. Returns an HTML partial with suggestion items.

2. **Modified `_field.html` macro:** Add a new branch for tag properties (before the default `<input type="text">`). Renders the tag input with `hx-get="/browser/tag-suggestions"`, `hx-trigger="input changed delay:200ms"`, and a suggestions dropdown div — same structure as the reference-field search but without the hidden IRI input.

3. **New template:** `browser/tag_suggestions.html` — renders suggestion items that, when clicked, set the input value to the selected tag string. Simpler than `search_suggestions.html` (no `selectReference` IRI handling).

4. **JS:** Minimal inline click handler in the template — `onclick` sets the input value and clears the suggestions div. Optionally: keyboard navigation (ArrowDown/ArrowUp/Enter) for power users, but this can be deferred.

5. **CSS:** Reuse `.suggestions-dropdown` and `.suggestion-item` from `forms.css`. Add tag-specific accent styling if desired (matching `.tag-pill` colors).

### Why not htmx `<datalist>`?

HTML `<datalist>` is tempting (zero JS) but has critical limitations: no styling control, no async loading, browser-inconsistent behavior, and poor support for the "create new tag" affordance. The htmx dropdown pattern gives full control and is already proven in this codebase.

### Why not a client-side JS autocomplete library?

The codebase is htmx + vanilla JS (no frameworks). Adding a JS autocomplete library (awesomplete, choices.js, etc.) would introduce a new dependency pattern. The existing htmx suggestion pattern works well and keeps the stack consistent.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Search-as-you-type dropdown | `_field.html` reference-field pattern + `search.py` | Proven htmx pattern, already styled in `forms.css` |
| Tag property detection | `is_tag_property()` / `'tags' in prop.path` heuristic | Used in 3 places already (D041), consistent |
| SPARQL execution with error handling | `_execute_sparql_select()` helper | Handles exceptions, returns `[]` on failure |
| SPARQL string escaping | `_sparql_escape()` in workspace.py | Escapes `\`, `"`, `\n` for SPARQL string literals |
| Suggestions dropdown CSS | `.suggestions-dropdown`, `.suggestion-item` in `forms.css` | Already styled, positioned, z-indexed |

## Existing Code and Patterns

- `backend/app/templates/forms/_field.html` — The `_render_input` macro dispatches on property type. Tag fields currently fall through to the default `<input type="text">`. Add a new `elif 'tags' in prop.path or 'keywords' in prop.path` branch before the default case. Follow the `prop.target_class` branch structure (search input + dropdown div) but simpler (no hidden IRI input).

- `backend/app/browser/search.py` — `search_references()` endpoint is the pattern to follow. New tag-suggestions endpoint is structurally identical but returns distinct tag strings instead of object IRIs+labels. Could live in `search.py` (same sub-router) or in `workspace.py` (near tag-children).

- `frontend/static/css/forms.css` lines 162–205 — `.reference-field`, `.suggestions-dropdown`, `.suggestion-item` CSS. Fully reusable for tag suggestions. Only addition needed: a `.tag-suggestion-item` variant (or reuse existing) for visual accent matching tag pills.

- `backend/app/browser/workspace.py` lines 151–193 — `_handle_by_tag()` SPARQL query fetches all distinct tag values with counts. The autocomplete endpoint needs a similar query but with a `CONTAINS(?tagValue, "{query}")` filter and without the `COUNT` aggregation (or with it for ranking).

- `backend/app/browser/tag_tree.py` — Pure function, not directly used by autocomplete, but the S03 infrastructure proves the SPARQL patterns work.

- `backend/app/templates/browser/search_suggestions.html` — Template pattern for suggestion items. Tag version is simpler: no `selectReference()`, no `Create new` option (users just type new tags freely).

- `backend/app/templates/forms/object_form.html` lines 127–141 — `addMultiValue()` JS function clones input fields for multi-value properties. Must work correctly with autocomplete-enabled tag inputs (clone needs the `hx-get` attributes and a new suggestions div).

## Constraints

- **htmx + vanilla JS only** — no JS frameworks, no npm dependencies. All interactivity via htmx attributes + inline `<script>` blocks.
- **Two tag properties** — `bpkm:tags` (`urn:sempkm:model:basic-pkm:tags`) and `schema:keywords` (`https://schema.org/keywords`). SPARQL must UNION both. The `is_tag_property` heuristic (`'tags' in path or 'keywords' in path`) determines which fields get autocomplete.
- **Multi-value** — Tag fields are multi-valued (`sh:maxCount` is null). Each value gets its own input + autocomplete dropdown. The `addMultiValue()` JS function must clone the autocomplete structure correctly (htmx attributes, new suggestion div ID).
- **SPARQL string injection** — User input goes into SPARQL FILTER. Must use `_sparql_escape()` to prevent injection. The existing reference search uses parameterized queries; tag suggestions must do the same.
- **Case sensitivity** — SPARQL `CONTAINS` is case-sensitive by default. Use `LCASE()` wrapper or `REGEX` with `"i"` flag for case-insensitive matching. RDF4J supports both.
- **Tag values are plain strings** — No IRI resolution needed. Autocomplete returns the tag string itself, which is directly set as the input value.
- **Empty query** — When the user focuses the input but hasn't typed, show all tags (or top N tags by frequency). This gives discoverability of existing tags.

## Common Pitfalls

- **`addMultiValue()` cloning breaks htmx** — When `addMultiValue()` clones a tag input, the cloned element has stale `hx-target` IDs pointing to the original suggestion div. Must update `hx-target` and suggestion div `id` with the new index (same issue already handled for reference fields in `addMultiValue()` — follow that pattern).

- **Suggestions dropdown doesn't close** — Need to dismiss the dropdown when the user clicks outside or presses Escape. The reference-field pattern relies on the dropdown being `:empty` to hide via CSS (`.suggestions-dropdown:not(:empty) { display: block }`). Tag selection should clear the dropdown innerHTML. Also need a click-outside handler or blur event.

- **Race condition on rapid typing** — htmx `delay:300ms` prevents rapid-fire requests, but if two requests are in flight, the last response wins. htmx handles this by default (cancels previous request on new trigger). No custom handling needed.

- **SPARQL injection via tag query** — The `q` parameter is user input that goes into a SPARQL FILTER string. Must escape with `_sparql_escape()` before interpolation. This is the same concern as the reference search, handled identically.

- **Large tag sets** — If there are thousands of unique tags, returning all on empty query is expensive. Cap results with `LIMIT 50` (or similar) and sort by frequency (`COUNT DESC`) so the most-used tags appear first.

- **Tag pill styling in edit mode** — Current `.tag-pill-item` styling (pill-shaped input) may conflict with the suggestions dropdown positioning. The dropdown needs `position: relative` on the parent container, same as `.reference-field`. Either wrap the tag input in a new container or add the positioning to `.tag-pill-item`.

## Open Risks

- **Performance with Ideaverse data** — Ideaverse import creates hundreds of unique tags. A `CONTAINS` + `LCASE` SPARQL filter on all tags should be fast (string comparison on a few hundred values), but hasn't been benchmarked. Mitigation: add `LIMIT 30` to cap results.

- **`addMultiValue()` complexity** — The function already handles reference field cloning (updating IDs, `hx-target`, etc.). Adding tag-autocomplete cloning follows the same pattern but needs testing to ensure correct ID generation and htmx reprocessing.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| htmx | N/A — htmx is well-understood in this codebase | none needed |
| FastAPI/Jinja2 | N/A — standard pattern, no skill needed | none needed |
| SPARQL | N/A — pattern reuse from S03 | none needed |

No external skills needed — this slice uses exclusively established codebase patterns.

## Sources

- Existing reference-field autocomplete: `backend/app/browser/search.py` + `forms/_field.html` + `search_suggestions.html`
- Tag property detection heuristic: D041 decision
- S03 tag tree SPARQL patterns: `backend/app/browser/workspace.py` lines 151–193, 704–850
- S03 summary forward intelligence: tag values come from both `bpkm:tags` and `schema:keywords` via UNION
- Form field rendering: `backend/app/templates/forms/_field.html` `_render_input` macro
- Multi-value JS: `object_form.html` `addMultiValue()` function
