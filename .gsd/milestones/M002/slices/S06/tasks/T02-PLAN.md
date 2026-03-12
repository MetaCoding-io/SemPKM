---
estimated_steps: 5
estimated_files: 4
---

# T02: Create dual-instance docker-compose and lifecycle scripts

**Slice:** S06 — Federation Bug Fix & Dual-Instance Testing
**Milestone:** M002

## Description

Federation cannot be tested with a single instance. This task creates a `docker-compose.federation-test.yml` that stands up two complete SemPKM stacks (each with its own triplestore, API backend, nginx frontend, and data volumes) on a shared Docker network. It also creates lifecycle scripts mirroring the existing `e2e/scripts/` pattern for the federation stack: start, wait-for-healthy, and stop.

Key requirements: each instance must have its own `BASE_NAMESPACE`, `APP_BASE_URL` set to the nginx service name URL (so cross-instance WebID resolution works within the Docker network), distinct port mappings for external access (3911/8911 for A, 3912/8912 for B), and separate volumes/databases to avoid any state leakage.

## Steps

1. Create `docker-compose.federation-test.yml` based on `docker-compose.test.yml` pattern:
   - Instance A: `triplestore-a` (port 8911 internal 8080), `api-a` (port 8911→8000 mapped, `APP_BASE_URL=http://frontend-a:80`, `BASE_NAMESPACE=https://instance-a.test/data/`, `SECRET_KEY=fed-test-key-a`), `frontend-a` (port 3911→80)
   - Instance B: `triplestore-b` (port 8912 internal 8080), `api-b` (port 8912→8000 mapped, `APP_BASE_URL=http://frontend-b:80`, `BASE_NAMESPACE=https://instance-b.test/data/`, `SECRET_KEY=fed-test-key-b`), `frontend-b` (port 3912→80)
   - Shared network `sempkm-federation` for cross-instance HTTP
   - Separate named volumes: `rdf4j_fed_a_data`, `sempkm_fed_a_data`, etc.
   - Health checks on triplestore and API services matching existing pattern

2. Create `e2e/scripts/start-federation-env.sh`:
   - Tear down any existing federation stack: `docker compose -f docker-compose.federation-test.yml down -v`
   - Build and start: `docker compose -f docker-compose.federation-test.yml up -d --build`
   - Call `wait-for-federation.sh`

3. Create `e2e/scripts/wait-for-federation.sh`:
   - Poll both `http://localhost:3911/api/health` and `http://localhost:3912/api/health`
   - Use same exponential backoff pattern as `wait-for-healthy.sh` (max 20 attempts)
   - Fail if either instance doesn't become healthy

4. Create `e2e/scripts/stop-federation-env.sh`:
   - `docker compose -f docker-compose.federation-test.yml down -v`

5. Test the full lifecycle: start → wait → verify both health endpoints → stop.

## Must-Haves

- [ ] `docker-compose.federation-test.yml` defines 6 services (2× triplestore, api, frontend)
- [ ] Each instance has its own `BASE_NAMESPACE`, `APP_BASE_URL`, `SECRET_KEY`, volumes
- [ ] Both instances are on the same Docker network for cross-instance HTTP
- [ ] Port mappings don't conflict with dev (3000/8001) or test (3901/8901) stacks
- [ ] `start-federation-env.sh` tears down, builds, starts, and waits
- [ ] `wait-for-federation.sh` verifies both instances are healthy
- [ ] Both instances respond to `curl /api/health` after startup

## Verification

- `e2e/scripts/start-federation-env.sh` completes without error
- `curl -sf http://localhost:3911/api/health` returns OK
- `curl -sf http://localhost:3912/api/health` returns OK
- `e2e/scripts/stop-federation-env.sh` cleans up all containers and volumes

## Observability Impact

- Signals added/changed: None — Docker health checks are the diagnostic surface
- How a future agent inspects this: `docker compose -f docker-compose.federation-test.yml logs api-a` or `api-b`; health endpoints at `:3911/api/health` and `:3912/api/health`
- Failure state exposed: Docker health check status per-service; `wait-for-federation.sh` prints attempt count and fails with clear error message

## Inputs

- `docker-compose.test.yml` — template for isolated test stack (volume naming, health checks, env vars)
- `e2e/scripts/start-test-env.sh`, `wait-for-healthy.sh` — patterns for lifecycle scripts
- S06-RESEARCH.md — networking requirements: `APP_BASE_URL` must use Docker service names for cross-instance resolution

## Expected Output

- `docker-compose.federation-test.yml` — dual-instance compose file
- `e2e/scripts/start-federation-env.sh` — federation stack start script
- `e2e/scripts/wait-for-federation.sh` — dual-health wait script
- `e2e/scripts/stop-federation-env.sh` — federation stack teardown script
