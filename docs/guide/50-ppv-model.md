# Chapter 50: PPV Model (Pillars, Pipelines & Vaults)

The **PPV model** brings August Bradley's Pillars, Pipelines & Vaults productivity system into SemPKM. PPV organizes your life around a five-level goal hierarchy — from broad life pillars down to individual action items — with a four-tier review cycle that keeps everything aligned. Because the model is built on the knowledge graph, all PPV objects participate in search, views, edges, SPARQL queries, and the AI copilot.

This chapter covers installing the model, understanding its types, using dashboards and workflows, working with the review system, and exploring the seed data.

---

## What is PPV?

PPV (Pillars, Pipelines & Vaults) is a life management methodology created by August Bradley. It structures personal productivity around three concepts:

- **Pillars** — the core areas of your life (Health, Career, Relationships, etc.) that define what matters most
- **Pipelines** — the goal-driven workflows that move projects from idea to completion, organized in a hierarchy from value goals down to action items
- **Vaults** — the knowledge stores that capture what you learn along the way (handled natively by SemPKM's knowledge graph)

The SemPKM PPV model implements the Pillars and Pipelines layers as typed objects with SHACL-validated forms, linked views, dashboards, and guided workflows.

---

## Types

The PPV model defines 12 types organized in two hierarchies:

### Goal Hierarchy

| Type | Icon | Purpose |
|------|------|---------|
| **PillarGroup** | `layers` | Groups related pillars (e.g., "Personal Growth", "Professional") |
| **Pillar** | `mountain` | A core life area (e.g., Health, Career, Finance) |
| **ValueGoal** | `compass` | A value-driven goal linked to a pillar (e.g., "Achieve financial independence") |
| **GoalOutcome** | `target` | A measurable outcome that advances a value goal |
| **Project** | `folder-kanban` | A concrete project with tasks that delivers a goal outcome |
| **ActionItem** | `square-check` | An individual task within a project, with status and priority |

The hierarchy flows top-down: **PillarGroup → Pillar → ValueGoal → GoalOutcome → Project → ActionItem**. Each level links to the one above via a relationship property (e.g., `ppv:pillar`, `ppv:valueGoal`, `ppv:goalOutcome`).

### Review Hierarchy

| Type | Icon | Purpose |
|------|------|---------|
| **WeeklyReview** | `calendar-days` | Weekly reflection with pillar scoring, wins, and struggles |
| **MonthlyReview** | `calendar-range` | Monthly assessment rolling up weekly reviews |
| **QuarterlyReview** | `calendar-clock` | Quarterly goal and alignment check |
| **YearlyReview** | `calendar-heart` | Annual life direction review |

Reviews form a time-based hierarchy: **Weekly → Monthly → Quarterly → Yearly**. Each review type has enriched reflection fields — wins, struggles, lessons learned, and gratitude — that build a record of growth over time.

### Supporting Types

| Type | Icon | Purpose |
|------|------|---------|
| **PillarScore** | `bar-chart-2` | A numeric score (1–10) for a pillar during a weekly review |
| **GuidingPrinciples** | `heart-handshake` | Core values and principles that guide decision-making |

PillarScore instances are created during weekly reviews — one per pillar — to track how each life area is performing over time. GuidingPrinciples captures your foundational values in one place for reference during reviews and goal-setting.

---

## Dashboards

The PPV model ships with five dashboards, each focused on a different aspect of the system:

### Action Items

Task management dashboard showing active action counts, immediate-priority items, and both table and kanban views of all actions. Use this for daily task triage.

### Life Dashboard

High-level overview of your pillars, goals, and projects. Shows active action, project, and goal counts alongside a pillar table and principles summary. Start here for a bird's-eye view.

### Projects Board

Project management with kanban and table views. Includes a stat card for active project count and a SPARQL query that surfaces orphan projects — those not linked to any goal outcome.

### Goals Overview

Tracks value goals and their outcomes. Shows active goal counts, tables for both value goals and goal outcomes, and highlights goals that have no active outcomes — a signal that goal progress may have stalled.

### Review Hub

Central hub for the review system. Displays pillar score tables, weekly review listings, and a review hierarchy graph showing how reviews connect across time scales.

---

## Workflows

The PPV model includes five guided workflows that walk you through recurring processes:

### Daily Check-in

A quick two-step workflow: create a new action item, then review the action kanban board to see everything in context.

### Weekly Review

The core review ritual with four steps:

1. **Review Action Items** — open the Action Items dashboard to triage completed, deferred, and new tasks
2. **This Week's Reviews** — see existing weekly review entries in table view
3. **Create Weekly Review** — fill out the weekly review form with wins, struggles, lessons learned, gratitude, and pillar scores
4. **Review Hub** — check the review hub dashboard to see scores and trends

### Monthly Review

A five-step workflow that zooms out to the monthly level: review past monthly entries, check the review hub, revisit weekly reviews, create a new monthly review, and assess goal outcomes.

### Quarterly Review

Assess quarterly progress with four steps: review past quarterly entries, create a new one, check the goals overview dashboard, and review value goals.

### Yearly Review

Full life direction review in four steps: review past yearly entries, create a new review, open the life dashboard for the big picture, and explore the full PPV hierarchy graph.

---

## The Review System

The review system is the heartbeat of PPV. It works in nested cycles:

**Weekly** — Every week, you score each pillar 1–10 (via PillarScore instances), note wins and struggles, and capture lessons learned. This is the most granular review and feeds all higher-level reviews.

**Monthly** — Each month, you review the weekly scores and reflections, identify monthly themes, and assess whether your projects are aligned with your goals.

**Quarterly** — Every quarter, you step back to evaluate goal progress, check value alignment, and decide whether to adjust your goal outcomes or start new projects.

**Yearly** — Once a year, you review the full hierarchy — pillars, goals, projects, and all reviews — to set direction for the coming year.

Each review type includes enriched reflection fields:

- `ppv:wins` — what went well during the period
- `ppv:struggles` — challenges faced
- `ppv:lessonsLearned` — insights to carry forward
- `ppv:gratitude` — what you're grateful for

These fields build a searchable record of personal growth across the knowledge graph.

---

## Installation

1. Navigate to **Admin > Mental Models**.
2. Click **Install Model**.
3. Enter the archive path: `ppv` (the bundled model ships with SemPKM).
4. Click **Install**.

The model registers all 12 types with their SHACL shapes (for form validation), views (table, kanban, graph), five dashboards, and five workflows. Dashboards appear in the **DASHBOARDS** section of the workspace sidebar, and workflows appear in the **WORKFLOWS** section.

> **Tip:** After installing, check the Explorer sidebar — you should see PPV types listed under their icons. Open any dashboard from the sidebar to verify the installation.

---

## Seed Data

The PPV model ships with seed data that populates the system with demo instances across all 12 types. This lets you explore dashboards, workflows, and views with realistic data before adding your own.

The seed data includes:

- **3 Pillar Groups** (Personal Growth, Professional, Relationships & Community)
- **6 Pillars** (Health & Fitness, Learning & Development, Career, Finance, Family, Community)
- **4 Value Goals** spanning different pillars
- **4 Goal Outcomes** linked to value goals
- **4 Projects** with various statuses (Active, Planning, Completed)
- **6 Action Items** across priorities (Immediate, High, Normal)
- **4 Reviews** (1 weekly, 1 monthly, 1 quarterly, 1 yearly) with enriched reflection fields
- **3 Pillar Scores** linking pillars to the weekly review with numeric ratings
- **1 Guiding Principles** instance with core values

All seed instances are linked into the hierarchy — projects connect to goal outcomes, which connect to value goals, which connect to pillars, which belong to pillar groups. The review hierarchy is similarly connected, with pillar scores linking to both the weekly review and their respective pillars.

> **Note:** Because seed data creates instances in the knowledge graph, uninstalling the model will prompt you to confirm removal of these objects. You can also delete individual seed instances from the object editor if you want to replace them with your own data.

---

## Tips and Best Practices

- **Start with pillars.** Define your 4–8 life pillars before creating goals or projects. Everything in PPV flows from the pillars.
- **Use the Weekly Review workflow.** The weekly review is the minimum viable PPV practice. Even if you skip monthly/quarterly reviews initially, weekly pillar scoring builds the data that makes higher-level reviews valuable.
- **Check orphan projects.** The Projects Board dashboard includes a query for projects not linked to any goal outcome. Orphan projects are a signal of misalignment.
- **Use the graph view.** The full hierarchy graph (available in the Yearly Review workflow and as a standalone view) shows how everything connects. It's the fastest way to spot gaps in your system.
- **Score honestly.** Pillar scores are for you, not for judgment. A score of 3 is useful information. A score of 8 you don't believe undermines the whole system.
