# S02: Correctness Fixes

**Goal:** Fix three correctness bugs: unstable validation report IRIs (COR-01), false-positive SPARQL keyword detection in string literals (COR-02), and broken `source_model` attribution with multiple models (COR-03).
**Demo:** Validation report IRI is deterministic across process restarts; `scope_to_current_graph()` correctly injects FROM clauses even when query strings contain "FROM" or "GRAPH" inside literals; `get_all_view_specs()` returns the correct `source_model` for each spec when multiple models are installed.

## Must-Haves

- COR-01: `validation/report.py` uses `hashlib.sha256` instead of `hash()` for fallback IRI
- COR-02: `scope_to_current_graph()` and `check_member_query_safety()` strip string literals and comments before keyword detection
- COR-03: `get_all_view_specs()` uses `GRAPH ?g { ... }` pattern and maps each spec to its source model ID

## Proof Level

- This slice proves: contract (unit-level correctness of three isolated functions)
- Real runtime required: no (all three fixes are verifiable with unit-style assertions; S03 adds formal pytest coverage)
- Human/UAT required: no

## Verification

All three fixes are self-contained pure functions or query builders. Verification uses a quick Python script that exercises each fix in isolation:

- `python -c` inline assertions for COR-01: call `report_iri` with a non-standard event IRI twice in same process, confirm identical results; confirm the IRI uses a hex digest pattern
- `python -c` inline assertions for COR-02: call `_strip_sparql_strings(query)` on queries with "FROM" and "GRAPH" inside string literals and comments, confirm keywords are removed from the stripped version; call `scope_to_current_graph()` on such queries and confirm FROM clause is injected
- `python -c` inline assertions for COR-03: confirm the new SPARQL query in `get_all_view_specs` uses `GRAPH ?g` pattern (structural check; full integration tested in S03)
- Docker build succeeds: `docker compose build backend`
- Existing E2E tests still pass (run after all three fixes)

## Observability / Diagnostics

- Runtime signals: existing `logger.info` in `get_all_view_specs` already logs spec count and model count — no new signals needed
- Inspection surfaces: none new — all three are pure function fixes
- Failure visibility: COR-01 failure would produce non-deterministic IRIs (detectable by comparing outputs); COR-02 failure would skip FROM injection (detectable by checking returned query); COR-03 failure would produce empty `source_model` (detectable by checking ViewSpec objects)
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `backend/app/sparql/utils.py` (created in S01 — `escape_sparql_regex`; the new `_strip_sparql_strings` helper lives in `client.py` alongside the functions that use it)
- New wiring introduced in this slice: none (fixes are in-place changes to existing functions)
- What remains before the milestone is truly usable end-to-end: S03 adds formal pytest unit tests for these fixes; S04–S07 address other milestone requirements

## Tasks

- [x] **T01: Stabilize validation report IRI with hashlib** `est:15m`
  - Why: COR-01 — `hash()` is randomized per-process since Python 3.3; fallback validation report IRIs become unreachable across restarts
  - Files: `backend/app/validation/report.py`
  - Do: Import `hashlib`, replace `hash(self.event_iri)` with `hashlib.sha256(self.event_iri.encode()).hexdigest()` at line 175
  - Verify: `python -c "from app.validation.report import ValidationReport; ..."` — two calls with identical non-standard event IRI produce identical report IRIs; IRI contains hex characters only
  - Done when: `report_iri` property returns a stable, deterministic IRI for any `event_iri` input, including the fallback path

- [x] **T02: Make SPARQL keyword detection ignore string literals and comments** `est:45m`
  - Why: COR-02 — `scope_to_current_graph()` and `check_member_query_safety()` falsely detect FROM/GRAPH keywords inside SPARQL string literals, causing incorrect scoping/rejection
  - Files: `backend/app/sparql/client.py`
  - Do: Add `_strip_sparql_strings()` helper that removes SPARQL string literal contents (triple-quoted first, then single-quoted, handling escaped quotes) and `#`-comments before keyword detection. Use it in both `scope_to_current_graph()` and `check_member_query_safety()` before their `re.search` calls.
  - Verify: Inline Python assertions confirming: (1) query with `FILTER(CONTAINS(?label, "FROM the archive"))` gets FROM injected, (2) query with `'GRAPH data'` in a literal gets FROM injected, (3) query with `# FROM comment` gets FROM injected, (4) query with real `FROM <...>` is left unchanged, (5) `check_member_query_safety` does not reject queries with FROM/GRAPH only inside literals
  - Done when: Both functions correctly distinguish real SPARQL clauses from keywords inside string literals and comments

- [x] **T03: Fix source_model attribution with multiple models via GRAPH pattern** `est:45m`
  - Why: COR-03 — `get_all_view_specs()` sets `source_model=""` when >1 model is installed, losing view provenance for type-switching, deduplication, and grouping
  - Files: `backend/app/views/service.py`
  - Do: Replace merged FROM-clause query with `GRAPH ?g { ... }` pattern that captures which graph each spec lives in. Build a reverse map from `urn:sempkm:model:{id}:views` → `{id}`. Set each spec's `source_model` by looking up the `?g` binding in the reverse map.
  - Verify: Structural check that the generated SPARQL uses `GRAPH ?g`; verify reverse map logic extracts model ID correctly from graph IRI pattern
  - Done when: Each `ViewSpec` has `source_model` set to the correct model ID string regardless of how many models are installed; Docker build succeeds; existing E2E tests pass

## Files Likely Touched

- `backend/app/validation/report.py`
- `backend/app/sparql/client.py`
- `backend/app/views/service.py`
