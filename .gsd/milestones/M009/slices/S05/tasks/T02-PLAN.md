---
estimated_steps: 6
estimated_files: 7
---

# T02: SDK permission enforcement on CommandClient, GraphClient, HttpClient

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

Add real permission enforcement to SDK clients. `CommandClient` enforces command type whitelist and IRI prefix on all created IRIs. `GraphClient` gates on `sparql_read` permission. `HttpClient` enforces network domain restriction via `fnmatch` glob matching. `AppContext` threads manifest permissions through to all client constructors. Runner reads permissions from manifest at startup.

## Steps

1. Modify `CommandClient.__init__` to accept `allowed_commands: set[str]` and `iri_prefix: str`. In `execute()`, raise `PermissionError` if command type not in whitelist. Validate all IRI params (check `iri` for object.create/object.patch/body.set, `subject` and `object` for edge.create/edge.patch) — reject if not matching `urn:sempkm:app:{appId}:`.
2. Modify `GraphClient.__init__` to accept `sparql_read: bool`. In `query()`, raise `PermissionError` if False.
3. Modify `HttpClient.__init__` to accept `allowed_domains: list[str]`. In `request()` / `get()` / `post()`, extract hostname from URL via `urllib.parse.urlparse`, validate against domain list using `fnmatch.fnmatch`. Empty list = all blocked. `["*"]` = unrestricted. Raise `PermissionError` on rejection.
4. Modify `AppContext.__init__` to accept `permissions: dict` extracted from manifest. Thread `commands` list → CommandClient.allowed_commands, `iri_prefix` computed from app_id → CommandClient.iri_prefix, `sparql_read` bool → GraphClient, `network.domains` → HttpClient.
5. Modify `runner.py` to read manifest YAML, extract permissions section, compute iri_prefix as `urn:sempkm:app:{app_id}:`, pass to AppContext constructor.
6. Write `test_sdk_permissions.py` — test each enforcement layer: command whitelist allow/reject, IRI prefix allow/reject (all command types), sparql_read gate, domain glob allow/reject, wildcard domain, empty domain list, StateClient graph scoping verification.

## Must-Haves

- [ ] CommandClient rejects unpermitted command types with PermissionError
- [ ] CommandClient rejects IRIs outside app prefix for all command param types
- [ ] GraphClient rejects queries when sparql_read=False
- [ ] HttpClient rejects requests to non-permitted domains
- [ ] HttpClient allows wildcard pattern `["*"]`
- [ ] StateClient verified scoped to app state graph

## Verification

- `cd backend && .venv/bin/pytest tests/test_sdk_permissions.py -v` — all pass
- `cd backend && .venv/bin/pytest tests/ -v` — full suite, zero regressions

## Inputs

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — existing stub from S02
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — existing stub from S02
- `backend/sdk/sempkm_app_sdk/clients/http.py` — existing stub from S02
- `backend/sdk/sempkm_app_sdk/context.py` — existing AppContext from S02
- `backend/sdk/sempkm_app_sdk/runner.py` — existing runner from S02

## Observability Impact

- **Failure signals:** `PermissionError` exceptions raised by SDK clients include the offending value and the full allowed list/prefix in the error message. No runtime logs — these are client-side guards that fail fast with diagnosable messages.
- **Inspection:** Future agents can verify enforcement by instantiating clients with test permissions and calling methods with invalid inputs — PermissionError messages are self-documenting.
- **No new runtime state:** Permission enforcement is stateless and synchronous. No DB writes, no background processes, no log streams.

## Expected Output

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — modified, permission enforcement
- `backend/sdk/sempkm_app_sdk/clients/graph.py` — modified, sparql gate
- `backend/sdk/sempkm_app_sdk/clients/http.py` — modified, domain enforcement
- `backend/sdk/sempkm_app_sdk/context.py` — modified, permissions threading
- `backend/sdk/sempkm_app_sdk/runner.py` — modified, manifest permissions reading
- `backend/tests/test_sdk_permissions.py` — new, ~12-15 tests
