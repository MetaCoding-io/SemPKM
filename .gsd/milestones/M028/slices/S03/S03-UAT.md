# S03: E2E tests and user guide — UAT

**Milestone:** M028
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven for docs + live-runtime for mock server and E2E)
- Why this mode is sufficient: Mock server selftest validates endpoints without Docker; docs are static artifacts verifiable by inspection; full E2E test requires live Docker stack but individual components can be verified offline

## Preconditions

- Working directory is the M027 worktree (or main tree with M028 code merged)
- Python 3.12+ available for mock server selftest
- For live E2E: Docker test stack running (`docker compose -f docker-compose.test.yml up -d`) with mock-llm service healthy
- For live E2E: Playwright and dependencies installed (`npx playwright install chromium`)

## Smoke Test

Run `python3 e2e/mock-llm-api/server.py --selftest` — should print 5/5 checks passed and exit 0. This confirms the mock LLM server endpoints work without Docker.

## Test Cases

### 1. Mock LLM server selftest validates all endpoints

1. Run `python3 e2e/mock-llm-api/server.py --selftest`
2. **Expected:** Output shows 5 checks with ✓ markers: GET /health → 200, GET /v1/models → 200 with test-model, POST /v1/chat/completions → 200 with claims, GET /unknown → 404, POST /unknown → 404. Final line: "5/5 checks passed". Exit code 0.

### 2. Mock LLM server returns valid claim JSON structure

1. Start the mock server: `python3 e2e/mock-llm-api/server.py &`
2. Run: `curl -s -X POST http://localhost:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"test","messages":[]}' | python3 -c "import sys,json; d=json.load(sys.stdin); c=json.loads(d['choices'][0]['message']['content']); assert len(c['claims'])==3; assert all(k in cl for cl in c['claims'] for k in ['text','confidence','type']); print('OK')"`
3. Kill the server
4. **Expected:** "OK" printed — the mock returns 3 claims each with text, confidence, and type fields

### 3. Mock LLM service in Docker compose

1. Run `grep -A 15 "mock-llm:" docker-compose.test.yml`
2. **Expected:** Service definition with image python:3.12-slim, volume mount `./e2e/mock-llm-api:/app:ro`, healthcheck using curl to /health, network sempkm-test
3. Run `grep "mock-llm" docker-compose.test.yml | grep depends_on -A5`
4. **Expected:** mock-llm appears in api service depends_on with condition: service_healthy

### 4. E2E test file structure and coverage

1. Run `grep -c "test(" e2e/tests/25-extension/extension-ai-insights.spec.ts`
2. **Expected:** 3 (three serial test cases)
3. Run `grep "test.describe.serial" e2e/tests/25-extension/extension-ai-insights.spec.ts`
4. **Expected:** Match found — tests run in serial order
5. Run `grep "configureLLM\|mock-llm:8080" e2e/tests/25-extension/extension-ai-insights.spec.ts`
6. **Expected:** Matches found — LLM configured to Docker-internal mock-llm hostname

### 5. E2E test covers graceful degradation

1. Run `grep -A5 "ai-unavailable" e2e/tests/25-extension/extension-ai-insights.spec.ts`
2. **Expected:** Test verifies `#ai-unavailable` element is visible when LLM is not configured, with text containing "LLM configuration"

### 6. E2E test verifies edge creation via SPARQL

1. Run `grep -B2 -A10 "sempkm:Edge" e2e/tests/25-extension/extension-ai-insights.spec.ts`
2. **Expected:** SPARQL query checking for `sempkm:Edge` with `sempkm:source` and `sempkm:predicate` — proves accept-suggestion creates the correct RDF edge

### 7. Chapter 40 content completeness

1. Run `wc -l docs/guide/40-ai-features.md`
2. **Expected:** ~170 lines
3. Run `grep "^##" docs/guide/40-ai-features.md`
4. **Expected:** Sections for at least: Claim Detection, Graph Matching, Relationship Suggestions, Personalized Summaries, Troubleshooting
5. Run `grep "confidence" docs/guide/40-ai-features.md | head -3`
6. **Expected:** Confidence level documentation (established, likely, possible, speculative)
7. Run `tail -3 docs/guide/40-ai-features.md`
8. **Expected:** Navigation footer with Previous → Chapter 39, Next → Appendix A

### 8. Three-file navigation sync

1. Run `grep "40-ai-features" docs/guide/README.md`
2. **Expected:** TOC entry like `40. [AI Features](40-ai-features.md)`
3. Run `grep "40-ai-features" docs/guide/index.html`
4. **Expected:** Sidebar `<li>` entry with data-file attribute
5. Run `grep "40-ai-features" backend/app/templates/guide.html`
6. **Expected:** htmx button with hx-get pointing to Chapter 40

### 9. Chapter 39 navigation chain updated

1. Run `tail -3 docs/guide/39-notion-import.md`
2. **Expected:** "Next: [Chapter 40: AI Features](40-ai-features.md)" — not "Next: Appendix A"

### 10. Glossary entries added

1. Run `grep "AI Insights\|Claim Detection\|Graph Matching" docs/guide/appendix-d-glossary.md`
2. **Expected:** At least 3 matches with cross-references to Chapter 40

## Edge Cases

### Mock LLM server handles unknown paths

1. Run `python3 e2e/mock-llm-api/server.py &` then `curl -s http://localhost:8080/nonexistent`
2. **Expected:** HTTP 404 with JSON body `{"message": "Not Found"}` — structured error, not HTML

### Mock LLM health endpoint for Docker healthcheck

1. Run `python3 e2e/mock-llm-api/server.py &` then `curl -s http://localhost:8080/health`
2. **Expected:** HTTP 200 with JSON `{"status":"ok"}`

### Chapter 40 has See Also cross-references

1. Run `grep "See Also\|Chapter 10\|Chapter 32\|Appendix A" docs/guide/40-ai-features.md`
2. **Expected:** Cross-references to related chapters present

## Failure Signals

- `python3 e2e/mock-llm-api/server.py --selftest` exits non-zero or reports ✗ markers — mock server broken
- `grep "40-ai-features"` returns fewer than 3 files — navigation sync incomplete
- Chapter 39 footer still points to "Appendix A" instead of "Chapter 40" — navigation chain broken
- E2E test file has fewer than 3 `test()` calls — test coverage insufficient
- No `sempkm:Edge` or `SPARQL` references in E2E test — edge verification missing
- Glossary matches fewer than 3 — glossary entries missing or misplaced

## Requirements Proved By This UAT

- EXT-32 — Mock LLM server returns canned claim JSON for deterministic testing; Playwright E2E test exercises sidebar AI insights → accept suggestion → verify object/edge created via SPARQL
- EXT-33 — Chapter 40 documents claim detection, graph matching, suggestions, personalized summaries, accept/dismiss, and troubleshooting; all 3 navigation files updated

## Not Proven By This UAT

- Full sidebar progressive rendering (claims → matches → suggestions → summary appearing sequentially) — requires live Docker stack with navigable content page in persistent context
- Firefox extension behavior — Playwright lacks Firefox --load-extension support
- Real LLM quality (claim extraction accuracy on real web pages) — mock returns fixed canned responses
- Performance under load (5-second latency target) — not measured with mock server

## Notes for Tester

- The mock LLM selftest is the fastest validation — run it first. If it fails, nothing downstream works.
- The E2E test is designed for the Docker test stack. Running it locally requires `docker compose -f docker-compose.test.yml up -d` with mock-llm healthy.
- The `configureLLM()` helper uses `http://mock-llm:8080` (Docker-internal hostname). This is intentional — the Python backend inside Docker makes the LLM call, not the browser.
- Chapter 40's troubleshooting section documents the same failure modes the E2E test verifies (LLM not configured, no Research model for matching).
