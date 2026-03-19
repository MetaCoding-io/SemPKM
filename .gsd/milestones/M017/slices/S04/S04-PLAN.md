# S04: E2E Tests + User Guide

**Goal:** Prove integration with a mock GitHub REST API server and Playwright E2E test, and document the GitHub sync workflow in Chapter 35.

**Demo:** `python3 e2e/mock-github-api/server.py --selftest` passes. Playwright E2E test covers the full lifecycle against Docker test stack. Chapter 35 documents the sync workflow.

## Must-Haves

- Mock GitHub REST API server with canned responses for: `/user`, `/user/repos`, `/repos/{owner}/{repo}/issues`, `/repos/{owner}/{repo}/issues/{number}/timeline`, `PATCH /repos/{owner}/{repo}/issues/{number}`
- GITHUB_API_URL env var for test/production flexibility (like LINEAR_API_URL)
- Playwright E2E spec covering ~12 phases: cleanup → install → connect → select repos → configure → sync → verify via SPARQL → push → verify push → admin detail → cleanup
- docker-compose.test.yml updates: mock-github service, GITHUB_API_URL env var
- User guide Chapter 35 with field mapping tables, setup instructions, troubleshooting
- README TOC, glossary entries, navigation chain updates

## Verification

- `python3 e2e/mock-github-api/server.py --selftest` — passes
- `docker compose -f docker-compose.test.yml config --quiet` — valid compose
- `node --check e2e/tests/32-github-sync/github-sync.spec.ts` — syntax valid
- Chapter 35 committed with ≥10 sections

## Tasks

- [ ] **T01: Mock GitHub REST API server** `est:45m`
  - Why: E2E test needs a controllable GitHub API — real API is non-deterministic
  - Files: `e2e/mock-github-api/server.py`
  - Do: Python stdlib HTTP server (following M016's mock-linear-api pattern) returning canned REST responses. Match request path and method: GET `/user` → user JSON, GET `/user/repos` → repo list, GET `/repos/testowner/testrepo/issues?state=all` → issues + PRs list (include one issue and one PR with `pull_request` key), GET `/repos/testowner/testrepo/issues/1/timeline` → cross-referenced event linking PR#2 to issue#1, PATCH `/repos/testowner/testrepo/issues/{number}` → echo back patched fields. Link header pagination (return `Link: <url>; rel="next"` on first page, no Link on last). Rate-limit headers on all responses. `--selftest` flag validates all canned responses without network.
  - Verify: `python3 e2e/mock-github-api/server.py --selftest`
  - Done when: Selftest passes, all 5 endpoint types return correct canned data

- [ ] **T02: Docker config + GITHUB_API_URL env var + E2E spec** `est:45m`
  - Why: Proves the full integrated lifecycle against Docker test stack
  - Files: `docker-compose.test.yml`, `apps/github-sync/services/github_client.py`, `e2e/tests/32-github-sync/github-sync.spec.ts`, `e2e/helpers/selectors.ts`
  - Do: Add `GITHUB_API_URL` env var to GitHubClient (default `https://api.github.com`, override for test). Add mock-github service to docker-compose.test.yml (python3 server.py on port 4011). Pass `GITHUB_API_URL=http://mock-github:4011` to api service. Write Playwright E2E spec: Phase 0 cleanup, Phase 1 install basic-pkm, Phase 2 install github-sync, Phase 3 connect PAT, Phase 4 select repo, Phase 5 configure sync direction, Phase 6 Sync Now, Phase 7 verify tasks via SPARQL, Phase 8 verify PR task with different provider, Phase 9 verify PR-to-issue edge, Phase 10 push change (if bidirectional), Phase 11 admin detail, Phase 12 cleanup. Add githubSync selector section to selectors.ts.
  - Verify: `docker compose -f docker-compose.test.yml config --quiet` + `node --check e2e/tests/32-github-sync/github-sync.spec.ts`
  - Done when: Compose config valid, spec syntax valid, test structurally correct

- [ ] **T03: User guide Chapter 35 + glossary + README** `est:30m`
  - Why: Standing requirement — user-visible features must be documented
  - Files: `docs/guide/35-github-sync.md`, `docs/guide/README.md`, `docs/guide/34-linear-sync.md`, `docs/guide/appendix-d-glossary.md`
  - Do: Chapter 35 with sections: Overview, Prerequisites (PAT with repo scope), Installation, Connecting (PAT), Selecting Repositories, Sync Settings (direction, interval), Running Sync, Field Mapping (issue→task table from research), PR Handling, Viewing Synced Tasks, Pushing Changes, Troubleshooting (rate limits, missing issues, cross-repo edges). Update README TOC with Chapter 35. Update Chapter 34 nav footer to link to Chapter 35. Add glossary entries: GitHub Sync, Pull Request Linking. Update Chapter 35 nav footer to link to Appendix A.
  - Verify: File exists with ≥10 sections, README TOC includes Chapter 35
  - Done when: Chapter 35 committed, navigation chain correct, glossary entries added

## Files Likely Touched

- `e2e/mock-github-api/server.py`
- `e2e/tests/32-github-sync/github-sync.spec.ts`
- `e2e/helpers/selectors.ts`
- `docker-compose.test.yml`
- `apps/github-sync/services/github_client.py`
- `docs/guide/35-github-sync.md`
- `docs/guide/README.md`
- `docs/guide/34-linear-sync.md`
- `docs/guide/appendix-d-glossary.md`
