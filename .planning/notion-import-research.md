# Notion Import Flow — Research & Design

**Date:** 2026-03-12  
**Context:** Design a user-friendly interactive flow to import a Notion workspace (or portion of it) into SemPKM, mirroring the existing Obsidian import wizard pattern. The PPV mental model was originally researched from Notion via a Notion MCP — that same MCP could be the live-connection path.

---

## 1. How Notion Data Maps to SemPKM

### Notion's Content Types

| Notion Concept | Structure | SemPKM Equivalent | Notes |
|---------------|-----------|-------------------|-------|
| **Database** | Container with schema (properties as columns), rows are pages | **Type (class)** | Each database = one RDF type. Column schema = SHACL shape properties |
| **Database Row** | A page with typed properties + optional body content | **Object (instance)** | Property values map to RDF triples, body to markdown content |
| **Standalone Page** | Free-form blocks (text, headings, toggles, callouts, etc.) | **Note object** with markdown body | No structured properties beyond title — content-first |
| **Nested Sub-page** | Page inside another page | **Object with parent edge** | `dcterms:isPartOf` or similar relationship |
| **Relation property** | Cross-database link (DB A row → DB B row) | **Edge (RDF triple)** | The most valuable signal — these ARE the knowledge graph |
| **Rollup property** | Computed aggregation from relations | **Skip / derived** | These are views, not data — can be recomputed via SPARQL |
| **Formula property** | Computed value | **Skip / derived** | Same — computed, not stored |
| **Select / Multi-select** | Enum / tag values | **Category / schema:keywords** | Multi-select → multiple triples |
| **Dashboard page** | A page whose body is all database views, filters, embeds | **Skip or import as Note** | Layout info, not knowledge — offer user the choice |

### The Three Content Tiers

Users need to understand that their Notion workspace contains three fundamentally different kinds of content:

1. **Structured Data** (databases + rows) — the highest-value import target. Schema maps to types, rows map to objects, relations map to edges. This is where the knowledge graph lives.

2. **Rich Content** (standalone pages, database row bodies) — free-form writing that we convert to markdown. Valuable as note bodies, but no structured properties.

3. **Layout/Views** (dashboards, linked views, galleries, boards, calendars) — these are *presentations* of data, not data itself. SemPKM reconstructs views from the data model, so importing the layout is unnecessary.

---

## 2. Import Source Options

### Option A: Notion ZIP Export (Markdown + CSV)

**How it works:** User goes to Notion Settings → Export → "Markdown & CSV" → downloads a ZIP.

**ZIP structure:**
```
Workspace Name/
├── Standalone Page abc123.md
├── Database Name def456/
│   ├── Database Name def456.csv          ← schema + all row properties
│   ├── Row Title 111aaa.md               ← body content of row
│   ├── Row Title 222bbb.md
│   └── Row Title 222bbb/                 ← attachments folder
│       └── image.png
```

**Pros:**
- No API key needed — zero auth friction
- Mirrors the Obsidian flow (user uploads a ZIP)
- All data is local — no rate limits, no network issues
- CSV has all property values in a parseable format
- Works for any Notion plan (free, plus, business)

**Cons:**
- Notion appends a 32-char hex ID to every filename/folder — need to strip these
- Database properties are ONLY in the CSV, NOT in the .md frontmatter
- Relations in CSV are stored as page titles (strings), not IDs — fragile for resolution
- No explicit schema metadata — must infer property types from CSV column values
- Callouts, toggles, synced blocks get lossy markdown conversion
- Rollup/Formula columns appear in CSV as computed values (no semantic meaning)
- User must manually export (can't automate from our side)

### Option B: Notion API (Live Connection)

**How it works:** User creates a Notion Integration, shares specific pages/databases with it, provides the API token.

**API endpoints (2025-09-03+ version):**
- `POST /v1/search` → find all databases and top-level pages
- `GET /v1/databases/{id}` → get database schema (property definitions + types)
- `POST /v1/data_sources/{id}/query` → paginated row retrieval
- `GET /v1/pages/{page_id}/markdown` → page body as Enhanced Markdown (new in 2025!)
- `GET /v1/blocks/{page_id}/children` → recursive block tree (fallback if markdown endpoint lacks detail)

**Pros:**
- **Rich schema metadata** — property types (select options, relation targets, number formats) are explicit
- **Relations preserve IDs** — cross-database links can be resolved precisely
- User can scope exactly which databases/pages to share (fine-grained)
- Incremental sync possible (webhooks, last_edited_time filtering)
- The 2025 Markdown Content API makes body extraction much simpler

**Cons:**
- Requires user to create an Integration and share pages — more setup friction
- Rate limited to ~3 req/s — large workspaces need queuing/backoff
- 100-item pagination — many requests for big databases
- Token management (secure storage, expiry)
- Long pages (>20K blocks) truncate — need fallback fetching

### Option C: Notion MCP (via MCP Server)

**How it works:** A Notion MCP server (like the one used for PPV research) runs locally and exposes Notion's API as MCP tools.

**Pros:**
- Already proven — the PPV ontology was researched this way
- MCP protocol handles connection lifecycle
- Could be used as the *backend* for Option B without writing raw HTTP client code

**Cons:**
- Requires MCP infrastructure on the user's machine or server
- Not currently connected in the SemPKM stack
- Adds a dependency layer between SemPKM and Notion

### Recommendation: **ZIP Export first (Option A), API second (Option B)**

Start with ZIP because:
1. Zero auth friction — mirrors the proven Obsidian UX
2. Covers the 80% case (structured databases + page content)
3. The scanner/executor architecture already exists — we're adapting, not building from scratch
4. API can be added later as an "advanced" / "live sync" feature

The Notion MCP (Option C) is excellent for *development and research* (exploring workspace structure, testing mappings) but isn't the right UX for end users.

---

## 3. Wizard Flow Design

### Existing Obsidian Flow (6 steps)
```
Upload ZIP → Scan → Type Mapping → Property Mapping → Preview → Import
```

### Proposed Notion Flow (7 steps)

```
Upload ZIP → Parse → Classify → Type Mapping → Property Mapping → Relation Mapping → Preview → Import
```

The key additions vs Obsidian:
- **Parse** replaces Scan — parses CSVs (not frontmatter) and .md files
- **Classify** — new step where user classifies each database/page group as "Structured Data", "Content Page", or "Skip"
- **Relation Mapping** — new step specific to Notion's cross-database Relations

#### Step 1: Upload
Same UX as Obsidian — drag-and-drop ZIP upload zone.
- Accept `.zip` files
- Extract and validate structure (look for `.csv` files as database indicator)
- Detect workspace name from root folder

#### Step 2: Parse & Inventory
Automatically scan the extracted ZIP:

**What the scanner detects:**
- **Databases:** Identified by `.csv` files. Parse CSV headers for property schema. Count rows.
- **Standalone pages:** `.md` files NOT inside a database folder (no sibling `.csv`)
- **Database row pages:** `.md` files inside a database folder (body content for rows)
- **Attachments:** Images, PDFs, etc. in subfolders
- **Relations:** CSV columns whose values look like page titles from other databases (heuristic cross-referencing)

**Scanner output (shown to user):**
```
┌──────────────────────────────────────────────┐
│  📊 3 Databases    📝 12 Standalone Pages    │
│  📋 247 Database Rows    📎 34 Attachments   │
│  🔗 5 Cross-DB Relations detected            │
└──────────────────────────────────────────────┘

Databases:
  Projects (42 rows, 8 properties) .............. ✔ Structured
  Action Items (156 rows, 6 properties) ......... ✔ Structured  
  Meeting Notes (49 rows, 4 properties) ......... ✔ Structured

Standalone Pages:
  Home Dashboard ................................ 📊 Dashboard
  Weekly Review Template ........................ 📝 Content
  Getting Started Guide ......................... 📝 Content
  ...
```

#### Step 3: Classify Content
User reviews each detected group and classifies it:

| Classification | Meaning | Import Behavior |
|---------------|---------|----------------|
| **📊 Structured Data** (default for databases) | This is a real data type with instances | → continues to Type Mapping |
| **📝 Content Page** | Free-form writing, import as a Note | → creates a Note object with markdown body |
| **📊 Dashboard / View** | Layout page referencing other databases | → **metadata preserved** as DashboardSpec object (title, referenced DBs, view hints, raw content) for user reference and future AI copilot reconstruction |
| **🔖 Bookmark Collection** | Page of web links / references | → creates Note with extracted URLs as properties |
| **⏭️ Skip** | Template, empty, or irrelevant | → not imported at all |

For databases, classification is defaulted to "Structured Data." For standalone pages, we apply heuristics:
- Pages with mostly database view embeds → suggest "Dashboard / View"
- Pages with substantial text content → suggest "Content Page"
- Pages that are mostly links/bookmarks → suggest "Bookmark Collection"
- Template pages (detected by "Template" in name or near-empty content) → suggest "Skip"
- Wiki pages → suggest "Content Page" (preserve verification status as property)

**Dashboard preservation note:** When a user classifies a page as "Dashboard / View", we don't silently discard it. Instead, we record a `DashboardSpec` object that captures the page title, which databases it referenced, any view type hints, and the raw markdown content. This gives the user a reference for rebuilding the view in SemPKM, and provides structured context for a future AI copilot to auto-generate equivalent views.

#### Step 4: Type Mapping
Same UX as Obsidian, but data source is different:

For each database classified as "Structured Data":
- Show the database name and sample rows
- Show available SemPKM types (from installed mental models)
- User maps: `Notion "Projects" database → ppv:Project`
- **Auto-suggest:** Match database name against installed type labels (fuzzy match)
- Option to create a new type (using basic-pkm:Note as fallback)

#### Step 5: Property Mapping  
Same UX as Obsidian, but richer because we have CSV column schemas:

For each mapped database:
- Show CSV column names with detected types and sample values
- Show available SHACL properties for the target SemPKM type
- User maps: `Notion "Status" column → ppv:status`
- **Auto-suggest:** Match column names against property labels
- **Smart type detection from CSV:**
  - `Select` columns (limited unique values) → suggest enum/category properties
  - `Date` columns (ISO date patterns) → suggest date properties
  - `Checkbox` columns (true/false) → suggest boolean properties
  - `URL` columns → suggest URL properties
  - `Relation` columns → handled in next step (skip here)
  - `Rollup` / `Formula` columns → suggest "Skip (computed)"

#### Step 6: Relation Mapping (NEW — Notion-specific)
This step is unique to Notion because Notion Relations are first-class:

For each Relation column detected across mapped databases:
- Show: `Projects."Related Goals" → Goals database`
- User maps the predicate: `→ ppv:alignsWithGoal`
- Show available object/annotation properties from installed models
- **Auto-suggest:** If both databases are mapped to known types, look for properties whose domain/range match

This is where the knowledge graph emerges — Relations become RDF edges.

#### Step 7: Preview
Same as Obsidian — show sample transformed objects with their properties and edges.

Additional Notion-specific preview elements:
- Show sample relation edges: `"Q1 Product Launch" → ppv:alignsWithGoal → "Grow Revenue"`
- Show content pages with markdown body preview
- Highlight any relation targets that couldn't be resolved

#### Step 8: Import (Execute)
Two-pass execution (mirrors Obsidian pattern):

**Pass 1: Create Objects**
- For each database row → create RDF object with mapped properties
- For each content page → create Note object with markdown body
- Track `notionPageId` as `sempkm:importSource` for deduplication

**Pass 2: Create Edges**
- For each Relation column value → resolve target object by title match → create RDF edge
- Report unresolved relations (target not imported or ambiguous title match)

SSE streaming progress throughout, same as Obsidian.

---

## 4. Notion-Specific Scanner Design

### NotionZIPScanner — Key Differences from VaultScanner

| Aspect | Obsidian VaultScanner | Notion ZIP Scanner |
|--------|----------------------|-------------------|
| **Type detection** | Heuristic (frontmatter, folders, tags) | Explicit (each CSV = one database = one type) |
| **Schema source** | Inferred from frontmatter key frequency | Explicit from CSV headers + value analysis |
| **Property types** | Unknown (all strings) | Inferred from CSV values (dates, booleans, URLs, enums) |
| **Relations** | Wiki-links `[[target]]` in body text | Relation columns in CSV (page title strings) |
| **Body content** | The entire .md file after frontmatter | Separate .md file per row, in database subfolder |
| **File naming** | User-chosen names | Names with 32-char hex ID appended |
| **Root detection** | Look for `.obsidian/` folder | Look for `.csv` files at various nesting levels |

### CSV Parsing Strategy

```python
# Notion CSV columns have specific patterns:
# - Regular text: arbitrary strings  
# - Select: limited set of unique values (< 20 unique in column)
# - Multi-select: comma-separated within cell
# - Date: ISO 8601 patterns
# - Checkbox: "Yes"/"No" or "true"/"false"
# - Relation: values that match titles in other database CSVs
# - URL: starts with http:// or https://
# - Number: parseable as float
# - Rollup: often numeric or list-like (see detection below)
# - Formula: could be anything (usually computed, see detection below)
```

**Rollup/Formula detection from CSV (heuristic):**

Rollups and formulas lose their "type" in CSV export — they just become value columns. Detection strategy:

1. **Column name patterns:** Names like "Total X", "Count of X", "% Complete", "Sum of X" strongly suggest rollups. Names with operators or conditional language suggest formulas.
2. **Value uniformity:** Rollup columns often have very uniform value shapes (all integers, all percentages, all "0" or empty). Formulas producing conditional text have a small set of unique outputs (e.g., "✅", "⏳", "❌").
3. **Cross-reference with Relations:** If a column's name contains the name of another database (e.g., "Action Items Count" when there's an "Action Items" DB), it's very likely a rollup over that relation.
4. **Ask the user:** In the Property Mapping step, flag suspected rollup/formula columns with a "This looks computed — skip data, preserve as dashboard hint?" option.

When the API import path is available later, this becomes trivial — the Notion API explicitly labels `rollup` and `formula` property types and provides the full configuration (source relation, aggregation function, formula expression).

### Filename ID Stripping

Notion appends ` abc123def456...` (space + 32 hex chars) to every filename and folder:
```
"Meeting Notes 5f2e8a3b1c4d6e7f8a9b0c1d2e3f4a5b.md"  →  "Meeting Notes"
"Projects 1a2b3c4d/Projects 1a2b3c4d.csv"              →  "Projects"
```

Regex: `r'\s+[0-9a-f]{32}$'` applied to stem before extension.

### Cross-Database Relation Detection

1. Parse all CSVs first, collecting all row titles per database
2. For each CSV column, check if its values are a subset of another database's row titles
3. If >80% of non-empty values in column X match titles in Database Y → it's a Relation to Y
4. This heuristic works because Notion exports Relations as plain title strings

---

## 5. Data Models

### NotionScanResult (extends/parallels VaultScanResult)

```python
@dataclass
class NotionDatabaseInfo:
    """A detected Notion database from the ZIP export."""
    name: str                           # cleaned name (ID stripped)
    csv_path: str                       # relative path to CSV
    row_count: int
    columns: list[NotionColumnInfo]     
    sample_rows: list[dict]             # up to 5 sample rows
    body_folder: str | None             # path to folder with row .md files
    row_files_count: int                # how many .md body files exist

@dataclass  
class NotionColumnInfo:
    """A column (property) detected in a Notion database CSV."""
    name: str
    inferred_type: str                  # "text", "select", "multi_select", "date", 
                                        # "checkbox", "url", "number", "relation", 
                                        # "rollup", "formula", "unknown"
    unique_values: int
    sample_values: list[str]            # up to 5 samples
    empty_count: int
    relation_target_db: str | None      # if type=="relation", which DB it points to

@dataclass
class NotionStandalonePage:
    """A standalone page (not a database row)."""
    title: str
    path: str
    has_content: bool
    word_count: int
    suggested_classification: str       # "content", "dashboard", "template", "skip"

@dataclass
class NotionRelationInfo:
    """A detected cross-database relation."""
    source_db: str
    source_column: str
    target_db: str
    match_confidence: float             # 0.0–1.0 based on title match %

@dataclass
class NotionScanResult:
    """Complete result of scanning a Notion ZIP export."""
    workspace_name: str
    import_id: str
    extract_path: str
    databases: list[NotionDatabaseInfo]
    standalone_pages: list[NotionStandalonePage]
    relations: list[NotionRelationInfo]
    total_files: int
    csv_files: int
    markdown_files: int
    attachment_files: int
    warnings: list[ScanWarning]
    scan_duration_seconds: float
```

### NotionMappingConfig (extends/parallels MappingConfig)

```python
@dataclass
class NotionMappingConfig:
    """Complete mapping configuration for a Notion import."""
    version: int = 1
    
    # DB classification: db_name → "structured" | "content" | "skip"
    classifications: dict[str, str]
    
    # Type mappings: db_name → TypeMapping (same as Obsidian)
    type_mappings: dict[str, TypeMapping | None]
    
    # Property mappings: target_type_iri → {csv_column → PropertyMapping}
    property_mappings: dict[str, dict[str, PropertyMapping | None]]
    
    # Relation mappings: "source_db.column" → RelationMapping
    relation_mappings: dict[str, RelationMapping | None]

@dataclass
class RelationMapping:
    """Maps a Notion Relation column to an RDF predicate."""
    predicate_iri: str
    predicate_label: str
    target_type_iri: str                # the RDF type of the target DB's objects
```

---

## 6. Architecture: Reuse from Obsidian Module

| Component | Reuse Strategy |
|-----------|---------------|
| **Router pattern** | Copy and adapt — same endpoint structure, different module name |
| **ScanBroadcast / SSE** | **Reuse directly** — import from `obsidian.broadcast` or extract to shared module |
| **Step bar template** | **Reuse directly** — just pass different step labels |
| **Upload form template** | **Reuse directly** — identical UX (accept ZIP) |
| **Import progress template** | **Reuse directly** — identical SSE-driven progress |
| **Import summary template** | **Adapt** — add relation stats |
| **ImportExecutor** | **Adapt** — Pass 1 reads CSV instead of frontmatter, Pass 2 resolves Relations instead of wiki-links |
| **Models (TypeMapping, PropertyMapping)** | **Reuse** — extract to shared module |
| **Scanner** | **New** — NotionZIPScanner with CSV parsing, ID stripping, relation detection |

### Suggested Module Structure

```
backend/app/notion/
├── __init__.py
├── router.py           # FastAPI routes (adapted from obsidian/router.py)
├── scanner.py          # NotionZIPScanner (new — CSV + .md parsing)
├── executor.py         # NotionImportExecutor (adapted from obsidian/executor.py)
├── models.py           # NotionScanResult, NotionMappingConfig, etc.
└── csv_parser.py       # CSV column type inference, ID stripping, relation detection

backend/app/imports/     # NEW shared module
├── __init__.py
├── broadcast.py        # Moved from obsidian/broadcast.py
├── models.py           # Shared TypeMapping, PropertyMapping, ImportResult
└── templates.py        # Shared template helpers if needed

backend/app/templates/notion/
├── import.html
└── partials/
    ├── step_bar.html           # Could share with obsidian via include
    ├── upload_form.html        # Nearly identical to obsidian
    ├── scan_results.html       # Notion-specific: databases, pages, relations
    ├── classify.html           # NEW: structured/content/skip classification
    ├── type_mapping.html       # Adapted from obsidian
    ├── property_mapping.html   # Adapted from obsidian
    ├── relation_mapping.html   # NEW: relation → predicate mapping
    ├── preview.html            # Adapted with relation preview
    ├── import_progress.html    # Reuse obsidian's
    └── import_summary.html     # Adapted with relation stats
```

---

## 7. Complete Notion Content Inventory — What Can We Import?

Beyond databases and standalone pages, Notion workspaces contain many other content types. Here's the full inventory with import strategy for each:

### Tier 1: High-Value Structured Data (Import as Objects)

| Notion Content | What It Is | Import Strategy |
|---------------|------------|----------------|
| **Database rows** | Typed records with properties | → RDF objects with mapped properties |
| **Relation columns** | Cross-DB links | → RDF edges (most valuable signal) |
| **Select / Multi-select** | Enum values, tags | → Category properties or `schema:keywords` |
| **Date properties** | Dates, date ranges | → `xsd:date` / `xsd:dateTime` literals |
| **Checkbox properties** | Boolean flags | → `xsd:boolean` literals |
| **URL properties** | Links | → `xsd:anyURI` literals |
| **Number properties** | Quantities | → `xsd:decimal` / `xsd:integer` literals |
| **Person properties** | "Created by", "Assigned to" | → Plain text string (or link to Person object if matching) |

### Tier 2: Rich Content (Import as Notes / Bodies)

| Notion Content | What It Is | Import Strategy |
|---------------|------------|----------------|
| **Standalone pages** | Free-form writing | → Note objects with markdown body |
| **Database row bodies** | Content inside a DB row | → Object body (markdown) attached to the row's RDF object |
| **Wiki pages** | Verified/owned docs | → Note objects, preserve verification metadata as properties |
| **Comments** | Discussion threads (opt-in in export) | → Could attach as `rdfs:comment` annotations or skip |
| **Web bookmarks** | `bookmark` blocks in pages | → Extract URLs, store as Note with `schema:url` property |
| **Synced blocks** | Content mirrored across pages | → Flattened in export (content duplicated). Import once, skip dupes |
| **Toggle blocks** | Collapsible content | → Convert to markdown (headings or `<details>` blocks) |
| **Callout blocks** | Highlighted boxes | → Convert to blockquote or custom markdown notation |

### Tier 3: Metadata to Preserve (Not imported as objects, but recorded)

| Notion Content | What It Is | Preservation Strategy |
|---------------|------------|----------------------|
| **Dashboard pages** | Pages composed of DB views, filters, charts, embeds | → Record as `ImportedDashboardSpec` (see below) |
| **Database views** | Board, Gallery, Calendar, Timeline, Chart configurations | → Record view type + filters + sort + grouping |
| **Automations** | Trigger→action rules on databases | → Record as text description in dashboard spec |
| **Favorites / Sidebar order** | Personal nav organization | → Record as ordered list for reference |
| **Page hierarchy** | Parent/child page nesting | → Preserve via `dcterms:isPartOf` edges |
| **Page icons & covers** | Emoji icons, cover images | → Store icon as property, download cover image |

### Tier 4: Skip (Platform-bound, no meaningful export)

| Notion Content | Why Skip |
|---------------|----------|
| **Notion Forms** | Form logic (conditional questions) doesn't export; data goes to a DB we already import |
| **Notion Sites** | Publishing config (domains, SEO, nav) — platform-specific |
| **Notion Mail** | Email threads — different domain entirely |
| **Notion Calendar** | Calendar views are just date-property DB views — data already captured |
| **AI Agents** | Platform-bound LLM workflows — no export representation |
| **Connected/Synced DBs** | External data (Jira, GitHub) exports as a static snapshot — import if user wants, but warn it's stale |
| **Integrations** | API connections, Zapier/Make rules — platform plumbing |
| **Rollup properties** | Computed aggregations — preserve in DashboardSpec (see Section 8) as derived-field hints. Records which relation was rolled up, what aggregation was used (count, sum, etc.), giving the AI copilot enough to reconstruct equivalent SPARQL aggregations or ViewSpec computed fields |
| **Formula properties** | Computed values — preserve in DashboardSpec as formula specs. The formula text itself (e.g., `if(Status == "Done", "✅", "⏳")`) encodes business logic the user cared about. Snapshot values can optionally be imported as static text properties |

---

## 8. Dashboard & View Metadata Preservation

### The Problem You Identified
When a user skips a "dashboard" page, that page represented *intent* — how they organized and viewed their data. Discarding it entirely loses that signal. Even if we can't recreate the exact Notion layout, we should capture *what the user was trying to see* so they (or an AI copilot) can rebuild it later.

### What We Can Extract from Dashboard Pages

Even in a ZIP export, dashboard pages contain useful signals:

1. **Database view embeds** — references to which databases were shown
2. **Inline text** — sometimes users add headers, instructions, or context between views
3. **View names** — if the page title follows patterns like "Weekly Dashboard", "Project Tracker Overview"
4. **Page hierarchy** — where the dashboard sat in the workspace tree (what it was "about")

### Proposed: `ImportedDashboardSpec` Object

When the user classifies a page as "Dashboard / View" in the Classify step, instead of silently skipping it, create a lightweight metadata record:

```python
@dataclass
class DashboardSpec:
    """Preserved metadata about a skipped dashboard/view page."""
    title: str                          # "Weekly Review Dashboard"
    original_path: str                  # path in Notion export
    description: str                    # any inline text found on the page
    referenced_databases: list[str]     # names of databases embedded on this page
    view_hints: list[ViewHint]          # detected view configurations
    derived_fields: list[DerivedFieldSpec]  # rollups and formulas from referenced DBs
    parent_page: str | None             # what page this dashboard lived under
    raw_content: str                    # original markdown (for AI copilot later)

@dataclass
class ViewHint:
    """A hint about a database view configuration found on a dashboard."""
    database_name: str
    view_type: str | None               # "board", "gallery", "calendar", "timeline", "table", "chart", None
    filter_description: str | None       # any filter text we can extract
    group_by: str | None                 # property used for grouping (board columns, etc.)

@dataclass
class DerivedFieldSpec:
    """A rollup or formula column from a Notion database — preserved as a
    reconstruction hint for AI copilot or future dashboard builder."""
    database_name: str                  # which DB this came from
    column_name: str                    # "Completion %", "Total Tasks"
    field_type: str                     # "rollup" or "formula"
    # Rollup-specific:
    source_relation: str | None         # which relation column was rolled up
    aggregation: str | None             # "count", "sum", "percent_checked", etc.
    # Formula-specific:
    formula_text: str | None            # raw formula expression from Notion
    # Both:
    sample_values: list[str]            # up to 5 sample computed values from CSV
```

**Why rollups and formulas belong here:** These columns encode *what derived information the user cared about*. A rollup like "Count of completed Action Items per Project" tells us the user wants an aggregation view — which maps directly to a SPARQL `COUNT` query or a future ViewSpec computed field. A formula like `if(prop("Status") == "Done", "✅", "⏳")` encodes business logic (conditional formatting, status derivation) that an AI copilot can translate into equivalent SemPKM view rules.

The CSV export includes the *computed values* for rollups and formulas as plain columns. We can:
1. Parse the column header to identify it as rollup/formula (heuristic: columns with mostly numeric values or limited unique values that don't match a select pattern)
2. Record the column name and sample values in the DashboardSpec
3. If using the API path later, we get explicit rollup/formula metadata (source relation, aggregation type, formula expression) which makes reconstruction much richer

### How This Gets Stored in RDF

Create a lightweight RDF type for these:

```turtle
sempkm:DashboardSpec a owl:Class ;
    rdfs:label "Dashboard Specification" ;
    rdfs:comment "Preserved metadata about a dashboard or view page from an imported workspace. Not yet implemented as a live view — serves as a reference for the user or AI copilot to reconstruct." .

sempkm:referencesDatabase a owl:ObjectProperty ;
    rdfs:domain sempkm:DashboardSpec ;
    rdfs:comment "Links a dashboard spec to the database types it referenced." .

sempkm:viewHint a owl:DatatypeProperty ;
    rdfs:domain sempkm:DashboardSpec ;
    rdfs:comment "JSON blob describing a detected view configuration (type, filters, grouping)." .

sempkm:rawSourceContent a owl:DatatypeProperty ;
    rdfs:domain sempkm:DashboardSpec ;
    rdfs:comment "Original markdown content from the source page, preserved for AI copilot reconstruction." .

sempkm:derivedField a owl:DatatypeProperty ;
    rdfs:domain sempkm:DashboardSpec ;
    rdfs:comment "JSON blob describing a rollup or formula column — captures the computation intent (aggregation type, source relation, formula expression) plus sample values for reconstruction." .
```

The `derivedField` entries capture rollups and formulas from the databases referenced by the dashboard. Even when the dashboard page itself is skipped, its referenced databases' computed columns are recorded here because they represent the *analytical intent* — what the user wanted to see derived from their data. This is the bridge between "I had a Notion formula" and "the AI copilot can generate a SPARQL query or ViewSpec that does the same thing."

### What This Enables

1. **Immediate value:** User sees "3 dashboard specs preserved" in the import summary. They can browse these in the workspace and see "oh right, I had a Weekly Review dashboard that showed Action Items filtered by status, grouped by project."

2. **AI copilot value:** When the copilot is ready, a user can say "rebuild my Weekly Review dashboard" and the copilot has:
   - The original page title and context
   - Which databases/types were referenced
   - View type hints (board, calendar, etc.)
   - The raw markdown for any custom instructions or layout notes
   - The full import context (what types those databases mapped to)

3. **Progressive reconstruction:** As SemPKM builds more view/dashboard capabilities, these specs become actionable. A future "Dashboard Builder" could read DashboardSpec objects and auto-generate ViewSpecs.

### UX in the Wizard

In the **Classify** step, when user marks something as "Dashboard / View":

```
┌─────────────────────────────────────────────────────────┐
│ 📊 Weekly Review Dashboard                    [Skip ▾]  │
│                                                         │
│ ℹ️ This page references: Action Items, Projects,       │
│    Goal Outcomes                                        │
│                                                         │
│ Dashboard metadata will be preserved so you can         │
│ rebuild this view later. The raw content is saved        │
│ for your reference.                                     │
└─────────────────────────────────────────────────────────┘
```

And in the **Import Summary**:

```
✅ Import Complete
   📋 247 objects created
   🔗 89 edges created  
   📊 3 dashboard specs preserved     ← new
   ⚠️ 4 unresolved relations
```

---

## 9. Edge Cases & Challenges

### 1. Notion ID Stripping Ambiguity
Two databases could have the same name after stripping IDs. Solution: detect collisions and keep a disambiguating suffix.

### 2. Relation Resolution by Title
Notion CSV exports Relations as plain text titles. If two rows in the target DB have the same title, resolution is ambiguous. Solution: warn user, pick first match, allow manual resolution in preview step.

### 3. Multi-select Columns
A cell like `"Tag1, Tag2, Tag3"` needs to be split into multiple RDF triples. Need to detect this vs a plain text comma (heuristic: if the column has few unique "components" across all rows, it's multi-select).

### 4. Nested Databases (Sub-pages containing DBs)
Notion allows databases inside pages inside databases. The ZIP flattens this somewhat. Scanner needs to handle arbitrary nesting of folders.

### 5. Dashboard Pages
These pages are mostly `![[embed]]` references to database views. In the ZIP export, they become nearly empty markdown with broken embed references. Best to detect and suggest "Skip."

### 6. Date Formatting
Notion exports dates in various formats depending on locale and property settings. Need robust date parsing (dateutil or similar).

### 7. File/Media Properties
Some Notion properties are file uploads. These appear in the CSV as URLs (S3 pre-signed, possibly expired). Need to handle gracefully — warn if URLs are expired.

### 8. Person Properties
"Created by" / "Assigned to" columns contain Notion user display names. These could map to Person objects or be stored as plain strings.

---

## 8. Future: API-Based Import (Phase 2)

Once ZIP import is solid, add an API-connected flow:

### Step 1: Connect
- User creates Notion Integration at notion.so/my-integrations
- Shares specific databases/pages with the integration
- Provides API token to SemPKM (via `secure_env_collect`)

### Step 2: Browse & Select
- SemPKM calls `/v1/search` to list all shared databases and pages
- User selects which to import (checkbox UI)
- Shows database schemas with explicit Notion property types

### Step 3: Same Wizard
- Type Mapping, Property Mapping, Relation Mapping, Preview, Import
- But with richer data: explicit property types, real relation IDs (not title-matching), formulas/rollups flagged properly

### Advantages over ZIP
- Explicit property types (no inference needed)
- Relation resolution by ID (not title matching — no ambiguity)
- Incremental re-import (only new/changed rows)
- Page body as Enhanced Markdown (better fidelity than ZIP export)

---

## 10. Summary: Build Order

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | Extract shared infrastructure from Obsidian module (broadcast, models, step bar) | Small |
| **Phase 2** | Notion ZIP scanner (CSV parsing, ID stripping, relation detection, dashboard detection) | Medium |
| **Phase 3** | Notion wizard steps 1-3 (Upload, Parse, Classify — with all 5 classification options) | Medium |
| **Phase 4** | Notion wizard steps 4-6 (Type/Property/Relation mapping) — adapt from Obsidian | Medium |
| **Phase 5** | Notion executor — objects, edges, content pages, **DashboardSpec preservation** | Medium |
| **Phase 6** | Preview step + import summary (showing dashboard specs preserved count) | Small |
| **Phase 7** | Comments import (opt-in), bookmark extraction, wiki verification metadata | Small |
| **Future** | Notion API live-connection import | Large |
| **Future** | AI copilot dashboard reconstruction from DashboardSpec objects | Medium |
