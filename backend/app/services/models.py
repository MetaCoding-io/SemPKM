"""ModelService orchestrating install, remove, and list pipelines for Mental Models.

Coordinates manifest validation, JSON-LD loading, archive validation,
transactional named graph writes, seed data materialization via EventStore,
and prefix registration. Provides the real shapes loader and starter model
auto-install for application startup.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, XSD

from app.events.store import EventStore, Operation
from app.models.loader import ModelArchive, load_archive
from app.models.manifest import ManifestSchema, parse_manifest
from app.models.registry import (
    MODELS_GRAPH,
    InstalledModel,
    ModelGraphs,
    check_user_data_exists,
    clear_model_graphs,
    is_model_installed,
    list_models as registry_list_models,
    unregister_model,
)
from app.models.validator import ArchiveValidationReport, validate_archive
from app.services.prefixes import PrefixRegistry
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# SemPKM vocabulary namespace
SEMPKM_NS = "urn:sempkm:"

# --- Analytics helper functions ---

_LINK_BUCKETS = [
    ("0", 0, 0),
    ("1-2", 1, 2),
    ("3-5", 3, 5),
    ("6-10", 6, 10),
    ("11+", 11, None),
]


def _extract_last_modified(bindings: list[dict]) -> str | None:
    """Extract ISO date string from a MAX(?mod) SPARQL result.

    Returns the value string if present and non-empty, else None.
    """
    if not bindings:
        return None
    val = bindings[0].get("lastMod", {}).get("value", "")
    return val if val else None


def _iso_week_key(ts_str: str) -> str | None:
    """Convert an ISO datetime string to 'YYYY-Www' week key.

    Returns None if the timestamp cannot be parsed.
    """
    try:
        # Handle both 'T'-separated and space-separated formats
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        iso_cal = dt.isocalendar()
        return f"{iso_cal.year}-W{iso_cal.week:02d}"
    except (ValueError, AttributeError):
        return None


def _pad_weekly_trend(
    week_counts: dict[str, int], now: datetime
) -> list[dict[str, object]]:
    """Return 8 weekly buckets ending at the current week, filling gaps with 0.

    Args:
        week_counts: Dict of 'YYYY-Www' -> count from query results.
        now: Current datetime (UTC) for determining the 8-week window.

    Returns:
        List of 8 dicts with 'week' (str) and 'count' (int), oldest first.
    """
    from datetime import timedelta

    result = []
    for i in range(7, -1, -1):
        dt = now - timedelta(weeks=i)
        iso_cal = dt.isocalendar()
        key = f"{iso_cal.year}-W{iso_cal.week:02d}"
        result.append({"week": key, "count": week_counts.get(key, 0)})
    return result


def _bucket_link_counts(link_counts: list[int]) -> list[dict[str, object]]:
    """Bucket a list of per-instance link counts into histogram buckets.

    Buckets: 0, 1-2, 3-5, 6-10, 11+

    Args:
        link_counts: List of integers, one per instance.

    Returns:
        List of dicts with 'bucket' (str) and 'count' (int).
    """
    buckets = {label: 0 for label, _, _ in _LINK_BUCKETS}
    for c in link_counts:
        for label, lo, hi in _LINK_BUCKETS:
            if hi is None:
                if c >= lo:
                    buckets[label] += 1
                    break
            elif lo <= c <= hi:
                buckets[label] += 1
                break
    return [{"bucket": label, "count": buckets[label]} for label, _, _ in _LINK_BUCKETS]


@dataclass
class InstallResult:
    """Result of a model install operation."""

    success: bool
    model_id: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RemoveResult:
    """Result of a model remove operation."""

    success: bool
    model_id: str
    errors: list[str] = field(default_factory=list)


def _rdf_term_to_sparql(term) -> str:
    """Serialize an rdflib term to SPARQL syntax.

    Handles URIRef, Literal (with datatype/language), and BNode.
    """
    if isinstance(term, URIRef):
        return f"<{term}>"
    elif isinstance(term, Literal):
        escaped = (
            str(term)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        if term.language:
            return f'"{escaped}"@{term.language}'
        elif term.datatype:
            return f'"{escaped}"^^<{term.datatype}>'
        else:
            return f'"{escaped}"'
    elif isinstance(term, BNode):
        return f"_:{term}"
    else:
        return f"<{term}>"


def _build_insert_data_sparql(named_graph_iri: str, graph: Graph) -> str:
    """Build SPARQL INSERT DATA for writing an rdflib Graph to a named graph.

    Uses triple-by-triple serialization (not N-Triples) per Research Pitfall 2.
    """
    triple_lines = []
    for s, p, o in graph:
        triple_lines.append(
            f"    {_rdf_term_to_sparql(s)} {_rdf_term_to_sparql(p)} {_rdf_term_to_sparql(o)} ."
        )
    triples_str = "\n".join(triple_lines)

    return f"""INSERT DATA {{
  GRAPH <{named_graph_iri}> {{
{triples_str}
  }}
}}"""


def _build_register_sparql(manifest: ManifestSchema, installed_at: str) -> str:
    """Build SPARQL INSERT DATA for model registry entry."""
    model_iri = f"urn:sempkm:model:{manifest.modelId}"

    desc_escaped = (
        manifest.description
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )

    return f"""INSERT DATA {{
  GRAPH <{MODELS_GRAPH}> {{
    <{model_iri}> a <{SEMPKM_NS}MentalModel> ;
        <{SEMPKM_NS}modelId> "{manifest.modelId}" ;
        <{SEMPKM_NS}version> "{manifest.version}" ;
        <http://purl.org/dc/terms/title> "{manifest.name}" ;
        <http://purl.org/dc/terms/description> "{desc_escaped}" ;
        <{SEMPKM_NS}namespace> "{manifest.namespace}" ;
        <{SEMPKM_NS}installedAt> "{installed_at}"^^<{XSD.dateTime}> .
  }}
}}"""


class ModelService:
    """Orchestrates Mental Model install, remove, and list operations.

    Uses RDF4J transactions for atomic model graph writes. Seed data
    is materialized via EventStore after the model graph transaction
    to maintain event sourcing consistency.
    """

    def __init__(
        self,
        triplestore_client: TriplestoreClient,
        event_store: EventStore,
        prefix_registry: PrefixRegistry,
    ) -> None:
        self._client = triplestore_client
        self._event_store = event_store
        self._prefix_registry = prefix_registry

    async def install(self, model_dir: Path) -> InstallResult:
        """Install a Mental Model from a directory.

        Full pipeline: parse manifest -> check duplicates -> load JSON-LD ->
        validate archive -> write named graphs in transaction -> register
        model metadata -> materialize seed data -> register prefixes.

        Args:
            model_dir: Path to the model archive directory.

        Returns:
            InstallResult with success status, model_id, and any errors/warnings.
        """
        # 1. Parse manifest
        try:
            manifest = parse_manifest(model_dir)
        except (ValueError, Exception) as e:
            return InstallResult(success=False, errors=[f"Manifest error: {e}"])

        model_id = manifest.modelId

        # 2. Check duplicate
        try:
            already_installed = await is_model_installed(self._client, model_id)
            if already_installed:
                return InstallResult(
                    success=False,
                    model_id=model_id,
                    errors=[
                        f"Model '{model_id}' is already installed. "
                        "Remove it first to reinstall."
                    ],
                )
        except Exception as e:
            return InstallResult(
                success=False,
                model_id=model_id,
                errors=[f"Failed to check existing models: {e}"],
            )

        # 3. Load archive
        try:
            archive = load_archive(model_dir, manifest)
        except (FileNotFoundError, ValueError, Exception) as e:
            return InstallResult(
                success=False,
                model_id=model_id,
                errors=[f"Archive loading error: {e}"],
            )

        # 4. Validate archive
        report: ArchiveValidationReport = validate_archive(archive)
        if not report.is_valid:
            error_messages = [
                f"[{issue.file}:{issue.rule}] {issue.message}"
                for issue in report.errors
            ]
            return InstallResult(
                success=False,
                model_id=model_id,
                errors=error_messages,
            )

        # Collect warnings
        warning_messages = [
            f"[{issue.file}:{issue.rule}] {issue.message}"
            for issue in report.warnings
        ]

        # 5-9. Write graphs in a transaction
        graphs = ModelGraphs(model_id)
        installed_at = datetime.now(timezone.utc).isoformat()

        txn_url: str | None = None
        try:
            txn_url = await self._client.begin_transaction()

            # 6. Write each artifact graph to its named graph
            if len(archive.ontology) > 0:
                sparql = _build_insert_data_sparql(graphs.ontology, archive.ontology)
                await self._client.transaction_update(txn_url, sparql)

            if len(archive.shapes) > 0:
                sparql = _build_insert_data_sparql(graphs.shapes, archive.shapes)
                await self._client.transaction_update(txn_url, sparql)

            if len(archive.views) > 0:
                sparql = _build_insert_data_sparql(graphs.views, archive.views)
                await self._client.transaction_update(txn_url, sparql)

            if archive.rules is not None and len(archive.rules) > 0:
                sparql = _build_insert_data_sparql(graphs.rules, archive.rules)
                await self._client.transaction_update(txn_url, sparql)

            # 7. Register model metadata within the transaction
            register_sparql = _build_register_sparql(manifest, installed_at)
            await self._client.transaction_update(txn_url, register_sparql)

            # 9. Commit the model graph transaction
            await self._client.commit_transaction(txn_url)
            txn_url = None  # Prevent rollback in finally

        except Exception as e:
            # 12. Rollback on error
            if txn_url is not None:
                try:
                    await self._client.rollback_transaction(txn_url)
                except Exception:
                    pass  # Best-effort rollback
            logger.error("Failed to install model '%s': %s", model_id, e)
            return InstallResult(
                success=False,
                model_id=model_id,
                errors=[f"Transaction error during install: {e}"],
            )

        # 8. Materialize seed data via EventStore (outside model transaction)
        if archive.seed is not None and len(archive.seed) > 0:
            try:
                seed_inserts = list(archive.seed)
                operation = Operation(
                    operation_type="model.install",
                    affected_iris=[f"urn:sempkm:model:{model_id}"],
                    description=f"Seed data from model '{manifest.name}' install",
                    data_triples=seed_inserts,
                    materialize_inserts=seed_inserts,
                    materialize_deletes=[],
                )
                await self._event_store.commit([operation])
                logger.info(
                    "Materialized %d seed triples for model '%s'",
                    len(archive.seed),
                    model_id,
                )
            except Exception as e:
                # Seed materialization failure is a warning, not a full failure
                # The model graphs are already committed
                logger.warning(
                    "Seed data materialization failed for model '%s': %s",
                    model_id,
                    e,
                )
                warning_messages.append(
                    f"Seed data materialization failed: {e}"
                )

        # 10. Register model prefixes
        if manifest.prefixes:
            self._prefix_registry.register_model_prefixes(manifest.prefixes)
            logger.info(
                "Registered %d prefixes for model '%s'",
                len(manifest.prefixes),
                model_id,
            )

        # 11. Return success
        logger.info("Model '%s' v%s installed successfully", model_id, manifest.version)
        return InstallResult(
            success=True,
            model_id=model_id,
            warnings=warning_messages,
        )

    async def remove(self, model_id: str) -> RemoveResult:
        """Remove an installed Mental Model.

        Checks for user data before removing. If instances of model types
        exist in the current state graph, removal is blocked.

        Args:
            model_id: The model identifier to remove.

        Returns:
            RemoveResult with success status and any errors.
        """
        # 1. Check model exists
        try:
            installed = await is_model_installed(self._client, model_id)
            if not installed:
                return RemoveResult(
                    success=False,
                    model_id=model_id,
                    errors=[f"Model '{model_id}' is not installed."],
                )
        except Exception as e:
            return RemoveResult(
                success=False,
                model_id=model_id,
                errors=[f"Failed to check model status: {e}"],
            )

        # 2. Load ontology graph to check types
        graphs = ModelGraphs(model_id)
        try:
            turtle_bytes = await self._client.construct(
                f"CONSTRUCT {{ ?s ?p ?o }} FROM <{graphs.ontology}> WHERE {{ ?s ?p ?o }}"
            )
            ontology_graph = Graph()
            if turtle_bytes.strip():
                ontology_graph.parse(data=turtle_bytes, format="turtle")
        except Exception as e:
            return RemoveResult(
                success=False,
                model_id=model_id,
                errors=[f"Failed to load ontology graph: {e}"],
            )

        # 3. Check for user data
        model_namespace = f"urn:sempkm:model:{model_id}:"
        try:
            types_with_data = await check_user_data_exists(
                self._client, model_namespace, ontology_graph
            )
            if types_with_data:
                type_list = ", ".join(types_with_data)
                return RemoveResult(
                    success=False,
                    model_id=model_id,
                    errors=[
                        f"Cannot remove model '{model_id}': user data exists for "
                        f"types: {type_list}. Delete all instances first."
                    ],
                )
        except Exception as e:
            return RemoveResult(
                success=False,
                model_id=model_id,
                errors=[f"Failed to check user data: {e}"],
            )

        # 4. Clear all model named graphs
        try:
            await clear_model_graphs(self._client, model_id)
        except Exception as e:
            return RemoveResult(
                success=False,
                model_id=model_id,
                errors=[f"Failed to clear model graphs: {e}"],
            )

        # 5. Unregister model
        try:
            await unregister_model(self._client, model_id)
        except Exception as e:
            return RemoveResult(
                success=False,
                model_id=model_id,
                errors=[f"Failed to unregister model: {e}"],
            )

        # 6. Prefix cleanup is additive and doesn't cause issues, skip for now

        # 7. Return success
        logger.info("Model '%s' removed successfully", model_id)
        return RemoveResult(success=True, model_id=model_id)

    async def list_models(self) -> list[InstalledModel]:
        """List all installed Mental Models.

        Returns:
            List of InstalledModel with metadata.
        """
        return await registry_list_models(self._client)

    async def get_model_detail(self, model_id: str) -> dict | None:
        """Get detailed information about an installed model.

        Queries the triplestore for ontology classes, properties,
        SHACL shapes, and view specs from the model's named graphs.

        Returns:
            Dict with model info, types, properties, views, shapes,
            or None if the model is not installed.
        """
        models = await registry_list_models(self._client)
        model_info = next((m for m in models if m.model_id == model_id), None)
        if not model_info:
            return None

        graphs = ModelGraphs(model_id)
        namespace = model_info.namespace

        types = await self._query_types(graphs.ontology, namespace)
        properties = await self._query_properties(graphs.ontology, namespace)
        views = await self._query_views(graphs.views)
        shapes = await self._query_shapes(graphs.shapes, namespace)
        prefixes = await self._query_prefixes(model_id)

        return {
            "info": model_info,
            "types": types,
            "properties": properties,
            "views": views,
            "shapes": shapes,
            "prefixes": prefixes,
        }

    async def _query_types(self, ontology_graph: str, namespace: str) -> list[dict]:
        """Extract OWL classes from the ontology graph."""
        sparql = f"""SELECT ?class ?label ?comment WHERE {{
  GRAPH <{ontology_graph}> {{
    ?class a <http://www.w3.org/2002/07/owl#Class> ;
           <http://www.w3.org/2000/01/rdf-schema#label> ?label .
    OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#comment> ?comment }}
  }}
}} ORDER BY ?label"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [
            {
                "iri": b["class"]["value"],
                "local_name": b["class"]["value"].replace(namespace, "") if namespace else b["class"]["value"],
                "label": b["label"]["value"],
                "comment": b.get("comment", {}).get("value", ""),
            }
            for b in bindings
        ]

    async def _query_properties(self, ontology_graph: str, namespace: str) -> list[dict]:
        """Extract OWL properties from the ontology graph."""
        sparql = f"""SELECT ?prop ?propType ?label ?comment ?domain ?range ?inverse WHERE {{
  GRAPH <{ontology_graph}> {{
    ?prop a ?propType ;
          <http://www.w3.org/2000/01/rdf-schema#label> ?label .
    VALUES ?propType {{
      <http://www.w3.org/2002/07/owl#DatatypeProperty>
      <http://www.w3.org/2002/07/owl#ObjectProperty>
    }}
    OPTIONAL {{ ?prop <http://www.w3.org/2000/01/rdf-schema#comment> ?comment }}
    OPTIONAL {{ ?prop <http://www.w3.org/2000/01/rdf-schema#domain> ?domain }}
    OPTIONAL {{ ?prop <http://www.w3.org/2000/01/rdf-schema#range> ?range }}
    OPTIONAL {{ ?prop <http://www.w3.org/2002/07/owl#inverseOf> ?inverse }}
  }}
}} ORDER BY ?propType ?label"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        def _short(iri: str) -> str:
            """Shorten IRI to local name for display."""
            if not iri:
                return ""
            for prefix_map in [
                (namespace, ""),
                ("http://www.w3.org/2001/XMLSchema#", "xsd:"),
                ("http://www.w3.org/2002/07/owl#", "owl:"),
                ("http://www.w3.org/2000/01/rdf-schema#", "rdfs:"),
                ("http://purl.org/dc/terms/", "dcterms:"),
                ("https://schema.org/", "schema:"),
                ("http://xmlns.com/foaf/0.1/", "foaf:"),
                ("http://www.w3.org/2004/02/skos/core#", "skos:"),
            ]:
                if iri.startswith(prefix_map[0]):
                    return prefix_map[1] + iri[len(prefix_map[0]):]
            return iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]

        return [
            {
                "iri": b["prop"]["value"],
                "label": b["label"]["value"],
                "comment": b.get("comment", {}).get("value", ""),
                "prop_type": "Object" if "ObjectProperty" in b["propType"]["value"] else "Datatype",
                "domain": _short(b.get("domain", {}).get("value", "")),
                "range": _short(b.get("range", {}).get("value", "")),
                "inverse": _short(b.get("inverse", {}).get("value", "")),
            }
            for b in bindings
        ]

    async def _query_views(self, views_graph: str) -> list[dict]:
        """Extract ViewSpec definitions from the views graph."""
        sparql = f"""SELECT ?view ?label ?targetClass ?renderer ?columns ?sortDefault WHERE {{
  GRAPH <{views_graph}> {{
    ?view a <urn:sempkm:vocab:ViewSpec> ;
          <http://www.w3.org/2000/01/rdf-schema#label> ?label .
    OPTIONAL {{ ?view <urn:sempkm:vocab:targetClass> ?targetClass }}
    OPTIONAL {{ ?view <urn:sempkm:vocab:rendererType> ?renderer }}
    OPTIONAL {{ ?view <urn:sempkm:vocab:columns> ?columns }}
    OPTIONAL {{ ?view <urn:sempkm:vocab:sortDefault> ?sortDefault }}
  }}
}} ORDER BY ?targetClass ?renderer"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [
            {
                "iri": b["view"]["value"],
                "label": b["label"]["value"],
                "target_class": b.get("targetClass", {}).get("value", "").rsplit(":", 1)[-1],
                "renderer": b.get("renderer", {}).get("value", ""),
                "columns": b.get("columns", {}).get("value", ""),
                "sort_default": b.get("sortDefault", {}).get("value", ""),
            }
            for b in bindings
        ]

    async def _query_shapes(self, shapes_graph: str, namespace: str) -> list[dict]:
        """Extract SHACL NodeShape summaries from the shapes graph."""
        # Get NodeShapes
        sparql = f"""SELECT ?shape ?label ?targetClass WHERE {{
  GRAPH <{shapes_graph}> {{
    ?shape a <http://www.w3.org/ns/shacl#NodeShape> ;
           <http://www.w3.org/2000/01/rdf-schema#label> ?label .
    OPTIONAL {{ ?shape <http://www.w3.org/ns/shacl#targetClass> ?targetClass }}
  }}
}} ORDER BY ?label"""
        result = await self._client.query(sparql)
        shape_bindings = result.get("results", {}).get("bindings", [])

        shapes = []
        for sb in shape_bindings:
            shape_iri = sb["shape"]["value"]
            target = sb.get("targetClass", {}).get("value", "")
            target_short = target.replace(namespace, "") if namespace and target else target

            # Get properties for this shape
            props_sparql = f"""SELECT ?name ?path ?datatype ?class ?minCount ?maxCount ?group ?groupLabel ?order WHERE {{
  GRAPH <{shapes_graph}> {{
    <{shape_iri}> <http://www.w3.org/ns/shacl#property> ?prop .
    ?prop <http://www.w3.org/ns/shacl#name> ?name .
    OPTIONAL {{ ?prop <http://www.w3.org/ns/shacl#path> ?path }}
    OPTIONAL {{ ?prop <http://www.w3.org/ns/shacl#datatype> ?datatype }}
    OPTIONAL {{ ?prop <http://www.w3.org/ns/shacl#class> ?class }}
    OPTIONAL {{ ?prop <http://www.w3.org/ns/shacl#minCount> ?minCount }}
    OPTIONAL {{ ?prop <http://www.w3.org/ns/shacl#maxCount> ?maxCount }}
    OPTIONAL {{ ?prop <http://www.w3.org/ns/shacl#order> ?order }}
    OPTIONAL {{
      ?prop <http://www.w3.org/ns/shacl#group> ?group .
      ?group <http://www.w3.org/2000/01/rdf-schema#label> ?groupLabel .
    }}
  }}
}} ORDER BY ?order"""
            props_result = await self._client.query(props_sparql)
            prop_bindings = props_result.get("results", {}).get("bindings", [])

            def _short_iri(iri: str) -> str:
                if not iri:
                    return ""
                for prefix_map in [
                    (namespace, ""),
                    ("http://www.w3.org/2001/XMLSchema#", "xsd:"),
                    ("http://purl.org/dc/terms/", "dcterms:"),
                    ("https://schema.org/", "schema:"),
                    ("http://xmlns.com/foaf/0.1/", "foaf:"),
                    ("http://www.w3.org/2004/02/skos/core#", "skos:"),
                ]:
                    if iri.startswith(prefix_map[0]):
                        return prefix_map[1] + iri[len(prefix_map[0]):]
                return iri.rsplit("/", 1)[-1].rsplit("#", 1)[-1]

            props = []
            for pb in prop_bindings:
                dt = pb.get("datatype", {}).get("value", "")
                cls = pb.get("class", {}).get("value", "")
                min_c = pb.get("minCount", {}).get("value", "")
                max_c = pb.get("maxCount", {}).get("value", "")

                cardinality = ""
                if min_c and max_c:
                    cardinality = f"{min_c}..{max_c}"
                elif min_c:
                    cardinality = f"{min_c}..*"
                elif max_c:
                    cardinality = f"0..{max_c}"

                props.append({
                    "name": pb["name"]["value"],
                    "path": _short_iri(pb.get("path", {}).get("value", "")),
                    "type": _short_iri(dt) if dt else (_short_iri(cls) + " (ref)" if cls else ""),
                    "cardinality": cardinality,
                    "group": pb.get("groupLabel", {}).get("value", ""),
                    "required": min_c == "1",
                })
            shapes.append({
                "label": sb["label"]["value"],
                "target_class": target_short,
                "target_class_iri": target,
                "property_count": len(props),
                "properties": props,
            })
        return shapes

    async def _query_prefixes(self, model_id: str) -> dict[str, str]:
        """Get the prefix mappings from the model registry."""
        # Prefixes aren't stored in triplestore — return empty
        return {}

    async def get_type_analytics(self, type_iris: list[str]) -> dict[str, dict]:
        """Get live analytics per type: counts, top nodes, connections, dates, trends, distributions.

        Args:
            type_iris: List of full type IRIs to query.

        Returns:
            Dict keyed by type IRI with keys: count, top_nodes,
            avg_connections, last_modified, growth_trend, link_distribution.
        """
        analytics: dict[str, dict] = {}
        for iri in type_iris:
            analytics[iri] = {
                "count": 0,
                "top_nodes": [],
                "avg_connections": 0.0,
                "last_modified": None,
                "growth_trend": [],
                "link_distribution": [],
            }

        if not type_iris:
            return analytics

        # Batch instance counts
        values = " ".join(f"<{iri}>" for iri in type_iris)
        count_sparql = f"""SELECT ?type (COUNT(DISTINCT ?s) AS ?count) WHERE {{
  GRAPH <urn:sempkm:current> {{
    ?s a ?type .
  }}
  VALUES ?type {{ {values} }}
}} GROUP BY ?type"""
        try:
            result = await self._client.query(count_sparql)
            for b in result.get("results", {}).get("bindings", []):
                t_iri = b["type"]["value"]
                if t_iri in analytics:
                    analytics[t_iri]["count"] = int(b["count"]["value"])
        except Exception:
            pass

        # Top nodes per type by incoming link count
        for iri in type_iris:
            if analytics[iri]["count"] == 0:
                continue
            top_sparql = f"""SELECT ?s (SAMPLE(?lbl) AS ?label) (COUNT(DISTINCT ?ref) AS ?linkCount) WHERE {{
  GRAPH <urn:sempkm:current> {{
    ?s a <{iri}> .
    OPTIONAL {{
      ?ref ?p ?s .
      FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
    }}
    OPTIONAL {{ ?s <http://purl.org/dc/terms/title> ?t }}
    OPTIONAL {{ ?s <http://xmlns.com/foaf/0.1/name> ?n }}
    OPTIONAL {{ ?s <http://www.w3.org/2004/02/skos/core#prefLabel> ?l }}
  }}
  BIND(COALESCE(?t, ?n, ?l, REPLACE(STR(?s), "^.*/", "")) AS ?lbl)
}} GROUP BY ?s ORDER BY DESC(?linkCount) LIMIT 5"""
            try:
                result = await self._client.query(top_sparql)
                for b in result.get("results", {}).get("bindings", []):
                    analytics[iri]["top_nodes"].append({
                        "label": b.get("label", {}).get("value", "?"),
                        "link_count": int(b.get("linkCount", {}).get("value", "0")),
                    })
            except Exception:
                pass

        # --- Avg connections per type ---
        for iri in type_iris:
            inst_count = analytics[iri]["count"]
            if inst_count == 0:
                continue
            avg_conn_sparql = f"""SELECT (COUNT(?link) AS ?totalLinks) WHERE {{
  GRAPH <urn:sempkm:current> {{
    ?s a <{iri}> .
    {{
      ?s ?p ?o .
      FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
      BIND(?p AS ?link)
    }} UNION {{
      ?o2 ?p2 ?s .
      FILTER(?p2 != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
      BIND(?p2 AS ?link)
    }}
  }}
}}"""
            try:
                result = await self._client.query(avg_conn_sparql)
                bindings = result.get("results", {}).get("bindings", [])
                if bindings:
                    total = int(bindings[0].get("totalLinks", {}).get("value", "0"))
                    analytics[iri]["avg_connections"] = round(total / inst_count, 1)
            except Exception:
                logger.warning("avg_connections query failed for type <%s>", iri)

        # --- Last modified per type ---
        for iri in type_iris:
            if analytics[iri]["count"] == 0:
                continue
            # Primary: dcterms:modified on instances
            last_mod_sparql = f"""SELECT (MAX(?mod) AS ?lastMod) WHERE {{
  GRAPH <urn:sempkm:current> {{
    ?s a <{iri}> .
    ?s <http://purl.org/dc/terms/modified> ?mod .
  }}
}}"""
            try:
                result = await self._client.query(last_mod_sparql)
                bindings = result.get("results", {}).get("bindings", [])
                last_mod = _extract_last_modified(bindings)
                if last_mod:
                    analytics[iri]["last_modified"] = last_mod
                    continue
                # Fallback: latest event timestamp for instances of this type
                fallback_sparql = f"""SELECT (MAX(?ts) AS ?lastMod) WHERE {{
  GRAPH ?ev {{
    ?ev <urn:sempkm:operationType> ?op ;
        <urn:sempkm:affectedIRI> ?aff ;
        <urn:sempkm:timestamp> ?ts .
    FILTER(CONTAINS(STR(?op), "object"))
  }}
  FILTER(STRSTARTS(STR(?ev), "urn:sempkm:event:"))
  GRAPH <urn:sempkm:current> {{
    ?aff a <{iri}> .
  }}
}}"""
                result = await self._client.query(fallback_sparql)
                bindings = result.get("results", {}).get("bindings", [])
                last_mod = _extract_last_modified(bindings)
                if last_mod:
                    analytics[iri]["last_modified"] = last_mod
            except Exception:
                logger.warning("last_modified query failed for type <%s>", iri)

        # --- Growth trend per type (last 8 weeks) ---
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        eight_weeks_ago = now - timedelta(weeks=8)
        cutoff_iso = eight_weeks_ago.strftime("%Y-%m-%dT%H:%M:%S")
        for iri in type_iris:
            if analytics[iri]["count"] == 0:
                analytics[iri]["growth_trend"] = _pad_weekly_trend({}, now)
                continue
            growth_sparql = f"""PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?ts WHERE {{
  GRAPH ?ev {{
    ?ev <urn:sempkm:operationType> ?op ;
        <urn:sempkm:affectedIRI> ?aff ;
        <urn:sempkm:timestamp> ?ts .
    FILTER(CONTAINS(STR(?op), "object.create"))
    FILTER(?ts >= "{cutoff_iso}"^^xsd:dateTime)
  }}
  FILTER(STRSTARTS(STR(?ev), "urn:sempkm:event:"))
  GRAPH <urn:sempkm:current> {{
    ?aff a <{iri}> .
  }}
}}"""
            try:
                result = await self._client.query(growth_sparql)
                bindings = result.get("results", {}).get("bindings", [])
                week_counts: dict[str, int] = {}
                for b in bindings:
                    ts_str = b.get("ts", {}).get("value", "")
                    if ts_str:
                        week_key = _iso_week_key(ts_str)
                        if week_key:
                            week_counts[week_key] = week_counts.get(week_key, 0) + 1
                analytics[iri]["growth_trend"] = _pad_weekly_trend(week_counts, now)
            except Exception:
                logger.warning("growth_trend query failed for type <%s>", iri)
                analytics[iri]["growth_trend"] = _pad_weekly_trend({}, now)

        # --- Link distribution per type ---
        for iri in type_iris:
            if analytics[iri]["count"] == 0:
                continue
            link_dist_sparql = f"""SELECT ?s (COUNT(?link) AS ?linkCount) WHERE {{
  GRAPH <urn:sempkm:current> {{
    ?s a <{iri}> .
    {{
      ?s ?p ?o .
      FILTER(?p != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
      BIND(?p AS ?link)
    }} UNION {{
      ?o2 ?p2 ?s .
      FILTER(?p2 != <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
      BIND(?p2 AS ?link)
    }}
  }}
}} GROUP BY ?s"""
            try:
                result = await self._client.query(link_dist_sparql)
                bindings = result.get("results", {}).get("bindings", [])
                link_counts = []
                for b in bindings:
                    link_counts.append(
                        int(b.get("linkCount", {}).get("value", "0"))
                    )
                # Include zero-link instances (not returned by query)
                instances_with_links = len(link_counts)
                zero_link_count = analytics[iri]["count"] - instances_with_links
                link_counts.extend([0] * zero_link_count)
                analytics[iri]["link_distribution"] = _bucket_link_counts(link_counts)
            except Exception:
                logger.warning("link_distribution query failed for type <%s>", iri)

        return analytics


async def model_shapes_loader(client: TriplestoreClient) -> Graph:
    """Load SHACL shapes from all installed models.

    Replaces empty_shapes_loader with real shapes from installed models.
    Queries the model registry to find installed models, then fetches
    all shapes graphs via SPARQL CONSTRUCT.

    Args:
        client: The triplestore client.

    Returns:
        An rdflib Graph containing all installed model shapes.
    """
    # 1. List installed model IDs
    sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
    result = await client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])

    if not bindings:
        return Graph()

    # 2. Build CONSTRUCT with FROM clauses for each model's shapes graph
    from_clauses = []
    for b in bindings:
        model_id = b["modelId"]["value"]
        shapes_iri = f"urn:sempkm:model:{model_id}:shapes"
        from_clauses.append(f"FROM <{shapes_iri}>")

    from_str = "\n".join(from_clauses)
    construct_sparql = f"""CONSTRUCT {{ ?s ?p ?o }}
{from_str}
WHERE {{ ?s ?p ?o }}"""

    turtle_bytes = await client.construct(construct_sparql)
    shapes_graph = Graph()
    if turtle_bytes.strip():
        shapes_graph.parse(data=turtle_bytes, format="turtle")

    logger.info("Loaded %d shapes triples from %d model(s)", len(shapes_graph), len(bindings))
    return shapes_graph


async def ensure_starter_model(
    model_service: ModelService, starter_path: Path
) -> None:
    """Auto-install or upgrade the Basic PKM starter model.

    Called during application startup. Installs if no models exist,
    or reinstalls if the on-disk version is newer than the installed version.

    Args:
        model_service: The ModelService instance.
        starter_path: Path to the Basic PKM model directory.
    """
    if not starter_path.exists():
        logger.error(
            "Starter model path does not exist: %s", starter_path
        )
        return

    try:
        disk_manifest = parse_manifest(starter_path)
    except Exception as e:
        logger.warning("Failed to parse starter model manifest: %s", e)
        return

    try:
        models = await model_service.list_models()
    except Exception as e:
        logger.warning("Failed to check installed models: %s", e)
        return

    if not models:
        logger.info("No models installed, auto-installing Basic PKM starter model")
    else:
        installed = next(
            (m for m in models if m.model_id == disk_manifest.modelId), None
        )
        if installed and installed.version == disk_manifest.version:
            logger.info(
                "Starter model %s v%s is current, skipping",
                installed.model_id,
                installed.version,
            )
            return
        if installed:
            logger.info(
                "Starter model upgrade: v%s -> v%s, reinstalling",
                installed.version,
                disk_manifest.version,
            )
            await clear_model_graphs(model_service._client, installed.model_id)
            await unregister_model(model_service._client, installed.model_id)
        else:
            logger.info(
                "Found %d model(s) but not starter model, installing",
                len(models),
            )

    result = await model_service.install(starter_path)
    if result.success:
        logger.info(
            "Basic PKM starter model installed successfully (model_id=%s, v%s)",
            result.model_id,
            disk_manifest.version,
        )
    else:
        logger.error(
            "Failed to auto-install Basic PKM starter model: %s",
            result.errors,
        )
