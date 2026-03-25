---
estimated_steps: 14
estimated_files: 10
skills_used: []
---

# T03: Migrate likely-exploitable modules and remove all legacy escape functions

1. Migrate likely-exploitable modules:
   - browser/events.py: Replace bare replace('"', '\\"') with safe_literal() from builder
   - browser/favorites.py: Add safe_iri() validation on object_iri in toggle_favorite() before SQL storage
   - api/ai.py: Replace _sparql_escape_str with sparql_escape_string from builder
   - api/router.py: Replace _sparql_escape_str with sparql_escape_string from builder

2. Migrate remaining safe-but-inconsistent modules that use local escape functions:
   - browser/search.py: Replace _sparql_escape
   - browser/workspace.py: Replace _sparql_escape
   - federation/inbox.py: Replace _escape_sparql_string
   - federation/service.py: Replace _escape_sparql
   - services/webhooks.py: Replace _escape_sparql
   - task_templates/service.py: Replace _escape_sparql_string

3. Delete all 9 now-unused local escape functions.
4. Verify zero remaining local escape function definitions via grep.

## Inputs

- `backend/app/sparql/builder.py`

## Expected Output

- `backend/app/browser/events.py`
- `backend/app/browser/favorites.py`
- `backend/app/api/ai.py`
- `backend/app/api/router.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x --timeout=60 && rg 'def _sparql_escape|def _escape_sparql' app/ -g '*.py' | grep -v builder.py | wc -l | xargs test 0 -eq
