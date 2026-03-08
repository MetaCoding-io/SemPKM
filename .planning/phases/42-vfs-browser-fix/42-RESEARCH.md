# Phase 42: VFS Browser Fix — Research

**Researched:** 2026-03-06
**Domain:** VFS browser endpoints, htmx error handling, tree UX
**Confidence:** HIGH

## Summary

The VFS browser has three distinct bugs preventing VFS-01 satisfaction. The **primary bug** is a simple AttributeError: the `/browser/vfs/{model_id}/objects` endpoint calls `label_service.get_labels(iris)` but `LabelService` only exposes `resolve_batch(iris)`. This causes a 500 error on every type-folder expansion. The **secondary bug** is that the VFS model listing SPARQL queries for `urn:sempkm:modelName` but models are registered with `dcterms:title` -- so model names fall back to IDs (cosmetic but wrong). The **tertiary bug** is the infinite retry loop: htmx `hx-trigger="revealed"` re-fires on DOM changes after a failed request, and there is no global htmx error handler to stop retries.

All three bugs are confirmed via Docker logs (`AttributeError: 'LabelService' object has no attribute 'get_labels'`) and code inspection. UX improvements are minor polish on an already-functional tree component.

**Primary recommendation:** Fix the three bugs in order (API method name, SPARQL predicate, htmx error handling), then polish tree UX.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VFS-01 | Users can open an in-app VFS browser view that displays the virtual filesystem tree (model -> type -> objects) | Three bugs found: wrong LabelService method name (500 error), wrong SPARQL predicate for model name, infinite htmx retry loop. All fixes identified with exact line references. |
</phase_requirements>

## Root Cause Analysis

### Bug 1: `LabelService.get_labels()` does not exist (CRITICAL)

**File:** `backend/app/browser/router.py`, line 254
**Error:** `AttributeError: 'LabelService' object has no attribute 'get_labels'`
**Evidence:** Docker logs show repeated 500 errors on `GET /browser/vfs/basic-pkm/objects?type_iri=...`

The `vfs_type_objects` endpoint calls:
```python
labels = await label_service.get_labels(iris) if iris else {}
```

But `LabelService` (in `backend/app/services/labels.py`) exposes:
- `resolve(iri: str) -> str` -- single IRI
- `resolve_batch(iris: list[str]) -> dict[str, str]` -- batch, returns `{iri: label}`
- `invalidate(iris)` -- cache clear
- `set_language_prefs(langs)` -- language config

**Fix:** Change `get_labels` to `resolve_batch`. The return type is already `dict[str, str]` which matches usage on line 256.

### Bug 2: Wrong SPARQL predicate for model name (COSMETIC)

**File:** `backend/app/browser/router.py`, lines 178-192
**Impact:** Model tree nodes show IDs instead of human-readable names

The VFS root query uses:
```sparql
OPTIONAL { ?model <urn:sempkm:modelName> ?modelName }
```

But `register_model()` in `backend/app/models/registry.py` (line 132) stores:
```sparql
<model_iri> <http://purl.org/dc/terms/title> "Model Name"
```

**Fix:** Change `<urn:sempkm:modelName>` to `<http://purl.org/dc/terms/title>` in the VFS SPARQL query.

### Bug 3: Infinite htmx retry loop on error (UX-BREAKING)

**File:** `backend/app/templates/browser/_vfs_types.html` and `_vfs_objects.html`
**Mechanism:** `hx-trigger="revealed"` fires when a `display:none` element becomes visible. When the request fails (500), htmx swaps nothing, but the element stays visible. Any subsequent DOM change (layout reflow, other htmx swaps) can re-trigger `revealed`, creating an infinite loop.

**Evidence:** Docker logs show repeated identical requests to the same endpoint.

**No global htmx error handling exists** -- confirmed by searching all JS and template files for `htmx:responseError`, `htmx:afterRequest`, `htmx:sendError`. None found.

**Fix options (choose one):**
1. Add `once` modifier: `hx-trigger="revealed once"` -- fires exactly once regardless of success/failure. Simple, robust.
2. Add htmx error handler that removes `hx-trigger` on failure -- more complex, handles retries better.
3. Swap error content into the target on failure -- shows error message, prevents re-trigger since innerHTML changes.

**Recommended:** Option 1 (`revealed once`) for simplicity. If the request fails, the "Loading..." text stays visible, which is acceptable. Optionally combine with option 3 for better UX.

## Standard Stack

### Core (already in use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | current | API endpoints | Project standard |
| htmx | current | DOM updates, lazy loading | Project standard |
| Jinja2 | current | Template rendering | Project standard |
| Lucide | current | Icons | Project standard |

### No new dependencies needed
This phase is entirely bug fixes in existing code. No new libraries.

## Architecture Patterns

### Existing VFS Architecture (correct, just buggy)

```
Sidebar "Files" link
  -> workspace.js openVfsTab()
    -> dockview addPanel(special-panel, specialType='vfs')
      -> workspace-layout.js htmx.ajax('GET', '/browser/vfs', {target: el})
        -> router.py vfs_browser() -> vfs_browser.html
          -> User expands model node -> toggleVfsNode()
            -> display:none -> display:'' triggers hx-trigger="revealed"
              -> GET /browser/vfs/{model_id}/types -> _vfs_types.html
                -> User expands type node -> toggleVfsNode()
                  -> GET /browser/vfs/{model_id}/objects?type_iri=X -> _vfs_objects.html
                    -> Click object -> openTab(iri, label)
```

### Pattern: htmx `revealed` with error resilience

The existing pattern of `hx-trigger="revealed"` for lazy loading is used in:
- `inference_panel.html` (line 91)
- `workspace.html` (line 97, lint dashboard)
- `vfs_browser.html` (line 16)
- `_vfs_types.html` (line 10)

None of these use `once` modifier. All are vulnerable to retry loops on error, but in practice only VFS hits this because it's the only one with a bug that causes 500s. Adding `once` is safe for all of them, but for this phase, only fix VFS templates.

### Anti-Patterns to Avoid
- **Using inline `style="width:..."` on Lucide icons:** Must use CSS classes per CLAUDE.md
- **Missing `flex-shrink: 0` on SVGs in flex containers:** Per CLAUDE.md guidance
- **Relying on `hx-trigger="revealed"` without error handling:** The current pattern

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Label resolution | Custom SPARQL in VFS endpoint | `LabelService.resolve_batch()` | Already handles caching, precedence chain, language prefs |
| Model listing | Custom SPARQL | Could use `list_installed_models()` from registry.py | Already handles the query correctly with proper predicates |

**Key insight:** The VFS endpoint duplicated the model listing SPARQL instead of reusing `list_installed_models()` from `registry.py`, leading to the predicate mismatch. Consider using the existing function.

## Common Pitfalls

### Pitfall 1: LabelService API mismatch
**What goes wrong:** Calling `get_labels()` instead of `resolve_batch()` on `LabelService`
**Why it happens:** Method name guessed during implementation without checking the service class
**How to avoid:** Always check service class method signatures before calling
**Warning signs:** `AttributeError` in Docker logs

### Pitfall 2: SPARQL predicate inconsistency
**What goes wrong:** Using `urn:sempkm:modelName` when actual predicate is `dcterms:title`
**Why it happens:** Duplicate SPARQL queries that don't match `register_model()` in registry.py
**How to avoid:** Reuse existing query functions or reference `register_model()` for schema
**Warning signs:** Model names showing as IDs in the UI

### Pitfall 3: htmx `revealed` infinite retry
**What goes wrong:** Failed htmx request leaves `hx-trigger="revealed"` active, DOM changes re-trigger
**Why it happens:** No `once` modifier, no global error handler
**How to avoid:** Use `hx-trigger="revealed once"` or implement error content swap
**Warning signs:** Browser network tab shows repeated identical requests

### Pitfall 4: VFS type query uses shapes graph
**What goes wrong:** Type listing queries `ModelGraphs.shapes` graph for NodeShapes
**Why it happens:** Correct -- shapes are stored in model-specific shapes graph
**Risk:** If shapes graph uses different label predicates, type names may not resolve
**Current behavior:** Uses `rdfs:label` which is correct for shape labels

## Code Examples

### Fix 1: Correct LabelService method call
```python
# File: backend/app/browser/router.py, line 254
# Before (broken):
labels = await label_service.get_labels(iris) if iris else {}

# After (fixed):
labels = await label_service.resolve_batch(iris) if iris else {}
```

### Fix 2: Correct model name SPARQL predicate
```python
# File: backend/app/browser/router.py, lines 178-187
# Before (wrong predicate):
OPTIONAL { ?model <urn:sempkm:modelName> ?modelName }

# After (matches register_model):
OPTIONAL { ?model <http://purl.org/dc/terms/title> ?modelName }
```

### Alternative Fix 2: Reuse list_installed_models()
```python
# File: backend/app/browser/router.py
from app.models.registry import list_installed_models

@router.get("/vfs")
async def vfs_browser(request, client, current_user):
    installed = await list_installed_models(client)
    models = [{"id": m.model_id, "name": m.name} for m in installed]
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "browser/vfs_browser.html", {
        "models": models,
    })
```

### Fix 3: Prevent infinite retry
```html
<!-- File: backend/app/templates/browser/vfs_browser.html, line 16 -->
<!-- Before: -->
hx-trigger="revealed"

<!-- After: -->
hx-trigger="revealed once"

<!-- Same fix in _vfs_types.html, line 10 -->
```

### Optional: Error content on failure
```html
<!-- Add to vfs_browser.html script section -->
<script>
document.body.addEventListener('htmx:responseError', function(evt) {
    if (evt.detail.target && evt.detail.target.classList.contains('vfs-children')) {
        evt.detail.target.innerHTML = '<div class="vfs-empty-node">Failed to load</div>';
    }
});
</script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hx-trigger="revealed"` | `hx-trigger="revealed once"` | htmx best practice | Prevents retry loops |

## Open Questions

None -- all bugs have clear root causes and fixes.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (chromium project) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd e2e && npx playwright test --project=chromium -g "vfs"` |
| Full suite command | `cd e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VFS-01 | VFS tree loads models without 500 errors | manual-only | Manual: open VFS tab, expand model, expand type, click object | N/A |
| VFS-01 | Model names display correctly (not IDs) | manual-only | Manual: check model node label in VFS tree | N/A |
| VFS-01 | No infinite retry on error | manual-only | Manual: check browser network tab for repeated requests | N/A |

**Note:** E2E test files are not modifiable per project rules ("test files cannot be modified"). Existing VFS-related test files (`e2e/tests/vfs-webdav.spec.ts`, `e2e/tests/06-settings/vfs-settings.spec.ts`) test WebDAV, not the in-app VFS browser. Validation is manual for this phase.

### Sampling Rate
- **Per task commit:** Docker logs check for 500 errors, manual VFS tree expansion
- **Per wave merge:** Full E2E suite: `cd e2e && npx playwright test --project=chromium`
- **Phase gate:** Manual verification of VFS tree functionality

### Wave 0 Gaps
None -- no new test infrastructure needed. Fixes are backend bug fixes verified by manual testing.

## Sources

### Primary (HIGH confidence)
- Docker logs: `AttributeError: 'LabelService' object has no attribute 'get_labels'` -- direct error evidence
- `backend/app/services/labels.py` -- confirms `resolve_batch()` is the correct method
- `backend/app/models/registry.py` lines 127-137 -- confirms `dcterms:title` is the stored predicate
- `backend/app/browser/router.py` lines 171-261 -- VFS endpoint implementations

### Secondary (MEDIUM confidence)
- htmx docs on `revealed` trigger behavior -- `once` modifier prevents re-triggering

## Metadata

**Confidence breakdown:**
- Root cause analysis: HIGH - confirmed via Docker logs and code inspection
- Fix approach: HIGH - trivial method rename and predicate fix
- Retry loop fix: HIGH - standard htmx `once` modifier pattern

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- bug fix, no moving targets)
