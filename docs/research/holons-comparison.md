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

### Feature: Parameterized Views with Object Context, plus a "Lens" navigation mode

Extend saved queries with a parameter declaration, extend ViewSpec execution with a context binding, add a view picker to the object tab, and add a workspace-wide "Lens" mode that scopes the entire UI to a chosen object's sub-holarchy.

### User-Facing Terminology

- **Lens** — the user-facing term for what a developer might call a "holon scope." Works as a noun ("You are viewing through the lens of Project Alpha") and as a verb ("View through this lens").
- Breadcrumb shows the lens stack: `Home › Research › Project Alpha`.
- The SPARQL binding for parameterized views is `?lens` (the IRI of the object the lens is focused on).
- "Holon" stays in developer docs only.

### Which Objects Can Be a Lens?

**Class-declared with implicit fallback.** An ontology class can assert `sempkm:focusable true` (predicate TBD under `urn:sempkm:vocab:`) to declare that its instances can be viewed through. If no class in any installed model declares focusability, fall back to "any object that has `dcterms:isPartOf` incoming edges is focusable." This lets `basic-pkm` work out of the box while allowing richer models (`projects`, `ppv`, etc.) to be opinionated about which entities represent coherent wholes.

UI affordance: a small Lucide icon (`scan` or `focus`) on the object header, next to the view picker. Tooltip: "View through this lens."

### What Changes When a Lens Is Active

| Area | Behavior |
|---|---|
| Explorer tree root | Becomes the lens object; only descendants via `dcterms:isPartOf*` are shown |
| New-object form | `dcterms:isPartOf` pre-filled to the lens object |
| Search | Scoped to lens descendants by default, with a "search everywhere" toggle |
| Graph view | Renders the lens sub-graph only |
| Recent items | Filtered to lens descendants |
| Card / table views | Default filter appends `?x dcterms:isPartOf+ <lens>` |
| Tabs already open for objects outside the lens | Stay open but visually de-emphasized with an "outside lens" badge — closing them is manual |
| View picker on objects | Any view with a `?lens` parameter pre-binds it to the active lens |

### Entering, Stacking, and Exiting a Lens

- **Enter**: click the lens icon on an object header → workspace re-scopes, breadcrumb updates.
- **Stack**: entering a lens from within another lens deepens the stack (`Home › Research › Project Alpha › Phase 2`).
- **Exit**: click any breadcrumb segment to pop to that level; click `Home` to clear entirely; `Esc` pops one level.
- **Persistence**: lens stack stored in session state alongside tab state so a page reload resumes where the user was.

### Federation Bonus

The lens gives a clean sync primitive: "share this lens" = share the transitive `dcterms:isPartOf` closure of the lens object. That is the holonic boundary for export purposes, without needing per-entity named graphs.

### Open Design Questions

These are not yet decided. Leaving them here to return to before implementation begins.

1. **Icon choice.** Lucide candidates: `scan`, `focus`, `aperture`. `aperture` leans most into the lens metaphor; `focus` is most literal; `scan` is neutral.
2. **Navigating out of a lens via a link.** When the user clicks a backlink or inline reference to an object that sits outside the current lens, what happens?
   - (a) Lens clears automatically and the target opens at top level.
   - (b) Lens stays active; target opens in a tab flagged "outside lens" with a prompt to clear or expand the lens.
   - (c) Navigation is refused with a toast asking the user to exit the lens first.
3. **Lens memory per object.** When a user re-enters a lens they've been inside before (e.g. Project Alpha), should the workspace restore the last view/tab state it had inside that lens, or start fresh each time?
4. **Multiple lenses active at once.** Does the model support one lens at a time, or multiple? The options split along a holonic-purity line:
   - (a) **Single active lens per workspace.** Matches the holonic "you are inside one coherent whole" framing — one vocabulary, one boundary, one narrative at a time.
   - (b) **Union semantics** — explorer/search/views show items descending from ANY active lens. *Goes against holonic thinking*: a coherent "inside" requires a single boundary. If the user repeatedly wants lens A ∪ lens B, that is a signal the data is missing a common parent holon (e.g., "Active Projects") which, once created, can be lensed to give the union view naturally.
   - (c) **Side-by-side panes, each with its own independent lens.** Fully compatible with holonic thinking: each pane is a separate observer, each observer is inside exactly one whole. Holons constrain the *thing*, not the number of simultaneous observers.

   **Recommended position**: within a single pane, one lens at a time. If multi-lens UX is needed later, add side-by-side panes rather than union semantics. Persistent desire for a union is a prompt to model a containing holon.

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
