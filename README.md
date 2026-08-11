<div align="center">

# SemPKM

**Semantics-native Personal Knowledge Management.**
Structured like a knowledge graph. Feels like Notion.

[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](backend/pyproject.toml)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](backend/)
[![RDF4J](https://img.shields.io/badge/triplestore-RDF4J-orange)](https://rdf4j.org/)
[![htmx](https://img.shields.io/badge/frontend-htmx%20%2B%20vanilla%20JS-3D72D7)](frontend/)

[What is SemPKM?](docs/guide/01-what-is-sempkm.md) ·
[User Guide](docs/guide/README.md) ·
[Installation](docs/guide/03-installation-and-setup.md) ·
[CLAUDE.md](CLAUDE.md)

</div>

---

## Why SemPKM

Free-form tools (Obsidian, Notion, Roam) give you speed but shallow structure — a `[[wiki-link]]` doesn't say *how* two things relate. Academic RDF tools (Protégé, TopBraid) give you real structure but demand you think in triples and namespace IRIs.

SemPKM bridges the two: it stores everything as real RDF — validated with SHACL, queryable with SPARQL — but the UI is auto-generated from that schema, so you get forms, tables, cards, and graphs instead of triples. You get the rigor of a knowledge graph without ever needing to know it's one.

<div align="center">
<img src="docs/screenshots/guide-workspace-dockview.png" width="49%" alt="SemPKM workspace" />
<img src="docs/screenshots/guide-object-edit-view.png" width="49%" alt="SemPKM object editor" />
</div>

## Highlights

| | |
|---|---|
| 🧩 **Mental Models** | Installable packages that bundle ontology, SHACL shapes, views, and seed data into an instant PKM domain — ship with `basic-pkm`, `crm`, `research`, `zettelkasten`, `business-planning`, and more |
| 🔗 **Typed relationships** | Every edge has a meaning (`hasParticipant`, `isAbout`) — not just an implied link |
| 🕘 **Full history** | Every change is an immutable, attributed event — full audit trail, no lock-in |
| ✅ **Assistive validation** | SHACL-powered lint panel flags issues without blocking your work |
| 🗂️ **11 view renderers** | Table, cards, kanban, graph (2D/3D), calendar, timeline, map, OKR, BMC, quadrant, decision matrix |
| ⌨️ **IDE-style workspace** | Dockview tabs, nav tree, command palette, keyboard-first navigation |
| 🔐 **Passwordless auth** | Magic-link login, multi-user with owner/member roles, WebID + IndieAuth support |
| 🔌 **Integrations** | Webhooks, SPARQL endpoint, Obsidian vault import, sync apps for Linear/GitHub/Jira/Monday/Asana/Google/Outlook/CalDAV |
| 🐳 **One-command deploy** | `docker compose up` — self-hosted, your data, open formats |

<div align="center">
<img src="docs/screenshots/08-graph-view-dark.png" width="32%" alt="Graph view" />
<img src="docs/screenshots/06-table-view-dark.png" width="32%" alt="Table view" />
<img src="docs/screenshots/04-command-palette-dark.png" width="32%" alt="Command palette" />
</div>

## Quick Start

```bash
git clone git@github.com:MetaCoding-io/SemPKM.git
cd SemPKM
docker compose up -d
```

Then open **http://localhost:4000**. First run drops you into the setup wizard; after that, login is passwordless via magic link (see [Installation & Setup](docs/guide/03-installation-and-setup.md)).

## Architecture

- **Backend:** Python 3.12, FastAPI, async SQLAlchemy (SQLite/PostgreSQL) for app state, Eclipse RDF4J for the knowledge graph
- **Frontend:** htmx-driven server rendering + vanilla JS modules (`window.SemPKM` namespace), Dockview for the tabbed workspace, esbuild for bundling — no SPA framework
- **Data model:** RDF triples validated by SHACL shapes, queried via SPARQL; Mental Models package ontology + shapes + views + seed data into `.sempkm-model` archives

See [`CODEBASE.md`](CODEBASE.md) for the full repo map and [`.gsd/PROJECT.md`](.gsd/PROJECT.md) for current architecture notes.

## Docker Stacks

The repo ships several independent Compose stacks for different purposes — all self-contained with their own ports, volumes, and networks, so they can run side by side.

| Stack | File | Frontend | API | Purpose |
|---|---|---|---|---|
| **Dev** | `docker-compose.yml` | `:4000` | `:8001` | Primary development stack — hot-reloaded volume mounts, Jaeger tracing included |
| **Test** | `docker-compose.test.yml` | `:3901` | `:8901` | E2E test target — bundles ~10 mock integration API servers (Linear, GitHub, Jira, Monday, Asana, Google Calendar, Outlook, CalDAV, LLM) |
| **Demo** | `docker-compose.demo.yml` | `:3902` | `:8902` | Public read-only demo — `DEMO_MODE=true` bypasses auth, nginx blocks all writes at the proxy layer |
| **Cloud** | `docker-compose.cloud.yml` | `:443`/`:80` | — | *Overlay* on the dev stack (`-f docker-compose.yml -f docker-compose.cloud.yml`) — swaps nginx for Caddy with automatic TLS |
| **Federation test** | `docker-compose.federation-test.yml` | `:3911`/`:3912` | `:8911`/`:8912` | Two full stacks (A + B) side by side on a shared network for cross-instance federation E2E |

```bash
# Dev
docker compose up -d

# E2E test stack
docker compose -f docker-compose.test.yml up -d --build

# Read-only demo
docker compose -f docker-compose.demo.yml up -d --build

# Cloud deploy (requires .env with SEMPKM_DOMAIN)
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d

# Federation A/B testing
docker compose -f docker-compose.federation-test.yml up -d --build
```

## Documentation

- 📘 [User Guide](docs/guide/README.md) — installation through advanced SPARQL topics
- 🗺️ [CODEBASE.md](CODEBASE.md) — repository structure map
- 🧭 [TOUR.md](TOUR.md) — feature tour and manual test checklist
- 🤖 [CLAUDE.md](CLAUDE.md) — coding conventions for AI-assisted development on this repo

## Screenshots

<div align="center">
<img src="docs/screenshots/03-object-edit-form-dark.png" width="32%" alt="Object edit form" />
<img src="docs/screenshots/13-admin-models-dark.png" width="32%" alt="Model admin" />
<img src="docs/screenshots/16-lint-panel-dark.png" width="32%" alt="Lint panel" />
</div>
