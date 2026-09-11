<!-- GENERATED FILE. Do not edit. Source: models/basic-pkm/README.md. Regenerate with: python3 scripts/sync-model-docs.py -->
> **Bundled model documentation.** This page mirrors the `README.md` shipped inside the `basic-pkm` Mental Model archive. The same text is available in the app under **Admin > Models > Basic PKM > Documentation** and at `/api/models/basic-pkm/docs`. To change it, edit `models/basic-pkm/README.md` and run `scripts/sync-model-docs.py`.

# Basic PKM

**Model ID:** `basic-pkm` · **Namespace:** `urn:sempkm:model:basic-pkm:` · **Prefix:** `bpkm:`

Basic PKM is the default Mental Model installed on every SemPKM instance. It provides seven
general-purpose types for personal knowledge management and lightweight project management:
**Note**, **Concept**, **Project**, **Person**, **Task**, **Milestone**, and **Event**.

Use it as a starting point for almost any knowledge base: capture notes, organize them by
concept, group work under projects, track tasks toward milestones, and keep calendar events
alongside the people and projects they belong to.

## Version history

| Version | Change |
|---------|--------|
| 1.0.0 | Note, Concept, Project, Person |
| 2.0.0 | Added Task and Milestone for project management |
| 2.1.0 | Task scheduling fields (scheduled start/end, estimated duration, recurrence, exception dates) and external sync fields |
| 2.2.0 | Added Event for calendar sync (Google Calendar, Outlook, CalDAV) with attendees, recurrence, and free/busy fields |

Existing instances pick up new types by opening **Admin > Models > Basic PKM** and clicking
**Refresh**. Refresh reloads the ontology, shapes, views, rules, and this documentation from disk
without touching your data.

## Types

### Note

A single idea, observation, or reference. Notes are the atomic building blocks of your knowledge base.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | A concise title capturing the core idea |
| Body | string | | Main content (Markdown supported) |
| Type | enum | | `observation`, `idea`, `reference`, `meeting-note`, `journal` (default: `observation`) |
| About Concepts | → Concept | | Concepts this note discusses |
| Related Project | → Project | | The project this note belongs to |
| Source URL | URI | | Link to the original source |
| Tags | string[] | | Free-form labels |

### Concept

A topic or theme that notes can be *about*. Concepts form a hierarchy via broader/narrower links
and use the SKOS vocabulary (`skos:prefLabel`, `skos:broader`, ...).

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

### Project

A goal or initiative that organizes notes, people, tasks, milestones, and events.

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

### Person

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

### Task

A unit of work with status tracking, priority, effort sizing, scheduling, and due dates.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Clear, actionable task title |
| Description | string | | Acceptance criteria or details |
| Status | enum | | `todo`, `in-progress`, `done`, `blocked`, `cancelled` (default: `todo`) |
| Priority | enum | | `low`, `medium`, `high`, `critical` (default: `medium`) |
| Effort | enum | | `trivial`, `small`, `medium`, `large`, `epic` |
| Due Date | date | | When this task is due |
| Scheduled Start / End | dateTime | | When the task is scheduled to run (shown on the calendar) |
| Estimated Duration | string | | ISO 8601 duration, e.g. `PT1H30M` |
| Recurrence Rule | string | | RFC 5545 RRULE, e.g. `FREQ=WEEKLY;BYDAY=FR` |
| Exception Dates | string | | Comma-separated ISO dates to skip |
| Completed Date | date | | When the task was finished |
| Assigned To | → Person | | People responsible |
| Project | → Project | | Parent project |
| Milestone | → Milestone | | Which milestone this task belongs to |
| Depends On | → Task | | Tasks that must complete first |
| Related Notes | → Note | | Contextual notes |
| Related Concepts | → Concept | | Topic tags via concept links |
| Body | string | | Markdown notes on the task |
| Tags | string[] | | Free-form labels |

Tasks also carry external sync fields (**External Provider**, **External ID**, **External URL**,
**Last Synced**). Sync apps such as Linear, GitHub, Jira, Monday, Asana, and Todoist write these
fields; the provider enum is `asana`, `linear`, `jira`, `github`, `todoist`, `trello`, `manual`.

### Milestone

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

### Event

A calendar event, optionally synced from an external calendar provider. Events power the
calendar view and the Google Calendar, Outlook, and CalDAV sync apps.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | The event title |
| Description | string | | Agenda or notes |
| Status | enum | | `confirmed`, `tentative`, `cancelled` (default: `confirmed`) |
| Location | string | | Physical or virtual location |
| Visibility | enum | | `public`, `private`, `confidential` |
| Show As | enum | | `free`, `tentative`, `busy`, `out-of-office`, `working-elsewhere` (default: `busy`) |
| Conference URL | URI | | Video conference link |
| Meeting Notes | string | | Notes captured during or after the event |
| Start Date | dateTime | ✓ | When the event starts |
| End Date | dateTime | | When the event ends |
| All Day | boolean | | Whether this is an all-day event |
| Time Zone | string | | IANA time zone identifier |
| Recurrence Rule | string | | RFC 5545 RRULE |
| Recurring Event ID | string | | Identifier of the master recurring event |
| Reminder | integer | | Minutes before the event to remind |
| Attendees | → Person | | People attending |
| Organizer | → Person | | Person who organized the event |
| Response Status | enum | | `needs-action`, `accepted`, `declined`, `tentative` |
| Project | → Project | | The project this event relates to |
| Generated Task | → Task | | Tasks created from or linked to this event |
| Event Note | → Note | | Notes associated with this event |
| Body | string | | Markdown body |
| Tags | string[] | | Free-form labels |

Events carry the same external sync fields as tasks; the provider enum is `google-calendar`,
`outlook`, `caldav`, `manual`, plus a **Calendar** name.

## Relationships

```
Project ──hasParticipant──▸ Person (inverse: participatesIn)
Project ──hasNote──▸ Note
Project ──hasProjectTasks──▸ Task (inverse: taskProject)
Project ──hasMilestones──▸ Milestone (inverse: milestoneProject)
Task ──assignedTo──▸ Person (inverse: hasAssignedTask)
Task ──milestone──▸ Milestone (inverse: hasTasks)
Task ──dependsOn──▸ Task
Task ──relatedNote──▸ Note (inverse: hasRelatedNote, derived by rule)
Task ──relatedConcept──▸ Concept
Note ──isAbout──▸ Concept
Note ──relatedProject──▸ Project
Concept ──broader / narrower / related──▸ Concept
Event ──attendee / organizer──▸ Person
Event ──eventProject──▸ Project
Event ──generatedTask──▸ Task
Event ──eventNote──▸ Note
```

## Views and saved queries

Every type has **Table**, **Cards**, and **Graph** views. The model also ships these saved queries:

| Query | Description |
|-------|-------------|
| Active Projects | Projects with status `active` |
| Recent Notes | Notes sorted by creation date |
| Concept Hierarchy | Concept tree via broader/narrower links |
| My Open Tasks | Tasks with status `todo` or `in-progress` |
| Overdue Tasks | Tasks past their due date that are not done or cancelled |
| Blocked Tasks | Tasks with status `blocked` |
| Upcoming Events | Events starting from today onward |
| Past Events | Events that have already ended |

## Inference and validation rules

The `rules/basic-pkm.ttl` file ships SHACL-AF rules that run during inference and validation:

| Rule | Kind | Effect |
|------|------|--------|
| Derive hasRelatedNote inverse | Inference | Materializes `Note → hasRelatedNote → Task` from `Task → relatedNote` |
| Derive task project from milestone | Inference | A task linked to a milestone inherits the milestone's project |
| Overdue task | Warning | "Task is overdue: due date has passed but task is not done or cancelled." |
| Comma in tag | Warning | "Tag value contains a comma — split into individual tags." |
| Missing title | Warning | Object has none of `dcterms:title`, `rdfs:label`, `skos:prefLabel`, or `foaf:name` |
| Empty body | Info | "Object has no body content. Consider adding a description or notes." |
| Concept without definition | Info | "Concept has no definition. Consider adding a skos:definition." |
| Unconnected object | Info | "Object has no connections to other objects. Consider linking it." |
| Duplicate URL | Info | Another object of the same type shares this URL |

Inference entailments enabled by default: `owl:inverseOf` and SHACL rules. Others
(`rdfs:subClassOf`, `rdfs:subPropertyOf`, transitive properties, domain/range) can be switched on
per model under **Admin > Models > Basic PKM > Inference Settings**.

## Seed data

A fresh install materializes a small demo graph through the event store: a "SemPKM Development"
project with participants, notes about the architecture, a concept hierarchy under Knowledge
Management, and tasks and milestones with an intentionally overdue task so the lint panel has
something to show. Delete or edit these objects like any other data.

## Recommended dashboards

Use a **sidebar-main** layout:

- **Sidebar:** embed the "My Open Tasks" saved query as a view-embed block for a persistent task list.
- **Main:** embed the Tasks Table view, filtered by the selected task from the sidebar using cross-view context.

For a project-management overview, add a **grid-2x2** dashboard with Active Projects (top-left),
My Open Tasks (top-right), Overdue Tasks (bottom-left), and Blocked Tasks (bottom-right).
Events work well in the **Calendar** view renderer; add it as a block for a weekly agenda.

## Works with

- **Task sync apps:** Linear, GitHub, Jira, Monday, Asana, Todoist write `bpkm:Task`.
- **Calendar sync apps:** Google Calendar, Outlook, CalDAV write `bpkm:Event`.
- **Business Planning:** Eisenhower items link to `bpkm:Task`; any framework item can link to `bpkm:Project`.

---

**Back:** [Chapter 39: Mental Model Catalog](39-mental-model-catalog.md)
