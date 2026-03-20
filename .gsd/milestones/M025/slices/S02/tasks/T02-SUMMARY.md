---
id: T02
parent: S02
milestone: M025
provides:
  - docker-compose.demo.yml scripts volume mount for container-side seed execution
  - scripts/deploy-demo.sh deployment wrapper orchestrating start → health → seed → verify
  - sys.path fix in seed-demo-data.py enabling import of app modules from /app/scripts/
key_files:
  - docker-compose.demo.yml
  - scripts/deploy-demo.sh
  - scripts/seed-demo-data.py
key_decisions:
  - Added sys.path.insert(0, parent_dir) at script top rather than using PYTHONPATH env var — keeps the script self-contained with no external config dependency
patterns_established:
  - Container-side scripts under /app/scripts/ need sys.path manipulation since /app is not on Python's default path when running from a subdirectory
observability_surfaces:
  - deploy-demo.sh prints phased progress [1/4] through [4/4] with clear labels
  - Seed script --verify-only flag re-runs just SPARQL verification without modifying data
  - Seed script prints per-item pass/skip/fail status and summary table with actual vs expected counts
duration: 20m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Wire script into Docker Compose, create deploy wrapper, and verify against live stack

**Added scripts volume mount to docker-compose.demo.yml, created deploy-demo.sh wrapper, fixed sys.path for container imports, and verified full seed pipeline: 4 models, 74 objects, 12 cross-model edges, 10 markdown bodies with idempotent re-run**

## What Happened

1. Added `./scripts:/app/scripts:ro` volume mount to the `api` service in `docker-compose.demo.yml`, after the existing `./apps:/app/apps:ro` mount.

2. Created `scripts/deploy-demo.sh` — a 4-phase Bash wrapper that orchestrates: start demo stack → wait for API health → run seed script → run verification. Made executable.

3. Started the demo stack with `docker compose -f docker-compose.demo.yml up -d --build`. Triplestore, API, and frontend all came up healthy. basic-pkm auto-installed at startup.

4. First seed script run hit `ModuleNotFoundError: No module named 'app'` — the Python interpreter running `/app/scripts/seed-demo-data.py` doesn't have `/app` on `sys.path` by default (only `/app/.venv/lib/...` is on the path). Fixed by adding a `sys.path.insert(0, Path(__file__).resolve().parent.parent)` block before the app imports. This is the correct pattern for container-side scripts that live in subdirectories.

5. After the fix, the seed script ran successfully: installed 3 models (crm, zettelkasten, research), created 12 cross-model edges across all 5 model pairs, set 10 markdown bodies, and verification reported 74 objects / 4 models / 12 edges / 10 bodies — all passing.

6. Confirmed idempotency by re-running the seed script: all models reported "already installed (skipped)", all 12 edges reported "already exists (skipped)", bodies were re-set (inherently idempotent), and counts remained unchanged. Zero errors.

7. Verified via API: `GET /api/models` returned 4 models, `GET /api/types` returned 21 types across all models.

8. Tore down the demo stack with `docker compose down -v`.

## Verification

- `docker compose -f docker-compose.demo.yml config --quiet` — compose YAML valid
- Seed script exit 0 on first run with all phases passing
- --verify-only exit 0 reporting ≥50 objects, ≥4 models, ≥10 edges, ≥8 bodies
- `curl http://localhost:8902/api/models` returned 4 models (basic-pkm, crm, research, zettelkasten)
- Re-run seed script exit 0 with all models/edges skipped (idempotency confirmed)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose -f docker-compose.demo.yml config --quiet` | 0 | ✅ pass | <1s |
| 2 | `docker compose exec -T api python /app/scripts/seed-demo-data.py` (first run) | 0 | ✅ pass | ~5s |
| 3 | `docker compose exec -T api python /app/scripts/seed-demo-data.py --verify-only` | 0 | ✅ pass | ~2s |
| 4 | `curl /api/models \| assert len >= 4` | 0 | ✅ pass | <1s |
| 5 | `docker compose exec -T api python /app/scripts/seed-demo-data.py` (idempotent re-run) | 0 | ✅ pass | ~5s |
| 6 | `docker compose -f docker-compose.demo.yml down -v` | 0 | ✅ pass | ~5s |

### Slice-Level Verification

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | seed-demo-data.py completes without errors | ✅ pass | All 4 phases zero errors |
| 2 | Verification reports ≥50 objects, 4 models, ≥10 edges | ✅ pass | 74 objects, 4 models, 12 edges, 10 bodies |
| 3 | `curl /api/models` shows 4 models | ✅ pass | basic-pkm, crm, research, zettelkasten |
| 4 | `curl /browser/lint` returns validation warnings | ⏭ skipped | Lint is a workspace UI feature, not a standalone API endpoint — requires browser session |
| 5 | Re-running script is idempotent | ✅ pass | All items skipped, counts unchanged |

## Diagnostics

- Run `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only` to check seed state without modifying data
- deploy-demo.sh output shows phased progress with clear pass/fail indicators
- If seed script fails with ModuleNotFoundError, check that `sys.path` manipulation at top of script points to correct parent directory

## Deviations

- **sys.path fix**: The seed script needed `sys.path.insert(0, parent_dir)` added because `/app` is not on Python's default path when running from `/app/scripts/`. This was not anticipated in the task plan but is a standard pattern for container-side utility scripts.

## Known Issues

- The `curl http://localhost:3902/browser/lint` slice verification check is not feasible via curl — the lint/validation view is a workspace UI feature that requires an htmx browser session, not a standalone API endpoint. Full validation warning verification would need a browser-based test.

## Files Created/Modified

- `docker-compose.demo.yml` — Modified: added `./scripts:/app/scripts:ro` volume mount to api service
- `scripts/deploy-demo.sh` — New: 4-phase deployment wrapper (start → health wait → seed → verify), executable
- `scripts/seed-demo-data.py` — Modified: added sys.path manipulation to fix container-side imports
