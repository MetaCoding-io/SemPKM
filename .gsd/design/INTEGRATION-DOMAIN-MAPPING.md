# Integration Domain Mapping — Design Document

**Created:** 2026-03-16
**Status:** Draft
**Goal:** Validate that `bpkm:Task` and `bpkm:Event` (basic-pkm v2.2) can faithfully represent tasks and events from major PM and calendar providers, identify remaining gaps, and assess bidirectional sync feasibility.

---

## Provider Coverage

### Task/PM Providers

| Provider | API Type | Auth | Webhooks | Sync Feasibility |
|---|---|---|---|---|
| **Asana** | REST | OAuth 2.0 | Yes (project-scoped) | Bidirectional ✅ |
| **Monday.com** | GraphQL | OAuth 2.0 / API Token | Yes (board-scoped) | Bidirectional ✅ (with loop guard) |
| **Linear** | GraphQL | OAuth 2.0 / API Key | Yes (workspace-scoped) | Bidirectional ✅ |
| **Jira Cloud** | REST v3 | OAuth 2.0 (Atlassian Connect) | Yes (project-scoped) | Bidirectional ✅ |

### Calendar Providers

| Provider | API Type | Auth | Push Notifications | Sync Feasibility |
|---|---|---|---|---|
| **Google Calendar** | REST v3 | OAuth 2.0 (Google) | Yes (push via webhook channels) | Bidirectional ✅ |
| **Outlook/Microsoft 365** | Microsoft Graph REST | OAuth 2.0 (Microsoft Identity) | Yes (subscriptions with webhooks) | Bidirectional ✅ |
| **CalDAV** | WebDAV (RFC 4791) | HTTP Basic / OAuth 2.0 | Limited (poll or Apple push) | Bidirectional ✅ (polling) |
| **Apple Calendar (iCloud)** | CalDAV + push | Apple ID / App-specific password | Yes (Apple Push Notification) | Pull ✅ / Push ⚠️ (limited API) |

---

## 1. Asana → bpkm:Task

### Entity Mapping

| Asana Entity | SemPKM Type | Notes |
|---|---|---|
| Task | `bpkm:Task` | Direct |
| Subtask | `bpkm:Task` + `bpkm:parentTask` | Up to 5 levels |
| Milestone | `bpkm:Milestone` | `resource_subtype: "milestone"` |
| Project | `bpkm:Project` | Direct |
| Section | `bpkm:taskGroup` (string) | Preserved as group name |
| User | `bpkm:Person` | Match by email or create |
| Tag | `bpkm:tags` | Direct |
| Custom Field | See custom fields section | Configurable mapping |

### Field Mapping

| Asana Field | bpkm Property | Transform | Direction |
|---|---|---|---|
| `name` | `dcterms:title` | Direct | ↔ |
| `notes` (HTML) | `dcterms:description` | HTML → Markdown | ↔ |
| `completed` | `bpkm:taskStatus` | `true` → "done", `false` → see status mapping | ↔ |
| `completed_at` | `bpkm:completedDate` | datetime → date | ← |
| `due_on` | `bpkm:dueDate` | Direct (xsd:date) | ↔ |
| `due_at` | `bpkm:dueDate` | datetime → date (time lost) | ↔ |
| `start_on` | `bpkm:startDate` | Direct | ↔ |
| `start_at` | `bpkm:startDate` | datetime → date | ↔ |
| `assignee` | `bpkm:assignedTo` | User GID → Person IRI | ↔ |
| `followers` | `bpkm:followers` | User GIDs → Person IRIs | ← |
| `projects` | `bpkm:taskProject` | Multi-value | ↔ |
| `memberships[].section.name` | `bpkm:taskGroup` | First project's section | ← |
| `parent` | `bpkm:parentTask` | GID → Task IRI | ↔ |
| `dependencies` | `bpkm:dependsOn` | GIDs → Task IRIs | ↔ |
| `tags` | `bpkm:tags` | Tag names | ↔ |
| `permalink_url` | `bpkm:externalUrl` | Direct | ← |
| `gid` | `bpkm:externalId` | Direct | ← |
| `custom_fields` | See below | Configurable | ↔ |

### Status Normalization

Asana has no native status field. Status comes from completion + section placement + custom fields.

**Default mapping (no custom field):**

| Asana State | bpkm:taskStatus | bpkm:externalStatus |
|---|---|---|
| `completed=true` | done | "Completed" |
| `completed=false` (default) | todo | "" |

**With custom Status enum field (configurable):**

| Custom Field Label | bpkm:taskStatus | Notes |
|---|---|---|
| "To Do" / "Not Started" | todo | |
| "In Progress" / "Working" | in-progress | |
| "Done" / "Complete" | done | |
| "Blocked" / "On Hold" | blocked | |
| "Cancelled" / "Won't Do" | cancelled | |
| *(any other)* | todo (default) | Preserved in `externalStatus` |

**Section-based mapping (Kanban boards):**
The sync app can optionally map section names to statuses. User configures: "In Progress" section → `in-progress`, "Done" section → `done`.

### Priority Mapping

Asana has no native priority. Priority is a custom field:

| Custom Field Label | bpkm:priority |
|---|---|
| "Low" | low |
| "Medium" | medium |
| "High" | high |
| "Urgent" / "Critical" | critical |

Sync app must discover which custom field the user designated as "priority" during setup.

### Custom Fields Strategy

| Asana Custom Field Type | Mapping Strategy |
|---|---|
| `text` | Store as `bpkm:tags` or ignore |
| `number` | Map to `bpkm:storyPoints` if field is "Story Points"/"Estimate"; else ignore |
| `enum` | Map to status/priority if configured; else preserve in tags |
| `multi_enum` | Map to `bpkm:tags` |
| `date` | Ignore (duplicate of due/start dates usually) |
| `people` | Map to `bpkm:followers` if field is "Reviewers"; else ignore |

### API Characteristics

- **Rate limit:** Cost-based per minute per token. ~1500 requests/min for simple queries.
- **Pagination:** Max 100 items per page. `opt_fields` required for efficiency.
- **Webhooks:** Project-scoped. Payload has GID only — follow-up GET required.
- **No bulk GET:** Must fetch tasks individually or list from project.

---

## 2. Monday.com → bpkm:Task

### Entity Mapping

| Monday Entity | SemPKM Type | Notes |
|---|---|---|
| Item | `bpkm:Task` | Direct |
| Subitem | `bpkm:Task` + `bpkm:parentTask` | Up to 5 levels (Enterprise) |
| Board | `bpkm:Project` | One board = one project |
| Group | `bpkm:taskGroup` (string) | Group name preserved |
| User | `bpkm:Person` | Match by email |
| Tag | `bpkm:tags` | Via `tags` column |

### Column → Property Mapping

| Monday Column Type | bpkm Property | Transform | Direction |
|---|---|---|---|
| `name` (item name) | `dcterms:title` | Direct | ↔ |
| `long_text` / `text` | `dcterms:description` | Direct | ↔ |
| `status` (color) | `bpkm:taskStatus` + `bpkm:externalStatus` | Label → enum (configurable) | ↔ |
| `date` | `bpkm:dueDate` | Direct | ↔ |
| `timeline` | `bpkm:startDate` + `bpkm:dueDate` | Split start/end | ↔ |
| `people` | `bpkm:assignedTo` | User IDs → Person IRIs | ↔ |
| `numbers` | `bpkm:storyPoints` | If column is "Points"/"Estimate" | ↔ |
| `tags` | `bpkm:tags` | Tag names | ↔ |
| `dependency` | `bpkm:dependsOn` | Item IDs → Task IRIs | ↔ |
| `checkbox` | `bpkm:taskStatus` | checked → "done" | ↔ |
| `priority` (status) | `bpkm:priority` | Label mapping | ↔ |
| `link` | `bpkm:externalUrl` or note | URL extraction | ← |
| `connect_boards` | Object property links | Cross-model potential | ← |

### Status Normalization

Monday.com statuses are fully custom per board. Default mapping:

| Monday Label (Common) | bpkm:taskStatus | Color |
|---|---|---|
| "" (blank) | todo | gray |
| "Working on it" | in-progress | orange |
| "Done" | done | green |
| "Stuck" | blocked | red |

**Custom labels require user configuration during sync setup.** The sync app presents the board's status labels and asks the user to map each to a `bpkm:taskStatus` value.

### Webhook Loop Prevention

**Critical issue:** Monday.com has no webhook suppression. API-originated changes re-trigger webhooks.

**Solution:** The sync app maintains a `pending_changes` set keyed by `(item_id, column_id, timestamp)`. When a webhook arrives:
1. Check if this change matches a recently-pushed change (within 5s window)
2. If yes, skip processing (it's our own echo)
3. If no, process normally

Additionally, the app should include a `X-SemPKM-Sync: true` header or marker in update descriptions to help detect sync-originated changes.

### API Characteristics

- **Rate limit:** Complexity-based (5M per query per minute). Deeply nested queries consume fast.
- **No delta query:** No "changed since timestamp" endpoint. Must poll or rely on webhooks.
- **Webhook payload:** Minimal — most events require follow-up query.
- **Mirror columns:** Read-only via API. Must update source.

---

## 3. Linear → bpkm:Task

### Entity Mapping

| Linear Entity | SemPKM Type | Notes |
|---|---|---|
| Issue | `bpkm:Task` | Direct |
| Sub-issue | `bpkm:Task` + `bpkm:parentTask` | Unlimited depth |
| Project | `bpkm:Project` | Direct |
| Cycle | `bpkm:taskGroup` | Cycle name as group |
| Team | Organizational — not mapped | |
| Label | `bpkm:tags` | Direct |
| User | `bpkm:Person` | Match by email |

### Field Mapping

| Linear Field | bpkm Property | Transform | Direction |
|---|---|---|---|
| `title` | `dcterms:title` | Direct | ↔ |
| `description` (Markdown) | `dcterms:description` | Direct (both Markdown) | ↔ |
| `state.name` | `bpkm:taskStatus` + `bpkm:externalStatus` | See status mapping | ↔ |
| `priority` (0-4) | `bpkm:priority` | Numeric → enum | ↔ |
| `estimate` | `bpkm:storyPoints` | Direct (fibonacci) | ↔ |
| `dueDate` | `bpkm:dueDate` | Direct | ↔ |
| `startedAt` | `bpkm:startDate` | datetime → date | ← |
| `completedAt` | `bpkm:completedDate` | datetime → date | ← |
| `assignee` | `bpkm:assignedTo` | Single user | ↔ |
| `subscribers` | `bpkm:followers` | User list | ← |
| `parent` | `bpkm:parentTask` | Issue → Task IRI | ↔ |
| `relations` (blocks/blocked by) | `bpkm:dependsOn` | Relation type filter | ↔ |
| `project` | `bpkm:taskProject` | Single project | ↔ |
| `cycle.name` | `bpkm:taskGroup` | Cycle name | ← |
| `labels` | `bpkm:tags` | Label names | ↔ |
| `identifier` | `bpkm:externalId` | e.g., "LIN-123" | ← |
| `url` | `bpkm:externalUrl` | Direct | ← |

### Status Normalization

Linear has a well-defined state machine per team:

| Linear State | Type | bpkm:taskStatus |
|---|---|---|
| Backlog | backlog | todo |
| Todo | unstarted | todo |
| In Progress | started | in-progress |
| In Review | started | in-progress |
| Done | completed | done |
| Cancelled | cancelled | cancelled |

Linear's `state.type` field makes normalization reliable — it's one of: `backlog`, `unstarted`, `started`, `completed`, `cancelled`. The sync app maps by type, not by label:

```
backlog/unstarted → todo
started → in-progress
completed → done
cancelled → cancelled
```

Custom states inherit the type from their parent category, so this mapping is robust.

### Priority Normalization

| Linear Priority | Value | bpkm:priority |
|---|---|---|
| No priority | 0 | *(omit)* |
| Urgent | 1 | critical |
| High | 2 | high |
| Medium | 3 | medium |
| Low | 4 | low |

### API Characteristics

- **Rate limit:** 1500 requests/hour (simple), complexity-based for GraphQL.
- **Webhooks:** Workspace-scoped, rich payloads (include changed data!). Best webhook implementation of all four.
- **Delta sync:** `updatedAt` filter on queries enables efficient polling.
- **GraphQL:** Single request can fetch issue + relations + labels + project.

---

## 4. Jira Cloud → bpkm:Task

### Entity Mapping

| Jira Entity | SemPKM Type | Notes |
|---|---|---|
| Issue | `bpkm:Task` | Direct |
| Subtask | `bpkm:Task` + `bpkm:parentTask` | One level (classic) or unlimited (next-gen) |
| Epic | `bpkm:Milestone` or `bpkm:Project` | Configurable |
| Project | `bpkm:Project` | Direct |
| Sprint | `bpkm:taskGroup` | Sprint name |
| Component | `bpkm:tags` | Component names |
| User | `bpkm:Person` | Account ID → match by email |
| Label | `bpkm:tags` | Direct |

### Field Mapping

| Jira Field | bpkm Property | Transform | Direction |
|---|---|---|---|
| `summary` | `dcterms:title` | Direct | ↔ |
| `description` (ADF) | `dcterms:description` | ADF → Markdown | ↔ |
| `status.name` | `bpkm:taskStatus` + `bpkm:externalStatus` | See status mapping | ↔ |
| `priority.name` | `bpkm:priority` | Name → enum | ↔ |
| `story_points` (custom) | `bpkm:storyPoints` | Direct | ↔ |
| `duedate` | `bpkm:dueDate` | Direct | ↔ |
| `created` | `dcterms:created` | Direct | ← |
| `resolutiondate` | `bpkm:completedDate` | datetime → date | ← |
| `assignee` | `bpkm:assignedTo` | Account ID → Person | ↔ |
| `reporter` | `bpkm:followers` | Account ID → Person | ← |
| `watches` | `bpkm:followers` | Watch list | ← |
| `parent` | `bpkm:parentTask` | Issue key → Task IRI | ↔ |
| `issuelinks` (blocks) | `bpkm:dependsOn` | Filter by link type "Blocks" | ↔ |
| `project.key` | `bpkm:taskProject` | Project key → Project IRI | ↔ |
| `sprint.name` | `bpkm:taskGroup` | Active sprint name | ← |
| `labels` | `bpkm:tags` | Direct | ↔ |
| `components` | `bpkm:tags` | Component names as tags | ← |
| `key` | `bpkm:externalId` | e.g., "PROJ-123" | ← |
| `self` / browse URL | `bpkm:externalUrl` | Construct from key | ← |

### Status Normalization

Jira has customizable workflows per project. Status has a `statusCategory` that normalizes:

| Status Category | bpkm:taskStatus |
|---|---|
| `new` (To Do) | todo |
| `indeterminate` (In Progress) | in-progress |
| `done` (Done) | done |

The `statusCategory.key` field is reliable across all Jira projects, regardless of custom workflow states. This is the best mapping strategy:

```
statusCategory.key == "new" → todo
statusCategory.key == "indeterminate" → in-progress
statusCategory.key == "done" → done
```

"Blocked" doesn't have a native Jira status category. Options:
- Map specific status names containing "blocked" → `blocked`
- Use a custom field flag
- Let users configure per-project

### Priority Normalization

| Jira Priority | bpkm:priority |
|---|---|
| Lowest / Trivial | low |
| Low | low |
| Medium | medium |
| High | high |
| Highest / Blocker / Critical | critical |

### Description Format

Jira Cloud uses **Atlassian Document Format (ADF)** — a JSON-based rich text format. Conversion to Markdown is required:

```
ADF heading → # Markdown heading
ADF paragraph → plain text
ADF bulletList → - items
ADF codeBlock → ```code```
ADF mention → @username
ADF inlineCard → [link](url)
```

Libraries exist for ADF ↔ Markdown conversion (e.g., `adf-to-md`, `md-to-adf`).

### API Characteristics

- **Rate limit:** Per-user, per-app. ~100 requests/sec burst, sustained varies by plan.
- **Webhooks:** Project-scoped via Jira webhooks or Atlassian Connect events. Rich payloads.
- **JQL:** Powerful query language for filtered sync: `project = PROJ AND updated >= -15m`.
- **Bulk operations:** `POST /rest/api/3/search` with JQL returns up to 100 issues per page.

---

## Cross-Provider Comparison Matrix

### Field Coverage

| bpkm Property | Asana | Monday | Linear | Jira |
|---|---|---|---|---|
| `dcterms:title` | ✅ name | ✅ name | ✅ title | ✅ summary |
| `dcterms:description` | ✅ notes (HTML) | ✅ long_text | ✅ description (MD) | ✅ description (ADF) |
| `bpkm:taskStatus` | ⚠️ completed + custom | ⚠️ status column (custom) | ✅ state.type | ✅ statusCategory |
| `bpkm:priority` | ⚠️ custom field | ⚠️ status/priority col | ✅ priority (0-4) | ✅ priority |
| `bpkm:startDate` | ✅ start_on | ✅ timeline.from | ✅ startedAt | ❌ (custom field) |
| `bpkm:dueDate` | ✅ due_on | ✅ date | ✅ dueDate | ✅ duedate |
| `bpkm:completedDate` | ✅ completed_at | ❌ | ✅ completedAt | ✅ resolutiondate |
| `bpkm:effort` | ❌ | ❌ | ❌ | ❌ |
| `bpkm:storyPoints` | ⚠️ custom field | ⚠️ numbers column | ✅ estimate | ⚠️ custom field |
| `bpkm:assignedTo` | ✅ assignee (single) | ✅ people (multi) | ✅ assignee (single) | ✅ assignee (single) |
| `bpkm:followers` | ✅ followers | ⚠️ subscribers | ✅ subscribers | ✅ watches |
| `bpkm:parentTask` | ✅ parent (5 lvls) | ✅ subitems (5 lvls) | ✅ parent (unlimited) | ✅ parent (1-2 lvls) |
| `bpkm:taskProject` | ✅ projects (multi!) | ✅ board (single) | ✅ project (single) | ✅ project (single) |
| `bpkm:taskGroup` | ✅ section | ✅ group | ✅ cycle | ✅ sprint |
| `bpkm:dependsOn` | ✅ dependencies | ✅ dependency col | ✅ relations | ✅ issuelinks |
| `bpkm:tags` | ✅ tags | ✅ tags column | ✅ labels | ✅ labels + components |
| `bpkm:externalId` | ✅ gid | ✅ id | ✅ identifier | ✅ key |
| `bpkm:externalUrl` | ✅ permalink_url | ⚠️ construct | ✅ url | ⚠️ construct from key |
| `bpkm:externalStatus` | ⚠️ custom field label | ✅ status label | ✅ state.name | ✅ status.name |
| `bpkm:syncDirection` | N/A (config) | N/A (config) | N/A (config) | N/A (config) |

**Legend:** ✅ Direct mapping | ⚠️ Requires configuration or transform | ❌ Not available

### Status Normalization Reliability

| Provider | Strategy | Reliability | Notes |
|---|---|---|---|
| **Linear** | `state.type` enum | ⭐⭐⭐⭐⭐ | Built-in category. Best. |
| **Jira** | `statusCategory.key` | ⭐⭐⭐⭐ | Reliable but no "blocked" |
| **Asana** | Custom field + sections | ⭐⭐ | Requires user configuration |
| **Monday** | Custom status labels | ⭐⭐ | Requires user configuration |

### Webhook Quality

| Provider | Payload Quality | Suppression | Reliability |
|---|---|---|---|
| **Linear** | Rich (full data) | ✅ | ⭐⭐⭐⭐⭐ |
| **Jira** | Rich (configurable) | ✅ | ⭐⭐⭐⭐ |
| **Asana** | Minimal (GID only) | ✅ | ⭐⭐⭐ |
| **Monday** | Minimal (ID + value) | ❌ (loop risk!) | ⭐⭐ |

---

## Bidirectional Sync Architecture

### Sync Flow

```
Provider API ──webhook/poll──→ Sync App ──normalize──→ POST /api/commands ──→ SemPKM Graph
                                                                                    │
                                                            Tasks with externalProvider,
                                                            externalId, externalStatus,
                                                            lastSyncedAt, syncDirection
                                                                                    │
SemPKM Graph ──change event──→ Sync App ──denormalize──→ Provider API ──→ Provider Updated
```

### Conflict Resolution

When both sides change since `lastSyncedAt`:

1. **Field-level comparison** — only conflict on fields that both sides changed
2. **Status:** Provider wins (it's the workflow source of truth)
3. **Title/Description:** Last-write-wins (compare timestamps)
4. **SemPKM-only fields** (tags, relationships, notes): SemPKM always wins (provider doesn't have these)
5. **Provider-only fields** (custom fields not mapped): Provider always wins
6. **Configurable default:** User can set "prefer SemPKM" or "prefer provider" per integration

### Monday.com Loop Guard

```python
class LoopGuard:
    """Prevents webhook echo loops for Monday.com sync."""

    def __init__(self, ttl_seconds=10):
        self.recent_changes = {}  # (item_id, column_id) → timestamp
        self.ttl = ttl_seconds

    def mark_pushed(self, item_id, column_id):
        self.recent_changes[(item_id, column_id)] = time.time()

    def is_echo(self, item_id, column_id):
        key = (item_id, column_id)
        if key in self.recent_changes:
            if time.time() - self.recent_changes[key] < self.ttl:
                del self.recent_changes[key]
                return True
        return False
```

---

## 5. Google Calendar → bpkm:Event

### Entity Mapping

| Google Calendar Entity | SemPKM Type | Notes |
|---|---|---|
| Event | `bpkm:Event` | Direct |
| Recurring Event (master) | `bpkm:Event` + `bpkm:recurrenceRule` | Series master stores RRULE |
| Recurring Event (instance) | `bpkm:Event` + `bpkm:recurringEventId` | Links back to master |
| Calendar | `bpkm:calendarName` (string) | Calendar name preserved |
| Attendee | `bpkm:Person` (via `bpkm:attendee`) | Match by email or create |
| Organizer | `bpkm:Person` (via `bpkm:organizer`) | Match by email |

### Field Mapping

| Google Calendar Field | bpkm Property | Transform | Direction |
|---|---|---|---|
| `summary` | `dcterms:title` | Direct | ↔ |
| `description` | `dcterms:description` | HTML → Markdown | ↔ |
| `start.dateTime` / `start.date` | `schema:startDate` | dateTime direct; date → allDay=true | ↔ |
| `end.dateTime` / `end.date` | `schema:endDate` | dateTime direct; date → allDay=true | ↔ |
| `start.timeZone` | `bpkm:timeZone` | IANA identifier | ↔ |
| `status` | `bpkm:eventStatus` | confirmed/tentative/cancelled — exact match | ↔ |
| `location` | `bpkm:location` | Direct (physical location string) | ↔ |
| `visibility` | `bpkm:visibility` | default→public, public/private/confidential | ↔ |
| `transparency` | `bpkm:showAs` | opaque→busy, transparent→free | ↔ |
| `recurrence` | `bpkm:recurrenceRule` | First RRULE from array | ← |
| `recurringEventId` | `bpkm:recurringEventId` | Direct | ← |
| `attendees[].email` | `bpkm:attendee` → Person | Match by email, create if missing | ↔ |
| `attendees[self=true].responseStatus` | `bpkm:responseStatus` | needsAction→needs-action, rest direct | ↔ |
| `organizer.email` | `bpkm:organizer` → Person | Match by email | ← |
| `conferenceData.entryPoints[type=video].uri` | `bpkm:conferenceUrl` | First video entry point URI | ← |
| `hangoutLink` | `bpkm:conferenceUrl` (fallback) | Used if no conferenceData | ← |
| `reminders.overrides[0].minutes` | `bpkm:reminderMinutes` | First override, or default (30) | ↔ |
| `colorId` | `bpkm:tags` | Map to tag like `color:tomato` | ← |
| `htmlLink` | `bpkm:externalUrl` | Direct | ← |
| `id` | `bpkm:externalId` | Direct | ← |
| `iCalUID` | — | Stored for CalDAV cross-reference if needed | ← |
| `created` | `dcterms:created` | Direct | ← |
| `updated` | `dcterms:modified` | Direct | ← |
| *(all-day detection)* | `bpkm:allDay` | `start.date` present (no dateTime) → true | ↔ |

### Status Normalization

Google Calendar status maps 1:1 to our enum — no normalization needed:

| Google Status | bpkm:eventStatus | Notes |
|---|---|---|
| `confirmed` | confirmed | Default |
| `tentative` | tentative | Attendee hasn't accepted |
| `cancelled` | cancelled | Deleted or declined |

### Response Status Normalization

| Google responseStatus | bpkm:responseStatus | Notes |
|---|---|---|
| `needsAction` | needs-action | Default for new invites |
| `accepted` | accepted | |
| `declined` | declined | |
| `tentative` | tentative | |

### Visibility & ShowAs Mapping

| Google Field | Google Value | bpkm Property | bpkm Value |
|---|---|---|---|
| `visibility` | `default` | `bpkm:visibility` | (omit — uses calendar default, typically public) |
| `visibility` | `public` | `bpkm:visibility` | `public` |
| `visibility` | `private` | `bpkm:visibility` | `private` |
| `visibility` | `confidential` | `bpkm:visibility` | `confidential` |
| `transparency` | `opaque` | `bpkm:showAs` | `busy` |
| `transparency` | `transparent` | `bpkm:showAs` | `free` |

**Gap:** Google only supports busy/free. No out-of-office or working-elsewhere — those are Outlook-specific values we preserve for round-trip fidelity.

### Recurrence Handling

Google stores recurrence as an array of RFC 5545 strings on the series master event:
```
["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR", "EXDATE:20260320T090000Z"]
```

**Strategy:**
- **Pull:** Store the first RRULE in `bpkm:recurrenceRule`. EXDATE/RDATE handled by individual exception instances.
- **Instance events:** Have `recurringEventId` pointing to the master. Store `originalStartTime` as the instance's `schema:startDate`.
- **Push:** When user creates a recurring event in SemPKM, push the RRULE to Google. Editing a single instance creates an exception.
- **Expansion:** SemPKM does NOT expand recurrence into individual events. Only instances that are modified (exceptions) or have SemPKM-specific data (notes, tasks) get individual Event objects.

### API Characteristics

- **Rate limit:** 1,000,000 queries/day per project, 500 queries/100 seconds/user
- **Pagination:** `pageToken` + `maxResults` (default 250, max 2500)
- **Push notifications:** Channel-based via webhook URL. Must be renewed every ~7 days.
- **Incremental sync:** `syncToken` on list endpoint — returns only changed events since last sync. Highly efficient.
- **Batch requests:** Up to 50 requests per batch. Useful for initial sync.
- **Watch endpoint:** `events.watch()` registers for push notifications on a calendar.

---

## 6. Outlook / Microsoft 365 → bpkm:Event

### Entity Mapping

| Outlook Entity | SemPKM Type | Notes |
|---|---|---|
| Event | `bpkm:Event` | Direct |
| Event (seriesMaster) | `bpkm:Event` + `bpkm:recurrenceRule` | Master stores recurrence pattern |
| Event (occurrence/exception) | `bpkm:Event` + `bpkm:recurringEventId` | Links to series master |
| Calendar | `bpkm:calendarName` (string) | Calendar name preserved |
| Attendee | `bpkm:Person` (via `bpkm:attendee`) | Match by email |
| Organizer | `bpkm:Person` (via `bpkm:organizer`) | Match by email |

### Field Mapping

| Outlook/Graph Field | bpkm Property | Transform | Direction |
|---|---|---|---|
| `subject` | `dcterms:title` | Direct | ↔ |
| `body.content` | `dcterms:description` | HTML→Markdown (if body.contentType=html) | ↔ |
| `bodyPreview` | — | Not stored (truncated, read-only) | — |
| `start.dateTime` + `start.timeZone` | `schema:startDate` + `bpkm:timeZone` | Combine into xsd:dateTime; TZ stored separately | ↔ |
| `end.dateTime` + `end.timeZone` | `schema:endDate` | Same as start | ↔ |
| `isAllDay` | `bpkm:allDay` | Direct boolean | ↔ |
| `location.displayName` | `bpkm:location` | Direct | ↔ |
| `showAs` | `bpkm:showAs` | free/tentative/busy direct; oof→out-of-office; workingElsewhere→working-elsewhere | ↔ |
| `sensitivity` | `bpkm:visibility` | normal→public; personal→public; private→private; confidential→confidential | ↔ |
| `isCancelled` | `bpkm:eventStatus` | true→cancelled; false→check response | ← |
| `importance` | `bpkm:tags` | low→tag `importance:low`; normal→omit; high→tag `importance:high` | ← |
| `recurrence.pattern` + `range` | `bpkm:recurrenceRule` | Convert Outlook pattern to RFC 5545 RRULE | ← |
| `seriesMasterId` | `bpkm:recurringEventId` | Direct | ← |
| `type` | — | Used to determine if instance/master/exception | ← |
| `attendees[].emailAddress.address` | `bpkm:attendee` → Person | Match by email | ↔ |
| `attendees[].status.response` | — | Per-attendee status not directly stored (only self response) | ← |
| `responseStatus.response` | `bpkm:responseStatus` | none→needs-action; organizer→accepted; tentativelyAccepted→tentative; accepted/declined direct | ↔ |
| `organizer.emailAddress.address` | `bpkm:organizer` → Person | Match by email | ← |
| `onlineMeeting.joinUrl` | `bpkm:conferenceUrl` | Direct | ← |
| `onlineMeetingUrl` | `bpkm:conferenceUrl` (fallback) | If no onlineMeeting object | ← |
| `isReminderOn` + `reminderMinutesBeforeStart` | `bpkm:reminderMinutes` | If isReminderOn=true, store minutes | ↔ |
| `categories` | `bpkm:tags` | Direct (Outlook categories become tags) | ↔ |
| `webLink` | `bpkm:externalUrl` | Direct | ← |
| `id` | `bpkm:externalId` | Direct | ← |
| `iCalUId` | — | Stored for CalDAV cross-reference if needed | ← |
| `createdDateTime` | `dcterms:created` | Direct | ← |
| `lastModifiedDateTime` | `dcterms:modified` | Direct | ← |

### Status Normalization

Outlook doesn't have a single "status" field like Google. Event status is derived from multiple fields:

| Outlook State | bpkm:eventStatus | Logic |
|---|---|---|
| `isCancelled=true` | cancelled | Event was cancelled |
| `responseStatus.response=tentativelyAccepted` | tentative | User tentatively accepted |
| All other cases | confirmed | Default |

### ShowAs Mapping

| Outlook showAs | bpkm:showAs | Notes |
|---|---|---|
| `free` | free | |
| `tentative` | tentative | |
| `busy` | busy | Default |
| `oof` | out-of-office | Outlook-specific |
| `workingElsewhere` | working-elsewhere | Outlook-specific |
| `unknown` | busy (default) | Fallback |

### Sensitivity → Visibility Mapping

| Outlook sensitivity | bpkm:visibility | Notes |
|---|---|---|
| `normal` | (omit) | Default — public |
| `personal` | (omit) | Treated as public in most clients |
| `private` | private | Only attendees see details |
| `confidential` | confidential | Only organizer sees details |

### Recurrence Handling

Outlook uses a structured recurrence object instead of RRULE:
```json
{
  "pattern": {
    "type": "weekly",
    "interval": 1,
    "daysOfWeek": ["monday", "wednesday", "friday"],
    "firstDayOfWeek": "sunday"
  },
  "range": {
    "type": "endDate",
    "startDate": "2026-03-01",
    "endDate": "2026-06-30"
  }
}
```

**Conversion to RFC 5545 RRULE:**
```
FREQ=WEEKLY;INTERVAL=1;BYDAY=MO,WE,FR;UNTIL=20260630T000000Z
```

**Pattern type mapping:**
| Outlook `pattern.type` | RRULE `FREQ` |
|---|---|
| `daily` | `DAILY` |
| `weekly` | `WEEKLY` |
| `absoluteMonthly` | `MONTHLY` (with `BYMONTHDAY`) |
| `relativeMonthly` | `MONTHLY` (with `BYDAY` + `BYSETPOS`) |
| `absoluteYearly` | `YEARLY` (with `BYMONTH` + `BYMONTHDAY`) |
| `relativeYearly` | `YEARLY` (with `BYMONTH` + `BYDAY` + `BYSETPOS`) |

**Range type mapping:**
| Outlook `range.type` | RRULE clause |
|---|---|
| `endDate` | `UNTIL=<endDate>` |
| `numbered` | `COUNT=<numberOfOccurrences>` |
| `noEnd` | (no UNTIL or COUNT) |

### Response Status Mapping

| Outlook responseStatus.response | bpkm:responseStatus | Notes |
|---|---|---|
| `none` | needs-action | No response yet |
| `organizer` | accepted | Organizer is implicitly accepted |
| `tentativelyAccepted` | tentative | |
| `accepted` | accepted | |
| `declined` | declined | |
| `notResponded` | needs-action | Same as none |

### API Characteristics

- **Rate limit:** 10,000 requests per 10 minutes per app per mailbox
- **Pagination:** `@odata.nextLink` with `$top` (max 999 per page)
- **Delta queries:** `$deltaToken` returns only changes since last sync — similar to Google's syncToken
- **Webhooks (subscriptions):** Webhook URL receives change notifications. Max subscription lifetime: 4230 minutes (~3 days) for events. Must be renewed.
- **Batch requests:** Up to 20 requests per JSON batch via `/$batch` endpoint.
- **Calendar views:** `calendarView` endpoint expands recurrence into individual instances — useful for UI display.

---

## 7. CalDAV / iCalendar → bpkm:Event

### Entity Mapping

| CalDAV/iCalendar Entity | SemPKM Type | Notes |
|---|---|---|
| VEVENT | `bpkm:Event` | Direct |
| VEVENT with RRULE | `bpkm:Event` + `bpkm:recurrenceRule` | Series master |
| VEVENT with RECURRENCE-ID | `bpkm:Event` + `bpkm:recurringEventId` | Exception instance |
| VCALENDAR | `bpkm:calendarName` (string) | Calendar name |
| ATTENDEE | `bpkm:Person` (via `bpkm:attendee`) | Match by email (mailto: URI) |
| ORGANIZER | `bpkm:Person` (via `bpkm:organizer`) | Match by email |

### Field Mapping

| iCalendar Property | bpkm Property | Transform | Direction |
|---|---|---|---|
| `SUMMARY` | `dcterms:title` | Direct | ↔ |
| `DESCRIPTION` | `dcterms:description` | Plain text (some providers use HTML) | ↔ |
| `DTSTART` | `schema:startDate` | Convert to xsd:dateTime with TZ | ↔ |
| `DTEND` | `schema:endDate` | Convert to xsd:dateTime with TZ | ↔ |
| `DTSTART` (VALUE=DATE) | `bpkm:allDay` = true | Date-only → all-day event | ↔ |
| `DTSTART;TZID=...` | `bpkm:timeZone` | Extract TZID parameter | ↔ |
| `STATUS` | `bpkm:eventStatus` | TENTATIVE→tentative, CONFIRMED→confirmed, CANCELLED→cancelled | ↔ |
| `LOCATION` | `bpkm:location` | Direct | ↔ |
| `CLASS` | `bpkm:visibility` | PUBLIC→public, PRIVATE→private, CONFIDENTIAL→confidential | ↔ |
| `TRANSP` | `bpkm:showAs` | OPAQUE→busy, TRANSPARENT→free | ↔ |
| `RRULE` | `bpkm:recurrenceRule` | Direct (native RFC 5545) | ↔ |
| `RECURRENCE-ID` | `bpkm:recurringEventId` | UID of master event | ← |
| `ATTENDEE` (mailto:) | `bpkm:attendee` → Person | Extract email from mailto: URI | ↔ |
| `ATTENDEE;PARTSTAT=` | `bpkm:responseStatus` (for self) | NEEDS-ACTION→needs-action, ACCEPTED→accepted, DECLINED→declined, TENTATIVE→tentative | ↔ |
| `ORGANIZER` (mailto:) | `bpkm:organizer` → Person | Extract email | ← |
| `VALARM` TRIGGER | `bpkm:reminderMinutes` | Parse duration (e.g., -PT15M → 15) | ↔ |
| `CATEGORIES` | `bpkm:tags` | Comma-separated → array | ↔ |
| `UID` | `bpkm:externalId` | Direct | ← |
| `SEQUENCE` | — | Used for conflict detection | ← |
| `CREATED` | `dcterms:created` | Direct | ← |
| `LAST-MODIFIED` | `dcterms:modified` | Direct | ← |
| `URL` | `bpkm:externalUrl` | Direct | ← |

### CalDAV Sync Characteristics

- **Protocol:** WebDAV extension (HTTP methods: PROPFIND, REPORT, PUT, DELETE)
- **Sync method:** `sync-collection` REPORT with `sync-token` — returns changed/deleted resources since last sync
- **No webhooks (standard):** Polling required. Apple uses push notifications (proprietary).
- **ETags:** Used for optimistic concurrency — PUT with If-Match header prevents conflicts
- **iCalendar format:** Events exchanged as `.ics` files (RFC 5545 text format)
- **Auth:** HTTP Basic (Fastmail, Nextcloud), OAuth 2.0 (Google CalDAV), App-specific passwords (iCloud)

---

## Calendar Provider Cross-Comparison

### Field Coverage Matrix

| bpkm:Event Property | Google Calendar | Outlook/Graph | CalDAV/iCal | Notes |
|---|---|---|---|---|
| `dcterms:title` | ✅ summary | ✅ subject | ✅ SUMMARY | Universal |
| `dcterms:description` | ✅ description | ✅ body.content | ✅ DESCRIPTION | HTML vs plain text varies |
| `schema:startDate` | ✅ start | ✅ start | ✅ DTSTART | All support date+time+TZ |
| `schema:endDate` | ✅ end | ✅ end | ✅ DTEND | |
| `bpkm:allDay` | ✅ (date vs dateTime) | ✅ isAllDay | ✅ (VALUE=DATE) | Detection method varies |
| `bpkm:timeZone` | ✅ start.timeZone | ✅ start.timeZone | ✅ TZID | All use IANA identifiers |
| `bpkm:eventStatus` | ✅ status | ⚠️ (derived) | ✅ STATUS | Outlook derives from isCancelled + response |
| `bpkm:location` | ✅ location | ✅ location.displayName | ✅ LOCATION | |
| `bpkm:visibility` | ✅ visibility | ✅ sensitivity | ✅ CLASS | Enum names differ |
| `bpkm:showAs` | ⚠️ transparency (2 values) | ✅ showAs (5 values) | ⚠️ TRANSP (2 values) | Outlook richest; Google/CalDAV only busy/free |
| `bpkm:conferenceUrl` | ✅ conferenceData | ✅ onlineMeeting | ❌ | CalDAV has no standard conference field |
| `bpkm:recurrenceRule` | ✅ recurrence (RRULE) | ✅ recurrence (pattern→RRULE) | ✅ RRULE | All support RFC 5545; Outlook needs conversion |
| `bpkm:recurringEventId` | ✅ recurringEventId | ✅ seriesMasterId | ✅ RECURRENCE-ID | |
| `bpkm:organizer` | ✅ organizer | ✅ organizer | ✅ ORGANIZER | All provide email |
| `bpkm:attendee` | ✅ attendees[] | ✅ attendees[] | ✅ ATTENDEE | |
| `bpkm:responseStatus` | ✅ attendees[self].responseStatus | ✅ responseStatus.response | ✅ PARTSTAT | Enum values differ |
| `bpkm:reminderMinutes` | ✅ reminders.overrides | ✅ reminderMinutesBeforeStart | ✅ VALARM | Google supports multiple; we store first |
| `bpkm:tags` | ⚠️ colorId only | ✅ categories | ✅ CATEGORIES | Google has no categories |
| `bpkm:externalUrl` | ✅ htmlLink | ✅ webLink | ⚠️ URL (optional) | |
| `bpkm:meetingNotes` | ❌ | ❌ | ❌ | SemPKM-only field |
| `bpkm:eventProject` | ❌ | ❌ | ❌ | SemPKM-only relationship |
| `bpkm:generatedTask` | ❌ | ❌ | ❌ | SemPKM-only relationship |
| `bpkm:eventNote` | ❌ | ❌ | ❌ | SemPKM-only relationship |

### Sync Quality Ratings

| Dimension | Google Calendar | Outlook/Graph | CalDAV |
|---|---|---|---|
| **Field coverage** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Status reliability** | ⭐⭐⭐⭐⭐ (direct enum) | ⭐⭐⭐⭐ (derived) | ⭐⭐⭐⭐⭐ (direct enum) |
| **Recurrence support** | ⭐⭐⭐⭐⭐ (native RRULE) | ⭐⭐⭐⭐ (needs conversion) | ⭐⭐⭐⭐⭐ (native RRULE) |
| **Incremental sync** | ⭐⭐⭐⭐⭐ (syncToken) | ⭐⭐⭐⭐⭐ (deltaToken) | ⭐⭐⭐⭐ (sync-token) |
| **Push notifications** | ⭐⭐⭐⭐ (channel, 7-day renewal) | ⭐⭐⭐⭐ (subscription, 3-day renewal) | ⭐⭐ (polling or Apple push) |
| **Webhook payload** | ⭐⭐ (notification only, must GET) | ⭐⭐⭐ (resource data in notification) | N/A (poll-based) |
| **Batch support** | ⭐⭐⭐⭐⭐ (50/batch) | ⭐⭐⭐⭐ (20/batch) | ⭐⭐ (multiget REPORT) |

---

## Calendar Sync Architecture

### Sync Flow (extends Task sync architecture)

```
Calendar API ──push/poll──→ Sync App ──normalize──→ POST /api/commands ──→ SemPKM Graph
                                                                                 │
                                                     Events with externalProvider,
                                                     externalId, recurrenceRule,
                                                     conferenceUrl, responseStatus,
                                                     lastSyncedAt, syncDirection
                                                                                 │
SemPKM Graph ──change event──→ Sync App ──denormalize──→ Calendar API ──→ Provider Updated
```

### Calendar-Specific Sync Considerations

1. **Recurrence expansion:** SemPKM stores only the series master and explicitly modified exceptions. Calendar providers expand recurrence for display — our sync app should NOT create individual Event objects for every occurrence unless the user adds SemPKM-specific data (notes, tasks, project links) to a specific instance.

2. **Organizer vs attendee push:** When pushing a new event to a calendar provider, the SemPKM user becomes the organizer. When pulling, the organizer may be someone else. The `bpkm:organizer` field distinguishes these cases.

3. **Response status round-trip:** Changing `bpkm:responseStatus` in SemPKM should update the RSVP in the calendar provider. This is the primary "write-back" use case for calendar sync (most other fields are pull-only).

4. **Conference URL is read-only:** Google Meet and Teams links are generated by the calendar provider. SemPKM should never push a conference URL — only pull it.

5. **Time zone handling:** Store IANA time zone in `bpkm:timeZone`. Convert all datetimes to UTC for `schema:startDate`/`schema:endDate` in the RDF store, but preserve the original time zone for display and round-trip fidelity.

### Conflict Resolution (Calendar-Specific)

| Field | Resolution | Rationale |
|---|---|---|
| **Title/Description** | Provider wins | Calendar is the source of truth for event details |
| **Start/End times** | Provider wins | Time changes should originate from calendar |
| **Status (confirmed/tentative/cancelled)** | Provider wins | Calendar workflow controls this |
| **Response status (RSVP)** | Last-write-wins | User may RSVP from either side |
| **Location / Conference URL** | Provider wins | Usually set in calendar |
| **Recurrence rule** | Provider wins | Recurrence edits in calendar are complex |
| **Meeting notes** | SemPKM wins | SemPKM-only field |
| **Project / Task / Note links** | SemPKM wins | SemPKM-only relationships |
| **Tags** | Merge (union) | Both sides may add tags/categories |

---

## Remaining Gaps

### Not Yet Addressed (Tasks)

| Gap | Affected Providers | Priority | Recommendation |
|---|---|---|---|
| **Attachments/files** | All | Low | Out of scope for v1. File sync is complex (storage, bandwidth, versioning). |
| **Comments/activity** | All | Medium | Asana stories, Monday updates, Linear comments, Jira comments. Could map to `bpkm:Note` linked to task. Future work. |
| **Time tracking** | Asana, Monday, Jira | Low | Niche. Add `bpkm:actualTime` later if demand exists. |
| **Recurring tasks** | Asana, Monday | Low | Complex sync semantics. Punt to v2 of sync apps. |
| **Custom field round-trip** | Asana, Monday | Medium | Blank-node approach (`bpkm:customField` with name+value+type) for v1. |
| **Approvals** | Asana | Low | Asana-specific. Skip unless demand. |
| **Epics as Milestones** | Jira | Medium | Sync app should offer: Epic → Milestone vs Epic → Project (user configurable). |
| **Board views / Kanban** | Monday | Low | View-level, not data. Our views handle display independently. |

### Not Yet Addressed (Calendar)

| Gap | Affected Providers | Priority | Recommendation |
|---|---|---|---|
| **Per-attendee response status** | All | Medium | Currently only storing the current user's response. Individual attendee RSVP status (accepted/declined per person) could be modeled as blank nodes on the attendee relationship. Deferred. |
| **Multiple reminders** | Google Calendar | Low | Google supports multiple reminder overrides. We store only one `reminderMinutes`. Could add multi-value later. |
| **Attachments on events** | Google, Outlook | Low | Same complexity as task attachments. Out of scope for v1. |
| **Extended properties** | Google, Outlook | Low | Google `extendedProperties`, Outlook `singleValueExtendedProperties`. App-specific metadata. Ignore unless specific integration needs it. |
| **Location coordinates** | Outlook | Low | Outlook provides `location.coordinates` (lat/lng). Could add `bpkm:locationCoordinates` later. |
| **Multiple locations** | Outlook | Low | Outlook supports `locations[]` array. We store one string. Sufficient for v1. |
| **Free/busy queries** | Google, Outlook | Low | Separate API endpoint for availability checking. Not part of event sync — future feature. |
| **Calendar sharing/permissions** | All | Low | Calendar-level access control. Out of scope — handled by provider. |
| **Travel time** | Apple Calendar | Low | Apple-specific `X-APPLE-TRAVEL-DURATION`. Skip. |

### Custom Fields (Future — v2 of sync apps)

Recommended blank-node approach for preserving provider custom fields:

```turtle
<task:123> bpkm:customField [
    bpkm:cfName "Sprint" ;
    bpkm:cfValue "Sprint 42" ;
    bpkm:cfType "text" ;
    bpkm:cfProvider "asana" ;
    bpkm:cfProviderId "cf_12345"
] .
```

SPARQL queryable: `SELECT ?task ?val WHERE { ?task bpkm:customField [ bpkm:cfName "Sprint" ; bpkm:cfValue ?val ] }`

This requires adding to the ontology:
- `bpkm:customField` (ObjectProperty, domain: Task, range: blank node)
- `bpkm:cfName`, `bpkm:cfValue`, `bpkm:cfType`, `bpkm:cfProvider`, `bpkm:cfProviderId` (DatatypeProperties)

Deferred to when we build the actual sync apps (post-M009).

---

## Implementation Priority

### Task/PM Sync Apps

| Sync App | Priority | Rationale |
|---|---|---|
| `sempkm-app-linear` | 1 | Best API (rich webhooks, clean state types, GraphQL). Startup audience. Easiest to build first. |
| `sempkm-app-github` | 2 | Developer audience. Issues + PRs. OAuth well-understood. |
| `sempkm-app-asana` | 3 | Large user base. More complex (custom fields, sections, no native status). |
| `sempkm-app-jira` | 4 | Enterprise. Most complex (ADF, workflows, Atlassian Connect auth). |
| `sempkm-app-monday` | 5 | Column-centric model requires most mapping work. Webhook loop issue adds engineering cost. |

### Calendar Sync Apps

| Sync App | Priority | Rationale |
|---|---|---|
| `sempkm-app-google-calendar` | 1 | Largest user base. Excellent API (syncToken, push notifications, native RRULE). Best docs. |
| `sempkm-app-outlook` | 2 | Enterprise/Microsoft 365 users. Good API (delta queries, webhooks). Recurrence needs RRULE conversion. |
| `sempkm-app-caldav` | 3 | Covers Fastmail, Nextcloud, Synology, any standards-compliant server. Native iCalendar format. Poll-based sync. |
| `sempkm-app-apple-calendar` | 4 | Via CalDAV with Apple push notifications. iCloud auth complexity (app-specific passwords). Lower priority — CalDAV covers basic access. |
| `sempkm-app-todoist` | 6 | Simple API. Individual users. Quick build. |
