---
estimated_steps: 3
estimated_files: 1
skills_used:
  - test
  - best-practices
---

# T04: Unit tests for task template CRUD and instantiation

**Slice:** S05 — Task Templates & Review Workflows
**Milestone:** M034

## Description

Write comprehensive pytest unit tests for `TaskTemplateService` with a mocked `TriplestoreClient`. Covers create, list, get, update, delete, and instantiate operations. Verifies SPARQL queries are well-formed, JSON blobs are correctly serialized/deserialized, and batch instantiation generates the right command structure with `@slot:` references.

## Steps

1. **Create `backend/tests/test_task_templates.py`** with fixtures:
   - `mock_triplestore` — `AsyncMock` of TriplestoreClient with `.query()` returning configurable SPARQL JSON results and `.update()` as a no-op
   - `template_service` — `TaskTemplateService(mock_triplestore)`
   - Helper to build SPARQL JSON result bindings (the format RDF4J returns)

2. **Write CRUD tests:**
   - `test_create_template` — call `service.create(title="Sprint Planning", target_class="urn:sempkm:model:basic-pkm:Task", default_properties={"bpkm:taskStatus": "todo"})` → verify `triplestore.update()` called with SPARQL INSERT DATA containing the title, target class, and JSON-serialized properties in the `urn:sempkm:task-templates` graph
   - `test_list_templates` — mock query returning 2 template bindings → verify service returns list of 2 dicts with id, title, target_class
   - `test_get_template` — mock query returning 1 binding with all fields → verify dict includes parsed default_properties and subtask_definitions as Python dicts (not JSON strings)
   - `test_get_template_not_found` — mock query returning empty bindings → verify returns None
   - `test_update_template` — call `service.update(template_id, title="Updated")` → verify SPARQL DELETE/INSERT for the title predicate
   - `test_delete_template` — call `service.delete(template_id)` → verify SPARQL DELETE WHERE called against named graph
   - `test_instantiate_without_subtasks` — create template with no subtask_definitions → verify instantiate returns command list with single `object.create` command, slot="main", properties matching defaults
   - `test_instantiate_with_subtasks` — create template with 2 subtask definitions → verify command list has 1 `object.create` (slot="main") + 2 `object.create` + 2 `edge.create` (source="@slot:main", predicate="bpkm:hasSubtask")

3. **Run tests:** `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py -v`

## Must-Haves

- [ ] All CRUD operations tested (create, list, get, update, delete)
- [ ] Get returns parsed JSON dicts, not raw strings
- [ ] Not-found case returns None
- [ ] Instantiate with subtasks generates correct @slot: references
- [ ] Instantiate without subtasks generates single command
- [ ] SPARQL queries target `urn:sempkm:task-templates` named graph

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_task_templates.py -v` — all tests pass

## Inputs

- `backend/app/task_templates/service.py` — TaskTemplateService implementation from T01
- `backend/app/task_templates/router.py` — for understanding instantiate response format
- `backend/app/commands/schemas.py` — ObjectCreateCommand, EdgeCreateCommand schemas
- `backend/app/triplestore/client.py` — TriplestoreClient.query() returns dict (SPARQL JSON result format), .update() returns None

## Expected Output

- `backend/tests/test_task_templates.py` — comprehensive test file with 8+ test cases
