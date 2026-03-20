# M028: Browser Extension Phase 3 — Active Intelligence — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

M028 adds AI-powered claim detection, graph matching, contradiction surfacing, gap detection, and personalized summaries to the browser extension. The existing codebase provides strong foundations: the Phase 2 sidebar (`sidebar.js`) already renders grouped context results and has an "Add Evidence" action for Claim-type results; the LLM streaming proxy (`/browser/settings/llm/chat/stream`) proxies OpenAI-compatible chat completions via SSE; and the Research Workflow mental model defines Claim, Evidence, ResearchQuestion, and Argument types with confidence levels.

The **critical gap** is that the LLM proxy endpoint uses session cookie auth (`get_current_user`), but the browser extension uses Bearer token auth via `SemPKMClient`. The extension cannot call the LLM proxy without a new Bearer-compatible endpoint. This is the first thing to solve.

The work divides into four natural slices: (1) backend AI endpoints with Bearer auth, (2) claim detection and graph matching logic, (3) extension UI for suggestions and progressive loading, (4) E2E tests and user guide.

## Recommendation

Build the backend endpoints first (new `/api/llm/stream` with dual-auth, plus `/api/ai/detect-claims` and `/api/ai/suggest-relationships`), then the graph matching SPARQL queries, then the extension UI. The Research Workflow model's existing Claim/Evidence/ResearchQuestion types provide the schema — no model changes needed.

**Prove first:** A Bearer-authenticated LLM proxy call from the extension, returning claim JSON. This unblocks all downstream work.

**Reuse:** The Phase 2 sidebar rendering pattern (grouped results with action buttons), the context-query endpoint's SPARQL matching patterns, the SSE streaming approach from the LLM proxy, and the two-step object+edge creation from Phase 1.

## Implementation Landscape

### Key Files

- `backend/app/browser/settings.py` (lines 218–290) — existing LLM chat stream proxy at `/browser/settings/llm/chat/stream`. Uses `get_current_user` (cookie-only). Must be adapted or duplicated with `get_current_user_or_api` for Bearer access.
- `backend/app/services/llm.py` — `LLMConfigService` with encrypted API key storage. `get_decrypted_api_key()` and `get_config()` are the core methods. Reuse as-is.
- `extension/shared/api-client.js` — `SemPKMClient` with Bearer auth. Needs new methods: `detectClaims(pageContent)`, `matchClaims(claims)`, `suggestRelationships(context)`, `summarizePage(content, graphContext)`.
- `extension/sidebar/sidebar.js` — Phase 2 sidebar with grouped results rendering. Needs new sections for AI suggestions (claims, contradictions, gaps). Already has `_renderCard()`, `_renderGroup()`, and evidence capture flow.
- `extension/background/service-worker.js` — Message handler for sidebar ↔ background communication. Needs new message types for AI operations.
- `extension/shared/context-utils.js` — Ranking and grouping utilities. Needs claim-specific ranking.
- `backend/app/api/` — API router directory. New `ai.py` router for claim detection and suggestion endpoints.
- `models/research/` — Research Workflow model with Claim (confidence levels), Evidence (evidenceType, strength), ResearchQuestion. Schema for graph matching.
- `models/basic-pkm/` — Note, Concept types that claims may reference.

### Build Order

1. **Bearer-compatible LLM proxy** — New `POST /api/llm/stream` endpoint using `get_current_user_or_api` (dual-auth dependency from M013). This is the gating dependency — without it, the extension can't call the LLM at all. ~20 lines copying from settings.py with the auth swap.

2. **Claim detection endpoint** — New `POST /api/ai/detect-claims` that accepts page text content, calls the LLM with a claim-extraction prompt, returns structured JSON array of detected claims with confidence scores. This is a backend-only endpoint — testable with curl before any extension work.

3. **Graph matching queries** — New `POST /api/ai/match-claims` that accepts claim text, queries the graph via SPARQL for: (a) existing Claims with similar text (FTS via LuceneSail), (b) Research Questions related to the topic, (c) Evidence objects that reference similar sources. Returns matches with contradiction/corroboration indicators.

4. **Relationship suggestion endpoint** — New `POST /api/ai/suggest-relationships` that accepts page context (URL, title, claims) and returns relationship suggestions (shared references, topic overlap with existing objects). Can reuse context-query SPARQL patterns.

5. **Personalized summary endpoint** — New `POST /api/ai/summarize` that accepts page content + graph context objects, calls LLM with a summary prompt incorporating the user's existing knowledge.

6. **Extension sidebar UI** — New "AI Insights" section in sidebar with progressive loading: show claims first (fastest LLM call), then graph matches (SPARQL), then suggestions and summary. Accept/dismiss buttons on suggestions.

7. **Accept/dismiss actions** — Wire accept buttons to `createObject()` + `createEdge()` (existing two-step pattern from Phase 1). Dismiss stores in `chrome.storage.local` per-URL.

8. **E2E tests + user guide** — Mock LLM responses for deterministic testing. Chapter 40 user guide.

### Verification Approach

- Unit tests for claim extraction prompt parsing (pure function tests on LLM response → structured claims)
- Unit tests for SPARQL graph matching queries (mock triplestore responses)
- Unit tests for relationship suggestion logic
- E2E Playwright test: install extension → navigate to page with seed claims → verify sidebar shows AI insights → accept a suggestion → verify object/edge created via SPARQL
- Mock LLM server returning canned claim JSON for deterministic E2E testing

## Constraints

- **LLM proxy auth gap**: The existing `/browser/settings/llm/chat/stream` uses `get_current_user` (cookie-only auth). The extension uses Bearer tokens. A new endpoint with `get_current_user_or_api` is mandatory — cannot modify the existing endpoint without risking htmx frontend breakage.
- **No embedding/vector search**: CONTEXT.md explicitly scopes out embedding-based semantic search. Use FTS (LuceneSail) + SPARQL string matching for claim-to-graph matching. This limits matching quality but avoids infrastructure changes.
- **LLM latency**: Claim detection requires a full LLM call (2-5s). Graph matching is SPARQL (<500ms). Must show progressive results — claims first, then matches. SSE is the natural pattern (already used by LLM proxy).
- **Extension CSP**: Chrome MV3 forbids eval() and inline scripts. All JS must be plain vanilla (no build step, per D169).
- **Research model not always installed**: Claim matching against `research:Claim` objects only works if the Research Workflow model is installed. Must degrade gracefully — show claims without graph matches if no research model. Check installed types via `/api/types`.
- **LLM availability**: Must handle LLM not configured (no API key) gracefully. Show "AI features require LLM configuration" message, not errors. Check via `/.well-known/sempkm` capabilities or a new `/api/llm/status` endpoint.

## Common Pitfalls

- **Prompt engineering fragility** — Claim detection quality depends heavily on the prompt. Use a structured output format (JSON array with `text`, `confidence`, `type` fields) and validate the response. Fall back gracefully on malformed LLM output.
- **FTS false positives** — LuceneSail keyword search will return many loose matches for claim text. Must rank results by relevance (exact phrase > keyword overlap > single-word match) and cap at 5 matches per claim.
- **SSE through nginx** — The existing LLM proxy sets `X-Accel-Buffering: no` to prevent nginx from buffering SSE. New endpoints must do the same.
- **Rate limiting LLM calls** — A page with 50 paragraphs shouldn't trigger 50 LLM calls. Extract claims from the full page text in a single LLM call, not per-paragraph.
- **Extension sidebar height** — Adding AI sections to the existing sidebar may cause scroll overflow. Use collapsible sections (existing `_renderGroup()` pattern).

## Open Risks

- **LLM claim extraction quality** — Extracting well-formed, testable assertions from arbitrary web pages is genuinely hard. The prompt may need multiple iterations. Start with a simple prompt and iterate based on real-world testing.
- **False positive suggestions** — AI suggesting "This contradicts your Claim X" when it doesn't will erode trust. Conservative matching (high FTS score threshold + LLM verification) is better than aggressive matching.
- **Cross-model claim matching** — Claims may exist in any model (research:Claim, but also as assertions in Notes or Concepts). The SPARQL queries need to search broadly, not just the research model namespace.
- **LLM response format variability** — Different LLM providers (OpenAI, Anthropic, local models) may return slightly different JSON structures. The claim extraction parser must be defensive.

## Candidate Requirements

Based on CONTEXT.md scope and the implementation landscape:

| ID | Description | Class | Notes |
|----|-------------|-------|-------|
| EXT-22 | Bearer-authenticated LLM proxy for extension access | core-capability | Gating dependency — new `/api/llm/stream` with dual-auth |
| EXT-23 | Claim detection from page content via LLM | core-capability | `POST /api/ai/detect-claims` with structured JSON output |
| EXT-24 | Claim → graph matching via SPARQL/FTS | core-capability | Match detected claims against existing Claim/Note/Concept objects |
| EXT-25 | Contradiction/corroboration indicators on matched claims | core-capability | Compare confidence levels and evidence types |
| EXT-26 | Research question gap detection | core-capability | Match page topics against open ResearchQuestions |
| EXT-27 | Relationship suggestions based on shared references/topics | core-capability | Suggest "Link to Note X" when page cites same source |
| EXT-28 | Personalized page summary using graph context | core-capability | LLM summary incorporating user's existing knowledge |
| EXT-29 | Accept/dismiss UI for AI suggestions | core-capability | One-click object/edge creation from accepted suggestions |
| EXT-30 | Progressive loading (claims → matches → suggestions) | core-capability | SSE-based incremental display in sidebar |
| EXT-31 | Graceful degradation when LLM unavailable | core-capability | Feature disabled with clear message, no errors |
| EXT-32 | E2E tests with mock LLM server | quality-attribute | Deterministic claim detection testing |
| EXT-33 | User guide Chapter 40 | quality-attribute | AI features documentation |

**Advisory (not requirements):**
- Claim extraction prompt should be configurable via settings (power user feature, not v1)
- Embedding-based semantic search explicitly out of scope per CONTEXT.md
- Multi-page analysis ("compare 5 articles") explicitly out of scope per CONTEXT.md

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| LLM streaming proxy | Existing `llm_chat_stream()` in settings.py | Copy pattern, swap auth dependency — proven SSE + httpx streaming |
| Bearer auth on API endpoints | `get_current_user_or_api` from M013 | Already tested with 15 unit tests, used on all /api/ endpoints |
| Object + edge creation from extension | `SemPKMClient.createObject()` + `createEdge()` | Two-step pattern from Phase 1, proven in 3 E2E tests |
| FTS keyword search | LuceneSail via existing SPARQL patterns | context-query endpoint already does URL + keyword matching |
| Sidebar grouped rendering | `_renderGroup()` + `_renderCard()` in sidebar.js | Phase 2 pattern, just needs new card types for AI suggestions |
| SSE through nginx | `X-Accel-Buffering: no` header pattern | Already used by LLM proxy and import wizards |

## Sources

- Extension sidebar: `extension/sidebar/sidebar.js` — 330 lines, grouped results with evidence capture
- LLM proxy: `backend/app/browser/settings.py` lines 218-290 — SSE streaming via httpx
- LLM config: `backend/app/services/llm.py` — Fernet-encrypted key storage
- API client: `extension/shared/api-client.js` — Bearer auth, contextQuery(), createObject()
- Context query: `POST /api/context-query` — URL/title/keyword matching with FTS
- Research model: `models/research/` — Claim, Evidence, ResearchQuestion types
- Dual-auth: `get_current_user_or_api` in `backend/app/auth/dependencies.py`
- Phase 3 design: `.gsd/design/BROWSER-EXTENSION-DESIGN.md`
