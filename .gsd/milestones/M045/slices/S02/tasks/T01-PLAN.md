---
estimated_steps: 28
estimated_files: 7
skills_used: []
---

# T01: Docker non-root user and compose security hardening

Harden the backend Dockerfile to run as non-root (UID 1000) and add security_opt/cap_drop to all compose files.

## Steps

1. Edit `backend/Dockerfile`:
   - After the `WORKDIR /app` and before `COPY` commands, add `RUN groupadd -r sempkm && useradd -r -u 1000 -g sempkm sempkm`
   - After `RUN mkdir -p /app/data`, add `RUN chown -R sempkm:sempkm /app/data`
   - Remove `--reload --reload-dir /app/app` from the CMD line (production should not auto-reload)
   - Add `USER sempkm` after all RUN commands that need root (after COPY steps)
   - Final CMD: `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`

2. Edit `docker-compose.yml` (dev):
   - Add to `api` service: `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]`
   - Add to `api` service: `command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]` to restore dev hot-reload
   - Add to `frontend` service: `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]`

3. Edit `docker-compose.test.yml`:
   - Add `security_opt` and `cap_drop` to `api` and `frontend` services

4. Edit `docker-compose.demo.yml`:
   - Add `security_opt` and `cap_drop` to `api` and `frontend` services

5. Edit `docker-compose.cloud.yml`:
   - Add `security_opt` and `cap_drop` to the `frontend` override (api inherits from base compose)

6. Edit `docker-compose.federation-test.yml`:
   - Add `security_opt` and `cap_drop` to `api-a`, `api-b`, `frontend-a`, `frontend-b` services

7. Edit `docker-compose.test-ollama.yml`:
   - Add `security_opt` and `cap_drop` to `api` and `frontend` services

## Must-Haves

- [ ] Dockerfile has `USER sempkm` with UID 1000
- [ ] Dockerfile CMD has no `--reload` flag
- [ ] `/app/data` owned by sempkm user before USER directive
- [ ] All 6 compose files have `security_opt: ["no-new-privileges:true"]` and `cap_drop: [ALL]` on api/frontend services
- [ ] Dev compose restores `--reload` via command override

## Inputs

- ``backend/Dockerfile` — current Dockerfile running as root with --reload in CMD`
- ``docker-compose.yml` — dev compose with no security_opt or cap_drop`
- ``docker-compose.test.yml` — test compose`
- ``docker-compose.demo.yml` — demo compose`
- ``docker-compose.cloud.yml` — cloud compose (frontend override only)`
- ``docker-compose.federation-test.yml` — federation test with api-a, api-b, frontend-a, frontend-b`
- ``docker-compose.test-ollama.yml` — ollama test variant`

## Expected Output

- ``backend/Dockerfile` — non-root user, no --reload in CMD`
- ``docker-compose.yml` — security_opt, cap_drop, command override for dev reload`
- ``docker-compose.test.yml` — security_opt, cap_drop on api + frontend`
- ``docker-compose.demo.yml` — security_opt, cap_drop on api + frontend`
- ``docker-compose.cloud.yml` — security_opt, cap_drop on frontend override`
- ``docker-compose.federation-test.yml` — security_opt, cap_drop on all 4 services`
- ``docker-compose.test-ollama.yml` — security_opt, cap_drop on api + frontend`

## Verification

grep -q 'USER sempkm' backend/Dockerfile && ! grep -q '\-\-reload' backend/Dockerfile | tail -1 && grep -c 'no-new-privileges' docker-compose.yml docker-compose.test.yml docker-compose.demo.yml docker-compose.cloud.yml docker-compose.federation-test.yml docker-compose.test-ollama.yml | grep -v ':0$' | wc -l
