# S04: E2E Tests + User Guide — Research

**Date:** 2026-03-18

## Summary

This is a direct clone of M016/S04 (Linear Sync E2E + user guide). The mock server switches from GraphQL substring matching to REST path-based routing; the Playwright test follows the same 10-phase structure; and the user guide follows Chapter 34's layout with GitHub-specific field mapping tables. No novel technology, no risky integration — pure pattern replication.

The mock GitHub REST API server needs five endpoints: `GET /user`, `GET /user/repos`, `GET /repos/{owner}/{repo}/issues`, `GET /repos/{owner}/{repo}/issues/{number}/timeline`, and `PATCH /repos/{owner}/{repo}/issues/{number}`. The client already uses `GITHUB_API_URL` env var (defaults to `https://api.github.com`), so pointing it at `http://mock-github:8080` in docker-compose.test.yml is all the wiring needed.

## Recommendation

Three tasks in sequence: (1) mock GitHub API server + docker-compose integration + selftest, (2) Playwright E2E test, (3) Chapter 35 user guide + glossary/README updates.

## Implementation Landscape

### Key Files

**Mock server:**
- `e2e/mock-linear-api/server.py` — Reference pattern. Clone and adapt: replace `do_POST` GraphQL matching with `do_GET`/`do_PATCH` path-based routing.
- `e2e/mock-github-api/server.py` — New file. Python `http.server` module, same structure as mock-linear.

**Docker-compose:**
- `docker-compose.test.yml` — Add `mock-github` service (identical structure to `mock-linear`), add `GITHUB_API_URL: http://mock-github:8080` to `api` env vars, add `mock-github` to `api.depends_on`.

**E2E test:**
- `e2e/tests/31-linear-sync/linear-sync.spec.ts` — Reference pattern. The github-sync test follows the same phase structure but with github-sync specific selectors.
- `e2e/tests/32-github-sync/github-sync.spec.ts` — New file. ~12 phases.
- `e2e/helpers/selectors.ts` — Add `githubSync` section (mirroring `linearSync` but with github-sync CSS IDs/classes).

**User guide:**
- `docs/guide/34-linear-sync.md` — Reference pattern for Chapter 35.
- `docs/guide/35-github-sync.md` — New file. Same structure as Ch 34 with GitHub-specific field mapping.
- `docs/guide/README.md` — Add Ch 35 entry after Ch 34.
- `docs/guide/appendix-d-glossary.md` — Add GitHub Sync entry.
- `docs/guide/34-linear-sync.md` — Update "Next" nav link to point to Ch 35 instead of Appendix A.

**GitHub sync app templates (existing, for selector reference):**
- `apps/github-sync/frontend/templates/connect.html` — PAT form uses `id="github-pat"`, class `api-key-form`
- `apps/github-sync/frontend/templates/connect_status.html` — Uses `.connection-status`, `.repo-checkbox-item`, `.sync-config-form`, `#sync-now-btn`, `.sync-stats`

### Mock Server Endpoints

The mock server needs canned responses for each endpoint the GitHubClient calls:

| Endpoint | Method | Canned Response |
|---|---|---|
| `/user` | GET | `{login, id, name, email}` — verifies PAT |
| `/user/repos` | GET | Array of 2 repos — `test-owner/test-repo` (with issues) + `test-owner/empty-repo` |
| `/repos/test-owner/test-repo/issues` | GET | Array of 3 items: 2 issues + 1 PR (has `pull_request` key) |
| `/repos/test-owner/test-repo/issues/1/timeline` | GET | Array with 1 `cross-referenced` event linking PR #3 to issue #1 |
| `/repos/test-owner/test-repo/issues/{n}` | PATCH | Returns updated issue dict (echoes title/state back) |
| `/health` | GET | `{status: ok}` — Docker healthcheck |

Issues should have:
- Issue #1: open, with labels and assignee, has PR cross-ref in timeline
- Issue #2: closed (state_reason: completed), no assignee
- Item #3: open PR (has `pull_request` key), with labels

This covers: open/closed status mapping, label→tag mapping, assignee resolution, PR detection, PR-to-issue edge creation via timeline, and push sync verification.

Rate limit headers (`X-RateLimit-Remaining: 4999`, `X-RateLimit-Reset: {future}`) should be included on every response to avoid triggering the rate-limit sleep in the client.

No Link header pagination needed — canned responses fit in single pages.

### E2E Test Phases

Following linear-sync.spec.ts structure:

1. **Phase 0 — Cleanup:** Remove github-sync if installed from prior run
2. **Phase 1 — Prerequisite:** Ensure basic-pkm model installed
3. **Phase 2 — Install:** Install github-sync app, poll until Running
4. **Phase 3 — Open settings:** Navigate to workspace, expand APPS, click GitHub Sync
5. **Phase 4 — Connect:** Fill PAT, click Connect, verify "Connected" + username
6. **Phase 5 — Select repos:** Check repo checkbox, save
7. **Phase 6 — Configure sync:** Set bidirectional, save config
8. **Phase 7 — Sync Now:** Click Sync Now, wait for stats, verify pull status "ok" or "success" and created count ≥ 2
9. **Phase 8 — Verify tasks via SPARQL:** COUNT bpkm:Task objects ≥ 2 (issues) + 1 (PR) = ≥ 3
10. **Phase 9 — Verify PR edge:** SPARQL query for bpkm:dependsOn edge between PR task and issue task
11. **Phase 10 — Admin detail:** Navigate to admin apps page, verify github-sync shows Running
12. **Phase 11 — Cleanup:** Uninstall github-sync

### Selectors for E2E

From the github-sync templates:

```typescript
githubSync: {
  patInput: '#github-pat',
  connectBtn: '.api-key-form button[type="submit"]',
  connectStatus: '.connection-status',
  username: '.username',
  repoCheckbox: '.repo-checkbox-item input[type="checkbox"]',
  saveReposBtn: '.repos-section button[type="submit"]',
  syncDirectionBidirectional: 'input[name="sync_direction"][value="bidirectional"]',
  saveConfigBtn: '.sync-config-form button[type="submit"]',
  syncNowBtn: '#sync-now-btn',
  syncStats: '.sync-stats',
}
```

### User Guide Structure

Clone Chapter 34 structure, adapting for GitHub:

1. Prerequisites (basic-pkm + GitHub PAT)
2. Installing the App (path: `/app/apps/github-sync`)
3. Connecting to GitHub (PAT only, no OAuth — per D206)
4. Selecting Repositories (vs Linear's team selection)
5. Sync Configuration (direction + poll interval — identical to Linear)
6. Manual Sync
7. Understanding Sync Stats
8. Field Mapping tables (GitHub → bpkm:Task, status mapping, PR handling)
9. Push Sync (supported fields: title + status, not labels per research constraint)
10. PR-to-Issue Linking (unique to GitHub sync — explain timeline API approach)
11. Admin Monitoring
12. Troubleshooting
13. See Also

The field mapping table from M017-RESEARCH.md is the authoritative source.

### Build Order

1. **Mock server + Docker** (T01) — unblocks E2E test. Selftest validates canned responses before Docker involvement.
2. **E2E test** (T02) — depends on mock server in Docker. The primary verification artifact for GH-07 and runtime validation for GH-01 through GH-06.
3. **User guide** (T03) — independent of E2E test. Can reference verified behavior from T02.

### Verification Approach

- T01: `python e2e/mock-github-api/server.py --selftest` passes. `docker compose -f docker-compose.test.yml up -d --build` starts mock-github healthy.
- T02: `npx playwright test e2e/tests/32-github-sync/github-sync.spec.ts` passes against Docker test stack.
- T03: `docs/guide/35-github-sync.md` exists with field mapping tables. README TOC includes Ch 35. Glossary has GitHub Sync entry. Navigation links updated (Ch 34 → Ch 35 → Appendix A).

## Constraints

- `GITHUB_API_URL` env var must point to `http://mock-github:8080` in docker-compose.test.yml (not the real GitHub API).
- The mock server runs on port 8080 inside Docker (same as mock-linear) but on a different container hostname.
- E2E test must use generous timeouts — app installation + startup + sync involves multiple Docker-internal HTTP calls.
- Explorer APPS section starts collapsed — test must click the section header to expand it before clicking GitHub Sync leaf (per KNOWLEDGE.md).
- htmx forms use `/app/github-sync/` proxy prefix — the test interacts with the workspace page, not the raw app routes.

## Common Pitfalls

- **Mock server must return arrays for paginated endpoints** — `fetch_repos()`, `fetch_issues()`, `fetch_timeline()` all call `_paginate()` which expects `isinstance(data, list)`. If the mock returns a dict, results silently become `[{whole_dict}]` instead of the expected item list.
- **Rate limit headers required on every response** — The `_check_rate_limit()` method reads `X-RateLimit-Remaining` from every response. If missing, it defaults to checking `X-RateLimit-Reset` which could cause an error or unexpected sleep. Include both headers on all mock responses.
- **PR detection relies on `pull_request` key existence** — The mock PR item must include `"pull_request": {"html_url": "..."}` (any truthy value) for `is_pull_request()` to detect it.
- **Timeline cross-ref event format** — The event must have `"event": "cross-referenced"` and `source.issue.pull_request` must be truthy, and `source.issue.repository.full_name` must match the repo. Missing any of these fields causes silent skip.
