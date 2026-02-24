---
phase: quick-003
plan: 01
subsystem: research
tags: [annotation, hypothes.is, w3c, rdf, linked-data, pdf, rss]
dependency-graph:
  requires: []
  provides: [annotation-integration-strategy]
  affects: [rdf4j-store, fastapi-backend, pdf-viewer, rss-mental-model]
tech-stack:
  added: []
  patterns:
    - W3C Web Annotation Data Model (oa: namespace)
    - Hypothesis client embed via services config
    - Grant token JWT pattern for custom annotation backend
key-files:
  created:
    - .planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md
  modified: []
decisions:
  - "Hybrid annotation storage: Hypothesis client + SemPKM annotation API storing oa:Annotation triples in RDF4J (not self-hosted h server, not hypothes.is public API)"
  - "PDF annotation: PDF.js + Hypothesis client embedded in SemPKM viewer page (Option B) — no via proxy for private docs"
  - "RSS reader: embed Hypothesis client in article view template, not a custom annotation layer"
metrics:
  duration: 12min
  completed: 2026-02-24
  tasks-completed: 1
  files-created: 1
---

# Quick Task 003: Hypothes.is Annotation Technology Research Summary

**One-liner:** W3C Web Annotation (oa: namespace) + Hypothesis client with custom SemPKM annotation API storing oa:Annotation RDF triples in RDF4J.

## What Was Researched

Fetched and synthesized documentation from:
- W3C Web Annotation Data Model (REC 2017-02-23) — full IRI vocabulary, JSON-LD context
- W3C Web Annotation Protocol (REC 2017-02-23) — LDP container model, CRUD operations
- Hypothes.is live API root (https://hypothes.is/api/) — real JSON structure
- Real annotation examples from the Hypothes.is API (live fetch with selectors)
- Hypothesis client docs (h.readthedocs.io) — config, events, embedding, services API
- GitHub hypothesis/h — architecture, stack, licensing
- GitHub hypothesis/via — PDF proxy mechanism
- GitHub hypothesis/bouncer — deep-link service

## Key Findings

### W3C Standard

- `oa:Annotation` is a standard RDF resource with `oa:hasBody`, `oa:hasTarget`, `oa:motivatedBy`
- 13 standard motivation types: commenting, highlighting, tagging, replying, bookmarking, etc.
- Selectors (`oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:FragmentSelector`) identify sub-document targets
- Hypothes.is is **partially compliant**: uses W3C selector types but returns plain JSON (not JSON-LD), omits `@context`, omits `oa:motivatedBy`

### Hypothes.is Stack

- `h` server: Python/Pyramid + PostgreSQL + Elasticsearch + Redis — heavy, self-hosting is non-trivial
- `client`: JavaScript sidebar, embeds via single `<script>` tag, has native PDF.js support
- `via`: Python/NGINX proxy that injects client into arbitrary pages/PDFs
- `bouncer`: deep-link redirect service (low relevance for SemPKM)
- All components licensed BSD-2-Clause

### RDF Alignment

- Hypothes.is JSON annotations can be round-tripped to W3C RDF with no significant data loss
- `target[].source` → `oa:hasSource`, `target[].selector[]` → `oa:has{Type}Selector` map directly
- Non-W3C fields (`permissions`, `group`) stored as `hyp:` custom properties
- Full Turtle model provided for storing a Hypothes.is annotation as a named graph in RDF4J

## Recommendations Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Storage | Hybrid: Hypothesis client + SemPKM annotation API in RDF4J | No extra infra, SPARQL queryable, data sovereignty |
| PDF reader | Option B: PDF.js + Hypothesis client embedded | Native PDF.js integration, no via proxy needed |
| RSS reader | Hypothesis client in article view template | Reuse polished UI, avoid building from scratch |

## Implementation Plan (Not Scoped Yet)

| Phase | Task | Estimated Effort |
|-------|------|-----------------|
| 1 | Annotation REST API in SemPKM FastAPI (8 endpoints) | 2-3 days |
| 2 | Grant token JWT issuance for logged-in users | 0.5 day |
| 3 | PDF viewer page (PDF.js + Hypothesis client) | 1-2 days |
| 4 | RSS Feed Reader Mental Model | 2 days |

Total: ~6-8 days. These are not in the current v2.0 roadmap — they represent future scope.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- Research document exists: `.planning/quick/3-research-hypothes-is-annotation-technolo/hypothes-is-research.md` (1006 lines)
- All 7 sections present (1. W3C Standard, 2. Components, 3. RDF Alignment, 4. Use Cases, 5. Storage Options, 6. Embed API, 7. Recommendations)
- W3C IRIs cited: 46 occurrences of `oa:Annotation`, `oa:hasTarget`, `oa:TextQuoteSelector`, etc.
- Turtle/RDF example: Yes (complete named graph with selectors)
- Storage options comparison table: Yes
- Concrete recommendations: Yes (hybrid, Option B PDF, client-in-article-view RSS)
- Commit: 8d62fe1
