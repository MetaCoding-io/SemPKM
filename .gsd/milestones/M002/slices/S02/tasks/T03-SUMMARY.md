---
id: T03
parent: S02
milestone: M002
provides:
  - "Per-spec source_model attribution via GRAPH ?g pattern in get_all_view_specs()"
  - "graph_to_model reverse map from urn:sempkm:model:{id}:views → model ID"
key_files:
  - backend/app/views/service.py
key_decisions:
  - "Used VALUES clause to constrain ?g to known model view graph IRIs — prevents scanning unrelated named graphs while enabling per-spec graph attribution"
patterns_established:
  - "GRAPH ?g + VALUES pattern for multi-graph SPARQL queries that need per-result provenance"
observability_surfaces:
  - "Existing logger.info in get_all_view_specs already logs spec count and model count — unchanged"
duration: 25m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T03: Fix source_model attribution with multiple models via GRAPH pattern

**Replaced FROM-clause merge with GRAPH ?g pattern so each ViewSpec gets the correct source_model from its originating named graph.**

## What Happened

The `get_all_view_specs()` function previously built FROM clauses for all model view graphs, ran a single merged query, then set `source_model=model_ids[0] if len(model_ids) == 1 else ""`. With 2+ models, every spec got empty `source_model`.

Changed to:
1. Build a `graph_to_model` reverse map: `{f"urn:sempkm:model:{mid}:views": mid for mid in model_ids}`
2. Replace FROM clauses with `GRAPH ?g { ... }` pattern, adding `?g` to SELECT
3. Use `VALUES ?g { ... }` clause constraining to known model view graph IRIs
4. In the spec construction loop, extract `g_value` from each binding and look up `source_model` via `graph_to_model.get(g_value, "")`

The single-model case works identically (one VALUES entry, one graph matched). The zero-model early return path is unchanged.

## Verification

- ✅ `grep -n 'GRAPH ?g' backend/app/views/service.py` — shows GRAPH pattern at lines 152, 156
- ✅ `grep -n 'graph_to_model' backend/app/views/service.py` — shows reverse map at lines 142, 147, 150, 194
- ✅ `grep -n 'model_ids\[0\]' backend/app/views/service.py` — no matches (old logic removed)
- ✅ Docker build (`docker compose build api`) — succeeded with exit code 0
- ✅ Cache key `"all_specs"` unchanged (line 121)
- ✅ `source_model="user"` downstream contract preserved (lines 267, 305 — separate creation paths)
- ✅ Zero-model early return path unchanged (line ~140)
- ⏳ E2E tests: ran ~770 tests across chromium/firefox before timeout; all failures observed are pre-existing (batch-commands, webhooks, obsidian-import) — none related to views/service.py

### Slice-level verification (final task — all three COR fixes):
- ✅ COR-01: `report_iri` uses hashlib.sha256 (T01)
- ✅ COR-02: `_strip_sparql_strings()` strips literals/comments before keyword detection (T02)
- ✅ COR-03: GRAPH ?g pattern with reverse map (this task)
- ✅ Docker build succeeds
- ⏳ E2E tests: ran extensively, no new failures; pre-existing failures unrelated to S02 changes

## Diagnostics

Existing `logger.info` in `get_all_view_specs` logs spec count and model count. To inspect: check `source_model` on returned ViewSpec objects — empty string now only occurs for truly unmapped graph IRIs, not as a blanket fallback.

## Deviations

None.

## Known Issues

- E2E test suite takes 20+ minutes and has pre-existing failures in batch-commands, admin-webhooks, and obsidian-import specs — unrelated to this slice's changes.

## Files Created/Modified

- `backend/app/views/service.py` — Replaced FROM-clause merge with GRAPH ?g + VALUES pattern; added graph_to_model reverse map; source_model now set per-spec from graph binding
