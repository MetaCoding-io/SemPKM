---
id: T02
parent: S03
milestone: M025
provides:
  - Phase 4 in seed-demo-data.py — creates demo user row and pre-built demo dashboard with deterministic UUID
  - Dashboard count check in Phase 5 verification
key_files:
  - scripts/seed-demo-data.py
key_decisions:
  - Used `spec_iri` (not `view_iri`) in dashboard block config to match codebase convention in dashboard/router.py
  - Phase numbering: 5 phases (1-3 existing data, 4 new dashboard, 5 verification) — renumbered from 4 to 5 total
patterns_established:
  - SQLAlchemy merge for idempotent user upsert in seed scripts; select-before-insert pattern for dashboard idempotency
observability_surfaces:
  - Phase 4 prints `✓ Demo user ensured (demo@sempkm.app)` and `✓ Demo dashboard created` or `✓ Demo dashboard already exists (skipped)`
  - Phase 5 verification table includes `Dashboards` row with count vs expected ≥1
  - `--verify-only` path includes dashboard count check
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Extend seed script with Phase 4 — create demo dashboard and demo user row

**Added Phase 4 to seed-demo-data.py: creates demo user (UUID 00000000-...) and pre-built Demo Dashboard (UUID aaaaaaaa-bbbb-...) with sidebar-main layout containing table+graph view-embeds for cross-view context filtering**

## What Happened

Extended `scripts/seed-demo-data.py` with a new Phase 4 that creates the demo infrastructure needed for the tour's dashboard step. The implementation:

1. Added imports: `json`, `uuid as _uuid`, `sqlalchemy.select/func`, `User`, `DashboardSpec`, `async_session_factory`
2. Defined well-known UUIDs: `DEMO_USER_UUID` (00000000-...) and `DEMO_DASHBOARD_UUID` (aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee)
3. Wrote `phase_create_dashboard()` async function that:
   - Uses `session.merge()` to upsert a demo user row (email: demo@sempkm.app, role: guest)
   - Checks if dashboard already exists before creating (idempotent)
   - Creates a `DashboardSpec` with `sidebar-main` layout, two view-embed blocks (table emitting context, graph listening to context)
4. Renumbered all phases from /4 to /5 total
5. Added dashboard count to Phase 5 verification table
6. Updated `--verify-only` help text and skip message

Key deviation: The plan specified `view_iri` as the config key for view-embed blocks, but the actual codebase (`dashboard/router.py`) uses `spec_iri`. Used the correct key.

## Verification

- Python syntax check: valid
- Dashboard UUID present in script: confirmed
- Demo Dashboard name present: confirmed
- Demo user email present: confirmed
- sidebar-main layout present: confirmed
- Zero conflict markers across frontend/backend/scripts: confirmed
- All `_print_header` calls consistently use total=5
- Demo Docker stack not running — cannot verify live execution (downstream task will test)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('scripts/seed-demo-data.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `grep "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" scripts/seed-demo-data.py` | 0 | ✅ pass | <1s |
| 3 | `grep "Demo Dashboard" scripts/seed-demo-data.py` | 0 | ✅ pass | <1s |
| 4 | `grep "demo@sempkm.app" scripts/seed-demo-data.py` | 0 | ✅ pass | <1s |
| 5 | `grep "sidebar-main" scripts/seed-demo-data.py` | 0 | ✅ pass | <1s |
| 6 | `grep -rn "^<<<<<<< " frontend/ backend/app/templates/ scripts/ ...` | 0 | ✅ pass | <1s |

### Slice-level verification (partial — T02 is intermediate)

| Check | Status | Notes |
|-------|--------|-------|
| Tour auto-starts | ✅ (T01) | Covered by T01 |
| 7 tour steps without errors | ⏳ | Needs live demo stack |
| localStorage flag | ✅ (T01) | Covered by T01 |
| CTA banner visible | ⏳ | T03 (not yet built) |
| Dashboard exists in explorer | ⏳ | Needs live demo stack + seed run |
| Dashboard renders with data | ⏳ | Needs live demo stack |
| JS syntax tutorials.js | ⚠️ | Slice plan uses `ast.parse` which is Python-only — JS file can't be validated this way |
| Zero conflict markers | ✅ | 0 conflicts found |

## Diagnostics

- **Seed script Phase 4 output:** Look for `[4/5] Creating Demo Dashboard` header followed by user/dashboard status messages
- **Verification table:** Phase 5 includes `Dashboards` row showing actual count — 0 means Phase 4 failed
- **Direct DB inspection:** `SELECT * FROM dashboard_specs WHERE id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'`
- **Idempotency test:** Re-running seed script should show `Demo dashboard already exists (skipped)`

## Deviations

- Used `spec_iri` instead of plan's `view_iri` — matches actual codebase convention in `backend/app/dashboard/router.py`
- Plan's phase numbering was self-contradictory (vacillated between 5 and 6 total phases) — settled on 5 total which matches the simplest interpretation

## Known Issues

- Slice plan's JS syntax check (`ast.parse` on tutorials.js) is invalid — Python's `ast` module only parses Python, not JavaScript. This is a pre-existing plan error, not something introduced by this task.
- Live demo stack execution not verified (stack not running) — will be tested when demo stack is brought up for integration testing.

## Files Created/Modified

- `scripts/seed-demo-data.py` — Added Phase 4 (demo user + dashboard creation), dashboard count in Phase 5 verification, renumbered phases to /5 total, added imports for json, uuid, SQLAlchemy session/models
- `.gsd/milestones/M025/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
