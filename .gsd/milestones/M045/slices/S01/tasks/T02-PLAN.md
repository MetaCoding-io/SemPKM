---
estimated_steps: 8
estimated_files: 5
skills_used: []
---

# T02: Federation SHA-256 integrity hash and namespace-filtered import

Add content integrity verification (SHA-256 hash) to federation patch exports and imports per D372 backward-compat strategy. Add namespace filtering to reject system-managed predicates in incoming federation triples per F-037. Write unit tests.

Steps:
1. In `backend/app/federation/schemas.py`, add optional `content_hash: str | None = None` field to `PatchExportResponse`.
2. In `backend/app/federation/router.py` `export_patches()`, compute SHA-256 of `patch_text` and include it as `content_hash` in the response.
3. In `backend/app/federation/service.py` `sync_shared_graph()`, after receiving the remote response, check for `content_hash` field. If present, compute SHA-256 of received `patch_text` and compare. If mismatch, add error to SyncResult and return without applying. If absent, log WARNING about missing integrity verification.
4. Create `backend/app/federation/namespace_filter.py` with `filter_federation_triples(triples: list[tuple]) -> tuple[list[tuple], list[tuple]]` that splits triples into (allowed, rejected). Reject triples where any of s/p/o starts with system namespaces: `urn:sempkm:` (except `urn:sempkm:shared:` which is the federation graph itself), any predicate in `http://www.w3.org/2002/07/owl#`, `http://www.w3.org/ns/shacl#`, `http://www.w3.org/1999/02/22-rdf-syntax-ns#type` when the object is an OWL/SHACL class.
5. In `backend/app/federation/service.py` `sync_shared_graph()`, after deserializing the patch and before building Operations, call `filter_federation_triples()` on the inserts list. Log the count of rejected triples at WARNING if any. Use only the allowed triples for the Operation.
6. Write `backend/tests/test_federation_integrity.py` with tests: (a) export includes content_hash, (b) import with correct hash passes, (c) import with wrong hash fails, (d) import with missing hash logs warning but proceeds, (e) namespace filter rejects sempkm: predicates, (f) namespace filter rejects owl:Class triples, (g) namespace filter rejects sh: predicates, (h) namespace filter allows normal data triples, (i) namespace filter allows urn:sempkm:shared: graph IRIs in subjects.

## Inputs

- ``backend/app/federation/schemas.py` — PatchExportResponse to extend`
- ``backend/app/federation/router.py` — export_patches() to add hash computation`
- ``backend/app/federation/service.py` — sync_shared_graph() to add hash verification and namespace filtering`
- ``backend/app/federation/patch.py` — serialize_patch/deserialize_patch for understanding patch format`

## Expected Output

- ``backend/app/federation/schemas.py` — content_hash field added to PatchExportResponse`
- ``backend/app/federation/router.py` — SHA-256 hash computed and included in export`
- ``backend/app/federation/service.py` — hash verification and namespace filtering on import`
- ``backend/app/federation/namespace_filter.py` — namespace filtering utility`
- ``backend/tests/test_federation_integrity.py` — unit tests for integrity and filtering`

## Verification

cd backend && .venv/bin/python -m pytest tests/test_federation_integrity.py -v
