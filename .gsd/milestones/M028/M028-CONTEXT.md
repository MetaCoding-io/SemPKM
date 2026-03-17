---
depends_on: [M015]
---

# M028: Browser Extension Phase 3 — Active Intelligence

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

AI-powered features for the browser extension: automatic claim detection on web pages matched against existing claims in the graph, relationship suggestions, knowledge gap detection, and personalized page summaries using graph context. Uses SemPKM's existing LLM proxy so the extension doesn't need its own API keys.

## Why This Milestone

Phase 1 captures, Phase 2 surfaces context, Phase 3 actively thinks. While reading a page, the extension detects claims ("RDF scales better than property graphs") and matches them against your graph — surfacing contradictions, corroborations, and evidence gaps. This is the "AI that works because data is structured" story.

## User-Visible Outcome

### When this milestone is complete, the user can:

- See auto-detected claims on a web page highlighted with confidence indicators
- See "This claim contradicts your Claim X" when a page assertion conflicts with existing knowledge
- See "This page discusses your Research Question Y but you haven't captured evidence" gap alerts
- Get relationship suggestions ("This article cites the same source as your Note X — link them?")
- Request "Summarize this page in context of what I already know" for personalized summaries
- Accept or dismiss AI suggestions with one click

### Entry point / environment

- Entry point: Browser extension sidebar (enhanced from Phase 2)
- Environment: Chrome/Firefox extension
- Live dependencies involved: SemPKM LLM proxy, graph context via SPARQL

## Completion Class

- Contract complete means: claim detection extracts testable assertions, graph matching finds relevant objects, suggestions render correctly
- Integration complete means: detected claims match against real graph data, suggestions create valid objects/edges when accepted
- Operational complete means: LLM calls within acceptable latency (<3s), graceful degradation when LLM unavailable

## Final Integrated Acceptance

- User visits an article, extension detects 3 claims, one matches an existing Claim marked "speculative"
- Extension suggests "Add this as supporting evidence for your claim"
- User accepts, Evidence object created with correct links
- Personalized summary incorporates user's existing knowledge about the topic

## Risks and Unknowns

- **LLM quality for claim detection** — Extracting well-formed claims from arbitrary web pages is a hard NLP problem. May need prompt engineering iteration.
- **Latency** — LLM calls add 2-5 seconds. Must show progressive results (claims first, then matches).
- **False positive suggestions** — AI suggestions must be high-quality or users will disable the feature.

## Existing Codebase / Prior Art

- `.gsd/design/BROWSER-EXTENSION-DESIGN.md` — Phase 3 spec
- `backend/app/settings/llm.py` — LLM connection configuration
- Phase 1 (M014) + Phase 2 (M015) — extension infrastructure

## Relevant Requirements

- New: EXT-11 (claim detection), EXT-12 (contradiction surfacing), EXT-13 (gap detection), EXT-14 (personalized summaries)

## Scope

### In Scope

- Page content extraction and claim detection via LLM
- Claim → graph matching (SPARQL queries for similar/contradicting claims)
- Relationship suggestions based on shared references/topics
- Knowledge gap detection (open questions related to page topic)
- Personalized summarization using graph context
- Accept/dismiss UI for suggestions
- LLM proxy integration (uses SemPKM's configured LLM, not extension's own key)
- Progressive loading (claims → matches → suggestions)

### Out of Scope / Non-Goals

- Training custom models
- Embedding-based semantic search (use FTS + SPARQL for now)
- Real-time annotation overlay on page content
- Multi-page analysis ("compare these 5 articles")

## Technical Constraints

- LLM calls via SemPKM's `/api/llm/stream` proxy
- Must handle LLM unavailability gracefully (feature disabled, no errors)
- Claims must be extractable assertions (not just keywords)
- Graph queries for matching must be efficient (<500ms)

## Integration Points

- **LLM proxy** — `/api/llm/stream` for claim detection and summarization
- **SPARQL endpoint** — graph matching for claims, evidence, research questions
- **Phase 2 sidebar** — enhanced with AI suggestions section
- **POST /api/commands** — creating objects/edges from accepted suggestions
