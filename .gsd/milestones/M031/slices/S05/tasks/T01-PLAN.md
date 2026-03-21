---
estimated_steps: 5
estimated_files: 2
skills_used: []
---

# T01: Fix SPARQL prefix shortening and IRI pill fallthrough

**Slice:** S05 — SPARQL + Ontology + Graph + Full-Height Polish
**Milestone:** M031

## Description

Model ontology IRIs (e.g., `urn:sempkm:model:basic-pkm:Person`) fall through to plain `<span class="sparql-uri">` elements in SPARQL results because (a) the backend `_VOCAB_PREFIXES` tuple includes a broad `urn:sempkm:` that excludes ALL sempkm-namespace IRIs from enrichment, and (b) the frontend `shortenUri()` uses a hardcoded prefix map that doesn't include model-specific prefixes.

This task fixes both the backend filtering and the frontend rendering to properly handle model ontology IRIs.

## Steps

1. **Backend: Narrow `_VOCAB_PREFIXES` in `backend/app/sparql/router.py`** (line ~67-80). Replace the single broad `"urn:sempkm:"` entry with more specific exclusions that still block internal machinery IRIs but don't block model class/property IRIs. Specifically, keep entries like `"urn:sempkm:query:"`, `"urn:sempkm:dashboard:"`, `"urn:sempkm:workflow:"`, `"urn:sempkm:view:"`, `"urn:sempkm:canvas:"`, `"urn:sempkm:vfs:"` etc. — the internal mechanism namespaces. Do NOT exclude `urn:sempkm:model:*` since those are class/property IRIs that should get pills. Also update the corresponding JS `KNOWN_VOCAB_PREFIXES` array (line ~59) in `frontend/static/js/sparql-console.js` to match.

2. **Frontend: Make `shortenUri()` use `prefixCache`** in `frontend/static/js/sparql-console.js` (line ~380). After the hardcoded prefix check, build a reverse map from `prefixCache` (which maps `prefix → namespace`) to `namespace → prefix`, and iterate it to shorten URIs. Build the reverse map lazily (cache it in a module-level variable, rebuild when `prefixCache` changes in `fetchVocabulary()`).

3. **Frontend: Add vocab pill fallback in `renderCell()`** in `frontend/static/js/sparql-console.js` (line ~342). After the `if (enr)` check for enriched IRIs, add a second path: if the URI matches a vocabulary item in `vocabCache` (which contains items with `iri` and `qname` fields from `/api/sparql/vocabulary`), render it as a styled `<span class="sparql-iri-pill sparql-vocab-pill">` with the QName as label and a generic vocabulary icon (e.g., `tag` or `hash`). This gives model ontology class/property IRIs a pill appearance without needing full backend enrichment.

4. **Add CSS for `.sparql-vocab-pill`** in `frontend/static/css/workspace.css` (where the existing `.sparql-iri-pill` styles live, around line 6790). Style it similarly to `.sparql-iri-pill` but with a distinct visual treatment (e.g., a different accent color or dashed border) so users can distinguish data object pills from vocabulary/ontology pills.

5. **Validate**: Run `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"`. Grep to confirm no broad `urn:sempkm:` remains in `_VOCAB_PREFIXES`. Confirm `shortenUri` references `prefixCache`.

## Must-Haves

- [ ] `_VOCAB_PREFIXES` no longer contains a single broad `"urn:sempkm:"` entry — replaced with specific internal namespace entries
- [ ] `KNOWN_VOCAB_PREFIXES` JS array matches the updated backend list
- [ ] `shortenUri()` checks `prefixCache` after the hardcoded prefix map
- [ ] `renderCell()` renders vocabulary IRIs (from `vocabCache`) as vocab pills when no enrichment is available
- [ ] CSS styles for `.sparql-vocab-pill` exist

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/sparql/router.py').read())"` — syntax OK
- `grep "urn:sempkm:" backend/app/sparql/router.py` — shows specific sub-namespace entries, NOT a broad `"urn:sempkm:"`
- `grep "prefixCache" frontend/static/js/sparql-console.js | grep -i "shorten"` — shortenUri uses prefixCache
- `grep "sparql-vocab-pill" frontend/static/js/sparql-console.js` — vocab pill rendering exists
- `grep "sparql-vocab-pill" frontend/static/css/workspace.css` — CSS exists

## Inputs

- `backend/app/sparql/router.py` — contains `_VOCAB_PREFIXES` (line ~67) and `_is_object_iri()` (line ~177)
- `frontend/static/js/sparql-console.js` — contains `KNOWN_VOCAB_PREFIXES` (line ~59), `vocabCache` (line ~51), `prefixCache` (line ~52), `shortenUri()` (line ~380), `renderCell()` (line ~342)
- `frontend/static/css/workspace.css` — contains existing `.sparql-iri-pill` styles (line ~6790)

## Expected Output

- `backend/app/sparql/router.py` — `_VOCAB_PREFIXES` narrowed to specific internal namespaces
- `frontend/static/js/sparql-console.js` — `shortenUri()` uses `prefixCache`; `renderCell()` renders vocab pills
- `frontend/static/css/workspace.css` — new `.sparql-vocab-pill` styles added near existing `.sparql-iri-pill`
