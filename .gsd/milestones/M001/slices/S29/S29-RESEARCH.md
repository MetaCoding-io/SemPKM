# Phase 29: FTS Fuzzy Search - Research

**Researched:** 2026-03-01
**Domain:** RDF4J LuceneSail fuzzy query syntax, FastAPI search endpoint, ninja-keys command palette toggle pattern
**Confidence:** HIGH (primary findings from direct codebase analysis + verified against RDF4J official Javadoc)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FTS-04 | User can find objects with typo-tolerant fuzzy matching (edit distance ~1); fuzzy mode is a user-controlled toggle in the Ctrl+K palette; tokens <5 chars always use exact match | LuceneSail `term~1` syntax confirmed; `_normalize_query()` pattern in `SearchService`; fuzzy toggle via `ninja.data` mutation with localStorage persistence |
</phase_requirements>

---

## Summary

Phase 29 is a focused, fully independent two-backend + one-frontend change. The backend requires (1) adding `_normalize_query()` to `SearchService` to append `~1` to tokens ≥5 characters when fuzzy mode is active, and (2) adding a `fuzzy: bool = False` parameter to the `/api/search` endpoint. The frontend requires adding a fuzzy toggle command entry to ninja-keys (in `workspace.js`) that persists its state in `localStorage`. No new infrastructure, no migrations, no new packages.

The LuceneSail `term~1` fuzzy syntax is built into RDF4J and works directly in the `search:query` value already used in `FTS_QUERY`. The tokenization strategy (≥5 chars get `~1`, shorter tokens stay exact) prevents the short-token dictionary scan problem (e.g., `"of~1"` would match half the index). The toggle defaults to off so existing users see no behavior change until they opt in.

The one area of MEDIUM confidence is the `fuzzyPrefixLength` TTL config property. The research confirms the Java constant value is `"fuzzyPrefixLength"` and the existing `sempkm-repo.ttl` uses the `config:lucene.*` namespace pattern for LuceneSail parameters, suggesting `config:lucene.fuzzyPrefixLength` as the TTL property — but this exact key string was not confirmed in public documentation. The milestone research recommendation to set `fuzzyPrefixLength=2` is a useful enhancement (reduces noise by requiring 2 matching prefix chars before fuzzy expansion) but is not required for correctness; the feature works with the default of 0.

**Primary recommendation:** Implement `_normalize_query()` in `SearchService`, expose `fuzzy` param on `/api/search`, add a fuzzy toggle command to ninja-keys with localStorage persistence. The `fuzzyPrefixLength` TTL config is a nice-to-have enhancement; apply it but verify the TTL key via RDF4J Server UI after applying.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| RDF4J LuceneSail | 5.x (already running) | Full-text search with Lucene query syntax | Already deployed; `term~1` fuzzy is native Lucene syntax, no new packages |
| FastAPI | latest (already running) | HTTP endpoint with `fuzzy: bool` query param | Already the backend framework |
| ninja-keys | 1.2.2 (CDN, already loaded) | Command palette with toggle entry for fuzzy mode | Already integrated in workspace.js |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| localStorage (native browser) | N/A | Persist fuzzy toggle state across sessions | Used for all user preference persistence in this project |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `term~1` Lucene fuzzy | `term~` (Lucene ≤ 1.x fractional similarity) | `~1` is the integer edit-distance syntax for Lucene 4+; do not use fractional form |
| Single `fuzzy` backend param | Client-side token manipulation | Backend normalization is cleaner; keeps query logic server-side and testable |
| `~2` edit distance | `~1` | `~2` matches too broadly (near-full dictionary scan for 5-char tokens); `~1` is the correct default |

**Installation:** None — no new packages required.

---

## Architecture Patterns

### Files to Change

```
backend/app/services/search.py        — add _normalize_query(), add fuzzy param to search()
backend/app/sparql/router.py           — add fuzzy: bool = False query param to /api/search
config/rdf4j/sempkm-repo.ttl           — add config:lucene.fuzzyPrefixLength "2" (enhancement)
frontend/static/js/workspace.js        — add fuzzy toggle command to ninja.data, localStorage
```

No new files. No migrations. No new routes.

### Pattern 1: `_normalize_query()` in SearchService

**What:** A method that takes a raw query string and a `fuzzy: bool` flag, then returns a Lucene query string with `~1` appended to qualifying tokens.

**When to use:** Called from `search()` before interpolating the query into `FTS_QUERY`.

**Example:**
```python
# Source: RDF4J LuceneSail docs (term~N is standard Lucene fuzzy syntax)
def _normalize_query(self, query: str, fuzzy: bool = False) -> str:
    """Normalize query string; append ~1 to tokens >=5 chars if fuzzy mode active."""
    if not fuzzy:
        return query.strip()
    tokens = query.strip().split()
    normalized = []
    for token in tokens:
        # Avoid double-appending if user manually typed ~
        if len(token) >= 5 and not token.endswith('~') and not token.endswith('*'):
            normalized.append(token + '~1')
        else:
            normalized.append(token)
    return ' '.join(normalized)
```

**Key detail:** Skip tokens already ending in `~` or `*` (user-typed operators). This prevents `knowledge~1~1` if the user manually types fuzzy syntax.

### Pattern 2: `/api/search` endpoint — add `fuzzy` param

**What:** Add `fuzzy: bool = Query(False)` to the existing `search_knowledge_base` endpoint in `backend/app/sparql/router.py`. Pass it through to `search_service.search()`.

**Example:**
```python
# Source: existing router.py pattern — only the param and service call change
@router.get("/search")
async def search_knowledge_base(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    fuzzy: bool = Query(False),          # NEW
    user: User = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service),
) -> JSONResponse:
    results = await search_service.search(query=q, limit=limit, fuzzy=fuzzy)  # pass through
    ...
```

### Pattern 3: `SearchService.search()` — thread fuzzy through

**What:** Add `fuzzy: bool = False` to the `search()` method signature. Call `_normalize_query()` before `FTS_QUERY.format()`.

```python
# Source: backend/app/services/search.py direct analysis
async def search(self, query: str, limit: int = 20, fuzzy: bool = False) -> list[SearchResult]:
    if not query or not query.strip():
        return []
    normalized = self._normalize_query(query, fuzzy)
    sparql = FTS_QUERY.format(query=normalized, limit=limit)
    ...
```

### Pattern 4: ninja-keys fuzzy toggle command

**What:** A toggle command in `ninja.data` whose `title` reflects current state. On activation, it flips a module-level `_fuzzyEnabled` flag, updates localStorage, re-titles itself, and re-assigns `ninja.data` to trigger ninja-keys re-render.

**When to use:** Added in `_initFtsSearch(ninja)` after the change listener is registered.

**Example:**
```javascript
// Source: workspace.js direct analysis — follows existing toggle-* command pattern
var FUZZY_KEY = 'sempkm_fts_fuzzy';

function _initFtsSearch(ninja) {
  var _ftsDebounce = null;
  var _ftsAbort = null;
  var _fuzzyEnabled = localStorage.getItem(FUZZY_KEY) === 'true';

  function _updateFuzzyToggleTitle() {
    var idx = ninja.data.findIndex(function(d) { return d.id === 'fts-fuzzy-toggle'; });
    if (idx === -1) return;
    var newData = ninja.data.slice();
    newData[idx] = Object.assign({}, newData[idx], {
      title: _fuzzyEnabled ? 'Search: Fuzzy Mode ON (click to disable)' : 'Search: Fuzzy Mode OFF (click to enable)'
    });
    ninja.data = newData;
  }

  // Add fuzzy toggle to initial ninja.data
  ninja.data = ninja.data.concat([{
    id: 'fts-fuzzy-toggle',
    title: _fuzzyEnabled ? 'Search: Fuzzy Mode ON (click to disable)' : 'Search: Fuzzy Mode OFF (click to enable)',
    section: 'Search',
    handler: function() {
      _fuzzyEnabled = !_fuzzyEnabled;
      localStorage.setItem(FUZZY_KEY, String(_fuzzyEnabled));
      _updateFuzzyToggleTitle();
    }
  }]);

  ninja.addEventListener('change', function(e) {
    var query = (e.detail && e.detail.search) ? e.detail.search : '';
    if (!query || query.length < 2) {
      ninja.data = ninja.data.filter(function(d) { return !d.id.startsWith('fts-result-'); });
      return;
    }
    clearTimeout(_ftsDebounce);
    if (_ftsAbort) { _ftsAbort.abort(); }
    _ftsDebounce = setTimeout(function() {
      var controller = new AbortController();
      _ftsAbort = controller;
      var url = '/api/search?q=' + encodeURIComponent(query) + '&limit=10' + (_fuzzyEnabled ? '&fuzzy=true' : '');
      fetch(url, { signal: controller.signal, credentials: 'same-origin' })
        .then(function(resp) { return resp.ok ? resp.json() : null; })
        .then(function(data) {
          if (!data || !data.results) return;
          var baseData = ninja.data.filter(function(d) { return !d.id.startsWith('fts-result-'); });
          var ftsItems = data.results.map(function(r) {
            var icon = _typeToIcon(r.type);
            var snippet = r.snippet ? ' — ' + r.snippet.replace(/<\/?[^>]+>/g, '').substring(0, 60) : '';
            return {
              id: 'fts-result-' + r.iri,   // NOTE: renamed from 'fts-' to 'fts-result-' to avoid
              title: r.label + snippet,      // colliding with 'fts-fuzzy-toggle'
              section: 'Search',
              icon: icon,
              handler: function() { openTab(r.iri, r.label); }
            };
          });
          ninja.data = baseData.concat(ftsItems);
        })
        .catch(function() {});
    }, 300);
  });
}
```

**IMPORTANT ID CHANGE:** The existing code uses `id: 'fts-' + r.iri` and filters by `d.id.startsWith('fts-')`. Adding the toggle as `id: 'fts-fuzzy-toggle'` would cause the toggle to be removed on each FTS result update. The fix is to rename result IDs to `'fts-result-' + r.iri` and filter by `d.id.startsWith('fts-result-')`. Both the `ninja.addEventListener('change', ...)` filter and the initial data setup must use the new prefix.

### Pattern 5: `sempkm-repo.ttl` — fuzzyPrefixLength config

**What:** Add `config:lucene.fuzzyPrefixLength "2"` to the LuceneSail stanza in `config/rdf4j/sempkm-repo.ttl`.

**Caution:** The exact TTL property name for `fuzzyPrefixLength` was not confirmed in public documentation. The pattern from existing config (`config:lucene.indexDir` maps to sail param `lucenedir`) suggests `config:lucene.fuzzyPrefixLength` is the correct key. However, this must be verified after applying — check the RDF4J Server UI to confirm the parameter is accepted without error.

**Fallback:** If the TTL config key is wrong, RDF4J will likely ignore the unknown property (no error, no crash). Alternatively, `fuzzyPrefixLength` can be left at the default (0); the feature still works, with slightly more noise from fuzzy expansion.

**Expected TTL change:**
```turtle
config:sail.impl [
   config:sail.type "openrdf:LuceneSail" ;
   config:lucene.indexDir "/var/rdf4j/lucene" ;
   config:lucene.fuzzyPrefixLength "2" ;    # NEW — requires 2 prefix chars before fuzzy expansion
   config:delegate [
      ...
   ]
]
```

### Anti-Patterns to Avoid

- **`~2` edit distance:** Never use `~2` — at 5 characters it matches nearly all 5-char words in the index; `~1` is the correct threshold.
- **Fuzzy on tokens < 5 chars:** Do not append `~1` to short tokens (`"of~1"`, `"a~1"`, `"the~1"`). These produce dictionary-scan noise that floods results.
- **Leading wildcard (`*term`):** Not relevant to fuzzy, but avoid — LuceneSail does a full index scan for leading wildcards.
- **`id: 'fts-' + iri` colliding with toggle ID:** Existing result IDs use prefix `'fts-'`. Adding the toggle as `'fts-fuzzy-toggle'` would cause it to be deleted by the existing `startsWith('fts-')` filter on each query change. Must rename result ID prefix to `'fts-result-'`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Levenshtein distance in Python | LuceneSail `term~1` Lucene syntax | LuceneSail indexes the entire triplestore; custom Python matching would require fetching all labels first |
| Query tokenization | Regex-based tokenizer | `str.split()` on whitespace | Lucene query string tokenizes on whitespace naturally; multi-word fuzzy is `token1~1 token2~1` |

**Key insight:** The fuzzy operator is already in the index engine. The entire backend change is a string transformation on the query — no new query patterns, no new SPARQL, no new indexing.

---

## Common Pitfalls

### Pitfall 1: `fts-` ID prefix collision with fuzzy toggle
**What goes wrong:** Adding the toggle command with `id: 'fts-fuzzy-toggle'` and then filtering `startsWith('fts-')` in the `change` listener removes the toggle on every search input change.
**Why it happens:** The existing `_initFtsSearch` code uses `'fts-'` as a shared prefix for all FTS-injected items and clears them all when query changes.
**How to avoid:** Rename search result IDs to `'fts-result-' + r.iri` and update both the injection step and the filter step to use `startsWith('fts-result-')`. The toggle uses `id: 'fts-fuzzy-toggle'` and is never cleared by the change listener.
**Warning signs:** Fuzzy toggle disappears from the palette after typing any character.

### Pitfall 2: Double-appending fuzzy operator to user-typed queries
**What goes wrong:** User types `knowledge~1` manually; `_normalize_query()` appends another `~1`, producing `knowledge~1~1` which is a Lucene syntax error.
**Why it happens:** Normalization doesn't check for existing operators.
**How to avoid:** Skip tokens that already end with `~` (with or without a digit) or `*`.
**Warning signs:** LuceneSail SPARQL query exception for malformed query string in server logs.

### Pitfall 3: Short-token fuzzy noise
**What goes wrong:** "alice of~1 the~1 smith~1" returns hundreds of irrelevant results because `of~1` matches every 2-3 letter word in the index.
**Why it happens:** Edit distance 1 on a 2-character token matches almost everything.
**How to avoid:** Apply `~1` only to `len(token) >= 5`. Use exact match for tokens shorter than 5 characters.
**Warning signs:** Fuzzy search returns far more results than expected; single-word queries with short tokens return near-complete index.

### Pitfall 4: `fuzzyPrefixLength` TTL key not recognized
**What goes wrong:** RDF4J silently ignores `config:lucene.fuzzyPrefixLength` if the property name is not in its config schema.
**Why it happens:** The exact TTL property name is not confirmed in public docs; the pattern is inferred from existing keys.
**How to avoid:** After applying the TTL change, inspect RDF4J Server's repository configuration UI or logs to confirm the parameter was parsed. If ignored, remove the TTL line — the feature works with `fuzzyPrefixLength=0` (default), just with slightly more expansion noise.
**Warning signs:** No crash or error — just check whether fuzzy queries return more noise than expected on short-prefix tokens.

### Pitfall 5: localStorage key collision
**What goes wrong:** A future feature uses `sempkm_fts_fuzzy` for something else.
**How to avoid:** Use namespaced key `sempkm_fts_fuzzy`. Check existing localStorage keys in `workspace.js` before choosing (current keys: `sempkm_pane_sizes`, `sempkm_panel_key`, `sempkm_panel_positions`).

---

## Code Examples

### Full `_normalize_query()` implementation

```python
# Source: direct codebase analysis of backend/app/services/search.py
def _normalize_query(self, query: str, fuzzy: bool = False) -> str:
    """Normalize a user query string for LuceneSail.

    In fuzzy mode, appends ~1 (edit distance 1) to tokens with 5+ characters.
    Tokens shorter than 5 characters always use exact match to avoid
    dictionary-scan noise.

    Args:
        query: Raw user query string.
        fuzzy: Whether to apply fuzzy expansion.

    Returns:
        Normalized Lucene query string.
    """
    q = query.strip()
    if not fuzzy:
        return q
    tokens = q.split()
    normalized = []
    for token in tokens:
        # Skip tokens that already have an operator suffix (~, *, ?)
        if len(token) >= 5 and not token[-1] in ('~', '*', '?'):
            normalized.append(token + '~1')
        else:
            normalized.append(token)
    return ' '.join(normalized)
```

### `/api/search` endpoint change (sparql/router.py)

```python
# Source: direct codebase analysis
@router.get("/search")
async def search_knowledge_base(
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    fuzzy: bool = Query(False, description="Enable fuzzy (typo-tolerant) matching for tokens >=5 chars"),
    user: User = Depends(get_current_user),
    search_service: SearchService = Depends(get_search_service),
) -> JSONResponse:
    results = await search_service.search(query=q, limit=limit, fuzzy=fuzzy)
    return JSONResponse(content={
        "query": q,
        "fuzzy": fuzzy,
        "count": len(results),
        "results": [
            {
                "iri": r.iri,
                "type": r.type,
                "label": r.label,
                "snippet": r.snippet,
                "score": r.score,
            }
            for r in results
        ],
    })
```

### Frontend fetch with fuzzy param (workspace.js)

```javascript
// Source: direct codebase analysis of frontend/static/js/workspace.js _initFtsSearch
var url = '/api/search?q=' + encodeURIComponent(query)
        + '&limit=10'
        + (_fuzzyEnabled ? '&fuzzy=true' : '');
fetch(url, { signal: controller.signal, credentials: 'same-origin' })
```

### sempkm-repo.ttl change

```turtle
# Source: config/rdf4j/sempkm-repo.ttl direct analysis
# NOTE: config:lucene.fuzzyPrefixLength key is inferred from the config: namespace
# pattern — verify in RDF4J Server UI after applying
config:sail.impl [
   config:sail.type "openrdf:LuceneSail" ;
   config:lucene.indexDir "/var/rdf4j/lucene" ;
   config:lucene.fuzzyPrefixLength "2" ;
   config:delegate [
      config:sail.type "openrdf:NativeStore" ;
      config:native.tripleIndexes "spoc,posc,cspo" ;
      config:sail.defaultQueryEvaluationMode "STANDARD"
   ]
] .
```

---

## Existing Infrastructure Inventory

Critical context for the planner:

**`backend/app/services/search.py`:**
- `SearchService.search(query, limit)` — the method to modify
- `FTS_QUERY` — the SPARQL template using `search:query {query!r}` — this is where the normalized query lands
- No existing `_normalize_query()` method

**`backend/app/sparql/router.py`:**
- `GET /api/search` at line 128 — the endpoint to modify
- Currently accepts `q` and `limit`; add `fuzzy: bool = False`

**`frontend/static/js/workspace.js`:**
- `_initFtsSearch(ninja)` at line 1062 — the function to modify
- Currently uses `id: 'fts-' + r.iri` and filters `startsWith('fts-')` — must rename to `'fts-result-'`
- `ninja.data` assignment pattern already established for toggle items (see theme-light, theme-dark)

**`config/rdf4j/sempkm-repo.ttl`:**
- Currently has `config:lucene.indexDir "/var/rdf4j/lucene"` — add `fuzzyPrefixLength` here

**E2E tests (`e2e/tests/08-search/fts-search.spec.ts`):**
- Existing tests use `id.startsWith('fts-')` to check for FTS results (line 116: `d.id.startsWith('fts-') && d.section === 'Search'`)
- After renaming result IDs to `'fts-result-'`, this test would fail
- New tests (Phase 34, TEST-02) cover FTS; this phase should not break existing tests

**CRITICAL: The existing E2E test at line 116 checks `d.id.startsWith('fts-')`**. If result IDs are renamed to `'fts-result-'`, this test breaks. Since test files cannot be modified (per MEMORY.md), the renaming strategy must keep the existing test passing. Options:
1. Keep result IDs as `'fts-' + r.iri` and use a different prefix for the toggle: `'fts-toggle-fuzzy'` — then the filter `startsWith('fts-')` incorrectly deletes the toggle too.
2. Better: Use `id: 'fts-' + r.iri` unchanged for results (satisfies existing test), and use a completely different prefix for the toggle — e.g., `id: 'search-fuzzy-toggle'` (not starting with `'fts-'`). The change listener filter `startsWith('fts-')` then only removes results and never touches the toggle.

**Option 2 is correct.** The fuzzy toggle gets `id: 'search-fuzzy-toggle'` (or any non-`'fts-'` prefix). The change listener filter `startsWith('fts-')` correctly removes only search results, leaving the toggle intact. Existing E2E test continues to pass because result IDs still start with `'fts-'`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fractional fuzzy `term~0.8` | Integer edit distance `term~1` | Lucene 4.0 | Integer edit distance is the current standard; fractional syntax is deprecated |
| `fuzzyPrefixLength=0` (default) | `fuzzyPrefixLength=2` (recommended) | Config change | Requires 2 prefix chars to match before fuzzy expansion; reduces noise |

**Deprecated/outdated:**
- Lucene `~0.8` fractional similarity syntax: replaced by `~1` (integer edit distance 0, 1, or 2) in Lucene 4+. Do not use.

---

## Open Questions

1. **`config:lucene.fuzzyPrefixLength` TTL key**
   - What we know: The Java constant `FUZZY_PREFIX_LENGTH_KEY = "fuzzyPrefixLength"`. Existing TTL maps `config:lucene.indexDir` to `lucenedir` sail param.
   - What's unclear: Whether the TTL namespace maps `fuzzyPrefixLength` → `config:lucene.fuzzyPrefixLength` or uses a different pattern.
   - Recommendation: Apply `config:lucene.fuzzyPrefixLength "2"` and verify in RDF4J Server UI. If not accepted, remove it — the feature works without it (default is 0).

2. **Reindex required after `fuzzyPrefixLength` change?**
   - What we know: `fuzzyPrefixLength` is a QueryParser setting, not an index-time setting. It controls how the fuzzy query is expanded at search time, not how the index is built.
   - What's unclear: Whether changing this requires `forceReindex` in RDF4J.
   - Recommendation: No reindex should be needed. But if queries return unexpected results after the config change, trigger a reindex via RDF4J Server admin UI.

---

## Sources

### Primary (HIGH confidence)
- `backend/app/services/search.py` — direct codebase analysis; `SearchService.search()`, `FTS_QUERY`
- `backend/app/sparql/router.py` — direct codebase analysis; `/api/search` endpoint signature at line 128
- `frontend/static/js/workspace.js` — direct codebase analysis; `_initFtsSearch()` at line 1062, `ninja.data` toggle patterns, ID prefix `'fts-'`
- `config/rdf4j/sempkm-repo.ttl` — direct codebase analysis; existing LuceneSail stanza
- `e2e/tests/08-search/fts-search.spec.ts` — direct analysis; line 116 `startsWith('fts-')` constraint
- [RDF4J LuceneSail Javadoc 5.1.3](https://rdf4j.org/javadoc/latest/org/eclipse/rdf4j/sail/lucene/LuceneSail.html) — `FUZZY_PREFIX_LENGTH_KEY = "fuzzyPrefixLength"`, fuzzy query syntax
- [RDF4J Constant Field Values](https://rdf4j.org/javadoc/latest/constant-values.html) — confirms `FUZZY_PREFIX_LENGTH_KEY` string value
- `.planning/research/SUMMARY.md` — milestone research: LuceneSail `term~1` HIGH confidence, 5-char threshold, `fuzzyPrefixLength=2` recommendation

### Secondary (MEDIUM confidence)
- [RDF4J LuceneSail documentation](https://rdf4j.org/documentation/programming/lucene/) — fuzzy `term~N` syntax pattern; `config:lucene.*` namespace pattern for TTL config
- WebSearch results confirming `FUZZY_PREFIX_LENGTH_KEY = "fuzzyPrefixLength"` Java constant

### Tertiary (LOW confidence)
- `config:lucene.fuzzyPrefixLength "2"` as the TTL property name — inferred from existing `config:lucene.indexDir` pattern; not confirmed in official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing stack, no new packages, direct codebase verification
- Architecture: HIGH — based on direct analysis of all 4 files to change + E2E test constraint discovered
- Pitfalls: HIGH — ID prefix collision discovered via direct code analysis; `~1` vs `~2` confirmed via Lucene docs; short-token noise confirmed via SUMMARY.md
- fuzzyPrefixLength TTL key: MEDIUM — inferred from naming pattern, not confirmed

**Research date:** 2026-03-01
**Valid until:** Stable (no version changes planned; `~1` syntax is Lucene 4+ standard, unchanged for 10+ years)