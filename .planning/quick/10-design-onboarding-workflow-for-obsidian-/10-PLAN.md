---
phase: 10-design-onboarding-workflow-for-obsidian
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/guide/24-obsidian-onboarding.md
autonomous: true
requirements: []

must_haves:
  truths:
    - "A reader can follow the onboarding guide from Obsidian vault to SemPKM objects end-to-end"
    - "The guide explains how to parse untagged Markdown notes into structured SemPKM objects"
    - "The guide presents a concrete LLM-assisted workflow for mapping unstructured text to ontology types and properties"
    - "The guide documents the Command API import path with working code examples"
    - "The guide addresses the core Obsidian-to-SemPKM gap: untyped wiki-links becoming typed edges"
  artifacts:
    - path: "docs/guide/24-obsidian-onboarding.md"
      provides: "Complete onboarding workflow guide for Obsidian users"
      min_lines: 200
  key_links:
    - from: "docs/guide/24-obsidian-onboarding.md"
      to: "docs/guide/appendix-c-command-api-reference.md"
      via: "Cross-reference to Command API for import scripting"
      pattern: "command-api|api/commands"
    - from: "docs/guide/24-obsidian-onboarding.md"
      to: "docs/guide/19-creating-mental-models.md"
      via: "Cross-reference for users who want custom ontologies"
      pattern: "creating-mental-models|Mental Model"
---

<objective>
Design and document a complete onboarding workflow for Obsidian users who want to migrate their untagged/poorly-structured notes into SemPKM's typed object database, including LLM-assisted ontology mapping.

Purpose: Obsidian users with large vaults of unstructured Markdown notes face a significant gap when adopting SemPKM -- their notes lack the type information, structured properties, and typed relationships that SemPKM requires. This guide bridges that gap with a practical, reproducible workflow.

Output: A new user guide chapter (docs/guide/24-obsidian-onboarding.md) that covers vault analysis, type mapping strategy, LLM-assisted classification, import scripting via the Command API, and relationship extraction.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md

Key codebase references for the executor:

- Command API: `POST /api/commands` accepts `object.create`, `object.patch`, `body.set`, `edge.create`, `edge.patch` commands. Single or batch (atomic). See `docs/guide/appendix-c-command-api-reference.md` for full spec.
- Mental Model structure: `manifest.yaml` + `ontology/*.jsonld` (OWL classes/properties) + `shapes/*.jsonld` (SHACL forms/validation) + `views/*.jsonld` + `seed/*.jsonld`. See `docs/guide/19-creating-mental-models.md`.
- Basic PKM types: Note (dcterms:title, bpkm:noteType, bpkm:isAbout, bpkm:relatedProject, bpkm:body), Project (dcterms:title, bpkm:status, bpkm:priority, bpkm:hasParticipant, bpkm:hasNote), Person (foaf:name, bpkm:participatesIn), Concept (skos:prefLabel, dcterms:description).
- VFS/WebDAV: `/dav/` endpoint presents objects as Markdown+frontmatter files. Write path (Phase 27) allows editing bodies via PUT. See `docs/guide/23-vfs.md`.
- LLM connection: Fernet-encrypted API key in InstanceConfig, SSE streaming proxy. See `backend/app/services/llm.py`.
- Label precedence: dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName fallback.
- Predicate resolution in commands: full IRIs used as-is, compact IRIs (dcterms:title) expanded via prefix map, bare local names prefixed with BASE_NAMESPACE.
- Value resolution: strings starting with http/https/urn treated as IRI references; other strings become RDF literals.
- Existing FAQ answer at `docs/guide/appendix-f-faq.md` acknowledges Obsidian interop question but defers to future work.

@docs/guide/appendix-c-command-api-reference.md
@docs/guide/19-creating-mental-models.md
@docs/guide/23-vfs.md
@docs/guide/appendix-f-faq.md
@models/basic-pkm/manifest.yaml
@models/basic-pkm/ontology/basic-pkm.jsonld
</context>

<tasks>

<task type="auto">
  <name>Task 1: Research codebase and design the onboarding workflow</name>
  <files>docs/guide/24-obsidian-onboarding.md</files>
  <action>
Research the SemPKM codebase to understand the full import surface, then design and write a comprehensive user guide chapter covering the Obsidian-to-SemPKM onboarding workflow. The document should be written as a user guide chapter (matching the tone and formatting of existing chapters in docs/guide/), NOT as an internal design document.

The chapter should cover these sections:

**1. Introduction: The Gap Between Obsidian and SemPKM**
- Obsidian: flat Markdown files, untyped [[wiki-links]], optional YAML frontmatter, tag-based organization
- SemPKM: typed RDF objects, typed edges (hasParticipant, isAbout), SHACL-driven forms, Mental Model ontologies
- The core challenge: most Obsidian vaults have hundreds of notes with no frontmatter, no consistent tagging, and untyped links -- these need to be classified, structured, and connected

**2. Vault Audit: Understanding What You Have**
- How to analyze an Obsidian vault before importing:
  - Count files by folder structure (often the only implicit "type" signal)
  - Identify frontmatter usage patterns (YAML keys, consistency)
  - Catalog [[wiki-link]] patterns (which notes link to which)
  - Identify tag usage (#tag patterns)
  - Estimate content types from folder names and note titles
- Provide a concrete Python script example that walks a vault directory, counts files per folder, extracts frontmatter keys, and catalogs link targets
- Output: a vault audit summary (N notes, M folders, K unique tags, L unique link targets, frontmatter coverage %)

**3. Choosing a Mental Model Strategy**
- Three approaches depending on vault structure:
  - **Option A: Use Basic PKM as-is** -- Map notes to Note/Project/Person/Concept types. Best for general-purpose vaults.
  - **Option B: Extend Basic PKM** -- Add custom types to Basic PKM's ontology for domain-specific notes (e.g., Recipe, Book, Meeting). Explain this is NOT currently supported (models are immutable after install) but you can create a new model that imports Basic PKM's namespace.
  - **Option C: Create a custom Mental Model** -- For highly specialized vaults (research, legal, medical). Reference Chapter 19 for the full model author guide.
- Decision heuristic: If >80% of notes map cleanly to Note/Concept/Project/Person, use Option A. Otherwise, consider Option C.

**4. LLM-Assisted Type Classification**
- The manual approach is impractical for vaults with 500+ notes
- Design a workflow where an LLM reads each note's title, first ~500 chars of body, folder path, tags, and frontmatter, then classifies it into one of the target Mental Model types
- Provide a concrete prompt template for the LLM:
  ```
  You are classifying Obsidian notes for import into a structured knowledge base.
  Available types: Note, Project, Person, Concept

  For each note, return a JSON object with:
  - type: one of [Note, Project, Person, Concept]
  - title: the best title for this object
  - properties: key-value pairs matching the target type's schema
  - confidence: high/medium/low
  - reasoning: brief explanation

  Note to classify:
  - File: {filename}
  - Folder: {folder_path}
  - Tags: {tags}
  - Frontmatter: {frontmatter_yaml}
  - Content preview: {first_500_chars}
  ```
- Explain how to batch-process via the OpenAI-compatible API (which SemPKM's LLM config already supports)
- Provide a Python script skeleton that: reads vault files, sends classification prompts, collects results, writes a classification CSV for human review
- Emphasize the REVIEW step: LLM output should be reviewed before import, especially low-confidence classifications

**5. Property Extraction and Mapping**
- Beyond type classification, the LLM can extract structured properties:
  - For Notes: extract noteType (observation/idea/reference/meeting-note/journal), identify related concepts, extract mentioned people
  - For Projects: extract status, priority, dates from natural language ("started in January", "high priority")
  - For Persons: extract name, job title, organization from note content
  - For Concepts: extract prefLabel, description, broader/narrower concepts
- Map Obsidian frontmatter keys to SemPKM predicates (table of common mappings):
  - `title` / `name` -> dcterms:title / foaf:name (depending on type)
  - `tags` -> bpkm:tags
  - `status` -> bpkm:status
  - `created` / `date` -> dcterms:created
  - `aliases` -> skos:altLabel
- Handle the case where frontmatter has custom keys not in the ontology (log them, suggest extending the model or using tags)

**6. Relationship Extraction: Wiki-Links to Typed Edges**
- The hardest part: Obsidian [[wiki-links]] are untyped, SemPKM edges are typed
- Strategy 1: Infer edge type from context -- "Alice [[participated in]] the [[Project X]]" suggests hasParticipant
- Strategy 2: Default edge type (skos:related or a generic bpkm:relatedTo) with manual refinement later
- Strategy 3: LLM-assisted relationship typing -- send the sentence containing the link plus the source/target types, ask the LLM to classify the relationship
- Provide an LLM prompt template for relationship classification
- Explain how [[wiki-links]] need to be resolved to SemPKM IRIs (match by title/label, handle disambiguation)

**7. The Import Script: Putting It Together**
- Provide a complete, working Python import script that:
  1. Reads the classification CSV (from step 4)
  2. Builds Command API payloads (object.create + body.set for each note)
  3. Resolves [[wiki-links]] to edge.create commands
  4. Sends batched commands to POST /api/commands
  5. Handles errors and reports results
- Use the actual SemPKM Command API format from appendix-c (object.create with type, slug, properties; body.set with iri and body; edge.create with source, target, predicate)
- Show how to authenticate (session cookie from login)
- Show batch sizes (recommend 10-20 commands per batch to avoid timeouts)
- Include proper error handling and a dry-run mode

**8. Post-Import Verification**
- How to verify the import worked:
  - Browse objects in the SemPKM workspace by type
  - Check validation lint panel for missing required fields
  - Use SPARQL Console to count objects by type and verify totals match vault counts
  - Use graph view to visualize relationship structure
  - Use FTS keyword search to spot-check content
- Provide example SPARQL queries for verification:
  - Count objects by type
  - Find objects missing required properties
  - List all edges and their types

**9. Ongoing Workflow: Obsidian + SemPKM Side by Side**
- For users who want to keep using Obsidian for capture and SemPKM for structured knowledge:
  - Capture in Obsidian -> periodic batch import to SemPKM
  - Use VFS/WebDAV mount to browse SemPKM objects in a file manager alongside Obsidian
  - Future: webhook-triggered imports when files change
- Reference the VFS chapter (23-vfs.md) for WebDAV mount instructions

**Formatting and style requirements:**
- Follow the existing chapter style in docs/guide/ (see chapters 01-23 for reference)
- Use `---` section breaks between major sections
- Use proper Markdown headers (## for sections, ### for subsections)
- Use admonition-style callouts (> **Tip:**, > **Note:**, > **Warning:**)
- Include cross-references to other chapters ([Chapter 19](19-creating-mental-models.md), [Appendix C](appendix-c-command-api-reference.md))
- Include a "See Also" section at the end
- Include Previous/Next navigation links at the bottom
- Code examples should be complete and runnable (Python 3.10+, using only requests and pyyaml as dependencies)
- All Command API examples must match the exact format in appendix-c-command-api-reference.md

**What NOT to include:**
- Do not design or propose any new SemPKM features, APIs, or code changes
- Do not suggest changes to the Mental Model format
- Do not write implementation code for SemPKM itself
- This is purely a user-facing workflow guide using existing capabilities
  </action>
  <verify>
    <automated>test -f docs/guide/24-obsidian-onboarding.md && wc -l docs/guide/24-obsidian-onboarding.md | awk '{if ($1 >= 200) print "PASS: " $1 " lines"; else print "FAIL: only " $1 " lines"}'</automated>
  </verify>
  <done>
    - docs/guide/24-obsidian-onboarding.md exists with 200+ lines
    - Chapter covers all 9 sections: introduction, vault audit, model strategy, LLM classification, property extraction, relationship extraction, import script, post-import verification, ongoing workflow
    - Contains working Python code examples for vault audit, LLM classification, and Command API import
    - Contains LLM prompt templates for type classification and relationship typing
    - Cross-references appendix-c (Command API), chapter 19 (Creating Mental Models), chapter 23 (VFS)
    - Follows existing guide formatting conventions (headers, admonitions, See Also, nav links)
  </done>
</task>

<task type="auto">
  <name>Task 2: Update FAQ and guide index to reference the new chapter</name>
  <files>docs/guide/appendix-f-faq.md, docs/guide/README.md</files>
  <action>
Update two existing files to reference the new onboarding chapter:

1. **docs/guide/appendix-f-faq.md** -- Update the two relevant FAQ entries:
   - "Can I use SemPKM with Obsidian?" -- Add a sentence at the end of the answer pointing to the new chapter: "For a complete walkthrough of migrating an Obsidian vault to SemPKM, see [Chapter 24: Obsidian Onboarding](24-obsidian-onboarding.md)."
   - "Can I import data from other tools?" -- Add a sentence referencing the new chapter for Obsidian-specific imports: "For a step-by-step Obsidian vault migration guide including LLM-assisted classification, see [Chapter 24: Obsidian Onboarding](24-obsidian-onboarding.md)."

2. **docs/guide/README.md** -- Add the new chapter to the table of contents / index listing in the appropriate position (after chapter 23, before the appendices). Add it as:
   - `24. [Obsidian Onboarding](24-obsidian-onboarding.md)` or similar, matching the existing listing format.

Read both files first to understand their current structure before making changes.
  </action>
  <verify>
    <automated>grep -c "24-obsidian-onboarding" docs/guide/appendix-f-faq.md docs/guide/README.md | grep -v ":0$" | wc -l | awk '{if ($1 >= 2) print "PASS: both files reference new chapter"; else print "FAIL: missing references"}'</automated>
  </verify>
  <done>
    - appendix-f-faq.md Obsidian FAQ entry links to chapter 24
    - appendix-f-faq.md import FAQ entry links to chapter 24
    - README.md index includes the new chapter 24 in correct position
  </done>
</task>

</tasks>

<verification>
1. `docs/guide/24-obsidian-onboarding.md` exists and is a substantial guide (200+ lines)
2. The guide contains Python code examples (vault audit script, LLM classification script, import script)
3. The guide contains LLM prompt templates
4. The guide references the Command API format correctly (object.create, body.set, edge.create)
5. FAQ entries in appendix-f-faq.md link to the new chapter
6. README.md index includes the new chapter
</verification>

<success_criteria>
- A reader with an Obsidian vault can follow the guide from vault audit through import to verification
- Code examples are complete and use the actual SemPKM Command API format
- LLM prompt templates are concrete and ready to use
- The document fits naturally into the existing user guide structure
- Cross-references to Command API, Mental Model creation, and VFS chapters are present
</success_criteria>

<output>
After completion, create `.planning/quick/10-design-onboarding-workflow-for-obsidian-/10-SUMMARY.md`
</output>
