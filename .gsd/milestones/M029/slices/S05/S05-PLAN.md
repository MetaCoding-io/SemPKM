# S05: Lighthouse Verification & QUIC/HTTP/3 Decision

**Goal:** Document Lighthouse before/after measurements with metric deltas, record QUIC/HTTP/3 decision, register and validate all PERF requirements, and verify E2E tests pass against the optimized build.
**Demo:** Lighthouse report shows desktop Performance score with FCP, LCP, TTI, TBT, CLS documented. QUIC/HTTP/3 decision appears in DECISIONS.md. PERF-02 through PERF-10 are in REQUIREMENTS.md with validation proofs. E2E tests pass (or failures triaged as pre-existing).

## Must-Haves

- Lighthouse desktop preset run against authenticated workspace page (port 3000) with JSON report saved
- Before/after delta table documenting FCP, LCP, TTI, TBT, CLS with "before" estimated from pre-M029 baseline
- QUIC/HTTP/3 decision recorded via `gsd_save_decision` (defer — nginx:stable-alpine lacks HTTP/3, minimal benefit for self-hosted single-user)
- PERF-02 through PERF-10 requirements registered in REQUIREMENTS.md with status and validation proofs from S01–S04 summaries
- E2E test results documented — pass or failures triaged as pre-existing vs optimization-related

## Proof Level

- This slice proves: final-assembly (milestone-closing verification and documentation)
- Real runtime required: yes (Lighthouse against Docker stack, E2E tests)
- Human/UAT required: no

## Verification

- `ls .gsd/milestones/M029/slices/S05/lighthouse-after.report.json` — Lighthouse JSON report exists
- `grep 'PERF-02' .gsd/REQUIREMENTS.md` — PERF requirements registered
- `grep 'QUIC' .gsd/DECISIONS.md` — QUIC/HTTP/3 decision recorded
- `ls .gsd/milestones/M029/slices/S05/S05-SUMMARY.md` — Slice summary exists with before/after delta table and E2E results

## Integration Closure

- Upstream surfaces consumed: S01 (optimized assets at port 3000), S02 (gzip + cache headers), S03 (CSS code-splitting), S04 (timing + ETag middleware — worktree only, validated by unit tests)
- New wiring introduced in this slice: none — documentation and verification only
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Run Lighthouse measurements and document before/after deltas** `est:45m`
  - Why: Produces the Lighthouse data that PERF-07 requires and the before/after comparison that is a milestone success criterion. Must run against authenticated workspace page with desktop preset.
  - Files: `.gsd/milestones/M029/slices/S05/lighthouse-after.report.json`, `.gsd/milestones/M029/slices/S05/lighthouse-after.report.html`
  - Do: (1) Get auth session cookie from running Docker stack at port 3000 via magic-link → verify flow. (2) Run Lighthouse 3 times with `--preset=desktop --chrome-flags="--headless=new --no-sandbox"` and `--extra-headers` cookie. (3) Save JSON+HTML reports. (4) Extract median scores for Performance, FCP, LCP, TTI, TBT, CLS. (5) Also run compression/caching spot checks via curl (gzip on /assets/, immutable cache headers, CSS code-splitting on admin pages, ETag on /api/ — these complement Lighthouse). (6) Write a results markdown file documenting the before/after delta table. The "before" is an estimate (~40-60) based on known pre-M029 state: 18 CDN loads, no compression, no caching, no CSS splitting. Document that this is an estimate since the baseline wasn't captured before S01 work began.
  - Verify: `lighthouse-after.report.json` exists and contains `categories.performance.score`. Before/after delta table is in the results file.
  - Done when: Lighthouse JSON report saved, median desktop scores documented, before/after delta table written, spot checks documented.

- [x] **T02: Record QUIC/HTTP/3 decision and register PERF-02 through PERF-10 requirements** `est:30m`
  - Why: The roadmap requires QUIC/HTTP/3 decision in DECISIONS.md and PERF requirements in REQUIREMENTS.md. These are milestone definition-of-done items. PERF-02 through PERF-10 are referenced throughout S01–S04 summaries but never registered.
  - Files: `.gsd/DECISIONS.md`, `.gsd/REQUIREMENTS.md`
  - Do: (1) Call `gsd_save_decision` with scope=tech, decision="QUIC/HTTP/3 for self-hosted Docker deployment", choice="Defer — document rationale only", rationale covering nginx:stable-alpine lack of HTTP/3, minimal QUIC benefit for self-hosted single-user tool, Caddy alternative exists for demo (D246), revisable=Yes. (2) Register PERF-02 through PERF-10 requirements using the GSD requirement tools — each with description, class, status, primary_owner, validation proof referencing the appropriate S01–S04 summary evidence and T01 Lighthouse results.
  - Verify: `grep 'QUIC' .gsd/DECISIONS.md` shows decision. `grep -c 'PERF-' .gsd/REQUIREMENTS.md` returns ≥10 (PERF-01 already exists + PERF-02 through PERF-10).
  - Done when: QUIC/HTTP/3 decision recorded. All 9 PERF requirements (PERF-02 through PERF-10) appear in REQUIREMENTS.md with validation proofs.

- [x] **T03: E2E test verification against optimized build and slice summary** `est:30m`
  - Why: Roadmap requires "All existing E2E tests pass against the optimized build." Also produces the slice summary that closes S05 and M029.
  - Files: `.gsd/milestones/M029/slices/S05/S05-SUMMARY.md`
  - Do: (1) Run existing E2E tests against the main Docker stack (port 3000) using `TEST_BASE_URL=http://localhost:3000`. The test compose auth fixture reads setup token from docker-compose.test.yml containers — since we're using the main stack, either adapt the auth approach or run a representative subset of tests that can authenticate against port 3000. If full E2E suite can't run against port 3000 due to auth fixture incompatibility, run the test compose stack (port 3901) tests to verify nothing is broken, then document the limitation. (2) Triage any failures as pre-existing vs optimization-related. (3) Write S05-SUMMARY.md with: what happened, verification table, requirements validated (PERF-02 through PERF-10), before/after Lighthouse delta table (from T01 results), E2E results, forward intelligence.
  - Verify: E2E test results documented. S05-SUMMARY.md exists with complete verification table.
  - Done when: E2E test pass/fail documented with triage. S05-SUMMARY.md written with all sections complete.

## Observability / Diagnostics

- **Lighthouse JSON reports** — saved to `.gsd/milestones/M029/slices/S05/lighthouse-after.report.json`. Contains `finalDisplayedUrl` (must be `/browser/`, not `/login.html`), `categories.performance.score`, and all audit metrics. Inspect with `python3 -c "import json; ..."`.
- **Lighthouse HTML reports** — visual inspection at `.gsd/milestones/M029/slices/S05/lighthouse-after.report.html`. Open in browser for detailed audit breakdowns.
- **Curl spot checks** — compression (`Content-Encoding: gzip`), caching (`Cache-Control: public, max-age=31536000, immutable`), CSS code-splitting (admin pages load 0 workspace CSS files). These complement Lighthouse with direct HTTP header inspection.
- **Auth failure visibility** — if Lighthouse measures the login page instead of workspace, `finalDisplayedUrl` will show `/login.html`. This is the primary failure signal. Always verify before trusting Performance scores.
- **S04 middleware absence** — TimingMiddleware and ConditionalGetMiddleware exist in worktree only (validated by 36 unit tests) but are NOT in the running Docker stack. `Server-Timing` and `ETag` headers will be absent from curl checks — this is expected, not a failure.
- **Failure diagnostic** — if Lighthouse fails to connect, verify Docker stack is running with `curl -s http://localhost:3000/api/health`. If auth fails, verify magic-link flow returns a token and cookie exchange succeeds.

## Verification

- `ls .gsd/milestones/M029/slices/S05/lighthouse-after.report.json` — Lighthouse JSON report exists
- `grep 'PERF-02' .gsd/REQUIREMENTS.md` — PERF requirements registered
- `grep 'QUIC' .gsd/DECISIONS.md` — QUIC/HTTP/3 decision recorded
- `ls .gsd/milestones/M029/slices/S05/S05-SUMMARY.md` — Slice summary exists with before/after delta table and E2E results
- `python3 -c "import json; d=json.load(open('.gsd/milestones/M029/slices/S05/lighthouse-after.report.json')); assert '/browser' in d['finalDisplayedUrl'], 'Auth failed - measured login page'; print('OK: measured', d['finalDisplayedUrl'])"` — Lighthouse measured authenticated workspace, not login page
- `grep -c 'PERF-' .gsd/REQUIREMENTS.md` — returns ≥10 (PERF-01 existed + 9 new) — diagnostic for requirement registration completeness
- `grep -E 'E2E|e2e|test' .gsd/milestones/M029/slices/S05/S05-SUMMARY.md | head -5` — E2E test results documented in summary (failure-path: if absent, T03 did not complete E2E verification)

## Files Likely Touched

- `.gsd/milestones/M029/slices/S05/lighthouse-after.report.json`
- `.gsd/milestones/M029/slices/S05/lighthouse-after.report.html`
- `.gsd/milestones/M029/slices/S05/lighthouse-results.md`
- `.gsd/DECISIONS.md`
- `.gsd/REQUIREMENTS.md`
- `.gsd/milestones/M029/slices/S05/S05-SUMMARY.md`
