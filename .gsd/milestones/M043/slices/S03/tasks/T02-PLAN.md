---
estimated_steps: 15
estimated_files: 6
skills_used: []
---

# T02: Fine-grained API token scopes with enforcement middleware

1. Add scope field to ApiToken model in backend/app/auth/models.py:
   - scope: str (comma-separated, default='*' for full access)
   - Define scope constants: 'sparql:read', 'sparql:write', 'objects:read', 'objects:write', 'models:admin', 'users:admin', 'commands:execute', 'copilot:use', '*'

2. Create Alembic migration: ADD COLUMN scope TEXT DEFAULT '*' to api_tokens table.

3. Update token creation endpoint in backend/app/auth/router.py:
   - Accept optional scope parameter in create token request body
   - Default to '*' if not specified
   - Validate scope values against allowed set

4. Add scope enforcement:
   - Create a scope_required() dependency factory in backend/app/auth/dependencies.py
   - For token-authenticated requests: check if any of the token's scopes match the required scope (wildcard '*' always matches)
   - For session-authenticated requests: bypass scope check (sessions inherit full role permissions)
   - Add scope_required() to key endpoints: SPARQL router (sparql:read), commands router (commands:execute), copilot router (copilot:use), objects mutation endpoints (objects:write), admin model endpoints (models:admin)

5. Update token creation UI endpoint to accept and display scope choices.

Unit tests: verify scoped token gets 403 on out-of-scope endpoint, verify wildcard token works everywhere, verify session auth bypasses scope check.

## Inputs

- `.gsd/milestones/M042/slices/S01/S01-FINDINGS.md`

## Expected Output

- `backend/app/auth/models.py`
- `backend/app/auth/dependencies.py`
- `backend/app/auth/router.py`
- `backend/migrations/versions/xxx_add_api_token_scope.py`

## Verification

cd backend && .venv/bin/python -m pytest tests/ -v -x -k 'token or scope or auth' --timeout=60
