# Obsidian Import Wizard: Interactive UX/UI Flow Design

**Status:** Research document -- specification for future implementation
**Date:** 2026-03-03
**Context:** Replaces the external-script workflow described in Chapter 24 (Obsidian Onboarding) with an in-app interactive wizard modeled on OpenRefine's column reconciliation UX.

---

## 1. Overview and Design Goals

### Current Workflow (Chapter 24)

The existing Obsidian onboarding workflow requires three separate external Python scripts run outside SemPKM:

1. **vault_audit.py** -- scans the vault directory, extracts file counts, frontmatter keys, link targets, and tags. Output is a printed summary in the terminal.
2. **classify_vault.py** -- sends each note to an OpenAI-compatible LLM API for type classification. Output is a CSV file requiring manual review in a spreadsheet editor.
3. **import_to_sempkm.py** -- reads the reviewed CSV and vault files, builds Command API payloads, and batch-sends them to SemPKM.

This workflow has significant usability gaps:
- Requires Python, pip dependencies (requests, pyyaml), and a terminal
- CSV review in a spreadsheet is disconnected from the app
- No visual feedback during classification or import
- No interactive type/property mapping -- the user edits CSV cells by hand
- No undo or rollback mechanism
- LLM API key required even for vaults where folder-based classification would suffice

### Proposed In-App Wizard

An interactive import wizard built into SemPKM's workspace UI that provides a guided, visual experience for importing Obsidian vaults. The wizard replaces all three external scripts with a single in-app flow.

### Design Principles

1. **Progressive disclosure** -- each wizard step reveals only what the user needs at that stage. The vault scan summary appears before type mapping; type mapping appears before property mapping.

2. **OpenRefine-style reconciliation** -- the type and property mapping steps draw directly from OpenRefine's column reconciliation UX: a table of items with auto-suggested assignments, bulk operations via facets/filters, and a live distribution summary that updates as the user works.

3. **Batch-then-review** -- the wizard auto-suggests mappings (by folder, by frontmatter patterns, by string similarity) and presents them for review. The user corrects exceptions rather than configuring every file individually.

4. **No data loss** -- unmapped frontmatter keys are explicitly handled (skip or store as tag). Wiki-links to non-existent targets are logged, not silently dropped. The original vault is never modified.

5. **Server-side state** -- wizard state lives in the backend (SQLAlchemy models or session store), not in browser JavaScript. This allows the user to close the browser mid-wizard and resume later.

6. **Type-level mappings** -- property mappings apply to ALL files of a given type, not per-file. If the user maps `related` to `skos:related` for type Note, every Note file with a `related` frontmatter key inherits that mapping. This is the key UX insight from OpenRefine: reconciliation operates on columns (types), not rows (files).

---

## 2. Wizard Step Sequence

The wizard consists of six steps, presented as a horizontal stepper bar at the top of the wizard panel. Each step is an htmx partial page load.

```
[1. Scan] --> [2. Type Mapping] --> [3. Property Mapping] --> [4. Relationships] --> [5. Preview] --> [6. Import]
```

### Step 1: Start Import Job (Vault Scan)

**Purpose:** User selects a folder of .md files. Backend scans the folder, extracts file metadata, and displays a vault audit summary.

**Entry point:** Settings page or workspace toolbar button: "Import from Obsidian"

**Interaction flow:**

1. User enters or browses to a vault folder path (server filesystem path, since SemPKM runs locally or in Docker with volume mounts)
2. User clicks "Scan Vault"
3. Backend walks the directory, extracts metadata for each .md file:
   - Relative file path
   - Parent folder name
   - YAML frontmatter keys and values
   - Wiki-link targets (`[[target]]`)
   - Tags (`#tag`)
   - File size and modification date
4. Display summary stats as a dashboard card grid:
   - Total .md files found
   - Files with frontmatter (count and percentage)
   - Unique frontmatter keys (top 10 listed)
   - Folder distribution (bar chart or table)
   - Wiki-link count and unique target count
   - Tag count and top tags
5. User reviews the summary and clicks "Next: Map Types"

**Error handling:**
- Path does not exist or is not readable: show inline error with suggestion
- No .md files found: show warning, suggest checking the path
- Very large vault (>5000 files): show warning about processing time, proceed normally

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import from Obsidian                          Step 1 of 6: Scan  |
+------------------------------------------------------------------+
|                                                                  |
|  Vault Path: [/home/user/obsidian-vault________] [Browse] [Scan] |
|                                                                  |
|  +--- Vault Summary ----------------------------------------+   |
|  |                                                           |   |
|  |  Total Files     347       Files w/ Frontmatter  89 (26%) |   |
|  |  Unique Tags      54       Unique Link Targets       412  |   |
|  |                                                           |   |
|  |  --- Folder Distribution ---                              |   |
|  |  Daily Notes ........... 142  (41%)                       |   |
|  |  Meetings ............... 44  (13%)                       |   |
|  |  Projects ............... 31  ( 9%)                       |   |
|  |  People ................. 28  ( 8%)                       |   |
|  |  Concepts ............... 19  ( 5%)                       |   |
|  |  (root) ................. 83  (24%)                       |   |
|  |                                                           |   |
|  |  --- Top Frontmatter Keys ---                             |   |
|  |  date (89)  tags (67)  status (31)  aliases (22)          |   |
|  |  type (18)  priority (15)  related (12)  source (8)       |   |
|  |                                                           |   |
|  +-----------------------------------------------------------+   |
|                                                                  |
|                                          [Cancel]  [Next: Types] |
+------------------------------------------------------------------+
```

---

### Step 2: Type Mapping (OpenRefine-style)

**Purpose:** Assign a SemPKM type to each file. Default: all files start as Note. User uses bulk operations (folder-based, glob patterns, manual selection) to reassign types.

**Data source for available types:** `ShapesService.get_types()` returns all types from installed Mental Model shapes graphs. Not hardcoded to Basic PKM -- if a custom model adds Recipe or Meeting types, they appear here.

**Layout:** Split view with a file table on the left and a type distribution summary on the right.

**Interaction patterns:**

1. **Folder-based bulk assign:** Click a folder group header row to assign all files in that folder to a type. Example: click "People/" header, select "Person" from dropdown -- all 28 files in People/ become Person.

2. **Glob pattern assign:** A pattern input bar above the table. Enter `Projects/**` and select "Project" to assign all matching files. Patterns support `*` (single level) and `**` (recursive). Multiple patterns can be stacked.

3. **Individual file assign:** Each file row has a type dropdown. Click to change a single file's type.

4. **Filter/facet sidebar:** Filter the table by current assigned type, folder, or presence of specific frontmatter keys. This lets the user focus on unclassified files or review a specific type.

5. **Live distribution summary:** A sidebar card showing type counts that updates in real-time as assignments change:
   ```
   Note ........... 142  (41%)
   Person .......... 28  ( 8%)
   Project ......... 31  ( 9%)
   Concept ......... 19  ( 5%)
   Unassigned ..... 127  (37%)
   ```

**Type dropdown population:** The dropdown calls `ShapesService.get_types()` which returns `[{iri, label}]` for each `sh:NodeShape` with `sh:targetClass`. The dropdown displays `label` and stores `iri`.

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                     Step 2 of 6: Type Mapping      |
+------------------------------------------------------------------+
| Pattern: [Projects/** -> [Project v] ] [Apply]                   |
+----------------------------------------------+-------------------+
| File Path            | Folder   | FM Keys    | Type         |    |
|----------------------|----------|------------|--------------|    |
| [v] People/          |          |            | [Person   v] | <- folder header
|   Alice Chen.md      | People   | name,role  | [Person   v] |    |
|   Bob Smith.md       | People   | name       | [Person   v] |    |
|   ...28 files        |          |            |              |    |
|                      |          |            |              |    |
| [v] Projects/        |          |            | [Project  v] | <- folder header
|   Project Alpha.md   | Projects | status,pri | [Project  v] |    |
|   Migration Plan.md  | Projects | status     | [Project  v] |    |
|   ...31 files        |          |            |              |    |
|                      |          |            |              |    |
| [v] Concepts/        |          |            | [Concept  v] | <- folder header
|   Machine Learning.md| Concepts | aliases    | [Concept  v] |    |
|   ...19 files        |          |            |              |    |
|                      |          |            |              |    |
| [v] Daily Notes/     |          |            | [Note     v] |    |
|   2024-01-15.md      | Daily..  | date       | [Note     v] |    |
|   ...142 files       |          |            |              |    |
|                      |          |            |              |    |
| [v] (root)/          |          |            | [Note     v] |    |
|   README.md          | .        |            | [skip     v] |    |
|   TODO.md            | .        | tags       | [Note     v] |    |
|   ...83 files        |          |            |              |    |
+----------------------------------------------+-------------------+
| Type Distribution                                                |
| Note ........... 225   Project ......... 31                      |
| Person .......... 28   Concept ......... 19                      |
| Skipped .......... 1   Unassigned ...... 43                      |
+------------------------------------------------------------------+
|                                 [Back: Scan]  [Next: Properties] |
+------------------------------------------------------------------+
```

**Skip option:** Files can be marked "skip" to exclude them from import (e.g., README.md, template files).

---

### Step 3: Property Mapping (Per Type)

**Purpose:** For each type that has files assigned, map YAML frontmatter keys to SHACL property shapes. Mappings apply to ALL files of that type (type-level, not file-level).

**Data source for available properties:** `ShapesService.get_form_for_type(type_iri)` returns a `NodeShapeForm` with a `properties: list[PropertyShape]`. Each `PropertyShape` has:
- `path`: full predicate IRI (e.g., `http://purl.org/dc/terms/title`)
- `name`: human-readable label (e.g., "Title")
- `datatype`: XSD datatype if literal (e.g., `xsd:string`, `xsd:date`)
- `target_class`: if the property expects an object reference
- `min_count`: 0 or 1 (required vs optional)
- `in_values`: allowed values for dropdowns
- `description`: help text

**Layout:** Tabbed panel with one tab per assigned type. Each tab shows a two-column mapping table.

**Interaction flow:**

1. For each type tab (e.g., "Note (225 files)"), show:
   - Left column: unique frontmatter keys found across all files of this type, with occurrence count
   - Right column: auto-suggested SHACL property match (see fuzzy matching below)
   - Confidence indicator: high/medium/low based on match score
   - Action buttons: Accept, Change, Skip, Store as Tag

2. User reviews each suggestion:
   - **Accept** (default for high-confidence): keeps the suggested mapping
   - **Change**: opens a dropdown of all available properties for this type
   - **Skip**: frontmatter key is ignored during import
   - **Store as Tag**: value is appended to the object's tags property

3. Special handling for title properties:
   - The wizard auto-detects which frontmatter key is the title based on the type's title predicate (dcterms:title for Note/Project, foaf:name for Person, skos:prefLabel for Concept)
   - If no frontmatter key maps to the title, the filename (without .md) is used as the title

4. Preview panel: clicking any frontmatter key shows sample values from 3-5 files of this type, helping the user understand what the key contains

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                   Step 3 of 6: Property Mapping    |
+------------------------------------------------------------------+
| [Note (225)] [Person (28)] [Project (31)] [Concept (19)]         |
+------------------------------------------------------------------+
| Mapping properties for: Note (225 files)                         |
|                                                                  |
| Frontmatter Key | Occurs | Suggested Mapping     | Conf | Action|
|-----------------|--------|-----------------------|------|-------|
| title           | 180    | dcterms:title (Title) |  H   | [Acc] |
| date            |  89    | dcterms:created (Date)|  H   | [Acc] |
| tags            |  67    | bpkm:tags (Tags)      |  H   | [Acc] |
| status          |  31    | bpkm:noteType (Type)  |  M   | [Chg] |
| related         |  12    | skos:related (Related) |  M   | [Acc] |
| source          |   8    | -- no match --        |  --  | [Tag] |
| aliases         |  22    | skos:altLabel (Alias) |  H   | [Acc] |
| rating          |   5    | -- no match --        |  --  | [Skp] |
|                                                                  |
| +--- Sample Values for "status" (3 of 31 files) ---+            |
| |  Daily Notes/2024-01-15.md: "active"              |            |
| |  Projects/Alpha.md: "completed"                   |            |
| |  Meetings/standup.md: "recurring"                 |            |
| +---------------------------------------------------+            |
|                                                                  |
|                            [Back: Types]  [Next: Relationships]  |
+------------------------------------------------------------------+
```

**Key behavior:** When the user maps `status` to `bpkm:status` for type Project, every Project file with a `status` frontmatter key will have its value written to `bpkm:status`. This is type-level mapping, not file-level.

---

### Step 4: Relationship Mapping

**Purpose:** Configure how wiki-links (`[[target]]`) are converted to typed edges. Uses type-pair heuristics from Chapter 24's EDGE_PREDICATES table, with user overrides.

**Layout:** A mapping table showing type-pair to predicate assignments, plus a sample preview.

**Interaction flow:**

1. Show the auto-detected type-pair -> predicate table (derived from the Chapter 24 heuristic, extended for any types from installed Mental Models):

   ```
   Source Type  | Target Type | Predicate                | Override
   -------------|-------------|--------------------------|--------
   Project      | Person      | bpkm:hasParticipant      | [Change]
   Person       | Project     | bpkm:participatesIn      | [Change]
   Note         | Project     | bpkm:relatedProject      | [Change]
   Note         | Concept     | bpkm:isAbout             | [Change]
   Note         | Person      | skos:related             | [Change]
   Concept      | Concept     | skos:related             | [Change]
   *            | *           | skos:related (fallback)  | [Change]
   ```

2. User can change any predicate via dropdown (populated from all predicates across all installed shapes)

3. Default fallback predicate: `skos:related` -- used when no specific type-pair rule matches

4. Sample edge preview: show 5-10 detected edges with source title, target title, and the predicate that would be applied

5. Link resolution stats:
   - Total wiki-links found across all files
   - Links that resolve to a file in the import (will create edges)
   - Links that do not resolve (target file not in vault or skipped)
   - Links where target has no assigned type (uses fallback)

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                    Step 4 of 6: Relationships      |
+------------------------------------------------------------------+
| Edge Predicate Rules                                             |
|                                                                  |
| Source Type | Target Type | Predicate              | Action      |
|-------------|-------------|------------------------|-------------|
| Project     | Person      | bpkm:hasParticipant    | [Change v]  |
| Person      | Project     | bpkm:participatesIn    | [Change v]  |
| Note        | Project     | bpkm:relatedProject    | [Change v]  |
| Note        | Concept     | bpkm:isAbout           | [Change v]  |
| Note        | Person      | skos:related           | [Change v]  |
| Concept     | Concept     | skos:related           | [Change v]  |
| * (default) | *           | [skos:related      v]  |             |
|                                                                  |
| +--- Link Resolution Stats ---+                                 |
| | Total wiki-links:       512  |                                 |
| | Resolvable:             438  (86%)                             |
| | Unresolvable:            74  (14%) -- targets not in vault     |
| +------------------------------+                                 |
|                                                                  |
| +--- Sample Edges (5 of 438) ---------------------------+       |
| | Meeting Jan 15 --> Alice Chen    | bpkm:hasParticipant |       |
| | Project Alpha  --> Bob Smith     | bpkm:hasParticipant |       |
| | ML Research    --> Deep Learning | skos:related        |       |
| | Daily 2024-01  --> Project Alpha | bpkm:relatedProject |       |
| | Alice Chen     --> Project Alpha | bpkm:participatesIn |       |
| +-------------------------------------------------------|       |
|                                                                  |
|                               [Back: Properties]  [Next: Review] |
+------------------------------------------------------------------+
```

---

### Step 5: Preview and Confirm

**Purpose:** Show a complete summary of the import before execution. Run dry-run validation against SHACL shapes. Allow the user to go back and fix issues.

**Layout:** Summary dashboard with expandable sections.

**Content:**

1. **Object counts by type:** Table with type, count, and property mapping count
2. **Property mappings summary:** Collapsed per-type sections showing all active mappings
3. **Edge summary:** Total edges, predicate distribution
4. **Sample object previews:** 3-5 fully rendered objects showing how they will look after import (title, properties, body snippet, edges)
5. **Dry-run validation results:**
   - Duplicate title detection: warn if two files would create objects with the same title under the same type
   - Missing required properties: check each object against its type's SHACL shape `min_count` constraints
   - Invalid property values: check `sh:in` constraints (e.g., status must be one of active/completed/on-hold/cancelled)
   - Validation uses `PropertyShape.min_count` and `PropertyShape.in_values` from `ShapesService.get_form_for_type()`

6. **"Start Import" button** -- only enabled when no blocking validation errors exist (warnings are OK)

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                      Step 5 of 6: Preview         |
+------------------------------------------------------------------+
| Import Summary                                                   |
|                                                                  |
| Objects to create:                                               |
|   Note ........... 225    Project ......... 31                   |
|   Person .......... 28    Concept ......... 19                   |
|   Total: 303 objects                                             |
|                                                                  |
| Edges to create: 438                                             |
|   bpkm:hasParticipant ... 89    bpkm:isAbout ........... 67     |
|   bpkm:relatedProject ... 54    skos:related ........... 228    |
|                                                                  |
| +--- Validation Results ---+                                    |
| | [!] 3 warnings, 0 errors |                                    |
| | WARN: 2 duplicate titles found (Note: "TODO", "README")      |
| | WARN: 12 Notes missing "noteType" (optional, will be blank)  |
| | WARN: 3 Projects have status="in-progress" (not in sh:in)    |
| +---------------------------+                                    |
|                                                                  |
| +--- Sample Object Preview ---+                                 |
| | Type: Person                 |                                 |
| | Title: Alice Chen            |                                 |
| | Properties:                  |                                 |
| |   foaf:name = "Alice Chen"   |                                 |
| |   schema:jobTitle = "Eng"    |                                 |
| | Body: "Alice is a senior..." |                                 |
| | Edges: 3 incoming, 1 out    |                                 |
| +------------------------------+                                 |
|                                                                  |
|                          [Back: Relationships]  [Start Import]   |
+------------------------------------------------------------------+
```

---

### Step 6: Import Execution and Progress

**Purpose:** Execute the import via batched Command API calls. Show real-time progress and error reporting.

**Execution phases:**

1. **Creating objects** -- `object.create` commands batched 10-20 per request via `POST /api/commands`
2. **Setting body content** -- `body.set` commands for each file's Markdown body (frontmatter stripped)
3. **Creating edges** -- `edge.create` commands for resolved wiki-links

Each phase shows a progress bar and phase indicator.

**Progress communication:** Server-Sent Events (SSE) from a dedicated endpoint. The backend streams progress events as JSON lines:
```json
{"phase": "objects", "current": 45, "total": 303, "last_title": "Alice Chen"}
{"phase": "bodies",  "current": 12, "total": 280, "last_title": "Meeting Jan 15"}
{"phase": "edges",   "current": 200, "total": 438}
{"phase": "complete", "objects_created": 303, "edges_created": 438, "errors": 2}
```

**Error handling:** Individual command failures do not abort the import. Errors are collected and displayed in an error log panel. The user can review failed items and retry or skip them.

**Completion screen:** Shows import results with links to browse imported objects:
- "Browse all imported Notes (225)"
- "Browse all imported Persons (28)"
- "View import error log (2 failures)"

**ASCII wireframe:**

```
+------------------------------------------------------------------+
| Import Wizard                       Step 6 of 6: Importing      |
+------------------------------------------------------------------+
|                                                                  |
| Phase: Creating Objects                                          |
| [=========================>          ] 156 / 303  (51%)          |
|                                                                  |
| Last created: "Project Alpha" (Project)                          |
|                                                                  |
| +--- Phase Progress ---+                                        |
| | [x] Scan vault       |                                        |
| | [x] Create objects   | <- current                             |
| | [ ] Set body content |                                        |
| | [ ] Create edges     |                                        |
| +----------------------+                                        |
|                                                                  |
| +--- Error Log (1 error so far) ---+                            |
| | [!] object.create failed for "README.md":                     |
| |     "Slug 'readme' already exists"                            |
| +-----------------------------------+                            |
|                                                                  |
| ---- After completion: ----                                      |
|                                                                  |
| Import Complete!                                                 |
| Objects created: 302/303 (1 failed)                              |
| Bodies set: 280/302                                              |
| Edges created: 436/438 (2 targets not found)                    |
|                                                                  |
| [Browse Notes (225)]  [Browse Persons (28)]  [View Error Log]   |
| [Close Wizard]                                                   |
+------------------------------------------------------------------+
```

---

## 3. Data Model for Import Jobs

### Option A: SQLAlchemy Models (Recommended)

Persistent storage enables resumable imports and import history. Uses the existing SQLAlchemy session infrastructure.

```python
class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid4_hex)
    status: Mapped[str] = mapped_column(String, default="scanning")
    # Status values: scanning, mapping, previewing, importing,
    #                complete, failed, cancelled
    source_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=utcnow)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False
    )

    # Relationships
    file_mappings: Mapped[list["ImportFileMapping"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    property_mappings: Mapped[list["ImportPropertyMapping"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    edge_mappings: Mapped[list["ImportEdgeMapping"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class ImportFileMapping(Base):
    __tablename__ = "import_file_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("import_jobs.id"))
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    folder: Mapped[str] = mapped_column(String, default="")
    assigned_type: Mapped[str | None] = mapped_column(String, nullable=True)
    # None = unassigned, "skip" = excluded from import
    frontmatter_keys: Mapped[str] = mapped_column(Text, default="{}")
    # JSON dict of frontmatter key -> value for this file
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    # Resolved title (from frontmatter or filename)
    created_iri: Mapped[str | None] = mapped_column(String, nullable=True)
    # IRI of the created object (populated during import execution)

    job: Mapped["ImportJob"] = relationship(back_populates="file_mappings")


class ImportPropertyMapping(Base):
    __tablename__ = "import_property_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("import_jobs.id"))
    type_iri: Mapped[str] = mapped_column(String, nullable=False)
    frontmatter_key: Mapped[str] = mapped_column(String, nullable=False)
    target_predicate: Mapped[str | None] = mapped_column(String, nullable=True)
    mapping_mode: Mapped[str] = mapped_column(String, default="auto-suggested")
    # Modes: auto-suggested, user-set, skip, tag
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    job: Mapped["ImportJob"] = relationship(back_populates="property_mappings")

    # Unique constraint: one mapping per (job, type, frontmatter_key)
    __table_args__ = (
        UniqueConstraint("job_id", "type_iri", "frontmatter_key"),
    )


class ImportEdgeMapping(Base):
    __tablename__ = "import_edge_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("import_jobs.id"))
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    predicate: Mapped[str] = mapped_column(String, nullable=False)

    job: Mapped["ImportJob"] = relationship(back_populates="edge_mappings")

    __table_args__ = (
        UniqueConstraint("job_id", "source_type", "target_type"),
    )
```

### Option B: In-Memory Session State

Store wizard state in the server-side session (e.g., Starlette's SessionMiddleware with a signed cookie pointing to server-side storage).

**Pros:** No database migration needed, simpler implementation, automatic cleanup on session expiry.
**Cons:** Lost if session expires or server restarts, no import history, no resume-after-crash capability.

### Recommendation

Use **Option A (SQLAlchemy models)** for the following reasons:
- Import jobs for large vaults can take minutes; session timeout during import is a real risk
- Import history enables undo/rollback in a future enhancement
- The database migration is straightforward (4 new tables, no changes to existing tables)
- The existing Alembic migration pipeline handles this cleanly

---

## 4. Backend Integration Points

### Existing Services Used by Each Step

| Wizard Step | Backend Service | Method / Endpoint | Purpose |
|---|---|---|---|
| Step 1: Scan | *New* ImportService | `scan_vault(path)` | Walk directory, extract metadata |
| Step 2: Type Mapping | ShapesService | `get_types()` | Populate type dropdown with `[{iri, label}]` |
| Step 2: Type Mapping | ShapesService | `get_node_shapes()` | Get full `NodeShapeForm` list for type metadata |
| Step 3: Property Mapping | ShapesService | `get_form_for_type(type_iri)` | Get `PropertyShape` list for mapping targets |
| Step 3: Property Mapping | *New* FuzzyMatcher | `suggest_mappings(keys, shapes)` | Auto-suggest frontmatter-to-property matches |
| Step 4: Relationships | ShapesService | `get_node_shapes()` | Enumerate all property paths across all types |
| Step 5: Preview | ShapesService | `get_form_for_type(type_iri)` | Validate against `PropertyShape.min_count`, `in_values` |
| Step 5: Preview | SearchService | `search(title)` | Detect duplicate titles in existing data |
| Step 6: Import | Command API | `POST /api/commands` | Batch `object.create`, `body.set`, `edge.create` |

### New Endpoints Required

```
POST   /api/import/scan
  Body: { "path": "/home/user/obsidian-vault" }
  Response: { "job_id": "abc123", "file_count": 347, "summary": {...} }
  Creates an ImportJob in "scanning" status, returns vault audit summary.

GET    /api/import/{job_id}
  Response: Full ImportJob with file_mappings, property_mappings, edge_mappings.
  Used to hydrate the wizard UI on page load or resume.

PATCH  /api/import/{job_id}/files
  Body: { "updates": [{ "file_path": "People/Alice.md", "assigned_type": "Person" }] }
  Bulk-update file type assignments (Step 2).

PATCH  /api/import/{job_id}/properties
  Body: { "updates": [{ "type_iri": "...:Note", "key": "status", "target": "bpkm:status", "mode": "user-set" }] }
  Update property mappings (Step 3).

PATCH  /api/import/{job_id}/edges
  Body: { "updates": [{ "source_type": "Note", "target_type": "Concept", "predicate": "bpkm:isAbout" }] }
  Update edge predicate rules (Step 4).

GET    /api/import/{job_id}/preview
  Response: { "objects": [...], "edges": [...], "validation": {...} }
  Dry-run preview with validation results (Step 5).

POST   /api/import/{job_id}/execute
  Response: SSE stream of progress events
  Kicks off the actual import. Streams progress via Server-Sent Events.

GET    /api/import/{job_id}/status
  Response: { "status": "importing", "phase": "objects", "current": 45, "total": 303 }
  Poll-based fallback if SSE is not available.

DELETE /api/import/{job_id}
  Cancels and deletes an import job (cleanup).
```

### Command API Usage During Import (Step 6)

The import execution phase uses the existing `POST /api/commands` endpoint with batch payloads. Each batch contains 10-20 commands for atomicity and performance.

**Phase 1 -- Object creation:**
```json
[
  {
    "command": "object.create",
    "params": {
      "type": "Note",
      "slug": "meeting-jan-15",
      "properties": {
        "dcterms:title": "Meeting Jan 15",
        "bpkm:noteType": "meeting-note",
        "bpkm:tags": "meeting, standup"
      }
    }
  },
  ...
]
```

**Phase 2 -- Body content:**
```json
[
  {
    "command": "body.set",
    "params": {
      "iri": "https://example.org/data/Note/meeting-jan-15",
      "body": "## Attendees\n- Alice Chen\n- Bob Smith\n\n## Discussion\n..."
    }
  },
  ...
]
```

**Phase 3 -- Edge creation:**
```json
[
  {
    "command": "edge.create",
    "params": {
      "source": "https://example.org/data/Note/meeting-jan-15",
      "target": "https://example.org/data/Person/alice-chen",
      "predicate": "urn:sempkm:model:basic-pkm:hasParticipant"
    }
  },
  ...
]
```

### Markdown Body Extraction

During import, the backend strips YAML frontmatter from each .md file before sending the body content:

```python
import re

def extract_body(markdown_text: str) -> str:
    """Strip YAML frontmatter and return the body content."""
    return re.sub(
        r"^---\n.*?\n---\n?", "", markdown_text,
        count=1, flags=re.DOTALL
    ).strip()
```

Wiki-links (`[[target]]`) in the body are preserved as-is. A future enhancement could convert them to SemPKM-style object links, but for the initial implementation they remain as plain text.

---

## 5. Fuzzy Matching Algorithm for Property Auto-Suggestion

### Problem Statement

Given a YAML frontmatter key (e.g., `"related"`, `"jobTitle"`, `"date_created"`) and a list of `PropertyShape` objects, suggest the best-matching SHACL property.

The challenge: frontmatter keys use informal names (`"related"`, `"status"`, `"name"`), while SHACL properties use full IRIs (`http://www.w3.org/2004/02/skos/core#related`, `urn:sempkm:model:basic-pkm:status`, `http://xmlns.com/foaf/0.1/name`).

### Recommended Approach: Multi-Signal Token Matching

Use a combination of three signals, weighted and combined:

**Signal 1: Exact local name match (weight: 1.0)**
Extract the local name from the `PropertyShape.path` IRI (the part after `#` or the last `/`) and compare case-insensitively to the frontmatter key.

```python
def local_name(iri: str) -> str:
    """Extract local name from IRI (after # or last /)."""
    if "#" in iri:
        return iri.rsplit("#", 1)[-1]
    return iri.rsplit("/", 1)[-1]

# "http://www.w3.org/2004/02/skos/core#related" -> "related"
# "http://purl.org/dc/terms/title" -> "title"
# "urn:sempkm:model:basic-pkm:status" -> "status"
```

If `local_name(property.path).lower() == frontmatter_key.lower()`, confidence = 1.0 (exact match).

**Signal 2: PropertyShape.name similarity (weight: 0.8)**
Compare the frontmatter key to `PropertyShape.name` (the human-readable label like "Title", "Status", "Job Title") using Jaro-Winkler similarity.

Jaro-Winkler is preferred over Levenshtein for short strings because:
- It gives higher scores to strings that match from the beginning (prefix bonus)
- It handles transpositions well
- It is more discriminating for short tokens (5-15 chars) than raw edit distance

```python
from jellyfish import jaro_winkler_similarity

score = jaro_winkler_similarity(
    frontmatter_key.lower(),
    property.name.lower()
)
```

**Signal 3: Token overlap (weight: 0.6)**
Split both the frontmatter key and the property name/local-name on camelCase boundaries, underscores, and hyphens. Compute Jaccard similarity on the resulting token sets.

```python
import re

def tokenize(s: str) -> set[str]:
    """Split on camelCase, underscores, hyphens."""
    # Split camelCase: "jobTitle" -> ["job", "Title"]
    tokens = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    # Split on non-alphanumeric
    parts = re.split(r'[^a-zA-Z0-9]+', tokens)
    return {t.lower() for t in parts if t}

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

# "date_created" tokens: {"date", "created"}
# "dcterms:created" local name "created" tokens: {"created"}
# Jaccard: 1/2 = 0.5
```

**Combined score:**

```python
def match_score(
    frontmatter_key: str,
    prop: PropertyShape
) -> float:
    ln = local_name(prop.path).lower()
    fk = frontmatter_key.lower()

    # Signal 1: exact local name match
    if ln == fk:
        return 1.0

    # Signal 2: Jaro-Winkler on PropertyShape.name
    name_score = jaro_winkler_similarity(fk, prop.name.lower())

    # Signal 3: token overlap (best of local name and property name)
    fk_tokens = tokenize(fk)
    ln_tokens = tokenize(ln)
    name_tokens = tokenize(prop.name)
    token_score = max(jaccard(fk_tokens, ln_tokens), jaccard(fk_tokens, name_tokens))

    return 0.8 * name_score + 0.6 * token_score
```

**Confidence levels:**
- Score >= 0.9: High confidence (auto-accept candidate)
- Score >= 0.6: Medium confidence (suggest but require confirmation)
- Score < 0.6: Low confidence (show as "no match", offer manual selection)

### Dependency

The `jellyfish` Python library provides Jaro-Winkler (pure C implementation, fast). Add to `pyproject.toml`:

```toml
dependencies = [
    ...,
    "jellyfish>=1.0",
]
```

Alternative: implement Jaro-Winkler from scratch (the algorithm is ~30 lines) to avoid the dependency.

### Example Matches

| Frontmatter Key | Best Match Property | Score | Confidence |
|---|---|---|---|
| `title` | dcterms:title (name: "Title") | 1.0 | High |
| `name` | foaf:name (name: "Name") | 1.0 | High |
| `status` | bpkm:status (name: "Status") | 1.0 | High |
| `related` | skos:related (name: "Related") | 1.0 | High |
| `date_created` | dcterms:created (name: "Created") | 0.78 | Medium |
| `jobTitle` | schema:jobTitle (name: "Job Title") | 0.95 | High |
| `priority` | bpkm:priority (name: "Priority") | 1.0 | High |
| `source_url` | (no match) | 0.3 | Low |
| `rating` | (no match) | 0.2 | Low |

---

## 6. UI Technology Notes

### htmx Compatibility

The wizard is fully compatible with SemPKM's htmx-driven architecture. Each wizard step is a server-rendered HTML partial loaded via `hx-get` or `hx-post`.

**Step navigation:**

```html
<!-- Stepper bar -->
<div class="wizard-steps">
  <button hx-get="/import/{{job_id}}/step/1" hx-target="#wizard-content"
          class="step active">1. Scan</button>
  <button hx-get="/import/{{job_id}}/step/2" hx-target="#wizard-content"
          class="step">2. Types</button>
  ...
</div>

<div id="wizard-content">
  <!-- Step content loaded here via htmx -->
</div>
```

**Type assignment (Step 2):**

```html
<!-- Individual file type dropdown -->
<select hx-post="/import/{{job_id}}/files/{{file_id}}/type"
        hx-target="#type-distribution"
        hx-swap="outerHTML"
        name="type">
  {% for t in types %}
  <option value="{{t.iri}}" {% if t.iri == file.assigned_type %}selected{% endif %}>
    {{t.label}}
  </option>
  {% endfor %}
  <option value="skip">Skip</option>
</select>
```

**Glob pattern application (Step 2):**

```html
<form hx-post="/import/{{job_id}}/apply-glob"
      hx-target="#file-table"
      hx-swap="outerHTML">
  <input name="pattern" placeholder="Projects/**" />
  <select name="type">
    {% for t in types %}
    <option value="{{t.iri}}">{{t.label}}</option>
    {% endfor %}
  </select>
  <button type="submit">Apply</button>
</form>
```

**Property mapping (Step 3):**

```html
<!-- Property mapping row -->
<tr id="mapping-{{key}}">
  <td>{{key}}</td>
  <td>{{occurrence_count}}</td>
  <td>
    <select hx-post="/import/{{job_id}}/properties/{{type_iri}}/{{key}}"
            hx-target="#mapping-{{key}}"
            hx-swap="outerHTML"
            name="target">
      <option value="">-- no match --</option>
      {% for prop in available_properties %}
      <option value="{{prop.path}}" {% if prop.path == suggested %}selected{% endif %}>
        {{prop.name}} ({{prop.path | local_name}})
      </option>
      {% endfor %}
    </select>
  </td>
  <td>{{confidence_badge}}</td>
  <td>
    <button hx-post="..." hx-vals='{"mode": "skip"}'>Skip</button>
    <button hx-post="..." hx-vals='{"mode": "tag"}'>Tag</button>
  </td>
</tr>
```

### Server-Sent Events for Import Progress (Step 6)

htmx has built-in SSE support via the `sse` extension:

```html
<div hx-ext="sse"
     sse-connect="/api/import/{{job_id}}/execute"
     sse-swap="progress">
  <div id="progress-bar">Waiting to start...</div>
</div>
```

The backend SSE endpoint streams events:

```python
from starlette.responses import StreamingResponse

async def import_sse(job_id: str):
    async def event_stream():
        async for progress in execute_import(job_id):
            yield f"event: progress\ndata: {json.dumps(progress)}\n\n"
        yield f"event: complete\ndata: {json.dumps(final_summary)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
```

### State Management

All wizard state is stored server-side in the ImportJob SQLAlchemy model. The browser holds only the `job_id` (in the URL path or a hidden form field). This means:

- No complex JavaScript state management
- Browser refresh or back-button works correctly (htmx reloads from server)
- Multiple browser tabs for the same job show consistent state
- Session expiry does not lose import progress (data is in the database)

### CSS and Layout

The wizard UI reuses existing SemPKM CSS patterns:
- Card grid for summary stats (Step 1)
- Data table with sortable columns (Steps 2, 3, 4)
- Badge/pill components for type labels and confidence indicators
- Progress bar component (Step 6)
- The wizard panel replaces the main content area (not a modal overlay), allowing full-width tables

---

## 7. Detailed Screen Descriptions

### Step 1 Screen: Vault Scan

**Header:** "Import from Obsidian" with step indicator (1 of 6)
**Main content:**
- Path input field with optional browse button (if server supports file dialogs)
- "Scan" button triggers `POST /api/import/scan`
- After scan completes, displays a summary card grid:
  - Top row: 4 metric cards (Total Files, With Frontmatter, Unique Tags, Wiki-links)
  - Bottom section: two side-by-side panels
    - Left: Folder distribution table (folder name, file count, percentage bar)
    - Right: Top frontmatter keys list (key name, occurrence count)
- Footer: Cancel and Next buttons

### Step 2 Screen: Type Mapping

**Header:** Step indicator (2 of 6) + glob pattern input bar
**Main content:** Full-width data table
- Columns: Checkbox | File Path | Folder | Frontmatter Keys (truncated) | Assigned Type (dropdown)
- Rows grouped by folder with collapsible folder headers
- Folder header row: bold text, type dropdown applies to all files in folder
- Selected rows can be bulk-assigned via toolbar action
**Sidebar:** Type distribution card with live-updating counts and colored bars
**Footer:** Back and Next buttons

### Step 3 Screen: Property Mapping

**Header:** Step indicator (3 of 6) + type tabs
**Tab bar:** One tab per type with file count badge: "Note (225)" | "Person (28)" | "Project (31)" | "Concept (19)"
**Main content:** Mapping table for the active type tab
- Columns: Frontmatter Key | Occurs In | Suggested Mapping (dropdown) | Confidence (badge) | Action (Accept/Change/Skip/Tag)
- Below the table: collapsible "Sample Values" panel showing 3 example values for the selected key
**Footer:** Back and Next buttons

### Step 4 Screen: Relationship Mapping

**Header:** Step indicator (4 of 6)
**Main content:** Two sections
- Top: Edge predicate rules table (Source Type | Target Type | Predicate dropdown | Override button)
- Middle: Link resolution stats card (total links, resolvable count, unresolvable count)
- Bottom: Sample edges table showing 5-10 example edges with source, target, and predicate
**Footer:** Back and Next buttons

### Step 5 Screen: Preview and Confirm

**Header:** Step indicator (5 of 6)
**Main content:** Dashboard layout
- Top: Object counts by type (horizontal bar or card row)
- Middle-left: Collapsible property mapping summary per type
- Middle-right: Edge predicate distribution
- Bottom: Validation results panel (warnings in yellow, errors in red)
- Below: 3-5 sample object cards showing full rendered preview
**Footer:** Back and "Start Import" button (disabled if blocking errors exist)

### Step 6 Screen: Import Progress

**Header:** Step indicator (6 of 6)
**Main content:**
- Phase checklist with progress bar for current phase
- Current item indicator ("Last created: ...")
- Error log panel (collapsible, shows failed commands)
- After completion: summary card with browse links per type
**Footer:** "Close Wizard" button (after completion)

---

## 8. Open Questions and Future Enhancements

### LLM-Assisted Classification (Enhancement)

The wizard could offer an optional "Auto-classify with AI" button in Step 2 that sends unassigned files to an LLM for type classification (reusing the prompt from Chapter 24). This would require:
- LLM API configuration in SemPKM settings (API URL, key, model)
- A background job that classifies files in batches
- Results appearing as suggested types in the file table with confidence indicators
- User still reviews and confirms all suggestions

This is an enhancement, not a requirement for the initial wizard. The folder-based and manual assignment flows handle most vaults well without an LLM.

### Incremental / Delta Imports

After the initial import, users may want to re-import only new or modified files. This requires:
- Tracking which vault files have been imported (store in ImportFileMapping.created_iri)
- Comparing file modification dates against the last import timestamp
- Detecting renamed or moved files (by content hash or title matching)
- UI for reviewing the delta before importing

### Undo / Rollback

The import wizard creates objects via the Command API, which records all mutations in event graphs. A rollback feature could:
- Store the event IRIs generated during import in the ImportJob record
- Provide a "Rollback Import" button that deletes all objects created by the import
- Implementation: query the event graph for all objects created by the import's event IRIs, then issue `object.delete` commands

This depends on a `object.delete` command being available in the Command API (currently not implemented).

### Non-Obsidian Markdown Sources

The wizard's vault scanning logic assumes Obsidian conventions (YAML frontmatter, `[[wiki-links]]`, `#tags`). Other Markdown-based tools use different conventions:
- **Logseq:** block-based structure, `((block-refs))`, `[[page-links]]`
- **Dendrite:** hierarchical filenames (`root.child.grandchild.md`), no wiki-links
- **Foam/Zettelkasten:** UID-based filenames, `[[wiki-links]]` similar to Obsidian
- **Bear:** nested tags (`#tag/subtag`), no frontmatter

A future enhancement could add pluggable "source adapters" that normalize different Markdown tool conventions into the wizard's internal format.

### Batch Size Tuning

The current batch size (10-20 commands per `POST /api/commands`) is conservative. For large vaults (>1000 files), this could be tuned:
- Measure transaction latency vs batch size on the target triplestore
- Consider async command processing with a queue for very large imports
- Add a "batch size" setting in the wizard's advanced options

### Conflict Detection

For repeat imports or imports into a populated SemPKM instance:
- Use `SearchService.search(title)` to detect objects with matching titles already in the triplestore
- Offer merge/skip/replace options per conflict
- Show a conflict resolution step between Preview and Import

---

## 9. Implementation Priority

### Phase 1: Minimum Viable Wizard
- Steps 1, 2, 5, 6 (Scan, Type Mapping, Preview, Import)
- Folder-based type assignment only (no glob patterns)
- Title derived from filename, no property mapping
- All wiki-links mapped to `skos:related`
- No LLM integration

### Phase 2: Property and Relationship Mapping
- Steps 3, 4 (Property Mapping, Relationship Mapping)
- Fuzzy matching for property suggestions
- Type-pair heuristic for edge predicates
- Sample previews and validation

### Phase 3: Advanced Features
- Glob pattern type assignment
- LLM-assisted classification option
- Incremental imports
- Conflict detection
- Undo/rollback

This phased approach delivers a usable wizard quickly (Phase 1 covers the most common import scenario: folder-based classification into Basic PKM) while leaving room for sophisticated features in later iterations.
