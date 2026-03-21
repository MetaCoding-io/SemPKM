---
id: T01
parent: S05
milestone: M031
provides:
  - Narrowed _VOCAB_PREFIXES to specific internal namespaces so urn:sempkm:model:* IRIs get enriched
  - Dynamic prefix shortening via prefixCache/reversePrefixMap in shortenUri()
  - Vocab pill fallback for ontology IRIs via vocabIriIndex lookup in renderCell()
  - CSS styles for .sparql-vocab-pill (dashed-border italic pill for vocabulary terms)
key_files:
  - backend/app/sparql/router.py
  - frontend/static/js/sparql-console.js
  - frontend/static/css/workspace.css
key_decisions:
  - Used explicit allow-list of internal urn:sempkm: sub-namespaces instead of a broad exclusion, so new model ontology IRIs automatically get pills
  - Built reversePrefixMap as a derived cache rebuilt on vocabulary fetch, rather than computing it on every shortenUri() call
  - Vocab pills use dashed border + italic label to visually distinguish from enriched data-object pills
patterns_established:
  - vocabIriIndex and reversePrefixMap are rebuilt in fetchVocabulary() whenever prefixCache/vocabCache change — any new cache consumers should follow this pattern
observability_surfaces:
  - Browser console: vocabIriIndex and reversePrefixMap are module-level vars inspectable in devtools
  - console.warn on vocabulary fetch failure in fetchVocabulary()
  - DOM inspection: .sparql-vocab-pill class on ontology IRI pills; .sparql-iri-pill on enriched data pills
duration: 20m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Fix SPARQL prefix shortening and IRI pill fallthrough

**Replace broad urn:sempkm: vocab prefix exclusion with specific internal namespaces, add dynamic prefix shortening from prefixCache, and render vocab pills for model ontology IRIs**

## What Happened

The `_VOCAB_PREFIXES` tuple in `backend/app/sparql/router.py` contained a single broad `"urn:sempkm:"` entry that caused ALL `urn:sempkm:model:*` IRIs (model ontology classes and properties) to be excluded from enrichment in `_is_object_iri()`. This was replaced with ~28 specific internal sub-namespace entries (e.g., `urn:sempkm:query:`, `urn:sempkm:user:`, `urn:sempkm:workflow:`) while intentionally excluding `urn:sempkm:model:` so those IRIs can get enriched.

The matching JS `KNOWN_VOCAB_PREFIXES` array in `sparql-console.js` was updated to mirror the backend list.

`shortenUri()` now checks a dynamically-built `reversePrefixMap` (namespace→prefix, derived from `prefixCache`) after the hardcoded well-known prefix map, so model ontology IRIs like `urn:sempkm:model:basic-pkm:Person` can be shortened to QNames like `pkm:Person`.

`renderCell()` now has a vocab pill fallback path: after the enrichment check, it looks up the URI in `vocabIriIndex` (an IRI→item map built from `vocabCache`). If found, it renders a styled `.sparql-vocab-pill` with the item's QName and a badge-derived icon (box for classes, arrow-right for properties, type for datatype properties).

New CSS for `.sparql-vocab-pill` uses a dashed border and italic label to visually distinguish vocabulary term pills from enriched data-object pills.

## Verification

All five task-level verification checks pass:
1. Python syntax check on `backend/app/sparql/router.py` — OK
2. No broad `"urn:sempkm:"` in `_VOCAB_PREFIXES` — only specific sub-namespaces
3. `shortenUri()` uses `reversePrefixMap` (derived from `prefixCache`)
4. `renderCell()` renders `.sparql-vocab-pill` elements
5. `.sparql-vocab-pill` CSS exists in workspace.css

Slice-level checks relevant to T01 also pass:
- Backend syntax OK (router.py, service.py, admin router.py)
- `grep -c "urn:sempkm:" backend/app/sparql/router.py` = 39 (all specific entries, no broad match)
- `grep -q "sparql-vocab-pill" frontend/static/css/workspace.css` — PASS

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` | 0 | ✅ pass | <1s |
| 2 | `grep '"urn:sempkm:"' backend/app/sparql/router.py` (only comment, no tuple entry) | 0 | ✅ pass | <1s |
| 3 | `grep "prefixCache\|reversePrefixMap" sparql-console.js \| grep -i "shorten\|reverse"` | 0 | ✅ pass | <1s |
| 4 | `grep "sparql-vocab-pill" frontend/static/js/sparql-console.js` | 0 | ✅ pass | <1s |
| 5 | `grep "sparql-vocab-pill" frontend/static/css/workspace.css` | 0 | ✅ pass | <1s |
| 6 | `python3 -c "import ast; ast.parse(open('backend/app/ontology/service.py').read())"` | 0 | ✅ pass | <1s |
| 7 | `python3 -c "import ast; ast.parse(open('backend/app/admin/router.py').read())"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Inspect vocab pill rendering:** In browser devtools, look for `.sparql-vocab-pill` elements in the SPARQL results table. Absence means the IRI isn't in `vocabCache` — check `/api/sparql/vocabulary` response.
- **Inspect prefix shortening:** In browser console, type `reversePrefixMap` to see the namespace→prefix mapping. Empty object means `fetchVocabulary()` hasn't run or returned no prefixes.
- **Inspect vocab index:** In browser console, type `Object.keys(vocabIriIndex).length` to see how many vocabulary IRIs are indexed.
- **Backend filtering:** If model IRIs still aren't enriched, check whether a new `urn:sempkm:` sub-namespace was added without updating `_VOCAB_PREFIXES`.

## Deviations

- Added `vocabIriIndex` (IRI→item map) as an optimization over scanning `vocabCache` array on every `renderCell()` call. The plan suggested iterating `vocabCache`; using an indexed object is O(1) vs O(n) per cell.
- Added `reversePrefixMap` as a module-level variable rebuilt in `fetchVocabulary()` rather than lazily in `shortenUri()` — simpler and avoids stale-cache edge cases.

## Known Issues

None.

## Files Created/Modified

- `backend/app/sparql/router.py` — Replaced broad `"urn:sempkm:"` in `_VOCAB_PREFIXES` with 28 specific internal sub-namespace entries
- `frontend/static/js/sparql-console.js` — Updated `KNOWN_VOCAB_PREFIXES` to match backend; added `reversePrefixMap`/`vocabIriIndex` module vars; `fetchVocabulary()` rebuilds both maps; `shortenUri()` checks `reversePrefixMap`; `renderCell()` renders vocab pills via `vocabIriIndex`
- `frontend/static/css/workspace.css` — Added `.sparql-vocab-pill` styles (dashed border, italic label, muted icon color)
- `.gsd/milestones/M031/slices/S05/S05-PLAN.md` — Added Observability/Diagnostics section; marked T01 done
