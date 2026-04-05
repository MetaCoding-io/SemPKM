# S03: TBox Dashboards & Workflows — PPV Operating System — UAT

**Milestone:** M047
**Written:** 2026-04-05T00:12:29.225Z

# S03 UAT — TBox Dashboards & Workflows

## Preconditions
- PPV model v2 with manifest_version "2.0" available in models/ppv/
- Backend running with DashboardService and WorkflowService wired
- S01 infrastructure (source_model column, TBox lifecycle) in place
- S02 ontology (ViewSpecs, PillarScore, reviews) installed

## Test Cases

### TC-01: PPV Dashboard Content Validation
1. Load `models/ppv/dashboards/ppv.json` and parse as JSON
2. Verify exactly 5 dashboards with names: "Action Items", "Life Dashboard", "Projects Board", "Goals Overview", "Review Hub"
3. Verify each dashboard has a `blocks` array with ≥1 block
4. Verify all blocks have valid gridstack positions (x: 0-11, y ≥ 0, w: 1-12, h ≥ 1, x+w ≤ 12)
5. **Expected:** All 5 dashboards present with valid block layouts

### TC-02: PPV Workflow Content Validation
1. Load `models/ppv/workflows/ppv.json` and parse as JSON
2. Verify exactly 5 workflows with names: "Daily Check-in", "Weekly Review", "Monthly Review", "Quarterly Review", "Yearly Review"
3. Verify each workflow has a `steps` array with ≥1 step
4. Verify step types are one of: "view", "dashboard", "form"
5. Verify dashboard steps use `dashboard_name` (not `dashboard_id`) — resolution happens at install time
6. **Expected:** All 5 workflows present with valid step structures

### TC-03: Manifest Entrypoints
1. Load `models/ppv/manifest.yaml` and parse
2. Verify `entrypoints.dashboards` equals "dashboards/ppv.json"
3. Verify `entrypoints.workflows` equals "workflows/ppv.json"
4. **Expected:** Both entrypoints present and pointing to correct files

### TC-04: Dashboard Name Resolution at Install Time
1. Install PPV v2 model (triggers TBox lifecycle)
2. After install, list workflows sourced from PPV
3. For each workflow step with type "dashboard", verify `dashboard_id` is present (UUID format)
4. Verify `dashboard_name` key has been removed from resolved steps
5. **Expected:** All dashboard steps resolved to UUIDs

### TC-05: Unresolved Dashboard Name Degraded Mode
1. Create a test model with a workflow step referencing `dashboard_name: "Nonexistent Dashboard"`
2. Install the model
3. Verify install succeeds (no exception)
4. Verify the step still has `dashboard_name` (not resolved) — degraded but functional
5. **Expected:** Warning logged, install completes, step retains unresolved name

### TC-06: Seed Workflows Trimmed
1. Import `SEED_WORKFLOWS` from `app.dashboard.seed`
2. Verify exactly 1 entry
3. Verify the entry name is "Create & Review"
4. Verify no PPV-specific references (no "ppv:", no "Weekly Review", no "Monthly Review")
5. **Expected:** Only generic workflow remains in seed data

### TC-07: Install + Explorer Visibility
1. Install PPV v2 model as authenticated user
2. Open workspace explorer
3. Verify 5 dashboards appear in the DASHBOARDS section (tagged as model-sourced if UI supports it)
4. Verify 5 workflows appear in the WORKFLOWS section
5. **Expected:** All 10 surfaces visible in workspace

### TC-08: Uninstall Cleanup
1. With PPV installed (from TC-07), uninstall PPV
2. Verify all 5 model-sourced dashboards are removed
3. Verify all 5 model-sourced workflows are removed
4. Verify user-created dashboards/workflows (if any) are NOT removed
5. **Expected:** Clean removal of model-sourced surfaces only

### TC-09: Action Items Dashboard Block Types
1. Open the "Action Items" dashboard after PPV install
2. Verify stat-card blocks render (may show 0 counts if no data)
3. Verify view-embed blocks reference valid ViewSpec IRIs
4. **Expected:** Dashboard layout renders with correct block types

### TC-10: Weekly Review Workflow Steps
1. Launch "Weekly Review" workflow after PPV install
2. Verify first step is a dashboard step (resolved to Action Items dashboard UUID)
3. Verify workflow includes view steps, form steps, and dashboard steps
4. Step through at least the first step
5. **Expected:** Workflow navigable with correct step types and resolved dashboard references
