---
estimated_steps: 30
estimated_files: 3
skills_used: []
---

# T01: Backend explorer config model and query composition engine

Create the backend foundation: an ExplorerConfig dataclass, a query composition engine that builds SPARQL from filter/group/sort layers, and a config-options API endpoint.

**Slice context:** This is S01 of M054 — replacing the flat OBJECTS dropdown with composable filter/group/sort. This task builds the engine; T02 builds the tree-rendering endpoint; T03 builds the frontend config builder; T04 wires everything together.

**Architecture (D400):** Reuse VFS strategies.py query builders with a new composition layer.

## Steps

1. Create `backend/app/browser/explorer_config.py` with:
   - `ExplorerConfig` dataclass: `type_filter: str | None` (type IRI), `group_by: str | None` (property IRI or special values 'type', 'tag'), `sort_by: str | None` (property IRI or special values 'label', 'created'), `sort_order: str` ('asc'/'desc', default 'asc')
   - `build_explorer_query(config: ExplorerConfig) -> str` function that composes SPARQL:
     - Base: `SELECT ?iri ?label ?typeIri ?groupValue ?groupLabel ?sortValue` from current graph
     - Filter layer: if type_filter set, add `?iri a <type_filter_iri>`
     - Group layer: if group_by is 'type', bind `?groupValue` to `?typeIri` and `?groupLabel` to type local name; if group_by is 'tag', query `bpkm:tags`/`schema:keywords`; if group_by is a property IRI, query that property's values
     - Sort layer: if sort_by is 'label', ORDER BY ?label; if sort_by is 'created', ORDER BY dcterms:created; if sort_by is a property IRI, OPTIONAL bind that property and ORDER BY it
     - Always include label resolution using `_LABEL_OPTIONALS` and `_LABEL_COALESCE` from strategies.py
   - `build_group_folders_query(config: ExplorerConfig) -> str | None` — returns a query for folder-level groups (distinct group values + counts), or None if no grouping configured

2. Create `GET /browser/explorer/config-options` endpoint in workspace.py:
   - Returns JSON with: `types` (from ShapesService.get_types with hidden types excluded), `properties` (from ShapesService — for each type, list groupable/sortable properties with path IRI and label), `sort_options` (built-in: label, created; plus type-specific date/enum properties)
   - This endpoint powers the config builder dropdowns in T03

3. Create `backend/tests/test_explorer_config.py` with unit tests:
   - Test `build_explorer_query` with no config (all objects, sorted by label)
   - Test with type_filter only (produces `?iri a <type>` constraint)
   - Test with group_by='type' (produces groupValue/groupLabel bindings)
   - Test with group_by=property IRI (produces OPTIONAL property binding)
   - Test with sort_by='created' + sort_order='desc' (produces ORDER BY DESC)
   - Test with combined filter+group+sort (all layers compose correctly)
   - Test `build_group_folders_query` returns correct folder query or None

**Key constraints:**
- Import `_LABEL_OPTIONALS`, `_LABEL_COALESCE` from `app.vfs.strategies` — do NOT duplicate
- Use `CURRENT_GRAPH` from `app.rdf.namespaces`
- Use `safe_iri()` from `app.sparql.builder` for any IRI interpolation (Knowledge pattern 12)
- Filter out `rdfs:Resource` type from results
- Properties for grouping: use ShapesService.get_node_shapes() → iterate PropertyShape objects, expose those with `in_values` (enum-like) as preferred group candidates, and all others as available

## Inputs

- ``backend/app/vfs/strategies.py` — existing SPARQL query builders to reuse (_LABEL_OPTIONALS, _LABEL_COALESCE, query_type_folders pattern)`
- ``backend/app/services/shapes.py` — ShapesService.get_types(), get_node_shapes() for type/property enumeration`
- ``backend/app/browser/workspace.py` — explorer_tree endpoint pattern, _execute_sparql_select helper`
- ``backend/app/rdf/namespaces.py` — CURRENT_GRAPH constant`
- ``backend/app/sparql/builder.py` — safe_iri() for SPARQL IRI interpolation`

## Expected Output

- ``backend/app/browser/explorer_config.py` — ExplorerConfig dataclass + build_explorer_query() + build_group_folders_query()`
- ``backend/tests/test_explorer_config.py` — unit tests for query composition with all config combinations`
- ``backend/app/browser/workspace.py` — new config-options endpoint added`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_explorer_config.py -v
