# M017: GitHub Issues Sync App — Research

**Date:** 2026-03-18

## Summary

M016 Linear Sync established a clean, well-tested sync app architecture on the App Platform. M017 GitHub Issues Sync should be a near-clone of that architecture, swapping the GraphQL Linear client for a REST-based GitHub client. The field mapping is simpler than Linear (GitHub has no native priority field, uses open/closed state model), but PR-to-issue linking introduces a novel requirement not present in M016.

GitHub REST API v3 is the right choice per the context doc — simpler than GraphQL for this scope, 5000 requests/hour with token auth, cursor-based pagination via Link headers. The main architectural risk is PR-to-issue linking: GitHub's API doesn't return this as a first-class relationship. The `timeline` events endpoint (`GET /repos/{owner}/{repo}/issues/{number}/timeline`) returns `cross-referenced` events when a PR references an issue, which is the most reliable approach. Text parsing of "Closes #42" in PR bodies is fragile and unnecessary when the timeline API exists.

OAuth App authentication (not GitHub App) matches the context scope. GitHub OAuth uses a simple code-exchange flow similar to Linear's. Personal Access Tokens (classic or fine-grained) serve as the API key equivalent for local dev.

## Recommendation

Clone the Linear Sync architecture file-for-file, adapting each module:

| Linear Sync File | GitHub Sync Equivalent | Changes |
|---|---|---|
| `linear_client.py` | `github_client.py` | REST (httpx GET/PATCH/POST) instead of GraphQL, Link-header pagination |
| `field_mapper.py` | `field_mapper.py` | Simpler status map (open→todo, closed→done), no native priority, label→tag mapping |
| `sync_engine.py` | `sync_engine.py` | Nearly identical two-phase bulk pattern; add PR sync + PR-to-issue edge linking |
| `person_matcher.py` | `person_matcher.py` | Reuse verbatim — same SPARQL pattern, GitHub provides username + email |
| `auth.py` | `auth.py` | OAuth code exchange against `github.com/login/oauth`, PAT for API key mode |
| `app.py` | `app.py` | Same route structure, add repo selection (vs team selection) |
| `manifest.yaml` | `manifest.yaml` | Same shape, `api.github.com` + `github.com` in network permissions |

**Build order:** Auth + client first (proves API access), then pull sync for issues (core value), then PR sync + linking (novel risk), then push sync (reversal), then settings/docs/E2E.

## Implementation Landscape

### Key Files

- `apps/linear-sync/` — Complete reference implementation to clone. Every file maps 1:1.
- `apps/linear-sync/services/sync_engine.py` — Two-phase bulk create pattern (D204) — reuse exactly. Bypasses SDK IRI prefix check via `ctx.commands._client`.
- `apps/linear-sync/services/field_mapper.py` — Pure-function pattern with `build_task_properties()`, `build_issue_query()` equivalents. Unit-testable with zero mocks.
- `apps/linear-sync/services/person_matcher.py` — SPARQL email lookup + Person creation. Reuse verbatim or near-verbatim.
- `apps/linear-sync/manifest.yaml` — Manifest template: permissions, tasks, frontend, ui.pages.
- `backend/sdk/sempkm_app_sdk/` — SDK clients (commands, graph, http, state, settings). No SDK changes needed.
- `models/basic-pkm/` — bpkm:Task shape defines target properties. Same as Linear sync.
- `apps/linear-sync/frontend/templates/` — connect.html + connect_status.html. Adapt for repo selection UI.
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` — Cross-provider field coverage matrix (GitHub not explicitly mapped but follows same bpkm:Task pattern as Linear/Asana/Jira).

### GitHub API Specifics

**Issues endpoint:** `GET /repos/{owner}/{repo}/issues` — returns both issues and PRs (PRs are issues with a `pull_request` key). Filter with `?state=all&since={ISO8601}` for delta sync. Pagination via `Link` header (not cursor-based like GraphQL).

**PR-to-issue linking:** `GET /repos/{owner}/{repo}/issues/{number}/timeline` returns `cross-referenced` events when a PR body contains "Closes #42", "Fixes #42", etc. The event includes `source.issue.pull_request` confirming it's a PR. This is the reliable approach — no text parsing needed.

**Rate limiting:** 5000 requests/hour with token auth, 60/hour unauthenticated. `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers on every response. Client should check remaining count and sleep if approaching zero.

**Repo listing:** `GET /user/repos?type=owner&sort=updated` for repo selection in settings UI. Also `GET /orgs/{org}/repos` for org repos.

### GitHub → bpkm:Task Field Mapping

| GitHub Field | bpkm Property | Transform | Direction |
|---|---|---|---|
| `title` | `dcterms:title` | Direct | ↔ |
| `body` (Markdown) | body content | Direct (both Markdown) | ↔ |
| `state` | `bpkm:taskStatus` | open→todo, closed→done | ↔ |
| `state_reason` | `bpkm:externalStatus` | completed/not_planned/reopened | ← |
| `labels[].name` | `bpkm:tags` | Label names as tags | ↔ |
| `assignees[].login` | `bpkm:assignedTo` | Username → Person IRI (first assignee) | ↔ |
| `milestone.title` | `bpkm:taskProject` | Milestone → Project/Milestone IRI | ← |
| `number` | `bpkm:externalId` | e.g., "#42" | ← |
| `html_url` | `bpkm:externalUrl` | Direct | ← |
| `node_id` | `bpkm:externalUuid` | GitHub's global node ID | ← |
| `updated_at` | loop prevention | ISO-8601 comparison | internal |
| `pull_request` key | `bpkm:externalProvider` | "github-pr" vs "github" | ← |

**Notable gaps vs Linear:** No native priority field (labels can simulate), no estimate/effort field, no native subtask support (can use task lists in body but not API-accessible), simpler status model (open/closed vs Linear's 5-state machine).

### GitHub → bpkm:Milestone Mapping

| GitHub Field | bpkm Property | Transform |
|---|---|---|
| `milestone.title` | `dcterms:title` | Direct |
| `milestone.description` | `dcterms:description` | Direct |
| `milestone.state` | `bpkm:taskStatus` | open→todo, closed→done |
| `milestone.due_on` | `bpkm:dueDate` | ISO date truncation |
| `milestone.html_url` | `bpkm:externalUrl` | Direct |

### PR Handling

PRs are bpkm:Task objects with `externalProvider: "github-pr"`. The field mapping is identical to issues. PR-to-issue edges use `bpkm:dependsOn` (or a custom `bpkm:closesIssue` if the roadmap planner prefers a specific predicate). Edge direction: PR → Issue (PR closes/fixes issue).

Cross-repo dependency tracking (context scope item) works because each synced repo produces Task IRIs with repo-scoped slugs. A PR in repo-A referencing issue #42 in repo-B produces an edge if both repos are synced.

### IRI Minting

Follow Linear's `compute_issue_slug()` pattern: `SHA-256(repo_full_name + issue_number)[:16]` → `urn:sempkm:object:.../Task/gh-{hash16}`. The `repo_full_name` (e.g., `owner/repo`) ensures cross-repo uniqueness.

### Build Order

1. **Auth + Client** (proves API access, unblocks everything) — GitHub OAuth code exchange + PAT storage, REST client with pagination and rate-limit handling
2. **Pull sync: Issues** (core value) — Issue → bpkm:Task field mapping, two-phase bulk create, delta sync via `since` param
3. **Pull sync: PRs + linking** (novel risk) — PR detection via `pull_request` key, timeline API for cross-references, edge creation
4. **Push sync** (reversal) — Detect local changes, PATCH issues via REST API, loop prevention via `updated_at` comparison
5. **Settings UI + repo selection** — Repo picker, sync direction, poll interval
6. **E2E tests + user guide** — Mock GitHub API server (like M016's mock Linear), Playwright test, Chapter 35

### Verification Approach

- **Unit tests:** importlib-loaded from `apps/github-sync/services/` into `backend/tests/` (D203 pattern). Pure-function field mapper tests, mock httpx for client tests.
- **Mock API server:** Simple FastAPI app returning canned GitHub REST responses (repos, issues, PRs, timeline events). Follows M016's `e2e/mock-linear-api.js` pattern but for REST endpoints.
- **E2E test:** Install app → configure PAT → select repo → poll → verify tasks via SPARQL → push change → verify via mock API. ~12 phases following M016's 11-phase pattern.
- **Standing requirements:** E2E Playwright test + user guide chapter (Chapter 35).

## Constraints

- **App template htmx URLs must use `/app/github-sync/` prefix** (knowledge: "App template htmx URLs must use proxy prefix"). All `hx-post`/`hx-get` in templates must be prefixed.
- **SDK IRI prefix enforcement** bypassed via `ctx.commands._client` for bulk commands targeting platform-minted `urn:sempkm:object:` IRIs (D204). Same pattern as Linear.
- **GitHub REST API pagination** uses Link headers (RFC 8288), not cursor variables. Client must parse `<url>; rel="next"` from response headers.
- **GitHub issues endpoint returns PRs too** — must filter by presence/absence of `pull_request` key to distinguish.
- **No webhook support for local dev** — polling only (same as Linear per D200). Webhook endpoint can be stubbed for future external routing.

## Common Pitfalls

- **PR-to-issue linking via body text parsing** — Fragile regex for "Closes #42" variants. Use the timeline API instead — it returns structured `cross-referenced` events that definitively link PRs to issues.
- **Rate limit exhaustion on initial sync** — A repo with 500+ issues could consume significant quota. Implement `X-RateLimit-Remaining` checking with backoff sleep, not just error-on-429.
- **GitHub's `state_reason` field** — Only available on issues API v3 responses. Values: `completed`, `not_planned`, `reopened`, or `null`. Useful for distinguishing "closed as done" vs "closed as won't fix" — map `not_planned` to `cancelled`.
- **Assignees are multi-value on GitHub** — Issues can have multiple assignees. Map first assignee to `bpkm:assignedTo` (single-value in basic-pkm shape). Log a warning if multiple assignees are present.
- **Fine-grained PATs have repo scope** — Classic PATs need `repo` scope. Fine-grained PATs need repository access + Issues read/write permission. Settings UI should note this.

## Open Risks

- **Cross-repo PR linking requires both repos synced** — If repo-A's PR references repo-B's issue #42, the edge can only be created if both repos are synced. Otherwise the target IRI doesn't exist. Graceful skip with warning log.
- **GitHub milestone mapping creates bpkm:Milestone objects** — These need separate IRIs from tasks. The slug scheme must differentiate: `gh-milestone-{hash}` vs `gh-{hash}`.
- **Push sync for labels** — GitHub's label API requires label to exist on the repo first. Creating labels via API is possible but may surprise users. V1 should push status/title only, not labels.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---|---|---|
| REST pagination (Link header parsing) | `parse_header_links()` from httpx or manual regex | Simple pattern, ~5 lines. No library needed. |
| OAuth code exchange | Direct POST to `github.com/login/oauth/access_token` | GitHub's OAuth is a single POST, no library overhead |
| Markdown body sync | Direct pass-through | GitHub uses Markdown natively, same as SemPKM body content |
| Person matching | `person_matcher.py` from M016 | Identical SPARQL pattern, GitHub provides username + email |

## Sources

- GitHub REST API Issues docs: `GET /repos/{owner}/{repo}/issues`, `PATCH /repos/{owner}/{repo}/issues/{number}`
- GitHub REST API Timeline events: `GET /repos/{owner}/{repo}/issues/{number}/timeline` — `cross-referenced` event type for PR-to-issue links
- GitHub OAuth Web Application Flow: `POST https://github.com/login/oauth/access_token` with code exchange
- M016 Linear Sync implementation (complete reference in `apps/linear-sync/`)
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` — cross-provider bpkm:Task field coverage matrix
