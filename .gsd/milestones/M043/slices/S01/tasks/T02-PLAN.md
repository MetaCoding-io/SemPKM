---
estimated_steps: 6
estimated_files: 5
skills_used: []
---

# T02: Migrate confirmed-exploitable modules to SPARQLBuilder

Replace all f-string SPARQL IRI interpolation in the 4 confirmed-exploitable modules with SPARQLBuilder calls:

1. views/service.py (~45 <{iri}> patterns): Replace type_iri interpolation in build_dynamic_query(), _build_default_select(), execute_graph_query(), etc. with safe_iri(). Replace VALUES clause construction with values_clause().
2. views/router.py (~31 patterns): Add safe_iri() validation on all type/iri query parameters at endpoint entry point before any service call. This is the primary injection boundary.
3. browser/apps.py (~20 patterns): Replace raw f"<{iri}>" in right_pane_sections() and other endpoints with safe_iri().
4. vfs/mount_router.py (~41 patterns in mount_service + 72 in mount_router): Replace IRI field interpolation in mount creation/update SPARQL INSERT DATA with safe_iri(). Replace string interpolation with safe_literal().

For each module: remove the local escape function, import from sparql.builder, verify the module's existing tests pass.

## Inputs

- `backend/app/sparql/builder.py`

## Expected Output

- `backend/app/views/service.py`
- `backend/app/views/router.py`
- `backend/app/browser/apps.py`
- `backend/app/vfs/mount_router.py`
- `backend/app/vfs/mount_service.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60
