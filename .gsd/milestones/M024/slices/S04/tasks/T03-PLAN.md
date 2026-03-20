---
estimated_steps: 7
estimated_files: 6
---

# T03: User guide Chapter 37 + docs file updates

**Slice:** S04 — E2E tests + user guide
**Milestone:** M024

## Description

Write the Monday.com Sync user guide (Chapter 37) and update all three navigation files plus the appendix and glossary. The guide clones Chapter 36 (Jira Sync) structure but replaces Jira-specific content with Monday.com's unique column mapping workflow, custom label mapping, LoopGuard echo prevention, and the simpler single-token authentication.

**Key differences from Jira guide:**
- Monday.com uses a single API token (not email + token + site URL)
- Monday.com has fully customizable columns requiring a column mapping configuration step (novel to this app — the core UX differentiator)
- Status/priority labels are custom per-board — users must map them to bpkm enum values
- Monday.com uses LoopGuard TTL cache for echo prevention (not lastSyncedAt comparison like Jira)
- Groups are structural containers (not columns), subitems are separate items with parentTask linking
- Dependency columns create bpkm:dependsOn edges
- No JQL equivalent — filtering is done by board/project selection only
- No ADF conversion — Monday.com uses plain text and rich text columns

**KNOWLEDGE.md rule**: Three files must stay in sync — README.md TOC, index.html sidebar, guide.html in-app page.

## Steps

1. **Create `docs/guide/37-monday-sync.md`** (~350 lines) with these sections:

   **Header:**
   ```markdown
   # Chapter 37: Monday.com Sync
   ```

   **Intro paragraph** — Monday.com Sync connects Monday.com boards to SemPKM, synchronizing items as `bpkm:Task` objects. Highlight the key differentiator: user-configurable column mapping with type-filtered dropdowns, custom label mapping for status/priority, and LoopGuard echo prevention.

   **Prerequisites** (same structure as Ch 36):
   - Basic PKM model installed
   - Monday.com account with board access
   - API token from Monday.com: Administration → Developers → My Access Tokens (or My Apps → Personal API Token). Copy the token.

   **Installing the App**:
   - Admin > Applications, enter `/app/apps/monday-sync`, click Install, wait for Running status

   **Connecting to Monday.com**:
   - Single API token authentication (simpler than Jira's 3-field form)
   - Fill in the API token field, click Connect
   - On success: Connected badge, display name, boards list, sync config
   - Auth method table: API Token (Available), OAuth 2.0 (Not available)
   - Troubleshooting connection failures

   **Board Selection**:
   - Check boards to sync, click Save
   - Only items from selected boards are synced

   **Column Mapping** (novel section — this is the key differentiator):
   - Monday.com boards have fully customizable columns — unlike Jira/GitHub/Linear where field mapping is fixed
   - After selecting a board, click "Configure Columns" to open the column mapping form
   - The form shows dropdowns for each bpkm property (status, priority, due date, assignee, etc.)
   - Each dropdown is **type-filtered** — only Monday.com columns with compatible types appear as options
   - Worked example: "Status" column → maps to `bpkm:taskStatus`, "Priority" column → maps to `bpkm:priority`, "Due Date" → `bpkm:dueDate`, "Assignee" → `bpkm:assignedTo`
   - Column type compatibility table:

   | bpkm Property | Compatible Monday.com Column Types |
   |---|---|
   | taskStatus | status |
   | priority | status |
   | dueDate | date |
   | assignedTo | people |
   | tags | tag, dropdown |
   | description | text, long_text |

   **Status Label Mapping**:
   - Monday.com status columns have custom labels (e.g., "Working on it", "Stuck", "Done")
   - After configuring columns, click "Configure Labels" to map these to bpkm:taskStatus values
   - Mapping table example: "Working on it" → in-progress, "Done" → done, "Stuck" → blocked
   - Available bpkm:taskStatus values: todo, in-progress, done, cancelled, blocked

   **Priority Label Mapping**:
   - Same approach for priority columns: map Monday.com priority labels to bpkm:priority values
   - Available bpkm:priority values: critical, high, medium, low

   **Sync Configuration** (same structure as Jira):
   - Direction: Pull only (default) or Bidirectional
   - Poll Interval table: 5m/15m/30m/1h
   - Save Config button

   **Manual Sync** — Sync Now button description

   **Field Mapping Table** (comprehensive — all column types):

   | Monday.com Column Type | SemPKM Property | Transform | Direction |
   |---|---|---|---|
   | status | bpkm:taskStatus | Via label mapping | ↔ |
   | status (priority) | bpkm:priority | Via label mapping | ↔ |
   | date | bpkm:dueDate | Date string | ← only |
   | people | bpkm:assignedTo | Person resolution | ← only |
   | text | dcterms:title or body | Direct | ← only |
   | long_text | Body content | Direct | ← only |
   | numbers | Custom property | Numeric string | ← only |
   | tag | bpkm:tags | Tag name resolution | ← only |
   | dropdown | bpkm:tags | Label text | ← only |
   | dependency | bpkm:dependsOn | Edge creation | ← only |
   | Item name | dcterms:title | Direct | ↔ |
   | Item URL | bpkm:externalUrl | Constructed | ← only |
   | Item ID | bpkm:externalUuid | String | ← only |

   **LoopGuard Echo Prevention** (novel section):
   - Explain the problem: in bidirectional mode, pushing a change to Monday.com updates the item's timestamp. The next poll sees the "changed" item and re-imports it, creating an infinite loop.
   - Explain the solution: LoopGuard marks each pushed (item_id, column_id) pair with a 30-second TTL. During the next pull, if a change falls within the TTL window, it's recognized as an echo and skipped.
   - Note: LoopGuard is in-memory — marks are lost on app restart, which is acceptable because echo loops only occur within the same process lifetime.

   **Groups as taskGroup**:
   - Monday.com groups are structural containers (not columns)
   - Group title maps to `bpkm:taskGroup`
   - Example: items in group "Sprint 5" get `bpkm:taskGroup: "Sprint 5"`

   **Subitems as parentTask**:
   - Monday.com subitems are separate items nested under a parent
   - Each subitem becomes its own `bpkm:Task` with a `bpkm:parentTask` edge to the parent task

   **Dependencies as dependsOn**:
   - Monday.com dependency columns link items to their blockers
   - These create `bpkm:dependsOn` edges between the corresponding tasks in SemPKM

   **Troubleshooting** (similar structure to Jira):
   - "Not connected" after entering token
   - No boards appearing after connecting
   - No tasks appearing after sync
   - Column mapping issues
   - Push changes not reflected in Monday.com
   - App shows "Error" status

   **See Also** — links to Ch 29 (App Platform), Ch 10 (Mental Models), Appendix A

   **Navigation footer**: `**Previous:** [Chapter 36: Jira Sync](36-jira-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`

2. **Update `docs/guide/README.md`** — add line after the Jira entry (line 65):
   ```markdown
   37. [Monday.com Sync](37-monday-sync.md)
   ```

3. **Update `docs/guide/index.html`** — add `<li>` after the Jira entry (line 479):
   ```html
   <li><a href="#" data-file="37-monday-sync.md">37. Monday.com Sync</a></li>
   ```

4. **Update `backend/app/templates/guide.html`** — add `<button>` entry after the Jira entry (~line 374):
   ```html
         <button class="docs-chapter-item"
                 hx-get="/guide/37-monday-sync.md"
                 hx-target="#app-content"
                 hx-swap="innerHTML"
                 hx-push-url="true">
           <i data-lucide="columns-3"></i>
           <span>37. Monday.com Sync</span>
         </button>
   ```
   Use `columns-3` Lucide icon (represents the board/column nature of Monday.com).

5. **Update `docs/guide/appendix-a-environment-variables.md`** — add row after `JIRA_API_URL`:
   ```markdown
   | `MONDAY_API_URL` | Override the Monday.com GraphQL API URL. Used for testing with a mock server. | `https://api.monday.com/v2` | Monday.com Sync |
   ```

6. **Update `docs/guide/appendix-d-glossary.md`** — add 3 entries in alphabetical order:

   **Column Mapping** (insert between "Comment" and "Command"):
   ```markdown
   **Column Mapping**
   The user-configurable mapping between Monday.com board columns and SemPKM properties. Because Monday.com boards have fully customizable columns, the mapping cannot be hardcoded — users configure which columns correspond to status, priority, due date, etc. via type-filtered dropdowns. See [Chapter 37: Monday.com Sync](37-monday-sync.md).
   ```

   **LoopGuard** (insert between "Lint" and "Mental Model"):
   ```markdown
   **LoopGuard**
   An in-memory TTL cache that prevents echo loops in bidirectional sync. When a change is pushed to Monday.com, LoopGuard marks the affected item/column pair for 30 seconds. If the next pull sees the same change within that window, it recognizes it as an echo of the push and skips it. See [Chapter 37: Monday.com Sync](37-monday-sync.md).
   ```

   **Monday.com Sync** (insert between "Model" and "Named Graph"):
   ```markdown
   **Monday.com Sync**
   An app that synchronizes Monday.com board items with SemPKM `bpkm:Task` objects. Supports user-configurable column mapping, custom status/priority label mapping, bidirectional sync with LoopGuard echo prevention, groups as taskGroup, subitems as parentTask, and dependency edges. See [Chapter 37: Monday.com Sync](37-monday-sync.md).
   ```

7. **Update navigation chain** — fix the Chapter 36 footer to point to Chapter 37 instead of Appendix A:
   - In `docs/guide/36-jira-sync.md`, change the last line from:
     ```
     **Previous:** [Chapter 35: GitHub Sync](35-github-sync.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
     ```
     to:
     ```
     **Previous:** [Chapter 35: GitHub Sync](35-github-sync.md) | **Next:** [Chapter 37: Monday.com Sync](37-monday-sync.md)
     ```

## Must-Haves

- [ ] Chapter 37 exists with ~350 lines covering all sections
- [ ] Column mapping walkthrough section explains type-filtered dropdowns with worked example
- [ ] Status/priority label mapping documented with example mappings
- [ ] LoopGuard echo prevention documented with explanation of the TTL mechanism
- [ ] Field mapping table covers all 12 column types
- [ ] Groups, subitems, and dependencies sections present
- [ ] Troubleshooting section present
- [ ] README.md TOC has Chapter 37 entry
- [ ] index.html sidebar has Chapter 37 entry
- [ ] guide.html in-app page has Chapter 37 button
- [ ] Appendix A has MONDAY_API_URL row
- [ ] Glossary has 3 new entries (Column Mapping, LoopGuard, Monday.com Sync)
- [ ] Navigation chain: Ch 36 → Ch 37 → Appendix A

## Verification

- `test -f docs/guide/37-monday-sync.md` — file exists
- `wc -l docs/guide/37-monday-sync.md` — ~350 lines (300-400 range)
- `grep -c "37-monday-sync" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all 3 files return at least 1 match
- `grep "MONDAY_API_URL" docs/guide/appendix-a-environment-variables.md` — at least 1 match
- `grep -c "Column Mapping\|LoopGuard\|Monday.com Sync" docs/guide/appendix-d-glossary.md` — at least 3 matches
- `grep "37-monday-sync" docs/guide/36-jira-sync.md` — navigation chain updated

## Inputs

- `docs/guide/36-jira-sync.md` — Reference chapter to clone structure from (383 lines)
- `docs/guide/README.md` — Line 65 has Jira entry, add Monday.com after it
- `docs/guide/index.html` — Line 479 has Jira entry, add Monday.com after it
- `backend/app/templates/guide.html` — Lines 367-374 have Jira entry, add Monday.com after it
- `docs/guide/appendix-a-environment-variables.md` — Line 46 has JIRA_API_URL, add MONDAY_API_URL after
- `docs/guide/appendix-d-glossary.md` — Alphabetical glossary, insert 3 entries
- S01 Summary: Single API token auth (not email + token + site like Jira)
- S02 Summary: Column mapping UI with type-filtered dropdowns, per-board storage, label mapping
- S03 Summary: LoopGuard TTL cache, push sync, dependency edges, tag resolution
- Research: `COLUMN_TYPE_COMPATIBILITY` maps bpkm properties to compatible Monday.com column types
- D242: Per-board column mapping storage keys
- D243: Group title from item.group, not column_values

## Expected Output

- `docs/guide/37-monday-sync.md` — ~350 lines, complete Monday.com Sync user guide
- `docs/guide/README.md` — Chapter 37 entry added to TOC
- `docs/guide/index.html` — Chapter 37 entry added to sidebar
- `backend/app/templates/guide.html` — Chapter 37 button added to in-app page
- `docs/guide/appendix-a-environment-variables.md` — MONDAY_API_URL row added
- `docs/guide/appendix-d-glossary.md` — 3 glossary entries added
- `docs/guide/36-jira-sync.md` — Navigation footer updated to point to Chapter 37

## Observability Impact

This task produces documentation files only — no runtime behavior changes.

- **Guide navigation integrity**: Verify with `grep -c "37-monday-sync" docs/guide/README.md docs/guide/index.html backend/app/templates/guide.html` — all three must return ≥1.
- **Navigation chain**: `grep "37-monday-sync" docs/guide/36-jira-sync.md` confirms Ch 36 → Ch 37 link. The Ch 37 footer itself links to Appendix A.
- **Glossary completeness**: `grep -c "^\*\*Column Mapping\*\*\|^\*\*LoopGuard\*\*\|^\*\*Monday.com Sync\*\*" docs/guide/appendix-d-glossary.md` — must return 3.
- **Failure mode**: If a guide navigation file is missed, users navigating in-app or in the static docs site will skip from Ch 36 to Appendix A with no Ch 37 entry. The three-file sync rule (README.md TOC, index.html sidebar, guide.html in-app) is enforced by grep verification.
