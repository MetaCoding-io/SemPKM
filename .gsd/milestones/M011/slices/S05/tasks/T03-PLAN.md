---
estimated_steps: 5
estimated_files: 4
---

# T03: Write user guide Chapter 29 (Mental Model Catalog) and update navigation

**Slice:** S05 — Cross-Model Verification, E2E Tests & User Guide
**Milestone:** M011

## Description

Write the user guide chapter documenting all 4 new/upgraded M011 mental models. This is the final documentation deliverable for the milestone. The chapter follows the established format (see Chapter 28 for style reference) and covers each model with type descriptions, field reference, relationships, installation instructions, saved queries, and recommended dashboard configurations (per D150 — dashboards can't be bundled in archives, so document recommended configs instead).

## Steps

1. **Write `docs/guide/29-mental-model-catalog.md`** with these sections:

   **Header and intro:**
   ```markdown
   # Chapter 29: Mental Model Catalog
   
   SemPKM ships with several mental models... This chapter documents
   the models available for installation...
   ```

   **Section 1: basic-pkm v2.0 — Project Management**
   - What's new in v2.0 (Task and Milestone types added to existing Project, Person, Note, Concept)
   - Task type: fields (title, body, status, priority, dueDate, effort, assignedTo, tags), enum values for status (todo/in-progress/blocked/done/cancelled) and priority (low/medium/high/critical)
   - Milestone type: fields (title, status, targetDate, tasks), enum values for milestoneStatus (planned/in-progress/completed/cancelled)
   - Relationships: Task↔Project (via milestone chain), Task↔Person (assignedTo/hasAssignedTask), Milestone↔Project
   - Saved queries: "My Open Tasks", "Overdue Tasks", "Blocked Tasks"
   - Validation: automatic warning for overdue tasks (past dueDate + status "todo")
   - Installation: already installed by default, v2.0 applied via Admin > Mental Models > Refresh
   - Recommended dashboard: sidebar with "My Open Tasks" list, main area with filtered task detail

   **Section 2: Personal CRM**
   - Overview: manage contacts, companies, interactions, and deals
   - Contact type: fields (name, email, phone, role, company, tags)
   - Company type: fields (name, industry, website, size, address)
   - Interaction type: fields (title, interactionType, date, withContact, notes, followUpDate)
   - Deal type: fields (title, stage, value, currency, dealContact, dealCompany, expectedCloseDate)
   - Pipeline concept: Deal stages form a pipeline (lead → qualified → proposal → negotiation → closed-won/closed-lost)
   - Relationships: Contact↔Company (worksAt/hasEmployee), Contact↔Interaction, Deal↔Contact, Deal↔Company
   - Saved queries: "Stale Contacts", "Open Deals", "Upcoming Follow-ups", "Network Map"
   - Validation: warning for contacts with no interactions recorded
   - Installation: `Admin > Mental Models > Install > /app/models/crm`
   - Recommended dashboard: sidebar with Contact list, main with recent Interactions

   **Section 3: Zettelkasten+**
   - Overview: structured note-taking with provenance chain and argumentation links
   - FleetingNote: quick capture, fields (title, body, tags, status)
   - Source: reference material, fields (title, sourceType, author, url, publicationDate)
   - LiteratureNote: summarizes a source, fields (title, body, source, pageReference)
   - PermanentNote: your own atomic idea, fields (title, body, tags, developedInto, derivedFrom)
   - StructureNote: organizes permanent notes, fields (title, body, includes)
   - Provenance chain: FleetingNote → Source → LiteratureNote → PermanentNote → StructureNote
   - Argumentation links between PermanentNotes: supports, contradicts, followsFrom, relatedTo
   - Saved queries: "Unprocessed Fleeting Notes", "Isolated Permanent Notes", "Contradiction Map", "Provenance Chain"
   - Validation: warning for unprocessed fleeting notes, warning for orphaned permanent notes
   - Installation: `Admin > Mental Models > Install > /app/models/zettelkasten`
   - Recommended dashboard: overview of unprocessed notes count + recent permanent notes

   **Section 4: Research Workflow**
   - Overview: academic/research knowledge management with evidence tracking
   - Paper: fields (title, authors, journal, year, doi, paperType, abstract)
   - Claim: fields (title, body, confidence level), confidence enum (established/likely/possible/speculative/contested)
   - Evidence: fields (title, body, evidenceType, strength, linkedPaper, linkedClaim)
   - ResearchQuestion: fields (title, body, status, relatedPapers)
   - Argument: fields (title, body, argumentType, supportsClaim, evidenceBasis)
   - Evidence tracking: each Claim can have multiple Evidence objects with type (supporting/refuting/ambiguous) and strength (strong/moderate/weak)
   - Saved queries: "Unsupported Claims", "Contested Claims", "Research Gaps", "Orphan Evidence", "High Confidence Claims", "Citation Network"
   - Validation: warning for unsupported claims (no evidence), info for contested claims (both supporting and refuting evidence), warning for orphan evidence, info for unanswered questions
   - Installation: `Admin > Mental Models > Install > /app/models/research`
   - Recommended dashboard: claims overview with evidence status

   **Footer navigation:**
   ```markdown
   ---
   **Previous:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
   ```

2. **Update `docs/guide/README.md` TOC** — add Chapter 29 entry in Part VIII:
   ```markdown
   29. [Mental Model Catalog](29-mental-model-catalog.md)
   ```
   Place it after entry 28 (Dashboards and Workflows), before Part IX.

3. **Update `docs/guide/28-dashboards-and-workflows.md` footer** — change the "Next:" link from Appendix A to Chapter 29:
   ```markdown
   **Previous:** [Chapter 27: Spatial Canvas](27-spatial-canvas.md) | **Next:** [Chapter 29: Mental Model Catalog](29-mental-model-catalog.md)
   ```

4. **Update `docs/guide/appendix-d-glossary.md`** — add alphabetically-sorted entries for new model types:
   - **Argument** — A structured reasoning unit connecting evidence to claims...
   - **Claim** — An assertion or proposition with a confidence level...
   - **Company** — An organization entity in the CRM model...
   - **Contact** — A person you interact with in the CRM model...
   - **Deal** — A potential business opportunity in the CRM model...
   - **Evidence** — Supporting or refuting data for a research claim...
   - **FleetingNote** — A quick capture note in the Zettelkasten model...
   - **Interaction** — A recorded touchpoint with a Contact in the CRM model...
   - **LiteratureNote** — A summary of a source in the Zettelkasten model...
   - **Milestone** — A project milestone with target date and linked tasks...
   - **Paper** — An academic paper or publication in the Research Workflow model...
   - **PermanentNote** — An atomic, self-contained idea in the Zettelkasten model...
   - **ResearchQuestion** — An open question to investigate in the Research Workflow model...
   - **StructureNote** — An organizing note that connects permanent notes in the Zettelkasten model...
   - **Task** — A work item with status, priority, and due date...
   
   Each entry should be 1-2 sentences with a cross-reference to Chapter 29.

5. **Verify navigation chain:**
   - Ch. 28 → Ch. 29 → Appendix A (forward links)
   - Ch. 29 → Ch. 28 (back link)
   - README.md lists Ch. 29

## Must-Haves

- [ ] `docs/guide/29-mental-model-catalog.md` exists with 4 model sections
- [ ] Each section covers: type descriptions, key fields, relationships, saved queries, validation warnings, installation
- [ ] README.md TOC includes Chapter 29
- [ ] Ch. 28 "Next:" link points to Ch. 29 (not Appendix A)
- [ ] Ch. 29 "Previous:" links to Ch. 28, "Next:" links to Appendix A
- [ ] Appendix D glossary has entries for at least 10 new model types

## Verification

- `test -f docs/guide/29-mental-model-catalog.md` — file exists
- `grep "29-mental-model-catalog" docs/guide/README.md` — listed in TOC
- `grep "29-mental-model-catalog" docs/guide/28-dashboards-and-workflows.md` — Ch. 28 links to Ch. 29
- `grep "appendix-a" docs/guide/29-mental-model-catalog.md` — Ch. 29 links to Appendix A
- `grep -c "Chapter 29" docs/guide/appendix-d-glossary.md` — at least 5 glossary entries reference Ch. 29

## Inputs

- `docs/guide/28-dashboards-and-workflows.md` — most recent chapter, current "Next:" points to Appendix A. Footer format: `**Previous:** [Chapter 27: Spatial Canvas](27-spatial-canvas.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)`
- `docs/guide/README.md` — TOC structure, Part VIII section contains entries 21-28
- `docs/guide/appendix-d-glossary.md` — alphabetical glossary with existing entries (ABox, Block, Carousel View, etc.)
- Model manifests and archives (for type/field reference):
  - `models/basic-pkm/manifest.yaml` — v2.0.0, 6 types, modelId `basic-pkm`
  - `models/crm/manifest.yaml` — v1.0.0, 4 types, modelId `crm`
  - `models/zettelkasten/manifest.yaml` — v1.0.0, 5 types, modelId `zettelkasten`
  - `models/research/manifest.yaml` — v1.0.0, 5 types, modelId `research`
- D150: Dashboards can't be bundled in model archives — document recommended configs instead
- Slice summaries S01-S04: type lists, field details, saved query names, validation rule descriptions

## Expected Output

- `docs/guide/29-mental-model-catalog.md` — Chapter 29 (~300-500 lines of markdown)
- `docs/guide/README.md` — Updated with Ch. 29 in TOC
- `docs/guide/28-dashboards-and-workflows.md` — Updated "Next:" navigation link
- `docs/guide/appendix-d-glossary.md` — ~15 new glossary entries for model types

## Observability Impact

- **Signals changed:** No runtime signals — this task produces documentation files only.
- **Inspection surfaces:** Navigation chain integrity can be verified via `grep` commands in the Verification section. Chapter 29 content accuracy can be cross-referenced against model manifest.yaml and shapes/*.jsonld files.
- **Failure visibility:** Broken navigation links surface as 404s when serving docs; missing glossary entries surface as undefined terms in the guide. Verification grep commands catch both before deployment.
