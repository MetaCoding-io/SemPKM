# Holonic Concepts → SemPKM: Revised Feasibility

## Context

Originally this plan compared Kurt Cagle's four-graph holon model to SemPKM and recommended "projection views" + "scoped hierarchy" as the two holonic ideas worth adopting. The user pushed back on two assumptions:

1. **"Single-user PKM"** was wrong — SemPKM has a federation layer (`backend/app/federation/service.py`) where users sync named graphs to each other with per-user WebID-based access control. Multi-user/multi-org benefits of holonic boundaries DO apply.
2. **"Projection views need new infrastructure"** was wrong — SemPKM already has a full saved-query system (`backend/app/sparql/query_service.py`) with CRUD, sharing, history, and a **promote-to-view** endpoint (`/sparql/saved/{id}/promote` in `backend/app/sparql/router.py:713`). What's actually missing is narrower than I claimed.

This revision reframes the holonic features as two small, orthogonal extensions to existing systems rather than a new subsystem.

---

## What Actually Exists Today

| Capability | File | Status |
|---|---|---|
| Saved SPARQL queries (CRUD, share, fork) | `backend/app/sparql/query_service.py` | Full |
| Saved-query to promoted-view pipeline | `backend/app/sparql/router.py:713` | Full |
| ViewSpec (class-scoped views in mental models) | `backend/app/views/service.py` | Full |
| Generic table/card/graph renderers | `backend/app/views/service.py:218` | Full |
| Federation / named-graph sync between users | `backend/app/federation/service.py` | Full |
| `dcterms:isPartOf` hierarchy explorer | `backend/app/browser/workspace.py:126` | Full |
| Mount scope filters (`build_scope_filter`) | `backend/app/browser/workspace.py:420` | Full |
| **Query parameterization (e.g., `?focus`)** | — | **Gap** |
| **Object-level view picker (markdown / custom / …)** | `backend/app/templates/browser/object_tab.html` | **Gap** |
| **"Scope workspace into this object"** UI state | — | **Gap** |

---

## Direct Response to the User's Proposals

### "Couldn't parameterized saved queries = projection views?"

**Yes — almost entirely.** A saved query that accepts `?focus` (the current object's IRI) and is promoted to a view IS a projection. The only missing ingredient is:

1. A small convention in `query_service.py` for binding metadata (e.g. `sempkm:vocab:parameter ?focus`) and substitution (prepending `VALUES ?focus { <iri> }` at execution, or a binding map passed to the triplestore).
2. The view execution path in `backend/app/views/service.py` needs to accept an optional `context_iri` and forward it as a pre-bound variable to the query.

Everything else — storage, promotion, rendering, sharing — reuses what's there.

### "Couldn't per-object view selection replace scoped hierarchy?"

**Largely, yes.** If an object can be opened under a chosen view, and the view is a parameterized query receiving that object's IRI, then "Project Summary View" = a query over tasks/notes/references where `?x dcterms:isPartOf+ ?focus`. No new boundary/membrane machinery needed — just transitive-closure in the query.

What this does NOT cover (and where a tiny bit of extra state helps):

- **Workspace-wide scoping**: "pin this object as the root; everything in explorer, search, new-object parenting is now scoped to its descendants." That's a per-session UI state flag (`scoped_root_iri`) read by `workspace.py` hierarchy query and the new-object form. Small — one field in the session-state JSON plus a banner + "exit scope" button.

### "Over-engineering for single-user" — withdrawn

Federation is real. Multi-user sync of named graphs means boundary semantics (what gets synced, what stays private, what validation applies across the boundary) DO become architecturally relevant. SHACL-as-membrane on federated named graphs is a legitimate future direction — though still out of scope for the current tier.

---

## Revised Recommendation

**One small feature, two places to wire it, that delivers both "projection views" and most of "scoped hierarchy":**

### Feature: Parameterized Views with Object Context

Extend saved queries with a parameter declaration, extend ViewSpec execution with a context binding, and add a view picker to the object tab.

### Files to modify

| File | Change |
|---|---|
| `backend/app/sparql/query_service.py` | Add `parameters: list[str]` to `SavedQueryData` + `PromotedViewData`. Store via `sempkm:vocab:parameter` predicate. Add `substitute_bindings(query_text, bindings)` helper that prepends `VALUES (?p1 ?p2) { (<v1> <v2>) }`. |
| `backend/app/views/service.py` | Extend `ViewSpec` with `parameters: list[str]`. Add `execute_spec(spec, context_iri=None)` path that resolves `?focus` binding via the helper above. |
| `backend/app/views/router.py` | Accept `?focus=<iri>` query param; pass through to `execute_spec`. |
| `backend/app/browser/objects.py` (around `GET /object/{iri}`) | Load `available_views` filtered by those whose parameters ⊆ `{?focus}` or whose `target_class` matches object types. Render picker. |
| `backend/app/templates/browser/object_tab.html` | Add view-picker dropdown next to Edit button. Default option = "Markdown / Properties" (current behavior). Selecting a custom view HTMX-swaps the read face with the rendered view, passing `?focus=<object_iri>`. |
| `backend/app/browser/workspace.py` (optional scoped-root) | Honor session `scoped_root_iri`: in `_handle_hierarchy()` change root filter from "no parent" to "parent = scoped_root"; in new-object form default `dcterms:isPartOf = scoped_root`. |

### Reused existing functions — do not re-invent

- `QueryService.save_query`, `get_query`, `promote_to_view` — `backend/app/sparql/query_service.py`
- `ViewSpecService.get_all_view_specs`, `register_generic_views`, `get_generic_spec` — `backend/app/views/service.py`
- `scope_to_current_graph` — `backend/app/sparql/client.py`
- `build_scope_filter` — `backend/app/browser/workspace.py:420` (already does `dcterms:isPartOf*` descendants filtering for mounts; reuse for scoped-root)
- Existing flip-card mechanics in `workspace.js` + `workspace.css` — the view picker just replaces the read-face body; no new flip machinery needed
- `LabelService` for picker dropdown labels

### What we deliberately do NOT build

- No per-entity named graphs. The flat `urn:sempkm:current` graph stays.
- No SHACL-as-membrane enforcement. SHACL continues to drive forms and async validation.
- No Projection Graph materialization. Projections are computed on-demand by parameterized queries; if perf becomes an issue later, memoize results in a cache graph.
- No Portal abstraction. Hyperlinks + the view picker cover the "navigate into a holon" UX.

---

## Verification

1. **Unit** — given a saved query with `?focus` declared, calling `substitute_bindings(query, {"focus": "<urn:sempkm:object:abc>"})` produces a query that binds `?focus` and still parses. Test with the triplestore in the dev stack.
2. **Integration** — create a saved query `SELECT ?child ?label WHERE { ?child dcterms:isPartOf+ ?focus ; rdfs:label ?label }`, promote it to a view, then `GET /object/<iri>?view=<view_iri>` and confirm the response renders children of that object.
3. **UI (browser, no rebuild needed — volume-mounted)**:
   - Open any object with children; confirm view picker shows "Markdown/Properties" + promoted views that declare `?focus`.
   - Select the custom view; confirm read-face content swaps via HTMX without the flip animation firing (it's a content swap, not a mode flip).
   - Confirm object without `?focus`-compatible views shows only the default picker entry.
4. **Federation regression** — sync a promoted parameterized view to a peer via federation, open an object on the peer, confirm the view runs against the peer's local data with the peer's object IRI.
5. **Scoped-root (if implemented)** — click "Scope into this object" on a parent; confirm explorer root filter, new-object parent default, and scope banner all update; click "Exit scope" and confirm reversion.

---

## Sources

- [The Living Graph: Holons and the Four-Graph Model — Kurt Cagle](https://ontologist.substack.com/p/the-living-graph-holons-and-the-four)
- [Holons, Boundaries, and Context Graphs: From Koestler to SHACL — Kurt Cagle](https://ontologist.substack.com/p/holons-boundaries-and-context-graphs)
- [HOLONS: A New Hope — Kurt Cagle](https://ontologist.substack.com/p/a-new-hope)
- [Holon (philosophy) — Wikipedia](https://en.wikipedia.org/wiki/Holon_(philosophy))
