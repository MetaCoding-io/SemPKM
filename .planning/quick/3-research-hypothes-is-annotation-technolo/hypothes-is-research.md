# Hypothes.is and W3C Web Annotation Technology Research

**For:** SemPKM annotation integration
**Date:** 2026-02-24
**Sources:** W3C Web Annotation Data Model (REC 2017-02-23), W3C Web Annotation Protocol (REC 2017-02-23), W3C anno.jsonld context, Hypothes.is API (live), h.readthedocs.io client docs, GitHub hypothesis/h, hypothesis/via, hypothesis/bouncer

---

## 1. W3C Web Annotation Standard

### 1.1 Data Model Overview

The W3C Web Annotation Data Model (https://www.w3.org/TR/annotation-model/) is a W3C Recommendation published 2017-02-23. It defines a standard RDF-based model for annotations that can be serialized as JSON-LD.

**Core concept:** An annotation is a directed graph connecting a Body (the comment/note) to a Target (the resource being annotated). The motivation for the annotation describes *why* the annotation was created.

```
[oa:Annotation]
  ├── oa:hasBody  → [Body resource or embedded TextualBody]
  ├── oa:hasTarget → [oa:SpecificResource or full IRI]
  └── oa:motivatedBy → [oa:commenting | oa:highlighting | oa:tagging | ...]
```

### 1.2 Key Classes and Properties

**Core annotation class:**

| Term | Full IRI | Description |
|------|----------|-------------|
| `oa:Annotation` | `http://www.w3.org/ns/oa#Annotation` | The annotation resource itself |
| `oa:hasBody` | `http://www.w3.org/ns/oa#hasBody` | Relates annotation to its body |
| `oa:hasTarget` | `http://www.w3.org/ns/oa#hasTarget` | Relates annotation to what is being annotated |
| `oa:motivatedBy` | `http://www.w3.org/ns/oa#motivatedBy` | The motivation/intent behind the annotation |
| `oa:bodyValue` | `http://www.w3.org/ns/oa#bodyValue` | Shorthand for a plain text body (no separate body resource) |

**Embedded body:**

| Term | Full IRI | Description |
|------|----------|-------------|
| `oa:TextualBody` | `http://www.w3.org/ns/oa#TextualBody` | Body embedded as text in the annotation |
| `rdf:value` | `http://www.w3.org/1999/02/22-rdf-syntax-ns#value` | The actual text content |
| `dc:format` | `http://purl.org/dc/elements/1.1/format` | Media type of body text (e.g., `text/plain`, `text/html`) |

**Target selectors** (all use prefix `oa:`, full IRI `http://www.w3.org/ns/oa#`):

| Term | Full IRI | Use |
|------|----------|-----|
| `oa:SpecificResource` | `http://www.w3.org/ns/oa#SpecificResource` | A specific part of a resource |
| `oa:hasSource` | `http://www.w3.org/ns/oa#hasSource` | The base resource being selected from |
| `oa:hasSelector` | `http://www.w3.org/ns/oa#hasSelector` | The selector that identifies the fragment |
| `oa:TextQuoteSelector` | `http://www.w3.org/ns/oa#TextQuoteSelector` | Selects text by exact match + surrounding context |
| `oa:TextPositionSelector` | `http://www.w3.org/ns/oa#TextPositionSelector` | Selects text by character offset |
| `oa:FragmentSelector` | `http://www.w3.org/ns/oa#FragmentSelector` | Selects using URI fragment (e.g., `#page=5`) |
| `oa:RangeSelector` | `http://www.w3.org/ns/oa#RangeSelector` | Selects an XPath-based DOM range |
| `oa:exact` | `http://www.w3.org/ns/oa#exact` | Exact quoted text |
| `oa:prefix` | `http://www.w3.org/ns/oa#prefix` | Text immediately before the exact match |
| `oa:suffix` | `http://www.w3.org/ns/oa#suffix` | Text immediately after the exact match |
| `oa:start` | `http://www.w3.org/ns/oa#start` | Start character offset |
| `oa:end` | `http://www.w3.org/ns/oa#end` | End character offset |

**Motivation values** (all in `oa:` namespace):

| JSON-LD shorthand | Full IRI | Use |
|-------------------|----------|-----|
| `commenting` | `oa:commenting` | General comment/note about the target |
| `highlighting` | `oa:highlighting` | Highlight without comment |
| `tagging` | `oa:tagging` | Apply a tag |
| `replying` | `oa:replying` | Reply to another annotation |
| `bookmarking` | `oa:bookmarking` | Bookmark the target |
| `describing` | `oa:describing` | Longer descriptive annotation |
| `questioning` | `oa:questioning` | Ask a question about the target |
| `reviewing` | `oa:reviewing` | Review/assessment |
| `editing` | `oa:editing` | Propose an edit |
| `linking` | `oa:linking` | Link two resources |
| `classifying` | `oa:classifying` | Assign a category |
| `identifying` | `oa:identifying` | Identify the target as a known entity |

**Provenance:**

| Term | Full IRI | Description |
|------|----------|-------------|
| `dcterms:creator` | `http://purl.org/dc/terms/creator` | Creator agent (person or software) |
| `dcterms:created` | `http://purl.org/dc/terms/created` | Creation datetime (xsd:dateTime) |
| `dcterms:modified` | `http://purl.org/dc/terms/modified` | Last modification datetime |
| `as:generator` | `http://www.w3.org/ns/activitystreams#generator` | Software that created the annotation |

### 1.3 JSON-LD Representation and RDF Mapping

The W3C defines a canonical JSON-LD context at `https://www.w3.org/ns/anno.jsonld`. The core namespaces are:

```
oa:       http://www.w3.org/ns/oa#
dc:       http://purl.org/dc/elements/1.1/
dcterms:  http://purl.org/dc/terms/
foaf:     http://xmlns.com/foaf/0.1/
as:       http://www.w3.org/ns/activitystreams#
schema:   http://schema.org/
xsd:      http://www.w3.org/2001/XMLSchema#
```

A JSON-LD annotation with a text quote selector and comment body:

```json
{
  "@context": "http://www.w3.org/ns/anno.jsonld",
  "id": "http://example.org/anno1",
  "type": "Annotation",
  "motivation": "commenting",
  "creator": {
    "id": "http://example.org/user/alice",
    "type": "Person",
    "name": "Alice"
  },
  "created": "2026-02-24T12:00:00Z",
  "body": {
    "type": "TextualBody",
    "value": "This is a key insight about semantic annotations.",
    "format": "text/plain",
    "language": "en"
  },
  "target": {
    "source": "https://www.w3.org/TR/annotation-model/",
    "selector": {
      "type": "TextQuoteSelector",
      "exact": "An annotation is a set of connected resources",
      "prefix": "body is most frequently",
      "suffix": ", typically including a body and target"
    }
  }
}
```

This JSON-LD expands to the following RDF triples:

```turtle
@prefix oa:      <http://www.w3.org/ns/oa#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf:    <http://xmlns.com/foaf/0.1/> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix dc:      <http://purl.org/dc/elements/1.1/> .

<http://example.org/anno1>
  a oa:Annotation ;
  oa:motivatedBy oa:commenting ;
  dcterms:created "2026-02-24T12:00:00Z"^^xsd:dateTime ;
  dcterms:creator <http://example.org/user/alice> ;
  oa:hasBody _:body1 ;
  oa:hasTarget _:target1 .

<http://example.org/user/alice>
  a foaf:Person ;
  foaf:name "Alice" .

_:body1
  a oa:TextualBody ;
  rdf:value "This is a key insight about semantic annotations." ;
  dc:format "text/plain" ;
  dc:language "en" .

_:target1
  a oa:SpecificResource ;
  oa:hasSource <https://www.w3.org/TR/annotation-model/> ;
  oa:hasSelector _:sel1 .

_:sel1
  a oa:TextQuoteSelector ;
  oa:exact "An annotation is a set of connected resources" ;
  oa:prefix "body is most frequently" ;
  oa:suffix ", typically including a body and target" .
```

### 1.4 W3C Web Annotation Protocol

The protocol (https://www.w3.org/TR/annotation-protocol/) is built on LDP (Linked Data Platform) and REST. Key features:

**Media type:** `application/ld+json;profile="http://www.w3.org/ns/anno.jsonld"`

**LDP Container model:**
- Annotations live inside an `AnnotationContainer` (an LDP BasicContainer)
- Container URL advertised via `Link` header: `rel="http://www.w3.org/ns/oa#annotationService"`
- Paging uses ActivityStreams `OrderedCollection` / `OrderedCollectionPage`

**CRUD operations:**

| Operation | HTTP Method | URL | Notes |
|-----------|-------------|-----|-------|
| Create | `POST` | `/annotations/` | Returns 201 with `Location` header |
| Read | `GET` | `/annotations/:id` | Returns JSON-LD |
| Update | `PUT` | `/annotations/:id` | Full replacement |
| Delete | `DELETE` | `/annotations/:id` | Returns 204 |
| Search/List | `GET` | `/annotations/?target=<url>` | Container query |

### 1.5 Hypothes.is W3C Compliance Assessment

**Partial compliance.** Key divergences:

1. **IDs are opaque strings, not IRIs.** Hypothes.is uses short IDs like `Ew0RwuGbEeyuByc-GpcK6g` and the full URI is `https://hypothes.is/a/{id}` — not natively embedded in the annotation JSON.
2. **Uses custom JSON format, not JSON-LD.** The Hypothes.is API returns plain JSON, not `application/ld+json`. There is no `@context` field.
3. **Target uses `source`/`selector` keys** which map to `oa:hasSource`/`oa:hasSelector` — this part aligns.
4. **Selector types match W3C vocabulary**: `TextQuoteSelector`, `TextPositionSelector`, `RangeSelector` are all W3C-defined types.
5. **Tags stored flat** as a `tags` array, not as `oa:tagging` motivation with body resources.
6. **Motivation not exposed** in the public API response — highlighting vs. commenting is encoded in whether `text` and `tags` are present.
7. **Permissions model** (read/admin/update/delete arrays) is Hypothes.is-specific, not W3C.

**Mapping is possible** — see Section 3 for the conversion approach.

---

## 2. Hypothes.is Open-Source Components

### 2.1 `h` — The Annotation Server

- **GitHub:** https://github.com/hypothesis/h
- **Language:** Python (Pyramid framework, not FastAPI)
- **License:** BSD-2-Clause
- **Stars:** ~3,100 (active project)
- **Database:** PostgreSQL (primary data store) + Elasticsearch (full-text search index)
- **Architecture:** Monolith web app. Serves the hypothes.is website, REST API at `/api/`, and annotation management. Uses Celery for background tasks, Redis for task queue.
- **Auth:** OAuth 2.0 with grant tokens for partner integrations; JWT tokens for the client
- **Self-hosting complexity:** HIGH. Requires: Python runtime, PostgreSQL, Elasticsearch, Redis, Celery workers, email setup. Comprehensive Docker Compose provided but non-trivial.
- **What it provides:** Full W3C-ish annotation storage API, user accounts, groups, moderation, search, admin UI.

### 2.2 `client` — The Browser Embed (Sidebar)

- **GitHub:** https://github.com/hypothesis/client
- **Language:** JavaScript (Preact-based sidebar, bundled)
- **License:** BSD-2-Clause
- **What it does:** The annotation sidebar injected into any web page. Handles text selection, highlight rendering, creating/viewing/filtering annotations. Communicates with an annotation server via HTTP API.
- **Embedding:** Single `<script>` tag: `<script src="https://hypothes.is/embed.js" async></script>`
- **PDF support:** Built-in. The client detects PDF.js and intercepts annotation operations to work with PDF documents. No server-side PDF processing needed.
- **Self-hosting:** Can be built and served from own infrastructure; `assetRoot` config option sets where client assets are loaded from.

### 2.3 `via` — The Web Proxy

- **GitHub:** https://github.com/hypothesis/via
- **Language:** Python (Pyramid) + NGINX
- **License:** BSD-2-Clause
- **What it does:** Proxies arbitrary web pages and PDF files, injecting the Hypothesis client so you can annotate third-party pages without embedding the script yourself.
- **PDF handling:** Via serves PDFs through NGINX with the client injected. It does NOT send PDFs to any external service — it proxies from the original URL. The PDF is loaded in the browser using PDF.js.
- **Configuration:** `CLIENT_EMBED_URL` sets which embed.js to use. `NGINX_SECURE_LINK_SECRET` for signed URL security.
- **Self-hosting complexity:** MEDIUM. Requires Python, NGINX, Docker. Simpler than `h` but still a separate service.
- **Use:** `https://via.hypothes.is/<url>` wraps any page/PDF with the annotation sidebar.

### 2.4 `bouncer` — Deep-Link Service

- **GitHub:** https://github.com/hypothesis/bouncer
- **Language:** Python
- **License:** BSD-2-Clause
- **What it does:** Accepts deep links to annotations (e.g., `https://hyp.is/{id}/{url}`) and redirects the browser to the annotated page with the sidebar open and the target annotation highlighted.
- **How:** On redirect, adds `#annotations:{id}` fragment or communicates with the Chrome extension. For pages that embed the client, the fragment triggers the client to open the correct annotation.
- **Self-hosting relevance:** Low for SemPKM — only needed if sharing annotation deep-links with external users.

### 2.5 Other Components in the Hypothesis GitHub Org

- **`lms`** — Learning Management System integration (Canvas, Blackboard, Moodle). Not relevant for SemPKM.
- **`checkmate`** — URL blocklist service used by Via to prevent proxying unsafe URLs.
- **`product-backlog`** — Public issue/idea tracker.
- **`browser-extension`** — Chrome/Firefox extension that embeds the client on any page without the script tag.

---

## 3. RDF / Linked Data Alignment

### 3.1 Hypothes.is JSON to W3C RDF Mapping

The Hypothes.is API returns this JSON structure (real example from the live API):

```json
{
  "id": "Ew0RwuGbEeyuByc-GpcK6g",
  "created": "2022-06-01T11:07:49.704817+00:00",
  "updated": "2022-06-01T11:07:49.704817+00:00",
  "user": "acct:zhurovandrew@hypothes.is",
  "uri": "https://www.w3.org/TR/annotation-model/",
  "text": "Why to have both source and selector when source can be a URI of a selector?",
  "tags": [],
  "group": "__world__",
  "permissions": {
    "read": ["group:__world__"],
    "admin": ["acct:zhurovandrew@hypothes.is"]
  },
  "target": [
    {
      "source": "https://www.w3.org/TR/annotation-model/",
      "selector": [
        {
          "type": "RangeSelector",
          "endOffset": 34,
          "startOffset": 0,
          "endContainer": "/section[6]/section[2]/div[1]/pre[1]/span[11]",
          "startContainer": "/section[6]/section[2]/div[1]/pre[1]/span[8]"
        },
        {
          "end": 71157,
          "type": "TextPositionSelector",
          "start": 71069
        },
        {
          "type": "TextQuoteSelector",
          "exact": "\"source\": \"http://example.org/page1\"",
          "prefix": ": \"Annotation\",\n  \"body\": {\n    ",
          "suffix": "\n  },\n  \"target\": {\n    \"source\""
        }
      ]
    }
  ],
  "document": {
    "title": ["Web Annotation Data Model"]
  }
}
```

**Field mapping to W3C RDF:**

| Hypothes.is field | W3C RDF property | Notes |
|-------------------|------------------|-------|
| `id` | `@id` → IRI `https://hypothes.is/a/{id}` | Must construct full IRI |
| `created` | `dcterms:created` | Direct mapping |
| `updated` | `dcterms:modified` | Direct mapping |
| `user` | `dcterms:creator` | Construct as `foaf:Agent` with `foaf:accountName` |
| `uri` | — | Redundant with `target[].source` |
| `text` | `oa:TextualBody` via `oa:hasBody` | `rdf:value` = text content |
| `tags[]` | `oa:TextualBody` with `oa:hasPurpose oa:tagging` | One body per tag |
| `target[].source` | `oa:hasSource` on `oa:SpecificResource` | Direct mapping |
| `target[].selector[].type` | `a` (rdf:type) on selector node | `oa:TextQuoteSelector` etc. |
| `target[].selector[].exact` | `oa:exact` | Direct mapping |
| `target[].selector[].prefix` | `oa:prefix` | Direct mapping |
| `target[].selector[].suffix` | `oa:suffix` | Direct mapping |
| `target[].selector[].start` | `oa:start` (xsd:nonNegativeInteger) | Direct mapping |
| `target[].selector[].end` | `oa:end` (xsd:nonNegativeInteger) | Direct mapping |
| `permissions.read` | `dcterms:accessRights` or custom | No direct W3C mapping — store as custom property |
| `group` | Custom `hyp:group` property | No W3C equivalent |
| `document.title` | `dcterms:title` on target source | Hint only |

**Data loss during conversion:** The Hypothes.is `permissions`, `group`, `references` (thread), `links`, `flagged`, `hidden`, and `moderation_status` fields have no W3C equivalents. These are Hypothes.is operational metadata. If roundtripping is needed, store them as custom `hyp:` namespace properties.

### 3.2 Proposed RDF Model for Storing a Hypothes.is Annotation in SemPKM's Triplestore

The following Turtle shows how a Hypothes.is annotation with a text highlight and comment would be stored as first-class RDF in SemPKM's RDF4J triplestore. It uses SemPKM's standard named graph pattern where each "event" or "resource" gets its own named graph.

```turtle
# Prefixes
@prefix oa:      <http://www.w3.org/ns/oa#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf:    <http://xmlns.com/foaf/0.1/> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix dc:      <http://purl.org/dc/elements/1.1/> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix sempkm:  <https://sempkm.example.org/ns/> .
@prefix hyp:     <https://hypothes.is/ns/> .

# Named graph for this annotation resource
# (follows SemPKM's per-resource named graph pattern)
<https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g> {

  # The annotation itself
  <https://hypothes.is/a/Ew0RwuGbEeyuByc-GpcK6g>
    a oa:Annotation ;
    oa:motivatedBy oa:commenting ;
    dcterms:created "2022-06-01T11:07:49.704817+00:00"^^xsd:dateTime ;
    dcterms:modified "2022-06-01T11:07:49.704817+00:00"^^xsd:dateTime ;
    dcterms:creator <https://hypothes.is/users/zhurovandrew> ;
    oa:hasBody <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/body> ;
    oa:hasTarget <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/target> ;
    # Hypothes.is-specific metadata preserved as custom properties
    hyp:group "__world__" ;
    hyp:originalId "Ew0RwuGbEeyuByc-GpcK6g" ;
    sempkm:isPartOf <https://sempkm.example.org/nodes/my-rss-article-node> .  # link to RSS article node

  # The comment body
  <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/body>
    a oa:TextualBody ;
    rdf:value "Why to have both source and selector when source can be a URI of a selector?" ;
    dc:format "text/plain" ;
    dc:language "en" .

  # The target (specific segment of the annotated resource)
  <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/target>
    a oa:SpecificResource ;
    oa:hasSource <https://www.w3.org/TR/annotation-model/> ;
    oa:hasSelector <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/selector/textquote> ;
    oa:hasSelector <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/selector/textpos> .

  # TextQuoteSelector (for re-anchoring text if page changes)
  <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/selector/textquote>
    a oa:TextQuoteSelector ;
    oa:exact "\"source\": \"http://example.org/page1\"" ;
    oa:prefix ": \"Annotation\",\n  \"body\": {\n    " ;
    oa:suffix "\n  },\n  \"target\": {\n    \"source\"" .

  # TextPositionSelector (for fast offset-based lookup)
  <https://sempkm.example.org/annotations/Ew0RwuGbEeyuByc-GpcK6g/selector/textpos>
    a oa:TextPositionSelector ;
    oa:start 71069 ;
    oa:end 71157 .
}
```

### 3.3 SPARQL Queries for Common Operations

**Find all annotations on a given URL:**
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>

SELECT ?annotation ?body_text ?created
WHERE {
  ?annotation a oa:Annotation ;
    oa:hasTarget ?target ;
    dcterms:created ?created .
  ?target oa:hasSource <https://example.com/article/some-rss-article> .
  OPTIONAL {
    ?annotation oa:hasBody ?body .
    ?body rdf:value ?body_text .
  }
}
ORDER BY ?created
```

**Find all annotations by a user:**
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?annotation ?source ?body_text
WHERE {
  ?annotation a oa:Annotation ;
    dcterms:creator <https://sempkm.example.org/users/alice> ;
    oa:hasBody ?body ;
    oa:hasTarget ?target .
  ?body rdf:value ?body_text .
  ?target oa:hasSource ?source .
}
```

**Find annotations by tag:**
```sparql
PREFIX oa: <http://www.w3.org/ns/oa#>

SELECT ?annotation ?source
WHERE {
  ?annotation a oa:Annotation ;
    oa:hasBody ?tagBody ;
    oa:hasTarget ?target .
  ?tagBody a oa:TextualBody ;
    oa:hasPurpose oa:tagging ;
    rdf:value "important" .
  ?target oa:hasSource ?source .
}
```

### 3.4 Namespace Conflict Check

SemPKM uses `sempkm:` for its own vocabulary. The `oa:` namespace (`http://www.w3.org/ns/oa#`) does not conflict with SemPKM's namespace. Both can coexist in the same triplestore. The `dcterms:` namespace (`http://purl.org/dc/terms/`) is already used by SemPKM for `dcterms:created`, `dcterms:modified`, and `dcterms:title` — these are the same vocabulary, no conflict.

---

## 4. SemPKM Use Case Designs

### 4a. In-Browser PDF Reader with Annotation Support

#### Option A: Use `via.hypothes.is` proxy (Zero self-hosting)

**How it works:** Link to `https://via.hypothes.is/<pdf-url>`. Via proxies the PDF through NGINX, injects the Hypothesis client (PDF.js + sidebar), and annotations are stored on the public hypothes.is service.

**Annotation flow:**
1. User navigates to `https://via.hypothes.is/https://example.com/paper.pdf`
2. PDF is served via proxy with hypothesis client embedded
3. User highlights text → annotation created on `hypothes.is` public service
4. To pull annotations into SemPKM: poll `https://hypothes.is/api/search?url=<pdf-url>` and import

**Pros:**
- Zero implementation effort
- Full PDF annotation UI out of the box
- Works immediately

**Cons:**
- PDF is proxied through hypothes.is (privacy concern for confidential documents)
- Annotations stored externally — not in SemPKM's RDF4J by default
- Requires hypothes.is account
- Import sync adds complexity

**Recommendation:** Suitable for public PDFs only. Not for private documents.

---

#### Option B: Embed Hypothes.is client in a custom PDF.js viewer hosted by SemPKM (Recommended)

**How it works:** SemPKM hosts a PDF viewer page built on PDF.js. The Hypothesis client's embed.js is included. The client automatically detects PDF.js and enables PDF annotation. Annotations are stored in SemPKM's own annotation backend (see storage option "Hybrid" in Section 5).

**Architecture:**
```
SemPKM Backend (FastAPI)
  ├── GET /viewer/pdf?url=<url>   → renders PDF viewer HTML page
  └── POST /api/annotations       → SemPKM annotation endpoint (W3C-compatible)
      └── → stores in RDF4J as oa:Annotation triples

Browser
  ├── PDF.js renders the PDF
  └── Hypothesis client sidebar
       ├── Detects PDF.js automatically
       ├── Reads annotation service config from window.hypothesisConfig()
       └── POSTs new annotations to SemPKM's /api/annotations endpoint
```

**Embed setup:**
```html
<!-- /templates/pdf_viewer.html -->
<script>
window.hypothesisConfig = function() {
  return {
    services: [{
      apiUrl: 'https://sempkm.example.org/api/annotations/',
      authority: 'sempkm.example.org',
      grantToken: '{{ grant_token }}'   // JWT issued by SemPKM for this user
    }]
  };
};
</script>
<script src="https://hypothes.is/embed.js" async></script>

<!-- PDF.js viewer container -->
<div id="viewerContainer">
  <div id="viewer" class="pdfViewer"></div>
</div>
<script src="/static/pdfjs/web/viewer.js"></script>
```

**Annotation creation flow:**
1. User opens `GET /viewer/pdf?url=<pdf-url>` in SemPKM
2. SemPKM renders a page with PDF.js and the Hypothesis client
3. User highlights text in the PDF
4. Hypothesis client sends `POST /api/annotations/` with W3C-format body
5. SemPKM stores annotation as RDF triples in RDF4J
6. Client retrieves annotations with `GET /api/annotations/?url=<pdf-url>`

**SemPKM API surface needed:**
- `POST /api/annotations/` — create annotation
- `GET /api/annotations/:id` — retrieve annotation
- `PATCH /api/annotations/:id` — update annotation
- `DELETE /api/annotations/:id` — delete annotation
- `GET /api/annotations/?url=<target-url>` — list by target URL

**PDF selector for RDF4J storage:**
PDF annotations use `oa:FragmentSelector` with the page fragment:
```turtle
_:pdfSelector a oa:FragmentSelector ;
  rdf:value "page=5&annotation=xywh=100,200,300,50" ;
  dcterms:conformsTo <http://www.w3.org/TR/media-frags/> .
```

**Pros:**
- Annotations stored in SemPKM RDF4J — SPARQL queryable
- No external dependency for annotation storage
- Full Hypothesis UI (highlight rendering, sidebar, search)
- PDF documents stay on user's network

**Cons:**
- Must implement the W3C-compatible API surface the Hypothesis client expects (Medium effort)
- Grant token generation requires auth integration

---

#### Option C: PDF.js alone with custom annotation layer (No Hypothesis client)

**How it works:** SemPKM builds its own text selection → annotation UI on top of PDF.js, without using the Hypothesis client at all.

**Pros:**
- Full control over UI
- No dependency on Hypothesis client
- Lighter weight (no 200KB+ client JS bundle)

**Cons:**
- High implementation effort (selection rendering, sidebar, threading, tags — all from scratch)
- Loses ecosystem compatibility (can't exchange annotations with other W3C-compliant systems)

**Recommendation:** Not recommended unless Hypothesis client limitations become a blocking issue. Use Option B instead.

---

### 4b. RSS Feed Reader Mental Model with Annotation Support

#### Concept

An RSS Feed Reader Mental Model in SemPKM would define:
- `feed:Feed` — an RSS/Atom feed source
- `feed:Article` — an individual article/item from a feed
- `feed:Annotation` — a W3C annotation tied to an article

When a user reads an article in SemPKM's workspace, they see it rendered in a web view with the Hypothesis sidebar embedded. Annotations are created against the canonical article URL (`oa:hasSource`) and stored in SemPKM's RDF4J as first-class nodes.

#### Mental Model Sketch

**Ontology classes (in `feed:` namespace, e.g., `https://sempkm.example.org/models/feed/ns/`):**

```turtle
feed:Feed a rdfs:Class ;
  rdfs:label "RSS Feed" .

feed:Article a rdfs:Class ;
  rdfs:label "Feed Article" .

feed:feedUrl a rdf:Property ;
  rdfs:domain feed:Feed ;
  rdfs:range xsd:anyURI .

feed:articleUrl a rdf:Property ;
  rdfs:domain feed:Article ;
  rdfs:range xsd:anyURI .   # This becomes oa:hasSource target URL

feed:fromFeed a rdf:Property ;
  rdfs:domain feed:Article ;
  rdfs:range feed:Feed .

feed:readAt a rdf:Property ;
  rdfs:domain feed:Article ;
  rdfs:range xsd:dateTime .
```

**SHACL shapes:**
```turtle
feed:ArticleShape a sh:NodeShape ;
  sh:targetClass feed:Article ;
  sh:property [
    sh:path dcterms:title ;
    sh:datatype xsd:string ;
    sh:minCount 1
  ] ;
  sh:property [
    sh:path feed:articleUrl ;
    sh:datatype xsd:anyURI ;
    sh:minCount 1
  ] ;
  sh:property [
    sh:path feed:fromFeed ;
    sh:class feed:Feed ;
    sh:minCount 1
  ] .
```

**How annotations attach to articles:**

Each `oa:Annotation` gets `sempkm:isPartOf` linking it to the `feed:Article` node that represents the article in SemPKM. The annotation's target uses the canonical article URL:

```turtle
<https://sempkm.example.org/nodes/article-xyz>
  a feed:Article ;
  dcterms:title "The Future of Semantic Web" ;
  feed:articleUrl <https://example.com/blog/semantic-web-future> ;
  feed:fromFeed <https://sempkm.example.org/nodes/feed-techblog> .

<https://sempkm.example.org/annotations/ann-001>
  a oa:Annotation ;
  oa:motivatedBy oa:commenting ;
  oa:hasTarget [
    a oa:SpecificResource ;
    oa:hasSource <https://example.com/blog/semantic-web-future>
  ] ;
  sempkm:isPartOf <https://sempkm.example.org/nodes/article-xyz> .
```

**Feed Article view in SemPKM workspace:**

The article view template would:
1. Render the article body (fetched from the original URL or stored in `dcterms:description`)
2. Embed `window.hypothesisConfig()` with the SemPKM annotation API and the user's grant token
3. Include `hypothes.is/embed.js`
4. The Hypothesis client sidebar shows existing annotations for `feed:articleUrl`

**Jinja2 template sketch:**
```html
<!-- templates/models/feed/article_view.html -->
{% extends "base.html" %}
{% block content %}
<article class="feed-article">
  <h1>{{ article.title }}</h1>
  <div class="article-body">{{ article.body | safe }}</div>
</article>

<script>
window.hypothesisConfig = function() {
  return {
    openSidebar: false,
    showHighlights: true,
    services: [{
      apiUrl: '{{ request.base_url }}api/annotations/',
      authority: '{{ request.host }}',
      grantToken: '{{ user_grant_token }}'
    }]
  };
};
</script>
<script src="https://hypothes.is/embed.js" async></script>
{% endblock %}
```

---

## 5. Storage Options Comparison

| Option | Description | Pros | Cons | Effort |
|--------|-------------|------|------|--------|
| **Self-host `h`** | Run full Hypothes.is server (Python/Pyramid) alongside SemPKM | Full W3C-compatible API; battle-tested annotation UI; groups, moderation, user management | Requires PostgreSQL + Elasticsearch + Redis + Celery in addition to existing RDF4J; data lives in Postgres/ES, NOT in RDF4J; annotations not SPARQL-queryable; two separate data stacks; heavy ops burden | High |
| **Hypothes.is public API** | Use `hypothes.is` cloud service; annotations stored externally; import via polling | Zero infra; works immediately; full-featured UI | External service dependency; data not in SemPKM's RDF store; rate limits (5000 req/day); requires user to have hypothes.is account; privacy concern for private notes; sync complexity | Low (initially) + ongoing sync complexity |
| **Store in RDF4J directly** | Build a W3C-compatible annotation REST API in SemPKM's FastAPI; store as `oa:Annotation` RDF triples | Data in SemPKM's RDF4J — SPARQL queryable alongside other knowledge; no extra infrastructure; full semantic alignment; annotations become first-class SemPKM nodes | Must implement the W3C Protocol API surface that the Hypothesis client expects; ~4-6 endpoints; grant token auth | Medium |
| **Hybrid: Hypothesis client + SemPKM backend** | Configure Hypothesis client with `services[].apiUrl` pointing to SemPKM's annotation API | Reuses the polished Hypothesis sidebar UI; annotations stored in RDF4J; no Elasticsearch/PostgreSQL dependency; semantic integration | Same as "Store in RDF4J directly" — must implement the client-expected API; grant token JWT generation needed | Medium (recommended) |

### Recommendation: Hybrid approach (Option 4 — Hypothesis client + SemPKM backend)

**Reasoning:**
1. **No extra infrastructure** — SemPKM already runs FastAPI + RDF4J. Adding ~6 annotation endpoints costs nothing infra-wise.
2. **Annotations become semantic nodes** — `oa:Annotation` resources stored in RDF4J are queryable via SPARQL, can be linked to Mental Model nodes, and participate in the event-sourced write path.
3. **Best UI with minimal effort** — The Hypothesis client sidebar is polished, handles PDF.js integration, text highlighting, and threading. Building an equivalent from scratch would take much longer.
4. **Data ownership** — User's annotations never leave their self-hosted SemPKM instance.
5. **W3C alignment** — Storing annotations as `oa:Annotation` RDF now means SemPKM can export/import annotations from any W3C-compliant system in the future.

**Implementation cost estimate:** Medium (~2-3 days for the annotation API endpoints + RDF storage + grant token auth).

---

## 6. Hypothes.is Client Embed API

### 6.1 Adding the Client to a Webpage

**Simplest (uses hypothes.is public service):**
```html
<script src="https://hypothes.is/embed.js" async></script>
```

**Self-hosted or custom backend:**
```html
<script>
window.hypothesisConfig = function() {
  return {
    services: [{
      apiUrl: 'https://your-sempkm.example.org/api/annotations/',
      authority: 'your-sempkm.example.org',
      grantToken: '<JWT grant token>'
    }]
  };
};
</script>
<script src="https://hypothes.is/embed.js" async></script>
```

**Using a `<script>` JSON config block (for static/server-side rendering):**
```html
<script type="application/json" class="js-hypothesis-config">
{
  "openSidebar": false,
  "showHighlights": true,
  "theme": "clean"
}
</script>
<script src="https://hypothes.is/embed.js" async></script>
```

### 6.2 Key Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `services` | Array | (public service) | Custom annotation backend configuration |
| `services[].apiUrl` | String | — | Base URL of the annotation REST API |
| `services[].authority` | String | — | Domain authority for user account format |
| `services[].grantToken` | String\|null | null | JWT for authenticated access; null = read-only |
| `services[].onLoginRequest` | Function | — | Called when user clicks login; host app handles auth |
| `services[].onLogoutRequest` | Function | — | Called when user clicks logout |
| `services[].groups` | String[] | all groups | Restrict which annotation groups are visible |
| `openSidebar` | Boolean | false | Auto-open sidebar on load |
| `showHighlights` | Boolean\|String | "always" | Show/hide highlights in the document |
| `theme` | String | "classic" | `"classic"` (full UI) or `"clean"` (minimal) |
| `usernameUrl` | String | — | URL prefix for user profile links |
| `enableExperimentalNewNoteButton` | Boolean | false | Show "New Note" button in sidebar |
| `groupsAllowlist` | String[] | — | Limit visible groups to these IDs |
| `branding` | Object | — | CSS color overrides for sidebar branding |

### 6.3 Custom Annotation Backend Configuration (`services`)

The `services` array lets the client connect to a custom annotation server instead of hypothes.is. For SemPKM integration:

```javascript
window.hypothesisConfig = function() {
  return {
    services: [{
      // SemPKM's annotation API endpoint
      apiUrl: 'https://sempkm.example.org/api/annotations/',

      // Must match the authority in user account format
      // Users will be identified as "acct:username@sempkm.example.org"
      authority: 'sempkm.example.org',

      // JWT grant token issued by SemPKM for the logged-in user
      // If null, user is read-only (can see but not create annotations)
      grantToken: null,  // replaced with server-rendered value

      // Called when user clicks "Log in" in the sidebar
      onLoginRequest: function() {
        window.location.href = '/auth/login?redirect=' + window.location.href;
      },

      // Called when user clicks "Log out"
      onLogoutRequest: function() {
        window.location.href = '/auth/logout';
      },

      // Disable the "Share" link on individual annotations
      enableShareLinks: false,

      // Allow users to leave groups
      allowLeavingGroups: false
    }]
  };
};
```

**Grant token format:** The grant token is a signed JWT with specific claims. For integration with a custom server, the format expected by the client is a JWT signed with a shared secret:
```json
{
  "iss": "your-service-client-id",
  "aud": "hypothes.is",  // or your authority domain
  "sub": "acct:username@sempkm.example.org",
  "nbf": 1234567890,
  "exp": 1234567890
}
```
The exact format needed depends on whether SemPKM uses the public Hypothesis client build (which expects `aud: "hypothes.is"`) or a self-hosted client build configured for the custom authority. For a fully self-hosted client, the authority can be any domain.

### 6.4 JavaScript Events Emitted by the Client

The Hypothesis client emits custom DOM events on `document.body`:

| Event | When | Payload |
|-------|------|---------|
| `hypothesis:layoutchange` | Sidebar opens, closes, or resizes | `{ sidebarLayout: { expanded, width, height, sideBySideActive } }` |

Additional events available only via `window.hypothesisConfig()` callback functions:
- `onLayoutChange(layout)` — called when sidebar layout changes (alternative to DOM event)
- `onLoginRequest()` — user clicked login
- `onLogoutRequest()` — user clicked logout
- `onSignupRequest()` — user clicked sign up
- `onProfileRequest()` — user clicked their username
- `onHelpRequest()` — user clicked help

**Example: React to sidebar open/close in SemPKM's layout:**
```javascript
document.body.addEventListener('hypothesis:layoutchange', function(event) {
  const layout = event.detail.sidebarLayout;
  if (layout.sideBySideActive) {
    // Sidebar is in side-by-side mode — shrink the main content area
    document.querySelector('.article-body').style.marginRight = layout.width + 'px';
  }
});
```

### 6.5 Filtering Which Annotations Are Shown

The `groups` option in the `services` config controls which groups' annotations appear:
```javascript
services: [{
  apiUrl: '...',
  groups: ['group-id-1', 'group-id-2']  // Only show these groups
}]
```

In SemPKM's model, each user's personal annotations can be placed in a private group (or the `__world__` public group), and the client filtered to show only annotations relevant to the current document.

### 6.6 Known Limitations for Use in Custom Apps

1. **Single services entry only:** Despite `services` being an array, only the first item is used. Multiple backends are not supported.
2. **iframe restrictions:** When loaded inside an iframe, clipboard operations require `allow="clipboard-write"` permission. Same-origin iframes can receive annotation support via `enable-annotation` attribute on the iframe element.
3. **Cross-origin iframes:** The client can only annotate iframes that are direct children of the top-level document and share the same origin. Cross-origin iframes cannot be annotated via the parent-frame client.
4. **PDF annotation requires PDF.js:** The built-in PDF annotation support works specifically with PDF.js. If you use a different PDF renderer, the Hypothesis client will not detect it automatically. The PDF.js viewer must expose the `PDFViewerApplication` global.
5. **Authentication complexity:** The grant token JWT approach requires careful implementation to avoid security issues (token expiry, CORS, CSRF). Short-lived tokens (5 minutes) with refresh are recommended.
6. **Bundle size:** The Hypothesis client embed.js is ~200-400KB (gzipped). This is significant for pages where annotation is not always needed. Consider lazy-loading it only when the PDF viewer or article reader is open.
7. **`services` is experimental API:** The official docs note that the `services` configuration is experimental and may change. When using a custom backend, pin the embed.js URL to a specific version rather than using the `latest` CDN URL.

---

## 7. Recommendations

### 7.1 Storage Strategy: Hybrid (Medium effort — recommended)

**Decision: Store annotations natively in SemPKM's RDF4J using the hybrid approach.**

Build a minimal W3C-compatible annotation REST API in SemPKM's FastAPI backend. Configure the Hypothesis client to use this API via the `services.apiUrl` setting. Annotations are stored as `oa:Annotation` RDF triples in RDF4J and become first-class nodes queryable via SPARQL.

**What to implement:**
```
POST   /api/annotations/          → Create annotation, store in RDF4J
GET    /api/annotations/:id       → Retrieve by ID
PATCH  /api/annotations/:id       → Update (partial)
DELETE /api/annotations/:id       → Delete (logical delete or remove named graph)
GET    /api/annotations/?url=...  → List by target URL (SPARQL lookup)
GET    /api/profile               → Current user profile (needed by client)
GET    /api/groups                → Groups list (return SemPKM user groups)
GET    /api/profile/groups        → User's groups
```

The client also needs a root discovery endpoint:
```
GET    /api/                      → JSON with `links` object describing API endpoints
```

**Grant token auth:** Generate a short-lived JWT (5 min expiry) for the authenticated SemPKM user. The client sends this as a Bearer token in annotation API requests. Verify with the same PyJWT library already in use.

**Estimated effort:** 2-3 days (API endpoints + RDF serialization/deserialization + grant token JWT issuance).

---

### 7.2 PDF Reader: Option B — Embedded Hypothesis client + PDF.js (Medium effort — recommended)

**Decision: Host a PDF viewer page in SemPKM using PDF.js with the Hypothesis client embedded, pointing to SemPKM's own annotation API.**

**Why:** PDF.js is the standard browser-based PDF renderer used by Firefox and Chrome. The Hypothesis client has native PDF.js integration — it automatically detects `PDFViewerApplication` and enables text selection and highlighting. This gives high-quality PDF annotation without building a custom annotation layer.

**Implementation sketch:**
1. Add a `/viewer/pdf` route to SemPKM that renders a PDF.js viewer HTML page
2. Serve PDF.js static assets from SemPKM's static directory
3. Embed the Hypothesis client configured to use SemPKM's annotation API
4. Pass the PDF URL as a query parameter; PDF.js loads it
5. Store annotations in RDF4J as `oa:FragmentSelector` with PDF page references

**PDF fragment selector format in RDF:**
```turtle
_:sel a oa:FragmentSelector ;
  rdf:value "page=3" ;
  dcterms:conformsTo <http://tools.ietf.org/rfc/rfc3778> .  # PDF media type RFC
```

**Estimated effort:** 1-2 days (PDF.js integration page + Hypothesis client config).

---

### 7.3 RSS Feed Reader: Embed Hypothesis client in article view (Low-Medium effort — recommended)

**Decision: Add Hypothesis client to SemPKM's feed article view template and link annotations to the `feed:Article` node via `sempkm:isPartOf`.**

The RSS feed reader is a Mental Model implementation decision. The annotation layer is orthogonal — it's just adding the Hypothesis client embed to whatever article view template the RSS Mental Model defines.

**Why not build a custom lightweight annotation layer:** The Hypothesis client already provides:
- Text selection detection
- Highlight rendering overlay
- Annotation threading (replies)
- Tag support
- Search within annotations

Building all of this from scratch for the RSS reader would take far longer than the hybrid API approach.

**Implementation sketch:**
1. Define the RSS Mental Model with `feed:Feed`, `feed:Article` classes and SHACL shapes
2. The article view template embeds the Hypothesis client pointed at SemPKM's annotation API
3. The client annotates `feed:articleUrl` as the target source
4. SemPKM's annotation API stores the annotation and adds `sempkm:isPartOf <article-node-iri>`
5. The article node's page in SemPKM can show a count of annotations via SPARQL

**Estimated effort:** 1 day (article view template + hook annotation API to article node).

---

### 7.4 Implementation Order

| Phase | Task | Effort | Prerequisite |
|-------|------|--------|-------------|
| 1 | Implement annotation REST API in SemPKM FastAPI | Medium (2-3 days) | None |
| 2 | Grant token JWT issuance for logged-in users | Low (0.5 day) | Phase 1 |
| 3 | PDF viewer page with PDF.js + Hypothesis client | Medium (1-2 days) | Phase 1 |
| 4 | RSS Feed Reader Mental Model with annotation support | Medium (2 days) | Phase 1 |

Total estimated effort: ~6-8 days of implementation.

---

## Appendix A: W3C vs. Hypothes.is API Field Mapping Summary

| W3C Field | Hypothes.is JSON | Direction | Notes |
|-----------|------------------|-----------|-------|
| `@context` | (absent) | W3C only | Must add on export |
| `id` (IRI) | `id` (opaque string) | Different | Must construct `https://hypothes.is/a/{id}` |
| `type: Annotation` | (implicit) | — | Must add on export |
| `oa:motivatedBy` | (implicit in `text`/`tags` presence) | Different | Infer: if `text` set → `oa:commenting`; if tags only → `oa:tagging` |
| `dcterms:created` | `created` | Same (datetime string) | Direct |
| `dcterms:modified` | `updated` | Same | Direct |
| `dcterms:creator` | `user` (acct: format) | Different | Construct `foaf:Agent` |
| `oa:hasBody` (TextualBody) | `text` (string) | Different | Must wrap in body object |
| `oa:hasBody` (tag body) | `tags[]` | Different | One body per tag with `oa:hasPurpose oa:tagging` |
| `oa:hasTarget[].source` | `target[].source` | Same | Direct |
| `oa:TextQuoteSelector.exact` | `target[].selector[{TextQuoteSelector}].exact` | Same | Direct |
| `oa:TextQuoteSelector.prefix` | `target[].selector[].prefix` | Same | Direct |
| `oa:TextQuoteSelector.suffix` | `target[].selector[].suffix` | Same | Direct |
| `oa:TextPositionSelector.start` | `target[].selector[{TextPositionSelector}].start` | Same | Direct |
| `oa:TextPositionSelector.end` | `target[].selector[].end` | Same | Direct |
| — | `group` | Hypothes.is only | Store as `hyp:group` |
| — | `permissions` | Hypothes.is only | Store as custom property or map to ACL |
| — | `document.title` | Hypothes.is only | Use as `dcterms:title` hint on source resource |

## Appendix B: Resources for Implementation

- W3C Web Annotation Data Model: https://www.w3.org/TR/annotation-model/
- W3C Web Annotation Protocol: https://www.w3.org/TR/annotation-protocol/
- W3C anno.jsonld context: https://www.w3.org/ns/anno.jsonld
- Hypothesis Client Docs: https://h.readthedocs.io/projects/client/en/latest/
- Hypothesis Client Config Reference: https://h.readthedocs.io/projects/client/en/latest/publishers/config.html
- Hypothesis h server GitHub: https://github.com/hypothesis/h
- Hypothesis via proxy GitHub: https://github.com/hypothesis/via
- Hypothes.is live API root: https://hypothes.is/api/
- PDF.js GitHub: https://github.com/mozilla/pdf.js
