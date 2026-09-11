# Chapter 39: Mental Model Catalog

SemPKM ships eight bundled Mental Models. Each one defines domain-specific types, forms, views, and (for most) validation rules and saved queries. This chapter is the catalog: a short profile of every bundled model and where to find its full documentation.

> **Where the detailed docs live.** Every model archive ships its own `README.md` with field-by-field type references, relationship diagrams, saved queries, validation rules, and recommended dashboards. SemPKM renders it in the admin portal under **Admin > Models > *model* > Documentation**, and serves the raw Markdown at `/api/models/{modelId}/docs`. Because the documentation travels inside the archive, it always matches the installed version -- this chapter deliberately does not repeat it (or version numbers, which the admin portal shows).

For background on what Mental Models are and how they work, see [Chapter 9: Understanding Mental Models](09-understanding-mental-models.md). For installation, refresh, and removal, see [Chapter 10: Managing Mental Models](10-managing-mental-models.md). To build your own, see [Chapter 19: Creating Mental Models](19-creating-mental-models.md).

---

## Installing a bundled model

1. Open **Admin > Models**. The **Available Models** grid lists every bundled model that is not yet installed.
2. Click **Install** on a card (or enter `/app/models/{modelId}` in the install form).
3. Open the model's detail page and read the **Documentation** tab before creating your first objects.

Basic PKM is installed automatically on a fresh instance. All models can coexist -- their namespaces are independent and types do not collide.

---

## The bundled models

### Basic PKM

**Model ID:** `basic-pkm` · **Prefix:** `bpkm:` · Installed by default

General-purpose personal knowledge management plus lightweight project management: **Note**, **Concept**, **Project**, **Person**, **Task**, **Milestone**, and **Event**. Tasks carry scheduling, recurrence, and external-sync fields used by the Linear, GitHub, Jira, Monday, Asana, and Todoist apps; Events back the calendar view and the Google Calendar, Outlook, and CalDAV sync apps. Ships eight saved queries (open, overdue, and blocked tasks; upcoming and past events; active projects; recent notes; concept hierarchy) and SHACL-AF rules for overdue tasks, missing titles, comma-separated tags, and more.

Documentation: `models/basic-pkm/README.md` · Also see [Chapter 9](09-understanding-mental-models.md#the-basic-pkm-mental-model).

### Personal CRM

**Model ID:** `crm` · **Prefix:** `crm:`

Relationship management with **Contact**, **Company**, **Interaction**, and **Deal**. Deals move through a `lead → qualified → proposal → negotiation → won / lost` pipeline. Rules warn about contacts with no recorded interactions and overdue follow-ups; an inference rule derives each contact's last-contacted date.

Documentation: `models/crm/README.md`

### Zettelkasten+

**Model ID:** `zettelkasten` · **Prefix:** `zk:`

The Zettelkasten method with a full provenance chain: **FleetingNote → Source → LiteratureNote → PermanentNote → StructureNote**. Permanent notes connect through `supports`, `contradicts`, `followsFrom`, and `relatedTo` argumentation links; a Contradiction Map graph visualizes tensions. Rules flag unprocessed fleeting notes, isolated permanent notes, and unsourced ideas.

Documentation: `models/zettelkasten/README.md`

### Research Workflow

**Model ID:** `research` · **Prefix:** `res:`

Academic research tracking with **Paper**, **Claim**, **Evidence**, **ResearchQuestion**, and **Argument**. Claims carry a confidence level and accumulate supporting and refuting evidence with type and strength; rules flag unsupported and contested claims, orphan evidence, and unanswered questions. Includes a citation network graph and an evidence map.

Documentation: `models/research/README.md`

### Business Planning

**Model ID:** `business-planning` · **Prefix:** `bp:`

Fifteen strategy frameworks as container + item types (32 concrete types): Eisenhower Matrix, Decision Matrix, SWOT, Porter's Five Forces, PESTLE, BCG Matrix, Ansoff Matrix, Business Model Canvas, Lean Canvas, Value Chain, OKR, Balanced Scorecard, RACI Matrix, Stakeholder Map, and Risk Matrix. Four custom renderers -- **Quadrant**, **BMC**, **OKR**, and **Decision Matrix** -- plus cross-model edges to Basic PKM tasks and projects and PPV goal outcomes. No rules or saved queries; the README includes SPARQL starting points.

Documentation: `models/business-planning/README.md`

### Pillars, Pipelines & Vaults (PPV)

**Model ID:** `ppv` · **Prefix:** `ppv:` · v2 manifest

August Bradley's PPV system: a five-level goal hierarchy (**PillarGroup → Pillar → ValueGoal → GoalOutcome → Project → ActionItem**) and a four-tier review cycle (**Weekly → Monthly → Quarterly → Yearly**) with **PillarScore** and **GuidingPrinciples**. Installing it also creates five dashboards (Action Items, Life Dashboard, Projects Board, Goals Overview, Review Hub) and five guided workflows (Daily Check-in and the four reviews). Rules flag orphan action items and projects.

Documentation: `models/ppv/README.md` · Also see [Chapter 50: PPV Model](50-ppv-model.md).

### RSS Feeds

**Model ID:** `rss-feeds` · **Prefix:** `rss:`

The two types behind the RSS Reader app: **FeedSubscription** and **Article**, with Unread and Starred saved queries. No seed data -- the app populates the graph as it polls. Install the model before the app.

Documentation: `models/rss-feeds/README.md` · Also see [Chapter 40: RSS Reader](40-rss-reader.md).

### Media Scheduler

**Model ID:** `media-scheduler` · **Prefix:** `ms:`

The types behind the Media Scheduler app: **MediaSource** (podcast, YouTube, Spotify), **MediaItem**, **MediaCategory**, **DailyMediaPlan**, and **PlanEntry**. No seed data -- the app populates the graph. Install the model before the app.

Documentation: `models/media-scheduler/README.md` · Also see [Chapter 49: Media Scheduler](49-media-scheduler.md).

---

## Model comparison

| Model | Types | Focus | Rules | Saved queries | Ships dashboards/workflows | Seed data |
|-------|-------|-------|-------|---------------|----------------------------|-----------|
| Basic PKM | 7 | General PKM + projects + calendar | Yes | 8 | No | Yes |
| Personal CRM | 4 | Relationships + deals | Yes | 4 | No | Yes |
| Zettelkasten+ | 5 | Structured notes | Yes | 4 | No | Yes |
| Research Workflow | 5 | Academic research | Yes | 8 | No | Yes |
| Business Planning | 32 | Strategy frameworks + custom renderers | No | 0 | No | Yes |
| PPV | 12 | Life management + reviews | Yes | 0 (23 views) | Yes (5 + 5) | Yes |
| RSS Feeds | 2 | RSS Reader app | No | 2 | No | No |
| Media Scheduler | 5 | Media Scheduler app | No | 0 | No | No |

Type counts, view lists, and rule details for the installed version are always visible on the model's detail page (**Schema** and **Documentation** tabs).

---

## Marketplace models

Models installed from the remote marketplace follow the same conventions. Their documentation, if the author shipped one, appears on the same Documentation tab; models without one show an empty state and a `missing-docs` warning in the install result. See [Chapter 10](10-managing-mental-models.md) for marketplace installation and updates.

---

**Previous:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) | **Next:** [Chapter 30: Workspace Personas](30-personas.md)
