---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M028

## Success Criteria Checklist

- [x] **User visits a page and the sidebar's AI Insights section shows auto-detected claims with confidence indicators within 5 seconds** — evidence: S01 delivers `POST /api/ai/detect-claims` returning structured JSON with confidence/type fields (12 unit tests). S02 delivers `_renderClaimsSection()` with 4-color confidence badges (established=green, likely=blue, possible=amber, speculative=gray). S02 verification check #6 confirms all rendering functions exist. S03 E2E test 2 proves claim detection returns valid structured JSON from mock LLM. *Note: full sidebar rendering pipeline not E2E-tested due to persistent context limitation with chrome.scripting.executeScript — S03 uses API-only verification.*

- [x] **A detected claim that contradicts an existing Claim object in the graph displays contradiction indicator with a link** — evidence: S01 `_compute_indicator()` with 13 indicator logic tests covering bidirectional contradiction (high-existing/low-detected and low-existing/high-detected both map to 'contradicts'). S02 renders indicator badges (contradicts=red, corroborates=green, contested=amber, related=gray) nested under claim headers in `_renderMatchesSection()`.

- [x] **Extension shows research question gap alert when topics match open questions** — evidence: S01 `_find_research_gaps()` with keyword overlap analysis (≥2 meaningful words after stop-word filtering), 2 dedicated research gap tests + endpoint integration. S02 renders research gaps as alert-style cards in matches section.

- [x] **User sees relationship suggestion and can accept it with one click, creating the edge** — evidence: S01 `POST /api/ai/suggest-relationships` returns URL+FTS-based suggestions (4 integration tests). S02 renders suggestion cards with Accept/Dismiss buttons, Accept maps 4 suggestion types to distinct API command sequences (link→edge.create with schema:url, evidence→object.create+edge.create, supports→edge.create with res:supports, contradicts→edge.create with res:refutes). S03 E2E test 3 sends `acceptSuggestion` message to service worker and verifies edge creation via SPARQL query for `sempkm:Edge`.

- [x] **User requests personalized summary incorporating existing knowledge** — evidence: S01 `POST /api/ai/summarize` builds prompt incorporating graph context objects as context items (3 integration tests including graph context verification). S02 `_renderSummarySection()` renders styled text panel.

- [x] **All AI features degrade gracefully** — evidence: S01 returns 503 JSON `{"error": "LLM not configured"}` on all LLM-dependent endpoints (3 degradation tests). S01 `match-claims` and `suggest-relationships` work without LLM. S02 `_renderUnavailable()` shows "AI features require LLM configuration" message when `getLLMStatus()` returns `available: false`. S03 E2E test 1 verifies `/api/llm/status` returns `{available: false}` before configuration and `#ai-unavailable` appears in the sidebar.

- [x] **Accept creates correct object/edge via two-step pattern; dismiss persists per-URL in chrome.storage.local** — evidence: S02 Accept handler uses closure-based event handlers mapping 4 suggestion types to distinct command sequences. S02 Dismiss handler stores per-URL IRI arrays in `chrome.storage.local` with `dismissed_${url}` keys. S03 E2E test 3 verifies accept creates edge via SPARQL. S02 verification check #9 confirms `dismissed_` key pattern in service-worker.js.

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | 6 AI backend endpoints with Bearer auth, unit tests for parsing/matching/degradation | All 6 endpoints implemented in `backend/app/api/ai.py` (1119 lines) with dual-auth, 59 unit tests across 4 test files, well-known discovery updated | pass |
| S02 | Sidebar AI Insights UI with progressive loading, accept/dismiss, graceful degradation | Full AI Insights section with 6 rendering functions, 5 service worker handlers, generationId stale-update guard, 22 Node.js unit tests for API client, ~315 lines CSS | pass |
| S03 | E2E tests with mock LLM, Chapter 40 user guide, navigation updates | Mock LLM server (5-check selftest), 3 serial Playwright E2E tests, Chapter 40 (~170 lines, 8 sections), 3 navigation files updated, 3 glossary entries | pass — with deviation: API-only claim verification instead of full sidebar rendering |

## Cross-Slice Integration

**S01 → S02 boundary:** S01 produces all 6 endpoints with exact Pydantic schemas documented in boundary map. S02 summary confirms "S01 backend endpoints matched the contract exactly as documented in the boundary map" — no deviations. S02 consumes all 6 endpoints via 5 new `SemPKMClient` methods + direct `fetch()` calls in service worker.

**S01 → S03 boundary:** S03 mock LLM server provides canned responses to `POST /v1/chat/completions`. S03 E2E test calls `POST /api/ai/detect-claims` directly against the Docker stack backed by mock-llm service. No boundary mismatch.

**S02 → S03 boundary:** S03 E2E test 3 sends `acceptSuggestion` message via `chrome.runtime.sendMessage` — exercising the same code path the UI uses (S02's service worker handler). S03 E2E test 1 checks `#ai-unavailable` DOM element created by S02's `_renderUnavailable()`. Integration points align.

**No boundary mismatches detected.**

## Requirement Coverage

All 12 requirements from the roadmap (EXT-22 through EXT-33) are addressed:

| Requirement | Slice | Evidence | Status |
|-------------|-------|----------|--------|
| EXT-22 — Bearer LLM proxy | S01 | 8 unit tests (LLM stream SSE, status, auth, degradation) | advanced |
| EXT-23 — Claim detection | S01 | 12 unit tests (parser, prompt, endpoint), S03 E2E test 2 | advanced |
| EXT-24 — Claim→graph matching | S01 | 22 unit tests (indicator logic, endpoint, search errors) | advanced |
| EXT-25 — Contradiction/corroboration indicators | S01 | 13 indicator logic tests (bidirectional contradiction, multiple corroboration variants) | advanced |
| EXT-26 — Research question gap detection | S01 | 2 research gap tests + endpoint integration | advanced |
| EXT-27 — Relationship suggestions | S01 | 4 integration tests (URL matching, FTS keyword, dedup, cap) | advanced |
| EXT-28 — Personalized summary | S01 | 3 integration tests (success, graph context, LLM error fallback) | advanced |
| EXT-29 — Accept/dismiss UI | S02 | Closure-based handlers, 4 type mappings, chrome.storage.local dismiss; S03 E2E test 3 | advanced |
| EXT-30 — Progressive loading | S02 | `aiInsightsProgress` message protocol with generationId, section-by-section rendering | advanced |
| EXT-31 — Graceful degradation | S01+S02 | 503 JSON + _renderUnavailable(); S03 E2E test 1 | advanced |
| EXT-32 — E2E tests with mock LLM | S03 | 3 serial Playwright E2E tests, mock server with 5-check selftest | **validated** |
| EXT-33 — User guide Chapter 40 | S03 | Chapter 40 (~170 lines, 8 sections), 3 nav files updated, 3 glossary entries | **validated** |

**No unaddressed requirements.** EXT-22 through EXT-31 are "advanced" (implementation complete, unit-tested, partially E2E-tested) but not "validated" because the full sidebar rendering pipeline was not E2E-tested end-to-end. This is a Playwright persistent context limitation, not a code gap.

## Definition of Done Checklist

| # | Criterion | Met? | Notes |
|---|-----------|------|-------|
| 1 | All 4 backend AI endpoints return correct responses with Bearer auth | ✅ | Actually 6 endpoints (roadmap counted detect-claims, match-claims, suggest-relationships, summarize; plus llm/stream, llm/status). All dual-auth. 59 unit tests. |
| 2 | Extension sidebar shows AI Insights section with progressive loading | ✅ | 6 rendering functions, generationId stale-update guard, CSS for all sections. S02 verification checks 5-8 confirm. |
| 3 | Accept/dismiss actions create correct objects/edges and persist dismissals | ✅ | 4 suggestion type mappings, chrome.storage.local dismiss. S03 E2E test 3 proves edge creation via SPARQL. |
| 4 | Graceful degradation verified | ✅ | S03 E2E test 1 proves LLM-unconfigured path. S01 unit tests prove match-claims works without LLM. |
| 5 | Playwright E2E test proves full flow | ⚠️ | 3 serial E2E tests prove: degradation, claim detection (API-only), and accept→edge creation. Full sidebar rendering pipeline not tested (persistent context can't reliably trigger chrome.scripting.executeScript). Same backend code path is exercised. |
| 6 | User guide Chapter 40 with screenshots and troubleshooting | ⚠️ | Chapter 40 exists with 8 sections including troubleshooting. Screenshots not explicitly confirmed in S03 summary. |
| 7 | All new unit tests pass, zero regressions | ✅ | S01: 59 tests in 1.27s. S02: 22 tests. S03: 5-check selftest. No regressions reported. |

## Verdict Rationale

**Verdict: needs-attention** — All planned deliverables are present and functional. The core AI pipeline (claim detection → graph matching → relationship suggestions → personalized summary) is fully implemented across backend (S01) and extension frontend (S02), with comprehensive unit test coverage (81 tests total). The E2E tests prove the critical integration paths (graceful degradation, claim detection via mock LLM, edge creation from accepted suggestions).

Two minor gaps prevent a clean `pass`:

1. **E2E test scope limitation:** The Playwright E2E test does not exercise the full sidebar rendering pipeline (page visit → sidebar opens → claims render → matches render → suggestions render → summary renders). It uses API-only verification for claim detection and message-passing for accept suggestion. This is a known Playwright persistent context limitation (chrome.scripting.executeScript for page content extraction is unreliable), not a missing feature. The S03 summary documents this deviation transparently. The same backend code paths are exercised.

2. **Chapter 40 screenshots:** The Definition of Done specifies "screenshots" in the user guide, but S03's summary describes ~170 lines of text content with 8 sections. Screenshots are not explicitly mentioned as included. This is a documentation completeness gap, not a functional gap.

Neither gap warrants remediation slices — the first is a tooling constraint (Playwright + persistent contexts), and the second is a minor docs polish item. EXT-22 through EXT-31 remain at "active/advanced" status until full E2E validation is achievable, which may require future Playwright improvements or a manual UAT pass.

## Remediation Plan

No remediation slices needed. The gaps are:
- E2E sidebar rendering: blocked by Playwright persistent context limitation, not by missing code. A future UAT pass against a real browser can validate this.
- Screenshots in Chapter 40: minor polish — can be added in any future milestone that touches the user guide.
