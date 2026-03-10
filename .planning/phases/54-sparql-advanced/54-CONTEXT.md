# Phase 54: SPARQL Advanced - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can share saved SPARQL queries with specific collaborators (read-only) and promote saved queries into named views that appear in the nav tree alongside model-defined views. Query sharing and view promotion extend the Phase 53 SPARQL console. AI query helpers, query export, and collaborative editing are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Query Sharing Model
- **Share with specific users** — owner picks recipients from a simple dropdown of all non-guest users on the instance
- **Owner-only sharing control** — only the original creator can share/unshare a query; recipients cannot re-share
- **Live updates with version indicator** — recipients always see the latest version of a shared query; a subtle "Updated" badge appears when the query has changed since they last viewed it
- **No notification system** — shared queries appear passively in the recipient's Saved dropdown next time they open it

### Sharing UI
- **Share action in Saved dropdown** — each saved query entry gets a share icon button (following the existing star-icon pattern from Phase 53). Clicking opens a user picker dropdown
- **Simple dropdown of all users** — shows all non-guest users in a dropdown/checklist for sharing. No search/autocomplete needed
- **Separate "Shared with Me" section in Saved dropdown** — the Saved dropdown gets two sections with a visual separator: "My Queries" (top) and "Shared with Me" (bottom). Shared entries show the owner's name

### Shared Query Permissions
- **Run, fork, and edit in editor** — when a recipient loads a shared query, it loads into the editor as fully editable for ad-hoc tweaking. Changes never affect the original. A "Save as my own" button lets them fork it as their own saved query

### View Promotion Flow
- **Both entry points** — promote from the Saved dropdown (icon button) or directly from query results ("Save as View" button above results table). Both open the same promotion dialog
- **Separate "My Views" section in nav tree** — promoted views appear in a new top-level section below model-defined types, labeled "My Views" or "Custom Views". Keeps user-created views distinct from model views
- **Creator-only visibility** — promoted views are private to the user who created them. Other users don't see them in the nav tree
- **Easy toggle demotion** — a promoted view can be demoted back to just a saved query. The nav tree entry has a remove/demote action. The saved query remains intact

### View Result Rendering
- **Auto-detect columns from SELECT** — columns are automatically derived from the query's SELECT variables. No manual configuration needed
- **User chooses renderer type** — the promotion dialog offers all three renderer types (table, cards, graph) regardless of query shape. If the query doesn't map well to the chosen renderer, show a warning
- **Plain links for IRIs** — IRI columns in promoted view results render as clickable text links, consistent with how model-defined views currently render IRIs (not the pill style from the SPARQL console)

### Claude's Discretion
- Promotion dialog layout and field arrangement
- "Updated" badge styling and timing logic for shared queries
- How to handle graph renderer when query lacks ?source/?target variables
- Column header label resolution (use variable names or attempt label lookup)
- Sorting/pagination behavior for promoted views (follow existing ViewSpec patterns)
- "My Views" section icon and expand/collapse behavior in nav tree

</decisions>

<specifics>
## Specific Ideas

- The sharing UX should feel lightweight — icon button in the dropdown, not a separate management page
- "Shared with Me" section mirrors how Google Docs shows "Shared with me" as a distinct area
- View promotion should feel like "pinning" a query to the sidebar — minimal friction
- When forking a shared query, pre-fill the name with "Copy of {original name}"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SavedSparqlQuery` model (Phase 53): Has user_id, name, description, query_text — needs sharing columns added (or a join table)
- `ViewSpec` dataclass + `ViewSpecService`: Powers model-defined views with spec_iri, label, target_class, renderer_type, sparql_query, columns. User views need to integrate with this system
- `sparql-console.js`: Saved dropdown rendering, star-from-history pattern — extend with share icon and promote icon
- Nav tree (`nav_tree.html`): Renders type nodes — needs a new "My Views" section that loads user-promoted views

### Established Patterns
- Icon buttons in dropdowns: Phase 53's star-from-history pattern (icon button per dropdown entry)
- SQLAlchemy models with ForeignKey to users.id for user-scoped data
- ViewSpec service queries model views graphs via SPARQL — user views will be stored in SQLite instead
- htmx partial rendering for tree nodes and dropdown content

### Integration Points
- `SavedSparqlQuery` model: Add sharing relationship (join table for shared_with users)
- New model: `PromotedQueryView` (or extend SavedSparqlQuery with view metadata)
- `ViewSpecService.get_all_view_specs()`: Needs to also return user-promoted views alongside model views
- Nav tree template: Add "My Views" section with user-promoted views
- `sparql-console.js`: Extend Saved dropdown with share/promote icons and "Shared with Me" section
- `workspace.js`: Handle clicks on promoted view nav tree entries (load view in editor area)

</code_context>

<deferred>
## Deferred Ideas

- **AI Query Helper** — Noted in Phase 53, still deferred. Natural language to SPARQL generation
- **Query export/import** — Export queries as files for backup or cross-instance sharing
- **Collaborative query editing** — Real-time co-editing of shared queries
- **Shared promoted views** — Making promoted views visible to other users (currently creator-only)

</deferred>

---

*Phase: 54-sparql-advanced*
*Context gathered: 2026-03-10*
