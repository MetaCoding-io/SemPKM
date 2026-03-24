---
estimated_steps: 3
estimated_files: 2
skills_used:
  - test
---

# T03: Object Creation Unit Tests + Slice Verification

**Slice:** S03 — AI Personas & Object Creation from Chat
**Milestone:** M035

## Description

Close the slice with unit tests for the object creation extraction logic (detecting structured JSON from LLM responses, generating Command API payloads) and a comprehensive structural verification script proving all S03 deliverables are wired correctly.

## Steps

1. **Write `backend/tests/test_object_creation_chat.py`**: Unit tests covering:
   - Extract create_object JSON from LLM response in fenced ` ```json ` code block → returns parsed dict with action, type, properties
   - Extract create_object from response with mixed prose and JSON → correctly isolates the JSON block
   - Malformed JSON (missing closing brace, invalid syntax) → returns None / graceful handling
   - Missing required fields (no `type`, no `action`) → handled gracefully
   - Valid create_object payload generates correct `object.create` command shape: `{"command": "object.create", "params": {"type": "...", "properties": {...}}}`
   - System prompt contains object creation instructions (check `_build_system_prompt()` output contains "create_object")
   - `_detect_create_object_blocks()` helper returns empty list for text without JSON blocks
   - `_detect_create_object_blocks()` returns correct blocks for text with one or multiple JSON blocks
   Import `_detect_create_object_blocks` from `backend/app/api/copilot.py` and `_build_system_prompt` from `backend/app/copilot/service.py`.

2. **Write `.gsd/milestones/M035/slices/S03/verify-s03.sh`**: Structural verification script with checks:
   - File exists: `backend/app/copilot/personas.py`
   - File exists: `backend/migrations/versions/017_ai_personas.py`
   - File exists: `backend/tests/test_ai_personas.py`
   - File exists: `backend/tests/test_object_creation_chat.py`
   - Import: `from app.copilot.personas import AIPersonaService`
   - Import: `from app.copilot.models import AIPersona`
   - String check: `persona_id` in `backend/app/copilot/schemas.py`
   - String check: `persona_prompt` in `backend/app/copilot/service.py`
   - String check: `create_object` in `backend/app/api/copilot.py`
   - String check: `create_object` in `frontend/static/js/copilot.js`
   - String check: `copilot-persona` in `frontend/static/css/copilot.css`
   - String check: `copilot-create` in `frontend/static/css/copilot.css`
   - String check: persona endpoints: `GET.*personas` or `/personas` in copilot.py
   - Test suite: `pytest tests/test_ai_personas.py` passes
   - Test suite: `pytest tests/test_object_creation_chat.py` passes
   - Regression: `pytest tests/test_copilot_service.py` passes (48 tests)
   - Regression: `pytest tests/test_conversation_service.py` passes (22 tests)

3. **Run all verification and fix any issues**: Execute the verification script and all test suites. If any test or check fails, diagnose and fix. Ensure S01+S02 regression tests still pass.

## Must-Haves

- [ ] test_object_creation_chat.py covers extraction, malformed input, command generation, system prompt content
- [ ] verify-s03.sh checks all deliverables and all test suites pass
- [ ] S01 regression: 48 tests pass
- [ ] S02 regression: 22 tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_object_creation_chat.py -v` — all tests pass
- `bash .gsd/milestones/M035/slices/S03/verify-s03.sh` — all checks pass
- `cd backend && .venv/bin/python -m pytest tests/test_copilot_service.py tests/test_conversation_service.py -v` — 70 tests pass (48 + 22)

## Inputs

- `backend/app/api/copilot.py` — T02 output: `_detect_create_object_blocks()` function to test
- `backend/app/copilot/service.py` — T02 output: `_build_system_prompt()` with object creation instructions
- `backend/app/copilot/personas.py` — T01 output: AIPersonaService
- `backend/app/copilot/models.py` — T01 output: AIPersona model
- `backend/tests/test_ai_personas.py` — T01 output: persona tests (run for regression)

## Observability Impact

This task is test-only — no runtime behavior changes. The new test file (`test_object_creation_chat.py`) validates the detection and parsing signals established in T02. The verification script (`verify-s03.sh`) is a one-shot structural audit tool for future agents to confirm all S03 deliverables are intact. No new log keys, endpoints, or runtime signals are introduced.

## Expected Output

- `backend/tests/test_object_creation_chat.py` — new file: unit tests for create_object extraction and command generation
- `.gsd/milestones/M035/slices/S03/verify-s03.sh` — new file: structural verification script
