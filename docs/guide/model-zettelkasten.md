<!-- GENERATED FILE. Do not edit. Source: models/zettelkasten/README.md. Regenerate with: python3 scripts/sync-model-docs.py -->
> **Bundled model documentation.** This page mirrors the `README.md` shipped inside the `zettelkasten` Mental Model archive. The same text is available in the app under **Admin > Models > Zettelkasten+ > Documentation** and at `/api/models/zettelkasten/docs`. To change it, edit `models/zettelkasten/README.md` and run `scripts/sync-model-docs.py`.

# Zettelkasten+

**Model ID:** `zettelkasten` · **Namespace:** `urn:sempkm:model:zettelkasten:` · **Prefix:** `zk:`

Zettelkasten+ implements the Zettelkasten method for structured note-taking with a full provenance
chain from quick captures through permanent knowledge. It adds argumentation links between
permanent notes for building webs of interconnected ideas, and SHACL-AF rules that keep the
processing backlog visible.

## Types

### FleetingNote

A quick, raw capture of an idea or thought. Fleeting notes are the entry point to the
Zettelkasten — capture now, process later.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Short label for this thought |
| Body | string | | Main text content |
| Captured From | string | | Context where the thought was captured |
| Tags | string[] | | Free-form labels |
| Created | date | | When the note was captured |

### Source

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

### LiteratureNote

A summary of a key idea from a source, written in your own words. Each literature note references
a single source.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Concise title summarizing the key idea |
| Body | string | | Your paraphrase or summary |
| Original Quote | string | | Verbatim excerpt from the source |
| Page Reference | string | | Page number or location |
| Derived From | → Source | | The source being summarized |
| Tags | string[] | | Free-form labels |

### PermanentNote

An atomic, self-contained knowledge claim — the core of your Zettelkasten. Permanent notes
express your own ideas, developed from literature notes or original thought.

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

### StructureNote

An organizing note that curates permanent notes into coherent topics — argument maps, field
surveys, or indexes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Title | string | ✓ | Topic being organized |
| Body | string | | Overview text describing the organization |
| Purpose | enum | | `argument`, `survey`, `index`, `sequence`, `comparison` |
| Includes | → PermanentNote | | Permanent notes organized by this structure |
| Related Structures | → StructureNote | | Other structure notes on related topics |
| Tags | string[] | | Free-form labels |

## The provenance chain

The model enforces a clear provenance chain from raw capture to organized knowledge:

```
FleetingNote → Source → LiteratureNote → PermanentNote → StructureNote
     ↑              ↑           ↑              ↑               ↑
  quick capture   reference   summary of    your own idea   organized
                  material    source idea                   overview
```

Each arrow is a "developed from" or "derived from" link that keeps attribution back to the
original source.

## Argumentation links

PermanentNotes connect to each other through four argumentation link types:

| Link | Meaning |
|------|---------|
| **supports** | This idea provides evidence for the target idea |
| **contradicts** | This idea challenges or provides counter-evidence for the target |
| **followsFrom** | This idea is a logical continuation of the target |
| **relatedTo** | Thematic connection without a specific logical relationship |

Use the **Contradiction Map** saved query to visualize debates and tensions across your notes.

## Views and saved queries

Table views for Fleeting Notes, Sources, and Structure Notes; Cards for Literature Notes; and the
**Zettelkasten Graph** for Permanent Notes. Saved queries:

| Query | Description |
|-------|-------------|
| Unprocessed Fleeting Notes | Fleeting notes that have not been developed into literature or permanent notes |
| Isolated Permanent Notes | Permanent notes with no connections to other notes or structure notes |
| Contradiction Map | Graph of permanent notes connected by `contradicts` links |
| Provenance Chain | Graph showing the full path from sources through notes to structures |

## Validation rules

| Rule | Severity | Message |
|------|----------|---------|
| Unprocessed fleeting note | Warning | "This fleeting note hasn't been processed. Develop it into a literature or permanent note, or delete it." |
| Isolated permanent note | Warning | "This permanent note is isolated. Connect it to other ideas or include it in a structure note." |
| Unsourced idea | Info | "This idea has no literature source. Consider linking it to supporting evidence." |
| Empty note | Info | "Note has no body content. Consider adding your thoughts." |

## Installation

Go to **Admin > Models**, pick **Zettelkasten+** from the bundled catalog (or enter the path
`/app/models/zettelkasten`) and click **Install**. The five types appear in the Explorer sidebar;
seed data includes an unprocessed fleeting note so the warning rule has something to flag.

## Recommended dashboards and workflows

Use a **sidebar-main** layout:

- **Sidebar:** embed the "Unprocessed Fleeting Notes" saved query — your processing backlog at a glance.
- **Main:** embed the Zettelkasten Graph view to see connections between permanent notes, structure notes, and sources.

For a processing workflow, create a three-step workflow: (1) Fleeting Notes table to pick a
note, (2) Sources table to find or create a source, (3) a create form for PermanentNote
pre-linked to the source.

---

**Back:** [Chapter 39: Mental Model Catalog](39-mental-model-catalog.md)
