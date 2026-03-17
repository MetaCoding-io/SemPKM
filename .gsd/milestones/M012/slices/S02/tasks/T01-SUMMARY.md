---
id: T01
parent: S02
milestone: M012
provides:
  - BodyDiffParams and BodyDiffCommand Pydantic schemas
  - handle_body_diff() handler producing Operation with diff + body data triples
  - body.diff registered in HANDLER_REGISTRY and _COMMAND_EVENT_MAP
key_files:
  - backend/app/commands/handlers/body_diff.py
  - backend/app/commands/schemas.py
  - backend/app/commands/dispatcher.py
  - backend/app/commands/router.py
  - backend/tests/test_body_diff.py
key_decisions: []
patterns_established:
  - body.diff handler mirrors body.set but adds sempkm:bodyDiff data triple for diff text alongside the full body triple
observability_surfaces:
  - HANDLER_REGISTRY["body.diff"] present after _register_handlers()
  - _COMMAND_EVENT_MAP["body.diff"] == "object.changed"
  - InvalidCommandError raised if body.diff dispatched without registration
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Add body.diff command schema, handler, and dispatcher wiring

**Created BodyDiffParams/BodyDiffCommand schemas, handle_body_diff() handler, and wired body.diff into dispatcher and webhook systems.**

## What Happened

Added the `body.diff` operation type as pure backend plumbing:

1. **Schemas** (`schemas.py`): Added `BodyDiffParams(iri, body, diff_text, predicate)` and `BodyDiffCommand` with `Literal["body.diff"]` discriminator. Added `BodyDiffCommand` to the `Command` discriminated union.

2. **Handler** (`handlers/body_diff.py`): New async handler mirrors `handle_body_set()` but stores TWO data triples — `(subject, SEMPKM.bodyDiff, diff_literal)` for the diff text and `(subject, predicate, body_literal)` for the full new body. Materialization is identical to body.set: delete old body, insert new.

3. **Dispatcher** (`dispatcher.py`): Imported `handle_body_diff` and registered as `HANDLER_REGISTRY["body.diff"]`.

4. **Webhook map** (`router.py`): Added `"body.diff": "object.changed"` to `_COMMAND_EVENT_MAP`.

5. **Tests** (`test_body_diff.py`): 8 tests covering handler Operation output (type, data triples, materialization, custom predicate), schema validation, and wiring registration.

## Verification

- `python -c "from app.commands.handlers.body_diff import handle_body_diff; print('OK')"` — ✅ imports
- `python -c "from app.commands.schemas import BodyDiffCommand, BodyDiffParams; print('OK')"` — ✅ imports
- `python -c "from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers; _register_handlers(); assert 'body.diff' in HANDLER_REGISTRY; print('OK')"` — ✅ registered
- `python -c "from app.commands.router import _COMMAND_EVENT_MAP; assert _COMMAND_EVENT_MAP.get('body.diff') == 'object.changed'; print('OK')"` — ✅ mapped
- `python -m pytest tests/test_body_diff.py -v` — ✅ 8/8 passed
- `python -m pytest tests/ -v --tb=short` — ✅ 917 passed, 0 failures (no regressions)

### Slice-level verification (partial — T01 is intermediate):
- `test_body_diff.py`: ✅ handler produces correct Operation, data triples, materialization — PASS
- Remaining slice checks (save_body routing, event detail, compensation, backward compat) — expected to pass after T02/T03

## Diagnostics

- **Inspect handler registration:** `python -c "from app.commands.dispatcher import HANDLER_REGISTRY, _register_handlers; _register_handlers(); print(list(HANDLER_REGISTRY.keys()))"`
- **Inspect webhook mapping:** `python -c "from app.commands.router import _COMMAND_EVENT_MAP; print(_COMMAND_EVENT_MAP)"`
- **Failure shape:** Dispatching `body.diff` without registration raises `InvalidCommandError("Unknown command type: body.diff")` → 400 JSON response

## Deviations

None.

## Known Issues

- Worktree `.venv` has no packages installed — must use main repo venv at `/home/james/Code/SemPKM/backend/.venv/bin/python` with `PYTHONPATH` override for verification commands.

## Files Created/Modified

- `backend/app/commands/handlers/body_diff.py` — new handler for body.diff operations
- `backend/app/commands/schemas.py` — added BodyDiffParams, BodyDiffCommand, updated Command union
- `backend/app/commands/dispatcher.py` — registered body.diff handler
- `backend/app/commands/router.py` — added body.diff to webhook event map
- `backend/tests/test_body_diff.py` — 8 unit tests for handler, schema, and wiring
- `.gsd/milestones/M012/slices/S02/S02-PLAN.md` — added diagnostic verification steps, marked T01 done
- `.gsd/milestones/M012/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section
