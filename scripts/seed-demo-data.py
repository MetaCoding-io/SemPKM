#!/usr/bin/env python3
"""Seed demo data into a SemPKM demo instance.

Runs inside the Docker container via:
    docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py

Phases:
    1. Install Mental Models (crm, zettelkasten, research — basic-pkm auto-installs at startup)
    2. Create cross-model edges connecting objects across model boundaries
    3. Set markdown bodies on key objects for rich demo content
    4. Create demo user row and pre-built demo dashboard
    5. Verify: count objects, models, edges, bodies, dashboards and print summary

Idempotent: safe to run multiple times. Models are checked before install,
edges are checked via SPARQL ASK before creation, bodies are inherently
idempotent (replace existing).

Usage:
    python /app/scripts/seed-demo-data.py              # full seed
    python /app/scripts/seed-demo-data.py --verify-only # just run verification
"""

import argparse
import asyncio
import json
import sys
import uuid as _uuid
from pathlib import Path

# Ensure /app is on sys.path so 'app' package is importable when running
# via `python /app/scripts/seed-demo-data.py` inside the Docker container.
_app_root = str(Path(__file__).resolve().parent.parent)
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)

import httpx
from sqlalchemy import func, select

from app.auth.models import User
from app.commands.handlers.body_set import handle_body_set
from app.commands.handlers.edge_create import handle_edge_create
from app.commands.schemas import BodySetParams, EdgeCreateParams
from app.config import settings
from app.dashboard.models import DashboardSpec
from app.db.session import async_session_factory
from app.events.store import EventStore
from app.models.registry import is_model_installed
from app.services.models import ModelService
from app.services.prefixes import PrefixRegistry
from app.triplestore.client import TriplestoreClient
from app.triplestore.setup import ensure_repository

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------
BPKM = "urn:sempkm:model:basic-pkm:"
CRM = "urn:sempkm:model:crm:"
ZK = "urn:sempkm:model:zettelkasten:"
RES = "urn:sempkm:model:research:"

# ---------------------------------------------------------------------------
# Demo user / dashboard well-known UUIDs
# ---------------------------------------------------------------------------
DEMO_USER_UUID = _uuid.UUID("00000000-0000-0000-0000-000000000000")
DEMO_DASHBOARD_UUID = _uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

# ---------------------------------------------------------------------------
# Phase 2: Cross-model edges
# ---------------------------------------------------------------------------
CROSS_MODEL_EDGES: list[dict[str, str]] = [
    # basic-pkm Person ↔ crm Contact (people know CRM contacts)
    {
        "source": f"{BPKM}seed-person-alice",
        "target": f"{CRM}seed-contact-sarah",
        "predicate": f"{BPKM}knows",
        "label": "Alice knows Sarah (CRM contact)",
    },
    {
        "source": f"{BPKM}seed-person-bob",
        "target": f"{CRM}seed-contact-james",
        "predicate": f"{BPKM}knows",
        "label": "Bob knows James (CRM contact)",
    },
    # basic-pkm Note → research Paper (architecture note references KG survey)
    {
        "source": f"{BPKM}seed-note-architecture",
        "target": f"{RES}seed-paper-kg-survey",
        "predicate": f"{BPKM}isAbout",
        "label": "Architecture note references KG survey paper",
    },
    # basic-pkm Note → zettelkasten PermanentNote (graph viz idea relates to emergent structure)
    {
        "source": f"{BPKM}seed-note-graph-viz",
        "target": f"{ZK}seed-perm-emergent-structure",
        "predicate": f"{BPKM}hasRelatedNote",
        "label": "Graph viz idea relates to emergent structure note",
    },
    # basic-pkm Concept → research Claim (knowledge mgmt concept linked to KG reduces silos claim)
    {
        "source": f"{BPKM}seed-concept-knowledge-management",
        "target": f"{RES}seed-claim-kg-reduce-silos",
        "predicate": f"{BPKM}isAbout",
        "label": "Knowledge management concept relates to KG-reduces-silos claim",
    },
    # basic-pkm Concept → zettelkasten PermanentNote (semantic web concept to cognitive load note)
    {
        "source": f"{BPKM}seed-concept-semantic-web",
        "target": f"{ZK}seed-perm-cognitive-load",
        "predicate": f"{BPKM}relatedConcept",
        "label": "Semantic web concept relates to cognitive load note",
    },
    # crm Contact → research Paper (Sarah is author of PKM tools paper)
    {
        "source": f"{CRM}seed-contact-sarah",
        "target": f"{RES}seed-paper-pkm-tools",
        "predicate": f"{CRM}knows",
        "label": "CRM contact Sarah linked to PKM tools paper",
    },
    # zettelkasten Source → research Paper (Ahrens source references KG survey)
    {
        "source": f"{ZK}seed-source-ahrens",
        "target": f"{RES}seed-paper-kg-survey",
        "predicate": f"{ZK}relatedTo",
        "label": "Zettelkasten source Ahrens relates to KG survey paper",
    },
    # zettelkasten PermanentNote → basic-pkm Concept (confirmation bias note → event sourcing concept)
    {
        "source": f"{ZK}seed-perm-confirmation-bias",
        "target": f"{BPKM}seed-concept-event-sourcing",
        "predicate": f"{ZK}relatedTo",
        "label": "Confirmation bias note relates to event sourcing concept",
    },
    # research Claim → basic-pkm Project (PKM adoption claim relates to SemPKM project)
    {
        "source": f"{RES}seed-claim-pkm-adoption",
        "target": f"{BPKM}seed-project-sempkm",
        "predicate": f"{RES}addresses",
        "label": "PKM adoption claim relates to SemPKM project",
    },
    # research ResearchQuestion → zettelkasten StructureNote (PKM effectiveness question → case for structured notes)
    {
        "source": f"{RES}seed-rq-pkm-effectiveness",
        "target": f"{ZK}seed-structure-case",
        "predicate": f"{RES}addresses",
        "label": "PKM effectiveness question relates to structured note-taking case",
    },
    # basic-pkm Project → crm Deal (SemPKM project linked to platform deal)
    {
        "source": f"{BPKM}seed-project-sempkm",
        "target": f"{CRM}seed-deal-platform",
        "predicate": f"{BPKM}relatedProject",
        "label": "SemPKM project linked to platform licensing deal",
    },
]

# ---------------------------------------------------------------------------
# Phase 3: Markdown bodies
# ---------------------------------------------------------------------------
MARKDOWN_BODIES: dict[str, str] = {
    f"{BPKM}seed-note-architecture": """\
# Architecture Decision: Event Sourcing

## Context

SemPKM needed a persistence strategy that preserves the full history of every \
knowledge graph change while supporting real-time materialized views. After \
evaluating several approaches, event sourcing with RDF materialization was chosen.

## Key Decisions

- **Immutable event graphs**: Every write creates a named graph containing the \
operation metadata and data triples. These are never modified or deleted.
- **Current-state materialization**: A `urn:sempkm:current` graph is maintained \
by applying INSERT/DELETE operations atomically within the same RDF4J transaction.
- **SPARQL-native**: Both event storage and materialization use standard SPARQL \
UPDATE operations — no proprietary APIs.

## Trade-offs

| Aspect | Benefit | Cost |
|--------|---------|------|
| History | Full audit trail for every change | Storage grows linearly |
| Queries | Fast reads from materialized graph | Write path is 2× slower |
| Debugging | Can replay any point in time | Replay tooling not built yet |

## Lessons Learned

1. **Transaction boundaries matter** — materializing inserts before deletes \
caused race conditions with RDF4J's MVCC. Always delete first, then insert.
2. **Variable naming** — SPARQL DELETE WHERE patterns need unique variable names \
per triple pattern to avoid unintended joins across patterns.
3. **Graph isolation** — keeping ontology, shapes, and user data in separate \
named graphs prevents accidental cross-contamination during SHACL validation.
""",
    f"{BPKM}seed-note-kickoff": """\
# Meeting: Project Kickoff

**Date:** 2025-01-15  
**Attendees:** Alice, Bob, Carol

## Agenda

1. Project scope and timeline
2. Technology stack decisions
3. Role assignments
4. Next steps

## Discussion Notes

Alice presented the vision for SemPKM as a *semantic personal knowledge manager* \
that uses RDF and SHACL to provide structured, validated, interconnected knowledge \
management. The key differentiator is **Mental Models** — installable ontology \
packages that define types, shapes, views, and seed data.

Bob raised concerns about RDF complexity for end users. The team agreed that the \
UI must abstract away RDF terminology completely — users see "objects," "types," \
and "connections," never "triples," "predicates," or "named graphs."

Carol volunteered to lead the frontend work, focusing on:
- **Explorer** panel with tree/table/graph views
- **Object editor** with SHACL-driven form generation
- **Validation** dashboard showing SHACL-AF rule results

## Action Items

- [ ] Alice: Draft architecture decision record for event sourcing
- [ ] Bob: Set up CI/CD pipeline with Docker Compose
- [x] Carol: Create wireframes for explorer panel
""",
    f"{BPKM}seed-note-graph-viz": """\
# Idea: Graph Visualization

## The Problem

Knowledge graphs are powerful but invisible. Users create objects and connections \
but can't *see* the emergent structure of their knowledge. A graph visualization \
would make implicit patterns explicit.

## Approaches Considered

### 1. Force-directed layout (chosen)
- Uses physics simulation to position nodes
- Naturally clusters connected nodes together
- Interactive: drag, zoom, filter by type
- Libraries: D3.js, Cytoscape.js, Sigma.js

### 2. Hierarchical layout
- Good for tree-like structures
- Breaks down with many cross-links
- Better for specific views (project → tasks → milestones)

### 3. Radial layout
- Centers on a selected node
- Shows "neighborhood" clearly
- Useful for ego-centric views

## Design Principles

1. **Type coloring**: Each Mental Model type gets a distinct color from its \
manifest icon configuration
2. **Edge labels**: Show the predicate (relationship type) on hover
3. **Filtering**: Toggle visibility by type, model, or connection depth
4. **Performance**: Limit to ~500 nodes; paginate or cluster beyond that

## Open Questions

- How to handle nodes that belong to multiple models (via cross-model edges)?
- Should the graph show *all* edges or only user-created ones?
- What's the right default zoom level for a knowledge base with 50-100 objects?
""",
    f"{ZK}seed-perm-cognitive-load": """\
# Externalized Thinking Reduces Cognitive Load

## Core Insight

When we externalize our thinking into a structured system — writing things down, \
connecting ideas explicitly, organizing by relevance rather than chronology — we \
free up working memory for *new* thinking rather than *remembering* old thinking.

## Supporting Evidence

Ahrens (2017) argues that the slip-box works because it serves as an "external \
scaffold for thinking." Instead of trying to hold an entire argument in your head, \
you can:

1. **Capture** fleeting thoughts without pressure to organize
2. **Process** them into permanent notes with explicit connections
3. **Retrieve** related ideas through the link structure, not memory

## Connection to SemPKM

This is exactly what SemPKM's Mental Model architecture enables:
- **FleetingNotes** capture raw thoughts (low cognitive cost)
- **PermanentNotes** crystallize refined ideas (high value)
- **Edges** make connections explicit and browsable
- **SHACL rules** surface forgotten notes (unprocessed fleeting notes get warnings)

## Implications for Design

The UI should minimize friction for *capture* (quick-add, keyboard shortcuts) \
and maximize visibility of *connections* (graph view, backlinks, related objects). \
The goal is to make the system feel like an extension of thought, not a database \
to be administered.
""",
    f"{ZK}seed-perm-emergent-structure": """\
# Structure Emerges from Connections, Not Planning

## The Zettelkasten Principle

Luhmann's key insight was that you don't need to plan the structure of your \
knowledge in advance. Instead, structure *emerges* from the connections between \
individual notes. Start with atomic ideas, link them, and clusters form naturally.

## How This Manifests

In practice, this means:

- **No rigid hierarchies**: Notes aren't filed into folders. They're linked to \
other notes. The "structure" is the link graph itself.
- **Structure notes as indices**: When a cluster of notes grows large enough, a \
**StructureNote** acts as a curated entry point — like a table of contents for \
an emergent topic.
- **Serendipitous discovery**: Because notes are linked by *content* rather than \
*category*, browsing often surfaces unexpected connections.

## Anti-patterns

1. **Over-categorization**: Creating elaborate folder hierarchies before you have \
content. This front-loads decisions you don't have information to make yet.
2. **Orphan notes**: Notes without any links. They're invisible to the structure \
and will be forgotten. (SemPKM's SHACL rules warn about these.)
3. **Hub notes**: A single note linked to everything. This creates a false center \
that doesn't represent real conceptual structure.

## Connection to Graph Visualization

This principle is why graph visualization is so valuable for Zettelkasten-style \
systems — you can *see* the emergent clusters, identify orphans, and discover \
unexpected bridges between topics.
""",
    f"{ZK}seed-structure-case": """\
# The Case for Structured Note-Taking

## Overview

This structure note collects the core arguments for why structured, semantic \
note-taking systems outperform unstructured approaches (plain text files, \
simple markdown folders, etc.) for long-term knowledge work.

## Key Arguments

### 1. Typed Objects Enable Validation
When notes have explicit types (FleetingNote, PermanentNote, LiteratureNote), \
the system can enforce quality rules:
- Fleeting notes should be processed within a week
- Literature notes need a source reference
- Permanent notes should have at least one connection

### 2. Explicit Connections Beat Implicit Links
Wiki-style `[[backlinks]]` rely on name matching. Typed edges with predicates \
(`supports`, `contradicts`, `followsFrom`) carry semantic meaning that enables:
- Filtering connections by relationship type
- Traversing specific argument chains
- Detecting logical contradictions

### 3. Multiple Views Over Same Data
The same knowledge graph can be rendered as:
- A **table** for systematic review
- A **graph** for structural insight
- **Cards** for browsing and discovery
- A **timeline** for chronological analysis

### 4. Validation as a Thinking Tool
SHACL-AF rules aren't just data quality checks — they're *thinking prompts*:
- "You have 3 unprocessed fleeting notes" → reminder to reflect
- "This claim has no supporting evidence" → research prompt
- "This contact hasn't been reached in 90 days" → relationship maintenance

## Related Notes

- [[Externalized thinking reduces cognitive load]]
- [[Structure emerges from connections, not planning]]
- [[Confirmation bias threatens knowledge systems]]
""",
    f"{RES}seed-paper-kg-survey": """\
# Knowledge Graphs: A Survey of Techniques and Applications

## Summary

This survey paper provides a comprehensive overview of knowledge graph \
construction, representation, and application across enterprise and personal \
domains. It covers RDF/OWL foundations, graph databases, embedding techniques, \
and emerging applications in personal knowledge management.

## Key Takeaways

1. **Knowledge graphs reduce information silos** by providing a unified schema \
that connects data across domains. This is the core thesis that motivated \
SemPKM's multi-model architecture.
2. **Ontology-driven approaches** (RDF + SHACL) provide stronger guarantees \
than property-graph databases for data quality and interoperability.
3. **The cold-start problem** remains the biggest barrier to personal KG adoption. \
Users need compelling seed data and low-friction entry points.

## Relevance to SemPKM

This paper's framework for evaluating KG systems directly informed the \
Mental Model architecture:

| Paper Criterion | SemPKM Implementation |
|----------------|----------------------|
| Schema flexibility | Installable Mental Models with versioned ontologies |
| Data quality | SHACL shapes for form generation + SHACL-AF rules for validation |
| Query capability | SPARQL over RDF4J with materialized current-state graph |
| Extensibility | New models can define types, shapes, views, rules, and seed data |

## Open Research Questions

- How to measure "knowledge graph utility" for personal use cases?
- What's the optimal granularity for knowledge graph objects?
- How do cross-model edges affect reasoning and validation?
""",
    f"{RES}seed-paper-pkm-tools": """\
# Personal Knowledge Management Tools: A Comparative Analysis

## Summary

A systematic comparison of 12 PKM tools (Notion, Obsidian, Roam Research, \
Logseq, Tana, etc.) across dimensions of structure, extensibility, \
collaboration, and data portability. The paper identifies a gap in \
*semantically-aware* PKM tools that combine the flexibility of note-taking \
with the rigor of knowledge representation.

## Key Findings

1. **Adoption follows simplicity**: Tools with lower learning curves (Notion, \
Apple Notes) have 10-100× the user base of structured tools (Tana, Roam). \
But power users consistently migrate toward more structured systems.
2. **Lock-in is the primary pain point**: 8 of 12 tools use proprietary \
storage formats. Users report anxiety about data portability.
3. **Validation is absent**: No surveyed tool provides automated quality \
checks on knowledge content. Users rely on manual review.

## The Gap SemPKM Fills

| Dimension | Typical PKM Tools | SemPKM |
|-----------|------------------|--------|
| Storage | Proprietary JSON/SQLite | Open RDF (SPARQL endpoint) |
| Schema | Fixed or implicit | Explicit, installable Mental Models |
| Validation | None | SHACL shapes + SHACL-AF rules |
| Portability | Export to markdown | Native RDF/JSON-LD, standard vocabularies |
| Extensibility | Plugins/templates | Full ontology packages with seed data |

## Implications

The paper argues that the next generation of PKM tools will need to balance \
*simplicity of capture* with *richness of structure*. SemPKM's approach — \
where structure comes from Mental Models, not user effort — is one answer.
""",
    f"{BPKM}seed-concept-knowledge-management": """\
# Knowledge Management

## Definition

Knowledge management (KM) is the systematic process of creating, sharing, using, \
and managing the knowledge and information of an organization or individual. In \
the personal context, it focuses on capturing, organizing, and retrieving \
information to support thinking, learning, and decision-making.

## Historical Context

KM evolved through several waves:

1. **1990s — Enterprise KM**: Focused on codifying organizational knowledge into \
databases and intranets. Largely top-down, often failed due to lack of adoption.
2. **2000s — Social KM**: Wikis, blogs, and social bookmarking. Bottom-up, but \
lacked structure and quality control.
3. **2010s — Personal KM**: Rise of Evernote, then Notion, Obsidian, Roam. \
Individual-focused, but fragmented across tools.
4. **2020s — Semantic KM**: Knowledge graphs, linked data, AI-assisted \
organization. SemPKM sits here.

## Core Challenges

- **Capture friction**: The easier it is to capture, the more people capture. \
But low-friction capture produces low-quality knowledge.
- **Organization overhead**: Every organizational scheme has maintenance costs. \
The best systems minimize this through automation and inference.
- **Retrieval**: Knowledge is only valuable if you can find it when you need it. \
Full-text search is necessary but not sufficient — semantic search over typed, \
connected data is the next step.

## Connection to This Project

SemPKM addresses these challenges through:
- **Mental Models** that provide pre-built organization
- **SHACL validation** that automates quality checks
- **Graph views** that surface connections for retrieval
""",
    f"{BPKM}seed-concept-event-sourcing": """\
# Event Sourcing

## Definition

Event sourcing is an architectural pattern where state changes are stored as an \
immutable sequence of events, rather than by mutating a single current-state \
record. The current state is derived by replaying (or materializing) events.

## How SemPKM Uses Event Sourcing

Every write operation in SemPKM — creating an object, setting a body, adding an \
edge — produces an **immutable event named graph** containing:

- Operation type (e.g., `object.create`, `body.set`, `edge.create`)
- Timestamp
- Actor (user IRI)
- Data triples (the actual RDF changes)

The current state is maintained in a **materialized graph** (`urn:sempkm:current`) \
that is updated atomically within the same RDF4J transaction that writes the event.

## Benefits

1. **Full audit trail**: Every change is recorded. You can answer "who changed \
what and when?" for any object.
2. **Time travel**: By replaying events up to a specific timestamp, you can \
reconstruct the state of any object at any point in history.
3. **Conflict resolution**: For federation scenarios, events from different \
instances can be merged by timestamp ordering.
4. **Debugging**: When something goes wrong, you can examine the exact sequence \
of events that led to the current state.

## Trade-offs

- **Storage cost**: Events accumulate forever. Compaction strategies may be \
needed for long-running instances.
- **Write complexity**: Every write is two operations (event + materialization) \
in a single transaction. This adds latency.
- **Query complexity**: Queries run against the materialized graph, not the \
event stream. This is fast for reads but means the materialization logic \
must be correct.
""",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_header(phase: int, total: int, title: str) -> None:
    """Print a phase header."""
    print(f"\n{'='*60}")
    print(f"[{phase}/{total}] {title}")
    print(f"{'='*60}")


async def _edge_exists(client: TriplestoreClient, source: str, target: str, predicate: str) -> bool:
    """Check if a cross-model edge already exists via SPARQL ASK."""
    sparql = f"""ASK {{
  GRAPH <urn:sempkm:current> {{
    ?edge a <urn:sempkm:Edge> ;
          <urn:sempkm:source> <{source}> ;
          <urn:sempkm:target> <{target}> ;
          <urn:sempkm:predicate> <{predicate}> .
  }}
}}"""
    result = await client.query(sparql)
    return result.get("boolean", False)


# ---------------------------------------------------------------------------
# Phase implementations
# ---------------------------------------------------------------------------

async def phase_install_models(
    client: TriplestoreClient,
    model_service: ModelService,
) -> tuple[int, int, int]:
    """Phase 1: Install Mental Models.

    Returns (installed, skipped, errors) counts.
    """
    _print_header(1, 5, "Installing Mental Models")

    models_to_install = ["crm", "zettelkasten", "research"]
    installed = 0
    skipped = 0
    errors = 0

    # Verify basic-pkm is already installed (auto-installed at startup)
    if await is_model_installed(client, "basic-pkm"):
        print("  ✓ basic-pkm: already installed (auto-installed at startup)")
    else:
        print("  ⚠ basic-pkm: NOT installed — this is unexpected!")
        print("    The app should auto-install basic-pkm during startup.")
        print("    Attempting manual install...")
        try:
            await model_service.install(Path("/app/models/basic-pkm"))
            print("  ✓ basic-pkm: installed manually")
            installed += 1
        except Exception as e:
            print(f"  ✗ basic-pkm: install failed — {e}")
            errors += 1

    for model_id in models_to_install:
        try:
            if await is_model_installed(client, model_id):
                print(f"  ✓ {model_id}: already installed (skipped)")
                skipped += 1
            else:
                model_path = Path(f"/app/models/{model_id}")
                await model_service.install(model_path)
                print(f"  ✓ {model_id}: installed successfully")
                installed += 1
        except Exception as e:
            print(f"  ✗ {model_id}: install failed — {e}")
            errors += 1

    print(f"\n  Summary: {installed} installed, {skipped} skipped, {errors} errors")
    return installed, skipped, errors


async def phase_create_edges(
    client: TriplestoreClient,
    event_store: EventStore,
) -> tuple[int, int, int]:
    """Phase 2: Create cross-model edges.

    Returns (created, skipped, errors) counts.
    """
    _print_header(2, 5, "Creating Cross-Model Edges")

    created = 0
    skipped = 0
    errors = 0

    for edge_def in CROSS_MODEL_EDGES:
        source = edge_def["source"]
        target = edge_def["target"]
        predicate = edge_def["predicate"]
        label = edge_def["label"]

        try:
            if await _edge_exists(client, source, target, predicate):
                print(f"  ✓ {label}: already exists (skipped)")
                skipped += 1
                continue

            params = EdgeCreateParams(
                source=source,
                target=target,
                predicate=predicate,
            )
            operation = await handle_edge_create(params, settings.base_namespace)
            await event_store.commit(
                [operation],
                performed_by=None,
                performed_by_role=None,
            )
            print(f"  ✓ {label}: created")
            created += 1

        except Exception as e:
            print(f"  ✗ {label}: failed — {e}")
            errors += 1

    print(f"\n  Summary: {created} created, {skipped} skipped, {errors} errors")
    return created, skipped, errors


async def phase_set_bodies(
    event_store: EventStore,
) -> tuple[int, int]:
    """Phase 3: Set markdown bodies on key objects.

    Returns (set_count, errors) counts.
    """
    _print_header(3, 5, "Setting Markdown Bodies")

    set_count = 0
    errors = 0

    for iri, body in MARKDOWN_BODIES.items():
        try:
            params = BodySetParams(iri=iri, body=body)
            operation = await handle_body_set(params, settings.base_namespace)
            await event_store.commit(
                [operation],
                performed_by=None,
                performed_by_role=None,
            )
            # Truncate label for display
            label = iri.split(":")[-1]
            lines = body.strip().splitlines()
            title = lines[0].lstrip("# ").strip() if lines else "(empty)"
            print(f"  ✓ {label}: \"{title}\" ({len(body)} chars)")
            set_count += 1

        except Exception as e:
            label = iri.split(":")[-1]
            print(f"  ✗ {label}: failed — {e}")
            errors += 1

    print(f"\n  Summary: {set_count} set, {errors} errors")
    return set_count, errors


async def phase_create_dashboard() -> None:
    """Phase 4: Create demo user row and pre-built demo dashboard.

    Inserts a demo user (needed for FK constraint) and a dashboard
    demonstrating cross-view context filtering (table → graph).
    Idempotent: skips dashboard creation if already exists.
    """
    _print_header(4, 5, "Creating Demo Dashboard")

    async with async_session_factory() as session:
        # Ensure demo user exists (merge = insert-or-update)
        demo_user = User(
            id=DEMO_USER_UUID,
            email="demo@sempkm.app",
            display_name="Demo Visitor",
            role="guest",
        )
        await session.merge(demo_user)
        await session.flush()
        print("  ✓ Demo user ensured (demo@sempkm.app)")

        # Check if dashboard already exists
        result = await session.execute(
            select(DashboardSpec).where(DashboardSpec.id == DEMO_DASHBOARD_UUID)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("  ✓ Demo dashboard already exists (skipped)")
        else:
            blocks = [
                {
                    "type": "view-embed",
                    "slot": "sidebar",
                    "config": {
                        "spec_iri": "urn:sempkm:view:generic-table",
                        "emits_context": True,
                    },
                },
                {
                    "type": "view-embed",
                    "slot": "main",
                    "config": {
                        "spec_iri": "urn:sempkm:view:generic-graph",
                        "listens_to_context": "iri",
                    },
                },
            ]
            dashboard = DashboardSpec(
                id=DEMO_DASHBOARD_UUID,
                user_id=DEMO_USER_UUID,
                name="Demo Dashboard",
                description=(
                    "A pre-built dashboard demonstrating cross-view context "
                    "filtering. Click a row in the table to filter the graph."
                ),
                layout="sidebar-main",
                blocks_json=json.dumps(blocks),
            )
            session.add(dashboard)
            print("  ✓ Demo dashboard created")

        await session.commit()


async def phase_verify(client: TriplestoreClient) -> bool:
    """Phase 5: Verify seed data via SPARQL count queries and dashboard check.

    Returns True if all checks pass.
    """
    _print_header(5, 5, "Verifying Seed Data")

    all_ok = True

    # Count distinct objects in current graph
    sparql_objects = """SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE {
  GRAPH <urn:sempkm:current> { ?s a ?t }
}"""
    result = await client.query(sparql_objects)
    object_count = int(result["results"]["bindings"][0]["c"]["value"])

    # Count installed models
    sparql_models = """SELECT (COUNT(?m) AS ?c) WHERE {
  GRAPH <urn:sempkm:models> {
    ?m a <urn:sempkm:MentalModel> .
  }
}"""
    result = await client.query(sparql_models)
    model_count = int(result["results"]["bindings"][0]["c"]["value"])

    # Count cross-model edges (edges in current graph typed as sempkm:Edge)
    sparql_edges = """SELECT (COUNT(DISTINCT ?edge) AS ?c) WHERE {
  GRAPH <urn:sempkm:current> {
    ?edge a <urn:sempkm:Edge> ;
          <urn:sempkm:source> ?src ;
          <urn:sempkm:target> ?tgt .
  }
}"""
    result = await client.query(sparql_edges)
    edge_count = int(result["results"]["bindings"][0]["c"]["value"])

    # Count objects with bodies
    sparql_bodies = """SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE {
  GRAPH <urn:sempkm:current> {
    ?s <urn:sempkm:body> ?body .
  }
}"""
    result = await client.query(sparql_bodies)
    body_count = int(result["results"]["bindings"][0]["c"]["value"])

    # Count dashboards in SQLite
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.count()).select_from(DashboardSpec)
        )
        dashboard_count = result.scalar()

    # Print results table
    print()
    print(f"  {'Metric':<30} {'Actual':>8} {'Expected':>10} {'Status':>8}")
    print(f"  {'-'*30} {'-'*8} {'-'*10} {'-'*8}")

    checks = [
        ("Objects (distinct)", object_count, 50, "≥"),
        ("Installed models", model_count, 4, "≥"),
        ("Cross-model edges", edge_count, 10, "≥"),
        ("Objects with bodies", body_count, 8, "≥"),
        ("Dashboards", dashboard_count, 1, "≥"),
    ]

    for label, actual, expected, op in checks:
        if op == "≥":
            passed = actual >= expected
        else:
            passed = actual == expected
        status = "✓ pass" if passed else "✗ FAIL"
        if not passed:
            all_ok = False
        print(f"  {label:<30} {actual:>8} {op + str(expected):>10} {status:>8}")

    print()
    if all_ok:
        print("  ✓ All verification checks passed!")
    else:
        print("  ✗ Some verification checks failed — see above.")

    return all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the seed data script."""
    parser = argparse.ArgumentParser(
        description="Seed demo data into a SemPKM demo instance."
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Skip install/edge/body/dashboard phases; only run verification.",
    )
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║          SemPKM Demo Data Seeder                       ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Initialize services (same pattern as app.main lifespan)
    client = TriplestoreClient(
        base_url=settings.triplestore_url,
        repository_id=settings.repository_id,
    )

    # Ensure repository exists
    async with httpx.AsyncClient(timeout=30.0) as setup_client:
        await ensure_repository(
            client=setup_client,
            base_url=settings.triplestore_url,
            repo_id=settings.repository_id,
        )

    prefix_registry = PrefixRegistry()
    event_store = EventStore(client)
    model_service = ModelService(client, event_store, prefix_registry)

    if args.verify_only:
        print("\n  --verify-only: skipping phases 1-4")
        ok = await phase_verify(client)
        sys.exit(0 if ok else 1)

    # Phase 1: Install models
    try:
        await phase_install_models(client, model_service)
    except Exception as e:
        print(f"\n  ✗ Phase 1 failed critically: {e}")

    # Phase 2: Create cross-model edges
    try:
        await phase_create_edges(client, event_store)
    except Exception as e:
        print(f"\n  ✗ Phase 2 failed critically: {e}")

    # Phase 3: Set markdown bodies
    try:
        await phase_set_bodies(event_store)
    except Exception as e:
        print(f"\n  ✗ Phase 3 failed critically: {e}")

    # Phase 4: Create demo dashboard
    try:
        await phase_create_dashboard()
    except Exception as e:
        print(f"\n  ✗ Phase 4 failed critically: {e}")

    # Phase 5: Verify (always runs)
    ok = await phase_verify(client)

    print("\n" + "=" * 60)
    if ok:
        print("Done! Demo instance is seeded and verified.")
    else:
        print("Done with warnings — some verification checks failed.")
    print("=" * 60)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
