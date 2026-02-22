"""ViewSpecService for loading view specs from installed Mental Model views
graphs and executing their SPARQL queries with pagination, sorting, and filtering.

Follows the same pattern as ShapesService (app/services/shapes.py): queries the
model registry for installed model IDs, builds SPARQL with FROM clauses for each
model's views graph, and parses results into structured Python dataclasses.

Uses scope_to_current_graph() from app/sparql/client to inject FROM <urn:sempkm:current>
into view spec SPARQL queries before execution (per Research Pitfall 1).
"""

import logging
import math
import re
from dataclasses import dataclass, field

from app.models.registry import MODELS_GRAPH, SEMPKM_NS
from app.services.labels import LabelService
from app.sparql.client import scope_to_current_graph
from app.triplestore.client import TriplestoreClient

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


class ViewSpecService:
    """Load and execute view specs from installed Mental Model views graphs.

    Uses SPARQL SELECT to query sempkm:ViewSpec instances across all
    installed model views graphs, and executes their SPARQL queries
    with pagination, sorting, and filtering for table/card rendering.
    """

    def __init__(self, client: TriplestoreClient, label_service: LabelService) -> None:
        self._client = client
        self._label_service = label_service

    async def get_all_view_specs(self) -> list[ViewSpec]:
        """Load all view specs from all installed model views graphs.

        Queries the model registry for installed model IDs, then for each
        model builds FROM <urn:sempkm:model:{id}:views> clauses. Executes
        a SPARQL SELECT querying sempkm:ViewSpec instances with all
        properties.

        Returns:
            List of ViewSpec dataclasses parsed from SPARQL results.
        """
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

        # 2. Build FROM clauses for each model's views graph
        from_clauses = []
        model_ids = []
        for b in bindings:
            model_id = b["modelId"]["value"]
            model_ids.append(model_id)
            views_iri = f"urn:sempkm:model:{model_id}:views"
            from_clauses.append(f"FROM <{views_iri}>")

        from_str = "\n".join(from_clauses)

        # 3. Query view spec properties
        specs_sparql = f"""SELECT ?spec ?label ?targetClass ?renderer ?query ?columns ?sortDefault ?cardTitle ?cardSubtitle
{from_str}
WHERE {{
  ?spec a <{SEMPKM_VOCAB}ViewSpec> .
  OPTIONAL {{ ?spec <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
  OPTIONAL {{ ?spec <{SEMPKM_VOCAB}targetClass> ?targetClass }}
  OPTIONAL {{ ?spec <{SEMPKM_VOCAB}rendererType> ?renderer }}
  OPTIONAL {{ ?spec <{SEMPKM_VOCAB}sparqlQuery> ?query }}
  OPTIONAL {{ ?spec <{SEMPKM_VOCAB}columns> ?columns }}
  OPTIONAL {{ ?spec <{SEMPKM_VOCAB}sortDefault> ?sortDefault }}
  OPTIONAL {{ ?spec <{SEMPKM_VOCAB}cardTitle> ?cardTitle }}
  OPTIONAL {{ ?spec <{SEMPKM_VOCAB}cardSubtitle> ?cardSubtitle }}
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
                source_model=model_ids[0] if len(model_ids) == 1 else "",
            ))

        logger.info("Loaded %d view specs from %d model(s)", len(specs), len(model_ids))
        return specs

    async def get_view_specs_for_type(self, type_iri: str) -> list[ViewSpec]:
        """Filter view specs by target class matching type_iri.

        Args:
            type_iri: The target class IRI to filter by.

        Returns:
            List of ViewSpec instances targeting the given type.
        """
        all_specs = await self.get_all_view_specs()
        return [s for s in all_specs if s.target_class == type_iri]

    async def get_view_spec_by_iri(self, spec_iri: str) -> ViewSpec | None:
        """Find a single view spec by its IRI.

        Args:
            spec_iri: The view spec IRI to find.

        Returns:
            ViewSpec if found, None otherwise.
        """
        all_specs = await self.get_all_view_specs()
        for s in all_specs:
            if s.spec_iri == spec_iri:
                return s
        return None

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
            # Escape special regex chars in user input
            escaped = filter_text.replace("\\", "\\\\").replace('"', '\\"')
            # Match against the first column variable (typically ?title, ?name, ?label)
            first_col = spec.columns[0] if spec.columns else "s"
            filter_clause = f'FILTER(REGEX(STR(?{first_col}), "{escaped}", "i"))'

        # Build count query
        count_where = where_body
        if filter_clause:
            count_where = where_body + "\n  " + filter_clause

        count_query = f"""SELECT (COUNT(DISTINCT ?s) AS ?total)
{from_clause}
WHERE {{
  {count_where}
}}"""

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

        try:
            data_result = await self._client.query(data_query)
            data_bindings = data_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Data query failed for view spec %s", spec.spec_iri, exc_info=True)
            data_bindings = []

        # Parse rows - deduplicate by ?s to handle OPTIONAL cross-products
        seen_subjects = set()
        rows: list[dict] = []
        for b in data_bindings:
            subject = b.get("s", {}).get("value", "")
            if subject in seen_subjects:
                continue
            seen_subjects.add(subject)

            row: dict[str, str] = {"s": subject}
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
    return iri
