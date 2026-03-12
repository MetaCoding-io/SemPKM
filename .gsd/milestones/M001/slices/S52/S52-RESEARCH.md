# Phase 52: Bug Fixes & Security - Research

**Researched:** 2026-03-09
**Domain:** SPARQL role gating, event log compound event display, CSS layout fixes
**Confidence:** HIGH

## Summary

Phase 52 addresses three distinct concerns: (1) SPARQL role-based access control, (2) event log rendering bugs for compound events and missing undo for object.create, and (3) lint dashboard filter layout overflow. All three have well-understood code paths, established patterns to follow, and clear success criteria.

The SPARQL gating is the most architecturally significant change. The existing `require_role()` dependency is a proven pattern used in admin routes, and the `scope_to_current_graph()` function already handles graph isolation. The fix requires adding role checks at three layers: API endpoint access, `all_graphs` parameter gating, and SPARQL clause detection for members. The event log compound event issue stems from how `EventStore.commit()` joins multiple operation types with commas (e.g., `"body.set,object.create"`) but templates only match single operation types. The lint dashboard fix is a straightforward CSS change.

**Primary recommendation:** Fix in order: lint CSS (simplest, builds confidence), event log compound display + undo, then SPARQL role gating (most impactful, needs E2E test updates).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Guest:** No SPARQL access. Hide the SPARQL console tab entirely from the bottom panel (don't render the tab).
- **Member:** SPARQL access to current materialized graph only. `all_graphs` parameter rejected -- no toggle shown. If member tries to use `FROM` or `GRAPH` clauses targeting event/named graphs, return 403 Forbidden.
- **Owner:** Full SPARQL access including `all_graphs=true`. No restrictions.
- **Error handling:** Always return HTTP 403 for any SPARQL permission violation (no differentiated status codes).
- **Implementation pattern:** Use existing `require_role()` dependency from `auth/dependencies.py` -- proven pattern used in admin routes.
- **Compound events:** Display as "object.create" (primary action) with an expandable detail section showing that body was also set.
- **Undo for object.create:** Implement via a compensating event that soft-archives the object (not hard delete). The undo creates an explicit compensating event preserving the audit trail -- data is hidden, not destroyed.
- **Lint dashboard fix:** Remove hard-coded `200px` on search input. Make filter controls responsive with `flex-wrap: wrap` so they flow to a second line on narrow viewports.
- **Standing requirements:** Every wave/phase must update E2E tests and user guide if user-visible behavior changes.

### Claude's Discretion
- Exact CSS values for filter control sizing
- How to detect the "primary" operation in compound event types
- Soft-archive implementation details (RDF predicate choice, UI indicator)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPARQL-01 | SPARQL queries are gated by role -- guest has no access, member queries current graph only, owner queries all graphs | `require_role()` dependency pattern, `scope_to_current_graph()` utility, `_execute_sparql()` function, admin SPARQL page template, sidebar template, workspace bottom panel template |
| FIX-01 | Event log diffs render correctly for all operation types | Event store `commit()` compound type format, `event_detail.html` template branching, `build_compensation()` function, `event_log.html` operation type badges and undo button guards |
| FIX-02 | Lint dashboard controls display at correct width on all viewports | `.lint-dashboard-filters` CSS in `workspace.css` lines 3563-3594, lint_dashboard.html template |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | API endpoints, dependency injection | Already used; `Depends(require_role())` is the access control pattern |
| Jinja2 | existing | Server-side templates, conditional rendering | Already used for all HTML partials |
| htmx | existing | Dynamic HTML swaps in bottom panel | Already used for event log, lint dashboard |
| rdflib | existing | RDF triple construction for compensation events | Already used in event store |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| difflib | stdlib | Unified diff computation | Already used in `_compute_body_diff()` for body.set events |
| Yasgui (@zazuko/yasgui) | 4.5.0 | SPARQL editor (admin page) | No changes needed -- CDN loaded in `admin/sparql.html` |
| Playwright | existing | E2E test verification | Existing tests in `e2e/tests/05-admin/` and `e2e/tests/10-lint-dashboard/` |

### Alternatives Considered
None -- all changes use existing stack. No new libraries needed.

## Architecture Patterns

### Affected File Map
```
backend/app/
  auth/dependencies.py       # require_role() -- reference, no changes needed
  sparql/router.py            # Add role checks to GET/POST /api/sparql
  sparql/client.py            # Add SPARQL clause detection for member restriction
  events/query.py             # Add compound type parsing, object.create undo
  events/store.py             # Reference: commit() compound type format (line 126)
  browser/router.py           # Update undo endpoint to handle object.create
  admin/router.py             # Gate admin/sparql page by role

backend/app/templates/
  browser/event_detail.html   # Add compound event handling branch
  browser/event_log.html      # Update badge display + undo button guard for compound types
  browser/workspace.html      # Conditionally render SPARQL tab based on user.role
  components/_sidebar.html    # Conditionally show admin SPARQL link based on user.role

frontend/static/css/
  workspace.css               # Fix lint-dashboard-filters layout (lines 3563-3594)

e2e/tests/
  05-admin/sparql-console.spec.ts  # Existing -- may need role-gating tests
```

### Pattern 1: SPARQL Role Gating
**What:** Three-layer access control on SPARQL API and UI.
**When to use:** For any endpoint that needs differentiated behavior by role.

Layer 1 -- API endpoint access:
```python
# In sparql/router.py: replace get_current_user with role-aware dependency
@router.get("/sparql")
async def sparql_get(
    query: str = Query(...),
    all_graphs: bool = Query(False),
    user: User = Depends(get_current_user),  # Keep basic auth
    client: TriplestoreClient = Depends(get_triplestore_client),
) -> Response:
    # Guest check: role == "guest" -> 403
    if user.role == "guest":
        raise HTTPException(status_code=403, detail="SPARQL access denied")
    # Member check: reject all_graphs
    if user.role == "member" and all_graphs:
        raise HTTPException(status_code=403, detail="Requires owner role for all_graphs")
    # Member check: detect FROM/GRAPH clauses targeting non-current graphs
    if user.role == "member":
        _check_member_query_safety(query)
    return await _execute_sparql(query, client, all_graphs=all_graphs)
```

Layer 2 -- Query clause detection for members:
```python
# In sparql/client.py or sparql/router.py
import re
def _check_member_query_safety(query: str):
    """Reject queries with FROM or GRAPH clauses that escape current graph scope."""
    upper = query.upper()
    # FROM clauses let users target arbitrary graphs
    if re.search(r'\bFROM\s+', upper):
        raise HTTPException(status_code=403, detail="FROM clauses not allowed for member role")
    # GRAPH clauses let users access event graphs
    if re.search(r'\bGRAPH\s+', upper):
        raise HTTPException(status_code=403, detail="GRAPH clauses not allowed for member role")
```

Layer 3 -- UI conditional rendering:
```html
{# In workspace.html: conditionally render SPARQL bottom panel tab #}
{% if user.role != 'guest' %}
  <button class="panel-tab" data-panel="sparql-console">SPARQL</button>
{% endif %}

{# In _sidebar.html: conditionally show admin SPARQL link #}
{% if user.role == 'owner' %}
  <a href="/admin/sparql" ...>SPARQL Console</a>
{% endif %}
```

### Pattern 2: Compound Event Type Handling
**What:** Parse comma-separated operation types and display the primary action.
**When to use:** When rendering events that were committed as batched operations.

The `EventStore.commit()` stores compound types as: `",".join(sorted(all_operation_types))` (store.py line 126). Example: `"body.set,object.create"` when object creation includes a body.

Primary operation detection (Claude's discretion):
```python
# Priority order: the most significant action is the "primary" one
OPERATION_PRIORITY = [
    "object.create",
    "object.patch",
    "body.set",
    "edge.create",
    "edge.patch",
    "edge.create.undo",
]

def get_primary_operation(op_type_str: str) -> tuple[str, list[str]]:
    """Return (primary_op, secondary_ops) from a potentially compound op string."""
    parts = [p.strip() for p in op_type_str.split(",")]
    if len(parts) == 1:
        return parts[0], []
    for candidate in OPERATION_PRIORITY:
        if candidate in parts:
            others = [p for p in parts if p != candidate]
            return candidate, others
    return parts[0], parts[1:]
```

### Pattern 3: Object.create Undo via Soft-Archive
**What:** Compensating event that removes all triples for the object from current state.
**When to use:** Extending `build_compensation()` to handle `object.create`.

Soft-archive approach (Claude's discretion on RDF predicate):
```python
# In events/query.py build_compensation():
elif op_type == "object.create" or (
    "object.create" in op_type  # Handle compound types
):
    if not subject_iri or not detail.data_triples:
        return None
    # Build materialize_deletes for ALL triples of this subject in current state
    materialize_deletes = []
    for s_str, p_str, o_str in detail.data_triples:
        s = URIRef(s_str)
        p = URIRef(p_str)
        o = URIRef(o_str) if o_str.startswith(("http", "urn")) else Literal(o_str)
        materialize_deletes.append((s, p, o))
    return Operation(
        operation_type="object.create.undo",
        affected_iris=detail.summary.affected_iris,
        description=f"Undo object.create: {event_iri}",
        data_triples=[],
        materialize_inserts=[],
        materialize_deletes=materialize_deletes,
    )
```

### Anti-Patterns to Avoid
- **Hard-deleting on undo:** CONTEXT.md explicitly requires soft-archive via compensating event. Never DELETE the event graph or bypass event sourcing.
- **Client-side SPARQL filtering:** Do not rely on JavaScript to hide SPARQL features. The API layer must enforce 403 -- UI hiding is defense-in-depth only.
- **Matching compound operation types with `==`:** The template currently uses `== 'object.create'` etc. Compound types like `"body.set,object.create"` will never match. Use `in` or parse the comma-separated string.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Role checking | Custom role middleware | `require_role()` from `auth/dependencies.py` | Already handles 403, tested, used in admin routes |
| SPARQL clause detection | Full SPARQL parser | Regex on `FROM` and `GRAPH` keywords | The existing `scope_to_current_graph()` uses the same regex approach; a full parser would be overkill |
| Event diff rendering | Custom diff algorithm | `difflib.unified_diff` (already used in `_compute_body_diff()`) | Proven, handles edge cases |
| CSS responsive layout | JavaScript resize listener | `flex-wrap: wrap` with `min-width` | Pure CSS solution, no JS needed |

**Key insight:** All three fixes extend established patterns rather than introducing new infrastructure. The compound event bug is a display issue (template + query service), not a data model issue.

## Common Pitfalls

### Pitfall 1: Compound Operation Type String Matching
**What goes wrong:** Template `if` checks like `== 'object.create'` fail for compound types like `"body.set,object.create"`.
**Why it happens:** `EventStore.commit()` joins sorted operation types with commas. When object creation includes body content, the stored type is `"body.set,object.create"`.
**How to avoid:** Parse the comma-separated string in the query service or add Jinja2 filters that use `in` instead of `==`. Apply to both `event_detail.html` (diff rendering) and `event_log.html` (badge display, diff button, undo button).
**Warning signs:** Events that show no badge color, disabled diff button, disabled undo button despite being object.create events.

### Pitfall 2: SPARQL FROM/GRAPH Clause Bypass
**What goes wrong:** A member user could craft a query with `FROM <urn:sempkm:event:...>` to read event graph data that should be hidden.
**Why it happens:** `scope_to_current_graph()` skips injection when `FROM` is already present (client.py line 53), trusting the user's explicit FROM clause.
**How to avoid:** For members, check for FROM/GRAPH clauses BEFORE calling `scope_to_current_graph()` and return 403. The current-graph scoping function does not need changes -- just add a pre-check.
**Warning signs:** Members seeing event graph data, internal system triples, or triples from named graphs other than `urn:sempkm:current` and `urn:sempkm:inferred`.

### Pitfall 3: Admin SPARQL Page Still Accessible to Non-Owners
**What goes wrong:** The admin SPARQL page at `/admin/sparql` currently uses `get_current_user` (line 839 of admin/router.py), not `require_role("owner")`. Any authenticated user can access it.
**Why it happens:** The admin page was added before role gating was planned. Unlike the debug SPARQL page (which uses `require_role("owner")`), the admin one was left open.
**How to avoid:** Change the admin/sparql endpoint to use `require_role("owner", "member")` with the same logic that restricts members from all_graphs. Or simpler: keep the page accessible but the Yasgui endpoint (`/api/sparql`) enforces role at the API layer, so the page would show errors for guests anyway. Hide the sidebar link for guests.

### Pitfall 4: Workspace Template User Object
**What goes wrong:** Trying to access `user.role` in workspace.html but the variable not being available.
**Why it happens:** Forgetting to check if user is already in the template context.
**How to avoid:** The `workspace()` route at browser/router.py line 471 already passes `"user": user` in the context. The `user.role` field is a string: `"owner"`, `"member"`, or `"guest"`. Safe to use in Jinja2 conditionals.
**Warning signs:** Jinja2 `UndefinedError` on `user.role`.

### Pitfall 5: CSS `width: 200px` Not Responsive
**What goes wrong:** The search input's hard-coded `width: 200px` (workspace.css line 3582) causes it to overflow or force other controls off-screen on narrow viewports.
**Why it happens:** The parent `.lint-dashboard-filters` is `display: flex` without `flex-wrap: wrap`, so all items must fit in one line.
**How to avoid:** Remove `width: 200px`, add `flex: 1; min-width: 120px;` to the search input, and add `flex-wrap: wrap` to the parent container.

## Code Examples

### Existing: require_role() Usage (admin routes)
```python
# Source: backend/app/admin/router.py — proven pattern
@router.get("/models")
async def admin_models(
    request: Request,
    user: User = Depends(require_role("owner")),
):
    ...
```

### Existing: scope_to_current_graph() Bypass Detection
```python
# Source: backend/app/sparql/client.py lines 49-58
# Already checks for FROM/GRAPH clauses:
upper = query.upper()
if re.search(r'\bFROM\s+', upper):
    return query  # User explicitly controls scope
if CURRENT_GRAPH in query:
    return query  # Already scoped
```

### Existing: EventStore Compound Type Generation
```python
# Source: backend/app/events/store.py lines 105-128
all_operation_types: set[str] = set()
for op in operations:
    all_operation_types.add(op.operation_type)
combined_ops = ",".join(sorted(all_operation_types))
# Example output: "body.set,object.create"
```

### Existing: event_log.html Badge and Button Guards
```html
<!-- Source: backend/app/templates/browser/event_log.html lines 54, 76-88 -->
<!-- Badge uses replace('.', '-') for CSS class: -->
<span class="event-op-badge event-op-{{ event.operation_type | replace('.', '-') }}">
  {{ event.operation_type }}
</span>

<!-- Diff button guard: checks exact string match -->
{% if event.operation_type in ['object.patch', 'body.set', 'object.create', 'edge.create', 'edge.patch'] %}
  <button class="event-btn-diff" ...>Diff</button>
{% endif %}

<!-- Undo button guard: does NOT include object.create -->
{% if event.operation_type in ['object.patch', 'body.set', 'edge.create', 'edge.patch'] %}
  <button class="event-btn-undo" ...>Undo</button>
{% endif %}
```

### Existing: event_detail.html Operation Type Branching
```html
<!-- Source: backend/app/templates/browser/event_detail.html lines 3, 22, 58 -->
{% if detail.summary.operation_type == 'body.set' and detail.body_diff %}
  {# body diff view #}
{% elif detail.new_values %}
  {# property table for object.patch, edge.patch #}
{% elif detail.summary.operation_type == 'object.create' or detail.summary.operation_type == 'edge.create' %}
  {# creation view: show triples #}
{% else %}
  <div class="diff-no-data">No diff data available for this event type.</div>
{% endif %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No SPARQL role gating | `get_current_user` on /api/sparql | Current state | Any authenticated user can query any graph |
| Single operation events only | Compound operation types via comma-join | Phase ~16 (event store) | Templates don't handle compound types |
| Fixed-width lint controls | `width: 200px` on search input | Phase ~30 | Overflow on narrow viewports |

**Not deprecated/outdated -- just bugs to fix:**
- Compound event type display has never worked correctly since batch commands were introduced
- The undo button for object.create was intentionally omitted initially but is now needed
- The lint dashboard layout was correct at wider viewports but never tested at narrow ones

## Open Questions

1. **SPARQL Bottom Panel Tab**
   - What we know: The workspace bottom panel (workspace.html lines 62-101) currently has tabs for EVENT LOG, INFERENCE, AI COPILOT, and LINT. There is NO existing SPARQL tab in the bottom panel.
   - What's unclear: CONTEXT.md says "Hide the SPARQL console tab entirely from the bottom panel" for guests. But there is currently no SPARQL tab in the bottom panel at all.
   - Recommendation: The SPARQL console is only at `/admin/sparql` (admin page) and the sidebar link. Hide the sidebar link for guests. The bottom panel statement may be anticipating a future SPARQL tab that does not yet exist. For now, gate the admin page and API endpoint. If the planner wants a bottom panel SPARQL tab, that would be new feature work beyond the bug fix scope.

2. **Soft-Archive RDF Predicate**
   - What we know: CONTEXT.md says undo for object.create should "soft-archive" the object, not hard delete.
   - What's unclear: The simplest implementation removes all triples from the materialized state graph via `materialize_deletes`. The data still exists in the event graph (immutable). This effectively "hides" the object while preserving the full audit trail.
   - Recommendation: Use `materialize_deletes` to remove from current state. This IS soft-archive -- the event graph retains the creation data and a future "redo" could re-materialize. No need for a separate archive predicate unless the user wants archived objects to remain queryable (which was not specified).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (E2E), pytest + pytest-asyncio (backend unit) |
| Config file | `e2e/playwright.config.ts`, `backend/pyproject.toml` |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/05-admin/sparql-console.spec.ts` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPARQL-01 | Guest cannot access /api/sparql | E2E | `npx playwright test tests/05-admin/sparql-console.spec.ts` | Exists but needs role-gating cases |
| SPARQL-01 | Member rejected for all_graphs | E2E | Same file, new test case | Needs new test case |
| SPARQL-01 | Member rejected for FROM/GRAPH clauses | E2E | Same file, new test case | Needs new test case |
| SPARQL-01 | Owner has full access | E2E | Existing test passes | Exists (tests run as owner) |
| SPARQL-01 | Admin SPARQL page hidden from guests | E2E | New test | Needs new test case |
| FIX-01 | Compound event shows correct badge | E2E | `npx playwright test tests/06-settings/event-log.spec.ts` | Exists but needs compound case |
| FIX-01 | Compound event diff renders | E2E | Same file, new test case | Needs new test case |
| FIX-01 | object.create undo works | E2E | Same file, new test case | Needs new test case |
| FIX-02 | Lint filter controls wrap on narrow viewport | E2E/manual | `npx playwright test tests/10-lint-dashboard/lint-dashboard.spec.ts` | Exists, may verify via resize |

### Sampling Rate
- **Per task commit:** `npx playwright test --project=chromium tests/05-admin/ tests/06-settings/ tests/10-lint-dashboard/`
- **Per wave merge:** `npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `e2e/tests/05-admin/sparql-console.spec.ts` -- needs role-gating test cases (guest 403, member restrictions)
- [ ] `e2e/tests/06-settings/event-log.spec.ts` -- needs compound event display test + undo test
- [ ] `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` -- needs narrow viewport resize test for FIX-02

Note: E2E test files cannot be modified per project conventions (tests are sequential, 1 worker). New test cases should be added as new test blocks within existing spec files, or as new spec files in the appropriate directory.

## Sources

### Primary (HIGH confidence)
- `backend/app/auth/dependencies.py` -- `require_role()` implementation (lines 87-107)
- `backend/app/sparql/router.py` -- current SPARQL GET/POST endpoints (lines 77-125)
- `backend/app/sparql/client.py` -- `scope_to_current_graph()` and `inject_prefixes()` (lines 19-101)
- `backend/app/events/store.py` -- `EventStore.commit()` compound type generation (lines 104-128)
- `backend/app/events/query.py` -- `build_compensation()` and `EventQueryService` (full file)
- `backend/app/templates/browser/event_detail.html` -- diff rendering template (full file)
- `backend/app/templates/browser/event_log.html` -- event log timeline template (full file)
- `backend/app/templates/browser/workspace.html` -- bottom panel structure (lines 62-101)
- `backend/app/templates/components/_sidebar.html` -- admin SPARQL link (line 37)
- `backend/app/admin/router.py` -- admin SPARQL page handler (lines 838-848)
- `frontend/static/css/workspace.css` -- lint dashboard CSS (lines 3542-3685)
- `backend/app/auth/models.py` -- User model, role field (line 27)

### Secondary (MEDIUM confidence)
- `e2e/tests/05-admin/sparql-console.spec.ts` -- existing SPARQL E2E tests
- `e2e/tests/06-settings/event-log.spec.ts` -- existing event log E2E tests
- `e2e/tests/10-lint-dashboard/lint-dashboard.spec.ts` -- existing lint dashboard E2E tests

### Tertiary (LOW confidence)
None -- all findings are from direct codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all changes use existing libraries and patterns; no new dependencies
- Architecture: HIGH -- all file paths, function signatures, and template structures verified by reading source
- Pitfalls: HIGH -- compound type format verified from EventStore.commit() source; CSS values read from workspace.css

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable codebase, no external dependencies changing)