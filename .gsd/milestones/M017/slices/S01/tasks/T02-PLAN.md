---
estimated_steps: 5
estimated_files: 6
---

# T02: PAT auth + field mapper + person matcher

**Slice:** S01 — GitHub Client + PAT Auth + Issue Pull Sync
**Milestone:** M017

## Description

Implement the three pure-ish service modules that sit between the REST client and the sync engine: auth (PAT storage/verification), field mapper (GitHub JSON → bpkm:Task properties), and person matcher (GitHub username → SemPKM Person IRI). All three are side-effect-free at their core (field mapper is fully pure; auth and person matcher interact with StateClient/GraphClient but are easily mocked).

Reference implementations: `apps/linear-sync/services/auth.py` (200 lines), `apps/linear-sync/services/field_mapper.py` (358 lines), `apps/linear-sync/services/person_matcher.py` (139 lines).

## Steps

1. **Write `apps/github-sync/services/auth.py`:**
   - Read `apps/linear-sync/services/auth.py` for structure reference
   - `async def store_pat(state_client, pat: str)` — stores under key `github_pat`
   - `async def get_pat(state_client) -> str | None` — reads from StateClient
   - `async def verify_pat(github_client) -> dict` — calls `github_client.verify_token()`, returns user dict (login, name, email)
   - `async def get_connection_status(state_client, github_client) -> dict` — returns `{"connected": bool, "username": str|None, "pat_preview": str|None}`. PAT preview: show first 4 chars + `****` + last 4 chars (e.g., `ghp_****ab12`). If PAT exists but verify fails, return `{"connected": False, "error": str}`.
   - `async def disconnect(state_client)` — removes `github_pat` key
   - Logger: `github_sync.auth`

2. **Write `apps/github-sync/services/field_mapper.py`:**
   - Read `apps/linear-sync/services/field_mapper.py` for structure reference
   - Constants:
     - `BPKM = "urn:sempkm:model:basic-pkm:"`
     - `STATUS_MAP = {"open": "todo", "closed": "done"}` (two-state model — simpler than Linear's 5)
     - `STATE_REASON_MAP = {"completed": "done", "not_planned": "cancelled", "reopened": "todo"}` — refines closed status using `state_reason` when available
     - `REVERSE_STATUS_MAP = {"todo": "open", "in-progress": "open", "done": "closed", "cancelled": "closed", "blocked": "open"}` — for push sync (S03 will use)
   - `def compute_issue_slug(repo_full_name: str, issue_number: int) -> str` — `hashlib.sha256(f"{repo_full_name}#{issue_number}".encode()).hexdigest()[:16]` — produces `gh-{hash16}` slug
   - `def build_task_properties(issue: dict, repo_full_name: str, person_iri: str | None = None) -> dict` — returns dict of `{predicate_iri: value}`:
     - `dcterms:title` ← `issue["title"]`
     - `BPKM + "taskStatus"` ← `STATUS_MAP[issue["state"]]`, refined by `STATE_REASON_MAP[issue.get("state_reason")]` if present
     - `BPKM + "tags"` ← `[label["name"] for label in issue.get("labels", [])]`
     - `BPKM + "assignedTo"` ← `person_iri` (if provided, from first assignee)
     - `BPKM + "taskProject"` ← `issue["milestone"]["title"]` if milestone exists
     - `BPKM + "externalId"` ← `f"#{issue['number']}"`
     - `BPKM + "externalUrl"` ← `issue["html_url"]`
     - `BPKM + "externalUuid"` ← `issue["node_id"]`
     - `BPKM + "externalProvider"` ← `"github"` (S02 will use `"github-pr"` for PRs)
     - `BPKM + "dueDate"` ← `issue["milestone"]["due_on"][:10]` if milestone has due_on
   - `def is_pull_request(issue: dict) -> bool` — returns `"pull_request" in issue`
   - `def get_assignee_info(issue: dict) -> dict | None` — returns `{"login": str, "email": str|None}` from first assignee, or None
   - `def build_issue_patch(task_props: dict) -> dict` — reverse mapping for push sync (S03). Maps bpkm properties back to GitHub PATCH body: `{"title": ..., "state": ..., "labels": ...}`. Include the function now so S03 doesn't need to modify field_mapper.

3. **Write `apps/github-sync/services/person_matcher.py`:**
   - Read `apps/linear-sync/services/person_matcher.py` (139 lines) — near-verbatim copy
   - `PersonMatcher.__init__(self, graph_client, command_client)` with in-memory LRU cache
   - `async def match(self, assignee_info: dict) -> str | None` — SPARQL lookup by email (`foaf:mbox`) or GitHub login as fallback. On miss, creates Person via `object.create` command with email-derived slug and title from login. Caches result.
   - Adapt login field: Linear uses `user.email` primarily; GitHub uses `login` (username) primarily and `email` may be null if user has private email. PersonMatcher should try email first (if available), then fall back to matching by login stored as `BPKM + "externalId"`.
   - Logger: `github_sync.person`

4. **Write `backend/tests/test_github_field_mapper.py` (~35 tests):**
   - Load via importlib from `apps/github-sync/services/field_mapper.py`
   - Test groups:
     - **compute_issue_slug** (~4 tests): deterministic, different repos yield different slugs, different numbers yield different slugs, format is 16 hex chars
     - **build_task_properties** (~15 tests): basic issue with all fields, issue missing optional fields (no labels, no assignee, no milestone), open→todo, closed→done, closed+not_planned→cancelled, closed+completed→done, reopened→todo, labels mapped as tags, first assignee IRI passed through, milestone title mapped, externalId format "#N", externalUrl, externalUuid, externalProvider "github", dueDate from milestone
     - **is_pull_request** (~3 tests): issue without PR key returns False, issue with PR key returns True, PR-as-issue (GitHub returns both)
     - **get_assignee_info** (~4 tests): no assignees, one assignee with email, one assignee without email (null), multiple assignees (takes first)
     - **build_issue_patch** (~6 tests): title mapping, status todo→open, status done→closed, status cancelled→closed, labels reverse mapping, empty properties
     - **STATUS_MAP / REVERSE_STATUS_MAP** (~3 tests): all entries covered, round-trip consistency where applicable

5. **Write `backend/tests/test_github_auth.py` (~12 tests) and `backend/tests/test_github_person_matcher.py` (~10 tests):**
   - Load via importlib
   - **Auth tests:** store_pat writes to state, get_pat reads from state, verify_pat success returns user dict, verify_pat failure raises error, get_connection_status connected, get_connection_status disconnected, get_connection_status error, pat_preview masking (various PAT formats), disconnect clears key, missing pat returns None, empty pat handling
   - **Person matcher tests:** match by email found, match by login found, match miss creates person, cache hit skips SPARQL, email preferred over login, null email falls back to login, empty assignee returns None, cache LRU behavior, created person has correct properties, SPARQL query structure

## Must-Haves

- [ ] `build_task_properties()` maps all 11 fields from research doc field mapping table
- [ ] `compute_issue_slug()` produces deterministic 16-char hex slugs
- [ ] `is_pull_request()` correctly detects PRs from `pull_request` key
- [ ] `build_issue_patch()` reverse maps status/title/labels for push sync
- [ ] PAT storage/retrieval/verification via StateClient
- [ ] `get_connection_status()` returns masked PAT preview, never raw token
- [ ] PersonMatcher handles email-first lookup with login fallback
- [ ] ~55+ tests across three test files

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_github_field_mapper.py tests/test_github_auth.py tests/test_github_person_matcher.py -v` — all pass
- Confirm test count ≥55 with `pytest --co -q | tail -1`

## Inputs

- `apps/github-sync/services/github_client.py` — from T01, provides `GitHubClient`, `GitHubAuthError`
- `apps/linear-sync/services/auth.py` — reference auth implementation
- `apps/linear-sync/services/field_mapper.py` — reference field mapper
- `apps/linear-sync/services/person_matcher.py` — reference person matcher (near-verbatim copy)
- `.gsd/milestones/M017/M017-RESEARCH.md` — GitHub → bpkm:Task field mapping table, IRI minting scheme

## Expected Output

- `apps/github-sync/services/auth.py` — PAT auth functions (~150 lines)
- `apps/github-sync/services/field_mapper.py` — pure field mapping functions (~250 lines)
- `apps/github-sync/services/person_matcher.py` — person matching with SPARQL + cache (~140 lines)
- `backend/tests/test_github_field_mapper.py` — ~35 tests
- `backend/tests/test_github_auth.py` — ~12 tests
- `backend/tests/test_github_person_matcher.py` — ~10 tests
