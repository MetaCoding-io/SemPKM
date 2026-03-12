# T01: 37-global-lint-data-model-api 01

**Slice:** S37 — **Milestone:** M001

## Description

Build the lint data model, storage layer, and REST API endpoints for querying structured SHACL validation results.

Purpose: Transform raw pyshacl report graphs into individually queryable structured result triples stored in per-run named graphs. Provide paginated, filterable REST endpoints that Phase 38's dashboard UI will consume.

Output: New `backend/app/lint/` package with models, service, and router. Extended ValidationReport with structured triple generation. Working `/api/lint/results`, `/api/lint/status`, and `/api/lint/diff` endpoints.

## Must-Haves

- [ ] "GET /api/lint/results returns paginated validation results with severity, message, path, object_label"
- [ ] "GET /api/lint/results?severity=Violation filters to violations only"
- [ ] "GET /api/lint/results?object_type=<iri> filters by object type"
- [ ] "GET /api/lint/results?detail=full includes source_shape, constraint_component, source_model"
- [ ] "GET /api/lint/status returns summary counts (violations, warnings, infos, conforms, timestamp)"
- [ ] "GET /api/lint/diff returns new_issues and resolved_issues comparing latest vs previous run"
- [ ] "Validation runs store structured result triples in per-run named graphs"

## Files

- `backend/app/lint/__init__.py`
- `backend/app/lint/models.py`
- `backend/app/lint/service.py`
- `backend/app/lint/router.py`
- `backend/app/validation/report.py`
- `backend/app/services/validation.py`
- `backend/app/dependencies.py`
- `backend/app/main.py`
