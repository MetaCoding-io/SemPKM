# M047: PPV Model v2 - Versioned Manifests, TBox Dashboards/Workflows & Review System

## Vision
Mental Model manifests carry their full operational definition — dashboards, workflows, and templates ship with the model and are managed through the install/uninstall lifecycle. PPV becomes the reference v2 model, shipping August Bradley's complete review system as TBox operational surfaces.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Manifest v2 Infrastructure + TBox Install/Uninstall Lifecycle | high | — | ✅ | Install PPV with a v2 manifest carrying a test dashboard definition. Dashboard appears in workspace explorer tagged as model-sourced. Uninstall PPV — dashboard disappears. All 6 v1 models still install unchanged. |
| S02 | PPV Ontology Expansion — PillarScore, GuidingPrinciples & Enriched Reviews | medium | S01 | ✅ | After PPV install, create a PillarScore via SHACL form (linked to a pillar and weekly review, score 1-10). Create a GuidingPrinciples singleton. New enriched review fields (wins, challenges, supportingPriorities) appear on weekly/monthly/quarterly/yearly review forms. |
| S03 | TBox Dashboards & Workflows — PPV Operating System | medium | S01, S02 | ✅ | Install PPV v2 → 5 dashboards and 5 workflows appear in workspace. Open Action Items dashboard → stat-cards show counts, view-embeds show priority-filtered action tables. Launch Weekly Review workflow → step through guided review with pillar scoring, work review, and planning dashboards. Seed.py PPV workflows replaced by model-sourced TBox. |
| S04 | Seed Data Update & E2E Verification | low | S01, S02, S03 | ✅ | E2E test installs PPV v2, verifies dashboards and workflows exist, opens a dashboard, launches a workflow, uninstalls PPV, and verifies surfaces are removed. Seed data includes GuidingPrinciples and PillarScore instances for realistic dashboard rendering. |
