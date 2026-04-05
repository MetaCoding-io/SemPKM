# S04: Seed Data Update & E2E Verification

**Goal:** PPV seed data includes GuidingPrinciples and PillarScore instances with enriched review fields. E2E test verifies the full PPV v2 install → dashboard/workflow verification → UI rendering → uninstall lifecycle. User guide documents PPV v2.
**Demo:** After this: E2E test installs PPV v2, verifies dashboards and workflows exist, opens a dashboard, launches a workflow, uninstalls PPV, and verifies surfaces are removed. Seed data includes GuidingPrinciples and PillarScore instances for realistic dashboard rendering.

## Tasks
- [x] **T01: Added 1 GuidingPrinciples, 3 PillarScore instances and enriched reflection fields on all 4 review types to PPV seed data (31→35 instances, 10→12 types)** — The PPV seed file (ppv.jsonld) currently has 31 instances across 10 types but no GuidingPrinciples, no PillarScore, and no enriched review reflection fields. This task adds realistic seed data for the new S02 types so dashboards render with actual data.

## Steps

1. Read `models/ppv/seed/ppv.jsonld` to understand the existing JSON-LD structure and @context prefixes.
2. Add 1 GuidingPrinciples instance (`ppv:seed-guiding-principles`) with all 7 fields from the SHACL shape: `dcterms:title`, `ppv:values`, `ppv:purpose`, `ppv:meaning`, `ppv:manifestation`, `ppv:foundationalStatement`, `ppv:guidingWord`. All are `xsd:string` type. Use realistic August Bradley-style content.
3. Add 3 PillarScore instances linked to the existing weekly review (`ppv:seed-review-week-mar3`) and the 3 existing pillars (`ppv:seed-pillar-health`, `ppv:seed-pillar-career`, `ppv:seed-pillar-relationships`). Each PillarScore needs: `dcterms:title` (string), `ppv:score` (xsd:integer, 1-10), `ppv:wentWell` (string), `ppv:needsAttention` (string), `ppv:weeklyReview` (→ weekly review IRI), `ppv:pillar` (→ pillar IRI), `dcterms:created` (xsd:dateTime).
4. Add enriched reflection fields to 4 existing review instances:
   - WeeklyReview (`ppv:seed-review-week-mar3`): add `ppv:wins`, `ppv:challenges`, `ppv:supportingPriorities` (all xsd:string)
   - MonthlyReview (`ppv:seed-review-march-2026`): add `ppv:biggestWins`, `ppv:biggestChallenges`, `ppv:focusAreas`, `ppv:habitsToAdjust` (all xsd:string)
   - QuarterlyReview (`ppv:seed-review-q1-2026`): add `ppv:accomplishments`, `ppv:disappointments`, `ppv:whatWorked`, `ppv:whatDidntWork`, `ppv:howToImprove`, `ppv:annualVisionNotes` (all xsd:string)
   - YearlyReview (`ppv:seed-review-yearly-2026`): add `ppv:intentionWord`, `ppv:yearTheme` (all xsd:string)
5. Verify JSON is valid and type counts are correct.

## Must-Haves

- [ ] 1 GuidingPrinciples instance with all 7 text fields populated
- [ ] 3 PillarScore instances with scores 1-10, linked to existing pillars and weekly review
- [ ] All 4 review instances have enriched reflection fields matching their SHACL shapes
- [ ] JSON-LD is valid (parseable by python json module)
- [ ] All IRI references use existing seed IDs (no dangling references)

## Verification

- `python3 -c "import json; data=json.load(open('models/ppv/seed/ppv.jsonld')); types={}; [types.__setitem__(i.get('@type','?'), types.get(i.get('@type','?'),0)+1) for i in data['@graph']]; print(types); assert types.get('ppv:GuidingPrinciples')==1; assert types.get('ppv:PillarScore')==3; print('OK')"` exits 0
- `python3 -c "import json; data=json.load(open('models/ppv/seed/ppv.jsonld')); weekly=[i for i in data['@graph'] if i['@type']=='ppv:WeeklyReview'][0]; assert 'ppv:wins' in weekly; print('Enriched fields OK')"` exits 0
  - Estimate: 30m
  - Files: models/ppv/seed/ppv.jsonld
  - Verify: python3 -c "import json; data=json.load(open('models/ppv/seed/ppv.jsonld')); types={}; [types.__setitem__(i.get('@type','?'), types.get(i.get('@type','?'),0)+1) for i in data['@graph']]; assert types.get('ppv:GuidingPrinciples')==1; assert types.get('ppv:PillarScore')==3; print('Seed data OK')"
- [ ] **T02: Write E2E test for PPV v2 install/dashboard/workflow/uninstall lifecycle** — Write a Playwright E2E test that exercises the full PPV v2 lifecycle: install the model, verify dashboards and workflows were created, open a dashboard in the workspace, launch a workflow, then attempt uninstall.

The test uses API endpoints for verification and dockview helpers for UI interaction. Model uninstall will likely return 409 (seed data blocks removal) — handle this gracefully.

## Steps

1. Create `e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts`.
2. Import fixtures: `test, expect, BASE_URL` from `../../fixtures/auth`, `waitForWorkspace, waitForIdle` from `../../helpers/wait-for`, `openDashboardTab` from `../../helpers/dockview`.
3. Write a single consolidated test (to stay within magic-link rate limits) with these phases:
   - **Pre-clean**: Best-effort `DELETE /api/models/ppv` to handle leftover state from prior runs. Ignore 404/409.
   - **Install PPV**: `POST /api/models/install` with `{"path": "/app/models/ppv"}`. Assert 200. The path is the Docker container path (models are volume-mounted at /app/models/).
   - **Verify dashboards**: `GET /api/dashboard` → filter by name for 5 PPV dashboards (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub). Assert count >= 5.
   - **Verify workflows**: `GET /api/workflow` → filter by name for 5 PPV workflows (Daily Check-in, Weekly Review, Monthly Review, Quarterly Review, Yearly Review). Assert count >= 5.
   - **Open dashboard**: Navigate to `/browser/`, wait for workspace, use `openDashboardTab(page, dashboardId, dashboardName)` with the first found PPV dashboard. Wait for `.grid-stack` to be visible.
   - **Launch workflow**: Use `page.evaluate()` to call `window.SemPKM.openWorkflowTab(id, name)` with a found PPV workflow. Wait for workflow runner content (`.workflow-runner` or `.workflow-step-content` selector).
   - **Uninstall attempt**: `DELETE /api/models/ppv`. If 200, verify dashboards/workflows removed. If 409 (blocked by seed data), log and verify model still listed — this is expected behavior.
4. Use generous timeouts (120s for test, 30s for individual waits) since model install involves triplestore writes + seed materialization.
5. Dashboard IDs are dynamic UUIDs — the test must query the list API and find IDs by name before opening.

Key API details:
- `POST /api/models/install` — body: `{"path": "/app/models/ppv"}`, returns `{"model_id": "ppv", "message": "...", "warnings": []}`
- `DELETE /api/models/ppv` — returns 200 on success, 409 if user data exists, 404 if not installed
- `GET /api/dashboard` — returns `[{"id": "uuid", "name": "...", "description": "...", "layout": "..."}]`
- `GET /api/workflow` — returns `[{"id": "uuid", "name": "...", "description": "...", "step_count": N}]`
- All API calls need the auth cookie: `Cookie: sempkm_session=${sessionToken}`
- The session token comes from the `ownerPage` fixture: `const sessionToken = await page.evaluate(() => document.cookie.match(/sempkm_session=([^;]+)/)?.[1]);`

No openWorkflowTab helper exists in dockview.ts. Use `page.evaluate()` directly with `window.SemPKM.openWorkflowTab(id, name)` and then wait for a workflow-related selector.

## Must-Haves

- [ ] Test installs PPV v2 and verifies 5 dashboards + 5 workflows created
- [ ] Test opens a dashboard tab and verifies gridstack renders
- [ ] Test launches a workflow and verifies workflow UI renders
- [ ] Test handles uninstall 409 gracefully (seed data blocks removal)
- [ ] Test is idempotent (pre-clean handles leftover state)

## Verification

- `npx playwright test e2e/tests/47-ppv-v2/ --project=chromium` passes against the running test stack
- If the test stack is not running, verify the test file compiles: `cd e2e && npx tsc --noEmit`
  - Estimate: 1h
  - Files: e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts
  - Verify: cd e2e && npx tsc --noEmit 2>&1 | grep -c 'error' | grep -q '^0$' && echo 'TypeScript compiles OK' || echo 'TypeScript errors found'
- [ ] **T03: Write PPV v2 user guide chapter and update all three index files** — Create the PPV model user guide chapter and update all three index files that must stay in sync (KNOWLEDGE.md rule: 'User guide has THREE files that must stay in sync').

## Steps

1. Create `docs/guide/50-ppv-model.md` with content covering:
   - What the PPV model is (Pillars, Pipelines, Vaults — August Bradley's system)
   - Types included: PillarGroup, Pillar, ValueGoal, GoalOutcome, Project, ActionItem, WeeklyReview, MonthlyReview, QuarterlyReview, YearlyReview, PillarScore, GuidingPrinciples
   - 5 dashboards: Action Items (task management), Life Dashboard (pillar overview), Projects Board (project status), Goals Overview (value goals → outcomes), Review Hub (review navigation)
   - 5 workflows: Daily Check-in, Weekly Review (with pillar scoring), Monthly Review, Quarterly Review, Yearly Review
   - The review system: weekly → monthly → quarterly → yearly hierarchy, pillar scoring, enriched reflection fields
   - Installation: standard model install from admin page
   - Seed data: demo instances provided for exploring before adding own data
2. Update `docs/guide/README.md` — add entry `50. [PPV Model](50-ppv-model.md)` after line 76 (49. Media Scheduler).
3. Update `docs/guide/index.html` — add `<li><a href="#" data-file="50-ppv-model.md">50. PPV Model</a></li>` after the 49. Media Scheduler entry.
4. Update `backend/app/shell/router.py` — add `{"filename": "50-ppv-model.md", "title": "50. PPV Model", "icon": "compass"}` to the GUIDE_SECTIONS chapters list, before the "38. Hosted Demo" entry (which is the last non-appendix chapter).

## Must-Haves

- [ ] `docs/guide/50-ppv-model.md` exists with meaningful content (not a stub)
- [ ] `docs/guide/README.md` references the new chapter
- [ ] `docs/guide/index.html` references the new chapter
- [ ] `backend/app/shell/router.py` GUIDE_SECTIONS includes the new chapter entry

## Verification

- `test -f docs/guide/50-ppv-model.md && echo 'Guide exists'`
- `grep -q '50-ppv-model' docs/guide/README.md && echo 'README OK'`
- `grep -q '50-ppv-model' docs/guide/index.html && echo 'index.html OK'`
- `grep -q '50-ppv-model' backend/app/shell/router.py && echo 'router.py OK'`
  - Estimate: 30m
  - Files: docs/guide/50-ppv-model.md, docs/guide/README.md, docs/guide/index.html, backend/app/shell/router.py
  - Verify: test -f docs/guide/50-ppv-model.md && grep -q '50-ppv-model' docs/guide/README.md && grep -q '50-ppv-model' docs/guide/index.html && grep -q '50-ppv-model' backend/app/shell/router.py && echo 'All 4 files OK'
