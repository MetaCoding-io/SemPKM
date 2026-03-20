---
id: T01
parent: S02
milestone: M025
provides:
  - seed-demo-data.py script with 4 phases (model install, cross-model edges, markdown bodies, verification)
key_files:
  - scripts/seed-demo-data.py
key_decisions:
  - Used direct handler imports (handle_edge_create, handle_body_set) + EventStore.commit() rather than building Operations manually — leverages existing tested code
  - 12 cross-model edges covering all 5 possible model pairs (BPKM↔CRM, BPKM↔RES, BPKM↔ZK, CRM↔RES, RES↔ZK)
  - 10 markdown bodies across 3 models with 1000-5000 char content each
patterns_established:
  - Container-side seed scripts import app modules directly, bypassing HTTP API (which is blocked by nginx in demo mode)
observability_surfaces:
  - Script prints phased progress with per-item pass/skip/fail counts
  - --verify-only flag runs only SPARQL count verification against existing state
  - Phase 4 verification always runs, printing actual vs expected counts table
duration: 25m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Write seed-demo-data.py with model install, cross-model edges, and markdown bodies

**Created scripts/seed-demo-data.py — 4-phase idempotent seed script installing 3 models, creating 12 cross-model edges across 5 model pairs, and setting 10 rich markdown bodies with SPARQL verification**

## What Happened

Wrote the complete seed script following the task plan. The script has 4 phases:

1. **Install models** — Installs crm, zettelkasten, research (basic-pkm auto-installs at startup). Checks `is_model_installed()` before each install for idempotency.
2. **Create cross-model edges** — 12 edges connecting objects across all 5 unique model pairs (BPKM↔CRM: 3, BPKM↔RES: 3, BPKM↔ZK: 3, CRM↔RES: 1, RES↔ZK: 2). Each edge is checked via SPARQL ASK before creation.
3. **Set markdown bodies** — 10 objects get rich markdown content (1000-5000 chars each) covering architecture notes, meeting notes, Zettelkasten permanent notes, research paper summaries, and concept definitions. Bodies span 3 models (basic-pkm, zettelkasten, research).
4. **Verify** — SPARQL count queries check objects (≥50), models (≥4), edges (≥10), and bodies (≥8).

The script uses direct app module imports (`TriplestoreClient`, `EventStore`, `ModelService`, `handle_edge_create`, `handle_body_set`) rather than HTTP API calls, since nginx blocks POST in demo mode.

## Verification

- ✓ `python3 -c "import ast; ast.parse(open('scripts/seed-demo-data.py').read())"` — valid Python syntax
- ✓ All 4 phases present with progress output headers (`[1/4]` through `[4/4]`)
- ✓ 12 cross-model edges defined, all connecting objects from different model namespaces
- ✓ 10 markdown bodies with multi-paragraph content (1000-5000 chars each)
- ✓ Idempotency: `is_model_installed()` for models, SPARQL ASK `_edge_exists()` for edges, body.set inherently idempotent
- ✓ `--verify-only` flag present, skips phases 1-3

Slice-level verification checks requiring a live Docker stack (exec seed script, curl endpoints, re-run idempotency) are deferred to T02.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('scripts/seed-demo-data.py').read())"` | 0 | ✅ pass | <1s |
| 2 | Content check: 4 phases present | 0 | ✅ pass | <1s |
| 3 | Content check: 12 cross-model edges | 0 | ✅ pass | <1s |
| 4 | Content check: 10 markdown bodies ≥8 | 0 | ✅ pass | <1s |
| 5 | Content check: --verify-only flag | 0 | ✅ pass | <1s |
| 6 | Content check: idempotency patterns | 0 | ✅ pass | <1s |

## Diagnostics

- Run `docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py --verify-only` to check state without modifying data
- Script output shows per-item status (✓ created / ✓ skipped / ✗ failed) and a final summary table with actual vs expected counts
- Each phase catches per-item exceptions and continues — partial failures are visible in output

## Deviations

None — implemented exactly as planned.

## Known Issues

- Live Docker execution not tested (that's T02's scope — wire script into Docker Compose and run against live stack)
- Edge predicates use model-specific predicates (e.g., `bpkm:knows`, `zk:relatedTo`) which is semantically correct but means edge labels in the graph view will depend on label resolution

## Files Created/Modified

- `scripts/seed-demo-data.py` — New: complete 4-phase idempotent seed script (12 edges, 10 bodies, CLI args, verification)
- `.gsd/milestones/M025/slices/S02/tasks/T01-PLAN.md` — Modified: added Observability Impact section
