---
phase: quick-003
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md
autonomous: true
requirements: [QUICK-003]
must_haves:
  truths:
    - "Research document exists covering the W3C Web Annotation standard and how Hypothes.is implements it"
    - "Document explains Hypothes.is open-source components and what each one does"
    - "Document describes how Web Annotations map to RDF and align with SemPKM's RDF store"
    - "Document provides concrete designs for two SemPKM use cases: PDF reader with annotations and RSS feed reader with annotations"
    - "Document compares storage options (self-host h, use Hypothes.is API, store in RDF4J) with a clear recommendation"
    - "Document explains the Hypothes.is embed/client JavaScript API for integration into a custom app"
  artifacts:
    - path: ".planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md"
      provides: "Research findings on Hypothes.is annotation technology and W3C Web Annotation standard for SemPKM integration"
  key_links:
    - from: "W3C Web Annotation Data Model"
      to: "SemPKM RDF4J store"
      via: "research document — RDF alignment section"
    - from: "Hypothes.is embed client JS"
      to: "SemPKM web UI"
      via: "research document — integration section"
---

<objective>
Research Hypothes.is annotation technology and the W3C Web Annotation standard to determine how SemPKM can integrate web annotation capabilities.

Purpose: SemPKM needs annotation support for two concrete use cases — an in-browser PDF reader and an RSS feed reader Mental Model. This research determines the technical approach, storage strategy, and integration pattern before any implementation begins.

Output: A research markdown document at `.planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md`
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fetch W3C Web Annotation standard and Hypothes.is component documentation</name>
  <files>.planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md</files>
  <action>
    Fetch documentation from the W3C Web Annotation standards, Hypothes.is developer docs, and related sources. Synthesize findings into a research document.

    Sources to fetch (in order):

    1. W3C Web Annotation Data Model:
       https://www.w3.org/TR/annotation-model/
       Focus on: Annotation structure, body/target/motivation vocabulary, how it maps to RDF triples, JSON-LD context

    2. W3C Web Annotation Protocol:
       https://www.w3.org/TR/annotation-protocol/
       Focus on: REST API design, container model, LDP compliance, endpoints for create/read/update/delete

    3. Hypothes.is developer docs overview:
       https://web.hypothes.is/developers/
       Focus on: Embedding options, API overview, open-source components listed

    4. Hypothes.is annotation API reference:
       https://h.readthedocs.io/en/latest/api-reference/
       Focus on: Annotation object structure, authentication, search endpoint, how it relates to W3C model

    5. Hypothes.is client (browser embed) docs:
       https://h.readthedocs.io/projects/client/en/latest/
       Focus on: How to embed in a webpage, configuration options, JavaScript API, events, custom storage backends

    6. Hypothes.is `h` server GitHub README:
       https://github.com/hypothesis/h
       Focus on: Architecture, dependencies, self-hosting complexity, license

    7. Hypothes.is `via` proxy:
       https://github.com/hypothesis/via
       Focus on: What via does (proxies web pages for annotation), whether it works with PDFs, how it relates to PDF.js

    8. Hypothes.is PDF support:
       https://web.hypothes.is/blog/annotating-pdfs-without-uploading-them/
       or https://h.readthedocs.io/projects/client/en/latest/publishers/embedding.html
       Focus on: How PDF annotation works in the Hypothes.is client (PDF.js integration)

    9. JSON-LD context for W3C Web Annotations:
       https://www.w3.org/ns/anno.jsonld
       Focus on: Namespace IRIs used, how annotation body/target/motivation terms map to full IRIs

    10. Hypothes.is annotation storage / backend architecture:
        https://h.readthedocs.io/en/latest/arch/
        or search within https://h.readthedocs.io/en/latest/ for storage/database sections
        Focus on: What database h uses, whether annotations can be stored externally, ElasticSearch vs PostgreSQL

    SemPKM context to keep in mind while researching:
    - SemPKM uses RDF, SPARQL 1.1, SHACL stored in RDF4J (triplestore)
    - Mental Models bundle ontology + SHACL shapes + view definitions + seed data
    - Event sourcing: sempkm:Edge, sempkm:Event, sempkm:Command are core types
    - Backend: Python/FastAPI, Jinja2 templates, htmx for partial updates
    - Frontend: vanilla JS (no framework), Split.js for panes, CodeMirror for editing
    - The two target use cases are:
      a. PDF reader: Open PDFs in-browser with Hypothes.is-style annotation (highlight + note)
      b. RSS feed reader: A Mental Model for reading RSS articles with annotation support
    - Annotations should ideally land in RDF4J as first-class RDF resources (not a separate silo)

    Write a research document covering:

    ## 1. W3C Web Annotation Standard
    - Data Model: Annotation as an RDF resource with body, target, motivation
    - Key classes and properties: oa:Annotation, oa:hasBody, oa:hasTarget, oa:TextQuoteSelector, oa:FragmentSelector, oa:motivatedBy, and common motivation types (oa:commenting, oa:highlighting, oa:tagging)
    - JSON-LD representation and full IRI equivalents (so we know what triples to store)
    - Protocol: REST API shape, LDP container model
    - How compliant is Hypothes.is with the W3C standard? (partial or full?)

    ## 2. Hypothes.is Open-Source Components
    For each component explain: what it is, what it does, license, self-hosting feasibility:
    - `h` — the annotation server (Python/Pyramid)
    - `client` — the browser embed (JavaScript sidebar)
    - `via` — the web proxy for third-party pages
    - `bouncer` — deep-linking service
    - Any other relevant components found in the GitHub org

    ## 3. RDF / Linked Data Alignment
    - How do Hypothes.is annotation JSON objects map to W3C Web Annotation RDF triples?
    - Can Hypothes.is annotations be round-tripped through RDF4J with no data loss?
    - What SPARQL queries would retrieve annotations by target URL, by user, by tag?
    - Proposed RDF model for storing a Hypothes.is annotation in SemPKM's triplestore (show example Turtle)
    - Does the oa: namespace conflict with any existing sempkm: vocabulary?

    ## 4. SemPKM Use Case Designs

    ### 4a. In-Browser PDF Reader with Annotation Support
    - Option A: Use `via.hypothes.is` proxy (simplest, no self-hosting, sends PDFs to hypothes.is)
    - Option B: Embed Hypothes.is client directly in a custom PDF.js viewer hosted by SemPKM
    - Option C: PDF.js alone with a custom annotation layer (no Hypothes.is client)
    - For each option: how annotations are created, where they are stored, how to retrieve them in SemPKM
    - Recommended option with rationale

    ### 4b. RSS Feed Reader Mental Model with Annotation Support
    - How a "Feed Article" page in SemPKM could embed the Hypothes.is client sidebar
    - How feed article URLs serve as annotation targets (oa:hasTarget pointing to the article URL)
    - How annotations become RDF resources in SemPKM alongside the Feed Article node
    - Mental Model sketch: what classes, properties, SHACL shapes would the RSS + Annotation Mental Model define?

    ## 5. Storage Options Comparison

    | Option | Description | Pros | Cons |
    |--------|-------------|------|------|
    | Self-host `h` | Run full Hypothes.is server | Full W3C API, battle-tested | Python/Pyramid stack, PostgreSQL + Elasticsearch required, heavy |
    | Hypothes.is public API | Use hypothes.is cloud service | Zero infra, instant | External dependency, data not in SemPKM RDF store, rate limits |
    | Store in RDF4J directly | Build minimal annotation REST layer, store as W3C RDF | Data in SemPKM store, SPARQL queryable, no extra infra | Must implement W3C Protocol subset ourselves |
    | Hybrid: client writes to SemPKM | Configure Hypothes.is client with custom `serviceUrl` pointing to a SemPKM endpoint | Reuse client UI, data stays in RDF4J | Must implement API surface the client expects |

    Include recommendation with rationale based on SemPKM's architecture.

    ## 6. Hypothes.is Client Embed API
    - How to add the client to a webpage (script tag, configuration)
    - Key configuration options: `services`, `assetRoot`, `sidebarAppUrl`
    - How to configure a custom annotation storage backend (`serviceUrl` in services config)
    - JavaScript events the client emits (annotation created, deleted, etc.)
    - How to filter which annotations are shown (by group, by user, by URL)
    - Any known limitations for use inside iframes or custom apps

    ## 7. Recommendations
    For each of the three main decisions, give a clear recommendation:
    1. Storage: which option to use for SemPKM and why
    2. PDF reader: which approach (via proxy, embedded client, or PDF.js standalone)
    3. RSS reader: whether to embed Hypothes.is client or build a lighter custom annotation layer
    Include estimated implementation complexity for each (low/medium/high).

    Format the output as readable markdown with code blocks for RDF/Turtle examples and JSON examples. Be specific — cite actual W3C IRI names (oa:Annotation, oa:hasTarget, etc.) and actual Hypothes.is API fields.
  </action>
  <verify>File exists at `.planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md` with all 7 sections, including an RDF/Turtle example of an annotation and a storage options comparison table.</verify>
  <done>Research document exists, cites actual W3C Web Annotation vocabulary by IRI, covers both SemPKM use cases with concrete designs, and provides clear recommendations for storage strategy and integration approach.</done>
</task>

</tasks>

<verification>
- `.planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md` exists and is non-empty
- Document contains actual W3C annotation IRI references (e.g., `oa:Annotation`, `oa:hasTarget`, `oa:TextQuoteSelector`)
- Document contains a concrete RDF/Turtle example showing how an annotation would be stored in SemPKM's triplestore
- Document covers both PDF reader and RSS reader use cases
- Storage options comparison table is present
- Recommendations are concrete (not vague) with rationale
</verification>

<success_criteria>
A developer reading this document can decide within 10 minutes which storage approach to use and which PDF/RSS integration pattern to implement, without needing to read any external documentation first.
</success_criteria>

<output>
After completion, create `.planning/quick/3-research-hypothes-is-annotation-technolo/003-SUMMARY.md` with standard summary frontmatter including: what was researched, key findings, storage recommendation chosen, and any follow-up implementation tasks identified.
</output>
