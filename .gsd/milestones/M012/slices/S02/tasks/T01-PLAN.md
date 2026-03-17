---
estimated_steps: 6
estimated_files: 4
---

# T01: Add body.diff command schema, handler, and dispatcher wiring

**Slice:** S02 — Body.Diff — Incremental Storage & Rendering
**Milestone:** M012

## Description

Create the foundation for the `body.diff` operation type: a new Pydantic command model, a handler that produces the correct `Operation`, and wiring into the dispatcher and webhook systems. This is pure backend plumbing with no runtime dependencies — it can be tested by import alone.

The handler mirrors `handle_body_set()` but stores TWO things in `data_triples`: (1) the diff text via `sempkm:bodyDiff` predicate, and (2) the full new body via the body predicate. Materialization is identical to `body.set` — delete old body, insert new body in `urn:sempkm:current`.

## Steps

1. **Add `BodyDiffParams` to `backend/app/commands/schemas.py`:**
   ```python
   class BodyDiffParams(BaseModel):
       """Parameters for storing an incremental body diff."""
       iri: str              # The object IRI
       body: str             # Full new body content (for materialization)
       diff_text: str        # Unified diff string (for event storage)
       predicate: str | None = None  # Optional override; defaults to sempkm:body
   ```

2. **Add `BodyDiffCommand` to `backend/app/commands/schemas.py`:**
   ```python
   class BodyDiffCommand(BaseModel):
       """Store an incremental body diff."""
       command: Literal["body.diff"]
       params: BodyDiffParams
   ```
   Add `BodyDiffCommand` to the `Command` discriminated union.

3. **Create `backend/app/commands/handlers/body_diff.py`:**
   - Import `URIRef, Literal, Variable` from rdflib, `XSD` from rdflib.namespace, `SEMPKM` from `app.rdf.namespaces`
   - `async def handle_body_diff(params: BodyDiffParams, base_namespace: str) -> Operation:`
   - Resolve `predicate` (default to `SEMPKM.body`), same as `handle_body_set`
   - Build `data_triples`:
     - `(subject, SEMPKM.bodyDiff, Literal(params.diff_text, datatype=XSD.string))` — the stored diff
     - `(subject, predicate, Literal(params.body, datatype=XSD.string))` — the new full body
   - Build `materialize_deletes`: `[(subject, predicate, Variable("old_body"))]` — same as body.set
   - Build `materialize_inserts`: `[(subject, predicate, Literal(params.body, datatype=XSD.string))]`
   - If `predicate != SEMPKM.body`, also delete canonical body (same as body.set)
   - Return `Operation(operation_type="body.diff", affected_iris=[params.iri], description=f"Diff body on: {params.iri}", ...)`

4. **Register handler in `backend/app/commands/dispatcher.py`:**
   - In `_register_handlers()`, add:
     ```python
     from app.commands.handlers.body_diff import handle_body_diff
     HANDLER_REGISTRY["body.diff"] = handle_body_diff
     ```

5. **Add webhook mapping in `backend/app/commands/router.py`:**
   - Add `"body.diff": "object.changed"` to `_COMMAND_EVENT_MAP` dict

6. **Verify imports work:**
   - Run: `cd backend && python -c "from app.commands.handlers.body_diff import handle_body_diff; from app.commands.schemas import BodyDiffCommand; print('OK')"`

## Must-Haves

- [ ] `BodyDiffParams` model with `iri`, `body`, `diff_text`, `predicate` fields
- [ ] `BodyDiffCommand` added to `Command` discriminated union
- [ ] `handle_body_diff()` stores both `sempkm:bodyDiff` and body predicate in data_triples
- [ ] Handler materialization matches `body.set` pattern (delete old, insert new)
- [ ] Handler registered in `HANDLER_REGISTRY["body.diff"]`
- [ ] `"body.diff"` mapped to `"object.changed"` in `_COMMAND_EVENT_MAP`

## Verification

- `cd backend && python -c "from app.commands.handlers.body_diff import handle_body_diff; print('OK')"` — imports without error
- `cd backend && python -c "from app.commands.schemas import BodyDiffCommand, BodyDiffParams; print('OK')"` — imports without error
- `cd backend && python -c "from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers; _register_handlers(); assert 'body.diff' in HANDLER_REGISTRY; print('OK')"` — handler registered
- `cd backend && python -m pytest tests/ -v --tb=short -x -q 2>&1 | tail -5` — no regressions

## Inputs

- `backend/app/commands/schemas.py` — existing command models to extend (BodySetParams/BodySetCommand as reference pattern)
- `backend/app/commands/handlers/body_set.py` — reference handler implementation to mirror
- `backend/app/commands/dispatcher.py` — handler registry to extend
- `backend/app/commands/router.py` — webhook event map to extend
- `backend/app/events/store.py` — `Operation` dataclass used as handler return type
- `backend/app/rdf/namespaces.py` — `SEMPKM` namespace (auto-generates `SEMPKM.bodyDiff` as `URIRef("urn:sempkm:bodyDiff")`)

## Expected Output

- `backend/app/commands/handlers/body_diff.py` — new file with `handle_body_diff()` function
- `backend/app/commands/schemas.py` — extended with `BodyDiffParams`, `BodyDiffCommand`, updated `Command` union
- `backend/app/commands/dispatcher.py` — `body.diff` registered in handler registry
- `backend/app/commands/router.py` — `body.diff` mapped in webhook event map

## Observability Impact

- **New signal:** `body.diff` becomes a recognized `operation_type` in `HANDLER_REGISTRY` and `_COMMAND_EVENT_MAP`. Previously only `body.set` existed for body operations.
- **Inspection:** `HANDLER_REGISTRY.keys()` now includes `"body.diff"` — agents can verify via `python -c "from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers; _register_handlers(); print(list(HANDLER_REGISTRY.keys()))"`.
- **Webhook mapping:** `_COMMAND_EVENT_MAP["body.diff"]` returns `"object.changed"`, ensuring body diff operations trigger the same webhook events as body.set.
- **Failure visibility:** If `body.diff` is dispatched but not registered, `InvalidCommandError("Unknown command type: body.diff")` is raised — visible as a 400 response with structured error JSON. If the Pydantic discriminator fails, a `ValidationError` surfaces with the unknown `command` value.
