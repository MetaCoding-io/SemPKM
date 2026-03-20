---
id: S02
parent: M025
milestone: M025
provides:
  - scripts/seed-demo-data.py — 4-phase idempotent seed script installing 3 models, creating 12 cross-model edges, setting 10 markdown bodies, with SPARQL verification
  - scripts/deploy-demo.sh — deployment wrapper orchestrating start → health → seed → verify
  - docker-compose.demo.yml scripts volume mount for container-side seed execution
requires:
  - slice: S01
    provides: docker-compose.demo.yml with DEMO_MODE=true and nginx.demo.conf write-blocking
affects:
  - S03
key_files:
  - scripts/seed-demo-data.py
  - scripts/deploy-demo.sh
  - docker-compose.demo.yml
key_decisions:
  - D252: Seed script bypasses HTTP auth and nginx write-blocking by running inside the API container via direct Python module imports (TriplestoreClient, EventStore, ModelService) — not HTTP API calls
  - Used direct handler imports (handle_edge_create, handle_body_set) + EventStore.commit() rather than building Operations manually — leverages existing tested code paths
  - 12 cross-model edges covering all 5 possible model pairs (BPKM↔CRM, BPKM↔RES, BPKM↔ZK, CRM↔RES, RES↔ZK)
  - Container-side scripts need sys.path.insert(0, parent_dir) since /app is not on Python's default path when running from /app/scripts/
patterns_established:
  - Container-side seed scripts import app modules directly, bypassing HTTP API (which is blocked by nginx in demo mode)
  - sys.path manipulation block at top of any script under scripts/ that imports from the app package
  - Phased progress output ([1/4]...[4/4]) with per-item pass/skip/fail for operational visibility
observability_surfaces:
  - Seed script prints phased progress with per-item status (✓ created / ✓ skipped / ✗ failed)
  - --verify-only flag runs only SPARQL count verification against existing state without modifying data
  - Phase 4 verification always runs, printing actual vs expected counts table (objects ≥50, models ≥4, edges ≥10, bodies ≥8)
  - deploy-demo.sh prints 4-phase progress [1/4] through [4/4] with clear labels and final URL output
drill_down_paths:
  - .gsd/milestones/M025/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M025/slices/S02/tasks/T02-SUMMARY.md
duration: 45m
verification_result: passed
completed_at: 2026-03-20
---

# S02: Sample data generation script

**Idempotent 4-phase seed script installs 3 models, creates 12 cross-model edges across 5 model pairs, and sets 10 rich markdown bodies — producing 74 interconnected objects visible in the demo instance, verified by SPARQL and API queries against live Docker stack**

## What Happened

T01 wrote the complete `scripts/seed-demo-data.py` — a 4-phase async Python script that transforms a bare demo stack into a richly populated demo instance:

1. **Phase 1: Install models** — Installs crm, zettelkasten, and research models (basic-pkm auto-installs at startup). Each install checked via `is_model_installed()` for idempotency.
2. **Phase 2: Create cross-model edges** — 12 edges connecting objects across all 5 unique model pairs (BPKM↔CRM: 3, BPKM↔RES: 3, BPKM↔ZK: 3, CRM↔RES: 1, RES↔ZK: 2). Each edge checked via SPARQL ASK before creation.
3. **Phase 3: Set markdown bodies** — 10 objects get rich markdown content (1000–5000 chars each) covering architecture notes, meeting notes, Zettelkasten permanent notes, research paper summaries, and concept definitions across 3 models.
4. **Phase 4: Verify** — SPARQL count queries check objects (≥50), models (≥4), edges (≥10), and bodies (≥8).

The script uses direct app module imports (`TriplestoreClient`, `EventStore`, `ModelService`, `handle_edge_create`, `handle_body_set`) rather than HTTP API calls, since nginx blocks POST in demo mode (D252).

T02 wired the script into the Docker deployment:
- Added `./scripts:/app/scripts:ro` volume mount to the api service in `docker-compose.demo.yml`
- Created `scripts/deploy-demo.sh` — a 4-phase Bash wrapper (start → health wait → seed → verify)
- Fixed `ModuleNotFoundError` by adding `sys.path.insert(0, parent_dir)` at the top of the seed script (documented in KNOWLEDGE.md)
- Verified the full pipeline against a live Docker stack: 74 objects, 4 models, 12 edges, 10 bodies — all counts passing
- Confirmed idempotency by re-running the seed script: all models/edges skipped, counts unchanged
- Verified via API: `GET /api/models` returned 4 models, `GET /api/types` returned 21 types

## Verification

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | `python3 -c "import ast; ast.parse(...)"` — valid Python syntax | ✅ pass | Script parses cleanly |
| 2 | Seed script first run completes without errors | ✅ pass | All 4 phases zero errors |
| 3 | Verification reports ≥50 objects, 4 models, ≥10 edges, ≥8 bodies | ✅ pass | 74 objects, 4 models, 12 edges, 10 bodies |
| 4 | `curl /api/models` shows 4 models | ✅ pass | basic-pkm, crm, research, zettelkasten |
| 5 | `curl /api/types` shows types across models | ✅ pass | 21 types returned |
| 6 | Re-running seed script is idempotent | ✅ pass | All models/edges skipped, counts unchanged |
| 7 | `--verify-only` flag works without modifying data | ✅ pass | Only runs Phase 4 SPARQL queries |
| 8 | `docker compose -f docker-compose.demo.yml config --quiet` | ✅ pass | Compose YAML valid |
| 9 | Validation warnings for lint | ⏭ skipped | Lint is workspace UI — requires browser session, deferred to S03 |

## Requirements Advanced

- DEMO-03 (Sample data with cross-model edges) — 74 objects across 4 models with 12 cross-model edges and 10 markdown bodies, verified by SPARQL counts and API queries against live Docker stack. Validation-triggering data included (overdue task from basic-pkm seed, stale contact from CRM seed, unprocessed fleeting note from zettelkasten seed). Not yet validated because browser-level visibility (explorer, graph, table views) is untested — that requires S03's demo tour.

## Requirements Validated

- None — browser-level verification of sample data visibility deferred to S03/S04.

## New Requirements Surfaced

- DEMO-03 — Sample data with cross-model edges (tracked in milestone roadmap, now has concrete proof from execution)

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **sys.path fix** — The seed script needed `sys.path.insert(0, parent_dir)` added because `/app` is not on Python's default path when running from `/app/scripts/`. Not anticipated in the plan but is a standard pattern for container-side utility scripts. Documented in KNOWLEDGE.md for future scripts.

## Known Limitations

- **Validation warnings not browser-verified** — The lint/validation page requires a browser session (htmx-driven workspace UI). Confirming that SHACL-AF rules fire on seed data (overdue task, stale contact, unprocessed note) requires either browser-based E2E testing or direct pyshacl invocation. Deferred to S03.
- **Object count is 74, not 61** — The plan estimated ~61 objects, but the actual count is 74 because model seed data contributes more objects than initially estimated. This exceeds the milestone's "30-50" target, which is fine.
- **Edge labels depend on label resolution** — Cross-model edge predicates use model-specific predicates (e.g., `bpkm:knows`, `zk:relatedTo`) which is semantically correct but means edge labels in the graph view depend on LabelService resolution.

## Follow-ups

- S03 should verify sample data is visible in explorer, graph, and table views during tour development
- S03 should verify SHACL validation warnings fire on seed data via the lint page
- S04 should include the full `deploy-demo.sh` in deployment documentation

## Files Created/Modified

- `scripts/seed-demo-data.py` — New: 4-phase idempotent seed script (~800 lines) with 12 cross-model edges, 10 markdown bodies, CLI args, SPARQL verification
- `scripts/deploy-demo.sh` — New: 4-phase deployment wrapper (start → health → seed → verify), executable
- `docker-compose.demo.yml` — Modified: added `./scripts:/app/scripts:ro` volume mount to api service

## Forward Intelligence

### What the next slice should know
- The demo stack after seeding has 74 objects across 4 models (basic-pkm, crm, zettelkasten, research) with 21 types — significantly more than the originally estimated 61
- Cross-model edges use model-native predicates (bpkm:knows, bpkm:mentions, zk:relatedTo, etc.) — tour steps showing the graph view will see these as edge labels
- Markdown bodies are set on 10 objects across 3 models — these are the best candidates for tour stops showing the object read view
- Validation-triggering data comes from model seed data (overdue task, stale contact, unprocessed fleeting note) — not from the seed script itself. The script creates edges and bodies, not the validation-triggering objects.

### What's fragile
- **sys.path manipulation** — If the script is moved out of `/app/scripts/`, the parent directory calculation breaks. The block at the top of the script must be updated if the script moves.
- **Hardcoded object IRIs in edge definitions** — The seed script references specific objects by their full IRI (e.g., `urn:sempkm:bpkm:alice-johnson`). If model seed data IRIs change in a model version update, edges will silently fail to connect.

### Authoritative diagnostics
- `docker compose -f docker-compose.demo.yml exec -T api python /app/scripts/seed-demo-data.py --verify-only` — prints actual vs expected counts for objects, models, edges, bodies
- `curl http://localhost:8902/api/models | python3 -m json.tool` — confirms all 4 models installed
- `curl http://localhost:8902/api/types | python3 -m json.tool` — confirms types from all models visible

### What assumptions changed
- **Object count higher than planned** — Plan estimated ~61 objects (the number from T01's edge/body definitions), actual count is 74 because model seed data contributes more objects. The milestone target of 30-50 is well exceeded.
- **Lint verification not feasible via curl** — Plan listed `curl /browser/lint` as a verification step, but the lint page is workspace UI requiring a browser session, not a standalone API endpoint.
