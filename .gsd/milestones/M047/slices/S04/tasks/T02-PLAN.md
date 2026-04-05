---
estimated_steps: 32
estimated_files: 1
skills_used: []
---

# T02: Write E2E test for PPV v2 install/dashboard/workflow/uninstall lifecycle

Write a Playwright E2E test that exercises the full PPV v2 lifecycle: install the model, verify dashboards and workflows were created, open a dashboard in the workspace, launch a workflow, then attempt uninstall.

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

## Inputs

- ``models/ppv/seed/ppv.jsonld` — seed data with GuidingPrinciples and PillarScore instances (from T01)`
- ``models/ppv/dashboards/ppv.json` — 5 dashboard definitions created in S03`
- ``models/ppv/workflows/ppv.json` — 5 workflow definitions created in S03`
- ``e2e/fixtures/auth.ts` — ownerPage/ownerRequest fixtures for authenticated API calls`
- ``e2e/helpers/dockview.ts` — openDashboardTab helper for dashboard UI testing`
- ``e2e/helpers/wait-for.ts` — waitForWorkspace, waitForIdle helpers`
- ``e2e/tests/26-mental-models/mental-model-expansion.spec.ts` — reference pattern for model install/uninstall E2E tests`

## Expected Output

- ``e2e/tests/47-ppv-v2/ppv-v2-lifecycle.spec.ts` — Playwright test covering PPV v2 install → dashboard/workflow verification → UI rendering → uninstall`

## Verification

cd e2e && npx tsc --noEmit 2>&1 | grep -c 'error' | grep -q '^0$' && echo 'TypeScript compiles OK' || echo 'TypeScript errors found'
