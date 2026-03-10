# Phase 54: SPARQL Advanced - Research

**Researched:** 2026-03-10
**Domain:** Query sharing (multi-user access control), view promotion (SPARQL-to-nav-tree), ViewSpec integration
**Confidence:** HIGH

## Summary

Phase 54 extends the Phase 53 SPARQL console with two features: (1) sharing saved queries with other users for read-only access, and (2) promoting saved queries into named views that appear in the nav tree. Both features build directly on existing infrastructure -- the `SavedSparqlQuery` SQLAlchemy model, the `ViewSpec`/`ViewSpecService` system, the nav tree template, and the `sparql-console.js` saved dropdown.

Sharing requires a new join table (`shared_query_access`) linking saved queries to recipient users, new API endpoints for managing shares and listing shared queries, and frontend extensions to the Saved dropdown (share icon button, "Shared with Me" section, "Save as my own" fork action). View promotion requires a new `PromotedQueryView` SQLAlchemy model (or columns on `SavedSparqlQuery`) storing renderer type and display label, integration with `ViewSpecService.get_all_view_specs()` to include user-promoted views alongside model views, a new "My Views" section in the nav tree template, and promote/demote UI in both the Saved dropdown and the results area.

The key integration insight is that promoted views should create `ViewSpec` dataclass instances at runtime (not store RDF in the triplestore), injected into the `ViewSpecService` results. This avoids polluting the triplestore with user-level configuration while reusing all existing table/cards/graph rendering infrastructure. The SPARQL query from the saved query becomes the `ViewSpec.sparql_query`, columns are auto-detected from SELECT variables, and the existing `execute_table_query`/`execute_cards_query`/`execute_graph_query` methods handle execution unchanged.

**Primary recommendation:** Build in three waves -- (1) sharing model + endpoints + UI, (2) promotion model + ViewSpec integration + nav tree section, (3) result rendering and demote flow. Each wave is independently testable and deployable.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Share with specific users** -- owner picks recipients from a simple dropdown of all non-guest users on the instance
- **Owner-only sharing control** -- only the original creator can share/unshare a query; recipients cannot re-share
- **Live updates with version indicator** -- recipients always see the latest version of a shared query; a subtle "Updated" badge appears when the query has changed since they last viewed it
- **No notification system** -- shared queries appear passively in the recipient's Saved dropdown next time they open it
- **Share action in Saved dropdown** -- each saved query entry gets a share icon button (following the existing star-icon pattern from Phase 53). Clicking opens a user picker dropdown
- **Simple dropdown of all users** -- shows all non-guest users in a dropdown/checklist for sharing. No search/autocomplete needed
- **Separate "Shared with Me" section in Saved dropdown** -- the Saved dropdown gets two sections with a visual separator: "My Queries" (top) and "Shared with Me" (bottom). Shared entries show the owner's name
- **Run, fork, and edit in editor** -- when a recipient loads a shared query, it loads into the editor as fully editable for ad-hoc tweaking. Changes never affect the original. A "Save as my own" button lets them fork it as their own saved query
- **Both entry points** -- promote from the Saved dropdown (icon button) or directly from query results ("Save as View" button above results table). Both open the same promotion dialog
- **Separate "My Views" section in nav tree** -- promoted views appear in a new top-level section below model-defined types, labeled "My Views" or "Custom Views". Keeps user-created views distinct from model views
- **Creator-only visibility** -- promoted views are private to the user who created them. Other users don't see them in the nav tree
- **Easy toggle demotion** -- a promoted view can be demoted back to just a saved query. The nav tree entry has a remove/demote action. The saved query remains intact
- **Auto-detect columns from SELECT** -- columns are automatically derived from the query's SELECT variables. No manual configuration needed
- **User chooses renderer type** -- the promotion dialog offers all three renderer types (table, cards, graph) regardless of query shape. If the query doesn't map well to the chosen renderer, show a warning
- **Plain links for IRIs** -- IRI columns in promoted view results render as clickable text links, consistent with how model-defined views currently render IRIs (not the pill style from the SPARQL console)

### Claude's Discretion
- Promotion dialog layout and field arrangement
- "Updated" badge styling and timing logic for shared queries
- How to handle graph renderer when query lacks ?source/?target variables
- Column header label resolution (use variable names or attempt label lookup)
- Sorting/pagination behavior for promoted views (follow existing ViewSpec patterns)
- "My Views" section icon and expand/collapse behavior in nav tree

### Deferred Ideas (OUT OF SCOPE)
- **AI Query Helper** -- Noted in Phase 53, still deferred. Natural language to SPARQL generation
- **Query export/import** -- Export queries as files for backup or cross-instance sharing
- **Collaborative query editing** -- Real-time co-editing of shared queries
- **Shared promoted views** -- Making promoted views visible to other users (currently creator-only)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SPARQL-04 | User can share a saved query with other users (read-only) | New `shared_query_access` join table + Alembic migration 008. Share/unshare endpoints on sparql router. Frontend: share icon in Saved dropdown, user picker checklist, "Shared with Me" section. Uses existing `User` model for recipient lookup. |
| SPARQL-07 | User can promote a saved query to a named view browsable in the nav tree | New `PromotedQueryView` model + same migration. Promote/demote endpoints. ViewSpecService extended to include user-promoted views in `get_all_view_specs()`. New "My Views" section in nav tree template. Reuses existing table/cards/graph rendering infrastructure. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.46+ | New sharing + promotion models | Already used for all data models; async support |
| Alembic | 1.18+ | Database migration for new tables | Already used; 7 migrations exist (007 latest) |
| FastAPI | 0.115+ | New CRUD endpoints for sharing and promotion | Already used for all API routes |
| Jinja2 | 3.1+ | Nav tree "My Views" section template | Already used for all HTML rendering |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ViewSpecService | existing | Rendering promoted views using table/cards/graph | Core integration point for view promotion |
| LabelService | existing | Resolving labels in promoted view results | Column header and row label resolution |
| IconService | existing | Type icons for promoted views in nav tree | "My Views" section icons |
| htmx | 2.0 (CDN) | Lazy-load "My Views" section in nav tree | Follows existing tree node lazy-load pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite join table for sharing | RDF named graphs for share metadata | SQLite is simpler, user config belongs in SQLite not triplestore |
| Runtime ViewSpec injection | Store promoted views as RDF in triplestore | Avoids triplestore pollution; SQLite is source of truth for user config |
| Separate "My Views" nav section | Mix promoted views into type-based tree | User decision locks separate section; cleaner UX |

**Installation:**
No new packages needed. All backend dependencies already installed. No frontend CDN additions required.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
  sparql/
    models.py            # MODIFIED - add SharedQueryAccess, PromotedQueryView models
    schemas.py           # MODIFIED - add sharing/promotion request/response schemas
    router.py            # MODIFIED - add share/unshare, promote/demote, list-users endpoints
  views/
    service.py           # MODIFIED - extend get_all_view_specs() to include promoted views
  browser/
    router.py            # MODIFIED - extend nav_tree/workspace to include "My Views" section
  templates/browser/
    nav_tree.html         # MODIFIED - add "My Views" section below types
    sparql_panel.html     # MODIFIED - add share/promote icons, "Shared with Me" section
    promote_dialog.html   # NEW - promotion dialog (renderer picker, name field)
frontend/static/
  js/
    sparql-console.js     # MODIFIED - share/promote UI, "Shared with Me" section
  css/
    workspace.css         # MODIFIED - share/promote UI styles, "My Views" nav styles
backend/migrations/versions/
  008_sharing_promotion.py # NEW - shared_query_access + promoted_query_views tables
```

### Pattern 1: SQLAlchemy Join Table for Many-to-Many Sharing
**What:** A `shared_query_access` table linking `saved_sparql_queries.id` to `users.id`, with metadata for tracking "last viewed" timestamps for the "Updated" badge.
**When to use:** Representing the many-to-many relationship between queries and shared-with users.
**Example:**
```python
class SharedQueryAccess(Base):
    """Access record: a saved query shared with a specific user."""
    __tablename__ = "shared_query_access"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"), index=True
    )
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    __table_args__ = (
        UniqueConstraint("query_id", "shared_with_user_id", name="uq_shared_query_user"),
    )
```

### Pattern 2: PromotedQueryView Model (SQLite, not RDF)
**What:** A model linking a `SavedSparqlQuery` to view metadata (renderer type, display label). Stored in SQLite, not the triplestore.
**When to use:** Representing a saved query that has been promoted to a nav tree view.
**Example:**
```python
class PromotedQueryView(Base):
    """A saved query promoted to a named view in the nav tree."""
    __tablename__ = "promoted_query_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"), unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    display_label: Mapped[str] = mapped_column(String(255), nullable=False)
    renderer_type: Mapped[str] = mapped_column(String(20), default="table")  # table, card, graph
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### Pattern 3: ViewSpec Integration for Promoted Views
**What:** Convert `PromotedQueryView` + its `SavedSparqlQuery` into a `ViewSpec` dataclass at query time, injected into `get_all_view_specs()` results.
**When to use:** Making promoted views renderable using existing view infrastructure.
**Example:**
```python
# In ViewSpecService or a new method
async def get_user_promoted_view_specs(self, user_id: uuid.UUID, db: AsyncSession) -> list[ViewSpec]:
    """Load promoted query views for a user, converting to ViewSpec dataclasses."""
    result = await db.execute(
        select(PromotedQueryView, SavedSparqlQuery)
        .join(SavedSparqlQuery, PromotedQueryView.query_id == SavedSparqlQuery.id)
        .where(PromotedQueryView.user_id == user_id)
    )
    specs = []
    for pv, sq in result.all():
        columns = _extract_select_var_names(sq.query_text)
        specs.append(ViewSpec(
            spec_iri=f"urn:sempkm:user-view:{pv.id}",
            label=pv.display_label,
            target_class="",  # User views don't target a specific class
            renderer_type=pv.renderer_type,
            sparql_query=sq.query_text,
            columns=columns,
            source_model="user",
        ))
    return specs
```

### Pattern 4: Nav Tree "My Views" Section
**What:** A new explorer section in the workspace nav tree, below the OBJECTS and VIEWS sections, showing the current user's promoted views.
**When to use:** Rendering promoted views in the sidebar.
**Example:**
```html
<!-- In workspace.html, after section-views -->
<div class="explorer-section" id="section-my-views" data-panel-name="my-views">
    <div class="explorer-section-header"
         hx-get="/browser/my-views"
         hx-trigger="click once"
         hx-target="#my-views-tree"
         hx-swap="innerHTML">
        <i data-lucide="grip-vertical" class="panel-grip"></i>
        <span class="explorer-section-title">MY VIEWS</span>
    </div>
    <div class="explorer-section-body" id="my-views-tree">
        <div class="tree-empty">Loading views...</div>
    </div>
</div>
```

### Pattern 5: Saved Dropdown with "Shared with Me" Section
**What:** Extend the existing `loadSaved()` function to fetch both owned and shared queries, rendering them in separate sections.
**When to use:** Building the enhanced Saved dropdown.
**Example:**
```javascript
// New endpoint returns both sections
// GET /api/sparql/saved?include_shared=true
// Response: { my_queries: [...], shared_with_me: [...] }

// Each shared entry includes:
// { id, name, description, query_text, owner_name, updated_at, is_updated }
// is_updated = (query.updated_at > access.last_viewed_at)
```

### Pattern 6: Share User Picker
**What:** A lightweight checklist dropdown showing all non-guest users, with checkboxes for toggling share access.
**When to use:** The share action from a saved query.
**Example:**
```javascript
// 1. Fetch users: GET /api/sparql/users (returns non-guest users)
// 2. Fetch current shares: GET /api/sparql/saved/{id}/shares
// 3. Render checklist with pre-checked users
// 4. On toggle: PUT /api/sparql/saved/{id}/shares body={user_ids: [...]}
```

### Anti-Patterns to Avoid
- **Storing promoted views as RDF in the triplestore:** User config belongs in SQLite. The triplestore is for knowledge graph data.
- **Modifying the ViewSpec SPARQL query in the triplestore:** Promoted views use the saved query text directly, scoped to current graph at execution time.
- **Creating a separate rendering pipeline for promoted views:** Reuse the existing `execute_table_query`/`execute_cards_query`/`execute_graph_query` methods. Promoted views are just ViewSpecs with `source_model="user"`.
- **Building complex permission inheritance:** Sharing is a flat list. No groups, no cascading permissions, no re-sharing.
- **Auto-detecting renderer type:** User explicitly chooses renderer type in the promotion dialog. Don't try to infer it from query shape.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Table/cards/graph rendering | Custom rendering for promoted views | Existing ViewSpec execute_table_query/cards/graph methods | Already handle pagination, sorting, filtering, label resolution |
| SPARQL column extraction | Complex parser for SELECT vars | Regex on SELECT line: `/SELECT\s+(DISTINCT\s+)?(.+?)\s+WHERE/i` | Simple regex sufficient for well-formed queries; ViewSpec already does this |
| IRI rendering in view results | New pill/link renderer | Existing table_view.html `openTab()` links | View results already render IRIs as clickable links |
| User listing for share picker | Custom user management | `select(User).where(User.role != 'guest')` on existing User model | Auth models already have all user data needed |
| Nav tree lazy loading | Custom AJAX loader | htmx `hx-get` + `hx-trigger="click once"` | Same pattern as existing type nodes in nav_tree.html |

**Key insight:** The heaviest part of this phase (rendering query results as table/cards/graph views) is already fully implemented in the ViewSpec system. This phase is primarily about (1) a new join table + CRUD for sharing, (2) a new model + ViewSpec adapter for promotion, and (3) UI extensions to the existing SPARQL panel and nav tree.

## Common Pitfalls

### Pitfall 1: ViewSpec Cache Invalidation After Promote/Demote
**What goes wrong:** After promoting or demoting a view, the nav tree still shows stale data because `ViewSpecService._specs_cache` has a 300s TTL.
**Why it happens:** The cache stores model-defined view specs. If we mix user-promoted specs into the same cache, we'd need per-user cache keys, and invalidation becomes complex.
**How to avoid:** Keep user-promoted view specs OUT of the ViewSpecService cache entirely. Fetch them directly from SQLite on each request (cheap operation). Only model-defined specs use the TTL cache. The nav tree endpoint and view rendering endpoints query the DB directly for user specs.
**Warning signs:** Promoted view appears/disappears only after 5 minutes.

### Pitfall 2: SELECT Variable Extraction from Arbitrary SPARQL
**What goes wrong:** A query like `SELECT (COUNT(?x) AS ?total) WHERE {...}` has computed columns that don't map to simple variable names.
**Why it happens:** Users can write any valid SPARQL. Aggregated or aliased columns like `(STR(?label) AS ?name)` are common.
**How to avoid:** Use regex to extract both direct variables (`?var`) and aliases (`AS ?alias`). For the columns list, use the alias names when present: parse `\(\s*.+?\s+AS\s+\?(\w+)\s*\)` and `\?(\w+)` from the SELECT line. Show a warning in the promotion dialog if no columns are detected.
**Warning signs:** Empty column headers, missing data in promoted view.

### Pitfall 3: Promoted View Queries Without ?s Subject Variable
**What goes wrong:** The existing `execute_table_query` deduplicates rows by `?s` and uses `?s` as the clickable link. Promoted view queries may not have a `?s` variable.
**Why it happens:** Model-defined view specs always use `?s` as the subject variable. User SPARQL queries have arbitrary variable names.
**How to avoid:** For promoted views, skip the `?s`-based deduplication logic. Render all result rows as-is. If the query contains IRIs, render them as plain clickable links (not pills). The first URI column can serve as the "open in tab" target. This matches the user decision: "plain links for IRIs."
**Warning signs:** Empty table, all rows filtered out, "No results" for queries that return data in the SPARQL console.

### Pitfall 4: Graph Renderer Without ?source/?target Variables
**What goes wrong:** The graph renderer expects `?source`, `?target`, and optionally `?label` variables in the query. A promoted view with `SELECT ?s ?p ?o` won't produce a graph.
**Why it happens:** Users can choose any renderer type regardless of query shape.
**How to avoid:** In the promotion dialog, show a warning when the user selects "graph" renderer and the query doesn't contain `?source` and `?target` variables. Still allow the selection (per user decision), but display a helpful message in the rendered view if the graph has no edges. Fall back to showing nodes only.
**Warning signs:** Empty graph, no edges visible, confusing user experience.

### Pitfall 5: "Updated" Badge Timing -- last_viewed_at Race Condition
**What goes wrong:** The "Updated" badge flickers or never disappears because `last_viewed_at` is updated at the wrong time.
**Why it happens:** If we update `last_viewed_at` when listing shared queries (in the dropdown), the badge disappears before the user actually views the query. If we update it when loading into the editor, there's a small window where the update hasn't committed yet.
**How to avoid:** Update `last_viewed_at` when the shared query is loaded into the editor (not when listed in the dropdown). The badge comparison is `query.updated_at > access.last_viewed_at`. Use a separate endpoint like `POST /api/sparql/saved/{id}/mark-viewed` called after loading.
**Warning signs:** Badge never goes away, badge disappears without viewing the query.

### Pitfall 6: Foreign Key Cascade on Saved Query Deletion
**What goes wrong:** Deleting a saved query that has been shared or promoted fails with an integrity error.
**Why it happens:** Missing `ondelete="CASCADE"` on the foreign keys from `shared_query_access` and `promoted_query_views` to `saved_sparql_queries`.
**How to avoid:** Define both foreign keys with `ondelete="CASCADE"`. When a saved query is deleted, all shares and promotions are automatically cleaned up.
**Warning signs:** 500 errors when deleting shared/promoted queries.

### Pitfall 7: Lucide Icons in Flex Dropdowns
**What goes wrong:** Share, promote, and fork icon buttons in the Saved dropdown have invisible icons.
**Why it happens:** Per CLAUDE.md: Lucide SVGs inside flex containers without `flex-shrink: 0` get compressed to 0px width.
**How to avoid:** Follow the established `.sparql-star-btn` / `.sparql-delete-btn` CSS pattern from Phase 53. Add `flex-shrink: 0` and explicit width/height on SVG in all new icon button CSS rules.
**Warning signs:** Invisible icons in dropdown entries.

### Pitfall 8: Alembic Migration Numbering
**What goes wrong:** Migration revision collision.
**Why it happens:** Latest migration is `007_sparql_tables.py` with `down_revision = "006"`. New migration must be `008` with `down_revision = "007"`.
**How to avoid:** Check existing migration files before creating. Use `008` as the revision ID.
**Warning signs:** "Multiple head revisions" error from Alembic.

## Code Examples

### Existing Saved Dropdown Pattern (from sparql-console.js)
```javascript
// Source: frontend/static/js/sparql-console.js
// Each saved query entry has main area (click to load) + icon button (click to delete)
html += '<div class="sparql-dropdown-item sparql-saved-item" data-query-id="' + entry.id + '">';
html += '<div class="sparql-dropdown-item-main">';
html += '<span class="sparql-dropdown-item-name">' + escapeHtml(entry.name) + '</span>';
html += '</div>';
html += '<button class="sparql-delete-btn" title="Delete saved query"><i data-lucide="trash-2"></i></button>';
html += '</div>';
// New icons follow same pattern: share-2 (share), pin (promote)
```

### Existing Nav Tree Section Pattern (from workspace.html)
```html
<!-- Source: backend/app/templates/browser/workspace.html -->
<!-- VIEWS section pattern -- "My Views" follows identical structure -->
<div class="explorer-section" id="section-views" data-panel-name="views">
    <div class="explorer-section-header"
         hx-get="/browser/views/explorer"
         hx-trigger="click once"
         hx-target="#views-tree"
         hx-swap="innerHTML">
        <i data-lucide="grip-vertical" class="panel-grip"></i>
        <span class="explorer-section-title">VIEWS</span>
    </div>
    <div class="explorer-section-body" id="views-tree">
        <div class="tree-empty">Loading views...</div>
    </div>
</div>
```

### Existing ViewSpec Dataclass (from views/service.py)
```python
# Source: backend/app/views/service.py
@dataclass
class ViewSpec:
    spec_iri: str
    label: str
    target_class: str
    renderer_type: str  # "table", "card", "graph"
    sparql_query: str
    columns: list[str] = field(default_factory=list)
    sort_default: str = ""
    card_title: str = ""
    card_subtitle: str = ""
    source_model: str = ""  # model ID or "user"
    # Note: source_model="user" already anticipated -- perfect for promoted views
```

### Existing User Query Pattern (from auth/service.py)
```python
# Source: backend/app/auth/service.py
# Querying users -- used for share picker dropdown
result = await db.execute(
    select(User).where(User.role != 'guest')
)
users = result.scalars().all()
```

### SELECT Variable Extraction
```python
import re

def _extract_select_var_names(sparql_query: str) -> list[str]:
    """Extract variable names from a SPARQL SELECT clause.

    Handles both direct variables (?var) and aliases (expression AS ?alias).
    Returns variable names without the ? prefix.
    """
    # Match the SELECT line
    select_match = re.search(
        r'SELECT\s+(DISTINCT\s+)?(.+?)\s+WHERE',
        sparql_query, re.IGNORECASE | re.DOTALL
    )
    if not select_match:
        return []

    select_part = select_match.group(2)

    # Handle SELECT * -- return empty (columns determined at runtime)
    if select_part.strip() == '*':
        return []

    vars_found = []
    # Extract aliases: (... AS ?alias)
    for alias_match in re.finditer(r'AS\s+\?(\w+)', select_part, re.IGNORECASE):
        vars_found.append(alias_match.group(1))

    # Extract direct variables: ?var (not inside parentheses and not preceded by AS)
    # Remove alias expressions first
    cleaned = re.sub(r'\([^)]+\)', '', select_part)
    for var_match in re.finditer(r'\?(\w+)', cleaned):
        name = var_match.group(1)
        if name not in vars_found:
            vars_found.append(name)

    return vars_found
```

### Promoted View Rendering Integration
```python
# How to route a promoted view request through existing infrastructure:
# 1. User clicks "My Views" entry -> htmx GET to /browser/views/table/{spec_iri}
# 2. The spec_iri is urn:sempkm:user-view:{promoted_view_id}
# 3. ViewSpecService.get_view_spec_by_iri() checks model specs first, then user specs
# 4. For user specs, query PromotedQueryView from SQLite
# 5. Convert to ViewSpec dataclass, pass to execute_table_query()
# 6. Render with existing table_view.html / cards_view.html / graph_view.html
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No sharing | Share with specific users | Phase 54 | Collaboration without notification overhead |
| SPARQL-only results | Promoted views in nav tree | Phase 54 | Pinned queries as browsable views |
| Model-only ViewSpecs | Model + user ViewSpecs | Phase 54 | User-created views alongside model views |
| Single-section Saved dropdown | My Queries + Shared with Me | Phase 54 | Clear ownership in dropdown |

## Open Questions

1. **ViewSpecService DB session dependency**
   - What we know: `ViewSpecService` currently receives only `TriplestoreClient` and `LabelService` in its constructor (no SQLAlchemy session). To query `PromotedQueryView`, it needs a DB session.
   - What's unclear: Whether to inject `AsyncSession` into the service constructor, or create a separate method that receives the session as a parameter.
   - Recommendation: Add an optional `get_user_view_specs(user_id, db)` method that accepts the session as a parameter (not constructor). This keeps the constructor unchanged and follows the pattern where sessions are request-scoped via FastAPI `Depends()`. The router passes the session when calling this method.

2. **Promoted view IRI scheme**
   - What we know: Model-defined view specs use IRIs from the model's views graph (e.g., `urn:sempkm:model:basic-pkm:views:NoteTable`). User-promoted views need a synthetic IRI for ViewSpec.spec_iri.
   - What's unclear: The exact format and whether it needs to be URL-safe for the view router's path parameter routing.
   - Recommendation: Use `urn:sempkm:user-view:{uuid}` format. The existing `{spec_iri:path}` path convertor in the views router handles URN-style IRIs. The UUID part makes it globally unique.

3. **"Save as View" button placement in results area**
   - What we know: The SPARQL panel has a results area with an info line above the table. The "Save as View" button should appear above the results table.
   - What's unclear: Whether to add it to the existing info line or create a new action bar.
   - Recommendation: Add it to the existing results info line (`#sparql-results-info`), alongside the row count. It only appears after a successful query execution and when the current query is saved (i.e., has a saved query ID). This avoids creating a new UI element.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright 1.50.0 |
| Config file | e2e/playwright.config.ts |
| Quick run command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium tests/07-multi-user/` |
| Full suite command | `cd /home/james/Code/SemPKM/e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPARQL-04 | Share query with another user, recipient sees it | integration | Manual: open SPARQL panel as owner, share query, switch to member user, check Saved dropdown | No -- Wave 0 |
| SPARQL-04 | Fork shared query as own | smoke | Manual: load shared query, click "Save as my own", verify in My Queries | No -- Wave 0 |
| SPARQL-07 | Promote saved query to nav tree view | integration | Manual: save query, promote via dialog, check "My Views" nav section | No -- Wave 0 |
| SPARQL-07 | Promoted view renders using existing view infrastructure | smoke | Manual: click promoted view in nav tree, verify table/cards/graph renders | No -- Wave 0 |
| SPARQL-07 | Demote view back to saved query | smoke | Manual: click remove on "My Views" entry, verify view removed, saved query intact | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Manual smoke test in browser (share flow, promote flow, render check)
- **Per wave merge:** Full E2E suite run (ensure no regressions)
- **Phase gate:** Full suite green + manual feature verification before `/gsd:verify-work`

### Wave 0 Gaps
- No existing sharing or promotion E2E tests
- Manual testing is appropriate -- these features involve multi-user flows and visual rendering
- Backend API endpoints (share CRUD, promote CRUD) could have pytest unit tests if desired
- Multi-user testing requires two browser sessions or two users in the test database
- Framework install: already available (`cd e2e && npx playwright test`)

## Sources

### Primary (HIGH confidence)
- `backend/app/sparql/models.py` - Existing SavedSparqlQuery model structure, will be extended
- `backend/app/sparql/router.py` - Existing saved query CRUD endpoints, pattern for new endpoints
- `backend/app/sparql/schemas.py` - Existing Pydantic schemas, pattern for new schemas
- `frontend/static/js/sparql-console.js` - Existing saved dropdown rendering, share/promote icon pattern
- `backend/app/views/service.py` - ViewSpec dataclass, ViewSpecService methods, cache architecture
- `backend/app/views/router.py` - View rendering routes (table, cards, graph), spec_iri path routing
- `backend/app/views/registry.py` - Renderer registry (table, card, graph types)
- `backend/app/auth/models.py` - User model structure (id, email, display_name, role)
- `backend/app/templates/browser/workspace.html` - Nav tree sections, explorer-section pattern
- `backend/app/templates/browser/nav_tree.html` - Tree node rendering pattern
- `backend/app/templates/browser/sparql_panel.html` - SPARQL panel HTML structure
- `backend/app/browser/router.py` - Nav tree endpoint, workspace rendering
- `backend/migrations/versions/` - 007 is latest migration, next is 008

### Secondary (MEDIUM confidence)
- Phase 53 Research (53-RESEARCH.md) - Established patterns for SPARQL panel architecture

### Tertiary (LOW confidence)
- None -- all patterns are established in the existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use; no new dependencies
- Architecture: HIGH - All patterns follow existing codebase conventions; ViewSpec integration is straightforward
- Pitfalls: HIGH - Cache invalidation, column extraction, and FK cascades are well-understood concerns
- Sharing model: HIGH - Simple join table pattern; well-established SQLAlchemy practice
- View promotion: HIGH - ViewSpec dataclass already has `source_model` field anticipating "user" source

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, all internal codebase patterns)
