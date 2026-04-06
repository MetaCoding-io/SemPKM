"""ViewSpecService for loading view specs from installed Mental Model views
graphs and executing their SPARQL queries with pagination, sorting, and filtering.

Follows the same pattern as ShapesService (app/services/shapes.py): queries the
model registry for installed model IDs, builds SPARQL with FROM clauses for each
model's views graph, and parses results into structured Python dataclasses.

Uses scope_to_current_graph() from app/sparql/client to inject FROM <urn:sempkm:current>
into view spec SPARQL queries before execution (per Research Pitfall 1).
"""

import hashlib
import json
import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import rdflib
from dateutil.rrule import rruleset, rrulestr
from rdflib import RDF, URIRef

from app.models.registry import MODELS_GRAPH, SEMPKM_NS
from app.services.labels import LabelService
from app.services.shapes import NodeShapeForm, PropertyShape, ShapesService
from app.sparql.builder import safe_iri
from app.sparql.client import scope_to_current_graph, inject_prefixes
from app.sparql.query_service import QueryService
from app.sparql.utils import escape_sparql_regex
from app.triplestore.client import TriplestoreClient
from app.rdf.namespaces import CURRENT_GRAPH
from cachetools import TTLCache

logger = logging.getLogger(__name__)

SEMPKM_VOCAB = "urn:sempkm:vocab:"


@dataclass
class ViewSpec:
    """A view specification loaded from a model or user-defined."""

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


def _extract_select_var_names(sparql_query: str) -> list[str]:
    """Extract variable names from a SPARQL SELECT clause.

    Handles both direct variables (?var) and aliases (expression AS ?alias).
    Returns variable names without the ? prefix, or empty list for SELECT *.
    """
    select_match = re.search(
        r'SELECT\s+(DISTINCT\s+)?(.+?)\s+WHERE',
        sparql_query, re.IGNORECASE | re.DOTALL,
    )
    if not select_match:
        return []

    select_part = select_match.group(2)

    # Handle SELECT *
    if select_part.strip() == '*':
        return []

    vars_found: list[str] = []

    # Extract aliases: (... AS ?alias)
    for alias_match in re.finditer(r'AS\s+\?(\w+)', select_part, re.IGNORECASE):
        vars_found.append(alias_match.group(1))

    # Extract direct variables: ?var (outside parentheses)
    cleaned = re.sub(r'\([^)]+\)', '', select_part)
    for var_match in re.finditer(r'\?(\w+)', cleaned):
        name = var_match.group(1)
        if name not in vars_found:
            vars_found.append(name)

    return vars_found


class ViewSpecService:
    """Load and execute view specs from installed Mental Model views graphs.

    Uses SPARQL SELECT to query sempkm:ViewSpec instances across all
    installed model views graphs, and executes their SPARQL queries
    with pagination, sorting, and filtering for table/card rendering.
    """

    def __init__(
        self,
        client: TriplestoreClient,
        label_service: LabelService,
        query_service: QueryService | None = None,
        shapes_service: ShapesService | None = None,
        ttl: int = 300,
        maxsize: int = 64,
    ) -> None:
        self._client = client
        self._label_service = label_service
        self._query_service = query_service
        self._shapes_service = shapes_service
        self._generic_specs: list[ViewSpec] = []
        self._specs_cache: TTLCache[str, list[ViewSpec]] = TTLCache(
            maxsize=maxsize, ttl=ttl
        )

    async def get_all_view_specs(self) -> list[ViewSpec]:
        """Load all view specs from all installed model views graphs.

        Queries the model registry for installed model IDs, then for each
        model builds FROM <urn:sempkm:model:{id}:views> clauses. Executes
        a SPARQL SELECT querying sempkm:ViewSpec instances with all
        properties.

        Returns:
            List of ViewSpec dataclasses parsed from SPARQL results.
        """
        cache_key = "all_specs"
        if cache_key in self._specs_cache:
            logger.debug("ViewSpec cache hit")
            return self._specs_cache[cache_key]

        # 1. List installed model IDs
        model_sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        result = await self._client.query(model_sparql)
        bindings = result.get("results", {}).get("bindings", [])

        if not bindings:
            logger.info("No installed models found for view spec extraction")
            return []

        # 2. Build reverse map from graph IRI → model ID
        model_ids = []
        graph_to_model: dict[str, str] = {}
        for b in bindings:
            model_id = b["modelId"]["value"]
            model_ids.append(model_id)
            views_iri = f"urn:sempkm:model:{model_id}:views"
            graph_to_model[views_iri] = model_id

        # VALUES clause constrains ?g to only model view graphs
        values_entries = " ".join(safe_iri(iri) for iri in graph_to_model)

        # 3. Query view spec properties using GRAPH ?g pattern
        specs_sparql = f"""SELECT ?g ?spec ?label ?targetClass ?renderer ?query ?columns ?sortDefault ?cardTitle ?cardSubtitle
WHERE {{
  VALUES ?g {{ {values_entries} }}
  GRAPH ?g {{
    ?spec a <{SEMPKM_VOCAB}ViewSpec> .
    OPTIONAL {{ ?spec <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
    OPTIONAL {{ ?spec <{SEMPKM_VOCAB}targetClass> ?targetClass }}
    OPTIONAL {{ ?spec <{SEMPKM_VOCAB}rendererType> ?renderer }}
    OPTIONAL {{ ?spec <{SEMPKM_VOCAB}sparqlQuery> ?query }}
    OPTIONAL {{ ?spec <{SEMPKM_VOCAB}columns> ?columns }}
    OPTIONAL {{ ?spec <{SEMPKM_VOCAB}sortDefault> ?sortDefault }}
    OPTIONAL {{ ?spec <{SEMPKM_VOCAB}cardTitle> ?cardTitle }}
    OPTIONAL {{ ?spec <{SEMPKM_VOCAB}cardSubtitle> ?cardSubtitle }}
  }}
}}"""

        try:
            result = await self._client.query(specs_sparql)
        except Exception:
            logger.warning("Failed to query view specs", exc_info=True)
            return []

        specs_bindings = result.get("results", {}).get("bindings", [])

        specs: list[ViewSpec] = []
        for b in specs_bindings:
            spec_iri = b["spec"]["value"]
            columns_str = b.get("columns", {}).get("value", "")
            columns = [c.strip() for c in columns_str.split(",") if c.strip()] if columns_str else []
            g_value = b.get("g", {}).get("value", "")

            specs.append(ViewSpec(
                spec_iri=spec_iri,
                label=b.get("label", {}).get("value", _local_name(spec_iri)),
                target_class=b.get("targetClass", {}).get("value", ""),
                renderer_type=b.get("renderer", {}).get("value", "table"),
                sparql_query=b.get("query", {}).get("value", ""),
                columns=columns,
                sort_default=b.get("sortDefault", {}).get("value", ""),
                card_title=b.get("cardTitle", {}).get("value", ""),
                card_subtitle=b.get("cardSubtitle", {}).get("value", ""),
                source_model=graph_to_model.get(g_value, ""),
            ))

        self._specs_cache[cache_key] = specs
        logger.info(
            "ViewSpec cache miss -- loaded %d specs from %d model(s)",
            len(specs), len(model_ids),
        )
        return specs

    def invalidate_cache(self) -> None:
        """Clear cached view specs after model install/uninstall."""
        self._specs_cache.clear()
        logger.info("ViewSpec cache invalidated")

    # ── Generic views ──────────────────────────────────────────

    def register_generic_views(self) -> None:
        """Create 3 in-memory ViewSpec objects for the generic renderers.

        Called at startup. These specs have empty ``sparql_query`` because
        the query is built dynamically per request via ``build_dynamic_query()``.
        """
        self._generic_specs = [
            ViewSpec(
                spec_iri="urn:sempkm:view:generic-table",
                label="Table View",
                target_class="",
                renderer_type="table",
                sparql_query="",
                source_model="system",
            ),
            ViewSpec(
                spec_iri="urn:sempkm:view:generic-card",
                label="Card View",
                target_class="",
                renderer_type="card",
                sparql_query="",
                source_model="system",
            ),
            ViewSpec(
                spec_iri="urn:sempkm:view:generic-graph",
                label="Graph View",
                target_class="",
                renderer_type="graph",
                sparql_query="",
                source_model="system",
            ),
        ]
        logger.info("Registered %d generic views", len(self._generic_specs))

    def get_generic_spec(self, renderer: str) -> ViewSpec | None:
        """Return the generic ViewSpec for a renderer type, or None."""
        for spec in self._generic_specs:
            if spec.renderer_type == renderer:
                return spec
        return None

    # Renderers that show all types without SHACL-based filtering
    _UNFILTERED_RENDERERS: set[str] = {
        "table", "card", "graph",
        "quadrant", "bmc", "okr", "decision-matrix",
    }

    async def get_compatible_types(
        self,
        renderer: str,
        exclude_iris: set[str] | None = None,
    ) -> list[dict]:
        """Return types compatible with the given renderer.

        For most renderers, returns all types.  For renderers that depend on
        specific SHACL constraints, filters to only types whose shapes declare
        the required fields:

        - ``kanban``: needs a property with ``sh:in`` values (status field)
        - ``calendar`` / ``timeline``: needs a date/dateTime property
        - ``map``: needs a lat/lng property pair

        Args:
            renderer: Renderer name (e.g. 'kanban', 'table', 'map').
            exclude_iris: Optional set of type IRIs to omit from results.

        Returns:
            List of dicts with 'iri' and 'label' keys.
        """
        if not self._shapes_service:
            return []

        all_types = await self._shapes_service.get_types(exclude_iris=exclude_iris)

        if renderer in self._UNFILTERED_RENDERERS:
            logger.info(
                "compatible_types: renderer=%s total=%d compatible=%d",
                renderer, len(all_types), len(all_types),
            )
            return all_types

        compatible: list[dict] = []

        if renderer == "kanban":
            for t in all_types:
                status_field, _ = await self._detect_status_field(t["iri"])
                if status_field is not None:
                    compatible.append(t)
        elif renderer in ("calendar", "timeline"):
            for t in all_types:
                start_field, _ = await self._detect_date_fields(t["iri"])
                if start_field is not None:
                    compatible.append(t)
        elif renderer == "map":
            for t in all_types:
                lat_field, lng_field = await self._detect_geo_fields(t["iri"])
                if lat_field is not None and lng_field is not None:
                    compatible.append(t)
        else:
            # Unknown renderer — return all types as safe fallback
            compatible = all_types

        logger.info(
            "compatible_types: renderer=%s total=%d compatible=%d",
            renderer, len(all_types), len(compatible),
        )
        return compatible

    # ── Dynamic query builder ──────────────────────────────────

    _DEFAULT_COLUMNS = ["label", "type", "created", "modified"]

    async def get_generic_columns(
        self, type_iri: str | None,
    ) -> tuple[list[PropertyShape], list[str]]:
        """Derive column metadata from SHACL shapes, with a safe default fallback.

        Returns ``(property_shapes, column_names)``.  The default columns
        (label, type, created, modified) are used when:
        - ``type_iri`` is None or empty
        - No SHACL shape exists for the type
        - The shape has ≤2 properties (too sparse to be useful)
        """
        if not type_iri or not self._shapes_service:
            return [], list(self._DEFAULT_COLUMNS)

        try:
            form: NodeShapeForm | None = await self._shapes_service.get_form_for_type(type_iri)
        except Exception:
            logger.warning("get_generic_columns: shapes lookup failed for %s", type_iri, exc_info=True)
            return [], list(self._DEFAULT_COLUMNS)

        if form is None or len(form.properties) <= 2:
            return [], list(self._DEFAULT_COLUMNS)

        # Deterministic sort: (order, name)
        sorted_props = sorted(form.properties, key=lambda p: (p.order, p.name))

        columns: list[str] = []
        seen: dict[str, int] = {}
        for prop in sorted_props:
            raw = _var_name_from_iri(prop.path)
            if raw in seen:
                seen[raw] += 1
                raw = f"{raw}_{seen[raw]}"
            else:
                seen[raw] = 1
            columns.append(raw)

        return sorted_props, columns

    async def build_dynamic_query(
        self, type_iri: str | None, renderer: str = "table",
        scope_filter: str | None = None,
    ) -> tuple[str, list[str]]:
        """Build a SPARQL query dynamically from SHACL metadata.

        Returns ``(sparql_query, column_names)``.  The query intentionally
        omits ``FROM`` clauses — ``scope_to_current_graph()`` adds them at
        execution time.

        Args:
            type_iri: Optional RDF type IRI to filter by.
            renderer: One of 'table', 'card', 'graph'.
            scope_filter: Optional SPARQL WHERE body from a saved query.
                When provided, a sub-select constraining ?s is injected
                into the generated query.
        """
        if renderer == "graph":
            query = self._build_graph_query(type_iri, scope_filter=scope_filter)
            logger.debug("build_dynamic_query: type=%s renderer=graph scope=%s", type_iri, bool(scope_filter))
            return query, []

        shapes, columns = await self.get_generic_columns(type_iri)

        if not shapes:
            # Default columns query
            query = self._build_default_select(type_iri, scope_filter=scope_filter)
        else:
            query = self._build_shacl_select(type_iri, shapes, columns, scope_filter=scope_filter)

        logger.debug(
            "build_dynamic_query: type=%s, columns=%d scope=%s", type_iri, len(columns), bool(scope_filter),
        )
        return query, columns

    @staticmethod
    def _build_default_select(type_iri: str | None, scope_filter: str | None = None) -> str:
        """Build a SELECT query using the 4 default columns."""
        type_filter = ""
        if type_iri:
            type_filter = f"  ?s rdf:type {safe_iri(type_iri)} .\n"

        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "SELECT ?s ?label ?type ?created ?modified\n"
            "WHERE {\n"
            f"{type_filter}"
            f"{scope_clause}"
            "  ?s rdf:type ?type .\n"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            "  OPTIONAL { ?s dcterms:created ?created }\n"
            "  OPTIONAL { ?s dcterms:modified ?modified }\n"
            "}"
        )

    @staticmethod
    def _build_shacl_select(
        type_iri: str | None,
        shapes: list[PropertyShape],
        columns: list[str],
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query from SHACL PropertyShape metadata."""
        select_vars = "?s ?label " + " ".join(f"?{c}" for c in columns)

        type_filter = ""
        if type_iri:
            type_filter = f"  ?s rdf:type {safe_iri(type_iri)} .\n"

        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        optionals: list[str] = []
        for shape, col in zip(shapes, columns):
            optionals.append(f"  OPTIONAL {{ ?s {safe_iri(shape.path)} ?{col} }}")

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            f"SELECT {select_vars}\n"
            "WHERE {\n"
            f"{type_filter}"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            + "\n".join(optionals) + "\n"
            "}"
        )

    @staticmethod
    def _build_graph_query(type_iri: str | None, scope_filter: str | None = None) -> str:
        """Build a CONSTRUCT query for the graph renderer."""
        type_filter = ""
        if type_iri:
            type_filter = f"  ?s rdf:type {safe_iri(type_iri)} .\n"

        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "CONSTRUCT { ?s ?p ?o . ?s rdf:type ?type . ?s rdfs:label ?label }\n"
            "WHERE {\n"
            f"{type_filter}"
            f"{scope_clause}"
            "  ?s ?p ?o .\n"
            "  ?s rdf:type ?type .\n"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            "}\n"
            "LIMIT 200"
        )

    async def get_view_specs_for_type(self, type_iri: str) -> list[ViewSpec]:
        """Filter view specs by target class matching type_iri.

        Args:
            type_iri: The target class IRI to filter by.

        Returns:
            List of ViewSpec instances targeting the given type.
        """
        all_specs = await self.get_all_view_specs()
        return [s for s in all_specs if s.target_class == type_iri]

    async def get_view_spec_by_iri(
        self,
        spec_iri: str,
        user_id: uuid.UUID | None = None,
    ) -> ViewSpec | None:
        """Find a single view spec by its IRI.

        For user-promoted views (urn:sempkm:user-view:*), queries the
        QueryService for promoted view data.

        Args:
            spec_iri: The view spec IRI to find.
            user_id: Optional user ID for user-view resolution.

        Returns:
            ViewSpec if found, None otherwise.
        """
        # Check for user-promoted view IRI
        if spec_iri.startswith("urn:sempkm:user-view:") and user_id and self._query_service:
            view_id_str = spec_iri.split(":")[-1]
            try:
                view_id = uuid.UUID(view_id_str)
            except ValueError:
                return None
            # Find the promoted view that matches this view ID
            promoted = await self._query_service.list_promoted_views(user_id)
            for pv in promoted:
                if pv.id == str(view_id):
                    columns = _extract_select_var_names(pv.query_text)
                    return ViewSpec(
                        spec_iri=f"urn:sempkm:user-view:{pv.id}",
                        label=pv.display_label,
                        target_class="",
                        renderer_type=pv.renderer_type,
                        sparql_query=pv.query_text,
                        columns=columns,
                        source_model="user",
                    )
            return None

        # Check generic specs
        if spec_iri.startswith("urn:sempkm:view:generic-"):
            for gs in self._generic_specs:
                if gs.spec_iri == spec_iri:
                    return gs
            return None

        all_specs = await self.get_all_view_specs()
        for s in all_specs:
            if s.spec_iri == spec_iri:
                return s
        return None

    async def get_user_promoted_view_specs(
        self, user_id: uuid.UUID,
    ) -> list[ViewSpec]:
        """Load promoted query views for a user, converting to ViewSpec dataclasses.

        These are NOT cached (per Research pitfall 1) -- fetched from RDF on each request.

        Args:
            user_id: The user whose promoted views to load.

        Returns:
            List of ViewSpec dataclasses for the user's promoted views.
        """
        if not self._query_service:
            return []
        promoted = await self._query_service.list_promoted_views(user_id)
        specs: list[ViewSpec] = []
        for pv in promoted:
            columns = _extract_select_var_names(pv.query_text)
            specs.append(ViewSpec(
                spec_iri=f"urn:sempkm:user-view:{pv.id}",
                label=pv.display_label,
                target_class="",
                renderer_type=pv.renderer_type,
                sparql_query=pv.query_text,
                columns=columns,
                source_model="user",
            ))
        return specs

    async def execute_table_query(
        self,
        spec: ViewSpec,
        page: int = 1,
        page_size: int = 25,
        sort_col: str = "",
        sort_dir: str = "asc",
        filter_text: str = "",
    ) -> dict:
        """Execute a view spec's SPARQL query with pagination and sorting.

        Uses scope_to_current_graph() to inject FROM <urn:sempkm:current>
        into the spec's SPARQL query. Uses a two-phase approach per Research
        Pitfall 5: wraps the original WHERE clause for pagination on distinct
        subjects, then retrieves properties.

        Args:
            spec: The ViewSpec containing the SPARQL query.
            page: Page number (1-based).
            page_size: Number of results per page.
            sort_col: Column variable name to sort by.
            sort_dir: Sort direction ('asc' or 'desc').
            filter_text: Text to filter results by (regex match on first column).

        Returns:
            Dict with keys: rows, total, page, page_size, total_pages, columns.
        """
        if not spec.sparql_query:
            return {
                "rows": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "columns": spec.columns,
            }

        # Scope the query to the current graph
        scoped_query = scope_to_current_graph(spec.sparql_query)

        # Extract WHERE clause body from the query
        where_body = _extract_where_body(scoped_query)
        from_clause = _extract_from_clause(scoped_query)

        if not where_body:
            logger.warning("Could not extract WHERE body from view spec query: %s", spec.spec_iri)
            return {
                "rows": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "columns": spec.columns,
            }

        # Inject filter if provided
        filter_clause = ""
        if filter_text:
            escaped = escape_sparql_regex(filter_text)
            # Match against the first column variable (typically ?title, ?name, ?label)
            first_col = spec.columns[0] if spec.columns else "s"
            filter_clause = f'FILTER(REGEX(STR(?{first_col}), "{escaped}", "i"))'

        # Build count query -- user views count all rows, model views count distinct ?s
        count_where = where_body
        if filter_clause:
            count_where = where_body + "\n  " + filter_clause

        count_expr = "COUNT(*)" if spec.source_model == "user" else "COUNT(DISTINCT ?s)"
        count_query = f"""SELECT ({count_expr} AS ?total)
{from_clause}
WHERE {{
  {count_where}
}}"""

        count_query = inject_prefixes(count_query)

        try:
            count_result = await self._client.query(count_query)
            count_bindings = count_result.get("results", {}).get("bindings", [])
            total = int(count_bindings[0]["total"]["value"]) if count_bindings else 0
        except Exception:
            logger.warning("Count query failed for view spec %s", spec.spec_iri, exc_info=True)
            total = 0

        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 0

        # Clamp page
        if page < 1:
            page = 1
        if total_pages > 0 and page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size

        # Build sort clause
        sort_variable = sort_col if sort_col else (spec.sort_default if spec.sort_default else "")
        order_clause = ""
        if sort_variable:
            direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
            order_clause = f"ORDER BY {direction}(?{sort_variable})"

        # Extract SELECT variables from original query
        select_vars = _extract_select_vars(spec.sparql_query)

        # Build data query with pagination
        data_where = where_body
        if filter_clause:
            data_where = where_body + "\n  " + filter_clause

        data_query = f"""SELECT {select_vars}
{from_clause}
WHERE {{
  {data_where}
}}
{order_clause}
LIMIT {page_size}
OFFSET {offset}"""

        data_query = inject_prefixes(data_query)

        try:
            data_result = await self._client.query(data_query)
            data_bindings = data_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Data query failed for view spec %s", spec.spec_iri, exc_info=True)
            data_bindings = []

        # Parse rows -- user views skip ?s-based deduplication (Pitfall 3)
        rows: list[dict] = []
        if spec.source_model == "user":
            for b in data_bindings:
                row: dict[str, str] = {}
                for col in spec.columns:
                    row[col] = b.get(col, {}).get("value", "")
                rows.append(row)
        else:
            seen_subjects: set[str] = set()
            for b in data_bindings:
                subject = b.get("s", {}).get("value", "")
                if subject in seen_subjects:
                    continue
                seen_subjects.add(subject)

                row = {"s": subject}
                for col in spec.columns:
                    row[col] = b.get(col, {}).get("value", "")
                rows.append(row)

        return {
            "rows": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "columns": spec.columns,
        }

    async def execute_cards_query(
        self,
        spec: ViewSpec,
        page: int = 1,
        page_size: int = 12,
        filter_text: str = "",
        group_by: str | None = None,
    ) -> dict:
        """Execute a view spec's SPARQL query for card rendering.

        Two-phase approach: (1) get distinct ?s subjects with pagination,
        (2) fetch all properties and relationships for those subjects.
        Resolves labels for all IRIs and truncates body snippets.

        Args:
            spec: The ViewSpec containing the SPARQL query.
            page: Page number (1-based).
            page_size: Number of cards per page.
            filter_text: Text to filter results by (regex match on first column).
            group_by: Optional property IRI to group cards by.

        Returns:
            Dict with keys: cards, total, page, page_size, total_pages,
            groups (if group_by), group_by, columns.
        """
        if not spec.sparql_query:
            return {
                "cards": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "groups": None,
                "group_by": group_by,
                "columns": spec.columns,
            }

        scoped_query = scope_to_current_graph(spec.sparql_query)
        where_body = _extract_where_body(scoped_query)
        from_clause = _extract_from_clause(scoped_query)

        if not where_body:
            logger.warning("Could not extract WHERE body from view spec query: %s", spec.spec_iri)
            return {
                "cards": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "groups": None,
                "group_by": group_by,
                "columns": spec.columns,
            }

        # Inject filter if provided
        filter_clause = ""
        if filter_text:
            escaped = escape_sparql_regex(filter_text)
            first_col = spec.columns[0] if spec.columns else "s"
            filter_clause = f'FILTER(REGEX(STR(?{first_col}), "{escaped}", "i"))'

        count_where = where_body
        if filter_clause:
            count_where = where_body + "\n  " + filter_clause

        # Count query
        count_query = f"""SELECT (COUNT(DISTINCT ?s) AS ?total)
{from_clause}
WHERE {{
  {count_where}
}}"""

        count_query = inject_prefixes(count_query)

        try:
            count_result = await self._client.query(count_query)
            count_bindings = count_result.get("results", {}).get("bindings", [])
            total = int(count_bindings[0]["total"]["value"]) if count_bindings else 0
        except Exception:
            logger.warning("Count query failed for cards view spec %s", spec.spec_iri, exc_info=True)
            total = 0

        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 0
        if page < 1:
            page = 1
        if total_pages > 0 and page > total_pages:
            page = total_pages

        offset = (page - 1) * page_size

        # Get distinct subjects with pagination
        data_where = where_body
        if filter_clause:
            data_where = where_body + "\n  " + filter_clause

        subjects_query = f"""SELECT DISTINCT ?s
{from_clause}
WHERE {{
  {data_where}
}}
LIMIT {page_size}
OFFSET {offset}"""

        subjects_query = inject_prefixes(subjects_query)

        try:
            subj_result = await self._client.query(subjects_query)
            subj_bindings = subj_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Subjects query failed for cards view spec %s", spec.spec_iri, exc_info=True)
            subj_bindings = []

        subject_iris = []
        seen = set()
        for b in subj_bindings:
            iri = b.get("s", {}).get("value", "")
            if iri and iri not in seen:
                subject_iris.append(iri)
                seen.add(iri)

        if not subject_iris:
            return {
                "cards": [],
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "groups": None,
                "group_by": group_by,
                "columns": spec.columns,
            }

        # Fetch all properties for these subjects
        values_clause = " ".join(safe_iri(iri) for iri in subject_iris)
        props_query = f"""SELECT ?s ?p ?o
FROM <{CURRENT_GRAPH}>
WHERE {{
  VALUES ?s {{ {values_clause} }}
  ?s ?p ?o .
  FILTER(isLiteral(?o))
}}"""

        try:
            props_result = await self._client.query(props_query)
            props_bindings = props_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Properties query failed for cards view spec %s", spec.spec_iri, exc_info=True)
            props_bindings = []

        # Build property maps per subject
        props_by_subject: dict[str, list[tuple[str, str]]] = {iri: [] for iri in subject_iris}
        body_by_subject: dict[str, str] = {}
        body_predicates: set[str] = set()
        desc_by_subject: dict[str, str] = {}

        all_iris_to_resolve: set[str] = set(subject_iris)

        def _is_body_predicate(pred: str) -> bool:
            """Match urn:sempkm:body and model-specific body predicates."""
            return pred == "urn:sempkm:body" or pred.endswith(":body")

        for b in props_bindings:
            s = b["s"]["value"]
            p = b["p"]["value"]
            o_val = b["o"]["value"]
            if s in props_by_subject:
                props_by_subject[s].append((p, o_val))
                all_iris_to_resolve.add(p)
                # Track body and description for snippets
                if _is_body_predicate(p):
                    body_by_subject[s] = o_val
                    body_predicates.add(p)
                elif p == "http://purl.org/dc/terms/description":
                    desc_by_subject[s] = o_val

        # Fetch outbound relationships (IRI objects, not literals)
        out_query = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s ?predicate ?object
FROM <{CURRENT_GRAPH}>
WHERE {{
  VALUES ?s {{ {values_clause} }}
  ?s ?predicate ?object .
  FILTER(isIRI(?object))
  FILTER(?predicate != rdf:type)
}}"""

        try:
            out_result = await self._client.query(out_query)
            out_bindings = out_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Outbound query failed for cards view spec %s", spec.spec_iri, exc_info=True)
            out_bindings = []

        outbound_by_subject: dict[str, list[tuple[str, str]]] = {iri: [] for iri in subject_iris}
        for b in out_bindings:
            s = b["s"]["value"]
            pred = b["predicate"]["value"]
            obj = b["object"]["value"]
            if s in outbound_by_subject:
                outbound_by_subject[s].append((pred, obj))
                all_iris_to_resolve.add(pred)
                all_iris_to_resolve.add(obj)

        # Fetch inbound relationships
        in_query = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s ?predicate ?subject
FROM <{CURRENT_GRAPH}>
WHERE {{
  VALUES ?s {{ {values_clause} }}
  ?subject ?predicate ?s .
  FILTER(isIRI(?subject))
  FILTER(?predicate != rdf:type)
}}"""

        try:
            in_result = await self._client.query(in_query)
            in_bindings = in_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Inbound query failed for cards view spec %s", spec.spec_iri, exc_info=True)
            in_bindings = []

        inbound_by_subject: dict[str, list[tuple[str, str]]] = {iri: [] for iri in subject_iris}
        for b in in_bindings:
            s = b["s"]["value"]
            pred = b["predicate"]["value"]
            subj = b["subject"]["value"]
            if s in inbound_by_subject:
                inbound_by_subject[s].append((pred, subj))
                all_iris_to_resolve.add(pred)
                all_iris_to_resolve.add(subj)

        # Resolve all labels in one batch
        labels = await self._label_service.resolve_batch(list(all_iris_to_resolve)) if all_iris_to_resolve else {}

        # Build card data
        cards: list[dict] = []
        for iri in subject_iris:
            # Snippet: prefer body, fallback to description
            snippet = ""
            if iri in body_by_subject:
                snippet = body_by_subject[iri][:300]
                if len(body_by_subject[iri]) > 300:
                    snippet += "..."
            elif iri in desc_by_subject:
                snippet = desc_by_subject[iri][:300]
                if len(desc_by_subject[iri]) > 300:
                    snippet += "..."

            # Properties list (name/value pairs with resolved labels)
            properties = []
            for p, v in props_by_subject[iri]:
                # Skip body predicates and rdf:type from property display
                if p == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" or _is_body_predicate(p):
                    continue
                properties.append({
                    "name": labels.get(p, _local_name(p)),
                    "value": v,
                })

            # Outbound relations
            outbound_relations = []
            for pred, target in outbound_by_subject[iri]:
                outbound_relations.append({
                    "predicate_label": labels.get(pred, _local_name(pred)),
                    "target_iri": target,
                    "target_label": labels.get(target, _local_name(target)),
                    "direction": "outbound",
                })

            # Inbound relations
            inbound_relations = []
            for pred, source in inbound_by_subject[iri]:
                inbound_relations.append({
                    "predicate_label": labels.get(pred, _local_name(pred)),
                    "target_iri": source,
                    "target_label": labels.get(source, _local_name(source)),
                    "direction": "inbound",
                })

            cards.append({
                "iri": iri,
                "label": labels.get(iri, _local_name(iri)),
                "snippet": snippet,
                "properties": properties,
                "outbound_relations": outbound_relations,
                "inbound_relations": inbound_relations,
            })

        # Collect groupable property IRIs from card data
        groupable_props: list[dict[str, str]] = []
        seen_props: set[str] = set()
        for card in cards:
            for prop in card["properties"]:
                prop_name = prop["name"]
                if prop_name not in seen_props:
                    seen_props.add(prop_name)
                    # Find the original IRI for this property label
                    prop_iri = ""
                    for p, _ in props_by_subject.get(card["iri"], []):
                        if labels.get(p, _local_name(p)) == prop_name:
                            prop_iri = p
                            break
                    groupable_props.append({"name": prop_name, "iri": prop_iri})

        # Grouping by property value
        groups = None
        if group_by and cards:
            group_map: dict[str, list[dict]] = {}
            group_label = labels.get(group_by, _local_name(group_by))
            for card in cards:
                # Find the grouping value from properties
                group_vals: list[str] = []
                for prop in card["properties"]:
                    # Match by original IRI or resolved label
                    if prop["name"] == group_label or prop["name"] == _local_name(group_by):
                        raw = prop["value"]
                        # Split comma-separated values (e.g., tags)
                        if "," in raw:
                            group_vals.extend(
                                v.strip() for v in raw.split(",") if v.strip()
                            )
                        else:
                            group_vals.append(raw)
                        break
                if not group_vals:
                    group_vals = ["Ungrouped"]
                for gv in group_vals:
                    if gv not in group_map:
                        group_map[gv] = []
                    group_map[gv].append(card)

            groups = [
                {"group_label": k, "cards": v}
                for k, v in sorted(group_map.items(), key=lambda x: (x[0] == "Ungrouped", x[0]))
            ]

        return {
            "cards": cards,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "groups": groups,
            "group_by": group_by,
            "columns": groupable_props,
        }

    async def execute_graph_query(self, spec: ViewSpec) -> dict:
        """Execute a view spec's SPARQL CONSTRUCT query for graph visualization.

        Scopes the query to both current and inferred graphs, executes as
        CONSTRUCT to get Turtle bytes, parses with rdflib, and converts to
        Cytoscape.js-compatible JSON with nodes, edges, and type-to-color mapping.
        Inferred edges are annotated so the frontend can render them with
        dashed lines.

        Args:
            spec: The ViewSpec containing a CONSTRUCT SPARQL query.

        Returns:
            Dict with keys: nodes, edges, type_colors.
        """
        if not spec.sparql_query:
            return {"nodes": [], "edges": [], "type_colors": {}}

        # scope_to_current_graph now includes FROM <urn:sempkm:inferred> by default
        scoped_query = scope_to_current_graph(spec.sparql_query)

        try:
            turtle_bytes = await self._client.construct(scoped_query)
        except Exception:
            logger.warning("CONSTRUCT query failed for view spec %s", spec.spec_iri, exc_info=True)
            return {"nodes": [], "edges": [], "type_colors": {}}

        # Identify edges that exist only in the inferred graph (not in current)
        # by querying the inferred graph for all object properties
        inferred_edge_set: set[tuple[str, str, str]] = set()
        try:
            inf_query = """SELECT ?s ?p ?o
WHERE {
  GRAPH <urn:sempkm:inferred> {
    ?s ?p ?o .
    FILTER(isIRI(?o))
  }
}"""
            inf_result = await self._client.query(inf_query)
            for b in inf_result.get("results", {}).get("bindings", []):
                inferred_edge_set.add((
                    b["s"]["value"], b["p"]["value"], b["o"]["value"]
                ))
        except Exception:
            logger.warning("Inferred edges identification query failed", exc_info=True)

        # Identify edges from the mirrored graph
        mirrored_edge_set: set[tuple[str, str, str]] = set()
        try:
            mir_query = """SELECT ?s ?p ?o
WHERE {
  GRAPH <urn:sempkm:mirrored> {
    ?s ?p ?o .
    FILTER(isIRI(?o))
  }
}"""
            mir_result = await self._client.query(mir_query)
            for b in mir_result.get("results", {}).get("bindings", []):
                mirrored_edge_set.add((
                    b["s"]["value"], b["p"]["value"], b["o"]["value"]
                ))
        except Exception:
            logger.warning("Mirrored edges identification query failed", exc_info=True)

        return await self._parse_graph_results(turtle_bytes, inferred_edge_set, mirrored_edge_set)

    async def expand_neighbors(self, node_iri: str) -> dict:
        """Fetch all triples where node_iri is subject or object.

        Executes a SPARQL CONSTRUCT for both directions (outbound and inbound),
        scoped to the current, inferred, and mirrored graphs.

        Args:
            node_iri: The IRI of the node to expand.

        Returns:
            Dict with keys: nodes, edges, type_colors.
        """
        safe_node = safe_iri(node_iri)
        construct_query = f"""CONSTRUCT {{ ?s ?p ?o }}
FROM <{CURRENT_GRAPH}>
FROM <urn:sempkm:inferred>
FROM <urn:sempkm:mirrored>
WHERE {{
  {{ {safe_node} ?p ?o . BIND({safe_node} AS ?s) . FILTER(isIRI(?o)) }}
  UNION
  {{ ?s ?p {safe_node} . BIND({safe_node} AS ?o) . FILTER(isIRI(?s)) }}
}}"""

        try:
            turtle_bytes = await self._client.construct(construct_query)
        except Exception:
            logger.warning("Expand neighbors query failed for %s", node_iri, exc_info=True)
            return {"nodes": [], "edges": [], "type_colors": {}}

        # Identify which edges come from the inferred graph
        inferred_edges_query = f"""SELECT ?s ?p ?o WHERE {{
  GRAPH <urn:sempkm:inferred> {{
    {{ {safe_node} ?p ?o . BIND({safe_node} AS ?s) . FILTER(isIRI(?o)) }}
    UNION
    {{ ?s ?p {safe_node} . BIND({safe_node} AS ?o) . FILTER(isIRI(?s)) }}
  }}
}}"""
        inferred_edge_set: set[tuple[str, str, str]] = set()
        try:
            inf_result = await self._client.query(inferred_edges_query)
            for b in inf_result.get("results", {}).get("bindings", []):
                inferred_edge_set.add((
                    b["s"]["value"], b["p"]["value"], b["o"]["value"]
                ))
        except Exception:
            logger.warning("Inferred edges query failed for %s", node_iri, exc_info=True)

        # Identify which edges come from the mirrored graph
        mirrored_edges_query = f"""SELECT ?s ?p ?o WHERE {{
  GRAPH <urn:sempkm:mirrored> {{
    {{ {safe_node} ?p ?o . BIND({safe_node} AS ?s) . FILTER(isIRI(?o)) }}
    UNION
    {{ ?s ?p {safe_node} . BIND({safe_node} AS ?o) . FILTER(isIRI(?s)) }}
  }}
}}"""
        mirrored_edge_set: set[tuple[str, str, str]] = set()
        try:
            mir_result = await self._client.query(mirrored_edges_query)
            for b in mir_result.get("results", {}).get("bindings", []):
                mirrored_edge_set.add((
                    b["s"]["value"], b["p"]["value"], b["o"]["value"]
                ))
        except Exception:
            logger.warning("Mirrored edges query failed for %s", node_iri, exc_info=True)

        return await self._parse_graph_results(turtle_bytes, inferred_edge_set, mirrored_edge_set)

    # ── Calendar renderer ──────────────────────────────────────

    # Well-known date path IRI fragments (matched case-insensitively against
    # the local name of sh:path).  These are checked even when sh:datatype is
    # absent — e.g. bpkm:Event's schema:startDate has no datatype declaration.
    _WELL_KNOWN_DATE_PATHS: set[str] = {
        "startdate",
        "enddate",
        "duedate",
        "completeddate",
        "targetdate",
        "scheduledstart",
        "scheduledend",
    }

    # Priority order for selecting the *start* date field.
    # "scheduledstart" is highest priority for Task time-blocking.
    _START_DATE_PRIORITY = ["scheduledstart", "startdate", "duedate", "targetdate", "created"]

    _XSD_DATE_TYPES: set[str] = {
        "http://www.w3.org/2001/XMLSchema#date",
        "http://www.w3.org/2001/XMLSchema#dateTime",
    }

    async def _detect_date_fields(
        self, type_iri: str,
    ) -> tuple[PropertyShape | None, PropertyShape | None]:
        """Find date properties suitable for calendar start/end fields.

        Uses two heuristics:
        1. ``prop.datatype`` is ``xsd:date`` or ``xsd:dateTime``
        2. The local-name of ``prop.path`` matches a well-known date IRI
           (e.g. ``schema:startDate``, ``bpkm:dueDate``) — even when
           ``prop.datatype`` is ``None``.

        Returns ``(start_field, end_field)`` or ``(None, None)``.
        """
        if not self._shapes_service:
            return None, None

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_date_fields: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return None, None

        if form is None:
            return None, None

        # Collect all properties that look like dates
        date_props: list[PropertyShape] = []
        for prop in form.properties:
            local = _local_name(prop.path).lower()
            if prop.datatype in self._XSD_DATE_TYPES:
                date_props.append(prop)
            elif local in self._WELL_KNOWN_DATE_PATHS:
                date_props.append(prop)

        if not date_props:
            return None, None

        # Pick start field by priority
        start_field: PropertyShape | None = None
        for keyword in self._START_DATE_PRIORITY:
            for prop in date_props:
                if keyword in _local_name(prop.path).lower():
                    start_field = prop
                    break
            if start_field:
                break

        # Fallback: first date property
        if start_field is None:
            start_field = date_props[0]

        # Pick end field: prefer path containing "enddate" or "scheduledend"
        end_field: PropertyShape | None = None
        _END_KEYWORDS = ("scheduledend", "enddate")
        for kw in _END_KEYWORDS:
            for prop in date_props:
                local = _local_name(prop.path).lower()
                if kw in local and prop is not start_field:
                    end_field = prop
                    break
            if end_field:
                break

        logger.debug(
            "_detect_date_fields: type=%s start=%s end=%s",
            type_iri,
            start_field.path if start_field else None,
            end_field.path if end_field else None,
        )
        return start_field, end_field

    @staticmethod
    def _expand_rrule(
        rrule_str: str,
        dtstart: datetime,
        range_start: datetime,
        range_end: datetime,
        exdates: list[date] | None = None,
        max_instances: int = 52,
    ) -> list[datetime]:
        """Expand an RFC 5545 RRULE string into occurrence datetimes.

        Uses ``python-dateutil`` to parse the RRULE and generate occurrences
        within ``[range_start, range_end]``, excluding any dates in ``exdates``.
        Returns at most ``max_instances`` occurrences.

        On malformed input, logs a warning and returns an empty list — never
        raises.

        Args:
            rrule_str: RFC 5545 RRULE string (e.g. ``FREQ=WEEKLY;BYDAY=FR``).
            dtstart: The anchor datetime for recurrence calculation.
            range_start: Start of the expansion window (inclusive).
            range_end: End of the expansion window (inclusive).
            exdates: Optional dates to exclude from results.
            max_instances: Maximum number of occurrences to return (default 52).

        Returns:
            List of occurrence datetimes within the window.
        """
        try:
            rule = rrulestr(rrule_str, dtstart=dtstart)
            rset = rruleset()
            rset.rrule(rule)
            if exdates:
                for exd in exdates:
                    # Convert date to datetime at midnight for rruleset.exdate()
                    if isinstance(exd, date) and not isinstance(exd, datetime):
                        exd = datetime(exd.year, exd.month, exd.day)
                    rset.exdate(exd)
            occurrences = rset.between(range_start, range_end, inc=True)
            return list(occurrences[:max_instances])
        except Exception:
            logger.warning(
                "_expand_rrule: failed to parse RRULE %r with dtstart=%s",
                rrule_str, dtstart, exc_info=True,
            )
            return []

    @staticmethod
    def _build_calendar_select(
        type_iri: str,
        start_path: str,
        end_path: str | None = None,
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query that fetches subjects with date values.

        Args:
            type_iri: The RDF type IRI to filter by.
            start_path: The property IRI for the start date field.
            end_path: Optional property IRI for the end date field.
            scope_filter: Optional SPARQL WHERE body injected as sub-select.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        end_clause = ""
        end_var = ""
        if end_path:
            end_var = " ?endDate"
            end_clause = f"  OPTIONAL {{ ?s {safe_iri(end_path)} ?endDate }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            f"SELECT ?s ?label ?startDate{end_var} ?recurrenceRule ?exceptionDates\n"
            "WHERE {\n"
            f"  ?s rdf:type {safe_iri(type_iri)} .\n"
            f"  ?s {safe_iri(start_path)} ?startDate .\n"
            f"{end_clause}"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            "  OPTIONAL { ?s <urn:sempkm:model:basic-pkm:recurrenceRule> ?recurrenceRule }\n"
            "  OPTIONAL { ?s <urn:sempkm:model:basic-pkm:exceptionDates> ?exceptionDates }\n"
            "}"
        )

    async def execute_calendar_query(
        self,
        type_iri: str,
        start_field: PropertyShape,
        end_field: PropertyShape | None = None,
        scope_filter: str | None = None,
    ) -> dict:
        """Execute a calendar query and return FullCalendar-compatible events.

        Maps SPARQL results to FullCalendar event objects with ``id``,
        ``title``, ``start``, ``end``, ``allDay``, and ``extendedProps``.

        Detects ``allDay`` by checking whether the start value looks like
        an ``xsd:date`` (no 'T' time separator) vs ``xsd:dateTime``.

        Returns:
            ``{"events": [...], "date_fields": {"start": {...}, "end": {...} | None}}``
        """
        query = self._build_calendar_select(
            type_iri,
            start_field.path,
            end_path=end_field.path if end_field else None,
            scope_filter=scope_filter,
        )
        scoped = scope_to_current_graph(query)

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_calendar_query: query failed for type=%s start=%s",
                type_iri,
                start_field.path,
                exc_info=True,
            )
            return {
                "events": [],
                "date_fields": {
                    "start": {"path": start_field.path, "name": start_field.name},
                    "end": {"path": end_field.path, "name": end_field.name} if end_field else None,
                },
            }

        bindings = result.get("results", {}).get("bindings", [])

        events: list[dict] = []
        seen: set[str] = set()
        virtual_count = 0

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expansion_start = now - timedelta(days=183)  # ~6 months back
        expansion_end = now + timedelta(days=183)     # ~6 months forward

        for b in bindings:
            iri = b.get("s", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)

            label = b.get("label", {}).get("value", "") or _local_name(iri)
            start_val = b.get("startDate", {}).get("value", "")
            end_val = b.get("endDate", {}).get("value", "") if end_field else ""
            rrule_val = b.get("recurrenceRule", {}).get("value", "")
            exdates_val = b.get("exceptionDates", {}).get("value", "")

            if not start_val:
                continue

            # Detect allDay: xsd:date has no 'T', xsd:dateTime does
            all_day = "T" not in start_val

            event: dict = {
                "id": iri,
                "title": label,
                "start": start_val,
                "allDay": all_day,
                "extendedProps": {"iri": iri},
            }
            if end_val:
                event["end"] = end_val

            # Add recurrenceRule to master event's extendedProps for frontend indicator
            if rrule_val:
                event["extendedProps"]["recurrenceRule"] = rrule_val

            events.append(event)

            # ── RRULE expansion: generate virtual events ──
            if rrule_val:
                # Parse dtstart from start_val
                try:
                    if "T" in start_val:
                        # Strip timezone to keep naive — rruleset.between()
                        # needs consistent naive datetimes
                        dt_parsed = datetime.fromisoformat(
                            start_val.replace("Z", "+00:00")
                        )
                        dtstart = dt_parsed.replace(tzinfo=None)
                    else:
                        parsed_date = date.fromisoformat(start_val[:10])
                        dtstart = datetime(parsed_date.year, parsed_date.month, parsed_date.day)
                except (ValueError, TypeError):
                    dtstart = None

                if dtstart is None:
                    continue

                # Parse exdates (comma-separated ISO dates)
                exdates: list[date] | None = None
                if exdates_val:
                    exdates = []
                    for part in exdates_val.split(","):
                        part = part.strip()
                        if part:
                            try:
                                exdates.append(date.fromisoformat(part[:10]))
                            except (ValueError, TypeError):
                                pass

                # Compute original duration (default 1 hour if no end)
                if end_val:
                    try:
                        if "T" in end_val:
                            dt_end = datetime.fromisoformat(
                                end_val.replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        else:
                            parsed_end = date.fromisoformat(end_val[:10])
                            dt_end = datetime(parsed_end.year, parsed_end.month, parsed_end.day)
                        duration = dt_end - dtstart
                    except (ValueError, TypeError):
                        duration = timedelta(hours=1)
                else:
                    duration = timedelta(hours=1) if not all_day else timedelta(days=1)

                occurrences = self._expand_rrule(
                    rrule_val, dtstart, expansion_start, expansion_end,
                    exdates=exdates,
                )

                master_date = dtstart.date() if isinstance(dtstart, datetime) else dtstart
                for occ in occurrences:
                    occ_date = occ.date() if isinstance(occ, datetime) else occ
                    # Skip the master event's own date — it's already in events
                    if occ_date == master_date:
                        continue

                    if all_day:
                        occ_start = occ_date.isoformat()
                        occ_end = (occ_date + duration).isoformat() if duration.days > 1 else ""
                    else:
                        occ_start = occ.isoformat()
                        occ_end = (occ + duration).isoformat()

                    synth_id = f"{iri}__recurrence__{occ_date.isoformat()}"
                    virtual_event: dict = {
                        "id": synth_id,
                        "title": label,
                        "start": occ_start,
                        "allDay": all_day,
                        "extendedProps": {
                            "iri": iri,
                            "isVirtual": True,
                            "masterIri": iri,
                            "recurrenceRule": rrule_val,
                        },
                    }
                    if occ_end:
                        virtual_event["end"] = occ_end

                    events.append(virtual_event)
                    virtual_count += 1

        logger.info(
            "execute_calendar_query: type=%s events=%d (real=%d virtual=%d)",
            type_iri, len(events), len(seen), virtual_count,
        )

        return {
            "events": events,
            "date_fields": {
                "start": {"path": start_field.path, "name": start_field.name},
                "end": {"path": end_field.path, "name": end_field.name} if end_field else None,
            },
        }

    # Color assignments for merged calendar view (type IRI → hex color)
    _CALENDAR_TYPE_COLORS: dict[str, str] = {
        "urn:sempkm:model:basic-pkm:Event": "#8b5cf6",   # purple
        "urn:sempkm:model:basic-pkm:Task": "#10b981",    # green
    }

    async def execute_merged_calendar_query(
        self,
        scope_filter: str | None = None,
    ) -> dict:
        """Query both Event and Task types and merge into one event list.

        For each type in ``_CALENDAR_TYPE_COLORS``, detects date fields,
        runs ``execute_calendar_query()``, and annotates each result with
        ``sourceType`` and ``backgroundColor`` for FullCalendar styling.

        Args:
            scope_filter: Optional SPARQL WHERE body from a saved query.

        Returns:
            ``{"events": [...], "types_found": [...]}``
        """
        all_events: list[dict] = []
        types_found: list[str] = []

        for type_iri, color in self._CALENDAR_TYPE_COLORS.items():
            start_field, end_field = await self._detect_date_fields(type_iri)
            if start_field is None:
                logger.debug(
                    "execute_merged_calendar_query: skipping %s (no date fields)",
                    type_iri,
                )
                continue

            result = await self.execute_calendar_query(
                type_iri, start_field, end_field, scope_filter=scope_filter,
            )

            events = result.get("events", [])
            # Derive a short sourceType label from the type IRI local name
            local = type_iri.rsplit(":", 1)[-1] if ":" in type_iri else type_iri
            source_type = local.lower()  # "event" or "task"

            for ev in events:
                ev["backgroundColor"] = color
                ev["borderColor"] = color
                ep = ev.setdefault("extendedProps", {})
                ep["sourceType"] = source_type
                ep["typeIri"] = type_iri

            all_events.extend(events)
            types_found.append(type_iri)

            logger.info(
                "execute_merged_calendar_query: type=%s events=%d color=%s",
                type_iri, len(events), color,
            )

        return {"events": all_events, "types_found": types_found}

    # ── Map renderer ───────────────────────────────────────────

    _WELL_KNOWN_GEO_PATHS: set[str] = {
        "lat", "latitude", "long", "longitude", "lng",
    }

    _XSD_DECIMAL_TYPES: set[str] = {
        "http://www.w3.org/2001/XMLSchema#decimal",
        "http://www.w3.org/2001/XMLSchema#float",
        "http://www.w3.org/2001/XMLSchema#double",
    }

    _WELL_KNOWN_GEO_IRIS: dict[str, str] = {
        "http://www.w3.org/2003/01/geo/wgs84_pos#lat": "lat",
        "http://www.w3.org/2003/01/geo/wgs84_pos#long": "lng",
        "http://schema.org/latitude": "lat",
        "http://schema.org/longitude": "lng",
    }

    async def _detect_geo_fields(
        self, type_iri: str,
    ) -> tuple[PropertyShape | None, PropertyShape | None]:
        """Find lat/lng property pairs suitable for map rendering.

        Uses two heuristics in priority order:
        1. Well-known full IRI match (wgs84:lat/long, schema:latitude/longitude)
        2. Local-name heuristic against ``_WELL_KNOWN_GEO_PATHS``

        Returns ``(lat_field, lng_field)`` or ``(None, None)``.
        Both must be found — if only one is detected, returns ``(None, None)``.
        """
        if not self._shapes_service:
            return None, None

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_geo_fields: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return None, None

        if form is None:
            return None, None

        lat_field: PropertyShape | None = None
        lng_field: PropertyShape | None = None

        # Pass 1: well-known full IRI match (highest priority)
        for prop in form.properties:
            role = self._WELL_KNOWN_GEO_IRIS.get(prop.path)
            if role == "lat" and lat_field is None:
                lat_field = prop
            elif role == "lng" and lng_field is None:
                lng_field = prop

        if lat_field and lng_field:
            logger.debug(
                "_detect_geo_fields: IRI match type=%s lat=%s lng=%s",
                type_iri, lat_field.path, lng_field.path,
            )
            return lat_field, lng_field

        # Pass 2: local-name heuristic
        lat_field = None
        lng_field = None
        for prop in form.properties:
            local = _local_name(prop.path).lower()
            if local not in self._WELL_KNOWN_GEO_PATHS:
                continue
            if local in ("lat", "latitude") and lat_field is None:
                lat_field = prop
            elif local in ("long", "longitude", "lng") and lng_field is None:
                lng_field = prop

        if lat_field and lng_field:
            logger.debug(
                "_detect_geo_fields: heuristic match type=%s lat=%s lng=%s",
                type_iri, lat_field.path, lng_field.path,
            )
            return lat_field, lng_field

        logger.debug(
            "_detect_geo_fields: no geo pair found for type=%s (lat=%s lng=%s)",
            type_iri,
            lat_field.path if lat_field else None,
            lng_field.path if lng_field else None,
        )
        return None, None

    @staticmethod
    def _build_map_select(
        type_iri: str,
        lat_path: str,
        lng_path: str,
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query that fetches subjects with lat/lng values.

        Both lat and lng are required (non-OPTIONAL) — objects without
        both coordinates are excluded from results.

        Args:
            type_iri: The RDF type IRI to filter by.
            lat_path: The property IRI for the latitude field.
            lng_path: The property IRI for the longitude field.
            scope_filter: Optional SPARQL WHERE body injected as sub-select.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "SELECT ?s ?label ?lat ?lng\n"
            "WHERE {\n"
            f"  ?s rdf:type {safe_iri(type_iri)} .\n"
            f"  ?s {safe_iri(lat_path)} ?lat .\n"
            f"  ?s {safe_iri(lng_path)} ?lng .\n"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            "}"
        )

    async def execute_map_query(
        self,
        type_iri: str,
        lat_field: PropertyShape,
        lng_field: PropertyShape,
        scope_filter: str | None = None,
    ) -> dict:
        """Execute a map query and return marker data.

        Maps SPARQL results to marker objects with ``iri``, ``title``,
        ``lat``, and ``lng``. Deduplicates by IRI and parses coordinates
        as floats.

        Returns:
            ``{"markers": [...], "geo_fields": {"lat": {...}, "lng": {...}}}``
        """
        query = self._build_map_select(
            type_iri,
            lat_field.path,
            lng_field.path,
            scope_filter=scope_filter,
        )
        scoped = scope_to_current_graph(query)

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_map_query: query failed for type=%s lat=%s lng=%s",
                type_iri, lat_field.path, lng_field.path,
                exc_info=True,
            )
            return {
                "markers": [],
                "geo_fields": {
                    "lat": {"path": lat_field.path, "name": lat_field.name},
                    "lng": {"path": lng_field.path, "name": lng_field.name},
                },
            }

        bindings = result.get("results", {}).get("bindings", [])

        markers: list[dict] = []
        seen: set[str] = set()

        for b in bindings:
            iri = b.get("s", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)

            label = b.get("label", {}).get("value", "") or _local_name(iri)
            lat_val = b.get("lat", {}).get("value", "")
            lng_val = b.get("lng", {}).get("value", "")

            if not lat_val or not lng_val:
                continue

            try:
                lat_float = float(lat_val)
                lng_float = float(lng_val)
            except (ValueError, TypeError):
                logger.debug(
                    "execute_map_query: skipping %s — bad coords lat=%r lng=%r",
                    iri, lat_val, lng_val,
                )
                continue

            markers.append({
                "iri": iri,
                "title": label,
                "lat": lat_float,
                "lng": lng_float,
            })

        logger.info(
            "execute_map_query: type=%s markers=%d",
            type_iri, len(markers),
        )

        return {
            "markers": markers,
            "geo_fields": {
                "lat": {"path": lat_field.path, "name": lat_field.name},
                "lng": {"path": lng_field.path, "name": lng_field.name},
            },
        }

    # ── Kanban renderer ────────────────────────────────────────

    async def _detect_status_field(
        self, type_iri: str,
    ) -> tuple[PropertyShape | None, list[str]]:
        """Find the first SHACL property with ``sh:in`` values for kanban columns.

        Prefers a property whose ``path`` contains "status" (case-insensitive).
        Falls back to the first property with non-empty ``in_values``.

        Returns:
            ``(property_shape, in_values)`` or ``(None, [])`` when no suitable
            property exists.
        """
        if not self._shapes_service:
            return None, []

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_status_field: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return None, []

        if form is None:
            return None, []

        first_with_in: PropertyShape | None = None
        first_in_values: list[str] = []

        for prop in form.properties:
            if not prop.in_values:
                continue
            # Prefer property with "status" in path
            if "status" in prop.path.lower():
                return prop, list(prop.in_values)
            if first_with_in is None:
                first_with_in = prop
                first_in_values = list(prop.in_values)

        if first_with_in is not None:
            return first_with_in, first_in_values

        return None, []

    async def _detect_enrichment_fields(
        self, type_iri: str, status_field: PropertyShape | None = None,
    ) -> dict:
        """Detect priority-like and date-like fields for kanban card enrichment.

        Priority: first ``sh:in`` property whose path contains 'priority'
        (case-insensitive), falling back to any ``sh:in`` property that
        isn't the status field.

        Date: reuses ``_detect_date_fields()`` logic — takes the start field.

        Returns:
            ``{"priority_field": PropertyShape|None, "date_field": PropertyShape|None}``
        """
        result: dict = {"priority_field": None, "date_field": None}

        if not self._shapes_service:
            return result

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_enrichment_fields: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return result

        if form is None:
            return result

        # ── Priority field: sh:in property, prefer 'priority' in path ──
        status_path = status_field.path if status_field else None
        first_non_status_in: PropertyShape | None = None

        for prop in form.properties:
            if not prop.in_values:
                continue
            # Skip the status field itself
            if status_path and prop.path == status_path:
                continue
            if "priority" in prop.path.lower():
                result["priority_field"] = prop
                break
            if first_non_status_in is None:
                first_non_status_in = prop

        if result["priority_field"] is None and first_non_status_in is not None:
            result["priority_field"] = first_non_status_in

        # ── Date field: reuse _detect_date_fields start field ──
        start_field, _ = await self._detect_date_fields(type_iri)
        result["date_field"] = start_field

        return result

    @staticmethod
    def _build_kanban_select(
        type_iri: str,
        status_path: str,
        scope_filter: str | None = None,
        priority_path: str | None = None,
        date_path: str | None = None,
    ) -> str:
        """Build a SELECT query that fetches subjects with their status value.

        Args:
            type_iri: The RDF type IRI to filter by.
            status_path: The property IRI for the status field.
            scope_filter: Optional SPARQL WHERE body injected as sub-select.
            priority_path: Optional property IRI for priority enrichment.
            date_path: Optional property IRI for due-date enrichment.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        # Build enrichment OPTIONAL clauses and SELECT vars
        enrichment_vars = ""
        enrichment_clauses = ""
        if priority_path:
            enrichment_vars += " ?priorityValue"
            enrichment_clauses += f"  OPTIONAL {{ ?s {safe_iri(priority_path)} ?priorityValue }}\n"
        if date_path:
            enrichment_vars += " ?dateValue"
            enrichment_clauses += f"  OPTIONAL {{ ?s {safe_iri(date_path)} ?dateValue }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            f"SELECT ?s ?label ?statusValue{enrichment_vars}\n"
            "WHERE {\n"
            f"  ?s rdf:type {safe_iri(type_iri)} .\n"
            f"  ?s {safe_iri(status_path)} ?statusValue .\n"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            f"{enrichment_clauses}"
            "}"
        )

    async def execute_kanban_query(
        self,
        type_iri: str,
        status_field: PropertyShape,
        status_values: list[str],
        scope_filter: str | None = None,
    ) -> dict:
        """Execute a kanban grouping query and return column data.

        Groups results into columns matching the ``status_values`` order
        from ``sh:in``.  Objects whose status value does not appear in the
        list are placed in an "Unset" column appended at the end.

        Detects enrichment fields (priority, due date) from SHACL shapes
        and includes them in each item dict when available.

        Returns:
            ``{"columns": [...], "status_field": {...}, "total": N,
              "enrichment": {...}}``
        """
        # Detect enrichment fields
        enrichment_meta = await self._detect_enrichment_fields(
            type_iri, status_field=status_field,
        )
        priority_field = enrichment_meta["priority_field"]
        date_field = enrichment_meta["date_field"]

        query = self._build_kanban_select(
            type_iri,
            status_field.path,
            scope_filter=scope_filter,
            priority_path=priority_field.path if priority_field else None,
            date_path=date_field.path if date_field else None,
        )
        scoped = scope_to_current_graph(query)

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_kanban_query: query failed for type=%s status=%s",
                type_iri,
                status_field.path,
                exc_info=True,
            )
            return {
                "columns": [
                    {"value": v, "label": v.replace("-", " ").replace("_", " ").title(), "items": []}
                    for v in status_values
                ],
                "status_field": {"path": status_field.path, "name": status_field.name},
                "enrichment": self._build_enrichment_metadata(priority_field, date_field),
                "total": 0,
            }

        bindings = result.get("results", {}).get("bindings", [])

        # Build column buckets keyed by status value
        buckets: dict[str, list[dict]] = {v: [] for v in status_values}
        unset_items: list[dict] = []
        seen: set[str] = set()

        for b in bindings:
            iri = b.get("s", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)

            label = b.get("label", {}).get("value", "") or _local_name(iri)
            status_val = b.get("statusValue", {}).get("value", "")

            item: dict = {"iri": iri, "label": label}

            # Enrichment values (always present as keys, None when unset)
            priority_raw = b.get("priorityValue", {}).get("value") if priority_field else None
            date_raw = b.get("dateValue", {}).get("value") if date_field else None
            item["priority"] = priority_raw
            item["due_date"] = date_raw

            if status_val in buckets:
                buckets[status_val].append(item)
            else:
                unset_items.append(item)

        columns = []
        for v in status_values:
            columns.append({
                "value": v,
                "label": v.replace("-", " ").replace("_", " ").title(),
                "items": buckets[v],
            })

        if unset_items:
            columns.append({
                "value": "__unset__",
                "label": "Unset",
                "items": unset_items,
            })

        total = len(seen)

        return {
            "columns": columns,
            "status_field": {"path": status_field.path, "name": status_field.name},
            "enrichment": self._build_enrichment_metadata(priority_field, date_field),
            "total": total,
        }

    @staticmethod
    def _build_enrichment_metadata(
        priority_field: PropertyShape | None,
        date_field: PropertyShape | None,
    ) -> dict:
        """Build the enrichment metadata dict for kanban results."""
        enrichment: dict = {"priority_field": None, "date_field": None}
        if priority_field:
            enrichment["priority_field"] = {
                "path": priority_field.path,
                "name": priority_field.name,
                "values": list(priority_field.in_values),
            }
        if date_field:
            enrichment["date_field"] = {
                "path": date_field.path,
                "name": date_field.name,
            }
        return enrichment

    # ── Quadrant renderer ──────────────────────────────────────

    # Well-known Eisenhower quadrant labels: (x_value, y_value) → label
    # Multi-framework quadrant label mappings keyed by framework id.
    _QUADRANT_LABELS: dict[str, dict[tuple[str, str], str]] = {
        "eisenhower": {
            ("high", "high"): "Do First",
            ("low", "high"): "Schedule",
            ("high", "low"): "Delegate",
            ("low", "low"): "Eliminate",
        },
        "swot": {
            ("internal", "positive"): "Strengths",
            ("external", "positive"): "Opportunities",
            ("internal", "negative"): "Weaknesses",
            ("external", "negative"): "Threats",
        },
        "bcg": {
            ("high", "high"): "Stars",
            ("low", "high"): "Question Marks",
            ("high", "low"): "Cash Cows",
            ("low", "low"): "Dogs",
        },
        "ansoff": {
            ("existing", "existing"): "Market Penetration",
            ("existing", "new"): "Market Development",
            ("new", "existing"): "Product Development",
            ("new", "new"): "Diversification",
        },
        "stakeholder": {
            ("high", "high"): "Manage Closely",
            ("low", "high"): "Keep Satisfied",
            ("high", "low"): "Keep Informed",
            ("low", "low"): "Monitor",
        },
        "risk": {
            ("high", "high"): "Critical",
            ("low", "high"): "Monitor",
            ("high", "low"): "Mitigate",
            ("low", "low"): "Accept",
        },
    }

    # Keyword pairs for axis assignment: (x_keyword, y_keyword) → framework id.
    # The first matching pair wins. Check is case-insensitive on the local name.
    _AXIS_KEYWORD_PAIRS: list[tuple[str, str, str]] = [
        ("urgency", "importance", "eisenhower"),
        ("nature", "valence", "swot"),
        ("growth", "share", "bcg"),
        ("market", "product", "ansoff"),
        ("power", "interest", "stakeholder"),
        ("likelihood", "impact", "risk"),
    ]

    async def _detect_quadrant_axes(
        self, type_iri: str,
    ) -> tuple[PropertyShape | None, PropertyShape | None, list[str], list[str]]:
        """Find two SHACL properties with ``sh:in`` suitable for quadrant axes.

        Looks for properties whose ``in_values`` contain exactly two string
        values (e.g. ``["high", "low"]``).  Prefers property paths containing
        "urgency" for x-axis and "importance" for y-axis (case-insensitive).

        Returns:
            ``(x_axis, y_axis, x_values, y_values)`` or
            ``(None, None, [], [])`` when fewer than 2 qualifying properties
            are found.
        """
        if not self._shapes_service:
            return None, None, [], []

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_quadrant_axes: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return None, None, [], []

        if form is None:
            return None, None, [], []

        # Collect properties with exactly 2 sh:in values
        candidates: list[PropertyShape] = []
        for prop in form.properties:
            if prop.in_values and len(prop.in_values) == 2:
                candidates.append(prop)

        if len(candidates) < 2:
            logger.debug(
                "_detect_quadrant_axes: type=%s found %d candidates (need 2)",
                type_iri, len(candidates),
            )
            return None, None, [], []

        # Try to assign x/y by keyword preference
        x_axis: PropertyShape | None = None
        y_axis: PropertyShape | None = None

        for x_kw, y_kw, _fid in self._AXIS_KEYWORD_PAIRS:
            x_candidate: PropertyShape | None = None
            y_candidate: PropertyShape | None = None
            for prop in candidates:
                local = _local_name(prop.path).lower()
                if x_kw in local and x_candidate is None:
                    x_candidate = prop
                elif y_kw in local and y_candidate is None:
                    y_candidate = prop
            if x_candidate and y_candidate:
                x_axis = x_candidate
                y_axis = y_candidate
                break

        # Fill in any unassigned axis with remaining candidates
        remaining = [p for p in candidates if p is not x_axis and p is not y_axis]
        if x_axis is None and remaining:
            x_axis = remaining.pop(0)
        if y_axis is None and remaining:
            y_axis = remaining.pop(0)

        if x_axis is None or y_axis is None:
            return None, None, [], []

        logger.debug(
            "_detect_quadrant_axes: type=%s x=%s (%s) y=%s (%s)",
            type_iri,
            x_axis.path, x_axis.in_values,
            y_axis.path, y_axis.in_values,
        )
        return x_axis, y_axis, list(x_axis.in_values), list(y_axis.in_values)

    @staticmethod
    def _build_quadrant_select(
        type_iri: str,
        x_path: str,
        y_path: str,
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query that fetches subjects with two axis values.

        Both axis properties are required (non-OPTIONAL) — items missing
        either axis are excluded from results.

        Args:
            type_iri: The RDF type IRI to filter by.
            x_path: The property IRI for the x-axis field.
            y_path: The property IRI for the y-axis field.
            scope_filter: Optional SPARQL WHERE body injected as sub-select.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "SELECT ?s ?label ?xValue ?yValue\n"
            "WHERE {\n"
            f"  ?s rdf:type {safe_iri(type_iri)} .\n"
            f"  ?s {safe_iri(x_path)} ?xValue .\n"
            f"  ?s {safe_iri(y_path)} ?yValue .\n"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            "}"
        )

    def _quadrant_label(
        self, x_val: str, y_val: str,
        x_name: str, y_name: str,
    ) -> str:
        """Generate a human-readable label for a quadrant cell.

        Derives the framework key from axis names using keyword matching,
        then looks up the framework-specific label dict.  Falls back to
        a generic ``"X: val / Y: val"`` pattern.
        """
        # Determine framework key from axis names
        x_lower = x_name.lower()
        y_lower = y_name.lower()
        framework_key: str | None = None
        for x_kw, y_kw, fid in self._AXIS_KEYWORD_PAIRS:
            if x_kw in x_lower and y_kw in y_lower:
                framework_key = fid
                break

        if framework_key:
            label_dict = self._QUADRANT_LABELS.get(framework_key, {})
            specific = label_dict.get((x_val, y_val))
            if specific:
                return specific

        return f"{x_name}: {x_val} / {y_name}: {y_val}"

    async def execute_quadrant_query(
        self,
        type_iri: str,
        x_axis: PropertyShape,
        y_axis: PropertyShape,
        x_values: list[str],
        y_values: list[str],
        scope_filter: str | None = None,
    ) -> dict:
        """Execute a quadrant grouping query and return bucketed data.

        Groups results into quadrant buckets, one per (x_value, y_value)
        combination.  Items whose axis values don't match any bucket are
        placed in an "Unclassified" bucket.

        Returns:
            ``{"quadrants": [...], "axes": {"x": {...}, "y": {...}}, "total": N}``
        """
        query = self._build_quadrant_select(
            type_iri, x_axis.path, y_axis.path,
            scope_filter=scope_filter,
        )
        scoped = scope_to_current_graph(query)

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_quadrant_query: query failed for type=%s x=%s y=%s",
                type_iri, x_axis.path, y_axis.path,
                exc_info=True,
            )
            return {
                "quadrants": [
                    {
                        "x_value": xv,
                        "y_value": yv,
                        "label": self._quadrant_label(xv, yv, x_axis.name, y_axis.name),
                        "items": [],
                    }
                    for xv in x_values
                    for yv in y_values
                ],
                "axes": {
                    "x": {"path": x_axis.path, "name": x_axis.name},
                    "y": {"path": y_axis.path, "name": y_axis.name},
                },
                "total": 0,
            }

        bindings = result.get("results", {}).get("bindings", [])

        # Build quadrant buckets keyed by (x_value, y_value)
        buckets: dict[tuple[str, str], list[dict]] = {
            (xv, yv): [] for xv in x_values for yv in y_values
        }
        unclassified: list[dict] = []
        seen: set[str] = set()

        for b in bindings:
            iri = b.get("s", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)

            label = b.get("label", {}).get("value", "") or _local_name(iri)
            x_val = b.get("xValue", {}).get("value", "")
            y_val = b.get("yValue", {}).get("value", "")

            item = {"iri": iri, "label": label}
            key = (x_val, y_val)

            if key in buckets:
                buckets[key].append(item)
            else:
                unclassified.append(item)

        quadrants = []
        for xv in x_values:
            for yv in y_values:
                quadrants.append({
                    "x_value": xv,
                    "y_value": yv,
                    "label": self._quadrant_label(xv, yv, x_axis.name, y_axis.name),
                    "items": buckets[(xv, yv)],
                })

        if unclassified:
            quadrants.append({
                "x_value": "__unclassified__",
                "y_value": "__unclassified__",
                "label": "Unclassified",
                "items": unclassified,
            })

        total = len(seen)

        logger.info(
            "execute_quadrant_query: type=%s total=%d quadrants=%d",
            type_iri, total, len(quadrants),
        )

        return {
            "quadrants": quadrants,
            "axes": {
                "x": {"path": x_axis.path, "name": x_axis.name},
                "y": {"path": y_axis.path, "name": y_axis.name},
            },
            "total": total,
        }

    # ── BMC (Business Model Canvas) renderer ───────────────────

    BMC_SECTION_TYPES: dict[str, str] = {
        "key-partners": "Key Partners",
        "key-activities": "Key Activities",
        "key-resources": "Key Resources",
        "value-propositions": "Value Propositions",
        "customer-relationships": "Customer Relationships",
        "channels": "Channels",
        "customer-segments": "Customer Segments",
        "cost-structure": "Cost Structure",
        "revenue-streams": "Revenue Streams",
    }

    async def _detect_bmc_sections(
        self, type_iri: str,
    ) -> tuple["PropertyShape | None", "PropertyShape | None"]:
        """Find a SHACL property with exactly 9 ``sh:in`` values (BMC section type).

        Prefers a property whose path contains "sectiontype" (case-insensitive).
        Also looks for an ObjectProperty pointing to ``bp:BusinessModelCanvas``
        as the canvas link property.

        Returns:
            ``(section_prop, canvas_prop)`` or ``(None, None)`` when no
            qualifying property is found.
        """
        if not self._shapes_service:
            return None, None

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_bmc_sections: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return None, None

        if form is None:
            return None, None

        # Find the property with exactly 9 sh:in values
        section_prop: PropertyShape | None = None
        canvas_prop: PropertyShape | None = None

        for prop in form.properties:
            if prop.in_values and len(prop.in_values) == 9:
                if section_prop is None:
                    section_prop = prop
                # Prefer property with "sectiontype" in path
                local = _local_name(prop.path).lower()
                if "sectiontype" in local:
                    section_prop = prop

        # Look for an ObjectProperty referencing the canvas
        for prop in form.properties:
            if prop.target_class:
                local = _local_name(prop.target_class).lower()
                if "canvas" in local or "businessmodelcanvas" in local:
                    canvas_prop = prop
                    break

        if section_prop is None:
            logger.debug(
                "_detect_bmc_sections: type=%s no property with 9 sh:in values",
                type_iri,
            )
            return None, None

        logger.debug(
            "_detect_bmc_sections: type=%s section_prop=%s canvas_prop=%s",
            type_iri,
            section_prop.path,
            canvas_prop.path if canvas_prop else "(none)",
        )
        return section_prop, canvas_prop

    @staticmethod
    def _build_bmc_select(
        type_iri: str,
        section_path: str,
        canvas_path: str | None = None,
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query that fetches BMC section data.

        The sectionType property is required (non-OPTIONAL).
        sectionContent and canvas link are OPTIONAL.

        Args:
            type_iri: The RDF type IRI to filter by (e.g. BMCSection).
            section_path: The property IRI for the sectionType field.
            canvas_path: Optional property IRI for the canvas link.
            scope_filter: Optional SPARQL WHERE body for scope filtering.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        canvas_clause = ""
        if canvas_path:
            canvas_clause = f"  OPTIONAL {{ ?s {safe_iri(canvas_path)} ?canvas }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "SELECT ?s ?label ?sectionType ?sectionContent ?canvas\n"
            "WHERE {\n"
            f"  ?s rdf:type {safe_iri(type_iri)} .\n"
            f"  ?s {safe_iri(section_path)} ?sectionType .\n"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            "  OPTIONAL { ?s <urn:sempkm:model:business-planning:sectionContent> ?sectionContent }\n"
            f"{canvas_clause}"
            "}"
        )

    async def execute_bmc_query(
        self,
        type_iri: str,
        section_prop: "PropertyShape",
        canvas_prop: "PropertyShape | None",
        scope_filter: str | None = None,
    ) -> dict:
        """Execute a BMC grouping query and return bucketed section data.

        Groups results into 9 section buckets keyed by sectionType value.
        Items whose sectionType doesn't match any known bucket are skipped.

        Returns:
            ``{"sections": [...], "section_types": {...}, "total": N}``
            where each section has ``type``, ``label``, and ``items``.
        """
        query = self._build_bmc_select(
            type_iri,
            section_prop.path,
            canvas_path=canvas_prop.path if canvas_prop else None,
            scope_filter=scope_filter,
        )
        scoped = scope_to_current_graph(query)

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_bmc_query: query failed for type=%s section=%s",
                type_iri, section_prop.path,
                exc_info=True,
            )
            return {
                "sections": [
                    {"type": st, "label": lbl, "items": []}
                    for st, lbl in self.BMC_SECTION_TYPES.items()
                ],
                "section_types": dict(self.BMC_SECTION_TYPES),
                "total": 0,
            }

        bindings = result.get("results", {}).get("bindings", [])

        # Build section buckets keyed by sectionType value
        buckets: dict[str, list[dict]] = {
            st: [] for st in self.BMC_SECTION_TYPES
        }
        seen: set[str] = set()

        for b in bindings:
            iri = b.get("s", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)

            label = b.get("label", {}).get("value", "") or _local_name(iri)
            section_type = b.get("sectionType", {}).get("value", "")
            content = b.get("sectionContent", {}).get("value", "")
            canvas = b.get("canvas", {}).get("value", "")

            item = {
                "iri": iri,
                "label": label,
                "content": content,
                "canvas": canvas,
            }

            if section_type in buckets:
                buckets[section_type].append(item)

        sections = [
            {
                "type": st,
                "label": lbl,
                "items": buckets[st],
            }
            for st, lbl in self.BMC_SECTION_TYPES.items()
        ]

        total = len(seen)

        logger.info(
            "execute_bmc_query: type=%s total=%d sections=%d",
            type_iri, total, len(sections),
        )

        return {
            "sections": sections,
            "section_types": dict(self.BMC_SECTION_TYPES),
            "total": total,
        }

    # ── OKR (Objectives & Key Results) renderer ────────────────

    async def _detect_okr_structure(
        self, type_iri: str,
    ) -> tuple["PropertyShape | None", "PropertyShape | None", "PropertyShape | None", "PropertyShape | None"]:
        """Find SHACL properties for OKR progress computation.

        Looks for decimal properties whose paths contain "currentvalue"
        or "targetvalue" (case-insensitive), a string property containing
        "unit", and an ObjectProperty whose path contains
        "belongstoobjective".

        Returns:
            ``(current_prop, target_prop, unit_prop, objective_prop)`` or
            ``(None, None, None, None)`` when required properties are not
            found.
        """
        if not self._shapes_service:
            return None, None, None, None

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_okr_structure: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return None, None, None, None

        if form is None:
            return None, None, None, None

        current_prop: PropertyShape | None = None
        target_prop: PropertyShape | None = None
        unit_prop: PropertyShape | None = None
        objective_prop: PropertyShape | None = None

        xsd_decimal = "http://www.w3.org/2001/XMLSchema#decimal"

        for prop in form.properties:
            local = _local_name(prop.path).lower()

            if prop.datatype == xsd_decimal:
                if "currentvalue" in local and current_prop is None:
                    current_prop = prop
                elif "targetvalue" in local and target_prop is None:
                    target_prop = prop

            if prop.datatype and "unit" in local and not prop.target_class:
                unit_prop = prop

            if prop.target_class:
                if "belongstoobjective" in local:
                    objective_prop = prop

        if current_prop is None or target_prop is None:
            logger.debug(
                "_detect_okr_structure: type=%s missing currentValue or targetValue decimal properties",
                type_iri,
            )
            return None, None, None, None

        logger.debug(
            "_detect_okr_structure: type=%s current=%s target=%s unit=%s objective=%s",
            type_iri,
            current_prop.path,
            target_prop.path,
            unit_prop.path if unit_prop else "(none)",
            objective_prop.path if objective_prop else "(none)",
        )
        return current_prop, target_prop, unit_prop, objective_prop

    @staticmethod
    def _build_okr_select(
        type_iri: str,
        current_path: str,
        target_path: str,
        unit_path: str | None = None,
        objective_path: str | None = None,
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query for OKR key results with progress data.

        currentValue and targetValue are OPTIONAL (items with missing
        values get 0% progress).  Unit and objective join are OPTIONAL.

        Args:
            type_iri: The RDF type IRI (e.g. bp:KeyResult).
            current_path: Property IRI for the currentValue field.
            target_path: Property IRI for the targetValue field.
            unit_path: Optional property IRI for the unit field.
            objective_path: Optional property IRI linking to the objective.
            scope_filter: Optional SPARQL WHERE body for scope filtering.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        unit_clause = ""
        if unit_path:
            unit_clause = f"  OPTIONAL {{ ?s {safe_iri(unit_path)} ?unit }}\n"

        objective_clause = ""
        if objective_path:
            objective_clause = (
                f"  OPTIONAL {{\n"
                f"    ?s {safe_iri(objective_path)} ?objective .\n"
                f"    OPTIONAL {{ ?objective rdfs:label|dcterms:title ?objTitle }}\n"
                f"  }}\n"
            )

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "SELECT ?s ?title ?currentValue ?targetValue ?unit ?objective ?objTitle\n"
            "WHERE {\n"
            f"  ?s rdf:type {safe_iri(type_iri)} .\n"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?title }\n"
            f"  OPTIONAL {{ ?s {safe_iri(current_path)} ?currentValue }}\n"
            f"  OPTIONAL {{ ?s {safe_iri(target_path)} ?targetValue }}\n"
            f"{unit_clause}"
            f"{objective_clause}"
            "}"
        )

    async def execute_okr_query(
        self,
        type_iri: str,
        current_prop: "PropertyShape",
        target_prop: "PropertyShape",
        unit_prop: "PropertyShape | None" = None,
        objective_prop: "PropertyShape | None" = None,
        scope_filter: str | None = None,
    ) -> dict:
        """Execute an OKR query and compute progress percentages.

        Groups key results by their parent objective.  Each key result
        gets a ``progress`` field computed as
        ``(currentValue / targetValue) * 100`` clamped to 0–100.
        Division by zero (targetValue is 0 or missing) yields 0.

        Each objective gets an aggregate ``progress`` (average of its
        children).

        Returns:
            ``{"objectives": [...], "ungrouped": [...], "total": N}``
        """
        query = self._build_okr_select(
            type_iri,
            current_prop.path,
            target_prop.path,
            unit_path=unit_prop.path if unit_prop else None,
            objective_path=objective_prop.path if objective_prop else None,
            scope_filter=scope_filter,
        )
        scoped = scope_to_current_graph(query)

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_okr_query: query failed for type=%s",
                type_iri,
                exc_info=True,
            )
            return {"objectives": [], "ungrouped": [], "total": 0}

        bindings = result.get("results", {}).get("bindings", [])

        # Group key results by objective
        objectives_map: dict[str, dict] = {}  # objective_iri -> {title, key_results}
        ungrouped: list[dict] = []
        seen: set[str] = set()

        for b in bindings:
            iri = b.get("s", {}).get("value", "")
            if not iri or iri in seen:
                continue
            seen.add(iri)

            title = b.get("title", {}).get("value", "") or _local_name(iri)

            # Compute progress
            try:
                current_val = float(b.get("currentValue", {}).get("value", "0"))
            except (ValueError, TypeError):
                current_val = 0.0

            try:
                target_val = float(b.get("targetValue", {}).get("value", "0"))
            except (ValueError, TypeError):
                target_val = 0.0

            if target_val <= 0:
                progress = 0.0
            else:
                progress = max(0.0, min(100.0, (current_val / target_val) * 100.0))

            unit = b.get("unit", {}).get("value", "")

            kr_item = {
                "iri": iri,
                "title": title,
                "current_value": current_val,
                "target_value": target_val,
                "progress": round(progress, 1),
                "unit": unit,
            }

            obj_iri = b.get("objective", {}).get("value", "")
            if obj_iri:
                obj_title = b.get("objTitle", {}).get("value", "") or _local_name(obj_iri)
                if obj_iri not in objectives_map:
                    objectives_map[obj_iri] = {
                        "iri": obj_iri,
                        "title": obj_title,
                        "key_results": [],
                    }
                objectives_map[obj_iri]["key_results"].append(kr_item)
            else:
                ungrouped.append(kr_item)

        # Compute aggregate progress per objective
        objectives = []
        for obj_data in objectives_map.values():
            krs = obj_data["key_results"]
            if krs:
                avg_progress = sum(kr["progress"] for kr in krs) / len(krs)
            else:
                avg_progress = 0.0
            objectives.append({
                "iri": obj_data["iri"],
                "title": obj_data["title"],
                "progress": round(avg_progress, 1),
                "key_results": krs,
            })

        total = len(seen)

        logger.info(
            "execute_okr_query: type=%s total=%d objectives=%d ungrouped=%d",
            type_iri, total, len(objectives), len(ungrouped),
        )

        return {
            "objectives": objectives,
            "ungrouped": ungrouped,
            "total": total,
        }

    # ── Decision Matrix (Weighted Scoring) renderer ────────────

    async def _detect_decision_matrix_structure(
        self, type_iri: str,
    ) -> tuple["PropertyShape | None", "PropertyShape | None", "PropertyShape | None", "PropertyShape | None"]:
        """Find SHACL properties for Decision Matrix weighted scoring.

        Looks for:
        - A decimal property whose path contains "value" (the score value)
        - An ObjectProperty whose target_class path contains "alternative"
        - An ObjectProperty whose target_class path contains "criterion"

        The weight property lives on the Criterion type and is fetched
        via SPARQL join, not detected here.

        Returns:
            ``(value_prop, alt_prop, crit_prop, None)`` or
            ``(None, None, None, None)`` when required properties are not
            found.
        """
        if not self._shapes_service:
            return None, None, None, None

        try:
            form: NodeShapeForm | None = (
                await self._shapes_service.get_form_for_type(type_iri)
            )
        except Exception:
            logger.warning(
                "_detect_decision_matrix_structure: shapes lookup failed for %s",
                type_iri,
                exc_info=True,
            )
            return None, None, None, None

        if form is None:
            return None, None, None, None

        value_prop: PropertyShape | None = None
        alt_prop: PropertyShape | None = None
        crit_prop: PropertyShape | None = None

        xsd_decimal = "http://www.w3.org/2001/XMLSchema#decimal"

        for prop in form.properties:
            local = _local_name(prop.path).lower()

            if prop.datatype == xsd_decimal and "value" in local:
                if value_prop is None:
                    value_prop = prop

            if prop.target_class:
                tc_local = _local_name(prop.target_class).lower()
                if "alternative" in tc_local and alt_prop is None:
                    alt_prop = prop
                elif "criterion" in tc_local and crit_prop is None:
                    crit_prop = prop

        if value_prop is None or alt_prop is None or crit_prop is None:
            logger.debug(
                "_detect_decision_matrix_structure: type=%s missing required properties "
                "(value=%s, alt=%s, crit=%s)",
                type_iri,
                value_prop is not None,
                alt_prop is not None,
                crit_prop is not None,
            )
            return None, None, None, None

        logger.debug(
            "_detect_decision_matrix_structure: type=%s value=%s alt=%s crit=%s",
            type_iri, value_prop.path, alt_prop.path, crit_prop.path,
        )
        return value_prop, alt_prop, crit_prop, None

    @staticmethod
    def _build_decision_matrix_select(
        type_iri: str,
        value_path: str,
        alt_path: str,
        crit_path: str,
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query joining Score→Alternative and Score→Criterion.

        All joins are required (non-OPTIONAL) since a score without both
        references is meaningless.  Criterion weight is fetched via a
        well-known ``weight`` predicate on the criterion resource.

        Args:
            type_iri: The RDF type IRI for Score.
            value_path: Property IRI for the score value.
            alt_path: Property IRI linking score to alternative.
            crit_path: Property IRI linking score to criterion.
            scope_filter: Optional SPARQL WHERE body for scope filtering.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?score WHERE {{ {scope_filter} }} }}\n"

        # Derive weight predicate: replace the local name of the value
        # property with "weight" — e.g. bp:value → bp:weight.
        # Fallback to a well-known IRI for the weight property.
        weight_ns = value_path
        if "#" in weight_ns:
            weight_path = weight_ns.rsplit("#", 1)[0] + "#weight"
        elif "/" in weight_ns:
            weight_path = weight_ns.rsplit("/", 1)[0] + "/weight"
        else:
            weight_path = "urn:sempkm:model:business-planning:weight"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "SELECT ?score ?alt ?altTitle ?crit ?critTitle ?critWeight ?scoreValue\n"
            "WHERE {\n"
            f"  ?score rdf:type {safe_iri(type_iri)} .\n"
            f"  ?score {safe_iri(value_path)} ?scoreValue .\n"
            f"  ?score {safe_iri(alt_path)} ?alt .\n"
            f"  ?score {safe_iri(crit_path)} ?crit .\n"
            f"{scope_clause}"
            "  OPTIONAL { ?alt rdfs:label|dcterms:title ?altTitle }\n"
            "  OPTIONAL { ?crit rdfs:label|dcterms:title ?critTitle }\n"
            f"  OPTIONAL {{ ?crit {safe_iri(weight_path)} ?critWeight }}\n"
            "}"
        )

    async def execute_decision_matrix_query(
        self,
        type_iri: str,
        value_prop: "PropertyShape",
        alt_prop: "PropertyShape",
        crit_prop: "PropertyShape",
        scope_filter: str | None = None,
    ) -> dict:
        """Execute a Decision Matrix query and compute weighted scores.

        Groups scores by alternative.  For each alternative, computes
        ``weighted_score = Σ(critWeight × scoreValue)``.  Alternatives
        are ranked by descending weighted_score (ties get the same rank).

        Returns:
            ``{"alternatives": [...], "criteria": [...], "total_scores": N}``
            where each alternative has ``iri``, ``title``,
            ``weighted_score``, ``rank``, and ``scores`` dict keyed by
            criterion IRI.
        """
        query = self._build_decision_matrix_select(
            type_iri,
            value_prop.path,
            alt_prop.path,
            crit_prop.path,
            scope_filter=scope_filter,
        )
        scoped = scope_to_current_graph(query)

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_decision_matrix_query: query failed for type=%s",
                type_iri,
                exc_info=True,
            )
            return {"alternatives": [], "criteria": [], "total_scores": 0}

        bindings = result.get("results", {}).get("bindings", [])

        # Collect criteria and alternatives
        criteria_map: dict[str, dict] = {}  # crit_iri -> {title, weight}
        alt_map: dict[str, dict] = {}  # alt_iri -> {title, scores: {crit_iri: value}}

        for b in bindings:
            score_iri = b.get("score", {}).get("value", "")
            if not score_iri:
                continue

            alt_iri = b.get("alt", {}).get("value", "")
            crit_iri = b.get("crit", {}).get("value", "")
            if not alt_iri or not crit_iri:
                continue

            alt_title = b.get("altTitle", {}).get("value", "") or _local_name(alt_iri)
            crit_title = b.get("critTitle", {}).get("value", "") or _local_name(crit_iri)

            try:
                crit_weight = float(b.get("critWeight", {}).get("value", "1"))
            except (ValueError, TypeError):
                crit_weight = 1.0

            try:
                score_value = float(b.get("scoreValue", {}).get("value", "0"))
            except (ValueError, TypeError):
                score_value = 0.0

            # Register criterion
            if crit_iri not in criteria_map:
                criteria_map[crit_iri] = {
                    "iri": crit_iri,
                    "title": crit_title,
                    "weight": crit_weight,
                }

            # Register alternative and score
            if alt_iri not in alt_map:
                alt_map[alt_iri] = {
                    "iri": alt_iri,
                    "title": alt_title,
                    "scores": {},
                }
            alt_map[alt_iri]["scores"][crit_iri] = score_value

        # Compute weighted scores per alternative
        alternatives = []
        for alt_data in alt_map.values():
            weighted_score = 0.0
            for crit_iri, score_val in alt_data["scores"].items():
                crit_weight = criteria_map.get(crit_iri, {}).get("weight", 1.0)
                weighted_score += crit_weight * score_val
            alternatives.append({
                "iri": alt_data["iri"],
                "title": alt_data["title"],
                "weighted_score": round(weighted_score, 2),
                "scores": alt_data["scores"],
            })

        # Sort by weighted_score descending
        alternatives.sort(key=lambda a: a["weighted_score"], reverse=True)

        # Assign ranks (ties get same rank)
        rank = 1
        for i, alt in enumerate(alternatives):
            if i > 0 and alt["weighted_score"] < alternatives[i - 1]["weighted_score"]:
                rank = i + 1
            alt["rank"] = rank

        criteria = sorted(criteria_map.values(), key=lambda c: c.get("weight", 0), reverse=True)
        total_scores = len(bindings)

        logger.info(
            "execute_decision_matrix_query: type=%s total_scores=%d alternatives=%d criteria=%d",
            type_iri, total_scores, len(alternatives), len(criteria),
        )

        return {
            "alternatives": alternatives,
            "criteria": criteria,
            "total_scores": total_scores,
        }

    # ── Timeline renderer ──────────────────────────────────────

    # Status value → Frappe Gantt CSS class mapping
    _TIMELINE_STATUS_CLASSES: dict[str, str] = {
        "done": "bar-done",
        "completed": "bar-done",
        "in-progress": "bar-active",
        "in progress": "bar-active",
        "blocked": "bar-blocked",
        "cancelled": "bar-cancelled",
    }

    @staticmethod
    def _build_timeline_select(
        type_iri: str,
        start_path: str,
        end_path: str | None = None,
        scope_filter: str | None = None,
    ) -> str:
        """Build a SELECT query for timeline data including dependencies.

        Fetches task IRI, label, start/end dates, dependency IRIs via
        bpkm:dependsOn, priority, and status. Dependencies, end date,
        priority, and status are OPTIONAL since not all tasks have them.

        Args:
            type_iri: The RDF type IRI to filter by.
            start_path: The property IRI for the start date field.
            end_path: Optional property IRI for the end date field.
            scope_filter: Optional SPARQL WHERE body injected as sub-select.

        Returns:
            SPARQL SELECT query string.
        """
        scope_clause = ""
        if scope_filter:
            scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"

        end_clause = ""
        if end_path:
            end_clause = f"  OPTIONAL {{ ?s {safe_iri(end_path)} ?endDate }}\n"

        return (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "PREFIX dcterms: <http://purl.org/dc/terms/>\n"
            "\n"
            "SELECT ?s ?label ?startDate ?endDate ?dep ?priority ?status\n"
            "WHERE {\n"
            f"  ?s rdf:type {safe_iri(type_iri)} .\n"
            f"  ?s {safe_iri(start_path)} ?startDate .\n"
            f"{end_clause}"
            f"{scope_clause}"
            "  OPTIONAL { ?s rdfs:label|dcterms:title ?label }\n"
            "  OPTIONAL { ?s <urn:sempkm:model:basic-pkm:dependsOn> ?dep }\n"
            "  OPTIONAL { ?s <urn:sempkm:model:basic-pkm:priority> ?priority }\n"
            "  OPTIONAL { ?s <urn:sempkm:model:basic-pkm:taskStatus> ?status }\n"
            "}"
        )

    async def execute_timeline_query(
        self,
        type_iri: str,
        start_field: PropertyShape,
        end_field: PropertyShape | None = None,
        scope_filter: str | None = None,
    ) -> dict:
        """Execute timeline query and return Frappe Gantt-compatible task data.

        Groups SPARQL results by task IRI (since tasks with N dependencies
        produce N rows). For each unique task, collects: IRI, label, start
        date (stripped to YYYY-MM-DD), end date (fallback: start + 1 day),
        dependency IRIs, progress (default 0), and custom_class from status.

        Tasks without a valid startDate are excluded from results.

        Returns:
            ``{"tasks": [...], "dependency_count": N}``
        """
        query = self._build_timeline_select(
            type_iri,
            start_field.path,
            end_path=end_field.path if end_field else None,
            scope_filter=scope_filter,
        )
        scoped = scope_to_current_graph(query)

        logger.info(
            "execute_timeline_query: scoped_query=%s",
            scoped[:500],
        )

        try:
            result = await self._client.query(scoped)
        except Exception:
            logger.warning(
                "execute_timeline_query: query failed for type=%s start=%s",
                type_iri,
                start_field.path,
                exc_info=True,
            )
            return {"tasks": [], "dependency_count": 0}

        bindings = result.get("results", {}).get("bindings", [])

        # Group results by task IRI — a task with N deps produces N rows
        tasks_map: dict[str, dict] = {}
        for b in bindings:
            iri = b.get("s", {}).get("value", "")
            if not iri:
                continue

            start_val = b.get("startDate", {}).get("value", "")
            if not start_val:
                continue

            if iri not in tasks_map:
                label = b.get("label", {}).get("value", "") or _local_name(iri)
                end_val = b.get("endDate", {}).get("value", "")
                priority_val = b.get("priority", {}).get("value", "")
                status_val = b.get("status", {}).get("value", "")

                # Strip datetime to YYYY-MM-DD for Frappe Gantt
                start_date = start_val[:10] if len(start_val) >= 10 else start_val
                if end_val:
                    end_date = end_val[:10] if len(end_val) >= 10 else end_val
                else:
                    # Fallback: start + 1 day
                    try:
                        dt = datetime.strptime(start_date, "%Y-%m-%d")
                        end_date = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        end_date = start_date

                # Map status to Frappe Gantt CSS class
                custom_class = ""
                if status_val:
                    custom_class = self._TIMELINE_STATUS_CLASSES.get(
                        status_val.lower(), ""
                    )

                tasks_map[iri] = {
                    "id": iri,
                    "name": label,
                    "start": start_date,
                    "end": end_date,
                    "progress": 0,
                    "dependencies": [],
                    "custom_class": custom_class,
                }

            # Collect dependency IRI if present
            dep_val = b.get("dep", {}).get("value", "")
            if dep_val and dep_val not in tasks_map[iri]["dependencies"]:
                tasks_map[iri]["dependencies"].append(dep_val)

        tasks = list(tasks_map.values())
        dep_count = sum(len(t["dependencies"]) for t in tasks)

        logger.info(
            "execute_timeline_query: type=%s tasks=%d deps=%d",
            type_iri, len(tasks), dep_count,
        )

        return {"tasks": tasks, "dependency_count": dep_count}

    async def get_model_layouts(self) -> list[dict]:
        """Query installed model view specs for custom layout definitions.

        Looks for sempkm:layoutAlgorithm entries in views graphs that define
        sempkm:layoutName and sempkm:layoutConfig (JSON string).

        Returns:
            List of {"name": str, "label": str, "config": dict} for each
            model-contributed layout.
        """
        model_sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        try:
            result = await self._client.query(model_sparql)
        except Exception:
            return []

        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return []

        from_clauses = []
        for b in bindings:
            model_id = b["modelId"]["value"]
            from_clauses.append(f"FROM <urn:sempkm:model:{model_id}:views>")

        from_str = "\n".join(from_clauses)

        layout_sparql = f"""SELECT ?name ?label ?config
{from_str}
WHERE {{
  ?algo a <{SEMPKM_VOCAB}LayoutAlgorithm> .
  ?algo <{SEMPKM_VOCAB}layoutName> ?name .
  OPTIONAL {{ ?algo <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
  OPTIONAL {{ ?algo <{SEMPKM_VOCAB}layoutConfig> ?config }}
}}"""

        try:
            result = await self._client.query(layout_sparql)
        except Exception:
            return []

        layouts = []
        for b in result.get("results", {}).get("bindings", []):
            name = b["name"]["value"]
            label = b.get("label", {}).get("value", name.title())
            config_str = b.get("config", {}).get("value", "{}")
            try:
                config = json.loads(config_str)
            except (json.JSONDecodeError, TypeError):
                config = {}
            layouts.append({"name": name, "label": label, "config": config})

        return layouts

    async def _parse_graph_results(
        self,
        turtle_bytes: bytes,
        inferred_edge_set: set[tuple[str, str, str]] | None = None,
        mirrored_edge_set: set[tuple[str, str, str]] | None = None,
    ) -> dict:
        """Parse Turtle CONSTRUCT results into Cytoscape.js-compatible JSON.

        Iterates all triples:
        - Subjects are always nodes.
        - rdf:type triples set the node's type.
        - Object properties (o is URIRef) create edges.
        - Label properties set the node's display label.

        Returns:
            Dict with keys: nodes, edges, type_colors.
        """
        g = rdflib.Graph()
        try:
            g.parse(data=turtle_bytes, format="turtle")
        except Exception:
            logger.warning("Failed to parse CONSTRUCT Turtle results", exc_info=True)
            return {"nodes": [], "edges": [], "type_colors": {}}

        # Track nodes and edges
        nodes_dict: dict[str, dict] = {}  # IRI -> {id, types, label, properties}
        edges: list[dict] = []

        for s, p, o in g:
            s_str = str(s)
            p_str = str(p)

            # Ensure subject is a node
            if s_str not in nodes_dict:
                nodes_dict[s_str] = {"id": s_str, "types": set(), "label": "", "properties": []}

            if p_str == str(RDF.type) and isinstance(o, URIRef):
                # rdf:type triple -- add type to node
                nodes_dict[s_str]["types"].add(str(o))
            elif isinstance(o, URIRef):
                # Object property -- create edge and ensure target is a node
                o_str = str(o)
                if o_str not in nodes_dict:
                    nodes_dict[o_str] = {"id": o_str, "types": set(), "label": "", "properties": []}

                edges.append({
                    "source": s_str,
                    "target": o_str,
                    "predicate": p_str,
                })

                # Check if predicate is a label property
                if p_str in LABEL_PROPERTIES:
                    pass  # URIRef objects are not label values
            else:
                # Datatype property -- store for tooltips
                o_val = str(o)
                nodes_dict[s_str]["properties"].append((p_str, o_val))
                # Check if it's a label property
                if p_str in LABEL_PROPERTIES and not nodes_dict[s_str]["label"]:
                    nodes_dict[s_str]["label"] = o_val

        # Resolve labels for nodes without label properties via LabelService
        iris_needing_labels = [
            iri for iri, data in nodes_dict.items() if not data["label"]
        ]
        if iris_needing_labels:
            resolved = await self._label_service.resolve_batch(iris_needing_labels)
            for iri in iris_needing_labels:
                nodes_dict[iri]["label"] = resolved.get(iri, _local_name(iri))

        # Supplement: fetch all literal properties for graph nodes from all graphs
        # (CONSTRUCT results often only contain relationships + labels)
        all_node_iris = list(nodes_dict.keys())
        if all_node_iris:
            values_clause = " ".join(safe_iri(iri) for iri in all_node_iris)
            sup_query = f"""SELECT ?s ?p ?o
FROM <{CURRENT_GRAPH}>
FROM <urn:sempkm:inferred>
FROM <urn:sempkm:mirrored>
WHERE {{
  VALUES ?s {{ {values_clause} }}
  ?s ?p ?o .
  FILTER(isLiteral(?o))
}}"""
            try:
                sup_result = await self._client.query(sup_query)
                for b in sup_result.get("results", {}).get("bindings", []):
                    s = b["s"]["value"]
                    p = b["p"]["value"]
                    o_val = b["o"]["value"]
                    if s in nodes_dict:
                        # Avoid duplicates from CONSTRUCT-parsed properties
                        existing = {pi for pi, _ in nodes_dict[s]["properties"]}
                        if p not in existing:
                            nodes_dict[s]["properties"].append((p, o_val))
            except Exception:
                logger.warning("Supplementary properties query failed", exc_info=True)

        # Resolve predicate labels for edges and node properties
        pred_iris = set(e["predicate"] for e in edges)
        for data in nodes_dict.values():
            for p_iri, _ in data["properties"]:
                pred_iris.add(p_iri)
        pred_iris_list = list(pred_iris)
        if pred_iris_list:
            pred_labels = await self._label_service.resolve_batch(pred_iris_list)
        else:
            pred_labels = {}

        # Build type-to-color mapping
        all_types: set[str] = set()
        for data in nodes_dict.values():
            all_types.update(data["types"])

        # Query models for optional sempkm:nodeColor (best-effort)
        model_colors = await self._get_model_node_colors(all_types)

        type_colors: dict[str, str] = {}
        for t in all_types:
            if t in model_colors:
                type_colors[t] = model_colors[t]
            else:
                type_colors[t] = _color_for_type(t)

        # Resolve type labels for tooltip display
        type_labels = {}
        if all_types:
            type_labels = await self._label_service.resolve_batch(list(all_types))

        # Build output
        nodes_out = []
        for iri, data in nodes_dict.items():
            primary_type = next(iter(data["types"]), "")
            # Resolve type label to short name
            type_label = ""
            if primary_type:
                resolved_type = type_labels.get(primary_type, "")
                if not resolved_type or ":" in resolved_type:
                    type_label = _local_name(primary_type)
                else:
                    type_label = resolved_type
            # Build tooltip properties (resolved labels, short names)
            props = {}
            for p_iri, p_val in data["properties"]:
                if p_iri not in LABEL_PROPERTIES:
                    resolved_p = pred_labels.get(p_iri, "")
                    if not resolved_p or ":" in resolved_p:
                        p_name = _local_name(p_iri)
                    else:
                        p_name = resolved_p
                    props[p_name] = p_val
            nodes_out.append({
                "id": iri,
                "label": data["label"] or _local_name(iri),
                "type": primary_type,
                "type_label": type_label,
                "properties": props,
            })

        edges_out = []
        _inferred = inferred_edge_set or set()
        _mirrored = mirrored_edge_set or set()
        for e in edges:
            # Use resolved label if it's a real human-readable name,
            # otherwise fall back to local name for short display
            resolved = pred_labels.get(e["predicate"], "")
            # QName fallbacks contain colons (e.g. "sempkm:model:basic-pkm:hasNote")
            # — use _local_name for a short edge label instead
            if not resolved or ":" in resolved:
                short_label = _local_name(e["predicate"])
            else:
                short_label = resolved
            edge_key = (e["source"], e["predicate"], e["target"])
            # Check if this edge exists in the inferred or mirrored graph
            is_inferred = edge_key in _inferred
            is_mirrored = edge_key in _mirrored and edge_key not in _inferred
            edges_out.append({
                "source": e["source"],
                "target": e["target"],
                "predicate": e["predicate"],
                "predicate_label": short_label,
                "inferred": is_inferred,
                "mirrored": is_mirrored,
            })

        return {
            "nodes": nodes_out,
            "edges": edges_out,
            "type_colors": type_colors,
        }

    async def _get_model_node_colors(self, type_iris: set[str]) -> dict[str, str]:
        """Query models for optional sempkm:nodeColor on ontology classes.

        Args:
            type_iris: Set of type IRIs to look up colors for.

        Returns:
            Dict mapping type IRI -> hex color string.
        """
        if not type_iris:
            return {}

        model_sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        try:
            result = await self._client.query(model_sparql)
        except Exception:
            return {}

        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return {}

        # Build FROM clauses for each model's ontology graph
        from_clauses = []
        for b in bindings:
            model_id = b["modelId"]["value"]
            from_clauses.append(f"FROM <urn:sempkm:model:{model_id}:ontology>")

        from_str = "\n".join(from_clauses)

        values = " ".join(f"({safe_iri(iri)})" for iri in type_iris)
        color_sparql = f"""SELECT ?type ?color
{from_str}
WHERE {{
  VALUES (?type) {{ {values} }}
  ?type <{SEMPKM_VOCAB}nodeColor> ?color .
}}"""

        try:
            result = await self._client.query(color_sparql)
        except Exception:
            return {}

        colors: dict[str, str] = {}
        for b in result.get("results", {}).get("bindings", []):
            colors[b["type"]["value"]] = b["color"]["value"]
        return colors


# Tableau 10 color palette for auto-assigned node coloring
TABLEAU_10 = [
    '#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f',
    '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab',
]


def extract_scope_where_body(query_text: str) -> str:
    """Extract WHERE clause body from a saved query, normalizing to ?s.

    For views, the scope sub-select must output ``?s`` (the subject variable
    used in generic view queries).  This function extracts the WHERE body
    and renames the primary SELECT variable to ``?s`` if it differs.

    Returns empty string on parse failure.
    """
    match = re.search(r'WHERE\s*\{(.+)\}\s*$', query_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    body = match.group(1).strip()
    # Find the first SELECT variable to know what to rename
    select_match = re.search(r'SELECT\s+(?:DISTINCT\s+)?(\?\w+)', query_text, re.IGNORECASE)
    if select_match:
        select_var = select_match.group(1)
        if select_var != '?s':
            body = body.replace(select_var, '?s')
    return body

# Label property IRIs for display label extraction from CONSTRUCT results
LABEL_PROPERTIES = {
    str(URIRef("http://purl.org/dc/terms/title")),
    str(URIRef("http://www.w3.org/2000/01/rdf-schema#label")),
    str(URIRef("http://xmlns.com/foaf/0.1/name")),
    str(URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")),
    str(URIRef("https://schema.org/name")),
}


def _color_for_type(type_iri: str) -> str:
    """Auto-assign a color from the Tableau 10 palette based on type IRI hash."""
    idx = int(hashlib.md5(type_iri.encode()).hexdigest(), 16) % len(TABLEAU_10)
    return TABLEAU_10[idx]

def _extract_where_body(query: str) -> str:
    """Extract the content between the outermost WHERE { ... } in a SPARQL query.

    Returns the body without the WHERE keyword and outer braces.
    """
    # Find WHERE keyword followed by opening brace
    match = re.search(r'\bWHERE\s*\{', query, re.IGNORECASE)
    if not match:
        return ""

    start = match.end()
    depth = 1
    i = start

    while i < len(query) and depth > 0:
        if query[i] == '{':
            depth += 1
        elif query[i] == '}':
            depth -= 1
        i += 1

    if depth != 0:
        return ""

    return query[start:i - 1].strip()


def _extract_from_clause(query: str) -> str:
    """Extract FROM clauses from a SPARQL query."""
    from_matches = re.findall(r'(FROM\s+<[^>]+>)', query, re.IGNORECASE)
    return "\n".join(from_matches) if from_matches else ""


def _extract_select_vars(query: str) -> str:
    """Extract SELECT variable list from a SPARQL query."""
    match = re.search(r'SELECT\s+(.*?)\s*(?:FROM|WHERE)', query, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return "*"


def _local_name(iri: str) -> str:
    """Extract the local name from an IRI."""
    if "#" in iri:
        return iri.rsplit("#", 1)[-1]
    if "/" in iri:
        return iri.rsplit("/", 1)[-1]
    if ":" in iri:
        return iri.rsplit(":", 1)[-1]
    return iri


def _var_name_from_iri(iri: str) -> str:
    """Derive a SPARQL-safe variable name from a property IRI's local name.

    Replaces non-alphanumeric characters with ``_`` and strips leading
    digits so the result is a valid SPARQL variable name.
    """
    raw = _local_name(iri)
    sanitized = re.sub(r'[^A-Za-z0-9_]', '_', raw)
    # Strip leading digits/underscores to make a valid SPARQL var
    sanitized = sanitized.lstrip('0123456789_') or 'v'
    return sanitized


def inject_values_binding(query: str, var_name: str, iri: str) -> str:
    """Inject a VALUES ?var { <iri> } clause into a SPARQL query's WHERE body.

    Safely prepends a VALUES binding to the WHERE clause, enabling
    parameterized filtering (e.g. cross-view dashboard context).

    Args:
        query: The SPARQL query string.
        var_name: Variable name (without ?) — must be alphanumeric + underscore.
        iri: The IRI to bind — validated via safe_iri().

    Returns:
        Modified query with VALUES clause injected, or original query unchanged
        if iri is empty, invalid, or var_name fails sanitization.
    """
    if not iri:
        return query

    # Sanitize var_name: alphanumeric + underscore only
    if not var_name or not re.match(r'^[A-Za-z_]\w*$', var_name):
        logger.warning("inject_values_binding: rejected invalid var_name: %s", var_name)
        return query

    try:
        safe = safe_iri(iri)
    except ValueError:
        logger.warning("inject_values_binding: rejected invalid IRI: %s", iri)
        return query

    where_body = _extract_where_body(query)
    if not where_body:
        logger.warning("inject_values_binding: could not extract WHERE body")
        return query

    values_clause = f"VALUES ?{var_name} {{ {safe} }}"
    new_where_body = f"{values_clause}\n  {where_body}"

    # Reassemble: replace old WHERE { body } with new WHERE { values_clause + body }
    match = re.search(r'\bWHERE\s*\{', query, re.IGNORECASE)
    if not match:
        return query

    start = match.end()
    depth = 1
    i = start
    while i < len(query) and depth > 0:
        if query[i] == '{':
            depth += 1
        elif query[i] == '}':
            depth -= 1
        i += 1

    if depth != 0:
        return query

    # i-1 is the position of the closing brace
    new_query = query[:match.end()] + "\n  " + new_where_body + "\n" + query[i - 1:]

    logger.debug("inject_values_binding: var=%s iri=%s", var_name, iri)
    return new_query
