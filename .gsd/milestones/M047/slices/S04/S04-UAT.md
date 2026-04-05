# S04: Seed Data Update & E2E Verification — UAT

**Milestone:** M047
**Written:** 2026-04-05T00:33:20.038Z

## UAT: Seed Data Update & E2E Verification

### Preconditions
- Docker test stack running with PPV model files volume-mounted at `/app/models/ppv`
- PPV model NOT currently installed (or test handles pre-clean)
- Playwright test environment configured (`e2e/` directory with dependencies installed)

---

### Test 1: PPV Seed Data Completeness

**Steps:**
1. Open `models/ppv/seed/ppv.jsonld` and parse as JSON
2. Count instances by `@type`
3. Verify GuidingPrinciples instance exists with all 7 fields: `dcterms:title`, `ppv:values`, `ppv:purpose`, `ppv:meaning`, `ppv:manifestation`, `ppv:foundationalStatement`, `ppv:guidingWord`
4. Verify 3 PillarScore instances exist, each with `ppv:score` (integer 1-10), `ppv:pillar` (valid pillar IRI), `ppv:weeklyReview` (valid review IRI)
5. Verify WeeklyReview has `ppv:wins`, `ppv:challenges`, `ppv:supportingPriorities`
6. Verify MonthlyReview has `ppv:biggestWins`, `ppv:biggestChallenges`, `ppv:focusAreas`, `ppv:habitsToAdjust`
7. Verify QuarterlyReview has `ppv:accomplishments`, `ppv:disappointments`, `ppv:whatWorked`, `ppv:whatDidntWork`, `ppv:howToImprove`, `ppv:annualVisionNotes`
8. Verify YearlyReview has `ppv:intentionWord`, `ppv:yearTheme`

**Expected:** 35 total instances across 12 types. All enriched fields present. All IRI cross-references point to existing seed instance IDs.

---

### Test 2: PPV v2 E2E Lifecycle — Install & Dashboard Verification

**Steps:**
1. Run pre-clean: `DELETE /api/models/ppv` (ignore 404/409)
2. Install PPV: `POST /admin/models/install` with form data `model_path=/app/models/ppv`
3. Assert install succeeds (200 response)
4. `GET /api/dashboard` — filter results for PPV dashboard names
5. Verify at least 5 PPV dashboards exist: Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub

**Expected:** All 5 dashboards created during install. Each has a valid UUID id, name, and description.

---

### Test 3: PPV v2 E2E Lifecycle — Workflow Verification

**Steps:**
1. (Continuing from Test 2 — PPV installed)
2. `GET /api/workflow` — filter results for PPV workflow names
3. Verify at least 5 PPV workflows exist: Daily Check-in, Weekly Review, Monthly Review, Quarterly Review, Yearly Review

**Expected:** All 5 workflows created during install. Each has a valid UUID id, name, step_count > 0.

---

### Test 4: PPV v2 E2E Lifecycle — Dashboard UI Rendering

**Steps:**
1. Navigate to `/browser/` and wait for workspace to load
2. Open the first PPV dashboard (e.g., Action Items) via `openDashboardTab(page, id, name)`
3. Wait for `.grid-stack` selector to appear (up to 30s)

**Expected:** Dashboard tab opens in dockview. GridStack container renders with dashboard widget layout.

---

### Test 5: PPV v2 E2E Lifecycle — Workflow UI Rendering

**Steps:**
1. (Continuing from Test 4 — workspace open)
2. Launch a PPV workflow via `window.SemPKM.openWorkflowTab(id, name)`
3. Wait for workflow runner content (`.workflow-runner` or `.workflow-step-content`)

**Expected:** Workflow tab opens. Runner UI renders with step navigation.

---

### Test 6: PPV v2 E2E Lifecycle — Uninstall Handling

**Steps:**
1. `DELETE /api/models/ppv`
2. If 200: verify dashboards and workflows removed via API queries
3. If 409: verify model still listed (seed data blocks removal — expected behavior)
4. If 404: model was already removed — acceptable

**Expected:** Either clean uninstall (200 + surfaces removed) or graceful 409 with model intact. No crashes or unhandled errors.

---

### Test 7: User Guide Chapter

**Steps:**
1. Verify `docs/guide/50-ppv-model.md` exists and is non-empty
2. Verify `docs/guide/README.md` contains a link to `50-ppv-model.md`
3. Verify `docs/guide/index.html` contains a sidebar entry for `50-ppv-model.md`
4. Verify `backend/app/shell/router.py` GUIDE_SECTIONS list includes `50-ppv-model.md`
5. Open the guide chapter and verify it covers: 12 types, 5 dashboards, 5 workflows, review system, installation, seed data

**Expected:** Guide chapter is substantive (not a stub). All three index files reference it. In-app docs page would render the chapter correctly.

---

### Edge Cases

- **Re-install idempotency:** Running the E2E test twice should work — pre-clean handles leftover state
- **Seed data IRI integrity:** Every `ppv:pillar`, `ppv:weeklyReview`, and similar cross-reference in seed data points to an IRI that exists in the same file
- **PillarScore score range:** All scores are integers between 1 and 10 inclusive
