# S02 (Correctness Fixes) — Research

**Date:** 2026-03-12

## Summary

S02 addresses three correctness bugs: unstable validation report IRIs using Python's `hash()` (COR-01), false-positive SPARQL keyword detection in string literals (COR-02), and broken `source_model` attribution when multiple models are installed (COR-03). All three are low-risk, self-contained fixes with no external dependencies. The code paths are well-isolated and the fixes are straightforward.

COR-01 is a one-line change (swap `hash()` for `hashlib.sha256`). COR-02 requires a string-literal-aware regex or a simple preprocessing step to strip quoted strings before keyword detection. COR-03 requires switching from a merged `FROM` query to a per-graph `GRAPH ?g` pattern that captures provenance per spec.

## Recommendation

Fix all three in order of complexity: COR-01 first (trivial), then COR-02 (moderate — needs careful regex), then COR-03 (moderate — SPARQL restructure). No external libraries needed. The existing codebase has patterns for all three fixes. Total estimated effort: ~2 hours.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Stable hashing | `hashlib.sha256` (stdlib) | Already imported in `views/service.py`; deterministic across processes and restarts |

No external libraries needed for any of the three fixes.

## Existing Code and Patterns

- `backend/app/validation/report.py:164-175` — `report_iri` property. Primary path extracts UUID from `urn:sempkm:event:{uuid}` pattern (works correctly). Fallback path at line 175 uses `hash()` — only hit when event IRI doesn't match expected prefix format. Fix: replace `hash()` with `hashlib.sha256().hexdigest()`.

- `backend/app/sparql/client.py:47-98` — `scope_to_current_graph()`. Lines 83-87 check for existing `FROM` and `GRAPH` keywords using `re.search(r'\bFROM\s+', upper)` on the uppercased query string. Bug: this matches `FROM` inside string literals like `FILTER(CONTAINS(?label, "FROM the archive"))`. Same vulnerability in `check_member_query_safety()` at lines 21-43, but that's SEC scope (S01), not COR scope.

- `backend/app/views/service.py:130-191` — `get_all_view_specs()`. Builds FROM clauses for all model views graphs, runs a single merged SPARQL query, then sets `source_model=model_ids[0] if len(model_ids) == 1 else ""` at line 190. Bug: with 2+ models, every spec gets empty `source_model`. Fix: use `GRAPH ?g { ... }` pattern to capture which graph each spec lives in, then reverse-map `urn:sempkm:model:{id}:views` → `{id}`.

- `backend/app/events/query.py:124` — Shows existing `GRAPH ?event { ... }` pattern used elsewhere in the codebase. Same approach should work for view specs.

- `backend/app/views/service.py:51` — `ViewSpec.source_model` field. Used downstream: `source_model == "user"` gates skip deduplication, skip type switcher, and COUNT expression choice. Model IRI strings are used for grouping in the views index page. Empty string falls through to "Other" group.

## Constraints

- **COR-01:** The fallback path is rarely hit in practice (only when `event_iri` doesn't match `urn:sempkm:event:` prefix). But when it is hit, the hash is used to construct a triplestore IRI — must be stable across process restarts and Python versions. `hashlib.sha256` is the obvious choice.

- **COR-02:** A full SPARQL parser (pyparsing-based or rdflib.plugins.sparql) would be correct but is massive overkill for this function. The pragmatic fix is a regex that strips quoted string contents before checking for keywords. SPARQL has four string literal forms: `"..."`, `'...'`, `"""..."""`, `'''...'''`. The function already works on `.upper()` of the query.

- **COR-02:** `check_member_query_safety()` at lines 21-43 has the same vulnerability but is in SEC scope (COR-02 only covers `scope_to_current_graph`). However, since both functions share the same detection logic, the fix should extract a shared helper (e.g. `_has_graph_clause(query)` in the same module) that both can use. This aligns with S01's existing `escape_sparql_regex` in `sparql/utils.py`.

- **COR-03:** The RDF4J triplestore supports `GRAPH ?g { ... }` in SELECT queries. The existing codebase uses this pattern in `events/query.py`, `federation/service.py`, and `sparql/router.py`. The view spec IRI convention is `urn:sempkm:model:{model_id}:views`, so extracting the model ID from the graph IRI is a simple string split.

- **COR-03:** The `source_model` field is compared against `"user"` in multiple places (lines 263, 301, 373, 431 in service.py; lines 220, 312, 428 in router.py). Model specs use the model ID string (e.g. `"schema-org"`). The fix must preserve this contract — `source_model` should be the model ID string, not the full graph IRI.

## Common Pitfalls

- **COR-01: Using `hashlib` without `.hexdigest()`** — The hash object itself is not a string. Must call `.hexdigest()` to get a stable string representation for the IRI.

- **COR-02: Stripping strings too aggressively** — Must handle escaped quotes inside strings (`\"` inside `"..."`, `\'` inside `'...'`). The regex should use a non-greedy match that accounts for escape sequences, or better yet, use a state-machine approach that handles nested quotes properly.

- **COR-02: Forgetting triple-quoted strings** — SPARQL supports `"""..."""` and `'''...'''` multi-line string literals. These must be stripped before single-quoted variants to avoid partial matches.

- **COR-03: Breaking the cache key** — `get_all_view_specs()` uses `cache_key = "all_specs"` with a TTLCache. The fix changes the SPARQL query structure but not the caching logic. No cache key change needed since it's a static key.

- **COR-03: Model ID extraction fragility** — The graph IRI pattern `urn:sempkm:model:{id}:views` is constructed in two places: `models/registry.py:45` and `views/service.py:146`. The extraction logic should use the same prefix constant to avoid drift.

## Open Risks

- **COR-02 edge case: SPARQL comments** — SPARQL supports `#` line comments. A `FROM` keyword in a comment would also false-positive. The current code doesn't handle this, and the roadmap note mentions "string literals or comments" as the scope. The fix should strip comments too (lines starting with `#` after any whitespace).

- **COR-02 scope creep to `check_member_query_safety`** — The same string-literal vulnerability exists in `check_member_query_safety()`. While COR-02 requirement text says "scope_to_current_graph", the shared helper approach means both get fixed. This is fine — it's a natural consequence of extracting the detection logic — but should be tested in S03.

- **COR-03: Untested with zero models** — The `get_all_view_specs()` early return at line 140 handles the no-models case. The GRAPH-based query change shouldn't affect this path, but verify.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| SPARQL | letta-ai/skills@sparql-university | available (35 installs) — not relevant for targeted bug fixes |
| Python/FastAPI | — | none found / not needed |
| hashlib | — | stdlib, no skill needed |

## Sources

- COR-01 bug location: `backend/app/validation/report.py:175` — `hash()` is Python's non-deterministic hash (randomized per-process since Python 3.3 via PYTHONHASHSEED)
- COR-02 bug location: `backend/app/sparql/client.py:83-87` — naive `re.search(r'\bFROM\s+', upper)` without string literal awareness
- COR-03 bug location: `backend/app/views/service.py:190` — `model_ids[0] if len(model_ids) == 1 else ""`
- SPARQL string literal spec: SPARQL 1.1 §19.7 — four string literal forms with optional language tags and datatype IRIs
- Existing GRAPH pattern: `backend/app/events/query.py:124` — `GRAPH ?event { ... }` used throughout codebase
