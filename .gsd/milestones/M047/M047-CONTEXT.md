# M047 Context: PPV Model v2 — Versioned Manifests, TBox Dashboards/Workflows & Review System

**Created:** 2026-04-04
**Status:** Queued
**Depends on:** M046

## Vision

Make Mental Model manifests carry their full operational definition — not just vocabulary and shapes, but the dashboards, workflows, and templates that define how the model is *used*. Apply this to PPV by implementing August Bradley's complete review system (daily through yearly) as TBox operational surfaces that ship with the model.

The user who installs PPV should get the full operating system: the Action Items dashboard as their daily driver, the Weekly Review workflow that scores pillars and plans next week, the Life Dashboard that connects daily work to life direction. These aren't "sample data" — they're the methodology itself.

## Background: TBox vs ABox Distinction

The current manifest format treats dashboards and workflows as ABox (instance data seeded at runtime via `backend/app/dashboard/seed.py`). This is conceptually wrong:

- **TBox (terminological):** Classes, properties, shapes, views, rules, dashboards, workflows, templates — these define *what the model is and how it operates*
- **ABox (assertional):** Pillar instances, value goals, projects, action items, review entries — these are *what the user puts into the model*

The PPV Weekly Review workflow is TBox — it defines the PPV methodology. James's "Build a Life with My Partner" value goal is ABox — it's personal data.

Currently, the seeded workflows live in Python code (`backend/app/dashboard/seed.py`) and are created at first login. They're:
1. Non-portable — don't travel with the model archive
2. Fragile — hardcoded Python, not declarative
3. Not refreshable — model updates can't update the workflows
4. Conceptually ABox — stored in user tables alongside user-created workflows

## Part 1: Versioned Model Manifests

### Current Format (v1)

```yaml
modelId: ppv
version: "1.0.0"
name: "Pillars, Pipelines & Vaults"
namespace: "urn:sempkm:model:ppv:"
entrypoints:
  ontology: "ontology/ppv.jsonld"
  shapes: "shapes/ppv.jsonld"
  views: "views/ppv.jsonld"
  seed: "seed/ppv.jsonld"
  rules: "rules/ppv.ttl"
```

### Proposed Format (v2)

```yaml
manifest_version: "2.0"
modelId: ppv
version: "2.0.0"
name: "Pillars, Pipelines & Vaults"
namespace: "urn:sempkm:model:ppv:"
entrypoints:
  ontology: "ontology/ppv.jsonld"
  shapes: "shapes/ppv.jsonld"
  views: "views/ppv.jsonld"
  dashboards: "dashboards/ppv.jsonld"      # NEW
  workflows: "workflows/ppv.jsonld"        # NEW
  templates: "templates/ppv.jsonld"        # NEW
  seed: "seed/ppv.jsonld"
  rules: "rules/ppv.ttl"
```

### Backward Compatibility Requirements

- v1 manifests (no `manifest_version` field) install exactly as before
- The model installer detects version by presence/absence of `manifest_version`
- All 6 existing models (basic-pkm, crm, zettelkasten, research, ppv, business-planning) continue to work unmodified
- Only PPV gets a v2 manifest initially; other models can adopt later

### Install/Uninstall Lifecycle

TBox dashboards and workflows need to be distinguishable from user-created ones:
- On **install**: create dashboards/workflows from the manifest, tagged with `source_model`
- On **uninstall**: remove model-sourced dashboards/workflows, preserve user-created ones
- On **refresh/update**: replace model-sourced dashboards/workflows with new versions, preserve user-created ones
- User can **customize** a model dashboard (it becomes user-owned, no longer auto-updated)

### Serialization Format Decision

The dashboards/workflows files should use a JSON format that maps directly to the existing `DashboardService.create()` and `WorkflowService.create()` parameter shapes. This avoids inventing a new RDF vocabulary for operational surfaces — dashboards and workflows are UI constructs, not knowledge-domain concepts.

```jsonld
{
  "@context": { "ppv": "urn:sempkm:model:ppv:" },
  "dashboards": [
    {
      "id": "ppv:dashboard-action-items",
      "name": "Action Items",
      "description": "Daily driver — actions by priority, context, and completion status.",
      "blocks": [
        { "type": "stat-card", "config": { ... } },
        { "type": "view-embed", "config": { "spec_iri": "ppv:view-action-table", ... } }
      ]
    }
  ],
  "workflows": [ ... ],
  "templates": [ ... ]
}
```

## Part 2: PPV Ontology Expansion

### New Classes

#### PillarScore

The core mechanic of Bradley's weekly review. Every week, you score each active pillar 1-10 and reflect on what went well and what needs attention. This structured data enables trend tracking, charts, and pattern detection.

```
ppv:PillarScore
  ppv:weeklyReview → ppv:WeeklyReview (required, maxCount 1)
  ppv:pillar → ppv:Pillar (required, maxCount 1)
  ppv:score (xsd:integer, 1-10, required)
  ppv:wentWell (xsd:string, optional) — "What went well"
  ppv:needsAttention (xsd:string, optional) — "What needs attention"
  dcterms:created (xsd:dateTime)
```

**What this enables:**
- Line chart dashboard: pillar scores over time (X=week, Y=score, one line per pillar)
- Stat-card: average pillar score this month
- Alert rule: "pillar declining for 3+ consecutive weeks"
- Weekly review form-group: create multiple PillarScore entries linked to the review
- Cross-view context: click a weekly review → see its pillar scores

#### GuidingPrinciples

Bradley's values anchor. A singleton document that is transcluded into every weekly review. Contains the foundational statement you repeat to yourself weekly and the guiding word for your current life stage.

```
ppv:GuidingPrinciples
  ppv:values (xsd:string) — what you value most in life
  ppv:purpose (xsd:string) — what purpose you serve
  ppv:meaning (xsd:string) — why this purpose matters
  ppv:manifestation (xsd:string) — how you'll show these values
  ppv:foundationalStatement (xsd:string) — 3-5 line poetic statement
  ppv:guidingWord (xsd:string) — central word/phrase for this life stage
  dcterms:created (xsd:dateTime)
```

**What this enables:**
- Object-embed in weekly review dashboard — always visible during pillar scoring
- Yearly review workflow step: edit guiding principles form
- A grounding anchor that connects daily actions to core values

### Enriched Review Properties

Source: Bradley's Notion/Obsidian review templates (see Source Material section below).

**WeeklyReview additions:**
- `ppv:wins` (xsd:string) — overall what went well this week
- `ppv:challenges` (xsd:string) — what was hard
- `ppv:supportingPriorities` (xsd:string) — 3 supporting priorities for next week

**MonthlyReview additions:**
- `ppv:biggestWins` (xsd:string)
- `ppv:biggestChallenges` (xsd:string)
- `ppv:focusAreas` (xsd:string) — focus areas for next month
- `ppv:habitsToAdjust` (xsd:string)

**QuarterlyReview additions:**
- `ppv:accomplishments` (xsd:string)
- `ppv:disappointments` (xsd:string)
- `ppv:whatWorked` (xsd:string)
- `ppv:whatDidntWork` (xsd:string)
- `ppv:howToImprove` (xsd:string)
- `ppv:annualVisionNotes` (xsd:string)

**YearlyReview additions:**
- `ppv:intentionWord` (xsd:string) — word/phrase for the year ahead
- `ppv:yearTheme` (xsd:string) — theme or vision statement

### New ViewSpecs

| ViewSpec ID | Target Class | Renderer | Purpose |
|---|---|---|---|
| `ppv:view-pillarscore-table` | PillarScore | table | All scores with pillar, score, week, reflection |
| `ppv:view-action-kanban` | ActionItem | kanban | Actions by status — daily work view |
| `ppv:view-project-kanban` | Project | kanban | Projects by status — pipeline board |
| `ppv:view-action-by-context` | ActionItem | table | Filtered by context — GTD context lists |

### TBox Dashboards

These map directly to Bradley's "Alignment Zone" dashboards from the Obsidian vault.

**1. Action Items Dashboard** (daily driver)
Source: `/home/james/Documents/Vaults/PPV/Alignment/Action Items.md`

| Block | Type | Content |
|---|---|---|
| Today's Focus | stat-card | COUNT of Active actions where doDate = today |
| Immediate 🔥 | view-embed | Actions: status=Active, priority=Immediate |
| 1st Priority 🚀 | view-embed | Actions: status=Active, priority=1st Priority |
| 2nd Priority | view-embed | Actions: status=Active, priority=2nd Priority |
| By Context: Home | view-embed | Actions: status=Active, context=home |
| By Context: Errands | view-embed | Actions: status=Active, context=errands |
| By Context: Calls | view-embed | Actions: status=Active, context=calls |
| Waiting On | view-embed | Actions: status=Waiting |
| Completed Today | view-embed | Actions: done=true (recent) |

**2. Life Dashboard** (strategic context)
Source: `/home/james/Documents/Vaults/PPV/Life Dashboard.md`

| Block | Type | Content |
|---|---|---|
| Active Pillars | view-embed | Pillar cards view |
| Weekly Focus | markdown or stat-card | Current week's focus objective |
| Value Goals | view-embed | Value goals: status=Underway, sorted by pillar |
| Goal Outcomes | view-embed | Goal outcomes: status=Active, with progress |
| Active Projects | view-embed | Projects: status=Active, sorted by priority |
| Open Actions | stat-card | COUNT of active action items |
| Pillar Score Trend | chart | Line chart of PillarScore over recent weeks |

**3. Projects Board**
Source: `/home/james/Documents/Vaults/PPV/Alignment/Projects Board.md`

| Block | Type | Content |
|---|---|---|
| Projects by Status | view-embed | Projects kanban (Future → Next Up → Active → On Hold → Completed) |
| Orphan Check | sparql-result | Projects without a goal outcome link |

**4. Goals Overview**
Source: `/home/james/Documents/Vaults/PPV/Alignment/Goals Overview.md`

| Block | Type | Content |
|---|---|---|
| Value Goals by Pillar | view-embed | Value goals table sorted by pillar |
| Active Goal Outcomes | view-embed | Goal outcomes with progress |
| Upcoming Outcomes | view-embed | Next Up / Future outcomes |
| Alignment Check | sparql-result | Value goals without active goal outcomes |

**5. Review Hub**
Source: `/home/james/Documents/Vaults/PPV/Alignment/Review Hub.md`

| Block | Type | Content |
|---|---|---|
| Recent Weekly Reviews | view-embed | Last 8 weekly reviews |
| Monthly Reviews | view-embed | Last 6 monthly reviews |
| Quarterly Reviews | view-embed | Last 4 quarterly reviews |
| Review Schedule | markdown | Table: review type, frequency, best time |

### TBox Workflows

**1. Daily Check-in** (3-5 min)
- Step 1: Life Dashboard (dashboard) — reconnect with weekly focus and pillar priorities
- Step 2: Action Items (dashboard) — scan priorities, adjust if needed
- Step 3: Quick Add (form) — ActionItem creation form for anything new

**2. Weekly Review** (30-40 min)
Source: `/home/james/Documents/Vaults/PPV/Templates/Weekly Review.md`
- Step 1: Guiding Principles (dashboard) — object-embed of GuidingPrinciples + reflection prompts
- Step 2: Pillar Scoring (dashboard) — active pillars + form-group for PillarScore entries
- Step 3: Work Review (dashboard) — completed actions, waiting items, active projects
- Step 4: Life Maintenance (dashboard) — task template instantiation for recurring checklist
- Step 5: Plan Next Week (dashboard) — WeeklyReview creation form + action reprioritization
- Step 6: Confirm (view) — review graph showing new review + pillar scores

**3. Monthly Review** (45-60 min)
Source: `/home/james/Documents/Vaults/PPV/Templates/Monthly Review.md`
- Step 1: Weekly Rollup (dashboard) — this month's weeklies + pillar score trend chart
- Step 2: Pillar Assessment (dashboard) — pillar cards + avg score stat-cards
- Step 3: Pipeline Review (dashboard) — value goals, goal outcomes, projects
- Step 4: Create Review (form) — MonthlyReview with gratitude, learned, wins, challenges
- Step 5: Plan Next Month (dashboard) — focus areas + project reprioritization

**4. Quarterly Review** (60-90 min)
Source: `/home/james/Documents/Vaults/PPV/Templates/Quarterly Review.md`
- Step 1: Debrief (dashboard) — monthly reviews + 3-month pillar trends + reflection prompts
- Step 2: Pipeline Audit (dashboard) — full pipeline views
- Step 3: Someday/Maybe Triage (view) — projects with status Someday/Maybe
- Step 4: Create Review (form) — QuarterlyReview with accomplishments, disappointments, reflection

**5. Yearly Review** (2-3 hrs)
Source: `/home/james/Documents/Vaults/PPV/Templates/Yearly Review.md`
- Step 1: Year in Review (dashboard) — quarterly reviews + year-long pillar charts + stat-cards
- Step 2: Reflect/Interpret/Visualize (dashboard) — markdown with 15 reflection questions + guiding principles embed
- Step 3: System Audit (dashboard) — full hierarchy graph + all active pillars/goals/outcomes/projects
- Step 4: Create Review (form) — YearlyReview with intentionWord, yearTheme
- Step 5: Update Principles (form) — GuidingPrinciples edit form

### TBox Task Template

**Life Maintenance Checklist** (weekly recurring)
Source: `/home/james/Documents/Vaults/PPV/Templates/Weekly Review.md` Section II

```json
{
  "title": "Life Maintenance Checklist",
  "target_class": "ppv:ActionItem",
  "default_properties": {
    "ppv:status": "Active",
    "ppv:priority": "Scheduled",
    "ppv:context": "home",
    "ppv:energy": "low"
  },
  "subtask_definitions": [
    { "title": "Email: Process inbox to zero" },
    { "title": "Calendar: Review past 2 weeks and next 4 weeks" },
    { "title": "Desktop: Clear downloads folder and desktop files" },
    { "title": "Paper: File or scan physical documents" },
    { "title": "Events: Book recurring events for next week" }
  ]
}
```

## Explicit Exclusions

- **Vaults** — SemPKM's knowledge models (basic-pkm, Zettelkasten, Research) handle note-taking better than PPV's vault concept. Intentionally excluded.
- **Habits & Routines database** — Separate domain. Could be its own mental model later.
- **Accomplishments/Disappointments databases** — The Notion templates reference these as "[Future]" databases. Free-text fields on QuarterlyReview are sufficient.
- **Daily Tracking database** — Separate domain. The daily review is an operational workflow (dashboard + form), not a formal data-entry entity.

## Source Material Index

All original research and templates from this conversation:

| Source | Location | Content |
|---|---|---|
| Schema Spec | `/home/james/Documents/Vaults/PPV/System/Schema Spec.md` | Complete property schemas for all PPV types, Notion provenance, query patterns |
| Weekly Review Template | `/home/james/Documents/Vaults/PPV/Templates/Weekly Review.md` | 4-section template: Pillars (scoring), Pipelines (work review), Vaults, Planning |
| Monthly Review Template | `/home/james/Documents/Vaults/PPV/Templates/Monthly Review.md` | Warm-up, Pillar Assessment, Pipeline Review, Planning |
| Quarterly Review Template | `/home/james/Documents/Vaults/PPV/Templates/Quarterly Review.md` | Debrief (accomplishments/disappointments/reflection), Process & Update, Someday/Maybe |
| Yearly Review Template | `/home/james/Documents/Vaults/PPV/Templates/Yearly Review.md` | Reflect/Interpret/Visualize (15 questions), System Implementation Review, Planning |
| Action Items Dashboard | `/home/james/Documents/Vaults/PPV/Alignment/Action Items.md` | By Priority, By Context, Waiting On, Completed Today |
| Life Dashboard | `/home/james/Documents/Vaults/PPV/Life Dashboard.md` | Insight, Life Alignment (pillars, goals, outcomes), Execution (projects, actions) |
| Projects Board | `/home/james/Documents/Vaults/PPV/Alignment/Projects Board.md` | Future → Next Up → Active → On Hold → Completed |
| Goals Overview | `/home/james/Documents/Vaults/PPV/Alignment/Goals Overview.md` | Value Goals by Pillar, Active/Not Started/Completed Outcomes, Alignment Check |
| Review Hub | `/home/james/Documents/Vaults/PPV/Alignment/Review Hub.md` | Recent reviews, schedule, checklists |
| Guiding Principles | `/home/james/Documents/Vaults/PPV/System/Guiding Principles.md` | Values, Purpose, Meaning, Manifestation, Foundational Statement, Guiding Word |
| Weekly Review How-To | `/home/james/Documents/Vaults/PPV/System/How-To Guides/Conduct Weekly Review.md` | Step-by-step process (30-40 min), troubleshooting |
| PPV System Guide | `/home/james/Documents/Vaults/PPV/System/PPV System Guide.md` | Daily/Weekly/Monthly/Quarterly/Yearly workflow descriptions |
| M001 Research (PPV ontology) | `.gsd/milestones/M001/M001-RESEARCH.md` lines 4977-6277 | Original full Turtle ontology translated from Schema Spec |
| Current PPV Model | `models/ppv/` | Shipped ontology, shapes, views, rules, seed data |
| Current Seed Workflows | `backend/app/dashboard/seed.py` | 5 workflows to migrate from seed to TBox |
| Life Plan Seed Data | `models/ppv/seed/james-life.jsonld` | Real ABox: 9 pillars, 9 value goals, 12 goal outcomes, 13 projects, 28 actions |

## Suggested Slice Structure

**S01: Manifest v2 — Backward-Compatible Format Extension** `risk:high`
- Add `manifest_version` field detection to model installer
- Add `dashboards`, `workflows`, `templates` entrypoint handling
- v1 manifests continue to work unchanged
- Add `source_model` tracking on dashboard/workflow rows
- Install/uninstall/refresh lifecycle for TBox operational surfaces

**S02: PPV Ontology Expansion** `risk:medium` `depends:[S01]`
- Add PillarScore class + GuidingPrinciples class to ontology
- Add enriched review fields to Weekly/Monthly/Quarterly/Yearly reviews
- SHACL shapes for all new types and properties
- New ViewSpecs (pillar scores table, action kanban, project kanban, action by context)
- SHACL-AF rules (PillarScore → WeeklyReview denormalization)

**S03: TBox Dashboards & Workflows** `risk:medium` `depends:[S01, S02]`
- Create `dashboards/ppv.jsonld` with 5 dashboards
- Create `workflows/ppv.jsonld` with 5 workflows
- Create `templates/ppv.jsonld` with Life Maintenance template
- Update manifest.yaml to v2
- Migrate existing seed.py PPV workflows to model archive
- Verify install/uninstall creates and removes TBox surfaces correctly

**S04: Seed Data Update & E2E Verification** `risk:low` `depends:[S03]`
- Update james-life.jsonld: fill in Career and Mental Health pillars
- Add GuidingPrinciples seed instance
- Add sample PillarScore entries for one weekly review
- E2E tests: model install creates dashboards/workflows, uninstall removes them
- User guide documentation for the expanded PPV model
