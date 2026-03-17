---
estimated_steps: 5
estimated_files: 3
---

# T01: Fix SDK IRI prefix validation to whitelist model and standard namespace IRIs

**Slice:** S01 — Platform fix + Mental Model + App data pipeline
**Milestone:** M010

## Description

The SDK's `CommandClient._check_iri_prefix()` currently rejects ALL `urn:` IRIs that don't start with `urn:sempkm:app:{appId}:`, and ALL `http://`/`https://` IRIs (since they can never match the `urn:` prefix). This makes it impossible for any app to reference model-defined types (e.g., `urn:sempkm:model:rss-feeds:Article`) or standard vocabulary properties (e.g., `http://purl.org/dc/terms/title`) in `object.create` params.

Per decision D171, the fix scopes enforcement to only `urn:sempkm:app:*` and `urn:sempkm:data:*` namespaces — where the app is creating NEW IRIs. Model IRIs, standard vocabularies, and user-types pass through unchecked.

## Steps

1. Open `backend/sdk/sempkm_app_sdk/clients/commands.py` and read the current `_check_iri_prefix()` method (lines ~123-145). Note how it currently treats any string starting with `urn:`, `http://`, or `https://` as an IRI and requires it to start with the app's prefix.

2. Rewrite `_check_iri_prefix()` with the new logic:
   - If the string starts with `urn:sempkm:model:` → PASS (model namespace)
   - If the string starts with `urn:sempkm:user-types:` → PASS (user-created types)
   - If the string starts with `http://` or `https://` → PASS (standard vocabularies like dcterms, rdfs, schema.org)
   - If the string starts with `urn:sempkm:app:{app_id}:` → PASS (own app namespace)
   - If the string starts with `urn:sempkm:app:` or `urn:sempkm:data:` → FAIL (foreign app or data namespace)
   - If the string starts with `urn:` but none of the above → PASS (e.g., `urn:uuid:*` or other URN namespaces)
   - Non-IRI strings → skip (unchanged behavior)

3. Update the docstring to document the new enforcement scope.

4. Create `backend/tests/test_iri_prefix_fix.py` with these test cases:
   - `test_model_type_iri_passes` — `urn:sempkm:model:rss-feeds:Article` accepted
   - `test_standard_http_vocab_passes` — `http://purl.org/dc/terms/title` accepted
   - `test_standard_https_vocab_passes` — `https://schema.org/name` accepted
   - `test_user_types_iri_passes` — `urn:sempkm:user-types:CustomClass` accepted
   - `test_own_app_iri_passes` — `urn:sempkm:app:test-app:item1` accepted
   - `test_foreign_app_iri_blocked` — `urn:sempkm:app:other-app:thing` raises PermissionError
   - `test_data_namespace_iri_blocked` — `urn:sempkm:data:other:thing` raises PermissionError
   - `test_nested_model_iri_in_params_passes` — model IRI nested inside dict/list params
   - `test_mixed_valid_and_invalid_iri_fails` — params with both model IRI and foreign app IRI
   - `test_non_iri_strings_ignored` — plain text strings not treated as IRIs
   - `test_rdf_type_reference_pattern` — typical `object.create` with `type: "urn:sempkm:model:rss-feeds:Article"` and `iri: "urn:sempkm:app:rss-reader:article-123"` passes

5. Run both the new tests and the existing `test_app_permissions.py` to ensure no regression:
   ```bash
   cd backend && python -m pytest tests/test_iri_prefix_fix.py tests/test_app_permissions.py -v
   ```

## Must-Haves

- [ ] `_check_iri_prefix()` accepts `urn:sempkm:model:rss-feeds:Article` for any app
- [ ] `_check_iri_prefix()` accepts `http://purl.org/dc/terms/title` for any app
- [ ] `_check_iri_prefix()` accepts `https://schema.org/name` for any app
- [ ] `_check_iri_prefix()` accepts `urn:sempkm:user-types:CustomClass` for any app
- [ ] `_check_iri_prefix()` still rejects `urn:sempkm:app:other-app:thing` for app `test-app`
- [ ] `_check_iri_prefix()` rejects `urn:sempkm:data:foreign:thing` for app `test-app`
- [ ] All existing `test_app_permissions.py` tests still pass

## Verification

- `cd backend && python -m pytest tests/test_iri_prefix_fix.py -v` — all ≥10 tests pass
- `cd backend && python -m pytest tests/test_app_permissions.py -v` — no regressions (existing 33 tests pass)
- Manual check: inspect the changed method and confirm only `urn:sempkm:app:*` and `urn:sempkm:data:*` are enforced

## Inputs

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — current `_check_iri_prefix()` implementation to modify
- `backend/tests/test_app_permissions.py` — existing permission tests (reference patterns for test structure)
- Decision D171 in DECISIONS.md — specifies the exact enforcement scope

## Expected Output

- `backend/sdk/sempkm_app_sdk/clients/commands.py` — updated `_check_iri_prefix()` with whitelist logic
- `backend/tests/test_iri_prefix_fix.py` — new test file with ≥10 passing tests

## Observability Impact

- **PermissionError messages**: When `_check_iri_prefix()` rejects an IRI, the error message includes both the offending IRI and the app's required prefix — unchanged by this fix.
- **What passes now**: Model IRIs (`urn:sempkm:model:*`), standard vocabularies (`http://`, `https://`), and user-types (`urn:sempkm:user-types:*`) no longer trigger PermissionError. Agents inspecting error logs should only see IRI prefix rejections for `urn:sempkm:app:{foreign-app}:*` and `urn:sempkm:data:*` namespaces.
- **How to inspect**: Run any app's `object.create` command with model-type IRIs — should succeed. Try with a foreign app IRI — should raise PermissionError with the offending IRI in the message.
- **Failure state visible**: PermissionError traceback in app task logs (Admin > Applications > {app} > Task History) when an app references a foreign app's namespace.
