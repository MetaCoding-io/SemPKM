# Mental Models Expansion — Design Document

**Created:** 2026-03-16
**Status:** Draft
**Goal:** Expand the Mental Model lineup from 3 to 6+ models at public launch, covering the primary conversion personas (Obsidian power users, Notion escapees, professionals, researchers).

---

## Current State

| Model | Version | Types | Audience |
|---|---|---|---|
| basic-pkm | 1.3.0 | 4 (Project, Person, Note, Concept) | General PKM |
| ppv | 1.0.0 | 11 (Pillars/Goals/Actions/Reviews) | Goal planners |
| gist | 14.0.0 | Upper ontology foundation | (not user-facing) |

**Gap:** No task management, no CRM, no Zettelkasten methodology, no research workflow. The two existing models cover "casual knowledge capture" and "life goal planning" — missing the everyday operational layer and the deep thinking layer.

---

## Expansion Plan

### 1. basic-pkm v2.0 — Add Task Management + Integration Hub

### 2. Personal CRM (new model)

### 3. Zettelkasten+ (new model)

### 4. Research Workflow (new model)

---

## 1. basic-pkm v2.0: Task Management & Integration Hub

### Vision

Upgrade basic-pkm from a knowledge capture tool to a **knowledge + action** tool. Add Task and Milestone types that integrate natively with the existing Project/Note/Concept graph — and design them as a **semantic hub** for third-party task providers.

The key insight: users don't want to replace Asana or Linear or Jira. They want **one view across all of them**, semantically aligned so they can query, relate, and reason across tasks regardless of origin.

### New Types

#### `bpkm:Task` (extends `gist:Task`)

The atomic unit of work. Designed to be both a native SemPKM object and a **sync target** for external task providers.

**Datatype Properties:**
| Property | Datatype | Constraints | Notes |
|---|---|---|---|
| `dcterms:title` | xsd:string | required, maxCount 1 | Task title |
| `dcterms:description` | xsd:string | maxCount 1 | Longer description / acceptance criteria |
| `bpkm:taskStatus` | xsd:string | `sh:in` (todo, in-progress, done, blocked, cancelled) | Normalized across providers |
| `bpkm:priority` | xsd:string | `sh:in` (low, medium, high, critical) | Reuse existing priority enum |
| `bpkm:dueDate` | xsd:date | maxCount 1 | When it's due |
| `bpkm:completedDate` | xsd:date | maxCount 1 | When it was finished |
| `bpkm:effort` | xsd:string | `sh:in` (trivial, small, medium, large, epic) | T-shirt sizing |
| `bpkm:tags` | xsd:string | multi-value | Reuse existing tags |
| `bpkm:body` | xsd:string | maxCount 1 | Markdown notes on the task |

**Integration Properties (for synced tasks):**
| Property | Datatype | Constraints | Notes |
|---|---|---|---|
| `bpkm:externalId` | xsd:string | maxCount 1 | Provider's task ID (e.g., "PROJ-123") |
| `bpkm:externalUrl` | xsd:anyURI | maxCount 1 | Direct link to task in provider |
| `bpkm:externalProvider` | xsd:string | `sh:in` (asana, linear, jira, github, todoist, trello, manual) | Where it came from |
| `bpkm:lastSyncedAt` | xsd:dateTime | maxCount 1 | Last successful sync timestamp |
| `bpkm:syncDirection` | xsd:string | `sh:in` (pull, push, bidirectional) | How this task syncs |

**Object Properties (relationships):**
| Property | Range | Constraints | Notes |
|---|---|---|---|
| `bpkm:assignedTo` | `bpkm:Person` | multi-value | Who's responsible |
| `bpkm:taskProject` | `bpkm:Project` | maxCount 1 | Parent project |
| `bpkm:milestone` | `bpkm:Milestone` | maxCount 1 | Which milestone this belongs to |
| `bpkm:dependsOn` | `bpkm:Task` | multi-value | Blocking dependencies |
| `bpkm:relatedNote` | `bpkm:Note` | multi-value | Connected notes/context |
| `bpkm:relatedConcept` | `bpkm:Concept` | multi-value | Connected concepts |

#### `bpkm:Milestone` (extends `gist:Event`)

A grouping of tasks toward a specific deliverable or deadline. Lighter than PPV's goal hierarchy — this is project-scoped, not life-scoped.

**Datatype Properties:**
| Property | Datatype | Constraints | Notes |
|---|---|---|---|
| `dcterms:title` | xsd:string | required | Milestone name |
| `dcterms:description` | xsd:string | maxCount 1 | What this milestone delivers |
| `bpkm:milestoneStatus` | xsd:string | `sh:in` (planned, active, completed, cancelled) | |
| `bpkm:targetDate` | xsd:date | maxCount 1 | Deadline |
| `bpkm:completedDate` | xsd:date | maxCount 1 | When it was finished |

**Object Properties:**
| Property | Range | Constraints | Notes |
|---|---|---|---|
| `bpkm:milestoneProject` | `bpkm:Project` | maxCount 1 | Parent project |
| `bpkm:hasTasks` | `bpkm:Task` | multi-value | Inverse of `bpkm:milestone` |

### Updated Project Type

The existing `bpkm:Project` gains:
- `bpkm:hasTasks` — inverse of `bpkm:taskProject` (auto-derived via OWL inverseOf)
- `bpkm:hasMilestones` — inverse of `bpkm:milestoneProject`

No other changes to Project. It remains the top-level organizational unit.

### SHACL Shapes

#### TaskShape (4 groups)

**Basic Info:**
- title (required)
- description
- taskStatus (required, default: "todo")
- priority
- effort

**Dates:**
- dueDate
- completedDate

**Relationships:**
- assignedTo (Person picker)
- taskProject (Project picker)
- milestone (Milestone picker)
- dependsOn (Task picker, multi-value)
- relatedNote (Note picker, multi-value)
- relatedConcept (Concept picker, multi-value)

**Metadata:**
- tags
- externalProvider (read-only for synced tasks)
- externalId (read-only for synced tasks)
- externalUrl (rendered as clickable link)
- lastSyncedAt (read-only)
- created, modified

**editHelpText examples:**
- taskStatus: "Current state of the task. Synced tasks update this automatically."
- externalProvider: "Which service this task was imported from. Set automatically during sync."
- dependsOn: "Tasks that must be completed before this one can start."
- effort: "Rough size estimate. Useful for planning capacity across projects."

#### MilestoneShape (3 groups)

**Basic Info:**
- title (required)
- description
- milestoneStatus (required, default: "planned")

**Dates:**
- targetDate
- completedDate

**Relationships:**
- milestoneProject (Project picker)
- hasTasks (Task list, read-only — populated via inverse)

### Views

**Task Table:** title, status, priority, dueDate, assignedTo, project, milestone, externalProvider
- Default sort: dueDate ascending, then priority descending
- Saved queries:
  - "My Open Tasks" — status != done && status != cancelled, sorted by due date
  - "Overdue Tasks" — dueDate < today && status != done
  - "Tasks by Provider" — grouped by externalProvider
  - "Blocked Tasks" — status == blocked OR has unfinished dependsOn

**Task Card:** title, status badge, priority badge, dueDate, assignedTo avatar, provider icon
- Group by: project, milestone, status, priority, provider

**Milestone Table:** title, status, targetDate, project, task count (derived)

**Task Graph:** Tasks as nodes, `dependsOn` as edges, colored by status. Shows dependency chains visually.

**Dashboard (pre-built):** "Task Hub"
- Block 1: Open tasks table (filtered, sorted by due date)
- Block 2: Tasks by status (card view, grouped)
- Block 3: Overdue tasks (table, highlighted)
- Block 4: Task dependency graph

### The Integration Hub Design

This is the strategic part. Tasks with `externalProvider` set are **synced objects** — they live in SemPKM's graph but have a counterpart in an external system.

#### How Sync Works (M009 App Platform)

Each provider integration is a **SemPKM App** (built on M009):

```
sempkm-app-linear/          # Linear integration app
├── manifest.yaml
├── requirements.txt         # linear-python SDK
├── app.py                   # App entrypoint
│   ├── @app.task("sync-tasks")     # Scheduled: pull tasks from Linear
│   ├── @app.task("push-changes")   # Scheduled: push local changes back
│   └── @app.on_install()           # OAuth setup for Linear
└── templates/
    └── settings.html        # Linear workspace/team selector
```

**Sync flow:**

```
Linear API ──pull──→ App (sync-tasks) ──POST /api/commands──→ SemPKM graph
                                                                    │
                                                              Task objects with
                                                              externalProvider: "linear"
                                                              externalId: "LIN-123"
                                                              externalUrl: "https://..."
                                                                    │
SemPKM graph ──event──→ App (push-changes) ──Linear API──→ Linear updated
```

**Sync semantics:**
- `pull`: App reads from provider, creates/updates Task objects in SemPKM
- `push`: App watches for changes to tasks with matching `externalProvider`, pushes updates back
- `bidirectional`: Both directions, with conflict resolution (last-write-wins or user-prompted)

**Field mapping per provider:**

| SemPKM Field | Linear | Jira | GitHub Issues | Asana | Todoist |
|---|---|---|---|---|---|
| title | title | summary | title | name | content |
| taskStatus | state → normalized | status → normalized | state → normalized | status → normalized | checked → normalized |
| priority | priority (1-4) → normalized | priority → normalized | labels → inferred | — | priority (1-4) → normalized |
| dueDate | dueDate | duedate | milestone.due_on | due_on | due.date |
| assignedTo | assignee → Person | assignee → Person | assignees → Person | assignee → Person | responsible_uid → Person |
| description | description | description | body | notes | description |
| externalId | identifier (LIN-123) | key (PROJ-123) | number (#42) | gid | id |
| tags | labels | labels | labels | tags | labels |

**Status normalization:** Each provider app maps provider-specific statuses to the universal `bpkm:taskStatus` enum:

```
Linear:   Backlog/Triage → todo, In Progress → in-progress, Done → done, Cancelled → cancelled
Jira:     To Do → todo, In Progress → in-progress, Done → done
GitHub:   open → todo, closed → done
Asana:    incomplete → todo, complete → done
Todoist:  unchecked → todo, checked → done
```

Apps can define richer mappings in their settings (e.g., map Jira's custom "In Review" status to "in-progress" or a custom status if the user extends the enum).

#### The Unified View

Once tasks from multiple providers are in the graph, the user gets:

1. **Single task table** showing ALL tasks regardless of source — with a provider column and icon
2. **Cross-provider queries:** "Show me all high-priority tasks due this week across Linear, Jira, and my manual tasks"
3. **Semantic connections:** A task from Linear can be linked to a Note, a Concept, a Person — relationships that don't exist in Linear itself
4. **Dependency mapping across providers:** A GitHub Issue can `dependsOn` a Jira ticket — visible in the task dependency graph
5. **Dashboard:** "Task Hub" shows everything in one place. Filter by provider, project, person, status, date range.

#### Provider Apps (M009/M010+)

Each integration is a separate SemPKM App:

| App | Provider | Sync | Priority |
|---|---|---|---|
| `sempkm-app-github` | GitHub Issues + PRs | Bidirectional | High (developers) |
| `sempkm-app-linear` | Linear | Bidirectional | High (startups) |
| `sempkm-app-todoist` | Todoist | Bidirectional | High (individuals) |
| `sempkm-app-jira` | Jira Cloud | Pull + push | Medium (enterprise) |
| `sempkm-app-asana` | Asana | Pull + push | Medium (teams) |
| `sempkm-app-trello` | Trello | Pull | Low (simple boards) |
| `sempkm-app-notion` | Notion databases | Pull | Low (migration path) |

These ship **after M009** since they're built on the app platform. But the basic-pkm v2 Task/Milestone types ship **before M009** — they work standalone for manual task management and are ready to receive synced data when the apps arrive.

### Seed Data Updates

Add to existing basic-pkm seed:

**Milestones:**
- "v1.0 Launch" (active, target: 2026-04-15, project: SemPKM Development)
- "Documentation Complete" (planned, target: 2026-04-01, project: SemPKM Development)

**Tasks:**
- "Write user guide for graph view" (in-progress, high priority, assigned: Alice, milestone: Documentation Complete, relatedNote: "Architecture Decision: Event Sourcing")
- "Fix validation edge case" (todo, medium priority, assigned: Bob, milestone: v1.0 Launch, dependsOn: none)
- "Review PR #42" (todo, low priority, assigned: Carol, project: SemPKM Development, externalProvider: github, externalId: "#42", externalUrl: "https://github.com/...")
- "Design onboarding flow" (blocked, high priority, assigned: Alice, dependsOn: "Write user guide for graph view")

This seed data demonstrates: manual tasks, synced tasks (the GitHub one), dependencies, milestone grouping, and cross-type relationships (task → note).

### SHACL Rules

**TaskProjectDenormRule:** If a Task has a Milestone, and that Milestone has a Project, derive `bpkm:taskProject` on the Task. (Mirrors PPV's pillar denormalization pattern — lets users assign tasks to milestones without explicitly setting the project.)

**OverdueTaskValidation:** SHACL validation rule: if `bpkm:dueDate < today` and `bpkm:taskStatus` not in (done, cancelled), emit `sh:Warning` with message "Task is overdue." Shows in the lint panel.

### Icon Additions to Manifest

```yaml
icons:
  # ... existing Project, Person, Note, Concept icons ...
  - type: "bpkm:Task"
    icon: "check-square"
    color: "#10b981"    # emerald
  - type: "bpkm:Milestone"
    icon: "flag"
    color: "#f59e0b"    # amber
```

### Migration Path

basic-pkm v1.3.0 → v2.0.0 is **additive only**:
- Two new classes (Task, Milestone)
- New properties on existing Project (hasTasks, hasMilestones — both via inverse)
- No changes to existing types, properties, or shapes
- Existing user data is untouched

Can be deployed via `refresh_artifacts` endpoint (clears and rewrites shapes/views/rules/ontology graphs without affecting ABox data).

---

## 2. Personal CRM

### Vision

Contact and relationship management for professionals. Demonstrates SemPKM's typed relationship advantage over flat CRM databases — every interaction, deal, and company connection is a first-class graph edge with provenance.

**Target persona:** Notion users who built a CRM database, professionals managing networks, freelancers tracking clients.

### Namespace

`urn:sempkm:model:crm:` (prefix: `crm:`)

### Types

#### `crm:Contact` (extends `gist:Person`)

**Datatype Properties:**
| Property | Datatype | Constraints | Notes |
|---|---|---|---|
| `foaf:name` | xsd:string | required | Full name |
| `schema:email` | xsd:string | multi-value | Email addresses |
| `schema:telephone` | xsd:string | multi-value | Phone numbers |
| `schema:jobTitle` | xsd:string | | Current role |
| `schema:url` | xsd:anyURI | multi-value | LinkedIn, Twitter, website |
| `crm:location` | xsd:string | | City / region |
| `crm:relationship` | xsd:string | `sh:in` (friend, colleague, client, prospect, mentor, mentee, other) | How you know them |
| `crm:metVia` | xsd:string | | How/where you met |
| `crm:notes` | xsd:string | | Free-text notes |
| `bpkm:tags` | xsd:string | multi-value | Tags |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `crm:worksAt` | `crm:Company` | Current employer |
| `crm:hasInteraction` | `crm:Interaction` | Inverse populated |
| `crm:hasDeal` | `crm:Deal` | Inverse populated |
| `crm:knows` | `crm:Contact` | Symmetric — mutual connection |

#### `crm:Company` (extends `gist:Organization`)

**Datatype Properties:**
| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Company name (required) |
| `schema:url` | xsd:anyURI | Website |
| `crm:industry` | xsd:string | Industry/sector |
| `crm:size` | xsd:string | `sh:in` (solo, small, medium, large, enterprise) |
| `crm:notes` | xsd:string | Free-text notes |
| `bpkm:tags` | xsd:string | Tags |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `crm:hasEmployee` | `crm:Contact` | Inverse of worksAt |
| `crm:hasDeal` | `crm:Deal` | Deals with this company |

#### `crm:Interaction` (extends `gist:Event`)

**Datatype Properties:**
| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Summary (required) |
| `crm:interactionType` | xsd:string | `sh:in` (call, email, meeting, coffee, lunch, conference, message, other) |
| `crm:interactionDate` | xsd:date | When it happened (required) |
| `crm:notes` | xsd:string | What was discussed |
| `crm:followUpDate` | xsd:date | When to follow up |
| `crm:followUpDone` | xsd:boolean | Has follow-up been completed |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `crm:withContact` | `crm:Contact` | Who you interacted with (multi-value) |

#### `crm:Deal` (extends `gist:Agreement`)

**Datatype Properties:**
| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Deal name (required) |
| `crm:dealStage` | xsd:string | `sh:in` (lead, qualified, proposal, negotiation, won, lost) |
| `crm:value` | xsd:decimal | Deal value |
| `crm:currency` | xsd:string | `sh:in` (USD, EUR, GBP) — default USD |
| `crm:closeDate` | xsd:date | Expected/actual close date |
| `crm:notes` | xsd:string | |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `crm:dealContact` | `crm:Contact` | Primary contact |
| `crm:dealCompany` | `crm:Company` | Company |

### SHACL-AF Rules

**StaleContactRule:** Validation warning if a Contact has no Interaction with `interactionDate` in the last 90 days. Message: "You haven't interacted with {name} in over 90 days."

**FollowUpOverdueRule:** Validation warning if an Interaction has `followUpDate < today` and `followUpDone != true`. Message: "Follow-up overdue for interaction with {contact}."

**LastContactedDeriveRule:** SPARQL rule derives `crm:lastContactedDate` on each Contact from their most recent Interaction's `interactionDate`. Enables sorting contacts by recency.

### Views

**Contact Table:** name, jobTitle, company, relationship, lastContactedDate, tags
**Contact Card:** name, jobTitle, company, avatar placeholder — grouped by relationship type
**Contact Graph:** Contacts as nodes, `knows` edges between them, `worksAt` edges to companies. Color by relationship type.

**Company Table:** name, industry, size, employee count (derived), deal count (derived)
**Interaction Timeline:** title, type, date, contacts — sorted by date descending (most recent first)
**Deal Pipeline:** Card view grouped by dealStage — the classic Kanban pipeline

**Saved Queries:**
- "Stale Contacts" — no interaction in 90 days
- "Upcoming Follow-ups" — followUpDate in next 7 days, not done
- "Open Deals" — dealStage not in (won, lost)
- "Network Map" — full contact graph with companies

**Pre-built Dashboard:** "CRM Overview"
- Block 1: Upcoming follow-ups (table)
- Block 2: Recent interactions (timeline)
- Block 3: Deal pipeline (cards by stage)
- Block 4: Network graph

### Seed Data

**Companies:**
- Acme Corp (technology, large)
- Bright Ideas Studio (design, small)
- DataFlow Inc (data analytics, medium)

**Contacts:**
- Sarah Park (CTO @ Acme Corp, client, met at conference)
- James Liu (Designer @ Bright Ideas, colleague, met via mutual friend)
- Priya Sharma (CEO @ DataFlow, prospect, met at meetup)
- Marcus Cole (Engineer, friend, knows James Liu)

**Interactions:**
- "Coffee with Sarah" (coffee, 2026-03-10, followUp: 2026-03-20)
- "Project kickoff call" (call, 2026-03-05, with Sarah and Priya)
- "Design review" (meeting, 2026-03-12, with James)

**Deals:**
- "Acme Corp consulting" (proposal stage, $15,000, contact: Sarah, company: Acme)
- "DataFlow integration" (lead stage, $8,000, contact: Priya, company: DataFlow)

### Icon Manifest

```yaml
icons:
  - type: "crm:Contact"
    icon: "user"
    color: "#6366f1"    # indigo
  - type: "crm:Company"
    icon: "building-2"
    color: "#8b5cf6"    # violet
  - type: "crm:Interaction"
    icon: "message-circle"
    color: "#14b8a6"    # teal
  - type: "crm:Deal"
    icon: "handshake"
    color: "#f59e0b"    # amber
```

### Browser Extension Integration

The CRM model + extension enables:
- Clip a LinkedIn profile as a Contact (schema.org Person data auto-fills name, jobTitle, company)
- Clip a company website as a Company
- Quick-log an interaction from Gmail (if reading an email thread)

---

## 3. Zettelkasten+

### Vision

The Zettelkasten method done right — with enforced note types, typed argumentation links, and provenance chains from source material through literature notes to permanent ideas. What Obsidian users build manually with YAML conventions, SemPKM enforces structurally.

**Target persona:** Obsidian power users, Zettelkasten practitioners, serious readers and writers.

### Namespace

`urn:sempkm:model:zk:` (prefix: `zk:`)

### Types

#### `zk:FleetingNote` (extends `gist:FormattedContent`)

Raw captures. Unprocessed. Short-lived by design — the inbox of the Zettelkasten.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. Brief title or first line. |
| `zk:body` | xsd:string | The raw thought, quote, or observation. Markdown. |
| `zk:capturedFrom` | xsd:anyURI | URL if captured from web |
| `zk:processedInto` | `zk:LiteratureNote` or `zk:PermanentNote` | What this became (set when processed) |
| `bpkm:tags` | xsd:string | Quick tags |

#### `zk:Source` (extends `gist:Content`)

A book, article, paper, podcast, video, or any external work that you're reading/consuming.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. Title of the work. |
| `dcterms:creator` | xsd:string | Author(s) |
| `zk:sourceType` | xsd:string | `sh:in` (book, article, paper, podcast, video, talk, course, other) |
| `schema:datePublished` | xsd:date | Publication date |
| `schema:url` | xsd:anyURI | URL / DOI / ISBN link |
| `zk:notes` | xsd:string | Your overall notes/review of this source |
| `zk:rating` | xsd:integer | 1-5 stars (optional) |
| `bpkm:tags` | xsd:string | Tags |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `zk:hasLiteratureNote` | `zk:LiteratureNote` | Inverse of derivedFrom |

#### `zk:LiteratureNote` (extends `gist:FormattedContent`)

A note that captures someone else's idea — always tied to a Source. Written in your words but representing the author's thinking.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. The idea being captured. |
| `zk:body` | xsd:string | Your summary of the idea. Markdown. |
| `zk:originalQuote` | xsd:string | The exact quote from the source (optional) |
| `zk:pageReference` | xsd:string | Page number, timestamp, or location in source |
| `bpkm:tags` | xsd:string | Tags |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `zk:derivedFrom` | `zk:Source` | Required. Which source this came from. |
| `zk:developedInto` | `zk:PermanentNote` | What permanent idea this spawned |

#### `zk:PermanentNote` (extends `gist:FormattedContent`)

An atomic idea in your own words. The core unit of the Zettelkasten. One idea per note. Written as if explaining to someone else.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. The idea as a clear statement. |
| `zk:body` | xsd:string | Required. Full explanation. Markdown. Should be self-contained. |
| `zk:sequenceId` | xsd:string | Optional Luhmann-style ID (e.g., "1a2b3") for manual ordering |
| `bpkm:tags` | xsd:string | Tags |

**Object Properties (the argumentation links):**
| Property | Range | Notes |
|---|---|---|
| `zk:supports` | `zk:PermanentNote` | This idea supports that idea |
| `zk:contradicts` | `zk:PermanentNote` | This idea contradicts that idea |
| `zk:followsFrom` | `zk:PermanentNote` | This idea is a logical consequence of that idea |
| `zk:relatedTo` | `zk:PermanentNote` | Weaker association — worth exploring |
| `zk:developedFrom` | `zk:LiteratureNote` | Provenance: which literature note sparked this |
| `zk:includedinStructure` | `zk:StructureNote` | Which structure notes include this |

#### `zk:StructureNote` (extends `gist:FormattedContent`)

A curated outline that organizes permanent notes into a coherent sequence, argument, or topic overview. The Zettelkasten's "table of contents."

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. Topic or argument name. |
| `zk:body` | xsd:string | Outline/commentary connecting the notes. Markdown with links. |
| `zk:purpose` | xsd:string | `sh:in` (topic-overview, argument, sequence, literature-review, project-outline) |
| `bpkm:tags` | xsd:string | Tags |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `zk:includes` | `zk:PermanentNote` | Notes in this structure (multi-value, ordered via `sh:order`) |
| `zk:relatedStructure` | `zk:StructureNote` | Connected outlines |

### The Provenance Chain

This is the killer feature. Every permanent idea traces back to its origins:

```
Source (book/article)
  └── derivedFrom ←── LiteratureNote (author's idea in your words)
                          └── developedFrom ←── PermanentNote (your own idea)
                                                    ├── supports ──→ PermanentNote
                                                    ├── contradicts ──→ PermanentNote
                                                    └── included in ──→ StructureNote
```

SPARQL query: "For this permanent note, show me the full provenance chain back to the original source" — impossible in Obsidian without custom Dataview gymnastics. Native in SemPKM.

### SHACL-AF Rules

**UnprocessedFleetingRule:** Validation warning if a FleetingNote is older than 7 days and has no `processedInto` link. Message: "This fleeting note hasn't been processed. Develop it into a literature or permanent note, or delete it."

**OrphanPermanentNoteRule:** Validation warning if a PermanentNote has no `supports`, `contradicts`, `followsFrom`, or `includedinStructure` relationships. Message: "This permanent note is isolated. Connect it to other ideas or include it in a structure note."

**UnsupportedClaimRule:** Validation info if a PermanentNote has no `developedFrom` link to any LiteratureNote. Message: "This idea has no literature source. Consider linking it to supporting evidence."

### Views

**Inbox:** FleetingNote table, sorted by created date descending. "Processing queue" feel.
**Sources Library:** Source table with title, author, type, date, literature note count (derived).
**Literature Notes by Source:** Card view grouped by Source. Shows the reading extraction pipeline.
**Zettelkasten Graph:** PermanentNote nodes with `supports`/`contradicts`/`followsFrom` edges. Color-coded: green (supports), red (contradicts), blue (follows-from), gray (related). This is the actual Zettelkasten rendered as a graph.
**Structure Outlines:** StructureNote list with included note count.

**Saved Queries:**
- "Unprocessed Fleeting Notes" — older than 3 days, no processedInto
- "Isolated Permanent Notes" — no argumentation links
- "Contradiction Map" — all PermanentNote pairs connected by `contradicts`
- "Provenance Chain" — parameterized: given a PermanentNote, show Source → LiteratureNote → PermanentNote chain

**Pre-built Dashboard:** "Zettelkasten Workbench"
- Block 1: Fleeting note inbox (table)
- Block 2: Zettelkasten graph (argumentation map)
- Block 3: Recently added permanent notes (cards)
- Block 4: Isolated notes needing connections (table)

### Seed Data

**Sources:**
- "How to Take Smart Notes" by Sönke Ahrens (book, 2017)
- "The Art of Thinking Clearly" by Rolf Dobelli (book, 2013)
- "Networked Thought" (article, 2024, URL)

**Fleeting Notes:**
- "Interesting point about externalized thinking..." (3 days old, unprocessed)
- "Connection between Luhmann's slip-box and modern PKM" (1 day old)

**Literature Notes:**
- "Ahrens: Writing is thinking made explicit" (from Smart Notes, p. 45)
- "Ahrens: The slip-box forces elaboration" (from Smart Notes, p. 78)
- "Dobelli: Confirmation bias in note-taking" (from Thinking Clearly, p. 12)

**Permanent Notes:**
- "Externalized thinking reduces cognitive load" (developed from Ahrens lit note)
- "Structure emerges from connections, not planning" (developed from Ahrens lit note, supports "externalized thinking")
- "Confirmation bias threatens knowledge systems" (developed from Dobelli lit note, contradicts uncritical note-taking)

**Structure Note:**
- "The Case for Structured Note-Taking" (includes: externalized thinking + structure emerges + confirmation bias, purpose: argument)

### Icon Manifest

```yaml
icons:
  - type: "zk:FleetingNote"
    icon: "zap"
    color: "#f59e0b"    # amber — ephemeral, attention-grabbing
  - type: "zk:Source"
    icon: "book-open"
    color: "#6366f1"    # indigo
  - type: "zk:LiteratureNote"
    icon: "quote"
    color: "#8b5cf6"    # violet — derived from source
  - type: "zk:PermanentNote"
    icon: "gem"
    color: "#10b981"    # emerald — the valuable output
  - type: "zk:StructureNote"
    icon: "network"
    color: "#0ea5e9"    # sky blue — organizational
```

### Browser Extension Integration

The Zettelkasten model + extension is the strongest combo:

1. Reading an article → highlight a passage → "Save as Literature Note"
2. Extension auto-creates the Source (from page URL/title/author) if it doesn't exist
3. Creates the LiteratureNote with `derivedFrom → Source` edge
4. Selected text goes into `originalQuote`, page URL into source
5. User writes their summary in `body`
6. Later, from within SemPKM, user develops literature notes into permanent notes

The Phase 2 context overlay enhances this further: while reading, the sidebar shows "You have 3 permanent notes related to this article's topic. One contradicts a claim made here."

---

## 4. Research Workflow

### Vision

Claims-first academic PKM. The atomic unit isn't a note — it's a **claim with evidence and provenance**. Designed for literature reviews, systematic research, and argument construction.

**Target persona:** Academic researchers, graduate students, science writers, policy analysts.

### Namespace

`urn:sempkm:model:research:` (prefix: `res:`)

### Types

#### `res:Paper` (extends `gist:Content`)

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required |
| `dcterms:creator` | xsd:string | Author(s), multi-value |
| `res:venue` | xsd:string | Journal, conference, publisher |
| `res:year` | xsd:gYear | Publication year |
| `res:doi` | xsd:anyURI | DOI link |
| `res:abstract` | xsd:string | Paper abstract |
| `res:paperType` | xsd:string | `sh:in` (journal-article, conference-paper, preprint, book-chapter, thesis, report, other) |
| `bpkm:tags` | xsd:string | Tags / keywords |
| `res:notes` | xsd:string | Personal reading notes |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `res:hasClaim` | `res:Claim` | Claims extracted from this paper (inverse) |
| `res:cites` | `res:Paper` | Papers this paper references |
| `res:citedBy` | `res:Paper` | Inverse of cites |

#### `res:Claim` (extends `gist:FormattedContent`)

An atomic assertion — something that can be true or false, supported or refuted.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. The claim as a clear statement. |
| `res:claimBody` | xsd:string | Elaboration. Markdown. |
| `res:confidence` | xsd:string | `sh:in` (established, supported, contested, speculative, refuted) |
| `res:domain` | xsd:string | Research area / field |
| `bpkm:tags` | xsd:string | Tags |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `res:extractedFrom` | `res:Paper` | Which paper this claim comes from |
| `res:supportedBy` | `res:Evidence` | Evidence that supports this claim (inverse) |
| `res:refutedBy` | `res:Evidence` | Evidence that refutes this claim (inverse) |
| `res:corroborates` | `res:Claim` | Another claim that agrees |
| `res:contradicts` | `res:Claim` | Another claim that disagrees |
| `res:dependsOn` | `res:Claim` | Prerequisite claim |
| `res:addressedBy` | `res:Argument` | Arguments that use this claim (inverse) |

#### `res:Evidence` (extends `gist:FormattedContent`)

A specific data point, quote, finding, or observation that supports or refutes a claim.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. Brief description of the evidence. |
| `res:evidenceBody` | xsd:string | The evidence detail. Markdown. |
| `res:evidenceType` | xsd:string | `sh:in` (empirical-data, statistical-finding, case-study, expert-opinion, logical-argument, observation, quote) |
| `res:pageReference` | xsd:string | Page/section in source |
| `res:methodology` | xsd:string | How the evidence was obtained |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `res:supports` | `res:Claim` | Required. Which claim this supports. |
| `res:refutes` | `res:Claim` | Which claim this refutes (alternative to supports). |
| `res:fromPaper` | `res:Paper` | Source paper |

#### `res:ResearchQuestion`

The driving question that motivates an argument or literature review.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. The question. |
| `res:questionBody` | xsd:string | Context, motivation, scope. |
| `res:status` | xsd:string | `sh:in` (open, partially-answered, answered, abandoned) |
| `res:domain` | xsd:string | Research area |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `res:hasArgument` | `res:Argument` | Arguments addressing this question (inverse) |

#### `res:Argument` (extends `gist:FormattedContent`)

A structured synthesis connecting claims and evidence to address a research question.

| Property | Datatype | Notes |
|---|---|---|
| `dcterms:title` | xsd:string | Required. The argument's thesis. |
| `res:argumentBody` | xsd:string | Full argument. Markdown. |
| `res:argumentType` | xsd:string | `sh:in` (literature-review, position-paper, analysis, synthesis, rebuttal) |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `res:addresses` | `res:ResearchQuestion` | Which question this argument answers |
| `res:usesClaim` | `res:Claim` | Claims used in this argument (ordered) |
| `res:usesEvidence` | `res:Evidence` | Direct evidence references |

### SHACL-AF Rules

**UnsupportedClaimRule:** Warning if a Claim has `confidence` of "established" or "supported" but no linked Evidence with `supports` relationship. Message: "Claim marked as {confidence} but has no supporting evidence."

**ContestedClaimDetection:** Info if a Claim has both `supportedBy` and `refutedBy` evidence. Message: "This claim has conflicting evidence — review the argument."

**OrphanEvidenceRule:** Warning if Evidence has neither `supports` nor `refutes` link. Message: "This evidence isn't linked to any claim."

**UnansweredQuestionRule:** Info if a ResearchQuestion has status "open" and no linked Arguments. Message: "This research question has no arguments yet."

### Views

**Paper Library:** Table with title, authors, venue, year, claim count (derived).
**Claims by Confidence:** Card view grouped by confidence level. Visual overview of knowledge certainty.
**Evidence Map:** Graph view — Claims as nodes, Evidence as edges colored green (supports) or red (refutes). Papers as source nodes.
**Argument Builder:** StructureNote-like view showing an Argument with its Claims and Evidence in sequence.
**Citation Graph:** Paper → Paper via `cites` edges. Shows the literature network.

**Saved Queries:**
- "Unsupported Claims" — claims with no evidence
- "Contested Claims" — claims with both supporting and refuting evidence
- "Claims without Papers" — claims not extracted from any paper (user-generated)
- "Open Questions" — research questions with status "open"
- "Evidence Gaps" — claims marked speculative with no evidence at all

**Pre-built Dashboard:** "Research Command Center"
- Block 1: Paper library (table, sortable)
- Block 2: Claims by confidence (cards)
- Block 3: Evidence map (graph)
- Block 4: Open research questions (table)

### Seed Data

**Papers:**
- "The Semantic Web" by Tim Berners-Lee et al. (2001, journal-article, Scientific American)
- "Knowledge Graphs: Methodology, Tools and Selected Use Cases" by Fensel et al. (2020, book-chapter)
- "Personal Knowledge Management: A Systematic Review" (2023, journal-article)

**Claims:**
- "Semantic Web standards enable interoperable knowledge systems" (established, from Berners-Lee)
- "Knowledge graphs reduce information silos" (supported, from Fensel)
- "Most PKM tools fail at long-term knowledge retention" (contested, from systematic review)
- "RDF scales better than property graphs for heterogeneous data" (speculative, user-generated)

**Evidence:**
- "Linked Open Data Cloud contains 1,200+ datasets using RDF" (empirical-data, supports semantic web claim)
- "Survey of 200 organizations showed 73% reduction in duplicate data after KG adoption" (statistical-finding, supports knowledge graphs claim)
- "Longitudinal study found 60% of notes abandoned after 6 months" (empirical-data, supports PKM failure claim)
- "Counter-study found structured note-takers retained 40% more after 1 year" (empirical-data, refutes PKM failure claim)

**Research Question:**
- "How can semantic structure improve personal knowledge retention?" (open)

**Argument:**
- "Structured PKM systems prevent knowledge decay" (literature-review, addresses the question, uses claims 1-3)

### Icon Manifest

```yaml
icons:
  - type: "res:Paper"
    icon: "file-text"
    color: "#6366f1"    # indigo
  - type: "res:Claim"
    icon: "message-square-quote"
    color: "#f59e0b"    # amber
  - type: "res:Evidence"
    icon: "flask-conical"
    color: "#10b981"    # emerald
  - type: "res:ResearchQuestion"
    icon: "help-circle"
    color: "#ef4444"    # red — demands attention
  - type: "res:Argument"
    icon: "scale"
    color: "#8b5cf6"    # violet
```

### Browser Extension Integration

- Clip from PubMed/arXiv/Google Scholar as Paper (auto-fill from schema.org ScholarlyArticle or DOI metadata)
- Highlight a passage → "Save as Evidence" → link to existing Claim
- Phase 2 context overlay: "You have 2 Claims related to this paper. One has no evidence yet."

---

---

## 5. Calendar Hub (basic-pkm v2.0 extension)

### Vision

Same philosophy as the task hub: SemPKM becomes the **unified calendar view** across all your calendar providers. Google Calendar, Outlook, Apple Calendar, CalDAV — all synced into typed Event objects that live in your knowledge graph and can be linked to Contacts, Projects, Tasks, Notes, and Concepts.

The power isn't just aggregation — it's **semantic enrichment**. A calendar event in Google Calendar is just a title, time, and attendee list. In SemPKM, that same event is linked to the Project it belongs to, the Tasks it generated, the Notes taken during it, and the Contacts who attended. After the meeting, you annotate the event with outcomes and action items — and those connections persist in your graph forever.

### Why This Belongs in basic-pkm (Not a Separate Model)

Calendar events are fundamental to how people work. They're not a niche methodology (like Zettelkasten) or a domain workflow (like Research). Events connect to everything:
- Events have attendees → **Persons** (and CRM Contacts)
- Events belong to → **Projects**
- Events generate → **Tasks** (action items)
- Events produce → **Notes** (meeting notes)
- Events relate to → **Concepts** (topics discussed)

Putting events in basic-pkm means every user gets calendar integration out of the box.

### New Types

#### `bpkm:Event` (extends `gist:Event`)

A calendar event — meeting, appointment, deadline, reminder, or time block.

**Datatype Properties:**
| Property | Datatype | Constraints | Notes |
|---|---|---|---|
| `dcterms:title` | xsd:string | required | Event title |
| `dcterms:description` | xsd:string | maxCount 1 | Event description / agenda |
| `bpkm:eventType` | xsd:string | `sh:in` (meeting, appointment, deadline, reminder, focus-block, social, travel, other) | What kind of event |
| `schema:startDate` | xsd:dateTime | required | Start time |
| `schema:endDate` | xsd:dateTime | | End time |
| `bpkm:allDay` | xsd:boolean | default false | All-day event flag |
| `bpkm:location` | xsd:string | | Physical location or video link |
| `bpkm:recurrence` | xsd:string | | RRULE string (iCal format) for recurring events |
| `bpkm:eventStatus` | xsd:string | `sh:in` (confirmed, tentative, cancelled) | |
| `bpkm:meetingNotes` | xsd:string | | Post-meeting notes. Markdown. |
| `bpkm:tags` | xsd:string | multi-value | Tags |

**Integration Properties (for synced events):**
| Property | Datatype | Notes |
|---|---|---|
| `bpkm:externalId` | xsd:string | Provider's event ID |
| `bpkm:externalUrl` | xsd:anyURI | Link to event in provider's UI |
| `bpkm:externalProvider` | xsd:string | `sh:in` (google-calendar, outlook, apple-calendar, caldav, manual) |
| `bpkm:calendarName` | xsd:string | Which calendar within the provider (e.g., "Work", "Personal") |
| `bpkm:lastSyncedAt` | xsd:dateTime | Last sync timestamp |

**Object Properties:**
| Property | Range | Notes |
|---|---|---|
| `bpkm:attendee` | `bpkm:Person` | Who's attending (multi-value) |
| `bpkm:eventProject` | `bpkm:Project` | Which project this relates to |
| `bpkm:generatedTask` | `bpkm:Task` | Action items from this event |
| `bpkm:eventNote` | `bpkm:Note` | Meeting notes linked to this event |
| `bpkm:relatedConcept` | `bpkm:Concept` | Topics discussed |

### SHACL Shape

#### EventShape (4 groups)

**Basic Info:**
- title (required)
- eventType
- eventStatus
- description

**Schedule:**
- startDate (required)
- endDate
- allDay
- location
- recurrence (advanced, with editHelpText explaining RRULE format)

**Relationships:**
- attendee (Person picker, multi-value)
- eventProject (Project picker)
- generatedTask (Task picker, multi-value)
- eventNote (Note picker, multi-value)
- relatedConcept (Concept picker, multi-value)

**Metadata:**
- tags
- meetingNotes (large text area — post-meeting capture)
- externalProvider (read-only for synced events)
- calendarName (read-only for synced events)
- externalUrl (clickable link)
- lastSyncedAt (read-only)

### Views

**Calendar Table:** title, eventType, startDate, endDate, attendees, project, provider
- Default sort: startDate ascending
- Saved queries:
  - "Today's Events" — startDate is today
  - "This Week" — startDate within current week
  - "Upcoming with No Notes" — future events that have passed but no meetingNotes filled in
  - "Events by Calendar" — grouped by calendarName/externalProvider

**Event Card:** title, date/time, eventType badge, attendee count, provider icon
- Group by: eventType, project, calendarName, provider

**Event Timeline:** Vertical timeline view sorted by date (if this renderer exists; otherwise card view sorted by startDate)

**Event-Contact Graph:** Events as center nodes, attendees as connected nodes. Shows "who do I meet with most?" network.

**Pre-built Dashboard:** "Calendar Hub"
- Block 1: Today's events (table)
- Block 2: This week overview (cards by day)
- Block 3: Events needing notes (table — past events with no meetingNotes)
- Block 4: Meeting network (graph — event-contact connections)

### The Unified Calendar Story

Like tasks, each calendar provider integration is a **SemPKM App** (M009):

| App | Provider | Sync | Priority |
|---|---|---|---|
| `sempkm-app-google-calendar` | Google Calendar | Bidirectional | High |
| `sempkm-app-outlook` | Microsoft Outlook/365 | Bidirectional | High |
| `sempkm-app-caldav` | Any CalDAV server (Apple, Fastmail, Nextcloud) | Bidirectional | Medium |
| `sempkm-app-ical` | ICS file import | Pull only | Low (one-time imports) |

**Sync flow (same pattern as tasks):**

```
Google Calendar API ──pull──→ App ──POST /api/commands──→ SemPKM graph
                                                              │
                                                        Event objects with
                                                        externalProvider: "google-calendar"
                                                        calendarName: "Work"
                                                              │
SemPKM (event edited) ──push──→ App ──Google Calendar API──→ Updated in Google
```

**Multi-calendar unification:**
- A user has Google Calendar (work), Outlook (personal), and a shared CalDAV calendar
- All three sync into SemPKM as `bpkm:Event` objects with different `externalProvider` and `calendarName` values
- Single table/card/graph view shows ALL events across all calendars
- Cross-provider queries: "Show me all meetings this week where Sarah Park (CRM Contact) is an attendee, across all my calendars"

**Attendee → Person/Contact linking:**
- Synced events include attendee email addresses
- Integration apps match emails against existing `bpkm:Person` objects (via `foaf:mbox`) and `crm:Contact` objects (via `schema:email`)
- If a match is found: the `bpkm:attendee` edge links to the existing Person/Contact
- If no match: app can auto-create a stub Person with name + email, or leave unlinked
- This means your meeting network and your CRM network are the **same graph**

### SHACL-AF Rules

**MeetingNotesReminder:** Validation info if an Event has `schema:endDate` in the past, `eventType` is "meeting", and `meetingNotes` is empty. Message: "This meeting has ended but has no notes. Add meeting notes or action items."

**EventTaskReminder:** Validation info if an Event has `eventType` "meeting" and `generatedTask` is empty and event is in the past. Message: "No action items captured from this meeting."

### Seed Data Additions

**Events:**
- "Weekly Team Standup" (meeting, recurring weekly, confirmed, attendees: Alice & Bob, project: SemPKM Development)
- "Design Review with Carol" (meeting, 2026-03-18, attendees: Carol, project: Knowledge Garden, meetingNotes: "Discussed graph layout options...")
- "Sprint Planning" (meeting, 2026-03-20, attendees: Alice & Bob & Carol, externalProvider: google-calendar, calendarName: "Work")
- "Dentist Appointment" (appointment, 2026-03-22, allDay: false, externalProvider: google-calendar, calendarName: "Personal")

### Icon Addition

```yaml
  - type: "bpkm:Event"
    icon: "calendar"
    color: "#3b82f6"    # blue
```

### Cross-Type Power

With Task + Event + existing types all in basic-pkm, the graph becomes a complete operational hub:

```
Project ──hasTasks──→ Task ──assignedTo──→ Person
   │                   │                      │
   └──hasMilestones──→ Milestone         ←attendee── Event
   │                                          │
   └──hasNote──→ Note ←──eventNote────────────┘
   │                                          │
   └──hasParticipant──→ Person ──participatesIn──→ Project
```

**Example query:** "Show me all events, tasks, and notes related to the SemPKM project this week, with the people involved" — a single SPARQL query across the unified graph. Impossible when your calendar is in Google, tasks are in Linear, and notes are in Obsidian.

---

## Summary: Launch Lineup

| Model | Types | Persona | Status |
|---|---|---|---|
| **basic-pkm v2.0** | 7 (Project, Person, Note, Concept, **Task**, **Milestone**, **Event**) | Everyone | Upgrade existing |
| **ppv** | 11 | Goal planners | Shipped |
| **Personal CRM** | 4 (Contact, Company, Interaction, Deal) | Professionals, Notion users | New |
| **Zettelkasten+** | 5 (FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote) | Obsidian users, readers/writers | New |
| **Research Workflow** | 5 (Paper, Claim, Evidence, ResearchQuestion, Argument) | Academics, researchers | New |

**Total types across all models:** 32
**Total at launch:** 5 models + gist foundation

### Build Order

1. **basic-pkm v2.0** — Highest impact, additive to existing model, enables task hub story
2. **Personal CRM** — Broadest appeal, strongest Notion conversion angle
3. **Zettelkasten+** — Strongest Obsidian conversion angle
4. **Research Workflow** — Strongest differentiator, best demo material, but narrower audience

### Cross-Model Relationships

Models can reference each other's types via shared upper ontology (gist):

- A CRM Interaction can link to a basic-pkm Note (meeting notes)
- A Research Paper can link to a CRM Contact (the author you know personally)
- A Zettelkasten PermanentNote can link to a basic-pkm Concept
- A basic-pkm Task can reference a Research Paper ("Review this paper")

This is enabled by gist as the common foundation — all Person types extend `gist:Person`, all content types extend `gist:FormattedContent`, etc. The graph doesn't care which model created the object.
