# Integration Domain Mapping — Design Document

**Created:** 2026-03-16
**Status:** Draft
**Goal:** Validate that `bpkm:Task` (basic-pkm v2.1) can faithfully represent tasks from major PM providers, identify remaining gaps, and assess bidirectional sync feasibility.

---

## Provider Coverage

| Provider | API Type | Auth | Webhooks | Sync Feasibility |
|---|---|---|---|---|
| **Asana** | REST | OAuth 2.0 | Yes (project-scoped) | Bidirectional ✅ |
| **Monday.com** | GraphQL | OAuth 2.0 / API Token | Yes (board-scoped) | Bidirectional ✅ (with loop guard) |
| **Linear** | GraphQL | OAuth 2.0 / API Key | Yes (workspace-scoped) | Bidirectional ✅ |
| **Jira Cloud** | REST v3 | OAuth 2.0 (Atlassian Connect) | Yes (project-scoped) | Bidirectional ✅ |

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

## Remaining Gaps

### Not Yet Addressed

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

| Sync App | Priority | Rationale |
|---|---|---|
| `sempkm-app-linear` | 1 | Best API (rich webhooks, clean state types, GraphQL). Startup audience. Easiest to build first. |
| `sempkm-app-github` | 2 | Developer audience. Issues + PRs. OAuth well-understood. |
| `sempkm-app-asana` | 3 | Large user base. More complex (custom fields, sections, no native status). |
| `sempkm-app-jira` | 4 | Enterprise. Most complex (ADF, workflows, Atlassian Connect auth). |
| `sempkm-app-monday` | 5 | Column-centric model requires most mapping work. Webhook loop issue adds engineering cost. |
| `sempkm-app-todoist` | 6 | Simple API. Individual users. Quick build. |
