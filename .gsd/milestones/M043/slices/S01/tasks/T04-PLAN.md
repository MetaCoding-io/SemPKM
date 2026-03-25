---
estimated_steps: 7
estimated_files: 1
skills_used: []
---

# T04: Exploit regression tests — verify audit payloads are blocked

Create backend/tests/test_sparql_injection_regression.py with exact exploit payloads from the M042 audit:

1. F-006: GET /browser/views/generic/table?type=x>%20.%20?s%20?p%20?o%20}%20%23 → must return 400 or sanitized result (no data leak)
2. F-007: GET /browser/apps/right-pane-sections?iri=x>%20.%20?s%20?p%20?o%20}%20%23 → must return 400 (now also requires auth)
3. F-008: POST /browser/vfs/mounts with crafted group_by_property → must return 400
4. F-009: POST /browser/favorites with crafted object_iri → must return 400 or reject at validation
5. F-010: events.py search with backslash-quote breakout → must not leak data

Tests use FastAPI TestClient with authenticated sessions. Each test verifies the specific payload from the audit finding is rejected.

## Inputs

- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md`
- `.gsd/milestones/M042/M042-SECURITY-FINDINGS.md`

## Expected Output

- `backend/tests/test_sparql_injection_regression.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_sparql_injection_regression.py -v
