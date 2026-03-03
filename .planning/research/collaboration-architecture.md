# Collaboration & Federation Architecture Research

**Created:** 2026-03-03
**Context:** Deep research into how SemPKM (self-hosted, RDF triplestore-backed PKM) could support teams and collaboration. Evaluated SOLID, ActivityPub/Fediverse, RDF sync protocols, CRDTs, and hypertext-native patterns.

---

## Executive Summary

No single protocol is production-ready for collaborative RDF knowledge management in 2026. The recommended path is a **layered, incremental architecture** built on proven components: RDF Patch for change tracking, SPARQL Graph Store Protocol for graph exchange, Linked Data Notifications for cross-instance awareness, and WebID for federated identity. Real-time co-editing via CRDTs should wait for the W3C CRDT-for-RDF standardization effort to mature.

---

## 1. SOLID (Social Linked Data) Protocol

### How It Works

A [SOLID Pod](https://solidproject.org/) is a personal data store where all data lives as Linked Data resources (Turtle/JSON-LD) accessible via HTTP. Pods implement [LDP (Linked Data Platform)](https://www.w3.org/TR/ldp/) — data organized into containers holding resources. Authentication uses [WebID](https://www.w3.org/wiki/WebID) and [Solid-OIDC](https://solid.github.io/solid-oidc/). Access control via [WAC (Web Access Control)](https://solidproject.org/TR/wac) or ACP.

### Current State (2024-2026)

- **Governance:** [ODI took stewardship](https://theodi.org/news-and-events/news/odi-and-solid-come-together-to-give-individuals-greater-control-over-personal-data/) of Solid in October 2024
- **W3C:** [Linked Web Storage WG](https://www.w3.org/2024/09/linked-web-storage-wg-charter.html) targeting Candidate Recommendation by March 2026, full Rec by September 2026
- **Servers:** [Community Solid Server](https://github.com/CommunitySolidServer/CommunitySolidServer) (TypeScript, experimental TRL 1-3), [Enterprise Solid Server](https://www.inrupt.com/blog/enterprise-server-release) (Inrupt, commercial)
- **SHACL integration:** The [Solid Application Interoperability](https://solid.github.io/data-interoperability-panel/specification/) spec uses shapes for data validation — direct alignment with SemPKM

### Honest Assessment

A [detailed developer critique](https://blog.ldodds.com/2024/03/12/baffled-by-solid/) raises concerns: no commercial Pod hosting, no query API (document store not triplestore), poor UIs, missing pagination/search/timestamps. A [Solid app developer confirms](https://noeldemartin.com/blog/why-solid) RDF complexity and authentication friction remain pain points.

### Verdict for SemPKM

**Philosophically aligned, practically mismatched.** Pods are document stores — no SPARQL. Our triplestore *is* the data store. Monitor W3C standardization but don't adopt as infrastructure. Potentially useful as an interoperability target (export/import to Pods).

---

## 2. ActivityPub / Fediverse

### How It Works

[ActivityPub](https://www.w3.org/TR/activitypub/) (W3C Recommendation) has two sub-protocols: Client-to-Server (apps POST to user outbox) and Server-to-Server (servers deliver to recipient inboxes). Activities are JSON-LD documents — inherently RDF, though most implementations treat as opaque JSON.

### Non-Social Uses

- **[ForgeFed](https://forgefed.org/):** Federated code forges (Gitea/Forgejo cross-instance issues and merge requests)
- **[Bonfire](https://bonfirenetworks.org/):** Modular federated platform for coordination, governance, groups ([TechCrunch coverage](https://techcrunch.com/2025/06/05/bonfires-new-software-lets-users-build-their-own-social-communities-free-from-platform-control/))
- **[ActivityPods](https://activitypods.org/):** Combines ActivityPub federation with Solid Pod storage; [v2.0 roadmap](https://activitypods.org/the-road-to-activitypods-2-0) adds CRDT-based RDF sync via NextGraph partnership
- **[rdf-pub](https://rdf-pub.org/):** ActivityPub server supporting full RDF (not limited to ActivityStreams), uses rdf4j — pre-alpha
- **openEngiadina/CPub:** Attempted full RDF ActivityPub — [development discontinued](https://codeberg.org/openengiadina/cpub/), moved to XMPP

### Knowledge Sharing Pattern

[SocialHub discussion](https://socialhub.activitypub.rocks/t/federated-knowledge-management-with-activitypub/2991) proposes dual compatibility: generic fediverse services see basic title/summary, specialized nodes interpret full structured RDF data. Directly applicable to SemPKM.

### Verdict for SemPKM

**Good transport layer, wrong data model.** JSON-LD payloads map directly to our RDF, but the protocol is designed for social streams not knowledge graphs. The RDF-native implementations have failed or stalled. Use selectively for notifications/sharing, not as primary sync.

---

## 3. RDF Synchronization

### RDF Patch / RDF Delta

[RDF Patch](https://afs.github.io/rdf-patch/) is a text format for triple-level changes: `A <s> <p> <o>` (add), `D <s> <p> <o>` (delete), wrapped in transactions. [RDF Delta](https://afs.github.io/rdf-delta/) builds a replication system on top: a Delta Server hosts patch logs, clients fetch since last known version. Supports "Replicated Fuseki." **Note:** [RDF Delta is archived](https://github.com/afs/rdf-delta) (unmaintained), but concepts remain foundational.

### Jelly-Patch (2025)

[Jelly-Patch](https://jelly-rdf.github.io/dev/) is a binary RDF patch format built on Protocol Buffers. Published at SEMANTiCS 2025 ([paper](https://arxiv.org/html/2507.23499v1)): 3.5-8.9x better compression, up to 2.5x serialization throughput, 4.6x parsing throughput vs text-based patches. Java implementation (Apache 2.0); Python/Rust planned.

### SPARQL Graph Store Protocol

[W3C SPARQL 1.1 Graph Store HTTP Protocol](https://w3c.github.io/sparql-graph-store-protocol/) provides REST ops on named graphs: GET, PUT, POST (merge), DELETE. Coarse-grained (whole graphs) but directly supported by Fuseki/RDF4J.

### Linked Data Notifications (LDN)

[W3C Recommendation](https://www.w3.org/TR/ldn/) for decentralized notifications. Senders POST JSON-LD to receiver's Inbox (LDP container). Used for [credential exchange between Solid Pods](https://ceur-ws.org/Vol-3705/short04.pdf). Lightweight, RDF-native.

### Changeset Vocabularies

- **ChangeSet vocabulary:** Resource-centric, linking statements-to-add/remove
- **[eccrev (eccenca Revision Vocabulary)](https://github.com/eccenca/eccrev-vocab):** Based on Delta ontology, reuses PROV-O for provenance
- **[PROV-O](https://www.w3.org/TR/prov-o/):** W3C provenance ontology for who/when/why metadata

### Verdict for SemPKM

**The most practical building blocks.** RDF Patch is simple enough to implement in Python. Graph Store Protocol works with our existing triplestore. LDN adds lightweight notifications. These form the foundation of Layer 1 and Layer 2 in the recommended architecture.

---

## 4. Hypertext / Web-Native Collaboration

### Webmention

[W3C Recommendation](https://www.w3.org/TR/webmention/) for peer-to-peer web notifications. When site A links to site B, A sends an HTTP POST to B's endpoint. B can display it as a comment/reference. Simple, [well-adopted in IndieWeb](https://indieweb.org/Webmention).

### Linked Data Platform (LDP)

[W3C LDP 1.0](https://www.w3.org/TR/ldp/) defines REST patterns for RDF resource management: LDP Resources (documents via GET/PUT/DELETE), LDP Containers (collections, POST to create). Solid is built as an LDP profile. [Multiple implementations](https://www.w3.org/wiki/LDP_Implementations) (Fedora, Carbon LDP, Eclipse Lyo).

### Content-Addressable RDF

- **[IPLD (InterPlanetary Linked Data)](https://docs.ipfs.tech/concepts/merkle-dag/):** Merkle DAGs with hash-based addressing, used by IPFS
- **Timestamp-based integrity proofs:** Sorted Merkle trees from RDF datasets for verification
- Enables: verifiable snapshots, deduplication during sync, tamper detection

### dokieli

[dokieli](https://dokie.li/) ([paper](https://csarven.ca/dokieli-rww)) is a fully decentralized browser-based authoring platform: HTML+RDFa documents, LDP for storage, LDN for notifications, WebID for auth. Proves decentralized RDF collaboration works for real-world authoring.

### Verdict for SemPKM

**Webmention and LDN are low-hanging fruit** for cross-instance awareness. LDP provides clean CRUD if we ever expose graphs as web resources. Content-addressing is future-state for verification.

---

## 5. Self-Hosted + Cloud Coordination Patterns

### Matrix Protocol Model

[Matrix](https://matrix.org/) is federated real-time communication: event-based DAG in rooms, full state replication, E2E encryption, self-hostable. A [5-year self-hosting retrospective](https://yaky.dev/2025-11-30-self-hosting-matrix/) confirms viability but notes resource intensity. **Insight:** Matrix's "room" model maps well to "shared named graphs."

### Git-Like Sync for RDF

- **[Quit Store (Quads in Git)](https://github.com/AKSW/QuitStore):** Python-based, stores named graphs as N-Triples in Git, provides SPARQL 1.1 endpoint, supports branching/merging/push/pull. 1,031 commits, last significant activity 2022.
- **[Radicle](https://radicle.xyz):** P2P code collaboration on Git. Not RDF-specific but its replication model could inform graph sharing.

### CRDTs for RDF

**[W3C CRDT for RDF Community Group](https://www.w3.org/community/crdt4rdf/)** (est. October 2024, 27 members): coordinating efforts to specify CRDTs for RDF.

**[NextGraph](https://nextgraph.org/):** Novel CRDT designed for RDF, P2P, E2E encrypted, uses Oxigraph locally. Alpha stage, SDK published July 2025. [Partnering with ActivityPods](https://activitypods.org/activitypods-and-nextgraph-are-joining-forces) to replace Jena Fuseki.

**[m-ld](https://m-ld.org/doc/):** Decentralized live RDF sharing, embeds as library, eventual consistency, pluggable messaging. JS-only developer preview. [Paper](https://ceur-ws.org/Vol-2941/paper1.pdf).

### Pattern Comparison

| Pattern | Examples | Pros | Cons |
|---------|----------|------|------|
| **Hub-and-spoke cloud** | Notion, Google Docs | Simple, strong consistency | Single point of failure, data sovereignty |
| **Federated (S2S)** | Matrix, ActivityPub, Email | Self-hostable, resilient, proven | Complex state resolution, server-bound identity |
| **Peer-to-peer** | NextGraph, Radicle | Max sovereignty, offline-first | NAT traversal, discovery, key management |
| **Git-like (DVCS)** | Quit Store | Familiar, branching/merging, full history | RDF merge conflicts hard, no real-time |

### Verdict for SemPKM

**Federated (server-to-server) is the pragmatic choice** for self-hosted scenarios. CRDTs for RDF are the future but pre-standard. Quit Store's concepts (Git-backed graphs) could inform our versioning layer. NextGraph is the one to watch for Layer 4.

---

## 6. Real-World Examples

| Tool | Model | Lesson for SemPKM |
|------|-------|--------------------|
| **[Semantic MediaWiki](https://www.semantic-mediawiki.org/)** | Wiki editing + version history, 10+ years production | Simplest model wins. RDF behind the scenes. |
| **[dokieli](https://dokie.li/)** | Decentralized RDF authoring, LDP+LDN+WebID | Proves decentralized RDF collaboration works |
| **[Relay for Obsidian](https://relay.md/)** | CRDT-based folder-level sharing plugin | Local-first PKM adds collab via plugins, not core rewrites |
| **[ActivityPods](https://activitypods.org/)** | Solid + ActivityPub + NextGraph convergence | Most ambitious integration; too early to adopt |
| **Notion** | Cloud-first, operational transform | Users expect seamless real-time — anything less feels broken |

---

## Recommended Architecture: Layered & Incremental

Rather than betting on a single protocol, build incrementally using proven components:

### Layer 1: Named Graph Sync (Build First)

**Pattern:** RDF Patch logs + HTTP sync endpoint

1. Wrap triplestore writes to emit RDF Patch log entries
2. Expose a `/sync` endpoint serving patches since a given version
3. "Remote" configuration pointing to other SemPKM instances
4. Pull-based sync: periodically fetch patches from configured remotes
5. Named graph-level conflict detection (reject if base version diverged)

**Why first:** Uses existing triplestore, no new infra, solves core "share knowledge between instances" use case.

### Layer 2: Cross-Instance Notifications (Build Second)

**Pattern:** Linked Data Notifications + Webmention

- Instance A modifies a subscribed graph → sends LDN notification to instance B
- Instance A references instance B's content → sends Webmention
- Notifications trigger pull-based sync from Layer 1

### Layer 3: Federated Identity (Build Third)

**Pattern:** WebID for cross-instance identity

- Each SemPKM user gets a WebID (profile URL on their instance)
- Cross-instance permissions use WebID to identify remote users
- ACL on named graphs references WebIDs
- Local auth unchanged

### Layer 4: Real-Time Collaboration (Future)

**Pattern:** CRDT-based RDF sync (when ecosystem matures)

- Monitor W3C CRDT for RDF CG
- Watch NextGraph alpha → stable progression
- Integrate when mature Python/JS CRDT-for-RDF library exists

### What NOT to Build

- **Don't build a Solid Pod server** — different problem (app-data separation), no SPARQL
- **Don't implement full ActivityPub S2S** — enormous complexity, wrong use case
- **Don't build a custom CRDT** — W3C is standardizing this, wait
- **Don't try P2P yet** — NAT traversal unsolved for self-hosted; federated is pragmatic

---

## Technology Fitness Matrix

| Technology | SemPKM Fit | Maturity | Effort | Recommendation |
|-----------|-----------|----------|--------|----------------|
| RDF Patch | Excellent | Proven format | Medium | **Build Layer 1 on this** |
| Graph Store Protocol | Excellent | W3C Rec | Low | Use for full graph exchange |
| Linked Data Notifications | Good | W3C Rec | Low | **Build Layer 2 on this** |
| WebID | Good | W3C | Medium | **Build Layer 3 on this** |
| Webmention | Moderate | W3C Rec | Low | Add for cross-referencing |
| ActivityPub (C2S only) | Moderate | W3C Rec | High | Consider for external API |
| SOLID Protocol | Low-Moderate | Pre-Rec | Very High | Monitor only |
| NextGraph CRDT | High (future) | Alpha | N/A | **Monitor for Layer 4** |
| m-ld | Moderate | JS-only preview | High | Monitor |
| Quit Store | Moderate | Unmaintained | Medium | Borrow concepts |

---

## Projects to Watch

- **[NextGraph](https://nextgraph.org/)** — RDF CRDT, E2E encrypted, P2P. If it reaches stable, could be turnkey Layer 4
- **[W3C CRDT for RDF CG](https://www.w3.org/community/crdt4rdf/)** — standardization progress
- **[ActivityPods 2.0](https://activitypods.org/our-roadmap-for-2025)** — Solid + ActivityPub + NextGraph convergence
- **[Jelly-Patch](https://jelly-rdf.github.io/dev/)** — when Python/Rust implementations land
- **[Linked Web Storage WG](https://www.w3.org/2024/09/linked-web-storage-wg-charter.html)** — Solid standardization timeline

---

*Research conducted: 2026-03-03*
*Sources: 40+ web pages across W3C specs, GitHub repos, developer blogs, academic papers, and project documentation*
