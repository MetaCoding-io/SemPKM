---
estimated_steps: 6
estimated_files: 5
---

# T01: SDK permission enforcement in CommandClient and HttpClient

**Slice:** S05 — Scheduler, Permissions, Bulk EventStore & browserVisible
**Milestone:** M009

## Description

The SDK client stubs (`CommandClient`, `HttpClient`) were built in S02 as thin HTTP wrappers with permission enforcement explicitly deferred to S05. This task adds real enforcement: command whitelist checking, IRI prefix validation (recursive), and network domain restriction via glob matching.

The enforcement is client-side in the SDK (D157) — the platform API doesn't re-validate per-request. This is pragmatic for a personal tool with locally-installed apps.

Key constraints from research:
- IRI prefix enforcement must scan all string values in params dict recursively, not just the top-level `iri` key (nested properties like `dcterms:references` can contain IRIs)
- Network glob matching must strip port from hostname before matching (`api.hypothes.is:443` → `api.hypothes.is`)
- Empty `allowed_commands` = no commands allowed; `["*"]` in network = all domains allowed

## Steps

1. **Modify `CommandClient`** (`backend/sdk/sempkm_app_sdk/clients/commands.py`):
   - Add `allowed_commands: list[str]` and `app_id: str` to `__init__()` alongside existing `client` param
   - In `execute()`, before the HTTP call: check `command_type in allowed_commands`, raise `PermissionError(f"Command '{command_type}' not in allowed commands: {allowed_commands}")` if not
   - Add private `_check_iri_prefix(params: dict)` method that recursively walks all values in a dict/list structure. For any string value that looks like an IRI (starts with `urn:` or `http://` or `https://`), check it starts with `urn:sempkm:app:{self._app_id}:`. Raise `PermissionError` with the offending IRI if not. Call this from `execute()` on the params dict.

2. **Modify `HttpClient`** (`backend/sdk/sempkm_app_sdk/clients/http.py`):
   - Add `allowed_domains: list[str]` to `__init__()`
   - Add private `_check_domain(url: str)` method: parse URL with `urllib.parse.urlparse()`, extract hostname (strip port), match against each glob in `allowed_domains` using `fnmatch.fnmatch`. If no glob matches, raise `PermissionError(f"Domain '{hostname}' not in allowed domains: {allowed_domains}")`
   - Call `_check_domain()` at the start of `get()` and `post()`
   - Empty `allowed_domains` list means block all external HTTP

3. **Update `AppContext`** (`backend/sdk/sempkm_app_sdk/context.py`):
   - Add `permissions: dict | None = None` field to the dataclass (dict with keys `commands`, `network`, etc. matching manifest structure)
   - In the `commands` property, pass `allowed_commands=self.permissions.get("commands", [])` and `app_id=self.app_id` to `CommandClient()`
   - In the `http` property, pass `allowed_domains=self.permissions.get("network", [])` to `HttpClient()`

4. **Update SDK runner** (`backend/sdk/sempkm_app_sdk/runner.py`):
   - After loading the manifest YAML, extract `manifest.get("permissions", {})` and pass it as the `permissions` kwarg to `AppContext()`

5. **Write tests** (`backend/tests/test_app_permissions.py`):
   - Test CommandClient: allowed command succeeds (mock HTTP), disallowed command raises PermissionError, empty allowed list blocks all
   - Test IRI prefix: valid `urn:sempkm:app:test-app:xxx` passes, invalid `urn:sempkm:other:xxx` fails, nested params scanned recursively, non-IRI strings ignored
   - Test HttpClient: matching domain allowed, non-matching domain raises PermissionError, wildcard `*` allows all, `*.hypothes.is` matches `api.hypothes.is`, port stripping works (`api.hypothes.is:443`), empty allowed_domains blocks all
   - Test AppContext: permissions dict propagated to client constructors
   - Ensure SDK package is importable in tests (add `sys.path.insert` like `test_sdk_app.py` does)

6. **Verify** existing SDK tests still pass: `cd backend && python -m pytest tests/test_sdk_app.py tests/test_app_permissions.py -v`

## Must-Haves

- [ ] `CommandClient.execute()` raises `PermissionError` for commands not in whitelist
- [ ] IRI prefix enforcement scans params dict recursively (not just top-level)
- [ ] `HttpClient.get()`/`post()` raises `PermissionError` for unapproved domains
- [ ] Port is stripped from hostname before glob matching
- [ ] `AppContext` passes permissions to clients from manifest data
- [ ] SDK runner reads `manifest.permissions` and passes to AppContext
- [ ] Existing `test_sdk_app.py` tests still pass (backward compat)

## Verification

- `cd backend && python -m pytest tests/test_app_permissions.py -v` — all pass
- `cd backend && python -m pytest tests/test_sdk_app.py -v` — no regressions
- PermissionError messages include the offending value and the allowed list

## Inputs

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — current thin HTTP wrapper (32 lines), needs allowed_commands + IRI enforcement
- `backend/sdk/sempkm_app_sdk/clients/http.py` — current thin wrapper (36 lines), needs allowed_domains enforcement
- `backend/sdk/sempkm_app_sdk/context.py` — current AppContext dataclass (130 lines), needs permissions field
- `backend/sdk/sempkm_app_sdk/runner.py` — current runner (134 lines), reads manifest YAML, needs to extract permissions
- `backend/tests/test_sdk_app.py` — existing SDK tests, reference for test structure and SDK import path setup

## Expected Output

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — CommandClient with whitelist + IRI prefix enforcement
- `backend/sdk/sempkm_app_sdk/clients/http.py` — HttpClient with domain restriction via glob matching
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext with permissions field wired to clients
- `backend/sdk/sempkm_app_sdk/runner.py` — Runner passes manifest permissions to AppContext
- `backend/tests/test_app_permissions.py` — ~15-20 tests covering all enforcement paths
