# SemPKM Browser Extension — Design Document

**Created:** 2026-03-16
**Status:** Draft
**Depends on:** Core API (shipped), SHACL shapes endpoint (shipped), IndieAuth (shipped)
**Does NOT depend on:** M009 App Platform

---

## Vision

A browser extension that turns web browsing into a **bidirectional conversation** between what you're reading and what you already know. Not just a clipper — a knowledge context layer.

Every existing PKM clipper is a one-way pipe: web → notes. SemPKM's extension is the first to make browsing a two-way interaction by querying your graph while you browse.

---

## Competitive Landscape

| Capability | Obsidian Clipper | Notion Clipper | Tana Capture | Hypothesis | **SemPKM** |
|---|---|---|---|---|---|
| Typed capture | Templates (manual) | No | Supertags | No | **SHACL-driven** |
| Set properties at clip time | Frontmatter | **No** (3.4★ rating) | Fields | Tags only | **Full form** |
| Schema enforcement | No | No | No | No | **SHACL validation** |
| Show existing knowledge | No | No | No | Annotations only | **Graph context** |
| Create relations at capture | No | No | Partial | No | **Typed predicates** |
| Query your knowledge base | No | No | No | No | **SPARQL** |
| Schema.org ingestion | Extract → flatten | No | No | No | **Native RDF** |

**Key insight:** Notion's clipper has 1M+ users at 3.4★ — the lowest-rated major clipper — because it can't set database properties at capture time. Tana's Chrome extension was removed from the Web Store in August 2025. The bar is low.

---

## Architecture

```
┌─────────────────┐         ┌──────────────────────┐
│  Browser Extension │       │  SemPKM Instance      │
│                   │        │  (local or cloud)     │
│  ┌─────────────┐ │        │                       │
│  │ Popup UI    │──POST /api/commands──→ Object creation
│  │ (capture)   │──GET /api/shapes/{type}→ SHACL form fields
│  └─────────────┘ │        │                       │
│  ┌─────────────┐ │        │                       │
│  │ Sidebar UI  │──POST /api/sparql────→ Context queries
│  │ (context)   │──GET /browser/relations→ Related objects
│  └─────────────┘ │        │                       │
│  ┌─────────────┐ │        │                       │
│  │ Background  │──GET /api/models─────→ Installed models
│  │ Service     │──GET /.well-known/sempkm→ Discovery
│  └─────────────┘ │        │                       │
│  ┌─────────────┐ │        │                       │
│  │ Auth        │──IndieAuth PKCE──────→ Session token
│  │             │──API key (fallback)──→ Auth header
│  └─────────────┘ │        │                       │
└─────────────────┘         └──────────────────────┘
```

### Authentication

Two modes:
1. **IndieAuth + PKCE** — Full OAuth2 flow for cloud-hosted instances. Already implemented in SemPKM.
2. **API key** — Simple bearer token for self-hosted users who don't need OAuth. Stored in extension settings, transmitted via `Authorization: Bearer` header.

### Instance Discovery

Extension settings page: `SemPKM URL: http://localhost:3000`

On connection, the extension hits `/.well-known/sempkm` (new endpoint) returning:
```json
{
  "version": "2.5.0",
  "api": "/api",
  "sparql": "/api/sparql",
  "commands": "/api/commands",
  "models": "/api/models",
  "auth": {
    "indieauth": "/auth/authorize",
    "api_key": true
  },
  "capabilities": ["shapes", "sparql", "commands", "models"]
}
```

### New Backend Endpoints Needed

1. **`GET /api/shapes/{type_iri}`** — Returns SHACL property shapes for a given type as JSON. The extension uses this to dynamically render capture forms. (May already be partially available via the existing form generation pipeline — needs extraction into a standalone JSON endpoint.)

2. **`GET /api/types`** — Returns all available types from installed Mental Models with labels, icons, and which model they belong to. Used to populate the type selector in the popup.

3. **`GET /.well-known/sempkm`** — Instance discovery and capability advertisement.

4. **`POST /api/context-query`** — Accepts page metadata (URL, title, keywords, selected text) and returns related objects from the graph. This wraps a SPARQL query but provides a simpler interface for the extension. (Alternative: the extension constructs SPARQL directly and uses `/api/sparql`.)

---

## Phase 1: Smart Structured Capture

### User Flow

1. User is browsing a web page
2. Clicks the SemPKM extension icon (or presses `Alt+S` / configurable shortcut)
3. **Popup opens** showing:

```
┌──────────────────────────────────┐
│ ☰ SemPKM Capture                │
│                                  │
│ Save as: [Note ▾]               │
│          ├ Note                  │
│          ├ Concept               │
│          ├ Claim                 │
│          ├ Contact               │
│          ├ Source                 │
│          └ Paper                 │
│                                  │
│ ─── Basic Info ───────────────── │
│ Title:  [Auto-filled from page] │
│ Body:   [Selected text or empty]│
│ Type:   [observation ▾]         │
│ Source: [https://current-url]   │
│                                  │
│ ─── Relationships ────────────── │
│ Related to: [🔍 Search objects] │
│   → isAbout: "Knowledge Mgmt"  │
│   + Add relationship            │
│                                  │
│ ─── Metadata ─────────────────── │
│ Tags:   [tag1, tag2]           │
│                                  │
│ [Save to SemPKM]               │
│                                  │
│ ℹ Connected to localhost:3000   │
└──────────────────────────────────┘
```

4. **Type selector** is populated from installed Mental Models via `GET /api/types`
5. **Selecting a type** dynamically fetches SHACL shapes via `GET /api/shapes/{type}` and renders the appropriate form fields, grouped by PropertyGroup
6. **Auto-population:**
   - `dcterms:title` ← page `<title>` or `og:title`
   - `body` ← selected text (if any)
   - `schema:url` / source fields ← current page URL
   - `schema:author` ← page `meta[name=author]` or `og:author`
   - `dcterms:created` ← current timestamp
   - `schema:datePublished` ← page `meta` or schema.org
7. **Relationship picker** — inline search that queries `/api/sparql` for existing objects, with type filtering. User selects an object and a predicate (from available properties on the current type).
8. **Save** → `POST /api/commands` with the object creation payload
9. **Success toast** with "Open in SemPKM" link

### Schema.org Ingestion

When a page contains `<script type="application/ld+json">`:

1. Extension parses the JSON-LD
2. Detects `@type` — maps to Mental Model types where possible:
   - `schema:Person` → CRM Contact (if CRM model installed)
   - `schema:Article` / `schema:ScholarlyArticle` → Note or Paper
   - `schema:Organization` → CRM Company
   - `schema:Recipe`, `schema:Event`, etc. → type-specific if models exist
3. Auto-fills form fields from matching schema.org properties
4. **Advanced mode:** Option to "Import as RDF" — ingest the JSON-LD triples directly into the graph, mapping schema.org properties to Mental Model properties where SHACL shapes define equivalences

### Highlight & Clip

Beyond full-page capture:

1. User selects text on the page
2. Right-click → "Save to SemPKM" (context menu)
3. Popup opens with selected text pre-filled in `body`
4. Type defaults to Note, but user can switch to Claim, Evidence, LiteratureNote, etc.
5. Source URL and text anchor position are captured for provenance

---

## Phase 2: Knowledge Context Overlay

### Concept

As you browse, the extension quietly checks: **"Do I already know something about this?"**

This transforms the browser from a consumption tool into a **thinking environment**.

### User Flow

1. User navigates to any page
2. Extension's background service extracts signals:
   - Page URL (exact match against `schema:url` fields in graph)
   - Page title (fuzzy match against `dcterms:title`)
   - Meta keywords, description
   - `<h1>`/`<h2>` headings
   - Schema.org entities (names, types)
3. Background service queries SemPKM: `POST /api/context-query` with extracted signals
4. If matches found: **badge appears** on extension icon — "4 related"
5. User clicks badge → **sidebar opens** on the right side of the page:

```
┌────────────────────────────────┐
│ 📡 Your Knowledge Context      │
│                                │
│ 4 objects related to this page │
│                                │
│ ─── Notes (2) ──────────────── │
│ 📄 "Architecture Decision:     │
│    Event Sourcing"             │
│    → isAbout: Event Sourcing   │
│    [Open] [Link to this page]  │
│                                │
│ 📄 "Meeting: Project Kickoff"  │
│    → relatedProject: SemPKM    │
│    [Open] [Link to this page]  │
│                                │
│ ─── Concepts (1) ────────────── │
│ 💡 "Semantic Web"              │
│    3 connected notes           │
│    [Open] [Link to this page]  │
│                                │
│ ─── Claims (1) ──────────────── │
│ ⚡ "RDF scales better than     │
│    property graphs"            │
│    Status: No evidence linked  │
│    ⚠️ This page may contain    │
│    relevant evidence           │
│    [Open] [Add Evidence]       │
│                                │
│ ─── Quick Capture ───────────── │
│ [+ Save this page as...]      │
│                                │
└────────────────────────────────┘
```

### Context Matching Strategy

**Tier 1 — Exact matches (fast, high confidence):**
- URL match: `?obj schema:url <current-url>` — "you've saved this page before"
- URL domain match: `?obj schema:url ?url . FILTER(CONTAINS(?url, "domain.com"))` — "you have other saves from this site"

**Tier 2 — Title/label matches (fast, medium confidence):**
- FTS query against LuceneSail: page title keywords → matching object labels
- Heading keywords → concept/tag matches

**Tier 3 — Entity matches (slower, requires extraction):**
- Named entities from page text → match against `foaf:name`, `dcterms:title`, `skos:prefLabel`
- Schema.org entities on the page → match against typed objects in graph

**Tier 4 — Semantic matches (future, requires AI):**
- Embedding similarity between page content and object bodies
- Claim detection on page → match against existing claims

Start with Tiers 1-2 for Phase 2 launch. They're cheap SPARQL queries that return in milliseconds against a local instance.

### In-Context Actions

From the sidebar, users can:

1. **Open** an object in SemPKM (new tab)
2. **Link** the current page to an existing object: creates a typed relationship without leaving the browser
3. **Add Evidence** to a Claim: highlight text → create Evidence object → link to existing Claim via `supports` / `refutes`
4. **Quick capture** from sidebar: same as Phase 1 popup but with pre-selected relationships to the matched objects

### Performance Considerations

- **Debounce:** Context query fires 2 seconds after page load completes (not on every navigation)
- **Cache:** Results cached per URL for the session. Badge updates on cache hit without re-querying.
- **Opt-in:** Users can disable auto-context in extension settings. Manual trigger via icon click always available.
- **Query budget:** Context queries have a 500ms timeout. If the instance is slow (large graph), degrade gracefully — show "Check context" button instead of auto-querying.

---

## Phase 3: Active Intelligence (Future)

Requires AI/LLM integration (post-M010).

### Capabilities

1. **Auto-detect claims** on the page → match against existing claims in graph → surface contradictions and corroborations
2. **Suggest type** from page content: "This page has schema.org `ScholarlyArticle` — save as Paper?"
3. **Suggest relationships:** "This article cites the same source as your Note X — link them?"
4. **Gap detection:** "You have a ResearchQuestion about X. This page discusses X but you haven't captured anything from it yet."
5. **Smart summarization:** "Summarize this page in the context of what I already know" — uses graph context to generate a personalized summary, not a generic one

### Architecture Note

Phase 3 features would use the LLM proxy already in SemPKM (`/api/llm/stream`) so the extension doesn't need its own API keys. The LLM sees both the page content and relevant graph context from SPARQL queries.

---

## Technical Specifications

### Platform

- **Chrome** (Manifest V3) — primary target
- **Firefox** (WebExtension) — secondary, shares 95% of codebase
- **Safari** — future consideration (requires Xcode wrapper)

### Extension Components

```
sempkm-extension/
├── manifest.json            # Chrome Manifest V3
├── background/
│   ├── service-worker.js    # Auth, context queries, badge updates
│   └── api-client.js        # SemPKM API wrapper
├── popup/
│   ├── popup.html           # Capture popup shell
│   ├── popup.js             # Type selector, dynamic form rendering
│   └── popup.css
├── sidebar/
│   ├── sidebar.html         # Context overlay panel
│   ├── sidebar.js           # Context display, in-context actions
│   └── sidebar.css
├── content/
│   ├── extractor.js         # Page metadata, schema.org, entity extraction
│   ├── highlighter.js       # Text selection capture
│   └── context-menu.js      # Right-click "Save to SemPKM"
├── shared/
│   ├── shacl-renderer.js    # Renders SHACL shapes as HTML forms
│   ├── auth.js              # IndieAuth PKCE + API key management
│   ├── storage.js           # Extension settings persistence
│   └── types.js             # Type definitions, icon mappings
├── options/
│   ├── options.html         # Settings page (instance URL, auth, preferences)
│   └── options.js
└── assets/
    └── icons/               # Extension icons (16, 32, 48, 128px)
```

### SHACL Form Renderer

The core technical challenge is rendering SHACL shapes as HTML forms in the popup. Two approaches:

**Option A: Client-side rendering (recommended)**
- Extension fetches shape JSON from `/api/shapes/{type}`
- `shacl-renderer.js` interprets property shapes and generates form HTML:
  - `sh:datatype xsd:string` → `<input type="text">`
  - `sh:datatype xsd:date` → `<input type="date">`
  - `sh:datatype xsd:boolean` → `<input type="checkbox">`
  - `sh:in [list]` → `<select>` with options
  - `sh:class` → object reference picker (search input)
  - `sh:minCount > 0` → required field indicator
  - `sh:group` → fieldset grouping
  - `sh:order` → field ordering
  - `sempkm:editHelpText` → tooltip/placeholder
- **Pro:** Fast, works offline-ish (cached shapes), no round-trip for form HTML
- **Con:** Duplicates form rendering logic from backend templates

**Option B: Server-rendered HTML**
- Extension hits a new endpoint: `GET /api/capture-form/{type}?context=extension`
- Backend returns pre-rendered HTML form (like the existing htmx forms but styled for the popup)
- Extension injects the HTML into the popup
- **Pro:** Single source of truth for form rendering, stays in sync with app
- **Con:** Requires network round-trip, harder to auto-populate fields

**Recommendation:** Option A for Phase 1, with a thin SHACL interpreter that handles the common property types. The extension's form doesn't need to handle every SHACL edge case — just the ones that appear in the standard Mental Models (string, date, boolean, enum, object reference).

### Data Flow: Capture → Graph

```
User clicks Save
       │
       ▼
Extension builds command payload:
{
  "type": "object.create",
  "payload": {
    "typeIri": "urn:sempkm:model:basic-pkm:Note",
    "properties": {
      "dcterms:title": "Page Title",
      "bpkm:body": "Selected text...",
      "bpkm:noteType": "reference",
      "schema:url": "https://...",
      "bpkm:tags": ["tag1", "tag2"]
    },
    "edges": [
      {
        "predicate": "bpkm:isAbout",
        "target": "urn:sempkm:...:concept-123"
      }
    ]
  }
}
       │
       ▼
POST /api/commands
       │
       ▼
EventStore.commit() → named graph created
       │
       ▼
Materialized to urn:sempkm:current
       │
       ▼
Extension shows success toast
```

---

## Mental Model Integration Matrix

The extension's power scales with installed Mental Models:

| Model | Clip As... | Auto-fill From... | Unique Capability |
|---|---|---|---|
| **basic-pkm** | Note, Concept | title, URL, selected text | General capture |
| **basic-pkm (v2 with tasks)** | Task | title, URL | Quick task from any page |
| **Personal CRM** | Contact, Company | schema.org Person/Organization, LinkedIn structured data | Clip a LinkedIn profile as a typed Contact |
| **Zettelkasten+** | LiteratureNote, Source | title, author, URL, selected text | Auto-create Source + LiteratureNote pair with `derivedFrom` edge |
| **Research Workflow** | Paper, Claim, Evidence | DOI metadata, schema.org ScholarlyArticle | Clip from PubMed/arXiv → typed Paper with extracted claims |
| **RSS feeds (M010)** | FeedSubscription | RSS/Atom `<link>` discovery on page | "Subscribe to this site's feed" button |

---

## Settings & Configuration

### Extension Options Page

```
SemPKM Connection
─────────────────
Instance URL:  [http://localhost:3000    ]
Auth method:   (•) API Key  ( ) IndieAuth
API Key:       [••••••••••••••••••••••••]
Status:        ✅ Connected (v2.5.0, 3 models)

Capture Defaults
────────────────
Default type:       [Note ▾]
Auto-fill title:    [✓]
Auto-fill URL:      [✓]
Include selection:  [✓]

Context Overlay
───────────────
Auto-check context: [✓]
Check delay:        [2 seconds ▾]
Show badge count:   [✓]

Keyboard Shortcuts
──────────────────
Open capture:       [Alt+S]
Capture selection:  [Alt+Shift+S]
Toggle sidebar:     [Alt+K]
```

---

## Phased Delivery

### Phase 1: Smart Structured Capture
**Scope:** Popup capture with dynamic SHACL forms, type selection, auto-population, relationship picker, schema.org extraction, context menu integration.
**Dependency:** Existing API + 1-2 new endpoints (`/api/shapes/{type}`, `/api/types`)
**Timeline:** Can begin independently of M009

### Phase 2: Knowledge Context Overlay
**Scope:** Sidebar with context matching (Tiers 1-2), badge notifications, in-context actions (link, add evidence), related object display.
**Dependency:** `/api/context-query` endpoint or direct SPARQL from extension
**Timeline:** After Phase 1 is stable, benefits from more Mental Models being in use

### Phase 3: Active Intelligence
**Scope:** AI-powered claim detection, relationship suggestions, gap analysis, personalized summaries.
**Dependency:** LLM integration (post-M010), richer graph data
**Timeline:** Post-M010

---

## Success Metrics

- **Phase 1:** Users can capture a typed, validated object from any web page in under 10 seconds
- **Phase 2:** Extension surfaces relevant existing knowledge on >30% of pages visited by active users
- **Phase 3:** AI suggestions are accepted (not dismissed) >50% of the time
