# Chapter 39: Notion Import

SemPKM includes a built-in import wizard that converts a Notion workspace export into typed knowledge objects. The wizard handles ZIP upload, database scanning, type mapping, property mapping, relation mapping, preview, and import — all from within the browser, with no external scripts or command-line tools required.

By the end of this chapter you will know how to export your Notion workspace, upload it to SemPKM, review detected databases and columns, map Notion databases to Mental Model types, map columns to RDF properties, configure cross-database relation resolution, preview the result, and execute the import.

---

## Prerequisites

Before starting an import, make sure you have:

1. **A Mental Model installed.** The import maps Notion databases to types defined by your Mental Model (e.g., Basic PKM provides Note, Project, Person, and Concept). Install a model via **Admin > Mental Models** if you have not already. See [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **A Notion workspace export as a ZIP file.** To export from Notion:
   1. Open **Settings & members** from the left sidebar
   2. Select **Settings** → scroll to **Export all workspace content**
   3. Set **Export format** to **Markdown & CSV**
   4. Click **Export** and wait for the download link
   5. Download the `.zip` file — this is your import source

> **Note:** Only the "Markdown & CSV" export format is supported. The "HTML" format does not include the CSV database files that SemPKM needs for structured property import.

---

## Step 1: Upload Your Export

Navigate to **Tools > Import Notion** from the sidebar. You will see a file upload area.

Click **Choose File** and select your Notion `.zip` export, then click **Upload**. SemPKM extracts the archive on the server and prepares it for scanning.

If the file is not a valid ZIP archive, an error message will appear asking you to try again.

> **Note:** Only one import can be in progress per user at a time. If you navigate away and return, the wizard resumes where you left off. You can click **Discard** at any time to abandon an in-progress import and start over.

---

## Step 2: Review Scan Results

After upload, the scanner automatically analyzes the extracted workspace. The scan results page shows:

- **Stat cards** — Total databases found, total pages, and standalone pages (pages not in any database)
- **Database summaries** — Each detected database listed with its row count and column breakdown

### Column type badges

Each database column is shown with a type badge indicating its detected data type:

| Badge | Meaning |
|-------|---------|
| `text` | Plain text or rich text |
| `number` | Numeric values |
| `date` | Date or date-time values |
| `select` | Single-select dropdown |
| `multi_select` | Multi-select tags |
| `checkbox` | Boolean checkbox |
| `url` | URL/link values |
| `relation` | Cross-database relation |

### Cross-database relations

When two databases reference each other via a Notion relation column, the scanner detects the link and displays it with a **match percentage** — the proportion of relation values that resolved to rows in the target database. A high match percentage (90%+) means most references will create edges during import.

### Standalone pages

Pages that exist outside any database (e.g., top-level workspace pages with Markdown content but no CSV structure) are listed separately. These are imported as individual objects rather than as database rows.

### Warnings

The scan results include a warnings section for any issues discovered:

- **Malformed CSV** — a database file could not be parsed (encoding issues, missing headers)
- **Empty databases** — databases with column definitions but no data rows
- **Missing relation targets** — relation columns reference databases not found in the export

Review the scan results to understand the structure of your workspace before proceeding.

---

## Step 3: Type Mapping

Click **Next** to proceed to the type mapping step. For each detected database, you choose which Mental Model type it should map to — or skip it entirely.

For example, with Basic PKM installed:

| Notion Database | Map To |
|-----------------|--------|
| Tasks | Project |
| Reading List | Note |
| People | Person |
| Meeting Notes | Note |
| *(Standalone pages)* | Concept |

Each row shows a dropdown of available types from your installed Mental Model(s). To exclude a database from the import, leave it set to **— Skip —**.

Standalone pages get their own type mapping row, separate from the databases.

---

## Step 4: Property Mapping

Click **Next** to configure how database columns map to RDF properties for each target type.

The wizard shows one section per mapped type. Each section lists the CSV columns found in databases of that type, with a dropdown of available SHACL properties from the type's shape.

| CSV Column | Sample Values | Map To |
|------------|---------------|--------|
| Name | "Q3 Planning", "Bug Triage" | dcterms:title |
| Status | Done, In Progress | bpkm:status |
| Priority | High, Medium, Low | bpkm:priority |
| Due Date | 2025-03-15 | schema:dateModified |
| Tags | design, review | schema:keywords |
| Notes | *(long text)* | *(skip)* |

**Auto-suggest:** The wizard pre-selects matching properties when a column name closely matches a SHACL property name (e.g., "Status" auto-maps to `bpkm:status`). Review and adjust these suggestions as needed.

**Relation columns excluded:** Columns with the `relation` type badge do not appear in this step — they are handled separately in the next step.

If a column does not match any useful property, leave it unmapped. Unmapped columns are not imported.

---

## Step 5: Relation Mapping

Click **Next** to configure cross-database relation mappings. This step **only appears when relations were detected** during scanning.

For each detected relation, the wizard shows:

- **Source database** → **Target database** (e.g., Tasks → People)
- **Match percentage badge** — how many relation values resolved to target rows
- A dropdown of available edge predicates from your Mental Model

For example:

| Relation | Match | Map To |
|----------|-------|--------|
| Tasks → People (Assignee) | 95% | bpkm:hasParticipant |
| Reading List → People (Author) | 87% | dcterms:creator |
| Tasks → Tasks (Blocked By) | 100% | bpkm:dependsOn |

Select the appropriate edge predicate for each relation. Edges will be created between the imported objects during import.

If no relations were detected in your export, this step is skipped automatically.

---

## Step 6: Preview

Click **Next** to review a summary of all your mappings before committing. The preview page shows:

- **Mapping summary table** — all databases, their target types, and mapped column counts
- **Sample object cards** — a few representative objects showing how imported data will look with your current mappings

This is your last chance to verify that the mappings look correct. If something looks wrong, click **Back** to return to a previous step and adjust.

---

## Step 7: Import

Click **Import** to begin creating objects. The import runs in two passes with a live SSE progress bar:

### Pass 1: Create objects

For each database row and standalone page:

1. The row's CSV data is parsed using the column type information
2. The type mapping determines the RDF type
3. Column values are mapped to properties using your property mappings
4. Markdown body content (from the corresponding `.md` file) is attached
5. The object is created via the Command API with its type, properties, and body

A live progress bar shows how many objects have been processed.

### Pass 2: Resolve relations

After all objects are created, the importer resolves cross-database relations:

1. Each relation column value is matched to target objects by title (case-insensitive)
2. If a match is found, an edge is created using the predicate from your relation mapping
3. Unresolved relations (titles not found in the target database) are counted and reported

### Import summary

When the import completes, a summary page shows stat cards:

- **Created** — how many new objects were added
- **Edges** — how many relation edges were resolved
- **Skipped** — rows or pages that were not imported (unmapped types, errors)
- **Duration** — total import time

Collapsible sections below the stat cards show:

- **Unresolved relations** — relation values that could not be matched to a target object (usually due to duplicate or missing titles in the target database)
- **Errors** — any rows that failed to import, with error details

---

## After Import

Once the import is complete, your Notion data is now full SemPKM objects. You can:

- **Browse Imported Objects** — click this button to open the workspace filtered to your newly imported types
- **Import More** — upload another Notion export ZIP to import additional workspaces
- **Discard** — clean up the import session data

Imported objects behave identically to objects created directly in SemPKM:

- **Browse by type** — expand type nodes in the Explorer sidebar
- **Edit objects** — open any imported object to edit properties, body, or type
- **View relationships** — check the Relations panel to see edges from Notion relations
- **Use the graph view** — visualize how your imported data connects
- **Run SHACL validation** — the Lint panel flags objects missing required properties
- **Search** — press **Alt+K** to search imported objects by keyword

---

## How Notion Concepts Map to SemPKM

| Notion Concept | SemPKM Equivalent | Notes |
|----------------|-------------------|-------|
| Database | Type (from Mental Model) | Each database maps to one type |
| Row / Page | Object | Each row becomes a typed object |
| Property / Column | RDF Predicate | Columns map to SHACL properties |
| Relation | Edge | Cross-database links become edges |
| Standalone Page | Object (content type) | Pages outside databases imported as objects |
| Select / Multi-select | Enum / Tags | Select values become string literals or tags |
| Markdown body | Object body | Page content preserved as Markdown |

---

## Troubleshooting

### "No databases detected"

The scanner found no CSV files in the export. This usually means:

- The export was done in **HTML format** instead of **Markdown & CSV** — re-export with the correct format
- The ZIP structure was modified after export — use the file directly as downloaded from Notion

### "0 types available" in type mapping

No Mental Model is installed. Install a model via **Admin > Mental Models** before starting the import. See [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

### Unresolved relations

Relation values are matched to target objects by title (case-insensitive). Relations will not resolve if:

- The target row has a **duplicate title** — the importer cannot determine which object to link to
- The target database was **skipped** (unmapped) during type mapping
- The relation value contains extra whitespace or formatting that differs from the actual title

Unresolved relations are listed in the import summary. You can create the missing edges manually in the Relations panel.

### Import takes too long

Large Notion workspaces with thousands of rows may take several minutes to import. This is normal. The SSE progress bar shows real-time status during both object creation and relation resolution passes. Do not navigate away during import — the progress stream tracks the active session.

### Markdown body not imported

If an object has properties but no body content, the corresponding `.md` file may be missing from the export or may have a mismatched filename. Notion exports pair each database row with a Markdown file; if the file is absent, the object is created with properties only.

---

## See Also

- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) — install a model before importing
- [Chapter 24: Obsidian Onboarding](24-obsidian-onboarding.md) — import from Obsidian instead of Notion
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) — configuration options

---

**Previous:** [Chapter 38: Hosted Demo](38-hosted-demo.md) | **Next:** [Chapter 40: AI Features](40-ai-features.md)
