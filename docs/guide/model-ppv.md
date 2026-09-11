<!-- GENERATED FILE. Do not edit. Source: models/ppv/README.md. Regenerate with: python3 scripts/sync-model-docs.py -->
> **Bundled model documentation.** This page mirrors the `README.md` shipped inside the `ppv` Mental Model archive. The same text is available in the app under **Admin > Models > Pillars, Pipelines & Vaults (PPV) > Documentation** and at `/api/models/ppv/docs`. To change it, edit `models/ppv/README.md` and run `scripts/sync-model-docs.py`.

# Pillars, Pipelines & Vaults (PPV)

**Model ID:** `ppv` · **Namespace:** `urn:sempkm:model:ppv:` · **Prefix:** `ppv:` · **Manifest:** v2 (dashboards + workflows)

The PPV model brings August Bradley's *Pillars, Pipelines & Vaults* productivity system into
SemPKM. It organizes your life around a five-level goal hierarchy — from broad life pillars down
to individual action items — with a four-tier review cycle that keeps everything aligned.
Because it is a v2 manifest, installing it also creates five dashboards and five guided workflows.

- **Pillars** — the core areas of your life (Health, Career, Relationships, ...) that define what matters most.
- **Pipelines** — goal-driven workflows that move projects from idea to completion.
- **Vaults** — the knowledge stores; handled natively by the rest of SemPKM's knowledge graph.

## Types

### Goal hierarchy

| Type | Icon | Purpose |
|------|------|---------|
| **PillarGroup** | `layers` | Groups related pillars (e.g., "Personal Growth", "Professional") |
| **Pillar** | `mountain` | A core life area (e.g., Health, Career, Finance) |
| **ValueGoal** | `compass` | A value-driven goal linked to a pillar |
| **GoalOutcome** | `target` | A measurable outcome that advances a value goal, with a progress % |
| **Project** | `folder-kanban` | A concrete project that delivers a goal outcome |
| **ActionItem** | `square-check` | An individual task within a project |

The hierarchy flows top-down: **PillarGroup → Pillar → ValueGoal → GoalOutcome → Project →
ActionItem**. Each level links to the one above (`ppv:pillarGroup`, `ppv:pillar`,
`ppv:valueGoal`, `ppv:goalOutcome`, `ppv:project`).

Key fields:

| Type | Status values | Other notable fields |
|------|---------------|----------------------|
| Pillar | `Active`, `Paused`, `Inactive` | Icon, Color, Display Order, Pillar Group |
| ValueGoal | `Underway`, `Paused`, `Waiting`, `Off Track`, `Complete` | Priority (1st–5th), Target Date, Pillar ✓ |
| GoalOutcome | `Active`, `Next Up`, `Future 1–3`, `Completed` | Progress %, Target / Completed Date, Value Goal ✓ |
| Project | `Active`, `On Hold`, `Next Up`, `Future`, `Someday/Maybe`, `Completed` | Priority, Progress %, Start / Due / Review / Completed Date, Goal Outcome, Pillar |
| ActionItem | `Active`, `Waiting`, `Paused`, `Next Up`, `Future 1–3` | Priority (`Immediate`, `Quick`, `Scheduled`, 1st–5th, `Errand`, `Remember`), Done, Do Date, Context (`home`, `office`, `errands`, `calls`, `computer`, `anywhere`), Energy, Time Estimate, Project, Pillar |

### Review hierarchy

| Type | Icon | Purpose |
|------|------|---------|
| **WeeklyReview** | `calendar-days` | Weekly reflection: focus objective, wins, challenges, supporting priorities, plus pillar scores |
| **MonthlyReview** | `calendar-range` | Monthly roll-up: gratitude, learned this month, biggest wins/challenges, focus areas, habits to adjust |
| **QuarterlyReview** | `calendar-clock` | Quarterly reflection: accomplishments, disappointments, what worked / didn't, how to improve, annual vision notes |
| **YearlyReview** | `calendar-heart` | Annual direction: intention word and year theme |

Reviews nest in time: **Weekly → Monthly → Quarterly → Yearly** (`ppv:month`, `ppv:quarter`,
`ppv:yearLink`). Each carries a `Cycle` field fixed to its tier.

### Supporting types

| Type | Icon | Purpose |
|------|------|---------|
| **PillarScore** | `bar-chart-2` | A 1–10 score for one pillar within one weekly review, with "went well" / "needs attention" notes |
| **GuidingPrinciples** | `heart-handshake` | Values anchor: values, purpose, meaning, manifestation, foundational statement, guiding word |

## Dashboards

Installed automatically (v2 manifest, `dashboards/ppv.json`):

| Dashboard | What it shows |
|-----------|---------------|
| **Action Items** | Active action counts, immediate-priority items, table and kanban of all actions — daily triage |
| **Life Dashboard** | Pillars, goals, and projects overview with counts and a principles summary — start here |
| **Projects Board** | Project kanban and table, plus a query surfacing orphan projects not linked to a goal outcome |
| **Goals Overview** | Value goals and outcomes, highlighting goals with no active outcomes |
| **Review Hub** | Pillar score tables, weekly review listings, and the review hierarchy graph |

## Workflows

Installed automatically (`workflows/ppv.json`):

| Workflow | Steps |
|----------|-------|
| **Daily Check-in** | Create an action item, then review the action kanban |
| **Weekly Review** | Review action items → this week's reviews → create the weekly review (wins, challenges, pillar scores) → Review Hub |
| **Monthly Review** | Past monthly entries → Review Hub → weekly reviews → create monthly review → assess goal outcomes |
| **Quarterly Review** | Past quarterly entries → create quarterly review → Goals Overview → value goals |
| **Yearly Review** | Past yearly entries → create yearly review → Life Dashboard → full hierarchy graph |

## Views

Twenty-three views including the Life Dashboard, Pillar Hierarchy and Full Hierarchy graphs,
Goals Overview, Projects Board / Project Kanban, Action Items / Action Kanban / Actions by
Context, per-tier review tables, a Review Calendar, and Pillar Scores.

## Inference and validation rules

| Rule | Kind | Effect |
|------|------|--------|
| Derive project pillar from goal chain | Inference | A project inherits its pillar through GoalOutcome → ValueGoal |
| Derive action item pillar from project chain | Inference | An action item inherits its project's pillar |
| Derive pillar score date from weekly review | Inference | A pillar score takes the week start of its review |
| Orphan action item | Warning | "Action item is not linked to any project." |
| Orphan project | Warning | "Project is not linked to any goal outcome." |
| Stale project | Info | "Project has no modification date recorded. Consider reviewing its status." |

## Installation

Go to **Admin > Models**, pick **Pillars, Pipelines & Vaults** from the bundled catalog (or
enter the path `/app/models/ppv`) and click **Install**. Dashboards appear in the **DASHBOARDS**
section of the workspace sidebar and workflows in **WORKFLOWS**.

## Seed data

The bundle ships a connected demo hierarchy: 3 pillar groups, 6 pillars, 4 value goals, 4 goal
outcomes, 4 projects, 6 action items, one review at each tier, 3 pillar scores, and one Guiding
Principles document. Everything is linked so the dashboards and graphs render meaningfully out
of the box.

## Tips

- **Start with pillars.** Define your 4–8 life pillars before creating goals or projects.
- **Run the Weekly Review workflow.** Weekly pillar scoring builds the data that makes higher-level reviews valuable.
- **Check orphan projects.** The Projects Board dashboard and the orphan-project rule both flag misalignment.
- **Use the Full Hierarchy graph** to spot gaps in the system.
- **Link OKRs.** If Business Planning is installed, its Objectives can reference `ppv:GoalOutcome`.

---

**Back:** [Chapter 11: Mental Model Catalog](11-mental-model-catalog.md)
