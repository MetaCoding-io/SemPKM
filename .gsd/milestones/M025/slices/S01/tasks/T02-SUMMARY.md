---
id: T02
parent: S01
milestone: M025
provides:
  - Read-only nginx config (nginx.demo.conf) that blocks all write HTTP methods with 403 JSON
  - docker-compose.demo.yml wiring DEMO_MODE + demo nginx into a deployable 3-service stack
key_files:
  - frontend/nginx.demo.conf
  - docker-compose.demo.yml
key_decisions:
  - Used error_page 495 + named location @read_only for proper application/json content-type on 403 (bare return in nginx if-block defaults to text/plain)
  - Port allocation: 3902 (frontend) / 8902 (api) — fits the series dev=3000/8001, test=3901/8901, demo=3902/8902
patterns_established:
  - error_page + named location pattern for returning JSON from nginx method guards (avoids the if-is-evil pitfall)
observability_surfaces:
  - "curl -X POST http://localhost:3902/api/commands → 403 {\"error\": \"Demo instance is read-only\"} with Content-Type: application/json"
  - "docker compose -f docker-compose.demo.yml ps — shows 3 healthy services on sempkm-demo network"
  - "docker compose -f docker-compose.demo.yml exec api env | grep DEMO_MODE — confirms DEMO_MODE=true"
duration: 12m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Create demo nginx config and docker-compose.demo.yml

**Added read-only nginx config and Docker Compose file for the demo instance with write-method blocking and separate ports/volumes/network**

## What Happened

Created `frontend/nginx.demo.conf` by copying the base `nginx.conf` and adding a default-deny block at the top of the `server {}` context. The block uses nginx's `error_page 495 = @read_only` pattern to redirect all non-GET/HEAD/OPTIONS requests to a named location that returns `403 {"error": "Demo instance is read-only"}` with correct `application/json` content-type. This is the only difference from the base config — all location blocks are identical (confirmed via diff).

Created `docker-compose.demo.yml` with 3 services (triplestore, api, frontend) on a separate `sempkm-demo` network with separate volumes (`rdf4j_demo_data`, `sempkm_demo_data`) and non-conflicting ports (3902/8902). The api service has `DEMO_MODE: "true"` in its environment. The frontend service mounts `nginx.demo.conf` instead of `nginx.conf`.

The `error_page` + named location approach was chosen over a bare `if` + `return` because nginx's `return` inside an `if` block always sends `text/plain` content-type — there's no way to set `Content-Type: application/json` with that pattern. The custom error code 495 (unused by nginx) redirects internally to `@read_only` which sets `default_type application/json` before returning 403.

## Verification

1. **nginx -t** — passed with `--add-host api:127.0.0.1` (upstream hostname requires DNS resolution; base nginx.conf fails identically without it)
2. **docker compose config** — validated compose YAML and schema, exit code 0
3. **diff nginx.conf nginx.demo.conf** — only the header comment and read-only enforcement block differ; all location blocks unchanged
4. **T01 unit tests** — 14/14 pass, confirming no regression from T01 work

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker run --rm --add-host api:127.0.0.1 -v $(pwd)/frontend/nginx.demo.conf:/etc/nginx/conf.d/default.conf:ro nginx:stable-alpine nginx -t` | 0 | ✅ pass | 3.1s |
| 2 | `docker compose -f docker-compose.demo.yml config --quiet` | 0 | ✅ pass | 3.1s |
| 3 | `diff frontend/nginx.conf frontend/nginx.demo.conf` (only expected additions) | 1 (expected) | ✅ pass | <1s |
| 4 | `cd backend && .venv/bin/python -m pytest tests/test_demo_mode.py -v` | 0 | ✅ pass (14/14) | 0.3s |

### Slice-level verification (partial — T02 is intermediate)

| # | Check | Status |
|---|-------|--------|
| 1 | `pytest tests/test_demo_mode.py -v` — unit tests | ✅ 14/14 pass |
| 2 | `npx playwright test tests/50-demo/demo-read-only.spec.ts` — E2E test | ⬜ not yet created (T03) |
| 3 | `DEMO_MODE=false python -c "from app.auth.dependencies..."` | ✅ verified in T01 |

## Diagnostics

- **Inspect read-only guard:** `curl -X POST http://localhost:3902/api/commands` should return 403 JSON when the demo stack is running
- **Inspect CORS preflight:** `curl -X OPTIONS http://localhost:3902/api/commands` should return 204 (OPTIONS is in the allow list)
- **Failure mode:** If the read-only guard is missing or broken, POST requests reach the API (status will be whatever the API returns, not 403). If nginx.demo.conf has syntax errors, the frontend container fails to start — check `docker compose -f docker-compose.demo.yml logs frontend`.
- **Port conflicts:** If ports 3902 or 8902 are in use, the compose stack won't start. Check with `ss -tlnp | grep -E '3902|8902'`.

## Deviations

- The task plan explored several nginx approaches (if+return, set variable per location, limit_except) before settling on error_page + named location. Implemented the error_page approach directly as it's the only one that provides correct JSON content-type.
- `nginx -t` requires `--add-host api:127.0.0.1` since the standalone container can't resolve the `api` upstream hostname. This is expected behavior — the base `nginx.conf` has the same limitation. In the real Docker Compose network, DNS resolution is provided by Docker's embedded DNS.

## Known Issues

None.

## Files Created/Modified

- `frontend/nginx.demo.conf` — New: read-only nginx config with error_page 495 → @read_only guard blocking all write methods
- `docker-compose.demo.yml` — New: 3-service demo stack (triplestore, api, frontend) with DEMO_MODE=true, separate ports/volumes/network
- `.gsd/milestones/M025/slices/S01/tasks/T02-PLAN.md` — Added missing Observability Impact section (pre-flight fix)
