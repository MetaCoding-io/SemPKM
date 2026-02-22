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
            escaped = filter_text.replace("\\", "\\\\").replace('"', '\\"')
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
        values_clause = " ".join(f"<{iri}>" for iri in subject_iris)
        props_query = f"""SELECT ?s ?p ?o
FROM <urn:sempkm:current>
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
        desc_by_subject: dict[str, str] = {}

        all_iris_to_resolve: set[str] = set(subject_iris)

        for b in props_bindings:
            s = b["s"]["value"]
            p = b["p"]["value"]
            o_val = b["o"]["value"]
            if s in props_by_subject:
                props_by_subject[s].append((p, o_val))
                all_iris_to_resolve.add(p)
                # Track body and description for snippets
                if p == "urn:sempkm:body":
                    body_by_subject[s] = o_val
                elif p == "http://purl.org/dc/terms/description":
                    desc_by_subject[s] = o_val

        # Fetch outbound relationships (IRI objects, not literals)
        out_query = f"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?s ?predicate ?object
FROM <urn:sempkm:current>
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
FROM <urn:sempkm:current>
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
                snippet = body_by_subject[iri][:100]
                if len(body_by_subject[iri]) > 100:
                    snippet += "..."
            elif iri in desc_by_subject:
                snippet = desc_by_subject[iri][:100]
                if len(desc_by_subject[iri]) > 100:
                    snippet += "..."

            # Properties list (name/value pairs with resolved labels)
            properties = []
            for p, v in props_by_subject[iri]:
                # Skip body and rdf:type from property display
                if p in ("urn:sempkm:body", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"):
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

        # Grouping by property value
        groups = None
        if group_by and cards:
            group_map: dict[str, list[dict]] = {}
            group_label = labels.get(group_by, _local_name(group_by))
            for card in cards:
                # Find the grouping value from properties
                group_val = ""
                for prop in card["properties"]:
                    # Match by original IRI or resolved label
                    if prop["name"] == group_label or prop["name"] == _local_name(group_by):
                        group_val = prop["value"]
                        break
                if not group_val:
                    group_val = "(No value)"
                if group_val not in group_map:
                    group_map[group_val] = []
                group_map[group_val].append(card)

            groups = [
                {"group_label": k, "cards": v}
                for k, v in sorted(group_map.items())
            ]

        return {
            "cards": cards,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "groups": groups,
            "group_by": group_by,
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
