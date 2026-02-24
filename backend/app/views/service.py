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
from dataclasses import dataclass, field

import rdflib
from rdflib import RDF, URIRef

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
                    group_vals = ["(No value)"]
                for gv in group_vals:
                    if gv not in group_map:
                        group_map[gv] = []
                    group_map[gv].append(card)

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
            "columns": groupable_props,
        }

    async def execute_graph_query(self, spec: ViewSpec) -> dict:
        """Execute a view spec's SPARQL CONSTRUCT query for graph visualization.

        Scopes the query to the current graph, executes as CONSTRUCT to get
        Turtle bytes, parses with rdflib, and converts to Cytoscape.js-compatible
        JSON with nodes, edges, and type-to-color mapping.

        Args:
            spec: The ViewSpec containing a CONSTRUCT SPARQL query.

        Returns:
            Dict with keys: nodes, edges, type_colors.
        """
        if not spec.sparql_query:
            return {"nodes": [], "edges": [], "type_colors": {}}

        scoped_query = scope_to_current_graph(spec.sparql_query)

        try:
            turtle_bytes = await self._client.construct(scoped_query)
        except Exception:
            logger.warning("CONSTRUCT query failed for view spec %s", spec.spec_iri, exc_info=True)
            return {"nodes": [], "edges": [], "type_colors": {}}

        return await self._parse_graph_results(turtle_bytes)

    async def expand_neighbors(self, node_iri: str) -> dict:
        """Fetch all triples where node_iri is subject or object.

        Executes a SPARQL CONSTRUCT for both directions (outbound and inbound),
        scoped to the current graph.

        Args:
            node_iri: The IRI of the node to expand.

        Returns:
            Dict with keys: nodes, edges, type_colors.
        """
        construct_query = f"""CONSTRUCT {{ ?s ?p ?o }}
FROM <urn:sempkm:current>
WHERE {{
  {{ <{node_iri}> ?p ?o . BIND(<{node_iri}> AS ?s) . FILTER(isIRI(?o)) }}
  UNION
  {{ ?s ?p <{node_iri}> . BIND(<{node_iri}> AS ?o) . FILTER(isIRI(?s)) }}
}}"""

        try:
            turtle_bytes = await self._client.construct(construct_query)
        except Exception:
            logger.warning("Expand neighbors query failed for %s", node_iri, exc_info=True)
            return {"nodes": [], "edges": [], "type_colors": {}}

        return await self._parse_graph_results(turtle_bytes)

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

    async def _parse_graph_results(self, turtle_bytes: bytes) -> dict:
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

        # Supplement: fetch all literal properties for graph nodes from current graph
        # (CONSTRUCT results often only contain relationships + labels)
        all_node_iris = list(nodes_dict.keys())
        if all_node_iris:
            values_clause = " ".join(f"<{iri}>" for iri in all_node_iris)
            sup_query = f"""SELECT ?s ?p ?o
FROM <urn:sempkm:current>
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
            edges_out.append({
                "source": e["source"],
                "target": e["target"],
                "predicate": e["predicate"],
                "predicate_label": short_label,
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

        values = " ".join(f"(<{iri}>)" for iri in type_iris)
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
