---
id: T01
parent: S05
milestone: M009
provides:
  - CommandClient permission enforcement (command whitelist + IRI prefix scanning)
  - HttpClient domain enforcement (fnmatch glob matching with port stripping)
  - AppContext wiring of manifest permissions to SDK clients
key_files:
  - backend/sdk/sempkm_app_sdk/clients/commands.py
  - backend/sdk/sempkm_app_sdk/clients/http.py
  - backend/sdk/sempkm_app_sdk/context.py
  - backend/sdk/sempkm_app_sdk/runner.py
  - backend/tests/test_app_permissions.py
key_decisions:
  - IRI scanning uses heuristic (starts with urn: or http) rather than full IRI parsing
  - HttpClient with allowed_domains=None is permissive; allowed_domains=[] blocks all
  - Permission checks in _BulkCollector.add() are fail-fast per command
patterns_established:
  - SDK client permission pattern: __init__ accepts whitelist/prefix, execute() checks before dispatch, PermissionError with diagnostic message
  - Recursive IRI scanning in _check_iri_prefix() walks dict/list/tuple structures
observability_surfaces:
  - PermissionError messages include the offending value AND the allowed list/prefix
  - CommandClient._allowed_commands and HttpClient._allowed_domains inspectable
  - AppContext.permissions dict accessible for debugging
duration: ~30m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: SDK permission enforcement in CommandClient and HttpClient

**Added command whitelist, IRI prefix scanning, and network domain restriction enforcement to SDK clients, with manifest permissions wired through AppContext.**

## What Happened

1. Added permission enforcement to `CommandClient` — `allowed_commands` whitelist rejects unpermitted command types; `_check_iri_prefix()` recursively scans all string values in params dict and rejects IRIs not starting with `urn:sempkm:app:{app_id}:`.

2. Added domain enforcement to `HttpClient` — `allowed_domains` parameter accepts glob patterns matched via `fnmatch.fnmatch`. Port numbers stripped before matching. `None` = permissive, `[]` = block all, `["*"]` = allow all.

3. Updated `AppContext` to wire `permissions.commands` → `CommandClient` and `permissions.network` → `HttpClient`.

4. Wrote 26 tests covering whitelist, IRI prefix, domain enforcement, and AppContext wiring.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_app_permissions.py -v` — 26/26 passed

## Diagnostics

- `PermissionError` on command: includes rejected command type and allowed list
- `PermissionError` on IRI: includes offending IRI and required prefix
- `PermissionError` on domain: includes hostname and allowed domain patterns
- Inspect config: `ctx.commands._allowed_commands`, `ctx.http._allowed_domains`

## Files Created/Modified

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — whitelist + IRI prefix scanning
- `backend/sdk/sempkm_app_sdk/clients/http.py` — domain enforcement via fnmatch
- `backend/sdk/sempkm_app_sdk/context.py` — permissions wiring
- `backend/sdk/sempkm_app_sdk/runner.py` — manifest permissions parsing
- `backend/tests/test_app_permissions.py` — 26 tests
