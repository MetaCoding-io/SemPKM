# S03: TBox Dashboards & Workflows — PPV Operating System

**Goal:** PPV model ships 5 dashboards and 5 workflows as TBox definitions. Install resolves dashboard_name references in workflow steps to dashboard UUIDs. Seed.py retains only the generic "Create & Review" workflow.
**Demo:** After this: Install PPV v2 → 5 dashboards and 5 workflows appear in workspace. Open Action Items dashboard → stat-cards show counts, view-embeds show priority-filtered action tables. Launch Weekly Review workflow → step through guided review with pillar scoring, work review, and planning dashboards. Seed.py PPV workflows replaced by model-sourced TBox.

## Tasks
- [x] **T01: Replaced test dashboard with 5 real PPV dashboards (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub) using gridstack layout with 25 validated blocks** — Replace the single test dashboard in `models/ppv/dashboards/ppv.json` with 5 real PPV dashboards using gridstack layout. Each dashboard uses heading blocks, stat-cards with SPARQL queries, and view-embed blocks referencing PPV ViewSpec IRIs from S02.

**Dashboards to create:**
1. **Action Items** — stat-cards (active count, immediate priority count), view-embed for action-table, view-embed for action-kanban
2. **Life Dashboard** — stat-cards (active actions, active projects, active goals), view-embed for pillar-table, sparql-result for guiding principles
3. **Projects Board** — stat-card (active projects), view-embed for project-kanban, view-embed for project-table, sparql-result for orphan projects
4. **Goals Overview** — stat-card (active value goals), view-embed for valuegoal-table, view-embed for goaloutcome-table, sparql-result for goals without active outcomes
5. **Review Hub** — view-embed for pillarscore-table, view-embed for weekly-table, view-embed for review-graph

**GridStack constraints:** x: 0-11, y: ≥0, w: 1-12, h: ≥1, x+w ≤ 12. Stat-cards: 3w×2h. View-embeds: 6w×4h or 12w×6h. Headings: 12w×1h.

**ViewSpec IRI format:** Full IRI `urn:sempkm:model:ppv:view-{name}` (the ppv: prefix isn't available in the JSON — only in SPARQL queries at runtime). For view-embed blocks, use the full IRI.

**SPARQL queries for stat-cards** use prefixed form (ppv: prefix is auto-injected by the SPARQL router from model prefix registry at runtime):
- Active Actions: `SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:ActionItem ; ppv:status "Active" }`
- Immediate Priority: `SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:ActionItem ; ppv:status "Active" ; ppv:priority "Immediate" }`
- Active Projects: `SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:Project ; ppv:status "Active" }`
- Active Value Goals: `SELECT (COUNT(?s) AS ?count) WHERE { ?s a ppv:ValueGoal ; ppv:status "Underway" }`

**Block types available:** stat-card, view-embed, heading, markdown, sparql-result, chart, create-form, form-group, object-embed, divider
  - Estimate: 1h
  - Files: models/ppv/dashboards/ppv.json
  - Verify: python3 -c "import json; d=json.load(open('models/ppv/dashboards/ppv.json')); assert len(d['dashboards'])==5, f'Expected 5, got {len(d["dashboards"])}'; [print(f'  {i+1}. {dd["name"]}') for i,dd in enumerate(d['dashboards'])]; print('OK: 5 dashboards')" && cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py::TestLoadTboxDashboards::test_real_ppv_dashboards -v
- [x] **T02: Created 5 PPV workflows with dashboard_name→UUID resolution at install time** — Three pieces: (1) Create `models/ppv/workflows/ppv.json` with 5 workflow definitions. (2) Add `workflows: "workflows/ppv.json"` to `models/ppv/manifest.yaml`. (3) Add ~15 lines of dashboard_name→UUID post-processing in `ModelService.install()` so workflow steps with `dashboard_name` configs get resolved to real `dashboard_id` values at install time.

**Workflows to create:**
1. **Daily Check-in** — form step (create ActionItem), view step (action-kanban)
2. **Weekly Review** — dashboard step (Action Items dashboard), view step (weekly-table), form step (create WeeklyReview), dashboard step (Review Hub dashboard)
3. **Monthly Review** — view step (monthly-table), dashboard step (Review Hub), view step (weekly-table), form step (create MonthlyReview), view step (goaloutcome-table)
4. **Quarterly Review** — view step (quarterly-table), form step (create QuarterlyReview), dashboard step (Goals Overview), view step (valuegoal-table)
5. **Yearly Review** — view step (yearly-table), form step (create YearlyReview), dashboard step (Life Dashboard), view step (hierarchy-graph)

**Workflow step types:**
- `{"type": "view", "label": "...", "config": {"spec_iri": "urn:sempkm:model:ppv:view-XXX", "renderer_type": "table|graph|kanban"}}` — for ViewSpec steps
- `{"type": "dashboard", "label": "...", "config": {"dashboard_name": "Action Items"}}` — for dashboard steps (resolved to dashboard_id at install time)
- `{"type": "form", "label": "...", "config": {"target_class": "urn:sempkm:model:ppv:WeeklyReview"}}` — for form steps

**dashboard_name resolution in ModelService.install():**
The install sequence already creates dashboards before workflows (lines ~490-510 in models.py). After the dashboard creation loop, collect `{name: dashboard_data.id}` into a dict. Before creating each workflow, iterate its steps and replace any `config.dashboard_name` with `config.dashboard_id` using the mapping. If a referenced name isn't found, log a warning and leave the step as-is (degraded mode consistent with D380).

Same resolution must be added to `refresh_artifacts()` which does delete+recreate of TBox surfaces.

**Manifest update:** Add `workflows: "workflows/ppv.json"` under the `entrypoints:` section in `models/ppv/manifest.yaml`.
  - Estimate: 1h
  - Files: models/ppv/workflows/ppv.json, models/ppv/manifest.yaml, backend/app/services/models.py
  - Verify: python3 -c "import json; w=json.load(open('models/ppv/workflows/ppv.json')); assert len(w['workflows'])==5, f'Expected 5, got {len(w["workflows"])}'; print('OK: 5 workflows')" && python3 -c "import yaml; m=yaml.safe_load(open('models/ppv/manifest.yaml')); assert m['entrypoints'].get('workflows')=='workflows/ppv.json', 'Missing workflows entrypoint'; print('OK: manifest has workflows entrypoint')" && cd backend && .venv/bin/python -m pytest tests/test_tbox_lifecycle.py -v
- [ ] **T03: Migrate seed.py workflows + add tests for resolution and content validation** — Three pieces: (1) Remove the 4 PPV-specific workflows from `SEED_WORKFLOWS` in seed.py, keeping only "Create & Review". (2) Add test coverage for dashboard_name→UUID resolution in ModelService. (3) Update existing tbox_loader tests and add real PPV workflows content validation.

**seed.py changes:** Remove "Weekly Review", "Monthly Review", "Quarterly Review", "Yearly Review" entries from `SEED_WORKFLOWS` list. Keep "Create & Review" (generic, no PPV references). Remove the `_PPV` namespace constant since it's no longer used.

**Tests to add/update in `test_tbox_lifecycle.py`:**
- `test_install_v2_resolves_dashboard_names` — create a v2 manifest with workflow steps containing `dashboard_name` references → verify after install, workflow steps have `dashboard_id` (not `dashboard_name`)
- `test_install_v2_unresolved_dashboard_name_logs_warning` — workflow references a dashboard name that doesn't exist in the model → verify install succeeds (degraded mode) and step retains `dashboard_name`

**Tests to add/update in `test_tbox_loader.py`:**
- `test_real_ppv_workflows` — load real PPV workflows file, verify 5 workflows with expected names and step counts
- Update `test_real_ppv_dashboards` assertion: `len(result) >= 5` (previously >= 1)

**Tests to add in `test_data_widgets.py` or standalone:**
- `test_seed_workflows_count` — verify SEED_WORKFLOWS has exactly 1 entry ("Create & Review")

**Verification of seed.py:**
`python3 -c "from app.dashboard.seed import SEED_WORKFLOWS; assert len(SEED_WORKFLOWS)==1, f'Expected 1, got {len(SEED_WORKFLOWS)}'; print('OK: 1 seed workflow')"` (run from backend/)
  - Estimate: 45m
  - Files: backend/app/dashboard/seed.py, backend/tests/test_tbox_lifecycle.py, backend/tests/test_tbox_loader.py
  - Verify: cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py tests/test_tbox_lifecycle.py -v && .venv/bin/python -c "from app.dashboard.seed import SEED_WORKFLOWS; assert len(SEED_WORKFLOWS)==1; print('OK: 1 seed workflow')"
