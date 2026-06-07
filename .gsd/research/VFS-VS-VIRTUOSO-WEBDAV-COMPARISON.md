# SemPKM VFS vs. Virtuoso WebDAV — Side-by-Side Comparison

> **Status:** Research
> **Date:** 2026-05-15
> **Sources:** Kingsley Idehen, *"Virtuoso, WebDAV, Knowledge Graphs & AI: Reuniting Databases…"* (LinkedIn, 2025); OpenLink Virtuoso documentation; Virtuoso open-source NEWS; ODS-Briefcase wiki; VAL/VirtLDP wiki pages
> **Context:** Companion to `VFS-WRITE-THROUGH-DESIGN.md`. Compares our proposed VFS write-through design against Virtuoso's WebDAV+RDF stack — the most mature production system in this space (20+ years old).

---

## TL;DR

Virtuoso and SemPKM both stitch WebDAV onto an RDF store, but they're **inversions of each other**. Virtuoso's source of truth is a SQL table of DAV resources (`WS.WS.SYS_DAV_RES`), with RDF derived on top via triggers and the Sponger pipeline. SemPKM's source of truth is the triplestore, with the VFS as a derived projection.

This single architectural difference cascades into nearly every design choice. Virtuoso optimizes for "make heterogeneous external content addressable as RDF" (Dropbox, S3, IMAP, arbitrary files). SemPKM optimizes for "make a structured knowledge graph navigable as a filesystem." Neither is wrong; they're solving different problems.

Where Virtuoso is years ahead: **plug-in folder behaviors (DETs)**, **LDP/Solid integration**, **external-service mounts**, **declarative ACLs in RDF (VAL/WAC)**. Where SemPKM is doing something genuinely novel: **markdown-aware writes** (wiki-link sync, frontmatter modes), **content-addressed blob storage**, **multi-subtree mount specs with filter satisfiability**, **multi-path projection of one object**, **rename-safe IRI/path binding**.

---

## 1. The architectural inversion (this is the whole story)

```
Virtuoso:                                  SemPKM:
┌────────────────────────────┐             ┌────────────────────────────┐
│  WebDAV clients            │             │  WebDAV clients            │
└────────────┬───────────────┘             └────────────┬───────────────┘
             ▼                                          ▼
┌────────────────────────────┐             ┌────────────────────────────┐
│  WS.WS.SYS_DAV_RES         │             │  VFS provider              │
│  (SQL table, BLOB content) │             │  (computed projection)     │
│  ★ SOURCE OF TRUTH         │             └────────────┬───────────────┘
└────────────┬───────────────┘                          ▼
             │                              ┌────────────────────────────┐
             │ triggers, sponger,           │  RDF event store           │
             │ DET callbacks                │  (named graphs in RDF4J)   │
             ▼                              │  ★ SOURCE OF TRUTH         │
┌────────────────────────────┐             └────────────────────────────┘
│  RDF quad store            │
│  (derived; per-file +      │
│   public aggregate graphs) │
└────────────────────────────┘
```

**Consequence #1:** In Virtuoso, the DAV path **is** the resource IRI. Move the file → new IRI. Delete the file → bytes gone, derived RDF orphaned (Virtuoso clears the per-file private graph but the docs explicitly say to `SPARQL CLEAR GRAPH` for any aggregate triples — there's no automatic cleanup of the public graph).

In SemPKM, the IRI is UUID-based and the path is a slug. Rename is free; cross-path identity is preserved; the event store provides clean history.

**Consequence #2:** Virtuoso ingests *anything* and tries to derive RDF (the Sponger cartridge pipeline matches by MIME and URL pattern, emitting SIOC/FOAF/SKOS/EXIF/Annotea triples). SemPKM goes the other way — RDF is authored or imported as structured data, and the VFS is a navigable view of what's already typed.

**Consequence #3:** Virtuoso's "make external services queryable" pitch (DETs for S3, Dropbox, IMAP, OneDrive, Box, Azure, Nextcloud — all mounted as DAV folders with vendor-native API calls under the hood) is something SemPKM doesn't try to do. SemPKM's mount story is purely a projection of its own triplestore.

---

## 2. Feature-by-feature

| Concept | Virtuoso | SemPKM (proposed) | Verdict |
|---|---|---|---|
| **Source of truth** | SQL DAV table | RDF triplestore | Inverted models; each fits its goal |
| **Bytes storage** | `RES_CONTENT BLOB` in SQL | Content-addressed disk (`/data/blobs/<sha>`) | Different — see §3 |
| **Path → identity** | Path IS the IRI | Path = slug; IRI = UUID | SemPKM wins on rename safety |
| **One object at many paths** | Not built-in (one URL = one row) | Yes — same ETag at every matching subtree path | SemPKM win |
| **Multi-folder views** | "Smart Folders" (MIME filter), PropFilter/CatFilter DETs | Ordered subtree specs, SPARQL-filter-driven | Both have it; SemPKM unified, Virtuoso plug-in |
| **SPARQL-backed virtual folders** | DynaRes DET (saved query → result as file) | Filter-driven subtree (query → projected paths) | Different shapes — Virtuoso returns query *results*, SemPKM projects matching *objects* |
| **Filter satisfiability gating writes** | No equivalent | First-class — drives PUT-create authorization | SemPKM novelty |
| **Markdown frontmatter handling** | Absent (markdown is opaque text from RDF side) | Three modes per subtree (strict / passthrough / promote) | SemPKM win |
| **Wiki-link `[[…]]` → RDF edges** | Absent — no built-in Markdown link extractor | Sync on every save → `dcterms:references` edges; `bpkm:unresolvedRef` for late reconciliation | SemPKM novelty |
| **Embed `![[image.png]]` semantics** | Absent | Distinct predicate (`bpkm:embeds` / `foaf:depiction`) | SemPKM novelty |
| **Rename propagation** | Not applicable — rename = new IRI (no incoming-link rewrite) | Title patch → edge query → body rewrite in all sources | SemPKM novelty |
| **Type inference on upload** | Sponger cartridge pipeline (MIME-matched, RM_ID-ordered) | Subtree's `default_type` + filter-derived properties | Different mechanisms; Virtuoso richer for non-markdown |
| **Multi-type promotion (file stays `bpkm:File`, gains `bpkm:ResearchArticle`)** | Sponger can add extra `rdf:type`; no user-driven promotion UX | First-class workspace action; adds without replacing; demotable | SemPKM win on UX |
| **External-service mounts (Dropbox, S3, IMAP)** | DETs with native vendor APIs | Not in scope | Virtuoso win (but explicitly OOS for us) |
| **LDP integration** | First-class — one `LDP=ldp:BasicContainer` property turns a DAV folder into an LDP container; PUT Turtle creates LDPRs; `Accept: text/turtle` returns `ldp:contains` | None | Virtuoso win |
| **Solid pod hosting** | Yes (WebID-TLS + WAC + LDP all present) | None | Virtuoso win |
| **Authentication** | SQL users, WebID-TLS, VAL (RDF-based ACL engine using W3C WAC + OpenLink ACL ontologies) | Existing SemPKM auth (SQLite users, magic links, API tokens) | Different layers; Virtuoso's RDF-ACL is more expressive |
| **Versioning** | DeltaV referenced but not centrally documented; per-DET | Event-sourced, full history via existing event store | SemPKM win (it's our core model) |
| **WebDAV LOCK** | Supported (RFC 4918 baseline) | Planned (mapped to event-store optimistic concurrency) | Parity once shipped |
| **Custom PROPFIND properties** | Application properties allowed; no auto-mirror of arbitrary RDF predicates as DAV props | Planned `sempkm:*` namespace exposing `objectIri`, `appearsAt`, `backlinkCount`, etc. | SemPKM going further |
| **WebDAV SEARCH (RFC 5323)** | Not prominently documented | Planned (SPARQL pass-through) | Parity (both backlog) |
| **Folder behavior plug-ins** | DET is a full plug-in API — register a SQL package implementing `DAV_DIR_LIST_INT` etc. | Subtree specs are config, not code | Different philosophies; see §4 |
| **Per-folder RDF graph binding** | `virt:rdf_graph` property → triples from RDF uploads land in named graph | Implicit — all writes go to `urn:sempkm:current` | Virtuoso more flexible for multi-tenant; SemPKM single-tenant by design |
| **Bidirectional protocol surfaces** | Same URL is DAV resource + named graph + LDP resource simultaneously | DAV path only; semantic surface lives in workspace endpoints | Virtuoso win on protocol unification |

---

## 3. The bytes-storage choice in detail

Virtuoso puts bytes in `WS.WS.SYS_DAV_RES.RES_CONTENT` — a SQL BLOB. Everything in one database file. Pros: backup is one file, transactional consistency with metadata, no extra GC path. Cons: triplestore size balloons with file content, SQL BLOB performance ceilings, no natural deduplication.

SemPKM's proposed content-addressed disk store (`/data/blobs/<hash[0:2]>/<hash>`) gets free deduplication and keeps the triplestore lean. Cons: backups now need two paths, deletion is logical (event-sourced), and we eventually need a GC story.

Neither is "right." Virtuoso optimizes for *operational simplicity* (one database, one backup) at the cost of scalability. SemPKM optimizes for *scalability and clean separation* at the cost of operational complexity. SemPKM's choice is defensible *if and only if* we're serious about supporting large files (PDFs, images, video) — which we are, given the Obsidian-vault and Quarto use cases.

---

## 4. The DET plug-in model — worth borrowing?

Virtuoso's most powerful idea is **DETs (DAV Extension Types)** — register a SQL package implementing the DAV callback API (`DAV_DIR_LIST_INT`, `DAV_RES_UPLOAD_INT`, etc.) and a folder behaves like whatever you want. Built-in DETs include:

- `rdf_sink` — auto-load RDF on PUT
- `DynaRes` — SPARQL query saved as `.rq`, executed on GET, results returned as the file body
- `RDFData` — user profile/triples exposed as files
- `PropFilter` / `CatFilter` / `ResFilter` — declarative filters
- `S3 / Dropbox / GoogleDrive / OneDrive / IMAP / Nextcloud / FTP` — external service mounts

This is a genuinely good architectural pattern: folder behavior is a *strategy* (in the design-pattern sense), pluggable per-folder, with the WebDAV layer providing a clean call surface.

**Our model is currently config-only.** Subtree specs are data (filter + default_type + accepts), not code. This is right for the 95% case — declarative is simpler and safer than scripting — but we should keep DETs in mind as a *future* extension point. If a user wanted "every file in `/Inbox/` runs through an LLM that suggests a type before commit," that's a DET-style hook. We don't need it now, but the architecture should leave room.

**Concrete suggestion:** add a single optional `pre_create_hook` and `post_create_hook` field to `SubtreeSpec`, initially unused, so the door is open without committing to the full plug-in surface.

---

## 5. LDP/Solid — should we care?

Virtuoso's LDP integration is genuinely elegant: one property on a folder turns it into an LDP container, and the same URL serves DAV, raw content, and LDP-Turtle depending on `Accept`. Solid pod hosting falls out for free.

The strategic question is whether SemPKM should ever be a Solid pod. Arguments for:

- Federation story (M013's API surface + future M037 mobile) would benefit from LDP-shaped endpoints
- Solid is the closest thing to a standard for personal-data-pods, and the WebID-TLS infrastructure is already partially built (M002 added WebID profiles)
- Idehen's framing — *"folder tree as the agent UX"* — aligns with our copilot/MCP-server backlog items

Arguments against:

- LDP semantics for containers/membership conflict with our multi-subtree projection model (LDP assumes one container = one set of members; we have N filter-driven views over the same set)
- Solid's auth model (WAC over WebID) parallels but doesn't match our existing auth
- The full LDP test suite is a significant compliance burden

**My read:** not now. Revisit when we ship the MCP server (queued from M002) and need a standard surface for AI agents. At that point LDP-compatibility-mode for the VFS becomes a real option rather than a speculation. The custom PROPFIND properties we're planning (`sempkm:objectIri`, `sempkm:appearsAt`, etc.) are forward-compatible with adding LDP/Turtle responses later via content negotiation.

---

## 6. Where Idehen is right, and where it matters for us

The article's core claim — *"WebDAV reunites databases and file systems"* — is correct, and it's the same intuition driving our VFS work. The agent-UX angle (*"the folder tree is the right abstraction because both humans and agents already know it"*) is also right. These are not Virtuoso-specific insights; they're protocol-level insights, and any RDF-store-with-WebDAV is a candidate to realize them.

Where Idehen's framing is *less* applicable to SemPKM:

- His "drop a Turtle file → triples appear" pitch assumes users author RDF. **Our users don't** — they author markdown (with structure inferred from frontmatter) or import from Obsidian/Notion. The Sponger pipeline is overkill when the input is already structured.
- His "mount Dropbox/S3/IMAP as DAV folders" is a *consumption* story (heterogeneous data → unified query surface). Ours is a *production and curation* story (intentional knowledge graph → multiple navigation surfaces). Different goals, same protocol.
- His LDP/Solid framing assumes interoperability with the broader Solid ecosystem matters. For SemPKM in 2026 it doesn't yet — we're a single-tenant tool — but it might in 2027 once we have an MCP server.

---

## 7. Specific things we should consider stealing

1. **Per-subtree RDF graph binding.** Virtuoso's `virt:rdf_graph` per folder is a clean idea. We currently dump everything into `urn:sempkm:current`. A `target_graph` field on `SubtreeSpec` would let users segregate (e.g.) work-from-personal in the triplestore without changing the path-level UX. Cheap to add to S01.

2. **DET-style hook points.** Add optional `pre_create_hook` / `post_create_hook` fields now (unused), so we don't have to add them later via schema migration. See §4.

3. **Smart Folders' MIME-filter shorthand.** Virtuoso lets you write `Items/Graphics/Type/JPEG` and it auto-filters by MIME. We could provide path templates with the same affordance (`/{ext}/`) as a strategy alongside `by-tag`, `by-date`, etc.

4. **The "files-as-graph" framing for documentation.** Idehen's *"the URL is the file is the graph"* one-liner is a great teaching device. We should use a version of it in the user guide chapter on VFS — something like *"in SemPKM, the path is a view, the IRI is the identity, and edits flow to the object."*

5. **VAL-style RDF ACLs (long-term).** Not for now, but if/when we go multi-user beyond the current model, an RDF-encoded ACL using W3C WAC is a more expressive and standards-aligned answer than building our own ACL system. Worth a research milestone before any multi-tenant work.

---

## 8. Specific things we should *not* steal

1. **Bytes in SQL BLOBs.** Doesn't scale to PDFs and images. Content-addressed disk is the right call for us.
2. **The Sponger pipeline.** Cartridge-based metadata extraction is overkill for our authored-content workflow. Frontmatter + filter inference is sufficient.
3. **Path-as-IRI.** Rename safety is too important for the Obsidian-compat story.
4. **One URL = one row.** Multi-path projection of the same object is core to our model and absent from theirs.

---

## 9. Documentation gaps from the research

Things we couldn't confirm about Virtuoso (in case we want to verify before borrowing ideas):

- Exact `WS.WS.SYS_DAV_RES` column DDL (OpenLink wiki returns 403 to most automated fetchers)
- Whether `MOVE` on a sink-loaded file rewrites the per-file private graph IRI (likely not)
- Trailing flag character semantics in `:virtpermissions` strings
- Whether LDP POST `Slug:` is honored deterministically (community evidence suggests no)
- DeltaV versioning behavior — referenced in NEWS, not centrally documented
- Generic mechanism to surface arbitrary RDF predicates as PROPFIND custom XML

If we decide to borrow any specific mechanism (per-folder graph binding, DET-style hooks), worth one focused research pass against running Virtuoso to confirm behavior empirically.

---

## 10. Bottom line

Virtuoso has solved a *superset* of the problem we're solving — they ingest, query, federate, version, ACL, and serve heterogeneous content over RDF+WebDAV across SQL/SPARQL/LDP/IMAP — and they've been doing it since the late 1990s. But they've solved it for a different user: the data-integration engineer who needs to unify a corporate data estate. They have not solved the *PKM* problem (markdown-as-first-class, wiki-link backlinks, Obsidian-vault compat, blob storage with type promotion, multi-path-with-shared-identity), and their architectural choices (SQL-of-record, path-as-IRI) actively conflict with how we'd want to solve it.

**Our design is correctly differentiated.** The novel pieces — wiki-link sync, frontmatter modes, multi-subtree filter satisfiability, content-addressed blobs, multi-type promotion, multi-path-via-ETag — aren't there in Virtuoso and aren't trivially addable. The pieces where Virtuoso is ahead (DET plug-ins, LDP, external mounts, VAL ACLs) are either out of scope for us or candidates for *later* milestones once we've shipped the PKM-specific work.

Strategic posture: build what we designed; don't pivot to LDP/Solid compatibility now; add a `target_graph` per-subtree and reserve hook fields in the schema for forward compatibility with DET-style behaviors; revisit LDP and RDF-ACL when the MCP server lands and multi-user becomes real.

---

## Source notes

- Idehen article gated behind LinkedIn auth — thesis verified via search snippets and parallel Idehen writings on Medium/LinkedIn
- Virtuoso documentation gathered from `docs.openlinksw.com`, `vos.openlinksw.com`, the `openlink/virtuoso-opensource` GitHub repo (NEWS, issues), and `vemonet/virtuoso-ldp` (the cleanest public LDP-on-Virtuoso example)
- Specific OpenLink wiki pages with concrete technical detail: `VirtWebDAV`, `VirtLDP`, `VirtuosoRDFSinkFolder`, `VirtSpongerWhitePaper`, `BriefcaseFAQ`, `ValQuickStartGuide`, `VirtSparqlCxmlDETs` (DynaRes)
- RFCs referenced: 4918 (WebDAV), 3253 (DeltaV), 5842 (BIND), 5323 (SEARCH), 4437 (Redirect refs)
