---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T01: Fix scheduler datetime bug and add APP_BASE_URL to test compose

Fix two backend bugs that prevent all app subprocesses from working in the test container:

1. **Scheduler naive/aware datetime crash** — `backend/app/apps/scheduler.py` line 257: `now - last_run.started_at` crashes with TypeError because `now` is timezone-aware (UTC) but `last_run.started_at` from SQLite is naive. Apply the same pattern from Knowledge entry about SQLite naive datetimes: normalize `started_at` before subtraction.

2. **APP_BASE_URL missing** — `docker-compose.test.yml` api service environment block has no `APP_BASE_URL`. The default in `backend/app/main.py` is `http://localhost:4000` which is wrong inside the test container (the API listens on port 8000). Add `APP_BASE_URL: http://localhost:8000` to the api service environment.

## Inputs

- ``backend/app/apps/scheduler.py` — has datetime bug at line 257`
- ``docker-compose.test.yml` — missing APP_BASE_URL env var`
- ``backend/app/main.py` — reference for APP_BASE_URL default behavior (lines 398-404)`

## Expected Output

- ``backend/app/apps/scheduler.py` — datetime normalization fix applied`
- ``docker-compose.test.yml` — APP_BASE_URL added to api service environment`

## Verification

cd backend && python -c "import ast; ast.parse(open('app/apps/scheduler.py').read())" && grep -q 'APP_BASE_URL' ../docker-compose.test.yml && echo 'PASS'
