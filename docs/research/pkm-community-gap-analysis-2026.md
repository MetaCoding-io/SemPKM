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

## Key Strategic Insights (from deep-dive research)

### The Obsidian Dataview Problem — SemPKM's Biggest Opportunity

Obsidian's Dataview plugin is one of the most-used and most-hated plugins in the
ecosystem. Its pain points are *exactly* what SemPKM solves:

- DQL syntax has a steep learning curve (looks like SQL but isn't)
- Cannot query note *contents*, only indexed YAML frontmatter metadata
- Not interactive — view-only, cannot edit data inline from query results
- Performance degrades with large vaults
- No hierarchical/nested data support — flat metadata only
- Main developer is inactive; Obsidian's new Bases feature is still immature

**SemPKM's SPARQL over RDF triples is infinitely more powerful than DQL over
frontmatter.** This should be a key marketing message: "You wanted structured
data in your PKM? Here's what a real type system looks like."

### Mental Models as Software — A Blue Ocean

No existing tool treats mental models as structured, interconnected, *applicable*
knowledge objects. The landscape:

- **ModelThinkers** — searchable library + "playbooks" combining models, but
  content-only, not connected to your notes/decisions
- **M-Tool** — academic causal diagram mapping, not PKM-integrated
- **Mental Modeler** — fuzzy-logic cognitive mapping for group decision-making
- **Farnam Street** — ~100 models explained, pure content

What's missing (and what SemPKM could uniquely provide):
- Apply mental models to your own knowledge/decisions and track results
- Connect models to actual notes, projects, and decisions
- AI suggests relevant models based on the problem you're working on
- Capture model relationships (X is a special case of Y, A contradicts B in context C)
- Build a personal "latticework" (Munger's concept) that grows with you

### Ontology-Aware Spaced Repetition — Nobody Has This

Current SRS tools schedule individual cards independently. An ontology-aware SRS
could schedule reviews based on concept *relationships*:
- Reviewing a parent concept reinforces child concepts
- A weakly-recalled concept triggers review of related concepts
- Edge types inform scheduling (contradicting claims need more review than supporting ones)
- SHACL shapes could define "what constitutes mastery" per type

### The Academic Semantic PKM Legacy

Academic prototypes (SemperWiki, PlatypusWiki, WANT) validated the RDF+wiki
approach 15+ years ago but never delivered consumer-grade UX. SemPKM is the first
tool to bridge this gap — delivering semantic web power with modern UX.

### Markdown-LD — A Bridge Format

**Markdown-LD** and **MD-LD** are emerging tools that embed RDF triples in Markdown
files. This could bridge SemPKM's RDF world with the Markdown-loving PKM community,
enabling round-trip sync with Obsidian vaults while preserving semantic structure.

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

## Cross-Cutting Strategic Themes

1. **Structure is the moat** — Every trend (agentic AI, GraphRAG, spaced repetition,
   collaboration) points toward more structure. SemPKM's ontology-first approach is
   perfectly positioned for all of them.

2. **The UX gap is the real barrier** — Semantic web tech has been academically
   validated for 20+ years. What's missing is consumer-grade UX. The tools that win
   (Obsidian, Notion) win on UX, not data model sophistication.

3. **GraphRAG is the bridge to AI** — Combining knowledge graphs with RAG is the
   hottest area in AI+knowledge. SemPKM's RDF graph is directly usable for GraphRAG
   without transformation.

4. **Interoperability via RDF is a real differentiator** — While others fight over
   Markdown vs proprietary formats, RDF/JSON-LD/Turtle provides true semantic
   interoperability. Markdown-LD could bridge the communities.

5. **Mental models as ontology objects is a blue ocean** — No existing tool treats
   mental models as structured, interconnected, applicable knowledge objects.

6. **Enterprise KM is converging with personal KM** — The same semantic layer
   infrastructure enterprises are building (RDF, knowledge graphs, SPARQL) is what
   SemPKM already uses for personal knowledge. This bridge is unoccupied.

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
- [Dataview vs Datacore vs Obsidian Bases — Obsidian Rocks](https://obsidian.rocks/dataview-vs-datacore-vs-obsidian-bases/)
- [A Case Against Dataview — Obsidian Forum](https://forum.obsidian.md/t/a-case-against-dataview-a-story/82210)
- [Enhance Obsidian with a Type System — Obsidian Forum FR](https://forum.obsidian.md/t/super-fr-enhance-obsidian-with-a-type-system-for-notes-and-database-like-views-metadata-object-oriented-model/46444)
- [ModelThinkers — Munger's Latticework](https://modelthinkers.com/mental-model/mungers-latticework)
- [M-Tool: Mental Model Mapping Tool](https://m-tool.org/)
- [Markdown-LD — GitHub](https://github.com/ozekik/markdown-ld)
- [Semantic Wikis for PKM — Springer](https://link.springer.com/chapter/10.1007/11827405_50)
- [FSRS Has Made SRS Way Better — Domenic Denicola](https://domenic.me/fsrs/)
- [Effective Spaced Repetition — Borretti](https://borretti.me/article/effective-spaced-repetition)
- [Enterprise KM Trends 2025 — Enterprise Knowledge](https://enterprise-knowledge.com/top-knowledge-management-trends-2025/)
- [AgenticAKM — arXiv](https://arxiv.org/html/2602.04445v1)
- [Logseq Project Status Discussion](https://discuss.logseq.com/t/logseq-project-status/28849/20)
- [Building the Fastest Capture — Memotron](https://docs.memotron.app/blog/fastest-pkm-capture)
- [Knowledge Graph Tools 2026 — Atlas Blog](https://www.atlasworkspace.ai/blog/knowledge-graph-tools)

---
---

# Deep Dive: Agentic AI & Semantic Search for SemPKM

Detailed technical research into the two highest-priority opportunities:
proactive AI agents and "ask your knowledge base" semantic search.

---

## Part A: Agentic AI — Making SemPKM Proactive

### What "Agentic AI" Means in PKM Context

The shift is from **reactive** (user asks → AI answers) to **proactive** (AI monitors,
surfaces, suggests, acts). Concrete behaviors users want:

1. **Auto-surfacing**: "You wrote about this 3 months ago and never followed up"
2. **Auto-linking**: AI detects implicit connections between objects you haven't linked
3. **Knowledge curation**: "5 notes overlap on React state management — consolidate?"
4. **Contextual suggestions**: Writing a decision doc → AI suggests relevant mental models
5. **Contradiction detection**: "You said X here but Y there — which is current?"
6. **Gap identification**: "You're learning systems thinking but haven't connected it to any project"

### What Competitors Are Doing

| Tool | Capability | Limitation |
|------|-----------|------------|
| **Mem.ai** | Auto-organizes notes, temporal awareness, proactive surfacing | Closed-source, no structured data, no user ontology |
| **Notion AI** | Q&A over workspace, auto-fill DB properties, Slack/Drive connectors | Reactive only, treats everything as text |
| **Khoj** | Self-hosted RAG over notes, multi-modal search | No graph structure, no proactive behavior |
| **Obsidian Copilot** | Chat over vault, vector search | Plugin, not integrated; no graph awareness |
| **Fabric** (Daniel Miessler) | AI "patterns" as prompt templates for processing any content | Framework, not a PKM tool; no persistence |

**Key insight**: Nobody combines structured knowledge graph + proactive AI. All are
either text-only (Mem, Notion) or graph-only without AI (existing SemPKM).

### MCP (Model Context Protocol) and PKM

Anthropic's MCP creates a standard protocol for AI ↔ tool communication. Relevant MCP
servers already exist: obsidian-mcp, filesystem-mcp, sqlite-mcp, knowledge-graph-mcp.

**For SemPKM**: An MCP server exposing the SPARQL endpoint + command API would let any
MCP-compatible AI client (Claude, etc.) directly read from and write to SemPKM. This
is a leverage point — instead of building all AI features internally, expose SemPKM as
an MCP resource that external agents can use.

### Why SemPKM Has a Structural Advantage

**The GraphRAG shortcut**: Microsoft's GraphRAG (2024) and LightRAG (2024) both start
by using LLMs to *extract* a knowledge graph from unstructured text. This is:
- Expensive (many LLM calls per document)
- Lossy (extraction misses nuance)
- Error-prone (hallucinated entities/relations)
- Requires re-indexing when content changes

**SemPKM already has the graph.** User-validated, schema-aware, with OWL inference.
The entire expensive extraction step is skipped. SemPKM goes straight to graph-based
retrieval with clean structure.

### Architecture: SemPKM Agentic AI

```
┌─────────────────────────────────────────────────────────┐
│                    SemPKM Agent Loop                     │
│                                                         │
│  Triggers:                                              │
│  ├─ Event (object.create, edge.create, body.set)       │
│  ├─ Schedule (daily digest, weekly review)              │
│  └─ User request (chat, slash command)                  │
│                                                         │
│  Agent Tools:                                           │
│  ├─ sparql_query(q)    — read from knowledge graph     │
│  ├─ text_search(q)     — full-text search over bodies  │
│  ├─ vector_search(q)   — semantic similarity search    │
│  ├─ browse_ontology()  — read class/property defs      │
│  ├─ commands(batch)    — create/patch objects & edges   │
│  ├─ validate_shacl(o)  — check shape constraints       │
│  └─ suggest_model(ctx) — recommend mental models       │
│                                                         │
│  Output:                                                │
│  ├─ Suggestions (user approves before execution)       │
│  ├─ Notifications (surfaced knowledge, reminders)      │
│  └─ Direct answers (Q&A, summaries)                    │
└─────────────────────────────────────────────────────────┘
```

**Event-driven flow** (leveraging existing WebhookService):
1. User creates/edits an object → EventStore commits event
2. WebhookService dispatches to AI agent endpoint
3. Agent runs: SPARQL to find related objects, vector search for semantic neighbors
4. Agent proposes: "Link this to Project X? Apply SWOT Analysis model?"
5. Proposals appear in a notification/suggestion panel — user accepts or dismisses

### Concrete Agent Behaviors for SemPKM

**Tier 1 — Low-hanging fruit (existing infrastructure):**
- **Auto-classify captures**: Browser extension sends raw text → agent suggests type + properties
- **Link suggestions**: On object create, SPARQL + embeddings find related objects → suggest edges
- **SHACL gap detection**: "This Decision has no rationale property filled in"
- **Stale knowledge alerts**: Objects not updated in N days with open status

**Tier 2 — Medium complexity:**
- **Mental model suggestions**: Given a Decision object's context, suggest applicable models
- **Knowledge consolidation**: Detect near-duplicate objects via embeddings, propose merge
- **Weekly digest**: "This week you created 12 objects. 3 are unlinked. 2 decisions lack rationale."
- **Contradiction detection**: OWL consistency checking + LLM analysis of conflicting body text

**Tier 3 — Advanced:**
- **Research assistant**: "I'm exploring topic X" → agent finds gaps in your graph, suggests readings
- **Pattern recognition**: "Your last 5 architecture decisions all used the same 2 mental models"
- **Predictive linking**: Graph embedding models predict missing edges before the user thinks of them
- **Multi-user knowledge fusion**: In federated setup, surface relevant knowledge from other graphs

---

## Part B: Semantic Search — "Ask Your Knowledge Base"

### Current State of PKM Search

Every tool does text-based RAG: chunk notes → embed → vector search → LLM answer.
This works for "What did I write about X?" but fails for:

- **Structural queries**: "List all projects and their status" (needs SPARQL, not vector search)
- **Multi-hop reasoning**: "What mental models apply to my active projects?" (needs graph traversal)
- **Aggregation**: "How many decisions did I make this quarter?" (LLM counting is unreliable)
- **Temporal queries**: "What changed since my last review?" (timestamps in triples, not text)
- **Completeness**: Vector top-k may miss relevant items; SPARQL returns ALL matches

### SemPKM's Dual-Channel Architecture

```
User query: "What mental models have I used for architecture decisions?"

┌──────────────────┐
│  Query Router     │  LLM classifies query type
└────┬────────┬────┘
     │        │
     ▼        ▼
┌─────────┐ ┌──────────────┐
│ SPARQL  │ │ Vector Search │
│ Channel │ │ Channel       │
└────┬────┘ └──────┬───────┘
     │              │
     ▼              ▼
Structured      Semantic
results:        results:
exact matches   fuzzy matches
from triples    from body text
     │              │
     └──────┬───────┘
            ▼
    ┌──────────────┐
    │ Fusion &     │  Merge, deduplicate, rerank
    │ Reranking    │
    └──────┬───────┘
            ▼
    ┌──────────────┐
    │ LLM Answer   │  Synthesize with citations
    │ Generation   │  (clickable object links)
    └──────────────┘
```

### Text-to-SPARQL: Natural Language → Graph Queries

Research shows GPT-4/Claude achieve ~80% accuracy on SPARQL generation when given
the ontology schema. The approach:

1. **System prompt includes**: All classes, properties, ranges from installed mental models
2. **Few-shot examples**: 5-10 common query patterns for SemPKM's ontology
3. **Validation step**: Parse generated SPARQL before execution; retry on syntax error
4. **Fallback**: If SPARQL generation fails, fall back to vector search

**Example flow:**
```
User: "What books did I read about systems thinking?"

LLM generates:
  SELECT ?book ?title WHERE {
    ?book a pkm:Book ;
          dcterms:title ?title ;
          pkm:hasTopic ?topic .
    ?topic rdfs:label ?topicLabel .
    FILTER(CONTAINS(LCASE(?topicLabel), "systems thinking"))
  }

Execute against RDF4J → structured results → format answer
```

**SemPKM advantage**: The ontology schema is already well-defined (SHACL shapes provide
exact property names, types, cardinalities). This is exactly what the LLM needs to
generate correct SPARQL.

### Entity-Centric Retrieval (vs Chunk-Based)

Standard RAG chunks documents into 500-token pieces. This is arbitrary and lossy.
SemPKM can use **entity-centric retrieval** — each RDF object is a natural unit:

```
For entity <urn:sempkm:obj:Decision_123>:
  Type:       Decision
  Properties: title, date, status, rationale
  Body:       Markdown text (full content)
  Outgoing:   relatedTo Project_A, usedModel SWOT_Analysis
  Incoming:   reviewedBy Person_B, partOf Sprint_7
  Inferred:   also instance of TrackedItem (via OWL subclass)
```

This assembled context is richer than any text chunk because it includes **structure**
(type, properties, edges) alongside **content** (body text).

### OWL Inference as Retrieval Amplifier

OWL reasoning automatically expands queries:

| Inference Type | Example | Retrieval Effect |
|---------------|---------|-----------------|
| **Subclass** | Book ⊂ LearningResource | Query for "learning resources" also returns books |
| **Transitive** | A partOf B, B partOf C | Query for "parts of C" also returns A |
| **Inverse** | authorOf ↔ writtenBy | Store one direction, query both |
| **Domain/Range** | hasTopic → Concept | AI knows valid targets for relationships |

This is **free retrieval expansion** — no extra embeddings, no extra LLM calls.
The reasoner has already materialized inferred triples in `urn:sempkm:inferred`.

### Hybrid Retrieval: Best of Both Worlds

**Phase 1 — Seed discovery** (parallel):
- SPARQL: Find structurally matching entities (type, properties, edges)
- Vector: Find semantically similar body text (embeddings cosine similarity)

**Phase 2 — Context expansion**:
- For each seed entity, traverse graph 1-2 hops
- Gather: type info, direct properties, related entities, incoming edges

**Phase 3 — Reranking**:
- Score by: embedding similarity + graph distance + type relevance
- Return top-k with full entity context

### Grounded, Traceable Answers

Unlike text-only RAG where sources are vague ("from your notes"), SemPKM can provide:
- **Clickable object links**: Each citation links to the specific object in the workspace
- **Triple-level provenance**: "This answer is based on 3 triples: [Decision_123 usedModel SWOT], ..."
- **Query transparency**: Show the SPARQL query that was executed (for power users)
- **Confidence signals**: SPARQL results = 100% certain; vector results = similarity score

---

## Part C: Slash Commands for SemPKM's Editor

Based on the current CodeMirror 6 editor and workspace architecture, here are
slash commands ranked by value and implementation feasibility.

### Tier 1 — High Value, Straightforward Implementation

These leverage existing API endpoints and services.

| Command | Action | Implementation |
|---------|--------|---------------|
| `/link` | Search objects, insert `[[Object Title]]` wiki-link | RDF4J Lucene search → picker UI → insert markdown link |
| `/type` | Change object's RDF type | Show installed types → PATCH via commands API |
| `/tag` | Add/remove tags on current object | Autocomplete from existing tags → edge.create |
| `/template` | Insert template for current type | SHACL shape → generate markdown scaffolding |
| `/relate` | Create edge to another object | Object picker → edge type picker → edge.create |
| `/status` | Quick-set status property | Dropdown of valid values (from SHACL sh:in) |

### Tier 2 — Medium Complexity, High Value

These require new backend capabilities or LLM integration.

| Command | Action | Implementation |
|---------|--------|---------------|
| `/ask` | Ask a question about your knowledge base | Text-to-SPARQL + vector search → LLM answer |
| `/summarize` | Summarize current object or linked objects | Gather entity context → LLM summarize |
| `/suggest-links` | AI suggests related objects to link | Embeddings + SPARQL → show candidates |
| `/suggest-model` | AI recommends mental models for this object | Analyze object type + content → rank models |
| `/extract` | Extract structured properties from body text | LLM reads body → suggests property values |
| `/review` | Generate spaced repetition items from object | LLM creates Q&A pairs from content |

### Tier 3 — Advanced, Requires New Infrastructure

| Command | Action | Implementation |
|---------|--------|---------------|
| `/query` | Natural language → SPARQL → results | Text-to-SPARQL pipeline |
| `/canvas` | Create spatial canvas from current object's neighborhood | Graph traversal → spatial layout |
| `/compare` | Side-by-side comparison of two objects | Dual retrieval + LLM diff |
| `/explain` | Explain how two objects are connected | Graph path-finding + LLM narrative |
| `/refactor` | Split/merge/reorganize objects | Multi-command batch with preview |

### Implementation Notes

The CodeMirror 6 editor (`editor.js`) currently supports toolbar actions for basic
markdown formatting. Slash commands would integrate as a CodeMirror extension:

1. Listen for `/` keystroke in editor
2. Show autocomplete dropdown (ninja-keys style, already in workspace)
3. On selection, execute command (some inline, some open a modal/picker)
4. For AI commands, show streaming response in a panel or inline

The command palette (F1, ninja-keys) already has the UI pattern — slash commands
in the editor would follow the same pattern but triggered contextually while writing.

---

## Part D: Implementation Roadmap

### Phase 1 — Foundation (enables everything else)

1. **Embedding service**: Index object body text + assembled entity context as vectors
   - Use sentence-transformers locally or OpenAI API (LLM config already exists)
   - Store in pgvector (add to stack) or Chroma (simpler)
   - Re-embed on body.set events (webhook-triggered)

2. **Text-to-SPARQL endpoint**: `/api/nl-query`
   - Takes natural language, returns SPARQL results + generated query
   - System prompt with ontology schema from installed models
   - Validation + retry on syntax errors

3. **Basic slash commands**: `/link`, `/tag`, `/relate`, `/template`
   - CodeMirror extension for `/` trigger
   - Reuse existing search + command APIs

### Phase 2 — Semantic Search ("Ask Your KB")

4. **Hybrid retrieval endpoint**: `/api/ask`
   - Query router: classify → SPARQL and/or vector → fusion → LLM answer
   - Citations with clickable object links
   - Show in chat panel or bottom panel

5. **AI slash commands**: `/ask`, `/summarize`, `/suggest-links`
   - Streaming responses in editor or side panel

### Phase 3 — Proactive Agent

6. **Agent loop**: Event-driven via WebhookService
   - On object.create → suggest links, classify captures, check SHACL gaps
   - Suggestions panel in right pane (accept/dismiss UX)

7. **Scheduled agents**: Daily/weekly digests
   - Stale objects, unlinked knowledge, knowledge gaps
   - Notification system or email digest

8. **MCP server**: Expose SemPKM as MCP resource
   - External AI clients can read/write SemPKM knowledge graph
   - Multiplies value — any MCP-compatible agent becomes a SemPKM agent

---

## References (Deep Dive)

- [Microsoft GraphRAG — GitHub](https://github.com/microsoft/graphrag)
- [LightRAG — HKU, GitHub](https://github.com/HKUDS/LightRAG)
- [Khoj — Self-hosted AI, GitHub](https://github.com/khoj-ai/khoj)
- [LlamaIndex KnowledgeGraphIndex](https://docs.llamaindex.ai/)
- [Think-on-Graph — arXiv 2024](https://arxiv.org/abs/2307.07697)
- [Graph RAG Survey — Peng et al. 2024](https://arxiv.org/abs/2408.08921)
- [Unifying LLMs and KGs: A Roadmap — Pan et al. 2023](https://arxiv.org/abs/2306.08302)
- [KG-RAG: Bridging Knowledge and Creativity 2024](https://arxiv.org/abs/2405.12035)
- [SPARQL Generation with LLMs — 2024](https://arxiv.org/abs/2402.00285)
- [Mem.ai](https://mem.ai/)
- [Anthropic MCP Specification](https://modelcontextprotocol.io/)
- [Obsidian Smart Connections](https://github.com/brianpetro/obsidian-smart-connections)
- [nano-graphrag — GitHub](https://github.com/gusye1234/nano-graphrag)
- [Haystack — deepset](https://github.com/deepset-ai/haystack)
