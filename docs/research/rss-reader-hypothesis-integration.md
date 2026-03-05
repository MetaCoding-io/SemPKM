# RSS Reader & Hypothesis Integration — Feasibility Research

**Date:** 2026-03-02
**Goal:** Evaluate how difficult it would be to build Inoreader-like RSS reading + Hypothesis annotation integration into SemPKM, storing everything in the RDF graph.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Fit](#2-current-architecture-fit)
3. [Python RSS/Feed Parsing Libraries](#3-python-rssfeed-parsing-libraries)
4. [Feed Discovery](#4-feed-discovery)
5. [Content Extraction (Reader Mode)](#5-content-extraction-reader-mode)
6. [Feed Polling & Scheduling](#6-feed-polling--scheduling)
7. [OPML Import/Export](#7-opml-importexport)
8. [Hypothesis API & Annotation Sync](#8-hypothesis-api--annotation-sync)
9. [RDF Data Model Design](#9-rdf-data-model-design)
10. [Inoreader Feature Reference](#10-inoreader-feature-reference)
11. [Implementation Phases](#11-implementation-phases)
12. [Effort Estimates & Risk Assessment](#12-effort-estimates--risk-assessment)

---

## 1. Executive Summary

**Verdict: Very feasible.** SemPKM's architecture is well-suited for this feature. The command/event-sourcing pattern, RDF graph storage, htmx-driven workspace UI, and existing model system all align naturally with an RSS reader + annotation workflow.

**Key advantages of SemPKM's architecture:**
- The Mental Model system can define Article, Feed, Highlight types as a new model bundle
- The Command pattern (create/patch/edge) already handles all the write operations needed
- Event sourcing gives us an audit trail of all reading activity for free
- The workspace UI (panels, tabs, views) provides a natural home for a reader interface
- RDF4J triplestore can handle the W3C Web Annotation vocabulary natively
- httpx is already a dependency (async HTTP for feed fetching)

**What needs to be built from scratch:**
- Feed subscription management service + background polling
- Feed parsing and article ingestion pipeline
- Hypothesis API sync service
- Reader UI (article list, reading pane, annotation sidebar)
- A new Mental Model bundle with ontology, shapes, views, and seed data

**New dependencies required:** `feedparser` or `fastfeedparser`, `trafilatura` (content extraction), optionally `feedfinder2` (feed discovery), `opml` (import).

---

## 2. Current Architecture Fit

### What already exists and can be reused

| Concern | Existing Component | Reusability |
|---|---|---|
| Data storage | RDF4J triplestore + event sourcing | Direct reuse — articles become RDF objects |
| Write path | Command dispatcher (object.create, edge.create, etc.) | Direct reuse — ingested articles go through command pipeline |
| Async HTTP | httpx.AsyncClient (singleton) | Direct reuse for feed fetching and Hypothesis API calls |
| UI framework | htmx + Jinja2 fragments + Split.js workspace | Extend with new panels/views |
| Labels/display | LabelService (dcterms:title > rdfs:label > ...) | Direct reuse — articles get dcterms:title |
| Graph visualization | Cytoscape.js views | Reuse for article-concept relationship graphs |
| Markdown rendering | marked + highlight.js + DOMPurify | Reuse for article body display |
| Search | RDF4J Lucene index | Could extend for full-text article search |
| Webhooks | Existing webhook dispatch on event commit | Reuse for "new article" notifications |
| WebDAV | File-based read/write with frontmatter | Could expose articles as markdown files |

### What does NOT exist

- No RSS/feed parsing library in dependencies
- No background task scheduler (no Celery, APScheduler, or similar)
- No external API integration pattern (Hypothesis, etc.)
- No "reader mode" content extraction
- No read/unread state tracking beyond what RDF properties could model
- No keyboard shortcut framework beyond ninja-keys command palette

### Architecture gaps to fill

1. **Background task scheduling** — Need a way to poll feeds periodically. Options: APScheduler (lightweight, in-process), asyncio background tasks in FastAPI lifespan, or external cron.
2. **External API client pattern** — Need a reusable pattern for authenticated API calls to Hypothesis (and potentially other services in the future).
3. **Bulk ingestion** — Current command pipeline is designed for individual user actions. Feed updates may produce 10-50 new articles at once. Need to ensure EventStore.commit() handles batch operations efficiently.

---

## 3. Python RSS/Feed Parsing Libraries

### Comparison

| Library | Speed | Compatibility | Async | Maintained | License |
|---|---|---|---|---|---|
| **feedparser** 6.0.12 | Baseline (slowest) | Best — handles broken feeds | No (needs executor) | Yes | BSD |
| **FastFeedParser** 0.5.7 | 5-50x faster | Good — RSS 2.0, Atom 1.0, RDF 1.0, JSON Feed | No | Yes (Kagi) | MIT |
| **atoma** 0.0.17 | Fast | Good — typed objects | No | Low activity | MIT |
| **reader** 3.21 | N/A (full library) | Excellent — uses feedparser internally | No | Yes (Jan 2026) | BSD-3 |

### Recommendation for SemPKM

**feedparser** is the safest choice for a first implementation:
- Handles malformed feeds gracefully (critical for real-world RSS)
- Built-in ETag/Last-Modified conditional GET support
- Huge community knowledge base for edge cases
- The performance gap only matters at 1000+ feeds — acceptable for a personal knowledge management tool

**FastFeedParser** is a good upgrade path if performance becomes an issue later.

The `reader` library is worth studying for architectural patterns (how it handles storage, search, conditional GET, and plugins) but is too opinionated to embed directly — SemPKM has its own storage and command layer.

---

## 4. Feed Discovery

### How it works

Websites advertise feeds via `<link>` tags in HTML `<head>`:

```html
<link rel="alternate" type="application/rss+xml" href="/feed.xml" title="RSS Feed">
<link rel="alternate" type="application/atom+xml" href="/atom.xml" title="Atom Feed">
```

### Common URL patterns to probe when autodiscovery is absent

| Platform | Pattern |
|---|---|
| WordPress (~43% of web) | `/feed/`, `/feed/atom/`, `/comments/feed/` |
| Blogger/Blogspot | `/feeds/posts/default`, `/feeds/posts/default?alt=rss` |
| Medium | `/feed/{username}` or `/feed` on custom domains |
| GitHub | `/{user}/{repo}/releases.atom`, `/{user}/{repo}/commits.atom` |
| Generic | `/feed.xml`, `/rss.xml`, `/atom.xml`, `/rss`, `/feed`, `/index.xml` |

### Libraries

- **feedfinder2** — Simple `find_feeds(url)` function. Probes `<link>` tags + common URL patterns. ~50 lines of logic.
- **DIY approach** — Fetch with httpx, parse `<head>` with a simple regex or lxml, resolve relative URLs. Straightforward to implement (~50 lines).

### Recommendation

Implement feed discovery as a small utility function in the feed service. It's simple enough that a dedicated library is optional — httpx + BeautifulSoup/lxml is sufficient.

---

## 5. Content Extraction (Reader Mode)

For fetching clean article text from full web pages (when the RSS feed only provides a summary).

### Benchmark results (ScrapingHub Article Extraction Benchmark)

| Library | F1 Score | Best At |
|---|---|---|
| **trafilatura** | 0.958 | Best overall accuracy, multiple output formats |
| **newspaper4k** | 0.949 | News articles, metadata extraction |
| **readability-lxml** | 0.922 | Most consistent/predictable, Mozilla algorithm |

### Recommendation for SemPKM

**trafilatura** as the primary extractor:
- Best F1 score across diverse page types
- Outputs: plain text, Markdown, HTML, XML — Markdown output integrates perfectly with SemPKM's body.set command
- Extracts metadata: title, author, date, categories, tags
- Already falls back to readability-lxml internally
- Peer-reviewed (ACL 2021)
- Apache 2.0 license

The Markdown output mode is particularly valuable — articles can be stored as Markdown bodies on RDF objects, consistent with how SemPKM already stores note content.

---

## 6. Feed Polling & Scheduling

### Conditional GET (essential)

Two HTTP mechanisms to avoid re-downloading unchanged feeds:

1. **ETag / If-None-Match** — Server returns an ETag hash. Client sends it back. 304 if unchanged.
2. **Last-Modified / If-Modified-Since** — Server returns a timestamp. Client sends it back. 304 if unchanged.

feedparser supports both natively:
```python
d = feedparser.parse(url, etag=stored_etag, modified=stored_modified)
if d.status == 304:
    pass  # Feed unchanged
```

### Adaptive polling intervals

Not all feeds update at the same rate:
- High-frequency news: poll every 15-30 minutes
- Regular blogs: poll every 1-2 hours
- Infrequent personal sites: poll every 6-12 hours

**Strategy:** Track each feed's publication frequency. Adjust polling interval to ~2x the average time between posts, with a floor of 15 minutes and a ceiling of 12 hours. Also respect RSS `<ttl>` and HTTP `Cache-Control` hints.

### Scheduling in SemPKM

**Recommended: asyncio background task in FastAPI lifespan.**

SemPKM already uses a FastAPI lifespan function for startup/shutdown. A background task loop that runs during the lifespan is the simplest approach for a single-process personal tool:

```python
async def feed_poll_loop():
    while True:
        feeds_due = await get_feeds_due_for_update()
        for feed in feeds_due:
            await update_feed(feed)
        await asyncio.sleep(60)  # Check every minute which feeds are due
```

No need for Celery, Redis, or external schedulers for a personal PKM tool. If multi-user support is added later, APScheduler or Celery can be introduced.

---

## 7. OPML Import/Export

OPML is the universal interchange format for feed subscription lists.

### Import

```xml
<opml version="2.0">
  <body>
    <outline text="Tech" title="Tech">
      <outline type="rss" text="Ars Technica"
               xmlUrl="https://feeds.arstechnica.com/arstechnica/index"
               htmlUrl="https://arstechnica.com/" />
    </outline>
  </body>
</opml>
```

Libraries: `opml` (PyPI) or `listparser` for parsing. Simple enough for stdlib `xml.etree.ElementTree`.

### Export

Generate OPML from the graph by querying all feed subscriptions and their folder hierarchy. Use `xml.etree.ElementTree` (stdlib) — no external dependency needed.

### Recommendation

Use `listparser` for import (handles both OPML and other subscription list formats). Use stdlib `xml.etree.ElementTree` for export.

---

## 8. Hypothesis API & Annotation Sync

### API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/search` | Search annotations by URI, user, tags, text, group |
| `POST` | `/api/annotations` | Create annotation |
| `GET` | `/api/annotations/:id` | Retrieve annotation |
| `PUT` | `/api/annotations/:id` | Update annotation |
| `DELETE` | `/api/annotations/:id` | Delete annotation |

**Base URL:** `https://hypothes.is/api/`
**Auth:** Bearer token from `https://hypothes.is/account/developer`

### Annotation Data Model

Key fields in a Hypothesis annotation:
- `id` — unique identifier
- `created` / `updated` — ISO 8601 timestamps
- `user` — account URI (e.g., `acct:username@hypothes.is`)
- `uri` — URL of the annotated document
- `text` — the annotation body/comment
- `tags` — array of tag strings
- `target` — array of objects with `source` URL and `selector` array

**Target selectors** (how highlights are anchored):
- **TextQuoteSelector** — `exact` (highlighted text), `prefix` (context before), `suffix` (context after)
- **TextPositionSelector** — character offset `start`/`end`
- **RangeSelector** — XPath-based DOM positions

Hypothesis uses **fuzzy anchoring** with Levenshtein distance matching, making annotations resilient to document changes.

### W3C Web Annotation Standard

Hypothesis was deeply involved in creating the W3C Web Annotation standard (finalized 2017). The Hypothesis native API format is close to but not identical to the W3C JSON-LD format. Community converters exist for producing fully W3C-compliant JSON-LD.

The W3C vocabulary (`oa:` namespace) maps directly to RDF — this is ideal for SemPKM since we can store annotations as native RDF triples.

### Python Client Libraries

- **`python-hypothesis`** (PyPI: `python-hypothesis`) — Most established. `h_annot.search()` with keyword args.
- **DIY with httpx** — The API is simple REST. A thin wrapper around httpx is straightforward (~100 lines).

### Real-Time Sync

- **WebSocket**: `wss://hypothes.is/ws` — subscribe to annotation events
- **No webhooks** — no HTTP POST callbacks available
- **RSS feeds**: `https://hypothes.is/stream.atom?user=username` — but limited (public only, strips tags)

### Recommended sync strategy for SemPKM

1. **Initial sync**: Paginate through `/api/search?user={user}` to fetch all existing annotations
2. **Periodic sync**: Poll `/api/search?user={user}&sort=updated&order=desc` every few minutes, stop when reaching a previously-seen annotation
3. **Optional WebSocket**: For near-real-time sync, maintain a WebSocket connection to `wss://hypothes.is/ws` and process events as they arrive
4. **Bidirectional (future)**: SemPKM could create annotations back to Hypothesis via POST, enabling a two-way sync

---

## 9. RDF Data Model Design

### Recommended Vocabularies

| Prefix | URI | Use Case |
|---|---|---|
| `schema:` | `https://schema.org/` | Article types/properties |
| `dcterms:` | `http://purl.org/dc/terms/` | Bibliographic metadata (title, creator, date, source) |
| `oa:` | `http://www.w3.org/ns/oa#` | Annotations, highlights, bookmarks, selectors |
| `sioc:` | `http://rdfs.org/sioc/ns#` | Forums/feeds, posts, subscriptions |
| `as:` | `https://www.w3.org/ns/activitystreams#` | User activities (Read, Like, Follow) |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | Tags, categories, folder labels |
| `sempkm:` | (project namespace) | Custom properties (subscription settings, polling config) |

### Core Types

#### Feed
```turtle
<urn:feed:example-blog>
    a schema:DataFeed, sioc:Forum ;
    dcterms:title "Example Blog" ;
    schema:url <http://example.com/feed.xml> ;
    sioc:feed <http://example.com/feed.xml> ;
    sioc:link <http://example.com/> .
```

#### Feed Subscription (reified — per-user metadata)
```turtle
<urn:sempkm:subscription:1>
    a sempkm:FeedSubscription ;
    sempkm:feed <urn:feed:example-blog> ;
    dcterms:title "Example Blog (custom title)" ;
    dcterms:created "2026-01-15"^^xsd:date ;
    sempkm:folder <urn:sempkm:folder:tech> ;
    sempkm:pollingInterval "PT1H"^^xsd:duration ;
    sempkm:etag "\"abc123\"" ;
    sempkm:lastModified "2026-03-01T10:00:00Z"^^xsd:dateTime .
```

#### Article
```turtle
<urn:article:550e8400-...>
    a schema:Article ;
    dcterms:title "Understanding RDF for PKM" ;
    dcterms:creator "Alice Smith" ;
    dcterms:issued "2026-02-28"^^xsd:date ;
    schema:url <http://example.com/post/1> ;
    dcterms:description "A guide to using RDF..." ;
    dcterms:source <urn:feed:example-blog> ;
    schema:isPartOf <urn:feed:example-blog> ;
    dcterms:identifier "guid:http://example.com/post/1" .
```

Article body (full text) stored via the existing `body.set` command as Markdown.

#### Read/Unread State
```turtle
<urn:sempkm:activity:1>
    a as:Read ;
    as:actor <urn:sempkm:user:current> ;
    as:object <urn:article:550e8400-...> ;
    as:published "2026-03-01T09:15:00Z"^^xsd:dateTime .
```

#### Star/Bookmark
```turtle
<urn:sempkm:annotation:bookmark:1>
    a oa:Annotation ;
    oa:motivatedBy oa:bookmarking ;
    dcterms:created "2026-03-01T09:20:00Z"^^xsd:dateTime ;
    oa:hasTarget <urn:article:550e8400-...> .
```

#### Highlight (from Hypothesis)
```turtle
<urn:sempkm:annotation:highlight:1>
    a oa:Annotation ;
    oa:motivatedBy oa:highlighting ;
    dcterms:created "2026-03-01T14:30:00Z"^^xsd:dateTime ;
    sempkm:hypothesisId "abc123def" ;
    oa:hasTarget [
        a oa:SpecificResource ;
        oa:hasSource <urn:article:550e8400-...> ;
        oa:hasSelector [
            a oa:TextQuoteSelector ;
            oa:exact "RDF allows modeling knowledge as a graph" ;
            oa:prefix "As discussed earlier, " ;
            oa:suffix ". This has profound implications"
        ]
    ] ;
    oa:hasBody [
        a oa:TextualBody ;
        rdf:value "This is the key insight of the whole article." ;
        dcterms:format "text/plain"
    ] .
```

#### Feed Folder
```turtle
<urn:sempkm:folder:tech>
    a sempkm:FeedFolder ;
    skos:prefLabel "Technology" ;
    sempkm:parentFolder <urn:sempkm:folder:root> .
```

### Mental Model Bundle

This would be delivered as a new installable model (like `basic-pkm`):

```
models/rss-reader/
  manifest.yaml
  ontology/rss-reader.jsonld    # OWL classes + properties
  shapes/rss-reader.jsonld      # SHACL shapes for forms
  views/rss-reader.jsonld       # ViewSpec SPARQL queries
  seed/rss-reader.jsonld        # Default folders, sample feed
```

**Types defined:**
- `sempkm:Feed` (maps to schema:DataFeed + sioc:Forum)
- `sempkm:FeedSubscription`
- `sempkm:Article` (maps to schema:Article)
- `sempkm:FeedFolder`
- `sempkm:Highlight` (maps to oa:Annotation with oa:highlighting)
- `sempkm:Bookmark` (maps to oa:Annotation with oa:bookmarking)

**Views defined:**
- "Unread Articles" — SPARQL query filtering articles without an as:Read activity
- "Starred Articles" — SPARQL query for articles with oa:bookmarking annotations
- "Highlights" — SPARQL query for all oa:highlighting annotations
- "Feed List" — SPARQL query listing all subscriptions with unread counts
- "Articles by Feed" — Parametric view filtering by dcterms:source

---

## 10. Inoreader Feature Reference

### Core features to replicate (MVP)

| Feature | Difficulty | Notes |
|---|---|---|
| Add feed by URL | Low | Feed discovery + feedparser |
| Folder organization | Low | SKOS hierarchy in RDF |
| Article list (unread) | Low | SPARQL query + htmx list view |
| Read article in panel | Low | Markdown body display (existing infra) |
| Mark read/unread | Low | as:Read activity creation/deletion |
| Star/bookmark | Low | oa:Annotation with oa:bookmarking |
| OPML import | Low | listparser + batch object.create commands |
| OPML export | Low | SPARQL query + stdlib XML generation |

### Important features (Phase 2)

| Feature | Difficulty | Notes |
|---|---|---|
| Keyboard shortcuts (J/K/Space/F) | Medium | Extend ninja-keys + custom JS |
| Full-text search | Medium | RDF4J Lucene index on article body |
| Fetch full article (reader mode) | Medium | trafilatura integration |
| Hypothesis sync (import highlights) | Medium | API polling + OA triples |
| Tags on articles | Low | dcterms:subject or oa:tagging |
| Multiple view modes (list/card) | Low | Existing view renderer patterns |
| Feed polling scheduler | Medium | asyncio background task |
| Conditional GET (ETag/Last-Modified) | Low | feedparser built-in |

### Nice-to-have features (Phase 3+)

| Feature | Difficulty | Notes |
|---|---|---|
| Rules/filters (auto-tag, auto-read) | High | Rule engine on article ingestion |
| Highlight articles in-browser | High | Hypothesis client-side JS or custom |
| Two-way Hypothesis sync | Medium | POST annotations back to Hypothesis |
| Newsletter ingestion (via email) | High | Would need email receiving infrastructure |
| Social feed aggregation | High | Platform-specific APIs, auth complexity |
| AI article summaries | Medium | LLM API integration |
| Duplicate detection | Medium | Content similarity hashing |

---

## 11. Implementation Phases

### Phase 1: Core Feed Reader (MVP)

**New files:**
- `backend/app/feeds/router.py` — Feed management endpoints
- `backend/app/feeds/service.py` — FeedService (fetch, parse, ingest)
- `backend/app/feeds/discovery.py` — Feed URL discovery
- `backend/app/feeds/scheduler.py` — Background polling loop
- `backend/app/templates/feeds/` — Reader UI templates
- `models/rss-reader/` — Mental Model bundle

**New dependencies:**
- `feedparser` — Feed parsing
- `listparser` — OPML import

**Commands used (existing):**
- `object.create` — Create Feed, Article, Subscription objects
- `object.patch` — Update feed metadata, subscription settings
- `edge.create` — Link articles to feeds, folders, tags
- `body.set` — Store article content as Markdown

**UI additions:**
- "Feeds" panel in the left sidebar (alongside Objects/Views)
- Article list view in the center editor area
- Article reading pane (reuse existing object tab pattern)

### Phase 2: Hypothesis Integration + Polish

**New files:**
- `backend/app/hypothesis/service.py` — Hypothesis API client
- `backend/app/hypothesis/sync.py` — Annotation sync logic
- `backend/app/hypothesis/router.py` — Settings/config endpoints
- `backend/app/templates/feeds/highlights.html` — Highlight display

**New dependencies:**
- `trafilatura` — Content extraction for reader mode

**Features:**
- Hypothesis API token configuration in settings
- Initial annotation import (full history)
- Periodic annotation sync
- Highlight display alongside articles
- Link highlights to existing SemPKM concepts via edges

### Phase 3: Power Features

- Keyboard shortcuts for article navigation
- Full-text search across articles
- Filter/rule system for auto-organization
- OPML export
- Adaptive polling intervals
- Article-to-concept linking (manual and AI-suggested)

---

## 12. Effort Estimates & Risk Assessment

### Complexity assessment

| Component | Effort | Risk |
|---|---|---|
| Mental Model bundle (ontology/shapes/views) | Small | Low — follows existing pattern |
| Feed parsing + ingestion service | Medium | Low — feedparser is mature |
| Background polling scheduler | Medium | Medium — need to handle failures, retries gracefully |
| Reader UI (article list + reading pane) | Medium-Large | Low — htmx patterns are established |
| Hypothesis API integration | Medium | Medium — API is simple but sync edge cases (deletions, edits, conflicts) add complexity |
| OA annotation RDF modeling | Small | Low — W3C standard is well-defined |
| OPML import/export | Small | Low — simple XML format |
| Feed discovery | Small | Low — straightforward HTTP + HTML parsing |
| Keyboard shortcuts | Small | Low — ninja-keys exists |
| Full-text search | Medium | Medium — depends on RDF4J Lucene configuration |

### Key risks

1. **Feed polling reliability** — Feeds go down, return errors, change URLs. Need robust error handling with exponential backoff and dead-feed detection.
2. **Content extraction quality** — trafilatura is good but not perfect. Some sites block scrapers or require JavaScript rendering. Accepting "good enough" is important.
3. **Hypothesis API rate limits** — Not well-documented. Need to implement respectful polling with backoff.
4. **RDF4J performance at scale** — If a user subscribes to 100+ feeds with years of history, the triplestore could accumulate millions of triples. Need to consider pagination, archival, and query optimization.
5. **Event sourcing overhead** — Each article import creates an event graph. With 50 articles per feed update across 100 feeds, that's 5,000 event graphs per poll cycle. May need a bulk-import optimization that batches articles into fewer events.

### New dependencies summary

| Package | Purpose | Size | License |
|---|---|---|---|
| `feedparser` | RSS/Atom parsing | ~100KB | BSD |
| `trafilatura` | Article content extraction | ~2MB (with deps) | Apache 2.0 |
| `listparser` | OPML import | ~30KB | MIT |

All are pure Python, well-maintained, and have compatible licenses.

---

## Sources

### RSS/Feed Parsing
- [feedparser on GitHub](https://github.com/kurtmckee/feedparser)
- [FastFeedParser by Kagi](https://github.com/kagisearch/fastfeedparser)
- [atoma on GitHub](https://github.com/NicolasLM/atoma)
- [reader library by lemon24](https://github.com/lemon24/reader)
- [feedfinder2 on GitHub](https://github.com/dfm/feedfinder2)

### Content Extraction
- [Trafilatura docs & evaluation](https://trafilatura.readthedocs.io/en/latest/evaluation.html)
- [Comparison of web content extraction](https://chuniversiteit.nl/papers/comparison-of-web-content-extraction-algorithms)

### Feed Polling
- [feedparser ETag/Last-Modified docs](https://pythonhosted.org/feedparser/http-etag.html)
- [RSS Autodiscovery specification](https://www.rssboard.org/rss-autodiscovery)

### Hypothesis
- [Hypothesis API docs](https://h.readthedocs.io/en/latest/api/)
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/)
- [W3C Web Annotation Vocabulary](https://www.w3.org/TR/annotation-vocab/)

### RDF Vocabularies
- [Schema.org Article](https://schema.org/Article)
- [Dublin Core Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)
- [W3C Open Annotation (oa:)](http://www.w3.org/ns/oa#)
- [SIOC ontology](http://rdfs.org/sioc/spec/)
- [W3C Activity Streams 2.0](https://www.w3.org/TR/activitystreams-core/)

### Inoreader Reference
- [Inoreader 2025 year in review](https://www.inoreader.com/blog/2025/12/inoreader-2025-intelligence-and-automation-in-one-content-hub.html)
- [Best RSS reader apps 2026 (Zapier)](https://zapier.com/blog/best-rss-feed-reader-apps/)
- [Inoreader keyboard shortcuts](https://defkey.com/inoreader-shortcuts)
