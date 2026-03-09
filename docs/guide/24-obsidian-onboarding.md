# Chapter 24: Obsidian Import

SemPKM includes a built-in import wizard that converts an Obsidian vault into typed knowledge objects. The wizard handles scanning, type mapping, property mapping, preview, and import -- all from within the browser, with no external scripts or command-line tools required.

By the end of this chapter you will know how to upload a vault, review its structure, map detected note categories to Mental Model types, map frontmatter keys to RDF properties, preview the result, and execute the import.

---

## Prerequisites

Before starting an import, make sure you have:

1. **A Mental Model installed.** The import maps vault notes to types defined by your Mental Model (e.g., Basic PKM provides Note, Project, Person, and Concept). Install a model via **Admin > Mental Models** if you have not already. See [Chapter 10: Managing Mental Models](10-managing-mental-models.md).

2. **Your Obsidian vault as a ZIP file.** Compress your vault folder into a `.zip` archive. On macOS, right-click the vault folder and choose **Compress**. On Windows, right-click and choose **Send to > Compressed (zipped) folder**. On Linux, run `zip -r vault.zip /path/to/vault`.

---

## Step 1: Upload Your Vault

Navigate to **Tools > Obsidian Import** from the sidebar. You will see a file upload area.

Click **Choose File** and select your `.zip` archive, then click **Upload**. SemPKM extracts the archive on the server and prepares it for scanning.

If the file is not a valid ZIP archive, an error message will appear asking you to try again.

> **Note:** Only one import can be in progress per user at a time. If you navigate away and return, the wizard resumes where you left off. You can discard an in-progress import to start over.

---

## Step 2: Scan the Vault

After upload, click **Scan Vault** to analyze the contents. The scanner reads every Markdown file in the vault and extracts:

- **File counts** -- total files, Markdown files, attachments, and other files
- **Type groups** -- notes grouped by detected category (see below)
- **Frontmatter keys** -- YAML frontmatter keys with occurrence counts and sample values
- **Tags** -- all `#tags` found in note bodies and frontmatter
- **Wiki-links** -- all `[[wiki-link]]` targets and how often each is referenced
- **Warnings** -- broken wiki-links (targets not found in vault), empty notes, and malformed frontmatter

A live progress indicator shows scan progress via server-sent events (SSE).

### How type detection works

The scanner uses a multi-signal approach to group notes by likely type:

1. **Frontmatter type field** (highest priority): If a note has a `type`, `category`, `class`, `kind`, or `note_type` key in its frontmatter, that value becomes the group name. Signal: `frontmatter:type`.

2. **Parent folder**: If no type field exists, the note's parent folder name is used (e.g., notes in a `Projects/` folder are grouped as "Projects"). Common utility folders like `attachments`, `templates`, `daily`, and `inbox` are skipped. Signal: `folder:Projects`.

3. **First tag**: If the note has no type field and is in the vault root, the first tag (from frontmatter or body) is used. Signal: `tag:meeting`.

4. **Uncategorized**: Notes with no type signal at all are grouped as "Uncategorized". Signal: `none`.

### Reviewing scan results

The scan results page shows:

- A summary bar with file counts
- A table of detected type groups, each showing the group name, detection signal, note count, and sample file paths
- Expandable sections for frontmatter keys, tags, and wiki-link targets
- A warnings panel listing any issues found during scanning

Review the type groups to understand how your vault will be categorized. If the groupings look wrong, consider adding `type` frontmatter to your vault notes before re-scanning.

---

## Step 3: Map Types

Click **Map Types** to proceed to the type mapping step. For each detected type group, you choose which Mental Model type it should map to -- or skip it entirely.

For example, with Basic PKM installed:

| Detected Group | Signal | Map To |
|----------------|--------|--------|
| Projects | folder:Projects | Project |
| People | folder:People | Person |
| meeting | tag:meeting | Note |
| Uncategorized | none | Note |
| concept | frontmatter:type | Concept |

Each row shows a dropdown of available types from your installed Mental Model(s). Select the target type for each group. To exclude a group from the import, leave it unmapped.

Type mappings are auto-saved as you make selections -- no save button needed.

---

## Step 4: Map Properties

Click **Map Properties** to configure how frontmatter keys map to RDF properties for each target type.

The wizard shows one section per mapped type. Each section lists:

- The frontmatter keys found in notes of that type, with occurrence counts and sample values
- A dropdown of available properties from the type's SHACL shape

For example, mapping frontmatter for notes mapped to the **Project** type:

| Frontmatter Key | Sample Values | Map To |
|-----------------|---------------|--------|
| status | active, completed | bpkm:status |
| priority | high, medium | bpkm:priority |
| due_date | 2025-03-15 | schema:dateModified |
| aliases | -- | *(skip)* |

If a frontmatter key does not match any property in the type's shape, you can skip it. Skipped keys are not imported.

Property mappings are also auto-saved as you make selections.

---

## Step 5: Preview

Click **Preview** to see sample transformations before committing. The preview page shows a few notes from each type group with:

- The source file path
- The mapped properties and their values (extracted from frontmatter)
- Whether the note has body content

This is your last chance to verify that the mappings look correct before importing. If something looks wrong, go back to the type or property mapping steps to adjust.

---

## Step 6: Import

Click **Import** to begin creating objects. The import runs in two passes:

### Pass 1: Create objects

For each Markdown file in the vault:

1. The note is parsed for frontmatter and body content
2. Its type group is detected (same logic as the scanner)
3. The type mapping determines the RDF type
4. Frontmatter values are mapped to properties using your property mappings
5. The object is created via the Command API with its type, properties, and body
6. Tags from both frontmatter and body `#tags` are stored as `schema:keywords` values
7. An `sempkm:importSource` property records the original file path for deduplication

A live progress bar shows how many notes have been processed.

### Pass 2: Resolve wiki-links

After all objects are created, the importer resolves `[[wiki-links]]` between imported notes:

1. Each wiki-link target is matched by filename (case-insensitive)
2. If the target exists among imported objects, a `dcterms:references` edge is created
3. If a wiki-link has an alias (`[[target|alias]]`), the alias is stored as `rdfs:label` on the edge
4. Unresolved links (targets not found) are counted and reported

### Import summary

When the import completes, a summary shows:

- **Objects created** -- how many new objects were added
- **Skipped (existing)** -- notes that were already imported (deduplication by `sempkm:importSource`)
- **Skipped (errors)** -- notes that failed to import, with error details
- **Edges created** -- how many wiki-link relationships were resolved
- **Unresolved links** -- wiki-links whose targets were not found in the vault
- **Duration** -- total import time

The sidebar navigation tree refreshes automatically to show the newly imported objects.

---

## After Import

Once the import is complete, your Obsidian notes are full SemPKM objects. You can:

- **Browse by type** -- expand type nodes in the Explorer sidebar to see all imported objects
- **Edit objects** -- open any imported object to edit its properties, body, or type
- **View relationships** -- check the Relations panel to see wiki-link edges
- **Use the graph view** -- visualize how your imported notes connect to each other
- **Run SHACL validation** -- the Lint panel flags any objects missing required properties
- **Search** -- press **Alt+K** to search imported notes by keyword

Imported objects behave identically to objects created directly in SemPKM.

---

## Re-importing and Deduplication

You can run the import wizard again on an updated version of the same vault. The importer checks for existing `sempkm:importSource` values and skips notes that were already imported. This prevents duplicates when re-importing.

To re-import a note that was previously imported, delete the existing object first, then run the import again.

---

## Troubleshooting

### "The uploaded file is not a valid ZIP archive"

The file you selected is not a valid `.zip` file. Make sure you compressed the vault folder itself (not individual files). Some archive tools produce `.rar` or `.7z` files -- only `.zip` is supported.

### Notes appear in the wrong type group

The scanner uses a priority-based detection system. If notes are miscategorized:

- Add a `type` key to your notes' frontmatter (highest priority signal)
- Move notes into descriptively named folders (second priority)
- Re-scan after making changes

### Frontmatter parsing warnings

Some YAML frontmatter may fail to parse if it contains invalid YAML syntax (unclosed quotes, tabs instead of spaces, etc.). These notes will still be imported with their body content but without frontmatter properties.

### Large vaults

The scanner and importer process files sequentially. Very large vaults (thousands of notes) may take several minutes. The progress indicators show real-time status during both scanning and importing.

### Unresolved wiki-links

Wiki-links are resolved by matching the link target to filenames of imported notes (case-insensitive). Links will not resolve if:

- The target note was not included in the vault ZIP
- The target note's type group was not mapped (skipped during type mapping)
- The link uses a path prefix (e.g., `[[folder/note]]`) -- only the filename portion is matched

Unresolved links are reported in the import summary. You can create the missing objects manually and add edges in the Relations panel.

---

## See Also

- [Chapter 10: Managing Mental Models](10-managing-mental-models.md) -- install a model before importing
- [Chapter 19: Creating Mental Models](19-creating-mental-models.md) -- create custom types for specialized vaults
- [Chapter 23: Virtual Filesystem (WebDAV)](23-vfs.md) -- browse imported objects as Markdown files

---

**Previous:** [Chapter 23: Virtual Filesystem (WebDAV)](23-vfs.md) | **Next:** [Chapter 25: WebID Profiles](25-webid-profiles.md)
