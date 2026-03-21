---
estimated_steps: 5
estimated_files: 1
---

# T03: Docker integration verification and performance documentation

**Slice:** S01 — Validation Pipeline Fix & Performance Measurement
**Milestone:** M030

## Description

Verify the pipeline fix works in the real Docker stack and document the performance baseline. This retires the "Validation performance with rules enabled" risk from the M030 roadmap. The verification creates a real overdue task, triggers validation, and confirms the warning appears in the lint panel.

## Steps

1. Start the Docker test stack:
   ```bash
   cd /home/james/Code/SemPKM
   docker compose -f docker-compose.test.yml up -d --build
   ```
   Wait for health check: `curl -s http://localhost:8901/api/health`

2. Verify the pipeline fix is active by checking Docker logs for the shapes loader message:
   ```bash
   docker compose -f docker-compose.test.yml logs api 2>&1 | grep -i "shapes\|rules\|triples"
   ```
   The log should show both shapes AND rules triple counts (e.g., "Loaded X shapes + Y rules triples from N model(s)").

3. Create a Task with a past due date. Use the SPARQL API or the commands API to create a test task:
   ```bash
   curl -s -X POST http://localhost:8901/api/commands \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{"commands": [{"type": "object.create", "data": {"type_iri": "urn:sempkm:model:basic-pkm:Task", "properties": {"urn:sempkm:model:basic-pkm:taskStatus": "todo", "urn:sempkm:model:basic-pkm:dueDate": "2020-01-01", "http://purl.org/dc/terms/title": "Overdue test task"}}}]}'
   ```
   (Get the auth token from the test stack setup process.)

4. Trigger validation and check the lint panel/dashboard for the overdue-task warning. Either:
   - Open the browser to `http://localhost:3901/browser/` and navigate to the task object, check the lint panel in the right pane
   - Or check the lint dashboard at `http://localhost:3901/browser/lint-dashboard`
   - Or query the API for validation results

5. Document findings by saving a slice summary artifact:
   - Record pyshacl execution time from T02's functional test
   - Record Docker-observed behavior (rules loaded, warning appeared)
   - State whether the performance risk is retired (target: <5s for ~100 objects)
   - Use `gsd_save_summary` to persist the performance baseline

## Must-Haves

- [ ] Docker logs show rules triples loaded alongside shapes triples
- [ ] Overdue-task warning appears in lint panel or dashboard after creating an overdue task
- [ ] Performance baseline documented

## Verification

- Docker API logs contain "rules triples" in the shapes loader output
- Lint panel or dashboard shows at least one Warning result for the overdue task
- Performance documentation written via gsd_save_summary

## Observability Impact

- Signals added/changed: `model_shapes_loader` log message now includes rules triple count — enables future diagnosis of "are rules loaded?"
- How a future agent inspects this: `docker compose logs api | grep "rules triples"` shows whether rules are being loaded
- Failure state exposed: if rules count is 0, rules graphs are empty or not being fetched

## Inputs

- T01's code changes in `backend/app/services/models.py` and `backend/app/services/validation.py`
- T02's test results and performance timing
- Running Docker test stack

## Expected Output

- Evidence (log output or screenshot) of overdue-task warning in lint panel
- Performance baseline documented via gsd_save_summary (pyshacl timing with advanced=True)
