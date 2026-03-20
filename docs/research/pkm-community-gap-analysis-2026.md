# SemPKM Gap Analysis: What the PKM Community Wants (March 2026)

Research compiled from Reddit (r/PKMS, r/ObsidianMD, r/logseq, r/Zettelkasten),
PKM blogs, YouTube communities, and industry analysis.

---

## Executive Summary

SemPKM already has a strong semantic/ontology foundation that most PKM tools lack
entirely. However, the community is moving fast — especially around AI agents,
frictionless capture, spaced repetition, and visual-spatial thinking. Below are
the gaps ranked by community demand and strategic fit for SemPKM.

---

## HIGH PRIORITY — Strong Community Demand, Strong SemPKM Fit

### 1. Agentic Knowledge Management (AKM)

**What the community wants:**
- AI that *proactively* monitors your knowledge base, not just responds to queries
- Auto-suggest connections between notes/objects you haven't explicitly linked
- Surface "forgotten" knowledge when contextually relevant
- AI proposes actions (link these, merge those, flag contradictions) — human approves
- Background inference that runs continuously, not just on-demand

**Where SemPKM stands:**
- Has LLM integration (configurable API, streaming chat proxy)
- Has OWL 2 RL inference engine (inverse, transitive, subclass, SHACL-AF rules)
- Has webhooks for event-driven automation
- Missing: proactive AI agent that watches changes and suggests actions

**Gap:**
- No AI agent loop that monitors `object.changed` / `edge.changed` events and
  proposes new edges, tags, or actions
- No "suggested connections" UI (e.g., "These 3 objects may be related because...")
- No semantic similarity / embedding-based discovery
- Inference is on-demand — not continuous/background
- No AI-generated summaries or digests of recent activity

**Recommendation:** Build an agentic layer on top of the existing webhook + LLM
infrastructure. Subscribe an AI agent to object change events, compute embeddings,
and surface suggestions in a dedicated panel. Leverage SPARQL + embeddings for
hybrid retrieval (GraphRAG pattern).

---

### 2. Semantic Search with AI (Beyond Keyword Matching)

**What the community wants:**
- "Find notes about decision-making under uncertainty" (not just keyword "decision")
- Understand intent and context, not just string matching
- Question-answering over your knowledge base ("What did I learn about X?")
- Cross-reference across object types (find a Note related to a Research Paper)

**Where SemPKM stands:**
- Has Lucene full-text search via RDF4J LuceneSail
- Has SPARQL for structured queries
- Has fuzzy toggle

**Gap:**
- No vector/embedding-based semantic search
- No natural language question answering
- No RAG (retrieval-augmented generation) over the knowledge base
- No "search by meaning" — only search by text match

**Recommendation:** Add an embedding pipeline (compute embeddings on object
create/update, store in a vector index). Implement hybrid search: SPARQL for
structured + vector for semantic + Lucene for full-text. Add a "Ask your KB"
chat interface that uses RAG over the graph.

---

### 3. Spaced Repetition & Active Review

**What the community wants:**
- Review workflows that resurface important knowledge at optimal intervals
- Flashcard generation from notes (especially AI-generated)
- Daily/weekly review dashboards showing what to revisit
- Integration with Zettelkasten-style progressive summarization
- "Don't just store it — help me remember it"

**Where SemPKM stands:**
- Has Zettelkasten+ mental model (FleetingNote → LiteratureNote → PermanentNote)
- Has PPV model with review cycles
- Has dashboards (custom layout, blocks)
- Missing: actual spaced repetition scheduling

**Gap:**
- No SM-2/FSRS scheduling algorithm
- No flashcard generation or review UI
- No "due for review" queue based on last-seen dates
- No daily review dashboard with algorithmically chosen items
- PPV "review cycles" exist in the model but lack automation

**Recommendation:** Add review metadata (last_reviewed, next_review, ease_factor)
to objects. Implement a review queue endpoint with SM-2 or FSRS scheduling. Build
a "Daily Review" dashboard block type. Optionally, let the LLM generate flashcards
from object content.

---

### 4. Quick Capture / Low-Friction Input

**What the community wants:**
- Capture a thought in <5 seconds from any context
- Voice-to-note (speak → transcribed → auto-categorized)
- Browser clipper (save web content with metadata)
- Email-to-note, chat-to-note integrations
- Mobile-first capture (SemPKM is currently desktop/web only)
- "Inbox" pattern — dump now, triage later

**Where SemPKM stands:**
- Object creation requires navigating to type picker → filling form
- Has API (`POST /api/commands`) which could power integrations
- Has WebDAV for file-based access
- No mobile app, no browser extension, no voice capture

**Gap:**
- No quick-capture endpoint (minimal input: just title + optional body)
- No inbox/triage workflow
- No browser extension or bookmarklet
- No voice/audio transcription pipeline
- No email-to-object integration
- Mobile experience is web-responsive at best

**Recommendation:** Build a minimal quick-capture API endpoint (`POST /api/capture`)
that accepts text/URL/voice and creates a typed object (default: FleetingNote or
Inbox item). Build a simple progressive web app (PWA) for mobile capture. Add a
browser bookmarklet/extension. Consider Whisper API integration for voice.

---

### 5. Better Graph Visualization

**What the community wants:**
- Heptabase-style spatial canvas where you arrange ideas visually
- Zoom-in for detail, zoom-out for big picture
- Filter graph by type, tag, date range, model
- Cluster detection (auto-group related nodes)
- Timeline/chronological graph views
- "Local graph" centered on current object with configurable depth

**Where SemPKM stands:**
- Has Cytoscape.js graph views with fcose/dagre layouts
- Has Canvas (drag-and-drop, wiki-links, neighbor loading)
- Has node/edge filtering and pan/zoom

**Gap:**
- No persistent spatial positions (Canvas sessions save, but graph views don't)
- No cluster detection or auto-grouping
- No timeline visualization
- No "local graph" view (N-hop neighborhood of current object)
- Canvas is lightweight but lacks the polish of Heptabase
- No minimap for large graphs
- No graph-level search/filter UI

**Recommendation:** Add a "local graph" panel to the workspace (show 1-2 hop
neighborhood of the current object). Add persistent node positions for graph views.
Implement type-based coloring and cluster detection. Add a timeline view that
plots objects on a date axis.

---

## MEDIUM PRIORITY — Growing Demand, Good Strategic Fit

### 6. AI-Powered Auto-Organization

**What the community wants:**
- Auto-tagging based on content analysis
- Suggested type/classification for new objects
- Duplicate/near-duplicate detection
- Auto-linking related objects on save
- Summarization of long notes

**Where SemPKM stands:**
- SHACL validation catches structural issues
- Has inference engine for ontological relationships
- LLM integration exists but isn't wired to auto-organize

**Gap:**
- No auto-tagging pipeline
- No duplicate detection
- No content-based type suggestion
- No auto-linking

**Recommendation:** Wire the LLM to a post-save hook: analyze new/updated objects,
suggest tags, detect duplicates via embedding similarity, propose edges. Show
suggestions in a non-intrusive panel.

---

### 7. Better Obsidian Import & Bidirectional Sync

**What the community wants:**
- Obsidian is the #1 PKM tool — seamless migration is critical
- Round-trip sync (edit in either tool)
- Support for Obsidian plugins' frontmatter conventions
- Dataview query compatibility or migration path
- Obsidian community has 50K+ Reddit subscribers

**Where SemPKM stands:**
- Has Obsidian vault import (ZIP upload, wiki-link resolution, property mapping)
- Has WebDAV (could enable bidirectional editing)
- Has VFS file browser

**Gap:**
- Import is one-way (no sync-back to Obsidian vault)
- No incremental sync (must re-import entire vault)
- No Dataview query migration
- WebDAV could theoretically enable bidirectional editing but isn't marketed/documented

**Recommendation:** Build incremental Obsidian sync via the WebDAV mount point.
Document the WebDAV + Obsidian vault workflow. Add a Dataview-to-SPARQL migration
guide.

---

### 8. Templates & Workflow Automation

**What the community wants:**
- Daily note templates that auto-populate with date, agenda, linked items
- Project kickoff templates
- Meeting notes → action items extraction
- Recurring review templates (weekly review, monthly review)
- "If this then that" automation rules

**Where SemPKM stands:**
- Has Workflows (multi-step, form/confirmation/display steps)
- Has SHACL shapes (which function as form templates)
- Has mental models with seed data
- Has webhooks (event-driven triggers)

**Gap:**
- No date-relative templates ("today's daily note")
- No natural language → action item extraction
- No recurring scheduled workflows
- No IFTTT-style automation rules
- Workflow builder exists but is underutilized

**Recommendation:** Add a "Daily Note" template type with auto-populated date
properties. Add cron-based workflow triggers. Wire LLM to extract action items
from meeting notes and create Task objects.

---

### 9. Markdown / WYSIWYG Editor Improvements

**What the community wants:**
- Obsidian-level markdown editing (live preview, syntax highlighting)
- Slash commands in editor (type `/` to insert blocks, embeds, references)
- Transclusion (embed one note inside another)
- Block references (link to a specific paragraph, not just a whole note)
- Table editing, callout blocks, mermaid diagrams

**Where SemPKM stands:**
- Has markdown body editing with incremental diff storage
- DOMPurify sanitization
- Wiki-link syntax in Canvas

**Gap:**
- Editor is basic compared to Obsidian/Notion
- No slash commands
- No transclusion/block references
- No live preview mode
- No mermaid diagram rendering
- No callout blocks

**Recommendation:** Adopt a richer editor framework (e.g., TipTap, Milkdown, or
BlockNote) that supports slash commands, block references, and embeds. Add wiki-link
autocompletion. Render mermaid diagrams inline.

---

### 10. Data Portability & Standards Compliance

**What the community wants:**
- EU Data Act (2025) mandates export within 30 days, no lock-in
- Plain-text / open format export (Markdown + frontmatter)
- RDF/JSON-LD export for interoperability
- Migration tools from/to other PKM tools
- "I should be able to leave with all my data"

**Where SemPKM stands:**
- Uses RDF (inherently interoperable standard)
- Has SPARQL endpoint (machine-readable access)
- Has WebDAV (filesystem-level access)
- Has Obsidian import
- Has VFS with markdown export

**Gap:**
- No one-click "export everything as Markdown+frontmatter" bulk export
- No JSON-LD export endpoint
- No import from Notion, Roam, Logseq, or other tools
- RDF is powerful but unfamiliar to most users — need user-friendly export

**Recommendation:** Add bulk export: Markdown + YAML frontmatter (familiar to
Obsidian users), JSON-LD (for linked data consumers), and CSV (for spreadsheet
users). Add import adapters for Notion (CSV/JSON), Logseq (EDN/MD), Roam (JSON).

---

## LOWER PRIORITY — Niche but Valuable

### 11. Collaboration UX Polish

**Where SemPKM stands:** Has multi-user auth, shared graphs, federation, comments,
invitations, notifications.

**Gap:** The collaboration features exist but the UX may lag behind Notion's
real-time co-editing. Missing: cursor presence, real-time typing indicators,
@-mentions, inline commenting on specific paragraphs.

---

### 12. Plugin / Extension Ecosystem

**What the community wants:** Obsidian's #1 strength is its plugin ecosystem
(1000+ community plugins). Users want extensibility without waiting for core devs.

**Where SemPKM stands:** Has Apps/Extensions with proxy forwarding, manifests, and
command palette integration.

**Gap:** No public plugin marketplace, no plugin SDK documentation, no community
contribution pipeline. The extension system exists but isn't accessible to the
community.

---

### 13. Presentation / Publishing Mode

**What the community wants:**
- Share a subset of your KB publicly (digital garden)
- Slide deck generation from notes
- Published web views of knowledge graphs
- Zettelkasten-style public hypertext

**Where SemPKM stands:** WebID profiles exist. No public publishing.

**Gap:** No "publish to web" feature. No digital garden output. No slide generation.

---

### 14. Calendar & Time-Based Views

**What the community wants:**
- Calendar view of tasks, meetings, deadlines
- Timeline view of project progress
- "On this day" retrospectives
- Integration with Google Calendar / CalDAV

**Where SemPKM stands:** No calendar views. Objects have timestamps but no
calendar visualization.

**Gap:** No calendar view, no CalDAV integration, no timeline visualization.

---

## Mental Model Specific Gaps

### Current Models vs. Community Demand

| Model | SemPKM Has | Community Wants More |
|-------|-----------|---------------------|
| Basic PKM | Notes, Projects, Concepts, Tasks | Daily notes, Inbox, Quick capture |
| PPV | Full 5-level hierarchy | Automated review scheduling |
| CRM | Contacts, Companies, Deals | Email integration, activity auto-logging |
| Research | Papers, Claims, Evidence | Citation management (BibTeX), PDF annotation |
| Zettelkasten+ | Fleeting→Literature→Permanent | Spaced repetition, AI-assisted progression |

### Models the Community Would Love

1. **Learning/Study Model** — Courses, Flashcards, LearningGoals, StudySessions
   with spaced repetition scheduling built in
2. **Health/Habits Model** — HabitTracker, DailyLog, Metrics, Goals with
   streak tracking and visualization
3. **Reading/Media Model** — Books, Articles, Podcasts, Videos with Readwise-style
   highlight resurfacing
4. **Decision Journal Model** — Decisions, Outcomes, Biases, LessonsLearned
   with structured reflection prompts
5. **PARA Model** (Tiago Forte) — Projects, Areas, Resources, Archives with
   automated lifecycle management

---

## Competitive Landscape Summary

| Feature | Obsidian | Notion | Heptabase | Capacities | **SemPKM** |
|---------|----------|--------|-----------|------------|------------|
| Semantic/RDF backbone | No | No | No | No | **Yes** |
| OWL inference | No | No | No | No | **Yes** |
| SHACL validation | No | No | No | No | **Yes** |
| Plugin ecosystem | 1000+ | Growing | Limited | Limited | Early |
| AI integration | Plugins | Built-in | Built-in | Built-in | Configurable |
| Agentic AI | No | No | No | No | **Not yet** |
| Spaced repetition | Plugin | No | No | No | **Not yet** |
| Mobile app | Yes | Yes | No | Yes | **No** |
| Quick capture | Good | Good | Limited | Good | **Weak** |
| Graph visualization | Basic | No | Excellent | No | Good |
| Spatial canvas | No | No | **Best** | No | Basic |
| Collaboration | Paid team | Excellent | Limited | Limited | Federation |
| Data portability | Excellent (MD) | Mediocre | Mediocre | Mediocre | **Good (RDF)** |
| SPARQL queries | No | No | No | No | **Yes** |
| Mental models | No | No | No | Object types | **Best** |

---

## Top 5 Recommendations (Ordered by Impact)

1. **Build an Agentic AI layer** — This is the next frontier. SemPKM's RDF
   backbone + inference engine + webhooks is the *perfect* foundation for GraphRAG
   and agentic knowledge management. No competitor has this yet.

2. **Add semantic/vector search + RAG** — "Ask your knowledge base" is the most
   requested AI feature. SemPKM's structured graph makes this *better* than
   competitors because you get grounded, traceable answers.

3. **Implement spaced repetition** — The Zettelkasten+ and PPV models are begging
   for this. Low engineering effort, high user value.

4. **Build quick capture (PWA + API)** — Reduce friction to zero. A 3-field form
   (title, body, type) accessible from mobile is table stakes.

5. **Enhance the editor** — The editing experience is where users spend 80% of
   their time. Slash commands, wiki-link autocomplete, and block references would
   dramatically improve daily UX.

---

## Sources

- [PKM Weekly Newsletter](https://www.pkmweekly.com)
- [Agentic Knowledge Management — Sébastien Dubois](https://www.dsebastien.net/agentic-knowledge-management-the-next-evolution-of-pkm/)
- [AI Graph-Based PKM — Theo James / Medium](https://medium.com/@theo-james/ai-graph-based-personal-knowledge-management-c0e09ac55654)
- [Obsidian Is Starting to Fall Behind — XDA Developers](https://www.xda-developers.com/obsidian-is-starting-to-fall-behind-alternatives/)
- [Obsidian's Plugin Dependency Problem — XDA Developers](https://www.xda-developers.com/i-still-use-obsidian-but-i-wish-theyd-fix-its-plugin-dependency/)
- [Best PKM Apps 2026 — ToolFinder](https://toolfinder.com/best/pkm-apps)
- [PKM Tools Compared — AFFiNE](https://affine.pro/blog/best-pkm-tool-review)
- [AI4PKM Project — Jykim](https://jykim.github.io/AI4PKM/)
- [Heptabase Public Roadmap](https://wiki.heptabase.com/roadmap)
- [GraphRAG & Knowledge Graphs for 2026 — Fluree](https://flur.ee/fluree-blog/graphrag-knowledge-graphs-making-your-data-ai-ready-for-2026/)
- [6 Agentic Knowledge Base Patterns — The New Stack](https://thenewstack.io/agentic-knowledge-base-patterns/)
- [The Year of the Knowledge Graph 2025 — Semantic Arts](https://www.semanticarts.com/the-year-of-the-knowledge-graph-2025/)
- [Top Knowledge Management Trends 2026 — Enterprise Knowledge](https://enterprise-knowledge.com/top-knowledge-management-trends-2026/)
- [Obsidian Review 2026 — The Business Dive](https://thebusinessdive.com/obsidian-review)
- [Audionotes — Voice-First PKM](https://www.audionotes.app/blog/best-personal-knowledge-management-tools)
- [PKM for Researchers 2026 — Atlas](https://www.atlasworkspace.ai/blog/pkm-apps-for-researchers)
- [Best Spaced Repetition Apps 2025 — PDF Flashcards](https://www.pdfflashcards.com/blog/spaced-repetition-apps)
