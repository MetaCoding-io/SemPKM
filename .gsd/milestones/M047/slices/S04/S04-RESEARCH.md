# S04 Research: Seed Data Update & E2E Verification

## Summary

This is straightforward work: (1) add GuidingPrinciples and PillarScore instances to the PPV seed data file, (2) add enriched review properties to existing review instances, and (3) write an E2E test that installs PPV v2, verifies dashboards/workflows exist, opens a dashboard, launches a workflow, uninstalls, and verifies cleanup. All patterns are established — the codebase has existing model install E2E tests, dashboard/workflow API endpoints, and dockview helpers.

## Recommendation

Three tasks:
1. **Seed data update** — Add GuidingPrinciples + PillarScore instances to `models/ppv/seed/ppv.jsonld`, add enriched review fields to existing review instances. Quick JSON-LD editing.
2. **E2E test** — New spec at `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts` testing install → dashboard/workflow verification → open dashboard → launch workflow → uninstall → verify cleanup.
3. **User guide** — New chapter `docs/guide/50-ppv-model.md` documenting PPV v2 features (dashboards, workflows, review system). Update `docs/guide/README.md`, `docs/guide/index.html`, and `backend/app/templates/guide.html` (all three must stay in sync per KNOWLEDGE.md).

## Implementation Landscape

### Seed Data (models/ppv/seed/ppv.jsonld)

**Current state:** 377 lines, contains 3 PillarGroups, 3 Pillars, 5 ValueGoals, 5 GoalOutcomes, 4 Projects, 7 ActionItems, and 1 each of Weekly/Monthly/Quarterly/YearlyReview. No GuidingPrinciples, no PillarScore, no enriched review fields.

**What to add:**

1. **GuidingPrinciples instance** (`ppv:seed-guiding-principles`):
   - `dcterms:title`, `ppv:values`, `ppv:purpose`, `ppv:meaning`, `ppv:manifestation`, `ppv:foundationalStatement`, `ppv:guidingWord`
   - All `xsd:string` fields per the SHACL shape

2. **PillarScore instances** — 3 scores linked to the existing `ppv:seed-review-week-mar3` weekly review and the 3 existing pillars (`ppv:seed-pillar-health`, `ppv:seed-pillar-career`, `ppv:seed-pillar-relationships`):
   - Each has: `dcterms:title`, `ppv:score` (xsd:integer 1-10), `ppv:wentWell`, `ppv:needsAttention`, `ppv:weeklyReview` (→ `ppv:seed-review-week-mar3`), `ppv:pillar` (→ respective pillar), `dcterms:created`

3. **Enriched review fields** on existing review instances:
   - WeeklyReview (`ppv:seed-review-week-mar3`): add `ppv:wins`, `ppv:challenges`, `ppv:supportingPriorities`
   - MonthlyReview (`ppv:seed-review-march-2026`): add `ppv:biggestWins`, `ppv:biggestChallenges`, `ppv:focusAreas`, `ppv:habitsToAdjust`
   - QuarterlyReview (`ppv:seed-review-q1-2026`): add `ppv:accomplishments`, `ppv:disappointments`, `ppv:whatWorked`, `ppv:whatDidntWork`, `ppv:howToImprove`, `ppv:annualVisionNotes`
   - YearlyReview (`ppv:seed-review-yearly-2026`): add `ppv:intentionWord`, `ppv:yearTheme`

**james-life.jsonld** — Roadmap mentions "fill in Career and Mental Health pillars" and adding GuidingPrinciples + PillarScore. This file already has 9 pillars including Career and Mental Health. Adding GuidingPrinciples + PillarScore instances here too, plus enriched review fields on its reviews. However, this file is NOT loaded by the manifest (manifest points to `seed/ppv.jsonld`), so it's personal seed data that needs manual loading. Keep changes here minimal — focus on the standard ppv.jsonld which is what E2E tests will exercise.

### E2E Test Structure

**Directory:** `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts`

**Test flow (single consolidated test to stay within rate limits):**

1. **Pre-clean:** Try to remove PPV model if installed from prior run (best-effort)
2. **Install PPV v2:** `POST /api/models/install` with `{"path": "/app/models/ppv"}` — use API endpoint (JSON), not admin htmx form
3. **Verify model installed:** `GET /api/models` → confirm PPV appears in the list
4. **Verify dashboards created:** `GET /api/dashboard` → confirm 5 PPV dashboards exist by name (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub)
5. **Verify workflows created:** `GET /api/workflow` → confirm 5 PPV workflows exist by name (Daily Check-in, Weekly Review, Monthly Review, Quarterly Review, Yearly Review) plus 1 generic "Create & Review" from seed.py = 6 total
6. **Open a dashboard:** Navigate to workspace, use `openDashboardTab(id, name)` helper for the first dashboard, wait for `.grid-stack` to appear
7. **Launch a workflow:** Use `window.SemPKM.openWorkflowTab(id, name)` for a workflow, wait for the workflow runner content to load
8. **Uninstall PPV:** `DELETE /api/models/ppv` — will succeed because seed data exists but model removal handles that (actually — need to check if removal is blocked by seed data instances)
9. **Verify dashboards removed:** `GET /api/dashboard` → confirm 0 PPV dashboards remain
10. **Verify workflows removed:** `GET /api/workflow` → confirm only 1 generic workflow remains

**Key API endpoints:**
- `POST /api/models/install` — JSON `{"path": "/app/models/ppv"}`, returns `{"model_id": "ppv", "message": "...", "warnings": []}`
- `DELETE /api/models/{model_id}` — returns `{"model_id": "ppv", "message": "..."}`
- `GET /api/models` — returns `{"models": [...], "count": N}`
- `GET /api/dashboard` — returns `[{"id": "uuid", "name": "...", "description": "...", "layout": "..."}]`
- `GET /api/workflow` — returns `[{"id": "uuid", "name": "...", "description": "...", "step_count": N}]`

**Important constraint — model removal blocked by user data:**
The `ModelService.remove()` checks for user data instances in `urn:sempkm:current`. PPV seed data creates instances (pillars, goals, etc.), which means uninstall will be blocked with 409 Conflict. The existing E2E test (`26-mental-models`) handles this as best-effort cleanup. The S04 test should follow the same pattern — verify install + dashboards/workflows, then attempt uninstall. If uninstall is blocked (409), verify that model-sourced dashboards/workflows are NOT removed (they're tied to the model, not individual instances). The test can still verify the presence assertions.

Actually, re-reading the S01 code: `ModelService.remove()` calls `dashboard_service.delete_by_model(model_id)` and `workflow_service.delete_by_model(model_id)` as part of the removal. But if removal is blocked by user data (409), those calls never run. So the full uninstall lifecycle can only be tested if we can clean up seed data first — which we can't via the SPARQL API (read-only).

**Approach for uninstall verification:** Either (a) accept that uninstall may be blocked and test dashboards/workflows persist, or (b) install PPV v2, check surfaces, then use the admin refresh endpoint to verify TBox surfaces are recreated (refresh = delete + recreate). The refresh path is more reliably testable since it doesn't require removing model instances.

Better approach: Use a minimal test model that has NO seed data — install it with v2 manifest + dashboards/workflows, verify surfaces created, uninstall (no seed data = no 409), verify surfaces removed. But this requires creating a test fixture model. Simpler: just skip the uninstall assertion when 409 is returned.

**Fixtures & helpers needed:**
- `e2e/fixtures/auth.ts` — existing `ownerRequest` fixture for API calls
- `e2e/helpers/dockview.ts` — existing `openDashboardTab(page, id, name)` helper
- `e2e/helpers/wait-for.ts` — existing `waitForWorkspace`, `waitForIdle`
- No new helpers needed — `window.SemPKM.openWorkflowTab(id, name)` called directly via `page.evaluate()`

### User Guide Documentation

**Three files to update (KNOWLEDGE.md — "User guide has THREE files that must stay in sync"):**

1. `docs/guide/50-ppv-model.md` — New chapter: PPV v2 features, dashboards, workflows, review system
2. `docs/guide/README.md` — Add entry to table of contents
3. `docs/guide/index.html` — Add sidebar entry
4. `backend/app/templates/guide.html` — Add `<button>` element for the chapter

Content: Overview of PPV model with dashboards (what each one shows), workflows (daily/weekly/monthly/quarterly/yearly review cadence), new types (PillarScore, GuidingPrinciples), and the install experience.

### Natural Seams

1. **T01: Seed data** — Update `ppv.jsonld` with new instances and enriched fields. Update `james-life.jsonld` similarly. Verify with JSON parse + python type counting.
2. **T02: E2E test** — Write the lifecycle test. Depends on T01 (seed data must exist for realistic testing). Verify by running the test.
3. **T03: User guide** — Write docs. Independent of T01/T02. Verify all 3 files updated.

### Risks & Constraints

- **Model uninstall blocked by seed data** — 409 Conflict prevents full uninstall lifecycle testing. Mitigation: test install + surface creation thoroughly, make uninstall best-effort.
- **E2E test timeout** — Model install involves triplestore writes + seed materialization (3-10s). Dashboard/workflow rendering adds more. Use generous timeout (120s).
- **Dashboard UUID resolution** — Dashboard IDs are dynamically generated UUIDs. The test must query `GET /api/dashboard` to find IDs by name before opening them.
- **Workflow step rendering** — Dashboard steps in workflows reference dashboard UUIDs that were resolved at install time. If resolution failed (unlikely but possible), workflow steps will show errors.

### Verification Strategy

- **T01:** `python3 -c "import json; ..."` — parse ppv.jsonld, count types, verify GuidingPrinciples (1), PillarScore (3), enriched review fields present
- **T02:** `npx playwright test e2e/tests/47-ppv-v2/ --project=chromium` against running test stack
- **T03:** `grep` for new chapter in all 3 guide index files
