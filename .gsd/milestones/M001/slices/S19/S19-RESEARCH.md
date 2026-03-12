# Phase 19: Bug Fixes and E2E Test Hardening - Research

**Researched:** 2026-02-26
**Domain:** Python/FastAPI backend bug fixes, htmx/JS frontend bug fixes, Playwright e2e testing
**Confidence:** HIGH — all findings are from direct codebase inspection

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### UI Bugs to Fix (user-discovered)
1. **Docs/tutorials link does not work** — The Docs tab (Phase 18) link is broken; fix so the docs tab opens correctly.
2. **Tutorial links don't work** — When the docs tab does open, clicking tutorial links fails; fix the Driver.js tutorial launch.
3. **Tab reload on every click** — Clicking an already-active tab in the object browser reloads it; clicking a tab should be a no-op if already active.
4. **Split tab shows new tab content in old tab** — When splitting (Ctrl+\\), the old tab displays the new tab's content instead of its own; old tab must retain its content after a split.
5. **Edit button doesn't work on first touch** — The Edit/Done toggle fails on first click but works on subsequent clicks; must work on first interaction.
6. **Autocomplete concepts dropdown missing** — In edit mode, the autocomplete for reference properties (e.g. Concepts) does not show a dropdown; dropdown must appear and be selectable.

#### Tag Pill Display
- Property scope: `model:basic-pkm:tags` values only
- Display format: `#Label` inside a rounded pill element (e.g. `<span class="tag-pill">#Notes</span>`)
- Visual only — no click/navigation action
- Apply in both read-only and edit form views wherever this property's values are rendered

#### Tooltip Consistency
- Target locations: nav tree item hover + graph node hover
- Source style: use the graph view tooltip as the reference (shortened prefix labels, table-aligned layout, slightly larger than current nav tree tooltip)
- Tooltip should show: Type label + object label in a small table/grid layout with shortened IRI prefixes

#### Backend Bug Fixes (CONCERNS.md)
- **Label cache**: Call `label_service.invalidate(event_result.affected_iris)` after every `event_store.commit()` in browser router write handlers
- **Datetime timezone**: Replace all `datetime.now()` in browser router with `datetime.now(timezone.utc)`
- **EventStore DI**: Add `get_event_store` dependency to `dependencies.py`, inject via `Depends` in browser router write handlers
- **IRI validation**: Add validation that decoded IRIs are valid absolute URIs before SPARQL interpolation
- **Cookie secure**: Add `COOKIE_SECURE` env var (default `True`); use it in session cookie creation

#### CORS Fix
- Add `CORS_ORIGINS` env var: comma-separated list of allowed origins (e.g. `http://localhost:3901,https://myprod.com`)
- When `CORS_ORIGINS` is set: use those origins with `allow_credentials=True`
- When `CORS_ORIGINS` is not set: default to `["*"]` with `allow_credentials=False` (safe open fallback, no credential leakage)

#### Debug Endpoint Auth
- `/sparql` and `/commands` debug pages: add `Depends(require_role("owner"))` guard
- Owner role required, no DEBUG flag needed — simple and consistent with other owner-only pages

#### E2E Test Hardening
- Target: maintain >=118/123 passing on chromium with no regressions
- The 5 failing setup wizard tests (`00-setup/01-setup-wizard.spec.ts`) are a known infrastructure issue — document with a clear comment in the test file and/or a README note; do not skip or tag them
- Add new tests for critical Phase 10-18 paths: dark mode toggle, settings save, event log, split panes, tutorial launch
- Scope: add tests to cover success criteria #5 and #6 from the roadmap

### Claude's Discretion
- Exact pill CSS (color, border-radius, font-size — match the app's existing design language)
- Tooltip component implementation (custom CSS tooltip vs. existing popover infrastructure)
- Specific file locations for new e2e test specs
- Order of bug fixes within plan 19-01

### Deferred Ideas (OUT OF SCOPE)
- Alembic migration runner at startup — tech debt from CONCERNS.md, deferred (not in scope for Phase 19)
- ViewSpecService TTL cache — performance improvement from CONCERNS.md, deferred
- SMTP email delivery — missing feature from CONCERNS.md, separate future work
- Session cleanup job — maintenance task, deferred
- Dependency pinning in pyproject.toml — deferred
- Rate limiting on auth endpoints — security hardening, deferred
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUG-01 | Label cache invalidation called after every write — stale labels no longer persist after rename/patch | `LabelService.invalidate()` exists at `services/labels.py:128`; 4 `EventStore(client)` sites in `browser/router.py` (lines 697, 1013, 1120, 1298) need invalidate call after each commit |
| BUG-02 | All `datetime.now()` in browser router use `timezone.utc` — timestamps consistent with EventStore | 2 sites confirmed: `browser/router.py:688` and `browser/router.py:1111`; fix requires adding `timezone` to existing `datetime` import |
| BUG-03 | EventStore injected via DI in browser router's write handlers (not constructed ad-hoc) | `app.state.event_store` already set in `main.py:86`; add `get_event_store` to `dependencies.py` following existing pattern; replace 4 inline `EventStore(client)` constructions |
| BUG-04 | CORS wildcard + credentials misconfiguration resolved; debug endpoints require owner role | `main.py:266-272` has the misconfiguration; `debug/router.py:12,20` use only `get_current_user`; both need specific targeted fixes |
| BUG-05 | UI bugs fixed: docs/tutorial links, tab reload, split tab content bleed, edit button first-touch, autocomplete dropdown, tooltips, tag pills | Spread across `workspace-layout.js`, `workspace.js`, `_field.html`, `object_read.html`, `tree_children.html`, `nav_tree.html`; detailed per-bug analysis below |
| TEST-01 | E2E test suite runs >=118/123 on chromium with no regressions from Phase 10-18 work | Playwright project `chromium` in `e2e/playwright.config.ts`; existing 118/123 baseline from MEMORY.md |
| TEST-02 | Critical paths have e2e coverage: object CRUD, dark mode toggle, settings save, event log, split panes, tutorial launch | `06-settings/dark-mode.spec.ts` and `06-settings/settings-page.spec.ts` exist; need new specs for event log, split panes, tutorial launch |
</phase_requirements>

---

## Summary

Phase 19 is a pure polish/hardening phase — no new features, only bug fixes and test hardening. The work divides cleanly into two workstreams: (1) backend and frontend bug fixes and (2) e2e test hardening.

The backend bugs are small, surgical, and well-scoped. All 4 `EventStore(client)` constructions in `browser/router.py` need to be replaced with DI. The `datetime.now()` calls on lines 688 and 1111 need `timezone.utc`. The label cache invalidation pattern is already implemented (the `invalidate()` method exists at `labels.py:128`) — it just needs to be called after each commit. CORS, cookie-secure, and debug-endpoint fixes are each 1-3 line changes with matching env var additions.

The frontend bugs require careful diagnosis. The tab reload bug is a missing early-return guard in `switchTabInGroup` — it calls `loadTabInGroup` unconditionally even when `tabId === group.activeTabId`. The split-tab content bleed is in `splitRight()`: the old tab's `editorArea.innerHTML` is set to a loading skeleton then the new group's content is loaded into it instead of the new group's editor area. The edit-button first-touch bug is likely a timing issue where the `_initEditMode_` function reference on window is not yet set when `toggleObjectMode` first calls it. The autocomplete dropdown likely has a CSS `overflow:hidden` or z-index issue on the `.suggestions-dropdown` container.

The e2e hardening is additive — two test files need to be created (event log, split panes/tutorial) and the known 5 failing setup-wizard tests need a code comment explaining the infrastructure constraint (not to be skipped or tagged).

**Primary recommendation:** Implement backend bugs as one plan (19-01), UI bugs as a second plan (19-02), and e2e hardening as a third plan (19-03), allowing each to be verified independently.

---

## Standard Stack

### Core (already in use — no new dependencies needed)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| FastAPI | current | Web framework | `browser/router.py`, `dependencies.py` |
| Python `datetime` | stdlib | Timezone-aware timestamps | Add `timezone` to existing import |
| Playwright | current in `e2e/` | E2E test runner | `playwright.config.ts` in `e2e/` |
| htmx | CDN | Partial HTML swaps | Autocomplete uses `hx-get`/`hx-trigger` |
| Split.js | CDN | Pane splitting | `splitRight()` in `workspace-layout.js` |

### No New Dependencies

This phase requires zero new packages. All fixes use existing imports, existing CSS classes, and existing infrastructure.

---

## Architecture Patterns

### Pattern 1: DI Dependency Addition (for get_event_store)

The project has a well-established pattern in `app/dependencies.py`. All dependencies follow the same shape:

```python
# Source: backend/app/dependencies.py (all existing deps follow this pattern)
async def get_event_store(request: Request) -> EventStore:
    """Get the EventStore instance from app state.

    The store is created during app lifespan startup and stored on
    app.state.event_store.
    """
    return request.app.state.event_store
```

Then in `browser/router.py`, replace inline construction with injection. Current pattern (ad-hoc):

```python
# Current (bad) — browser/router.py line 697
event_store = EventStore(client)
```

Target pattern (DI):

```python
# Target — add to function signature
from app.events.store import EventStore
from app.dependencies import get_event_store

async def save_body(...,
    event_store: EventStore = Depends(get_event_store),
):
    # Remove: event_store = EventStore(client)
    # event_store is now injected
```

The 4 locations to fix are lines 697, 1013, 1120, and 1298. Each has a corresponding `from app.events.store import EventStore` local import that should be removed after moving to DI.

### Pattern 2: Label Cache Invalidation After Commit

After fixing the EventStore DI, each `event_store.commit()` call needs invalidation:

```python
# Source: CONCERNS.md recommendation + labels.py:128
event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)
# ADD: invalidate labels for affected IRIs
label_service.invalidate(event_result.affected_iris)
```

`event_result.affected_iris` is already populated by `EventStore.commit()` — confirmed from existing usage at line 1027 (`operation.affected_iris[0]`).

### Pattern 3: Timezone-Aware Datetime

```python
# Current (bad) — browser/router.py lines 688 and 1111
from datetime import datetime
now_literal = Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
properties[dcterms_modified] = datetime.now().isoformat()

# Fixed
from datetime import datetime, timezone
now_literal = Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)
properties[dcterms_modified] = datetime.now(timezone.utc).isoformat()
```

Only 2 lines need changing. The `from datetime import datetime` is already at line 11 of `browser/router.py` — add `timezone` to that import.

### Pattern 4: CORS with Environment Variable

```python
# Source: config.py pattern for env vars (all settings use pydantic BaseSettings)

# In config.py — add:
cors_origins: str = ""  # comma-separated list; empty = wildcard
cookie_secure: bool = True

# In main.py — replace static CORSMiddleware with:
cors_origins_list = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

The `settings` object is already imported in `main.py` and the CORSMiddleware block is at line 266-272.

### Pattern 5: Debug Endpoint Owner Guard

```python
# Source: debug/router.py lines 11-27 + auth/dependencies.py require_role pattern
# Current:
from app.auth.dependencies import get_current_user

@router.get("/sparql")
async def sparql_page(request: Request, user: User = Depends(get_current_user)):

# Fixed:
from app.auth.dependencies import require_role

@router.get("/sparql")
async def sparql_page(request: Request, user: User = Depends(require_role("owner"))):

@router.get("/commands")
async def commands_page(request: Request, user: User = Depends(require_role("owner"))):
```

`require_role` is already used in `browser/router.py` (line 1072: `Depends(require_role("owner", "member"))`).

### Pattern 6: Cookie Secure Config

```python
# Source: auth/router.py line 47
# Current:
secure=False,  # TODO: make configurable for production

# In config.py add:
cookie_secure: bool = True

# In auth/router.py fix:
from app.config import settings
# ...
secure=settings.cookie_secure,
```

### Pattern 7: Tab Already-Active Guard

The bug: `switchTabInGroup` at line 854 of `workspace-layout.js` calls `loadTabInGroup` even when the tab is already active. Fix is an early return:

```javascript
// Source: workspace-layout.js line 854 (switchTabInGroup)
function switchTabInGroup(tabId, groupId) {
    if (!layout) return;
    var group = layout.getGroup(groupId);
    if (!group) return;

    // ADD: early return if tab is already active
    if (group.activeTabId === tabId) return;  // <-- add this

    group.activeTabId = tabId;
    // ... rest unchanged
}
```

### Pattern 8: IRI Validation

```python
# Source: CONCERNS.md + Python urllib.parse
from urllib.parse import urlparse

def _validate_iri(iri: str) -> bool:
    """Check that a decoded IRI is a valid absolute URI."""
    try:
        result = urlparse(iri)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False

# In each route handler before SPARQL interpolation:
decoded_iri = unquote(object_iri)
if not _validate_iri(decoded_iri):
    raise HTTPException(status_code=400, detail="Invalid IRI")
```

Apply to all 6 locations in `browser/router.py` listed in CONCERNS.md (lines 413, 468, 601, 733, 844, 1332).

### Pattern 9: Tag Pills in Templates

Tag pills are visual-only, scoped to `model:basic-pkm:tags` property path. The property path is the full IRI from the SHACL shape — needs to be checked in a seed model file, but likely `https://example.org/models/basic-pkm/tags` or similar. Implementation uses Jinja2 `if prop.path == 'model:basic-pkm:tags'` check or checks for a prop name match.

In `object_read.html`, add a branch in the `{% else %}` clause for plain string values:

```jinja
{# In object_read.html property value rendering, inside the {% else %} branch for plain values #}
{% elif 'tags' in prop.path %}
  {% for v in vals %}
  <span class="tag-pill">#{{ v }}</span>
  {% if not loop.last %} {% endif %}
  {% endfor %}
{% else %}
  {% for v in vals %}{{ v }}{% if not loop.last %}, {% endif %}{% endfor %}
{% endif %}
```

The pill CSS class should be added to `workspace.css` following the existing design tokens:

```css
.tag-pill {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    background: var(--color-accent-muted, rgba(0, 120, 212, 0.12));
    color: var(--color-accent, #0078d4);
    border: 1px solid var(--color-accent-border, rgba(0, 120, 212, 0.3));
    margin: 2px 2px 2px 0;
    white-space: nowrap;
}
```

### Pattern 10: Tooltip on Nav Tree Items

The graph view tooltip uses `.graph-popover` CSS classes (defined in `views.css:527+`). The nav tree leaf nodes currently have no hover tooltip. The simplest approach is a custom CSS tooltip using `data-tooltip` attribute and a `::after` pseudo-element — the existing pattern in `style.css:857-858` already does this for collapsed sidebar nav links.

For nav tree leaf items, add `title` attribute on the `tree-leaf` div. For a richer tooltip matching the graph popup style, use a JS-driven approach that shows a `.graph-popover`-styled div on `mouseenter` using existing popover CSS.

The tree_children.html currently generates:

```jinja
<div class="tree-leaf" data-testid="nav-item" onclick="openTab('{{ obj.iri }}', '{{ obj.label }}')">
```

To add tooltip with type+label, add `title="{{ obj.type_label }}: {{ obj.label }}"` — this requires `obj.type_label` to be provided from the router. The router `tree_children` endpoint at `browser/router.py` needs to pass type label in the context.

Alternatively (simpler, no backend change): use `title="{{ obj.iri }}"` already available, then style with CSS tooltip.

The CONTEXT.md says "use graph style" — this implies the JS-driven popover approach, not the simple title tooltip.

### Anti-Patterns to Avoid

- **Don't skip or tag the 5 failing setup wizard tests** — document with a code comment instead, per CONTEXT.md
- **Don't construct EventStore ad-hoc after this phase** — always use DI from `dependencies.py`
- **Don't use `datetime.now()` without timezone** — always use `datetime.now(timezone.utc)`
- **Don't set `allow_credentials=True` with `allow_origins=["*"]`** — this violates CORS spec and browsers block it

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL validation | Custom regex | `urllib.parse.urlparse()` | stdlib, handles edge cases |
| CORS configuration | Custom CORS middleware | FastAPI `CORSMiddleware` already in use | Already configured, only env var needed |
| Tooltip styling | New popover component | Existing `.graph-popover` CSS classes in `views.css` | Consistent design, zero new code |
| Tab active guard | Complex state tracking | Single `if group.activeTabId === tabId: return` | Simple equality check is sufficient |

---

## Common Pitfalls

### Pitfall 1: EventStore DI Import Collision
**What goes wrong:** After adding `get_event_store` to function signatures, the inline `from app.events.store import EventStore` local imports (lines 672, 968, 1087, 1287) must be removed, or the module import statement at the top of the file must be added and local imports removed.
**Why it happens:** The EventStore imports are currently done inline inside the handler functions as local imports — unusual pattern for this codebase.
**How to avoid:** When converting to DI, remove all 4 local `from app.events.store import EventStore` imports and add a single top-level import if needed (though with DI, the type annotation just needs `EventStore` from the import already present in `dependencies.py`).
**Warning signs:** `ImportError` or `NameError: name 'EventStore' is not defined` at runtime.

### Pitfall 2: label_service Not in All 4 Write Handler Signatures
**What goes wrong:** Some of the 4 write handlers (lines 697, 1013, 1120, 1298) may not currently have `label_service: LabelService = Depends(get_label_service)` in their signature. Adding invalidation requires the service to be injected.
**Why it happens:** The label service is currently only injected where it is used for read operations.
**How to avoid:** Before adding the `label_service.invalidate()` call to each handler, verify that `label_service` is in the function signature. Add `label_service: LabelService = Depends(get_label_service)` if not present.
**Warning signs:** `NameError: name 'label_service' is not defined` inside the handler.

### Pitfall 3: Split Tab Content Bleed — Identifying the Real Root Cause
**What goes wrong:** `splitRight()` creates a new group and calls `loadTabInGroup(newGroupId, dupTab.id)`. The content ends up in the old group's editor area.
**Why it happens:** Most likely the `htmx.ajax()` call in `loadTabInGroup` uses `target: '#editor-area-' + groupId` but `groupId` resolves to the wrong value at call time — possibly because `setActiveGroup(newGroupId)` at line 805 changes `layout.activeGroupId` before `loadTabInGroup` finishes. Another possibility: DOM rendering order means `#editor-area-groupN` doesn't exist yet when htmx fires.
**How to avoid:** Trace the actual `groupId` parameter passed to `loadTabInGroup` in `splitRight()`. The call is `loadTabInGroup(newGroupId, dupTab.id)` at line 828 — verify `newGroupId` is the new group's id and the DOM element `#editor-area-{newGroupId}` exists before htmx fires.
**Warning signs:** Content appears in the wrong pane after split.

### Pitfall 4: Edit Button First-Touch — IIFE Timing
**What goes wrong:** `toggleObjectMode(safeId, objectIri)` is called, which calls `window['_initEditMode_' + safeId]()`. The function reference is set by an IIFE that runs after the tab HTML loads. If `toggleObjectMode` is called before the IIFE has run, `window['_initEditMode_' + safeId]` is `undefined`.
**Why it happens:** htmx swaps content but the inline script at the bottom of `object_tab.html` may run asynchronously after the first click event fires on the Edit button.
**How to avoid:** In `toggleObjectMode`, add a null check: `var initFn = window['_initEditMode_' + safeId]; if (typeof initFn === 'function') initFn();`. This is already present at line 593-594! The real bug may be elsewhere — check if `safe_id` in the button `onclick="toggleObjectMode('{{ safe_id }}', '{{ object_iri }}')"` matches the `safeId` used in the `window['_initEditMode_' + safeId]` assignment. The `safe_id` is set at the top of `object_tab.html` as `{{ object_iri | urlencode | replace('%', '_') }}`.
**Warning signs:** First click does nothing; second click works — suggests the function is registered by the first click's event handler execution order.

### Pitfall 5: Autocomplete Dropdown Z-Index / Overflow
**What goes wrong:** The `.suggestions-dropdown` renders but is clipped by a parent with `overflow: hidden` or appears behind other elements.
**Why it happens:** The `.object-form-section` container has `overflow-y: auto` per the inline styles in `object_tab.html`. The suggestions dropdown positioned absolutely inside the form section gets clipped.
**How to avoid:** Make `.suggestions-dropdown` use `position: fixed` with coordinates from `getBoundingClientRect()` — this is the pattern already used for autocomplete dropdowns (noted in STATE.md key decisions from 10-02: "position: fixed + getBoundingClientRect for dropdown overflow escape").
**Warning signs:** Dropdown appears briefly then disappears, or is clipped at form section boundary.

### Pitfall 6: E2E Tests Importing from Wrong Fixture
**What goes wrong:** New test files placed in wrong directory, or importing from `../../fixtures/auth` with wrong relative path.
**Why it happens:** The `e2e/tests/` subdirectory structure requires `../../fixtures/` for all test files two levels deep.
**How to avoid:** Follow existing pattern exactly. Ref: `e2e/tests/06-settings/dark-mode.spec.ts` uses `import { test, expect, OWNER_EMAIL, MEMBER_EMAIL } from '../../fixtures/auth'`.
**Warning signs:** TypeScript compilation errors on imports.

### Pitfall 7: CORS_ORIGINS env var must also update docker-compose
**What goes wrong:** Adding `CORS_ORIGINS` to `config.py` but not documenting it in the docker-compose environment section means dev environments continue using wildcard.
**Why it happens:** The env var works but isn't wired into the container.
**How to avoid:** Update `docker-compose.yml` (or `.env.example` if it exists) with a commented-out `CORS_ORIGINS` entry.
**Warning signs:** CORS errors in browser when testing with separate frontend/backend ports.

---

## Code Examples

### Backend: All 4 EventStore DI + Invalidation Locations

```python
# Source: browser/router.py — current ad-hoc pattern to replace (4 locations):
# Line 697 (save_body), 1013 (create_object), 1120 (save_object), 1298 (undo_event)

# Current ad-hoc (remove):
event_store = EventStore(client)

# Replace with DI signature addition + invalidation:
# Add to function signature:
event_store: EventStore = Depends(get_event_store),
label_service: LabelService = Depends(get_label_service),  # if not already present

# After each commit:
event_result = await event_store.commit([operation], performed_by=user_iri, performed_by_role=user.role)
label_service.invalidate(event_result.affected_iris)  # ADD THIS LINE
```

### Python: Datetime UTC Fix

```python
# Source: browser/router.py lines 688 and 1111
# Change line 11: from datetime import datetime
# To:
from datetime import datetime, timezone

# Line 688:
now_literal = Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)

# Line 1111:
properties[dcterms_modified] = datetime.now(timezone.utc).isoformat()
```

### Python: Cookie Secure Config

```python
# Source: config.py + auth/router.py line 47
# In config.py, add to Settings class:
cookie_secure: bool = True

# In auth/router.py, line 47:
secure=settings.cookie_secure,
# Remove the # TODO comment
```

### JavaScript: Tab Active Guard

```javascript
// Source: workspace-layout.js, add to switchTabInGroup() at line 857
function switchTabInGroup(tabId, groupId) {
    if (!layout) return;
    var group = layout.getGroup(groupId);
    if (!group) return;
    if (group.activeTabId === tabId) return;  // ADD: no-op if already active
    // ... rest unchanged
```

### E2E: New Test Pattern (event log coverage)

```typescript
// Source: pattern from e2e/tests/06-settings/settings-page.spec.ts
import { test, expect } from '../../fixtures/auth';
import { waitForWorkspace, waitForIdle } from '../../helpers/wait-for';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901';

test.describe('Event Log', () => {
  test('event log tab loads with event rows', async ({ ownerPage }) => {
    await ownerPage.goto(`${BASE_URL}/browser/`);
    await waitForWorkspace(ownerPage);

    // Open bottom panel (Ctrl+J) and switch to Event Log tab
    await ownerPage.keyboard.press('Control+j');
    await waitForIdle(ownerPage);
    // ... assertions
  });
});
```

---

## Codebase Topology: Files Touched Per Bug

This section maps each bug to the exact files that need changes.

### Backend Bugs (Plan 19-01)

| Bug | Files | Change Type |
|-----|-------|-------------|
| BUG-01: Label cache | `browser/router.py` (4 sites) | Add `label_service.invalidate()` after each commit |
| BUG-02: datetime UTC | `browser/router.py` (line 11, 688, 1111) | `timezone` import + 2 call sites |
| BUG-03: EventStore DI | `dependencies.py`, `browser/router.py` (4 sites) | New dep function + replace inline constructions |
| BUG-04a: CORS | `config.py`, `main.py` (lines 266-272) | New env var + conditional CORSMiddleware setup |
| BUG-04b: Debug auth | `debug/router.py` (lines 11, 20) | `get_current_user` → `require_role("owner")` |
| BUG-05a: IRI validation | `browser/router.py` (6 sites per CONCERNS.md) | Add `_validate_iri()` helper + check before each SPARQL interpolation |
| BUG-05b: Cookie secure | `config.py`, `auth/router.py` (line 47) | New env var + use `settings.cookie_secure` |

### UI Bugs (Plan 19-02)

| Bug | Files | Change Type |
|-----|-------|-------------|
| Tab reload on click | `frontend/static/js/workspace-layout.js` | Add `if (group.activeTabId === tabId) return;` to `switchTabInGroup` |
| Split tab content bleed | `frontend/static/js/workspace-layout.js` | Debug `splitRight()` — verify `newGroupId` and DOM timing |
| Edit button first touch | `frontend/static/js/workspace.js` | Diagnose `toggleObjectMode`/`_initEditMode_` timing; may be a safe_id encoding issue |
| Autocomplete dropdown | `frontend/static/js/workspace.js` or CSS | Fix `position:fixed` + `getBoundingClientRect()` for dropdown per STATE.md pattern 10-02 |
| Docs tab link | `frontend/static/js/workspace.js` or `workspace-layout.js` | Fix `openDocsTab` or nav link handler |
| Tutorial launch | `backend/app/templates/browser/docs_page.html` | Fix `window.startWelcomeTour`/`startCreateObjectTour` availability at click time |
| Tag pills | `backend/app/templates/browser/object_read.html`, CSS | Add `tag-pill` class conditional rendering for `tags` property |
| Tooltips | `backend/app/templates/browser/tree_children.html`, CSS or JS | Add hover tooltip (type + label) on nav tree items |

### E2E Tests (Plan 19-03)

| Coverage Gap | New File | Tests to Add |
|-------------|----------|-------------|
| Event log | `e2e/tests/03-navigation/event-log.spec.ts` or `e2e/tests/` appropriate dir | Panel opens, events render, filter works |
| Split panes | `e2e/tests/03-navigation/split-panes.spec.ts` | Ctrl+\\ creates split, tabs independent |
| Tutorial launch | `e2e/tests/07-multi-user/` or new dir | Docs tab opens, tutorial button visible |
| Setup wizard docs | `e2e/tests/00-setup/01-setup-wizard.spec.ts` | Add comment about infrastructure constraint |

---

## Open Questions

1. **Exact root cause of edit button first-touch bug**
   - What we know: `toggleObjectMode` calls `window['_initEditMode_' + safeId]` which is set by an IIFE at end of `object_tab.html`; the check `if (typeof initFn === 'function') initFn()` is present at line 593-594
   - What's unclear: Whether the bug is actually a safe_id encoding mismatch (urlencode produces `%3A` for `:`, then `replace('%', '_')` produces `_3A`) vs the button's onClick calling with a different safeId encoding
   - Recommendation: During implementation, add a `console.log` to verify the `safeId` in the button matches the key in `window` object

2. **Exact root cause of split tab content bleed**
   - What we know: `splitRight()` at line 795-831 creates a new group and calls `loadTabInGroup(newGroupId, dupTab.id)` which uses `htmx.ajax` targeting `#editor-area-{newGroupId}`
   - What's unclear: Whether the DOM element `#editor-area-{newGroupId}` exists when htmx fires (it's created by `recreateGroupSplit()`), or whether `setActiveGroup` at line 805 causes the old group to get focus and then htmx targets its editor area
   - Recommendation: Check whether `recreateGroupSplit()` is called synchronously before `loadTabInGroup`, verify DOM state

3. **Tag property path for model:basic-pkm:tags**
   - What we know: The property path in the SHACL form will be the full IRI, not the prefixed form
   - What's unclear: The exact IRI string (likely `https://example.org/models/basic-pkm/tags` or `model:basic-pkm:tags` expanded)
   - Recommendation: Inspect the Basic PKM model's SHACL shapes file to get the exact path, or match on the property name "Tags" rather than the IRI

4. **Docs tab opening bug — what's broken**
   - What we know: `docs_page.html` template exists and has `hx-get` calls for guide chapters; there's an `openDocsTab` function referenced in `workspace-layout.js` (line 726 handles `special:docs`)
   - What's unclear: Whether the nav link to open the docs tab is broken, or whether the docs tab content itself errors
   - Recommendation: Trace the nav sidebar link for "Docs & Tutorials" to see if `openDocsTab` or `openTab('special:docs', ...)` is called correctly

---

## Validation Architecture

> nyquist_validation is not set in .planning/config.json (no `workflow.nyquist_validation` key) — skipping this section per instructions.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `backend/app/browser/router.py` — all 4 EventStore ad-hoc constructions confirmed at lines 697, 1013, 1120, 1298
- Direct codebase inspection: `backend/app/browser/router.py` — datetime.now() at lines 688, 1111
- Direct codebase inspection: `backend/app/dependencies.py` — EventStore not present, pattern confirmed from existing deps
- Direct codebase inspection: `backend/app/main.py:85-86` — `app.state.event_store` already set in lifespan
- Direct codebase inspection: `backend/app/debug/router.py` — uses `get_current_user` not `require_role`
- Direct codebase inspection: `backend/app/main.py:266-272` — CORS wildcard + credentials confirmed
- Direct codebase inspection: `backend/app/config.py` — no `cors_origins` or `cookie_secure` fields
- Direct codebase inspection: `backend/app/auth/router.py:47` — `secure=False` hardcoded
- Direct codebase inspection: `backend/app/services/labels.py:128` — `invalidate()` exists and is correct
- Direct codebase inspection: `frontend/static/js/workspace-layout.js:854-867` — `switchTabInGroup` loads without active-tab guard
- Direct codebase inspection: `frontend/static/js/workspace-layout.js:795-831` — `splitRight()` code
- Direct codebase inspection: `e2e/playwright.config.ts` — chromium project, single worker, retries: 1
- Direct codebase inspection: `e2e/tests/` — existing test files mapped
- `MEMORY.md` — 118/123 pass baseline confirmed

### Secondary (MEDIUM confidence)
- `.planning/codebase/CONCERNS.md` — authoritative audit of all bugs; line numbers verified against actual code
- `.planning/phases/19-bug-fixes-and-e2e-test-hardening/19-CONTEXT.md` — user decisions locked

### Tertiary (LOW confidence)
- Root causes of edit-button first-touch and split-tab bleed bugs — diagnosis is based on code reading, not runtime verification; exact fix requires implementation-time debugging

---

## Metadata

**Confidence breakdown:**
- Backend bugs (BUG-01, BUG-02, BUG-03, BUG-04): HIGH — exact file locations and line numbers confirmed from codebase inspection; patterns are clear
- Frontend bugs (BUG-05): MEDIUM — code paths identified but root cause of edit-button and split-bleed bugs needs runtime verification
- E2E hardening (TEST-01, TEST-02): HIGH — existing infrastructure understood; new test files follow confirmed patterns
- Tag pills / tooltips: HIGH — exact template locations confirmed; implementation pattern clear from existing code

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (codebase is stable; bugs are well-understood; 30-day window appropriate)