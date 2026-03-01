# Chapter 24: Obsidian Onboarding

This chapter walks you through migrating an Obsidian vault into SemPKM. By the end, you will have a repeatable workflow for auditing your vault, classifying notes by type, extracting structured properties, converting wiki-links into typed edges, and importing everything via the Command API.

The workflow is designed for vaults of any size -- from a few dozen notes to thousands -- and uses LLM-assisted classification to make large vaults practical.

---

## 1. The Gap Between Obsidian and SemPKM

Obsidian and SemPKM store knowledge in fundamentally different ways.

**Obsidian** keeps your notes as flat Markdown files in a local folder. Connections between notes use `[[wiki-links]]`, which are untyped -- a link from a meeting note to a person looks identical to a link from a project to a concept. Organization comes from folder structure, tags (`#tag`), and optional YAML frontmatter. There is no schema: any note can have any shape.

**SemPKM** stores knowledge as typed RDF objects in a graph database. Every object has a declared type (Note, Project, Person, Concept), every relationship has a named predicate (`hasParticipant`, `isAbout`, `relatedProject`), and every type has a SHACL shape that defines its expected properties and generates editing forms automatically. Organization is structural, not positional.

The core challenge when migrating is this: most Obsidian vaults have hundreds of notes with no frontmatter, no consistent tagging, and untyped links. Each note needs to be:

1. **Classified** -- assigned a SemPKM type (Note, Project, Person, Concept)
2. **Structured** -- its content mapped to typed properties (`dcterms:title`, `foaf:name`, `bpkm:status`)
3. **Connected** -- its `[[wiki-links]]` converted into typed edges (`bpkm:hasParticipant`, `bpkm:isAbout`)

This chapter provides a concrete, end-to-end workflow for all three steps.

---

## 2. Vault Audit: Understanding What You Have

Before importing anything, analyze your vault to understand its structure, size, and existing metadata. This audit shapes your import strategy.

### What to look for

- **Folder structure** -- folders are often the only implicit "type" signal. A folder named `People/` probably contains person-like notes; `Projects/` contains project-like notes.
- **Frontmatter coverage** -- how many notes have YAML frontmatter? Which keys are used? Are they consistent?
- **Wiki-link patterns** -- which notes link to which? Are there hub notes that link to many others?
- **Tag usage** -- which `#tags` appear? Do they map to types or topics?
- **Content types** -- can you estimate types from filenames alone? ("Meeting with Alice" is likely a Note; "Alice Chen" is likely a Person.)

### Vault audit script

The following Python script walks an Obsidian vault directory, counts files per folder, extracts frontmatter keys, and catalogs link targets. It requires only the Python standard library and `pyyaml`.

```python
#!/usr/bin/env python3
"""Audit an Obsidian vault before importing into SemPKM."""

import os
import re
import yaml
from pathlib import Path
from collections import Counter


def audit_vault(vault_path: str) -> dict:
    """Walk an Obsidian vault and produce a structural summary."""
    vault = Path(vault_path)
    stats = {
        "total_files": 0,
        "files_by_folder": Counter(),
        "frontmatter_keys": Counter(),
        "files_with_frontmatter": 0,
        "link_targets": Counter(),
        "tags": Counter(),
    }

    for md_file in vault.rglob("*.md"):
        stats["total_files"] += 1
        relative_folder = str(md_file.parent.relative_to(vault))
        stats["files_by_folder"][relative_folder] += 1

        text = md_file.read_text(encoding="utf-8", errors="replace")

        # Extract YAML frontmatter
        fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if fm_match:
            stats["files_with_frontmatter"] += 1
            try:
                fm = yaml.safe_load(fm_match.group(1))
                if isinstance(fm, dict):
                    for key in fm:
                        stats["frontmatter_keys"][key] += 1
            except yaml.YAMLError:
                pass

        # Extract [[wiki-links]]
        for link in re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text):
            stats["link_targets"][link.strip()] += 1

        # Extract #tags
        for tag in re.findall(r"(?:^|\s)#([a-zA-Z0-9_/-]+)", text):
            stats["tags"][tag] += 1

    return stats


def print_report(stats: dict) -> None:
    """Print a human-readable audit summary."""
    print(f"=== Vault Audit ===")
    print(f"Total Markdown files: {stats['total_files']}")
    fm_pct = (
        (stats["files_with_frontmatter"] / stats["total_files"] * 100)
        if stats["total_files"]
        else 0
    )
    print(f"Files with frontmatter: {stats['files_with_frontmatter']} ({fm_pct:.0f}%)")
    print(f"Unique link targets: {len(stats['link_targets'])}")
    print(f"Unique tags: {len(stats['tags'])}")

    print(f"\n--- Files by Folder ---")
    for folder, count in stats["files_by_folder"].most_common(20):
        print(f"  {folder}: {count}")

    print(f"\n--- Top Frontmatter Keys ---")
    for key, count in stats["frontmatter_keys"].most_common(20):
        print(f"  {key}: {count}")

    print(f"\n--- Top Link Targets ---")
    for target, count in stats["link_targets"].most_common(20):
        print(f"  [[{target}]]: {count}")

    print(f"\n--- Top Tags ---")
    for tag, count in stats["tags"].most_common(20):
        print(f"  #{tag}: {count}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/obsidian/vault")
        sys.exit(1)
    stats = audit_vault(sys.argv[1])
    print_report(stats)
```

Run it:

```bash
python3 vault_audit.py /path/to/your/vault
```

Example output:

```
=== Vault Audit ===
Total Markdown files: 347
Files with frontmatter: 89 (26%)
Unique link targets: 412
Unique tags: 54

--- Files by Folder ---
  Daily Notes: 142
  Projects: 31
  People: 28
  Concepts: 19
  Meetings: 44
  .: 83

--- Top Frontmatter Keys ---
  date: 89
  tags: 67
  status: 31
  aliases: 22
```

This output tells you that the vault has 347 notes, only 26% have frontmatter, and the folder names (`Projects`, `People`, `Concepts`, `Meetings`) strongly suggest type mappings.

---

## 3. Choosing a Mental Model Strategy

Based on your audit, decide which Mental Model to target for the import. There are three approaches.

### Option A: Use Basic PKM as-is

Map your notes to the four built-in types:

| Vault Pattern | SemPKM Type | Key Properties |
|---------------|-------------|----------------|
| People folder, person names | **Person** | `foaf:name`, `schema:jobTitle`, `schema:worksFor` |
| Project folder, initiative names | **Project** | `dcterms:title`, `bpkm:status`, `bpkm:priority` |
| Daily notes, meeting notes, journal | **Note** | `dcterms:title`, `bpkm:noteType`, `bpkm:body` |
| Topic notes, definitions, ideas | **Concept** | `skos:prefLabel`, `dcterms:description` |

This is the best option when your vault is a general-purpose knowledge base and 80% or more of your notes fit into these four types.

### Option B: Extend with a custom Mental Model

If your vault contains domain-specific note types (recipes, book reviews, meeting minutes with structured agendas), you can create a new Mental Model alongside Basic PKM. Your custom model defines additional types and properties in its own namespace while Basic PKM handles the general cases.

> **Note:** Mental Models are immutable after installation. You cannot add types to Basic PKM directly. Instead, create a separate model that covers your additional types. See [Chapter 19: Creating Mental Models](19-creating-mental-models.md) for the full model author guide.

### Option C: Create a fully custom Mental Model

For highly specialized vaults (research, legal, medical), you may want a Mental Model that replaces Basic PKM entirely. This gives you full control over types, properties, and relationships but requires more upfront design work.

### Decision heuristic

If more than 80% of your notes map cleanly to Note, Concept, Project, or Person, use **Option A**. If you have a significant number of notes that do not fit any of these types, consider **Option B** (extend) or **Option C** (replace). For most personal knowledge bases, Option A is the right starting point.

---

## 4. LLM-Assisted Type Classification

Manually classifying hundreds of notes is impractical. An LLM can read each note's metadata and content preview and assign it a type with high accuracy.

### The classification prompt

Use the following prompt template when calling an OpenAI-compatible LLM API:

```
You are classifying Obsidian notes for import into a structured knowledge base.

Available types: Note, Project, Person, Concept

Type definitions:
- Note: A note, observation, meeting note, journal entry, or piece of knowledge.
- Project: A project, initiative, or ongoing effort being tracked.
- Person: A person -- someone the user knows or works with.
- Concept: An abstract concept, topic, domain area, or idea being defined.

For each note, return a JSON object with:
- type: one of [Note, Project, Person, Concept]
- title: the best title for this object
- properties: key-value pairs matching the target type's schema (see below)
- confidence: high, medium, or low
- reasoning: brief explanation of why you chose this type

Property schemas by type:
- Note: { "noteType": "observation|idea|reference|meeting-note|journal", "tags": "comma-separated" }
- Project: { "status": "active|completed|on-hold|cancelled", "priority": "low|medium|high|critical" }
- Person: { "name": "full name", "jobTitle": "role if mentioned", "worksFor": "org if mentioned" }
- Concept: { "prefLabel": "preferred label", "description": "brief definition" }

Note to classify:
- File: {filename}
- Folder: {folder_path}
- Tags: {tags}
- Frontmatter: {frontmatter_yaml}
- Content preview: {first_500_chars}
```

### Classification script

The following script reads vault files, sends classification prompts to an OpenAI-compatible API, and writes results to a CSV for human review. It requires `requests` and `pyyaml`.

```python
#!/usr/bin/env python3
"""Classify Obsidian vault notes using an LLM for SemPKM import."""

import csv
import json
import os
import re
import sys
import time
import yaml
import requests
from pathlib import Path

# Configuration
API_URL = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "gpt-4o")

CLASSIFICATION_PROMPT = """You are classifying Obsidian notes for import into a structured knowledge base.

Available types: Note, Project, Person, Concept

Type definitions:
- Note: A note, observation, meeting note, journal entry, or piece of knowledge.
- Project: A project, initiative, or ongoing effort being tracked.
- Person: A person -- someone the user knows or works with.
- Concept: An abstract concept, topic, domain area, or idea being defined.

Return a JSON object (no markdown fencing) with:
- type: one of [Note, Project, Person, Concept]
- title: the best title for this object
- properties: key-value pairs matching the target type's schema
- confidence: high, medium, or low
- reasoning: brief explanation

Property schemas by type:
- Note: {{"noteType": "observation|idea|reference|meeting-note|journal", "tags": "comma-separated"}}
- Project: {{"status": "active|completed|on-hold|cancelled", "priority": "low|medium|high|critical"}}
- Person: {{"name": "full name", "jobTitle": "role", "worksFor": "organization"}}
- Concept: {{"prefLabel": "preferred label", "description": "brief definition"}}

Note to classify:
- File: {filename}
- Folder: {folder}
- Tags: {tags}
- Frontmatter: {frontmatter}
- Content preview: {preview}"""


def extract_note_metadata(filepath: Path, vault_root: Path) -> dict:
    """Extract metadata from a single Obsidian note."""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    folder = str(filepath.parent.relative_to(vault_root))

    # Extract frontmatter
    frontmatter = ""
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    body = text
    if fm_match:
        frontmatter = fm_match.group(1)
        body = text[fm_match.end():]

    # Extract tags
    tags = re.findall(r"(?:^|\s)#([a-zA-Z0-9_/-]+)", text)

    return {
        "filepath": str(filepath.relative_to(vault_root)),
        "filename": filepath.stem,
        "folder": folder,
        "tags": ", ".join(tags),
        "frontmatter": frontmatter,
        "preview": body[:500].strip(),
    }


def classify_note(metadata: dict) -> dict:
    """Send a note to the LLM for classification."""
    prompt = CLASSIFICATION_PROMPT.format(
        filename=metadata["filename"],
        folder=metadata["folder"],
        tags=metadata["tags"],
        frontmatter=metadata["frontmatter"],
        preview=metadata["preview"],
    )

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        },
        timeout=30,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"type": "Note", "title": metadata["filename"],
                "properties": {}, "confidence": "low",
                "reasoning": f"Failed to parse LLM response: {content[:200]}"}


def classify_vault(vault_path: str, output_csv: str) -> None:
    """Classify all notes in a vault and write results to CSV."""
    vault = Path(vault_path)
    notes = list(vault.rglob("*.md"))
    print(f"Found {len(notes)} notes to classify")

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "filepath", "type", "title", "properties",
            "confidence", "reasoning",
        ])
        writer.writeheader()

        for i, note_path in enumerate(notes, 1):
            metadata = extract_note_metadata(note_path, vault)
            print(f"  [{i}/{len(notes)}] {metadata['filepath']}...")

            result = classify_note(metadata)

            writer.writerow({
                "filepath": metadata["filepath"],
                "type": result.get("type", "Note"),
                "title": result.get("title", metadata["filename"]),
                "properties": json.dumps(result.get("properties", {})),
                "confidence": result.get("confidence", "low"),
                "reasoning": result.get("reasoning", ""),
            })

            # Rate limiting: small delay between requests
            time.sleep(0.5)

    print(f"\nClassification complete. Results written to {output_csv}")
    print("IMPORTANT: Review the CSV before importing, especially low-confidence entries.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} /path/to/vault output.csv")
        sys.exit(1)
    if not API_KEY:
        print("Error: Set LLM_API_KEY environment variable")
        sys.exit(1)
    classify_vault(sys.argv[1], sys.argv[2])
```

Run it:

```bash
export LLM_API_KEY="sk-..."
export LLM_MODEL="gpt-4o"       # or any OpenAI-compatible model
python3 classify_vault.py /path/to/vault classifications.csv
```

> **Warning:** Always review the CSV before importing. Open it in a spreadsheet editor, sort by the `confidence` column, and manually correct any `low` confidence entries. The LLM is a starting point, not the final word.

---

## 5. Property Extraction and Mapping

Beyond type classification, the LLM can extract structured properties from note content. The classification script above already does basic property extraction in the prompt. This section explains the property mapping in more detail.

### Property mapping table

Map Obsidian frontmatter keys and extracted properties to SemPKM predicates:

| Obsidian Key | SemPKM Predicate | Applies To | Notes |
|-------------|-----------------|------------|-------|
| `title`, `name` | `dcterms:title` / `foaf:name` | All / Person | Use `dcterms:title` for Notes, Projects, Concepts. Use `foaf:name` for Persons. |
| `tags` | `urn:sempkm:model:basic-pkm:tags` | All | Comma-separated string |
| `status` | `urn:sempkm:model:basic-pkm:status` | Project | Must be one of: active, completed, on-hold, cancelled |
| `priority` | `urn:sempkm:model:basic-pkm:priority` | Project | Must be one of: low, medium, high, critical |
| `created`, `date` | `dcterms:created` | All | ISO 8601 date |
| `aliases` | `skos:altLabel` | All | Alternative names for the object |
| `type` (note type) | `urn:sempkm:model:basic-pkm:noteType` | Note | Must be one of: observation, idea, reference, meeting-note, journal |

> **Note:** Model-specific properties like `bpkm:status` must use the full namespace IRI (`urn:sempkm:model:basic-pkm:status`) in Command API calls. The `bpkm:` prefix is not available in the common prefix map. See [Appendix C: Command API Reference](appendix-c-command-api-reference.md) for the full list of recognized prefixes.

### Handling unmapped frontmatter keys

If your vault uses custom frontmatter keys that do not map to any existing predicate (e.g., `source_url`, `read_date`, `rating`), you have three options:

1. **Store as tags** -- convert the key-value pair into a tag string (e.g., `rating:5`) and include it in the `bpkm:tags` property.
2. **Skip it** -- log unmapped keys during import and revisit them later.
3. **Create a custom Mental Model** -- if the unmapped keys represent a coherent domain concept (like book reviews with rating, author, genre), create a new model with proper types and properties. See [Chapter 19: Creating Mental Models](19-creating-mental-models.md).

### Type-specific property extraction

For each type, the LLM can extract specific properties from the note body:

**Notes:**
- `noteType`: infer from content (meeting minutes -> `meeting-note`, personal reflection -> `journal`, factual reference -> `reference`)
- Related concepts: identify topic keywords for `bpkm:isAbout` edges
- Related people: identify mentioned names for cross-referencing

**Projects:**
- `status`: infer from language ("completed in March" -> `completed`, "putting on hold" -> `on-hold`)
- `priority`: infer from language ("urgent", "critical", "low priority")
- Start/end dates: extract from natural language mentions

**Persons:**
- `foaf:name`: extract the full name
- `schema:jobTitle`: extract role or title if mentioned
- `schema:worksFor`: extract organization if mentioned

**Concepts:**
- `skos:prefLabel`: the canonical name for the concept
- `dcterms:description`: a brief definition extracted from the note body
- Broader/narrower: identify hierarchical concept relationships

---

## 6. Relationship Extraction: Wiki-Links to Typed Edges

Converting Obsidian's untyped `[[wiki-links]]` into SemPKM's typed edges is the hardest part of the migration. A link from "Meeting 2024-01-15" to "Alice Chen" could be `hasParticipant`, `isAbout`, or something else entirely. The link itself carries no type information.

### Strategy 1: Infer edge type from source and target types

Once you have classified both the source and target notes, the relationship type often follows from the type pair:

| Source Type | Target Type | Likely Edge Predicate |
|-------------|-------------|----------------------|
| Project | Person | `urn:sempkm:model:basic-pkm:hasParticipant` |
| Note | Project | `urn:sempkm:model:basic-pkm:relatedProject` |
| Note | Concept | `urn:sempkm:model:basic-pkm:isAbout` |
| Note | Person | `urn:sempkm:model:basic-pkm:isAbout` (or a generic relation) |
| Concept | Concept | `skos:related` |
| Person | Project | `urn:sempkm:model:basic-pkm:participatesIn` |

This heuristic covers the majority of cases for Basic PKM imports.

### Strategy 2: Default to a generic relationship

If you cannot determine the edge type, use `skos:related` as a catch-all. You can refine these generic edges later in SemPKM's UI by editing each edge's predicate. This gets your data into SemPKM quickly even if the relationships are not perfectly typed.

### Strategy 3: LLM-assisted relationship typing

For higher-quality imports, send the sentence containing each link (plus the source and target types) to an LLM for classification.

**Relationship classification prompt:**

```
You are classifying the relationship between two knowledge base objects.

Source object:
- Type: {source_type}
- Title: {source_title}

Target object:
- Type: {target_type}
- Title: {target_title}

Sentence containing the link: "{sentence}"

Available relationship predicates:
- hasParticipant: a Project has a Person as participant
- participatesIn: a Person participates in a Project
- relatedProject: a Note is related to a Project
- isAbout: a Note is about a Concept or topic
- hasNote: a Project has a related Note
- skos:related: generic relationship between any two objects
- skos:broader: a Concept is broader than another Concept
- skos:narrower: a Concept is narrower than another Concept

Return a JSON object with:
- predicate: one of the predicates above
- confidence: high, medium, or low
- reasoning: brief explanation
```

### Resolving wiki-links to SemPKM IRIs

Obsidian `[[wiki-links]]` use note titles (or aliases) as identifiers. To create edges in SemPKM, you need to map these to object IRIs.

During import, build a lookup table from the classification CSV:

```python
# Build title -> IRI lookup from classification results
iri_lookup = {}
for row in classification_rows:
    obj_type = row["type"]    # e.g., "Person"
    slug = slugify(row["title"])  # e.g., "alice-chen"
    iri = f"https://example.org/data/{obj_type}/{slug}"
    iri_lookup[row["title"].lower()] = iri
    # Also index the original filename (without .md)
    iri_lookup[row["filepath"].rsplit("/", 1)[-1].replace(".md", "").lower()] = iri
```

When processing `[[wiki-links]]`, look up the target in this table. If the target is not found (i.e., the linked note does not exist in the vault), skip the edge and log a warning.

---

## 7. The Import Script: Putting It Together

This script reads the classification CSV, builds Command API payloads, and sends them to SemPKM in batches.

### Prerequisites

- A running SemPKM instance with Basic PKM installed
- An authenticated session (login via the browser and copy the session cookie, or use an API token)
- The classification CSV from step 4, reviewed and corrected
- Python 3.10+ with `requests` and `pyyaml` installed

### Complete import script

```python
#!/usr/bin/env python3
"""Import classified Obsidian notes into SemPKM via the Command API."""

import csv
import json
import os
import re
import sys
import requests
from pathlib import Path

# Configuration
SEMPKM_URL = os.environ.get("SEMPKM_URL", "http://localhost:3901")
SESSION_COOKIE = os.environ.get("SEMPKM_SESSION", "")
API_TOKEN = os.environ.get("SEMPKM_API_TOKEN", "")
BATCH_SIZE = 10  # Commands per batch (10-20 recommended)
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

# Predicate mappings (type -> title predicate)
TITLE_PREDICATES = {
    "Note": "dcterms:title",
    "Project": "dcterms:title",
    "Person": "foaf:name",
    "Concept": "skos:prefLabel",
}

# Type-pair -> edge predicate heuristic
EDGE_PREDICATES = {
    ("Project", "Person"): "urn:sempkm:model:basic-pkm:hasParticipant",
    ("Person", "Project"): "urn:sempkm:model:basic-pkm:participatesIn",
    ("Note", "Project"): "urn:sempkm:model:basic-pkm:relatedProject",
    ("Note", "Concept"): "urn:sempkm:model:basic-pkm:isAbout",
    ("Project", "Note"): "urn:sempkm:model:basic-pkm:hasNote",
}


def slugify(text: str) -> str:
    """Convert a title to a URL-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80] or "untitled"


def get_auth_headers() -> dict:
    """Build authentication headers."""
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    elif SESSION_COOKIE:
        headers["Cookie"] = f"sempkm_session={SESSION_COOKIE}"
    else:
        print("Error: Set SEMPKM_SESSION or SEMPKM_API_TOKEN")
        sys.exit(1)
    return headers


def send_batch(commands: list, headers: dict) -> dict:
    """Send a batch of commands to the Command API."""
    if DRY_RUN:
        print(f"  [DRY RUN] Would send {len(commands)} commands:")
        for cmd in commands:
            print(f"    {cmd['command']}: {json.dumps(cmd['params'], indent=None)[:120]}")
        return {"results": [{"iri": "dry-run", "command": c["command"]} for c in commands]}

    response = requests.post(
        f"{SEMPKM_URL}/api/commands",
        headers=headers,
        json=commands,
        timeout=60,
    )
    if response.status_code != 200:
        print(f"  ERROR {response.status_code}: {response.text[:300]}")
        return {"results": [], "error": response.text}
    return response.json()


def build_create_command(row: dict) -> tuple[dict, str]:
    """Build an object.create command from a classification row."""
    obj_type = row["type"]
    title = row["title"]
    slug = slugify(title)

    properties = {}

    # Set the title using the correct predicate for this type
    title_pred = TITLE_PREDICATES.get(obj_type, "dcterms:title")
    properties[title_pred] = title

    # Parse and apply extracted properties
    try:
        extra_props = json.loads(row.get("properties", "{}"))
    except json.JSONDecodeError:
        extra_props = {}

    if obj_type == "Note":
        if "noteType" in extra_props:
            properties["urn:sempkm:model:basic-pkm:noteType"] = extra_props["noteType"]
        if "tags" in extra_props:
            properties["urn:sempkm:model:basic-pkm:tags"] = extra_props["tags"]
    elif obj_type == "Project":
        if "status" in extra_props:
            properties["urn:sempkm:model:basic-pkm:status"] = extra_props["status"]
        if "priority" in extra_props:
            properties["urn:sempkm:model:basic-pkm:priority"] = extra_props["priority"]
    elif obj_type == "Person":
        if "jobTitle" in extra_props:
            properties["schema:jobTitle"] = extra_props["jobTitle"]
        if "worksFor" in extra_props:
            properties["schema:worksFor"] = extra_props["worksFor"]
    elif obj_type == "Concept":
        if "description" in extra_props:
            properties["dcterms:description"] = extra_props["description"]

    iri = f"{SEMPKM_URL.rstrip('/')}/data/{obj_type}/{slug}"
    command = {
        "command": "object.create",
        "params": {
            "type": obj_type,
            "slug": slug,
            "properties": properties,
        },
    }
    return command, iri


def build_body_command(iri: str, body_text: str) -> dict:
    """Build a body.set command for a note's content."""
    return {
        "command": "body.set",
        "params": {
            "iri": iri,
            "body": body_text,
        },
    }


def build_edge_command(source_iri: str, target_iri: str,
                       source_type: str, target_type: str) -> dict | None:
    """Build an edge.create command using the type-pair heuristic."""
    predicate = EDGE_PREDICATES.get(
        (source_type, target_type),
        "http://www.w3.org/2004/02/skos/core#related",  # fallback
    )
    return {
        "command": "edge.create",
        "params": {
            "source": source_iri,
            "target": target_iri,
            "predicate": predicate,
        },
    }


def import_vault(csv_path: str, vault_path: str) -> None:
    """Run the full import from classification CSV + vault directory."""
    headers = get_auth_headers()
    vault = Path(vault_path)

    # Phase 1: Read classification CSV and build IRI lookup
    rows = []
    iri_lookup = {}  # lowercase title -> (iri, type)
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
            slug = slugify(row["title"])
            iri = f"{SEMPKM_URL.rstrip('/')}/data/{row['type']}/{slug}"
            iri_lookup[row["title"].lower()] = (iri, row["type"])
            # Also index by filename stem
            filename_stem = row["filepath"].rsplit("/", 1)[-1].replace(".md", "")
            iri_lookup[filename_stem.lower()] = (iri, row["type"])

    print(f"Loaded {len(rows)} classifications, {len(iri_lookup)} lookup entries")

    # Phase 2: Create objects (batched)
    print("\n--- Phase 2: Creating objects ---")
    commands = []
    iri_list = []  # track IRIs in order for body.set phase

    for row in rows:
        cmd, iri = build_create_command(row)
        commands.append(cmd)
        iri_list.append((iri, row))

        if len(commands) >= BATCH_SIZE:
            print(f"  Sending batch of {len(commands)} object.create commands...")
            send_batch(commands, headers)
            commands = []

    if commands:
        print(f"  Sending final batch of {len(commands)} object.create commands...")
        send_batch(commands, headers)

    # Phase 3: Set body content (batched)
    print("\n--- Phase 3: Setting body content ---")
    commands = []
    for iri, row in iri_list:
        filepath = vault / row["filepath"]
        if not filepath.exists():
            continue

        text = filepath.read_text(encoding="utf-8", errors="replace")
        # Strip frontmatter to get body only
        body = re.sub(r"^---\n.*?\n---\n?", "", text, count=1, flags=re.DOTALL).strip()
        if not body:
            continue

        commands.append(build_body_command(iri, body))

        if len(commands) >= BATCH_SIZE:
            print(f"  Sending batch of {len(commands)} body.set commands...")
            send_batch(commands, headers)
            commands = []

    if commands:
        print(f"  Sending final batch of {len(commands)} body.set commands...")
        send_batch(commands, headers)

    # Phase 4: Create edges from wiki-links (batched)
    print("\n--- Phase 4: Creating edges from wiki-links ---")
    commands = []
    edges_created = 0
    edges_skipped = 0

    for iri, row in iri_list:
        filepath = vault / row["filepath"]
        if not filepath.exists():
            continue

        text = filepath.read_text(encoding="utf-8", errors="replace")
        links = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)

        source_type = row["type"]
        for link_target in links:
            target_key = link_target.strip().lower()
            if target_key in iri_lookup:
                target_iri, target_type = iri_lookup[target_key]
                edge_cmd = build_edge_command(iri, target_iri, source_type, target_type)
                if edge_cmd:
                    commands.append(edge_cmd)
                    edges_created += 1
            else:
                edges_skipped += 1

            if len(commands) >= BATCH_SIZE:
                print(f"  Sending batch of {len(commands)} edge.create commands...")
                send_batch(commands, headers)
                commands = []

    if commands:
        print(f"  Sending final batch of {len(commands)} edge.create commands...")
        send_batch(commands, headers)

    print(f"\n=== Import Complete ===")
    print(f"Objects created: {len(rows)}")
    print(f"Edges created: {edges_created}")
    print(f"Edges skipped (target not found): {edges_skipped}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} classifications.csv /path/to/vault")
        print(f"\nEnvironment variables:")
        print(f"  SEMPKM_URL       SemPKM instance URL (default: http://localhost:3901)")
        print(f"  SEMPKM_SESSION   Session cookie value (from browser)")
        print(f"  SEMPKM_API_TOKEN API token (alternative to session cookie)")
        print(f"  DRY_RUN=true     Preview commands without sending")
        sys.exit(1)
    import_vault(sys.argv[1], sys.argv[2])
```

### Running the import

First, do a dry run to verify the commands look correct:

```bash
export SEMPKM_URL="http://localhost:3901"
export SEMPKM_SESSION="your-session-cookie-value"
export DRY_RUN=true
python3 import_to_sempkm.py classifications.csv /path/to/vault
```

Then run for real:

```bash
export DRY_RUN=false
python3 import_to_sempkm.py classifications.csv /path/to/vault
```

> **Tip:** To get your session cookie, log in to SemPKM in your browser, open Developer Tools (F12), go to the Application tab, and copy the value of the `sempkm_session` cookie. Alternatively, generate an API token in **Settings > API Tokens** and use `SEMPKM_API_TOKEN` instead.

---

## 8. Post-Import Verification

After the import completes, verify that your data arrived correctly.

### Browse by type

Open the SemPKM workspace and expand each type in the Explorer tree. Check that the expected number of objects appear under each type (Note, Project, Person, Concept). Open a few objects and verify their properties and body content look correct.

### Check the validation panel

Open several imported objects and check the **Lint Panel** in the right pane. SHACL validation will flag any objects missing required properties. Common issues after import:

- Notes missing a `noteType` value
- Projects with invalid `status` or `priority` values (must match the allowed dropdown values exactly)
- Persons missing `foaf:name`

### SPARQL verification queries

Open the **SPARQL Console** (bottom panel) and run these queries to verify the import.

**Count objects by type:**

```sparql
SELECT ?type (COUNT(?s) AS ?count)
WHERE {
  GRAPH <urn:sempkm:current> {
    ?s a ?type .
  }
}
GROUP BY ?type
ORDER BY DESC(?count)
```

Compare the counts to your classification CSV totals. They should match.

**Find objects missing required properties:**

```sparql
SELECT ?s ?type
WHERE {
  GRAPH <urn:sempkm:current> {
    ?s a ?type .
    FILTER(?type = <urn:sempkm:model:basic-pkm:Note>)
    FILTER NOT EXISTS { ?s <http://purl.org/dc/terms/title> ?title }
  }
}
```

**List all edges and their types:**

```sparql
SELECT ?predicate (COUNT(*) AS ?count)
WHERE {
  GRAPH <urn:sempkm:current> {
    ?edge a <urn:sempkm:Edge> ;
          <urn:sempkm:predicate> ?predicate .
  }
}
GROUP BY ?predicate
ORDER BY DESC(?count)
```

### Use keyword search

Press **Ctrl+K** to open the command palette and search for terms you know exist in your imported notes. Verify that full-text search returns the expected results.

### Check the graph view

Open a Project or Concept in the graph view to see its connections. Verify that edges link to the expected targets. If you see many `skos:related` edges, consider reviewing and re-typing them in the edge editor.

---

## 9. Ongoing Workflow: Obsidian + SemPKM Side by Side

Many users will want to keep using Obsidian for quick daily capture while using SemPKM for structured, long-term knowledge management. Here is a practical approach.

### Capture in Obsidian, structure in SemPKM

Use Obsidian for what it does best -- fast, low-friction note capture. Write meeting notes, jot down ideas, save references. Then periodically (weekly or monthly) run the classification and import workflow on new notes to bring them into SemPKM with proper types and relationships.

### Incremental imports

The import script can be run on a subset of vault files. To import only notes created since the last import:

1. Filter the vault audit to files modified after a specific date.
2. Run the LLM classification on only the new files.
3. Run the import script with the filtered CSV.

> **Warning:** The import script creates new objects each time it runs. If you import the same note twice, you will get duplicate objects. Before re-importing, check whether the object already exists by title or slug.

### Browse SemPKM via WebDAV

You can mount SemPKM's virtual filesystem alongside your Obsidian vault to browse structured objects in your file manager. See [Chapter 23: Virtual Filesystem (WebDAV)](23-vfs.md) for mount instructions.

The WebDAV mount exposes each object as a Markdown file with YAML frontmatter, making it easy to compare your Obsidian originals with the structured SemPKM versions.

### Future possibilities

As SemPKM evolves, deeper integration points may become available:

- Webhook-triggered imports when vault files change
- Direct Obsidian plugin for live sync
- Bidirectional sync between Obsidian Markdown and SemPKM objects

For now, the batch import workflow described in this chapter is the recommended approach.

---

## See Also

- [Appendix C: Command API Reference](appendix-c-command-api-reference.md) -- full API specification for building import scripts
- [Chapter 19: Creating Mental Models](19-creating-mental-models.md) -- how to create custom types and properties for specialized vaults
- [Chapter 23: Virtual Filesystem (WebDAV)](23-vfs.md) -- mount SemPKM as a filesystem alongside Obsidian
- [Appendix F: FAQ](appendix-f-faq.md) -- answers to common questions about Obsidian compatibility and data import

---

**Previous:** [Chapter 23: Virtual Filesystem (WebDAV)](23-vfs.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
