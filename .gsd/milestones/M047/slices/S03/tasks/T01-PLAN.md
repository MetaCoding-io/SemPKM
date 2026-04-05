---
estimated_steps: 15
estimated_files: 1
skills_used: []
---

# T01: Author 5 PPV dashboards in dashboards/ppv.json

Replace the single test dashboard in `models/ppv/dashboards/ppv.json` with 5 real PPV dashboards using gridstack layout. Each dashboard uses heading blocks, stat-cards with SPARQL queries, and view-embed blocks referencing PPV ViewSpec IRIs from S02.

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

## Inputs

- ``models/ppv/dashboards/ppv.json` — existing test dashboard to replace`
- ``models/ppv/views/ppv.jsonld` — 23 ViewSpec IRIs to reference in view-embed blocks`

## Expected Output

- ``models/ppv/dashboards/ppv.json` — 5 real PPV dashboards with gridstack layout, stat-cards, view-embeds, headings`

## Verification

python3 -c "import json; d=json.load(open('models/ppv/dashboards/ppv.json')); assert len(d['dashboards'])==5, f'Expected 5, got {len(d["dashboards"])}'; [print(f'  {i+1}. {dd["name"]}') for i,dd in enumerate(d['dashboards'])]; print('OK: 5 dashboards')" && cd backend && .venv/bin/python -m pytest tests/test_tbox_loader.py::TestLoadTboxDashboards::test_real_ppv_dashboards -v
