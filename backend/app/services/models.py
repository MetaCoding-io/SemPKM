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
    """Auto-install the Basic PKM starter model if no models are installed.

    Called during application startup to ensure a default model is available.

    Args:
        model_service: The ModelService instance.
        starter_path: Path to the Basic PKM model directory.
    """
    try:
        models = await model_service.list_models()
        if models:
            logger.info(
                "Found %d installed model(s), skipping starter model auto-install",
                len(models),
            )
            return
    except Exception as e:
        logger.warning("Failed to check installed models: %s", e)
        return

    logger.info("No models installed, auto-installing Basic PKM starter model")

    if not starter_path.exists():
        logger.error(
            "Starter model path does not exist: %s", starter_path
        )
        return

    result = await model_service.install(starter_path)
    if result.success:
        logger.info(
            "Basic PKM starter model installed successfully (model_id=%s)",
            result.model_id,
        )
    else:
        logger.error(
            "Failed to auto-install Basic PKM starter model: %s",
            result.errors,
        )
