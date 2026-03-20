# M028: Browser Extension Phase 3 — Active Intelligence

**Vision:** While reading any web page, the extension detects claims, matches them against the user's knowledge graph, surfaces contradictions and evidence gaps, suggests relationships, and provides personalized summaries — turning passive browsing into active knowledge building.

## Success Criteria

- User visits a page and the sidebar's AI Insights section shows auto-detected claims with confidence indicators within 5 seconds
- A detected claim that contradicts an existing Claim object in the graph displays "Contradicts your Claim X (speculative)" with a link
- Extension shows "This page discusses your Research Question Y but you haven't captured evidence" when topics match open questions
- User sees "Link to Note X — cites same source" relationship suggestion and can accept it with one click, creating the edge
- User requests "Summarize in context of what I know" and gets a personalized summary incorporating their existing knowledge
- All AI features degrade gracefully: "AI features require LLM configuration" message when no LLM is configured, claims shown without matches when Research model isn't installed
- Accept creates the correct object/edge via existing two-step pattern; dismiss persists per-URL in chrome.storage.local

## Key Risks / Unknowns

- **LLM proxy auth gap** — The existing `/browser/settings/llm/chat/stream` uses cookie-only auth (`get_current_user`). The extension uses Bearer tokens. Without a Bearer-compatible LLM endpoint, the extension cannot call the LLM at all. This is the gating dependency.
- **Claim extraction quality** — Extracting well-formed, testable assertions from arbitrary web pages is a hard NLP problem. The prompt must produce structured JSON reliably across different LLM providers (OpenAI, Anthropic, local models).
- **Graph matching false positives** — LuceneSail FTS returns loose keyword matches. Without embedding-based search (out of scope), matches must be aggressively ranked and capped to avoid suggesting nonsensical contradictions.

## Proof Strategy

- **LLM proxy auth gap** → retire in S01 by proving a Bearer-authenticated LLM call returns claim JSON from the extension sidebar
- **Claim extraction quality** → retire in S01 by proving the detect-claims endpoint returns parseable structured JSON from real page content, with fallback on malformed LLM output
- **Graph matching false positives** → retire in S02 by proving match-claims returns relevant results ranked by FTS score with a cap of 5 matches per claim, and contradiction/corroboration indicators align with stored confidence levels

## Verification Classes

- Contract verification: pytest unit tests for claim extraction parsing, SPARQL graph matching queries, relationship suggestion logic, prompt validation
- Integration verification: curl-testable backend endpoints (detect-claims, match-claims, suggest-relationships, summarize) against Docker stack with seed data and configured LLM
- Operational verification: LLM latency within 5s, graceful degradation when LLM unavailable or model not installed, progressive loading UX
- UAT / human verification: claim quality on real web pages (news articles, Wikipedia, blog posts) — subjective quality check

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 4 backend AI endpoints return correct responses with Bearer auth
- Extension sidebar shows AI Insights section with progressive loading (claims → matches → suggestions → summary)
- Accept/dismiss actions create correct objects/edges and persist dismissals
- Graceful degradation verified: LLM unconfigured shows message, Research model not installed shows claims without graph matches
- Playwright E2E test proves full flow: page visit → claim detection → graph match → accept suggestion → verify object/edge created
- User guide Chapter 40 documents AI features with screenshots and troubleshooting
- All new unit tests pass, zero regressions in existing test suite

## Requirement Coverage

- Covers: EXT-22, EXT-23, EXT-24, EXT-25, EXT-26, EXT-27, EXT-28, EXT-29, EXT-30, EXT-31, EXT-32, EXT-33
- Partially covers: none
- Leaves for later: none
- Orphan risks: none — all 12 candidate requirements from research are mapped

## Slices

- [x] **S01: Backend AI endpoints with Bearer auth** `risk:high` `depends:[]`
  > After this: curl can call POST /api/llm/stream with Bearer token and get streamed LLM response; POST /api/ai/detect-claims accepts page text and returns structured JSON claims array; POST /api/ai/match-claims queries the graph and returns matches with contradiction/corroboration indicators; POST /api/ai/suggest-relationships returns relationship suggestions; POST /api/ai/summarize returns personalized summary. All endpoints return clear error when LLM is not configured. Unit tests prove all parsing, matching, and degradation paths.

- [x] **S02: Extension sidebar AI Insights UI** `risk:medium` `depends:[S01]`
  > After this: user visits a page, opens sidebar via Alt+K, and sees an "AI Insights" collapsible section with progressive loading — detected claims appear first, then graph matches with contradiction/corroboration badges, then relationship suggestions with Accept/Dismiss buttons, then personalized summary. Accept creates object+edge via existing SemPKMClient two-step pattern. Dismiss stores per-URL in chrome.storage.local. "Configure LLM" message shown when LLM unavailable.

- [x] **S03: E2E tests and user guide** `risk:low` `depends:[S01,S02]`
  > After this: Playwright E2E test with mock LLM server exercises full flow (page visit → sidebar → AI insights → accept suggestion → SPARQL verify edge). Chapter 40 user guide documents AI features. All three navigation files updated.

## Boundary Map

### S01 → S02

Produces:
- `POST /api/llm/stream` — Bearer-authenticated LLM streaming proxy (SSE, X-Accel-Buffering: no)
- `POST /api/ai/detect-claims` — accepts `{content: string, url: string, title: string}`, returns `{claims: [{text, confidence, type}]}` JSON
- `POST /api/ai/match-claims` — accepts `{claims: [{text, confidence, type}]}`, returns `{matches: [{claim_text, matched_objects: [{iri, label, type, match_type, indicator, confidence}]}]}` JSON
- `POST /api/ai/suggest-relationships` — accepts `{url, title, claims}`, returns `{suggestions: [{type, label, target_iri, target_label, reason}]}` JSON
- `POST /api/ai/summarize` — accepts `{content, graph_context: [{iri, label, type, snippet}]}`, returns `{summary: string}` JSON
- `GET /api/llm/status` — returns `{available: bool, provider: string|null}` for feature gating
- All endpoints use `get_current_user_or_api` for dual-auth (cookie + Bearer)

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Same API endpoints as S01 → S02

### S02 → S03

Produces:
- Extension sidebar AI Insights section with `_renderAIInsights()`, `_renderClaims()`, `_renderMatches()`, `_renderSuggestions()`, `_renderSummary()` rendering functions
- New `SemPKMClient` methods: `detectClaims()`, `matchClaims()`, `suggestRelationships()`, `summarizePage()`, `getLLMStatus()`
- Accept/dismiss action handlers in sidebar.js
- New message types in service-worker.js for AI operations

Consumes:
- S01 API endpoints
