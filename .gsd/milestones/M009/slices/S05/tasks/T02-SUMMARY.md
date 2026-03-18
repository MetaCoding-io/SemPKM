---
id: T02
parent: S05
milestone: M009
provides:
  - SDK permission enforcement on CommandClient (command whitelist + IRI prefix), GraphClient (sparql_read gate), HttpClient (domain glob matching)
  - AppContext permissions threading from manifest dict to all client constructors
  - Runner reads permissions section from manifest YAML at startup
key_files:
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/sdk/sempkm_app_sdk/clients/graph.py
  - backend/sdk/sempkm_app_sdk/clients/http.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/sdk/sempkm_app_sdk/runner.py
  - backend/tests/test_sdk_permissions.py
key_decisions:
  - IRI prefix check skips object.create since platform assigns the IRI — only object.patch, body.set, body.diff, edge.create, edge.patch have IRI params to validate
  - Used _IRI_PARAMS lookup dict mapping command types to their IRI-carrying param names for extensibility
  - Default permissions are maximally restrictive — empty allowed_commands, sparql_read=False, empty allowed_domains
patterns_established:
  - Permission enforcement is stateless and synchronous — raises PermissionError with self-documenting messages including the offending value and the full allowed list/prefix
  - HttpClient._check_domain uses fnmatch.fnmatch for glob matching — supports *.example.com patterns
observability_surfaces:
  - PermissionError exceptions include the offending value and allowed list/prefix in the message — no runtime logs needed
duration: 20m
verification_result: passed
completed_at: 2026-03-18
blocker_discovered: false
---

# T02: SDK permission enforcement on CommandClient, GraphClient, HttpClient

**Added real permission enforcement to all three SDK clients — command whitelist + IRI prefix on CommandClient, sparql_read gate on GraphClient, fnmatch domain glob on HttpClient — with AppContext threading permissions from manifest and 33 targeted tests.**

## What Happened

Implemented permission enforcement across all SDK clients:

1. **CommandClient** — accepts `allowed_commands: set[str]` and `iri_prefix: str`. `execute()` rejects commands not in the whitelist and validates IRI params against the app prefix. Used a `_IRI_PARAMS` dict mapping each command type to its IRI-carrying params (e.g. edge.create checks `source` and `target`, object.patch checks `iri`). object.create has no IRI params since the platform assigns the IRI.

2. **GraphClient** — accepts `sparql_read: bool` (default False). `query()` raises `PermissionError` if False. Default-deny.

3. **HttpClient** — accepts `allowed_domains: list[str]`. All request methods go through `_check_domain()` which extracts hostname via `urlparse` and matches against patterns using `fnmatch.fnmatch`. Empty list blocks all, `["*"]` allows all.

4. **AppContext** — added `permissions: dict` field. Threads `permissions.commands` to CommandClient, `permissions.sparql_read` to GraphClient, `permissions.network.domains` to HttpClient. Computes `iri_prefix` as `urn:sempkm:app:{app_id}:`.

5. **Runner** — reads `manifest.permissions` section and passes to AppContext constructor.

6. **Tests** — 33 tests covering command whitelist (allow/reject/empty), IRI prefix (all command types), sparql_read gate, domain enforcement (exact/glob/wildcard/empty/multiple), and AppContext permissions threading.

Also updated 2 pre-existing tests in `test_sdk_app.py` that constructed clients without the new permission arguments.

## Verification

- `pytest tests/test_sdk_permissions.py -v` — 33/33 passed
- `pytest tests/ -v` — 1326 passed, 0 failed

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/pytest tests/test_sdk_permissions.py -v` | 0 | ✅ pass | 0.3s |
| 2 | `cd backend && .venv/bin/pytest tests/ -v` | 0 | ✅ pass | 39.7s |

### Slice-Level Verification (partial — T02 of T04)

| # | Command | Exit Code | Verdict | Notes |
|---|---------|-----------|---------|-------|
| 1 | `pytest tests/test_app_scheduler.py -v` | 0 | ✅ pass | T01 tests still pass |
| 2 | `pytest tests/test_sdk_permissions.py -v` | 0 | ✅ pass | This task |
| 3 | `pytest tests/test_bulk_eventstore.py -v` | — | ⏳ pending | T03 |
| 4 | `pytest tests/test_browser_visible.py -v` | — | ⏳ pending | T04 |
| 5 | `pytest tests/ -v` | 0 | ✅ pass | Full suite |

## Diagnostics

- **PermissionError messages** are self-documenting — include the offending value and allowed list/prefix. Example: `"Command type 'edge.create' is not permitted. Allowed: ['body.set', 'object.create']"`
- **No runtime state** — permission enforcement is stateless and synchronous, no DB writes or logs.
- **Inspection method:** Instantiate any client with test permissions and call methods with invalid inputs — PermissionError messages tell you exactly what's wrong.

## Deviations

- Task plan specified checking `subject` and `object` params for edge.create. The actual command schema uses `source` and `target`. Used the real field names from `EdgeCreateParams`.
- Added `body.diff` to the IRI param map — it has the same `iri` field as `body.set` and wasn't mentioned in the plan but exists in the command registry.

## Known Issues

None.

## Files Created/Modified

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — added command whitelist + IRI prefix enforcement
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — added sparql_read gate
- `backend/sdk/sempkm_app_sdk/clients/http.py` — added domain enforcement via fnmatch
- `backend/sdk/sempkm_app_sdk/context.py` — added permissions dict field, threading to all clients
- `backend/sdk/sempkm_app_sdk/runner.py` — reads manifest.permissions, passes to AppContext
- `backend/tests/test_sdk_permissions.py` — new, 33 tests
- `backend/tests/test_sdk_app.py` — updated 2 pre-existing tests to pass new permission args
