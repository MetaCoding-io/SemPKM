# Chapter 39: Mental Model Catalog

SemPKM ships with several mental models that define domain-specific types, forms, views, validation rules, and saved queries. This chapter documents the models available for installation, including field references, relationships, validation behavior, and recommended dashboard configurations.

> **Note:** Dashboards cannot be bundled inside model archives. The "Recommended Dashboard" sections below describe configurations you can build manually after installing a model. See [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) for how to create dashboards.

For background on what mental models are and how they work, see [Chapter 9: Understanding Mental Models](09-understanding-mental-models.md). For installation and management, see [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

---

## 1. Basic PKM v2.0 — Project Management

**Model ID:** `basic-pkm` · **Version:** 2.0.0 · **Namespace:** `urn:sempkm:model:basic-pkm:`

The Basic PKM model is the default model installed with every SemPKM instance. It provides six types for general-purpose personal knowledge management: **Note**, **Concept**, **Project**, **Person**, **Task**, and **Milestone**.

### What's New in v2.0

Version 2.0 adds **Task** and **Milestone** types to the original four types (Note, Concept, Project, Person). Tasks represent individual work items with status tracking, priority, effort sizing, and due dates. Milestones group related tasks toward a deliverable or deadline. Together they turn SemPKM into a lightweight project management system layered on top of your knowledge base.

### Types

#### Note

A single idea, observation, or reference. Notes are the atomic building blocks of your knowledge base.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A concise title capturing the core idea |
| Body | string | | Main content (Markdown supported) |
| Type | enum | | `observation`, `idea`, `reference`, `meeting-note`, `journal` |
| About Concepts | → Concept | | Concepts this note discusses |
| Related Project | → Project | | The project this note belongs to |
| Source URL | URI | | Link to the original source |
| Tags | string[] | | Free-form labels |

#### Concept

A topic or theme that notes can be *about*. Concepts form a hierarchy via broader/narrower links.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Label | string | ✓ | Primary name for the concept |
| Alternative Labels | string[] | | Synonyms or abbreviations |
| Definition | string | | What this concept means in your own words |
| Broader Concepts | → Concept | | Parent concepts |
| Narrower Concepts | → Concept | | More specific sub-concepts |
| Related Concepts | → Concept | | Lateral associations |
| Reference URL | URI | | Link to an authoritative source |
| Tags | string[] | | Free-form labels |

#### Project

A goal or initiative that organizes notes, people, tasks, and milestones.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Display name for the project |
| Description | string | | Brief summary of purpose and scope |
| Status | enum | | `active`, `completed`, `on-hold`, `cancelled` (default: `active`) |
| Priority | enum | | `low`, `medium`, `high`, `critical` (default: `medium`) |
| Start Date | date | | When the project began or is planned to begin |
| End Date | date | | When the project finished or is expected to finish |
| Participants | → Person | | People involved |
| Notes | → Note | | Related notes |
| Tasks | → Task | | Tasks belonging to this project |
| Milestones | → Milestone | | Milestones for this project |
| Tags | string[] | | Free-form labels |

#### Person

A contact or collaborator you interact with.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Name | string | ✓ | Full name |
| Email | string | | Primary email address |
| Job Title | string | | Role or position |
| Organization | string | | Company or institution |
| Phone | string | | Phone number |
| URL | URI | | Website or profile link |
| Notes | string | | Free-form notes about this person |
| Tags | string[] | | Free-form labels |
| Projects | → Project | | Projects this person is involved in |
| Assigned Tasks | → Task | | Tasks assigned to this person |

#### Task

A unit of work with status tracking, priority, effort sizing, and due dates.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Clear, actionable task title |
| Description | string | | Acceptance criteria or details |
| Status | enum | | `todo`, `in-progress`, `done`, `blocked`, `cancelled` (default: `todo`) |
| Priority | enum | | `low`, `medium`, `high`, `critical` (default: `medium`) |
| Effort | enum | | `trivial`, `small`, `medium`, `large`, `epic` |
| Due Date | date | | When this task is due |
| Completed Date | date | | When the task was finished |
| Assigned To | → Person | | Person responsible |
| Project | → Project | | Parent project |
| Milestone | → Milestone | | Which milestone this task belongs to |
| Depends On | → Task | | Tasks that must complete first |
| Related Notes | → Note | | Contextual notes |
| Related Concepts | → Concept | | Topic tags via concept links |
| Tags | string[] | | Free-form labels |

Tasks also support external sync fields (External Provider, External ID, External URL, Last Synced) for integration with tools like Linear, Jira, or GitHub.

#### Milestone

A project phase that groups related tasks toward a deliverable or deadline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Milestone name (e.g., "Beta Launch") |
| Description | string | | What this milestone delivers |
| Status | enum | | `planned`, `active`, `completed`, `cancelled` (default: `planned`) |
| Target Date | date | | Deadline for this milestone |
| Completed Date | date | | When the milestone was actually completed |
| Project | → Project | | Parent project |
| Tasks | → Task | | Tasks contributing to this milestone |
| Tags | string[] | | Free-form labels |

### Relationships

```
Project ──hasParticipant──▸ Person
Project ──hasNote──▸ Note
Project ──hasProjectTasks──▸ Task
Project ──hasMilestones──▸ Milestone
Task ──assignedTo──▸ Person (inverse: hasAssignedTask)
Task ──taskProject──▸ Project
Task ──milestone──▸ Milestone
Task ──dependsOn──▸ Task
Milestone ──milestoneProject──▸ Project
Milestone ──hasTasks──▸ Task
Note ──isAbout──▸ Concept
Note ──relatedProject──▸ Project
Concept ──broader/narrower──▸ Concept
```

### Saved Queries

| Query | Description |
|-------|-------------|
| **My Open Tasks** | Tasks with status `todo` or `in-progress` |
| **Overdue Tasks** | Tasks past their due date that are not done or cancelled |
| **Blocked Tasks** | Tasks with status `blocked` |
| Active Projects | Projects with status `active` |
| Recent Notes | Notes sorted by creation date |
| Concept Hierarchy | Concept tree via broader/narrower links |

### Validation Rules

| Rule | Severity | Message |
|------|----------|---------|
| Overdue task | Warning | "Task is overdue: due date has passed but task is not done or cancelled." |

This rule fires automatically via SHACL-AF when a task's due date is in the past and its status is still `todo` or `in-progress`.

### Installation

Basic PKM is installed by default. To upgrade to v2.0 (adding Task and Milestone types), go to **Admin > Mental Models** and click **Refresh** on the Basic PKM entry.

### Recommended Dashboard

Use a **sidebar-main** layout:

- **Sidebar:** Embed the "My Open Tasks" saved query as a view-embed block. This gives you a persistent task list for quick scanning.
- **Main:** Add a view-embed block showing the Tasks Table view, filtered by the selected task from the sidebar using cross-view context.

Optionally add a second dashboard with a **grid-2x2** layout showing Active Projects (top-left), My Open Tasks (top-right), Overdue Tasks (bottom-left), and Blocked Tasks (bottom-right) for a project management overview.

---

## 2. Personal CRM

**Model ID:** `crm` · **Version:** 1.0.0 · **Namespace:** `urn:sempkm:model:crm:`

The Personal CRM model helps you manage professional and personal relationships. Track contacts, companies, interactions, and business deals through a pipeline.

### Types

#### Contact

A person in your network.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| First Name | string | ✓ | Given name |
| Last Name | string | ✓ | Family name |
| Email | string | | Primary email address |
| Phone | string | | Phone number |
| Role | string | | Job title or role at their company |
| Works At | → Company | | Company where this contact works |
| Relationship | enum | | `colleague`, `client`, `friend`, `mentor`, `vendor`, `other` |
| Knows | → Contact | | Other contacts this person knows (mutual) |
| Follow-up Date | date | | Date by which to follow up |
| Follow-up Done | boolean | | Whether the follow-up is completed |
| Tags | string[] | | Free-form labels |
| Notes | string | | Free-form notes about this contact |

#### Company

An organization your contacts work at.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Company Name | string | ✓ | Display name |
| Industry | string | | Industry sector (e.g., Technology, Healthcare) |
| Website | string | | Company website URL |
| Company Size | enum | | `solo`, `small`, `medium`, `large`, `enterprise` |
| Employees | → Contact | | Contacts who work here (auto-populated) |
| Notes | string | | Free-form notes |

#### Interaction

A recorded touchpoint with one or more contacts.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Type | enum | ✓ | `meeting`, `call`, `email`, `coffee`, `conference`, `other` |
| Date | date | ✓ | When the interaction took place |
| Summary | string | | Brief summary of what was discussed |
| With Contact | → Contact | ✓ | Contact(s) involved (at least one required) |
| Follow-up Date | date | | When to follow up |
| Follow-up Done | boolean | | Whether the follow-up is completed |

#### Deal

A business opportunity tracked through a pipeline.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Deal Name | string | ✓ | Name or title of the deal |
| Stage | enum | ✓ | `lead`, `qualified`, `proposal`, `negotiation`, `won`, `lost` |
| Value | decimal | | Monetary value |
| Currency | enum | | `USD`, `EUR`, `GBP` (default: `USD`) |
| Contact | → Contact | | Primary contact for this deal |
| Company | → Company | | Company associated with this deal |
| Notes | string | | Deal-specific context |

### Pipeline Concept

Deal stages form a linear pipeline reflecting opportunity progression:

```
lead → qualified → proposal → negotiation → won / lost
```

Use the "Open Deals" saved query to see all deals not yet at `won` or `lost`. Filter the Deals Table view by stage to build a pipeline board.

### Relationships

```
Contact ──worksAt──▸ Company (inverse: hasEmployee)
Contact ──knows──▸ Contact (symmetric)
Interaction ──withContact──▸ Contact
Deal ──dealContact──▸ Contact
Deal ──dealCompany──▸ Company
```

### Saved Queries

| Query | Description |
|-------|-------------|
| **Stale Contacts** | Contacts with no recent interactions |
| **Upcoming Follow-ups** | Interactions or contacts with future follow-up dates |
| **Open Deals** | Deals not at `won` or `lost` stage |
| **Network Map** | Graph view of contacts and their connections |

### Validation Rules

| Rule | Severity | Message |
|------|----------|---------|
| No interactions | Warning | "Contact has had no interactions recorded. Consider reaching out." |
| Overdue follow-up | Warning | "Follow-up is overdue and not marked done." |

### Installation

Go to **Admin > Mental Models > Install** and enter the path:

```
/app/models/crm
```

Click **Install** and wait for the model to load. The four CRM types will appear in the Explorer sidebar.

### Recommended Dashboard

Use a **sidebar-main** layout:

- **Sidebar:** Embed the Contacts Table view as a view-embed block. This provides a scrollable contact list.
- **Main:** Add a view-embed block showing the Interactions Table, filtered by the selected contact from the sidebar using cross-view context.

For a pipeline overview, create a second dashboard with a **top-bottom** layout: Open Deals table on top, Stale Contacts table on the bottom.

---

## 3. Zettelkasten+

**Model ID:** `zettelkasten` · **Version:** 1.0.0 · **Namespace:** `urn:sempkm:model:zettelkasten:`

Zettelkasten+ implements the Zettelkasten method for structured note-taking with a full provenance chain from quick captures through permanent knowledge. It adds argumentation links between permanent notes for building webs of interconnected ideas.

### Types

#### FleetingNote

A quick, raw capture of an idea or thought. Fleeting notes are the entry point to the Zettelkasten — capture now, process later.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Short label for this thought |
| Body | string | | Main text content |
| Captured From | string | | Context where the thought was captured |
| Tags | string[] | | Free-form labels |
| Created | date | | When the note was captured |

#### Source

A book, article, paper, podcast, or other reference material you learn from.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Title of the source material |
| Creator | string | | Author or creator |
| Source Type | enum | | `book`, `article`, `paper`, `podcast`, `video`, `website`, `lecture`, `conversation` |
| Date Published | date | | Publication date |
| URL | string | | Direct link to the source |
| Notes | string | | General impressions or reading status |
| Rating | integer | | Quality rating from 1 (low) to 5 (high) |
| Tags | string[] | | Free-form labels |

#### LiteratureNote

A summary of a key idea from a source, written in your own words. Each literature note references a single source.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Concise title summarizing the key idea |
| Body | string | | Your paraphrase or summary |
| Original Quote | string | | Verbatim excerpt from the source |
| Page Reference | string | | Page number or location |
| Derived From | → Source | | The source being summarized |
| Tags | string[] | | Free-form labels |

#### PermanentNote

An atomic, self-contained knowledge claim — the core of your Zettelkasten. Permanent notes express your own ideas, developed from literature notes or original thought.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Clear, self-contained idea statement |
| Body | string | | Full articulation of the knowledge claim |
| Sequence ID | string | | Luhmann-style alphanumeric identifier (e.g., `1a2b`) |
| Supports | → PermanentNote | | Notes this idea provides evidence for |
| Contradicts | → PermanentNote | | Notes this idea challenges |
| Follows From | → PermanentNote | | Notes this idea is a logical continuation of |
| Related To | → PermanentNote | | Thematically related notes |
| Developed From | → LiteratureNote | | The literature note that inspired this idea |
| Included In Structure | → StructureNote | | Structure notes that organize this idea |
| Tags | string[] | | Free-form labels |

#### StructureNote

An organizing note that curates permanent notes into coherent topics — argument maps, field surveys, or indexes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Topic being organized |
| Body | string | | Overview text describing the organization |
| Purpose | enum | | `argument`, `survey`, `index`, `sequence`, `comparison` |
| Includes | → PermanentNote | | Permanent notes organized by this structure |
| Related Structures | → StructureNote | | Other structure notes on related topics |
| Tags | string[] | | Free-form labels |

### Provenance Chain

The Zettelkasten+ model enforces a clear provenance chain from raw capture to organized knowledge:

```
FleetingNote → Source → LiteratureNote → PermanentNote → StructureNote
     ↑              ↑           ↑              ↑               ↑
  quick capture   reference   summary of    your own idea   organized
                  material    source idea                   overview
```

Each arrow represents a "developed from" or "derived from" link that maintains attribution back to the original source.

### Argumentation Links

PermanentNotes connect to each other through four argumentation link types:

| Link | Meaning |
|------|---------|
| **supports** | This idea provides evidence for the target idea |
| **contradicts** | This idea challenges or provides counter-evidence for the target |
| **followsFrom** | This idea is a logical continuation of the target |
| **relatedTo** | Thematic connection without a specific logical relationship |

Use the "Contradiction Map" saved query to visualize debates and tensions across your notes.

### Saved Queries

| Query | Description |
|-------|-------------|
| **Unprocessed Fleeting Notes** | Fleeting notes that haven't been developed into literature or permanent notes |
| **Isolated Permanent Notes** | Permanent notes with no connections to other notes or structure notes |
| **Contradiction Map** | Graph of permanent notes connected by `contradicts` links |
| **Provenance Chain** | Graph showing the full path from sources through notes to structures |

### Validation Rules

| Rule | Severity | Message |
|------|----------|---------|
| Unprocessed fleeting note | Warning | "This fleeting note hasn't been processed. Develop it into a literature or permanent note, or delete it." |
| Isolated permanent note | Warning | "This permanent note is isolated. Connect it to other ideas or include it in a structure note." |
| Unsourced idea | Warning | "This idea has no literature source. Consider linking it to supporting evidence." |

### Installation

Go to **Admin > Mental Models > Install** and enter the path:

```
/app/models/zettelkasten
```

Click **Install** and wait for the model to load. The five Zettelkasten types will appear in the Explorer sidebar.

### Recommended Dashboard

Use a **sidebar-main** layout:

- **Sidebar:** Embed the "Unprocessed Fleeting Notes" saved query. This shows your processing backlog at a glance.
- **Main:** Embed the Zettelkasten Graph view to see connections between your permanent notes, structure notes, and sources.

For a processing workflow, create a workflow (see [Chapter 28](28-dashboards-and-workflows.md)) with three steps: (1) Fleeting Notes table to pick a note, (2) Sources table to find or create a source, (3) a create form for PermanentNote pre-linked to the source.

---

## 4. Research Workflow

**Model ID:** `research` · **Version:** 1.0.0 · **Namespace:** `urn:sempkm:model:research:`

The Research Workflow model supports academic and research knowledge management. It tracks papers, extracts claims, links evidence, constructs arguments, and manages research questions — all with confidence tracking and evidence quality assessment.

### Types

#### Paper

An academic paper or publication.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Full title of the paper |
| Authors | string | | Author names (comma-separated) |
| Year | gYear | | Publication year |
| Venue | string | | Journal, conference, or publication venue |
| DOI | URI | | Digital Object Identifier |
| Paper Type | enum | | `journal-article`, `conference-paper`, `preprint`, `book-chapter`, `thesis`, `report`, `other` |
| Abstract | string | | Abstract or summary |
| Cites | → Paper | | Papers this paper references |
| Cited By | → Paper | | Papers that cite this paper (inverse) |
| Has Claims | → Claim | | Claims extracted from this paper |

#### Claim

A specific assertion or proposition extracted from a paper, with a confidence level.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Statement | string | ✓ | The assertion text |
| Confidence | enum | | `established`, `supported`, `contested`, `speculative`, `refuted` |
| Rationale | string | | Justification for the confidence assessment |
| Extracted From | → Paper | | The paper this claim came from |
| Corroborates | → Claim | | Claims that say the same thing from different sources |
| Contradicts | → Claim | | Claims that oppose this one |
| Depends On | → Claim | | Claims this one logically depends on |
| Supported By | → Evidence | | Evidence that supports this claim |
| Refuted By | → Evidence | | Evidence that refutes this claim |
| Addressed By | → Argument | | Arguments that incorporate this claim |

#### Evidence

Empirical data, experimental results, or observations that support or refute claims.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Description | string | ✓ | What this evidence shows |
| Evidence Type | enum | | `empirical-data`, `statistical-finding`, `case-study`, `expert-opinion`, `logical-argument`, `observation`, `quote` |
| Source | string | | Citation or reference (e.g., "Table 3, p. 42") |
| Methodology | string | | Research methodology used |
| Strength | enum | | `strong`, `moderate`, `weak`, `anecdotal`, `preliminary` |
| Supports | → Claim | | Claims this evidence supports |
| Refutes | → Claim | | Claims this evidence refutes |
| From Paper | → Paper | | The paper this evidence originates from |

#### ResearchQuestion

An open question driving your investigation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Question | string | ✓ | The research question text |
| Status | enum | | `open`, `partially-answered`, `answered`, `abandoned` |
| Context | string | | Background or motivation |
| Significance | string | | Why this question matters |
| Has Arguments | → Argument | | Arguments that address this question |

#### Argument

A structured reasoning unit that synthesizes claims and evidence to address a research question.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Thesis | string | ✓ | The central thesis |
| Argument Type | enum | | `literature-review`, `position-paper`, `analysis`, `synthesis`, `rebuttal` |
| Summary | string | | Brief summary of the reasoning |
| Addresses | → ResearchQuestion | | The research question being answered |
| Uses Claims | → Claim | | Claims used as premises |
| Uses Evidence | → Evidence | | Evidence incorporated in the argument |

### Evidence Tracking

Each Claim can accumulate multiple Evidence objects. Evidence has both a **type** (what kind of data it is) and a **strength** (how compelling it is):

- **Evidence types:** empirical-data, statistical-finding, case-study, expert-opinion, logical-argument, observation, quote
- **Strength levels:** strong, moderate, weak, anecdotal, preliminary

Evidence links to claims via `supports` (confirming) or `refutes` (challenging) relationships. When a claim has both supporting and refuting evidence, the SHACL-AF rules automatically flag it as contested.

### Relationships

```
Paper ──cites──▸ Paper (inverse: citedBy)
Paper ──hasClaim──▸ Claim
Claim ──extractedFrom──▸ Paper
Claim ──corroborates──▸ Claim
Claim ──contradicts──▸ Claim
Claim ──dependsOn──▸ Claim
Evidence ──supports──▸ Claim (inverse: supportedBy)
Evidence ──refutes──▸ Claim (inverse: refutedBy)
Evidence ──fromPaper──▸ Paper
Argument ──addresses──▸ ResearchQuestion (inverse: hasArgument)
Argument ──usesClaim──▸ Claim
Argument ──usesEvidence──▸ Evidence
```

### Saved Queries

| Query | Description |
|-------|-------------|
| **Unsupported Claims** | Claims with no linked evidence |
| **Contested Claims** | Claims with both supporting and refuting evidence |
| **Research Gaps** | Open research questions with no arguments |
| **Orphan Evidence** | Evidence not linked to any claim |
| **High Confidence Claims** | Claims marked as `established` or `supported` |
| **Citation Network** | Graph of paper-to-paper citation links |
| All Papers with Claim Counts | Paper table with count of extracted claims |
| Evidence Map | Graph of claims and their evidence connections |

### Validation Rules

| Rule | Severity | Message |
|------|----------|---------|
| Unsupported claim | Warning | "Claim marked as {confidence} but has no supporting evidence." |
| Contested claim | Info | "This claim has conflicting evidence — review the argument." |
| Orphan evidence | Warning | "This evidence isn't linked to any claim." |
| Unanswered question | Info | "This research question has no arguments yet." |

### Installation

Go to **Admin > Mental Models > Install** and enter the path:

```
/app/models/research
```

Click **Install** and wait for the model to load. The five Research types will appear in the Explorer sidebar.

### Recommended Dashboard

Use a **sidebar-main** layout:

- **Sidebar:** Embed the "Unsupported Claims" saved query. This surfaces claims that need evidence — your highest-priority research gap.
- **Main:** Embed the Evidence Map graph view to see how evidence connects to claims across your research.

For a deeper overview, create a **grid-2x2** dashboard: Unsupported Claims (top-left), Contested Claims (top-right), Research Gaps (bottom-left), and High Confidence Claims (bottom-right).

---

## 5. Business Planning

**Model ID:** `business-planning` · **Version:** 1.0.0 · **Namespace:** `urn:sempkm:model:business-planning:`

The Business Planning model provides 15 strategic analysis frameworks as structured RDF data with custom visual renderers. Each framework follows a container + item pattern — you create a container (e.g., an Eisenhower Matrix) and then add items (e.g., Eisenhower Items) that reference it. The model includes 32 concrete types across five categories: prioritization, strategy analysis, business design, goal tracking, and resource management.

Four custom view renderers — **Quadrant**, **BMC**, **OKR**, and **Decision Matrix** — provide specialized visualizations that go beyond table and card views. The model also supports cross-model linking to Basic PKM tasks and projects and to PPV goal outcomes.

### Prioritization & Decision-Making

#### Eisenhower Matrix

The Eisenhower Matrix organizes items into four quadrants by urgency and importance: **Do First** (high/high), **Schedule** (low urgency/high importance), **Delegate** (high urgency/low importance), and **Eliminate** (low/low). Use the Quadrant view renderer for the visual 2×2 grid.

**Eisenhower Matrix** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this matrix (e.g., "Q2 Priorities") |
| Description | string | | Purpose or context for this matrix |
| X-Axis Label | string | | Horizontal axis label (default: "Urgency") |
| Y-Axis Label | string | | Vertical axis label (default: "Importance") |

**Eisenhower Item**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Short, actionable title for this item |
| Description | string | | Additional context or details |
| Urgency | enum | ✓ | `high`, `low` |
| Importance | enum | ✓ | `high`, `low` |
| Matrix | → Eisenhower Matrix | | Which matrix this item belongs to |
| Related Task | → bpkm:Task | | Link to a task in Basic PKM for tracking |

#### Decision Matrix

A weighted scoring matrix for comparing alternatives against multiple criteria. Each alternative is scored on every criterion, and scores are multiplied by criterion weights to produce a ranked total. Use the Decision Matrix view renderer for the scoring table.

**Decision Matrix** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this decision (e.g., "Technology Selection") |
| Description | string | | Purpose or constraints |

**Criterion**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Evaluation dimension (e.g., "Performance", "Cost") |
| Description | string | | What this criterion measures |
| Weight | decimal | ✓ | Relative weight (higher = more important) |
| Decision Matrix | → Decision Matrix | | Which matrix this criterion belongs to |

**Alternative**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Option name (e.g., "Vendor A", "Build In-House") |
| Description | string | | Key facts about this option |
| Decision Matrix | → Decision Matrix | | Which matrix this alternative belongs to |

**Score**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | | Optional label (auto-generated by view if empty) |
| Value | decimal | ✓ | Numeric score (e.g., 1–10) |
| Alternative | → Alternative | ✓ | Which option is being rated |
| Criterion | → Criterion | ✓ | Which evaluation dimension this score is for |

### Strategy Analysis

#### SWOT Analysis

Identifies Strengths, Weaknesses, Opportunities, and Threats by classifying items along two axes: **nature** (internal vs. external) and **valence** (positive vs. negative). Rendered as a quadrant view where the four combinations map to the classic SWOT grid.

**SWOT Analysis** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this SWOT analysis |
| Description | string | | Context or scope |

**SWOT Item**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | The factor being assessed |
| Description | string | | Additional detail |
| Nature | enum | ✓ | `internal`, `external` |
| Valence | enum | ✓ | `positive`, `negative` |
| SWOT Analysis | → SWOT Analysis | | Which analysis this item belongs to |

The four quadrants: **Strength** = internal + positive, **Weakness** = internal + negative, **Opportunity** = external + positive, **Threat** = external + negative.

#### Porter's Five Forces

Analyzes competitive dynamics by assessing five forces: Competitive Rivalry, Supplier Power, Buyer Power, Threat of Substitution, and Threat of New Entry.

**Porter's Five Forces Analysis** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this analysis |
| Description | string | | Industry or market context |

**Porter Force**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Description of this force |
| Description | string | | Supporting detail |
| Force Type | enum | ✓ | `Competitive Rivalry`, `Supplier Power`, `Buyer Power`, `Threat of Substitution`, `Threat of New Entry` |
| Intensity | enum | | `High`, `Medium`, `Low` |
| Porter Analysis | → Porter's Five Forces Analysis | | Which analysis this force belongs to |

#### PESTLE Analysis

Scans macro-environmental factors across six dimensions: Political, Economic, Social, Technological, Legal, and Environmental.

**PESTLE Analysis** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this analysis |
| Description | string | | Market or context |

**PESTLE Factor**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | The environmental factor |
| Description | string | | Supporting detail |
| PESTLE Category | enum | ✓ | `Political`, `Economic`, `Social`, `Technological`, `Legal`, `Environmental` |
| Impact | enum | | `High`, `Medium`, `Low` |
| PESTLE Analysis | → PESTLE Analysis | | Which analysis this factor belongs to |

#### BCG Matrix

The Boston Consulting Group growth-share matrix classifies business units or products into four quadrants: **Stars** (high growth/high share), **Cash Cows** (low growth/high share), **Question Marks** (high growth/low share), and **Dogs** (low growth/low share). Rendered as a quadrant view.

**BCG Matrix** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this portfolio analysis |
| Description | string | | Context or scope |

**BCG Item**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Business unit or product name |
| Description | string | | Additional detail |
| Market Growth | enum | ✓ | `high`, `low` |
| Market Share | enum | ✓ | `high`, `low` |
| BCG Matrix | → BCG Matrix | | Which matrix this item belongs to |

#### Ansoff Matrix

Maps growth strategies by market novelty and product novelty: **Market Penetration** (existing/existing), **Market Development** (new market/existing product), **Product Development** (existing market/new product), and **Diversification** (new/new). Rendered as a quadrant view.

**Ansoff Matrix** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this growth strategy analysis |
| Description | string | | Context or scope |

**Ansoff Item**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Growth strategy name |
| Description | string | | Supporting detail |
| Market Novelty | enum | ✓ | `existing`, `new` |
| Product Novelty | enum | ✓ | `existing`, `new` |
| Ansoff Matrix | → Ansoff Matrix | | Which matrix this item belongs to |

### Business Design

#### Business Model Canvas

Captures the nine building blocks of how an organization creates, delivers, and captures value (Osterwalder & Pigneur). Use the **BMC view renderer** for the standard canvas layout.

**Business Model Canvas** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this canvas (e.g., "SaaS Platform BMC") |
| Description | string | | What business this models |

**BMC Section**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Section name (usually matches the section type) |
| Section Type | enum | ✓ | `key-partners`, `key-activities`, `key-resources`, `value-propositions`, `customer-relationships`, `channels`, `customer-segments`, `cost-structure`, `revenue-streams` |
| Content | string | | Free-text content for this building block |
| Canvas | → Business Model Canvas | | Which canvas this section belongs to |

#### Lean Canvas

A one-page business model adapted from Business Model Canvas for lean startups (Ash Maurya). Uses the same BMC view renderer but with startup-oriented sections. Rendered with the **BMC view renderer**.

**Lean Canvas** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this canvas |
| Description | string | | What startup or product this models |

**Lean Canvas Section**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Section name |
| Section Type | enum | ✓ | `Problem`, `Solution`, `Key Metrics`, `Unique Value Proposition`, `Unfair Advantage`, `Channels`, `Customer Segments`, `Cost Structure`, `Revenue Streams` |
| Content | string | | Free-text content |
| Lean Canvas | → Lean Canvas | | Which canvas this section belongs to |

#### Value Chain

Breaks down an organization's activities into primary (directly creating value) and support (enabling primary activities) categories to identify competitive advantages (Porter's Value Chain).

**Value Chain** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this analysis |
| Description | string | | Organization or scope |

**Value Chain Activity**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Activity name |
| Description | string | | What this activity involves |
| Activity Type | enum | ✓ | `Primary`, `Support` |
| Category | string | | Specific category (e.g., Inbound Logistics, Operations, Marketing & Sales, HR, Technology) |
| Value Chain | → Value Chain | | Which value chain this activity belongs to |

### Goal Tracking

#### OKR (Objectives and Key Results)

OKRs pair qualitative objectives with measurable key results. Each Objective describes an aspirational goal; Key Results provide numeric targets that track progress. Use the **OKR view renderer** for a progress dashboard with bars.

**Objective**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Aspirational goal statement (e.g., "Improve Product Quality") |
| Description | string | | Context and success criteria |
| Timeframe | string | | Planning period (e.g., "Q2 2026", "H1 2026") |
| Related Goal Outcome | → ppv:GoalOutcome | | Link to a goal outcome in PPV |

**Key Result**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Measurable outcome (e.g., "Reduce bug count from 50 to 10") |
| Description | string | | Measurement method and data source |
| Current Value | decimal | | Where you are now |
| Target Value | decimal | | What number means full achievement |
| Unit | string | | Unit of measurement (e.g., "%", "points", "count") |
| Objective | → Objective | | Which objective this key result measures |

#### Balanced Scorecard

Translates strategy into measurable objectives across four perspectives: **Financial**, **Customer**, **Internal Process**, and **Learning & Growth** (Kaplan & Norton).

**Balanced Scorecard** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this scorecard |
| Description | string | | Strategic context |

**BSC Item**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Strategic objective or initiative |
| Description | string | | Additional detail |
| Perspective | enum | ✓ | `Financial`, `Customer`, `Internal Process`, `Learning & Growth` |
| Measure | string | | KPI or metric to track |
| Target | string | | Target value for the measure |
| Balanced Scorecard | → Balanced Scorecard | | Which scorecard this item belongs to |

### Resource Management

#### RACI Matrix

Clarifies roles and responsibilities by assigning Responsible, Accountable, Consulted, and Informed designations to activities.

**RACI Matrix** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this matrix |
| Description | string | | Project or context |

**RACI Entry**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Label for this entry |
| RACI Role | enum | ✓ | `Responsible`, `Accountable`, `Consulted`, `Informed` |
| Person | string | | The person or role assigned |
| Activity | string | | The activity or deliverable |
| RACI Matrix | → RACI Matrix | | Which matrix this entry belongs to |

#### Stakeholder Map

Plots stakeholders by **power** and **interest** to determine engagement strategy: Manage Closely (high/high), Keep Satisfied (high power/low interest), Keep Informed (low power/high interest), Monitor (low/low). Rendered as a quadrant view.

**Stakeholder Map** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this map |
| Description | string | | Project or initiative context |

**Stakeholder Item**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Stakeholder name or group |
| Description | string | | Additional detail |
| Stakeholder Power | enum | ✓ | `high`, `low` |
| Stakeholder Interest | enum | ✓ | `high`, `low` |
| Stakeholder Map | → Stakeholder Map | | Which map this stakeholder belongs to |

#### Risk Matrix

Assesses risks by plotting **likelihood** against **impact** to prioritize response: Critical (high/high), Mitigate (low likelihood/high impact), Monitor (high likelihood/low impact), Accept (low/low). Rendered as a quadrant view.

**Risk Matrix** (container)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A name for this matrix |
| Description | string | | Project or context |

**Risk Item**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Risk description |
| Description | string | | Additional detail |
| Risk Likelihood | enum | ✓ | `high`, `low` |
| Risk Impact | enum | ✓ | `high`, `low` |
| Risk Matrix | → Risk Matrix | | Which matrix this risk belongs to |

### Custom Renderers

The Business Planning model provides four custom view renderers that go beyond the default table and card views:

| Renderer | Type | Description |
|----------|------|-------------|
| **Quadrant** | `quadrant` | A 2×2 grid that places items in quadrants based on two classification axes. Used by Eisenhower Matrix (urgency × importance), SWOT Analysis (nature × valence), BCG Matrix (market growth × market share), Ansoff Matrix (market novelty × product novelty), Stakeholder Map (power × interest), and Risk Matrix (likelihood × impact). |
| **BMC** | `bmc` | A nine-section canvas layout matching the Business Model Canvas and Lean Canvas templates. Sections snap to the standard BMC grid positions. |
| **OKR** | `okr` | A progress dashboard showing Objectives with their Key Results as progress bars. Progress is calculated from current/target values. |
| **Decision Matrix** | `decision-matrix` | A scoring table showing alternatives as rows, criteria as columns, scores in cells, and weighted totals. Criteria weights are used to compute ranked scores. |

To open a custom view: navigate to the relevant type in the Explorer sidebar, then use the **Views** menu or the generic view tab to select the renderer.

### Cross-Model Edges

The Business Planning model defines three cross-model properties that link framework items to objects in other installed models:

| Property | From | To | Description |
|----------|------|----|-------------|
| `bp:relatedTask` | Eisenhower Item | bpkm:Task | Link a prioritized item to its task in Basic PKM for tracking |
| `bp:relatedGoalOutcome` | Objective | ppv:GoalOutcome | Link an OKR objective to a goal outcome in the PPV model |
| `bp:relatedProject` | Framework Item (any) | bpkm:Project | Link any framework item to a project in Basic PKM |

These edges appear in SHACL-generated edit forms when the target model is installed. The edge system supports arbitrary linking regardless of which model defines the property, so you can also create links manually via the edge editor.

### SPARQL Query Examples

**High-urgency, high-importance Eisenhower items (Do First quadrant):**

```sparql
PREFIX bp: <urn:sempkm:model:business-planning:>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?title WHERE {
  ?item a bp:EisenhowerItem ;
        dcterms:title ?title ;
        bp:urgency "high" ;
        bp:importance "high" .
}
ORDER BY ?title
```

**OKR progress — average completion percentage per Objective:**

```sparql
PREFIX bp: <urn:sempkm:model:business-planning:>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?objective (AVG(?pct) AS ?avgProgress) WHERE {
  ?obj a bp:Objective ;
       dcterms:title ?objective .
  ?kr  a bp:KeyResult ;
       bp:belongsToObjective ?obj ;
       bp:currentValue ?current ;
       bp:targetValue ?target .
  BIND(IF(?target > 0, ?current / ?target * 100, 0) AS ?pct)
}
GROUP BY ?objective
ORDER BY DESC(?avgProgress)
```

**Decision Matrix weighted totals — rank alternatives by score:**

```sparql
PREFIX bp: <urn:sempkm:model:business-planning:>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?alternative (SUM(?weightedScore) AS ?total) WHERE {
  ?score a bp:Score ;
         bp:scoreAlternative ?alt ;
         bp:scoreCriterion ?crit ;
         bp:value ?val .
  ?alt   dcterms:title ?alternative .
  ?crit  bp:weight ?weight .
  BIND(?val * ?weight AS ?weightedScore)
}
GROUP BY ?alternative
ORDER BY DESC(?total)
```

### Relationships

```
EisenhowerItem ──belongsToMatrix──▸ EisenhowerMatrix
EisenhowerItem ──relatedTask──▸ bpkm:Task
BMCSection ──belongsToCanvas──▸ BusinessModelCanvas
Objective ──relatedGoalOutcome──▸ ppv:GoalOutcome
KeyResult ──belongsToObjective──▸ Objective
Criterion ──belongsToDecisionMatrix──▸ DecisionMatrix
Alternative ──belongsToDecisionMatrix──▸ DecisionMatrix
Score ──scoreAlternative──▸ Alternative
Score ──scoreCriterion──▸ Criterion
SWOTItem ──belongsToSWOT──▸ SWOTAnalysis
BCGItem ──belongsToBCG──▸ BCGMatrix
AnsoffItem ──belongsToAnsoff──▸ AnsoffMatrix
PorterForce ──belongsToPorter──▸ PorterAnalysis
PESTLEFactor ──belongsToPESTLE──▸ PESTLEAnalysis
BSCItem ──belongsToBSC──▸ BalancedScorecard
RACIEntry ──belongsToRACI──▸ RACIMatrix
VCActivity ──belongsToVC──▸ ValueChain
StakeholderItem ──belongsToStakeholderMap──▸ StakeholderMap
RiskItem ──belongsToRiskMatrix──▸ RiskMatrix
LeanCanvasSection ──belongsToLeanCanvas──▸ LeanCanvas
FrameworkItem ──relatedProject──▸ bpkm:Project
```

### Saved Queries

This model does not ship with saved queries. Use the SPARQL examples above as a starting point and save your own via the SPARQL console.

### Validation Rules

This model does not ship with SHACL-AF validation rules. All field constraints are enforced by the SHACL shapes at edit time (required fields, enum values, cardinality).

### Installation

Go to **Admin > Mental Models > Install** and enter the path:

```
/app/models/business-planning
```

Click **Install** and wait for the model to load. The 32 Business Planning types will appear in the Explorer sidebar grouped by their framework.

### Recommended Dashboard

Use a **grid-2x2** layout:

- **Top-left:** Embed a Quadrant view filtered to Eisenhower Items for your current priority matrix.
- **Top-right:** Embed an OKR view showing your active objectives and key result progress.
- **Bottom-left:** Embed a BMC view for your current business model canvas.
- **Bottom-right:** Embed a Decision Matrix view for your most active decision.

For a strategic overview, create a second dashboard with a **top-bottom** layout: SWOT Quadrant view on top, Porter's Five Forces table on the bottom.

---

## Model Comparison

| Feature | Basic PKM v2.0 | Personal CRM | Zettelkasten+ | Research Workflow | Business Planning |
|---------|----------------|--------------|----------------|-------------------|-------------------|
| **Types** | 6 | 4 | 5 | 5 | 32 |
| **Focus** | General PKM + projects | Relationships + deals | Structured notes | Academic research | Strategic analysis frameworks |
| **Validation rules** | 1 | 2 | 3 | 4 | 0 |
| **Saved queries** | 6 | 4 | 4 | 8 | 0 |
| **Key concept** | Task/Milestone hierarchy | Deal pipeline | Provenance chain | Evidence tracking | Multi-framework analysis with custom renderers |

All models can coexist in the same SemPKM instance without conflicts — their namespaces are independent and types do not collide. Install as many as you need for your workflow.

---

**Previous:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) | **Next:** [Chapter 30: Workspace Personas](30-personas.md)
