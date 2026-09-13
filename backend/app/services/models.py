"""ModelService orchestrating install, remove, and list pipelines for Mental Models.

Coordinates manifest validation, JSON-LD loading, archive validation,
transactional named graph writes, seed data materialization via EventStore,
TBox surface creation (dashboards/workflows from v2 manifests),
and prefix registration. Provides the real shapes loader and starter model
auto-install for application startup.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, XSD

from app.events.store import EventStore, Operation
from app.models.loader import ModelArchive, load_archive, load_model_docs
from app.models.manifest import ManifestSchema, parse_manifest
from app.models.migrations import (
    MigrationCompiler,
    MigrationDelta,
    MigrationError,
    MigrationSpec,
    discover_migrations,
    select_chain,
)
from app.models.registry import (
    MODELS_GRAPH,
    InstalledModel,
    ModelGraphs,
    check_user_data_exists,
    clear_inferred_graph,
    clear_model_graphs,
    get_applied_migrations,
    is_model_installed,
    list_models as registry_list_models,
    record_applied_migration,
    set_model_version,
    unregister_model,
)
from app.models.validator import ArchiveValidationReport, validate_archive
from app.services.prefixes import PrefixRegistry
from app.triplestore.client import TriplestoreClient
from app.rdf.namespaces import CURRENT_GRAPH

logger = logging.getLogger(__name__)

# SemPKM vocabulary namespace
SEMPKM_NS = "urn:sempkm:"

# A bulk migration can touch far more subjects than are useful to list on the
# event. Beyond this many, the event records the true subject count instead of
# every IRI, so the event graph does not balloon.
MAX_EVENT_AFFECTED_SUBJECTS = 1000

# Triples per INSERT DATA statement when writing a migration journal.
JOURNAL_CHUNK_SIZE = 1000


# --- browserVisible helpers ---


def _expand_prefix(type_ref: str, prefixes: dict[str, str]) -> str:
    """Expand 'prefix:LocalName' to full IRI using manifest prefixes dict.

    Already-expanded IRIs (http://, urn:) are returned unchanged.
    """
    if ":" not in type_ref or type_ref.startswith("http") or type_ref.startswith("urn"):
        return type_ref
    prefix, local = type_ref.split(":", 1)
    base = prefixes.get(prefix, "")
    return base + local if base else type_ref


def _resolve_dashboard_names(
    steps: list[dict],
    dashboard_name_to_id: dict[str, str],
    model_id: str,
) -> list[dict]:
    """Replace ``dashboard_name`` with ``dashboard_id`` in workflow steps.

    For each step whose ``config`` contains a ``dashboard_name`` key, look up
    the name in the mapping built during dashboard creation.  If found, set
    ``config.dashboard_id`` to the UUID string and remove ``dashboard_name``.
    If the name is not found (e.g. dashboard creation failed), log a warning
    and leave the step unchanged — degraded mode consistent with D380.

    Returns a *shallow copy* of the steps list with mutated config dicts so
    the original JSON definitions are not modified.
    """
    resolved: list[dict] = []
    for step in steps:
        config = step.get("config", {})
        name = config.get("dashboard_name")
        if name is not None and dashboard_name_to_id:
            dash_id = dashboard_name_to_id.get(name)
            if dash_id:
                config = {**config, "dashboard_id": dash_id}
                del config["dashboard_name"]
            else:
                logger.warning(
                    "Workflow step references dashboard '%s' not found "
                    "in model '%s' — leaving dashboard_name unresolved",
                    name,
                    model_id,
                )
            resolved.append({**step, "config": config})
        else:
            resolved.append(step)
    return resolved


def get_hidden_type_iris(models_dir: Path | str | None = None) -> set[str]:
    """Return the set of full type IRIs where ``browserVisible`` is ``False``.

    Iterates on-disk model manifests, expands prefixed type names against
    each manifest's ``prefixes`` dict, and collects the IRIs of all icon
    definitions that have ``browserVisible: False``.

    Returns an empty set when no models are installed or when every icon
    entry is visible (the default).
    """
    if models_dir is None:
        return set()

    models_path = Path(models_dir)
    if not models_path.is_dir():
        return set()

    hidden: set[str] = set()
    try:
        entries = list(models_path.iterdir())
    except OSError:
        return hidden

    for entry in entries:
        manifest_path = entry / "manifest.yaml"
        if not manifest_path.exists():
            continue
        try:
            manifest = parse_manifest(entry)
            prefixes = dict(manifest.prefixes or {})
            for icon_def in manifest.icons or []:
                if not icon_def.browserVisible:
                    full_iri = _expand_prefix(icon_def.type, prefixes)
                    hidden.add(full_iri)
        except Exception:
            logger.debug("Skipping manifest at %s for browserVisible scan", entry, exc_info=True)
            continue

    return hidden


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
class RefreshResult:
    """Result of a model artifact refresh operation."""

    success: bool
    model_id: str
    graphs_refreshed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class InstallResult:
    """Result of a model install operation."""

    success: bool
    model_id: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dashboards_created: int = 0
    workflows_created: int = 0


@dataclass
class PlannedMigration:
    """One migration's compiled delta, as shown in an upgrade preview."""

    version: str
    description: str
    delete_count: int
    insert_count: int
    already_applied: bool
    steps: list[dict] = field(default_factory=list)


@dataclass
class UpgradePlan:
    """The read-only preview of what an upgrade would change.

    Produced without writing anything, so an operator can see the exact
    number of triples each step touches before committing to it.
    """

    success: bool
    model_id: str
    from_version: str = ""
    to_version: str = ""
    migrations: list[PlannedMigration] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def pending(self) -> list[PlannedMigration]:
        return [m for m in self.migrations if not m.already_applied]

    @property
    def delete_count(self) -> int:
        return sum(m.delete_count for m in self.pending)

    @property
    def insert_count(self) -> int:
        return sum(m.insert_count for m in self.pending)

    @property
    def is_noop(self) -> bool:
        """True when the upgrade would change no instance data at all."""
        return self.delete_count == 0 and self.insert_count == 0


@dataclass
class UpgradeResult:
    """Result of a model upgrade operation."""

    success: bool
    model_id: str
    from_version: str = ""
    to_version: str = ""
    migrations_applied: list[str] = field(default_factory=list)
    migrations_skipped: list[str] = field(default_factory=list)
    triples_deleted: int = 0
    triples_inserted: int = 0
    graphs_refreshed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RollbackResult:
    """Result of rolling one migration back off a model."""

    success: bool
    model_id: str
    version: str
    triples_restored: int = 0
    triples_removed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class RemoveResult:
    """Result of a model remove operation."""

    success: bool
    model_id: str
    errors: list[str] = field(default_factory=list)
    dashboards_deleted: int = 0
    workflows_deleted: int = 0


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
    to maintain event sourcing consistency. For v2 manifests, creates
    model-sourced TBox surfaces (dashboards/workflows) after install
    and removes them on uninstall.
    """

    def __init__(
        self,
        triplestore_client: TriplestoreClient,
        event_store: EventStore,
        prefix_registry: PrefixRegistry,
        dashboard_service=None,
        workflow_service=None,
    ) -> None:
        self._client = triplestore_client
        self._event_store = event_store
        self._prefix_registry = prefix_registry
        self._dashboard_service = dashboard_service
        self._workflow_service = workflow_service

    async def install(
        self, model_dir: Path, user_id: uuid.UUID | None = None
    ) -> InstallResult:
        """Install a Mental Model from a directory.

        Full pipeline: parse manifest -> check duplicates -> load JSON-LD ->
        validate archive -> write named graphs in transaction -> register
        model metadata -> materialize seed data -> create TBox surfaces
        -> register prefixes.

        Args:
            model_dir: Path to the model archive directory.
            user_id: Owner UUID for model-sourced dashboards/workflows.
                If None, TBox surface creation is skipped.

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

        # 4b. Parse migrations now, so a malformed migration fails the install
        # rather than surfacing at the first upgrade. A fresh install starts
        # at the manifest's version with no legacy data, so every migration
        # the archive ships is recorded as already applied.
        try:
            migration_specs = discover_migrations(model_dir, manifest)
        except MigrationError as e:
            return InstallResult(
                success=False,
                model_id=model_id,
                errors=[f"Migration error: {e}"],
            )

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

        # 7b. Seed the applied-migration ledger. Nothing predates a fresh
        # install, so the archive's whole migration history counts as done.
        for spec in migration_specs:
            try:
                await record_applied_migration(self._client, model_id, spec.version)
            except Exception as e:
                logger.warning(
                    "Failed to record migration %s as applied for '%s': %s",
                    spec.version,
                    model_id,
                    e,
                )
                warning_messages.append(
                    f"Could not record migration {spec.version} in the ledger: {e}"
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

        # 9b. Create TBox surfaces (dashboards/workflows) from v2 manifest
        dashboards_created = 0
        workflows_created = 0
        if user_id is not None:
            try:
                from app.models.tbox_loader import load_tbox_dashboards, load_tbox_workflows

                # Build dashboard name→UUID mapping for workflow resolution
                dashboard_name_to_id: dict[str, str] = {}

                if self._dashboard_service is not None:
                    tbox_dashboards = load_tbox_dashboards(model_dir, manifest)
                    if tbox_dashboards:
                        for dash_def in tbox_dashboards:
                            dash_data = await self._dashboard_service.create(
                                user_id=user_id,
                                name=dash_def["name"],
                                layout=dash_def.get("layout", "single"),
                                blocks=dash_def.get("blocks", []),
                                description=dash_def.get("description", ""),
                                source_model=model_id,
                            )
                            dashboard_name_to_id[dash_def["name"]] = str(dash_data.id)
                            dashboards_created += 1
                        logger.info(
                            "Created %d TBox dashboard(s) for model '%s'",
                            dashboards_created,
                            model_id,
                        )

                if self._workflow_service is not None:
                    tbox_workflows = load_tbox_workflows(model_dir, manifest)
                    if tbox_workflows:
                        for wf_def in tbox_workflows:
                            steps = _resolve_dashboard_names(
                                wf_def.get("steps", []),
                                dashboard_name_to_id,
                                model_id,
                            )
                            await self._workflow_service.create(
                                user_id=user_id,
                                name=wf_def["name"],
                                steps=steps,
                                description=wf_def.get("description", ""),
                                source_model=model_id,
                            )
                            workflows_created += 1
                        logger.info(
                            "Created %d TBox workflow(s) for model '%s'",
                            workflows_created,
                            model_id,
                        )
            except Exception as e:
                # TBox creation failure is degraded mode, not install failure (D380)
                logger.warning(
                    "TBox surface creation failed for model '%s': %s",
                    model_id,
                    e,
                )
                warning_messages.append(f"TBox surface creation failed: {e}")

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
            dashboards_created=dashboards_created,
            workflows_created=workflows_created,
        )

    async def refresh_artifacts(
        self,
        model_id: str,
        user_id: uuid.UUID | None = None,
        model_dir: Path | None = None,
    ) -> RefreshResult:
        """Refresh a model's artifact graphs from disk without touching seed or user data.

        Clears and reloads the 4 artifact graphs (ontology, shapes, views, rules)
        from the on-disk model archive in a single RDF4J transaction. The seed graph
        and registry entry are explicitly excluded. Also refreshes TBox surfaces
        (dashboards/workflows) by deleting old ones and recreating from disk.

        Args:
            model_id: The model identifier to refresh.
            user_id: Owner UUID for refreshed TBox surfaces. If None, TBox
                refresh is skipped.
            model_dir: Archive to reload from. Defaults to whatever
                ``resolve_model_dir`` finds for this model id.

        Returns:
            RefreshResult with success status, refreshed graph names, and any errors.
        """
        # 1. Verify model is installed
        try:
            installed = await is_model_installed(self._client, model_id)
            if not installed:
                return RefreshResult(
                    success=False,
                    model_id=model_id,
                    errors=[f"Model '{model_id}' is not installed."],
                )
        except Exception as e:
            return RefreshResult(
                success=False,
                model_id=model_id,
                errors=[f"Failed to check model status: {e}"],
            )

        # 2. Locate model directory on disk (bundled or marketplace) unless
        # the caller already knows which archive to reload from.
        from app.models.paths import resolve_model_dir
        if model_dir is None:
            model_dir = resolve_model_dir(model_id)
        if model_dir is None:
            return RefreshResult(
                success=False,
                model_id=model_id,
                errors=[f"Model directory not found on disk in any search path"],
            )

        # 3. Parse manifest and load archive
        try:
            manifest = parse_manifest(model_dir)
        except (ValueError, Exception) as e:
            return RefreshResult(
                success=False,
                model_id=model_id,
                errors=[f"Manifest error: {e}"],
            )

        try:
            archive = load_archive(model_dir, manifest)
        except (FileNotFoundError, ValueError, Exception) as e:
            return RefreshResult(
                success=False,
                model_id=model_id,
                errors=[f"Archive loading error: {e}"],
            )

        # 4. Clear and reload artifact graphs in a transaction
        graphs = ModelGraphs(model_id)
        # Only the 4 artifact graphs — NOT seed, NOT registry
        artifact_graph_iris = [graphs.ontology, graphs.shapes, graphs.views, graphs.rules]

        txn_url: str | None = None
        graphs_refreshed: list[str] = []
        try:
            txn_url = await self._client.begin_transaction()

            # CLEAR SILENT the 4 artifact graphs
            for graph_iri in artifact_graph_iris:
                await self._client.transaction_update(
                    txn_url, f"CLEAR SILENT GRAPH <{graph_iri}>"
                )

            # INSERT DATA for each non-empty artifact graph
            if len(archive.ontology) > 0:
                sparql = _build_insert_data_sparql(graphs.ontology, archive.ontology)
                await self._client.transaction_update(txn_url, sparql)
                graphs_refreshed.append("ontology")

            if len(archive.shapes) > 0:
                sparql = _build_insert_data_sparql(graphs.shapes, archive.shapes)
                await self._client.transaction_update(txn_url, sparql)
                graphs_refreshed.append("shapes")

            if len(archive.views) > 0:
                sparql = _build_insert_data_sparql(graphs.views, archive.views)
                await self._client.transaction_update(txn_url, sparql)
                graphs_refreshed.append("views")

            if archive.rules is not None and len(archive.rules) > 0:
                sparql = _build_insert_data_sparql(graphs.rules, archive.rules)
                await self._client.transaction_update(txn_url, sparql)
                graphs_refreshed.append("rules")

            # Commit transaction
            await self._client.commit_transaction(txn_url)
            txn_url = None  # Prevent rollback in finally

        except Exception as e:
            if txn_url is not None:
                try:
                    await self._client.rollback_transaction(txn_url)
                except Exception:
                    pass  # Best-effort rollback
            logger.error("Failed to refresh artifacts for model '%s': %s", model_id, e)
            return RefreshResult(
                success=False,
                model_id=model_id,
                errors=[f"Transaction error during refresh: {e}"],
            )

        # Refresh TBox surfaces (delete old, recreate from disk)
        if user_id is not None:
            try:
                from app.models.tbox_loader import load_tbox_dashboards, load_tbox_workflows

                # Build dashboard name→UUID mapping for workflow resolution
                dashboard_name_to_id: dict[str, str] = {}

                if self._dashboard_service is not None:
                    await self._dashboard_service.delete_by_model(model_id)
                    tbox_dashboards = load_tbox_dashboards(model_dir, manifest)
                    if tbox_dashboards:
                        for dash_def in tbox_dashboards:
                            dash_data = await self._dashboard_service.create(
                                user_id=user_id,
                                name=dash_def["name"],
                                layout=dash_def.get("layout", "single"),
                                blocks=dash_def.get("blocks", []),
                                description=dash_def.get("description", ""),
                                source_model=model_id,
                            )
                            dashboard_name_to_id[dash_def["name"]] = str(dash_data.id)
                if self._workflow_service is not None:
                    await self._workflow_service.delete_by_model(model_id)
                    tbox_workflows = load_tbox_workflows(model_dir, manifest)
                    if tbox_workflows:
                        for wf_def in tbox_workflows:
                            steps = _resolve_dashboard_names(
                                wf_def.get("steps", []),
                                dashboard_name_to_id,
                                model_id,
                            )
                            await self._workflow_service.create(
                                user_id=user_id,
                                name=wf_def["name"],
                                steps=steps,
                                description=wf_def.get("description", ""),
                                source_model=model_id,
                            )
            except Exception as e:
                logger.warning(
                    "TBox surface refresh failed for model '%s': %s",
                    model_id,
                    e,
                )

        logger.info(
            "Model '%s' artifacts refreshed: %s",
            model_id,
            ", ".join(graphs_refreshed) if graphs_refreshed else "none (all empty)",
        )
        return RefreshResult(
            success=True,
            model_id=model_id,
            graphs_refreshed=graphs_refreshed,
        )

    # ------------------------------------------------------------------
    # Versioned upgrades
    # ------------------------------------------------------------------

    async def _upgrade_context(self, model_id: str, model_dir: Path | None = None):
        """Gather everything an upgrade needs, or the reason it cannot run.

        Args:
            model_id: The installed model to upgrade.
            model_dir: Archive to upgrade from. Defaults to whatever
                ``resolve_model_dir`` finds. The marketplace passes the
                freshly downloaded archive explicitly, because a bundled copy
                of the same model id would otherwise win the search order.

        Returns:
            A tuple of ``(context, errors)``. ``context`` is None when
            ``errors`` is non-empty.
        """
        from app.models.paths import resolve_model_dir

        try:
            models = await self.list_models()
        except Exception as e:
            return None, [f"Failed to list installed models: {e}"]

        installed = next((m for m in models if m.model_id == model_id), None)
        if installed is None:
            return None, [f"Model '{model_id}' is not installed."]

        if model_dir is None:
            model_dir = resolve_model_dir(model_id)
        if model_dir is None:
            return None, [
                f"Model directory for '{model_id}' not found on disk in any "
                "search path."
            ]

        try:
            manifest = parse_manifest(model_dir)
        except Exception as e:
            return None, [f"Manifest error: {e}"]

        try:
            specs = discover_migrations(model_dir, manifest)
        except MigrationError as e:
            return None, [f"Migration error: {e}"]

        try:
            chain = select_chain(specs, installed.version, manifest.version)
        except MigrationError as e:
            return None, [str(e)]

        try:
            applied = await get_applied_migrations(self._client, model_id)
        except Exception as e:
            return None, [f"Failed to read applied migrations: {e}"]

        return (installed, model_dir, manifest, chain, applied), []

    async def plan_upgrade(
        self, model_id: str, model_dir: Path | None = None
    ) -> UpgradePlan:
        """Compile what an upgrade would change, without changing anything.

        Every query this issues is a SELECT, so the plan is safe to run at any
        time -- including repeatedly, from a preview screen.

        Counts are exact for the first pending migration. When a chain has
        more than one, later migrations are compiled against the current
        state rather than the state their predecessors would leave behind,
        so their counts are estimates; the plan says so in its warnings.

        Args:
            model_id: The model identifier to plan an upgrade for.

        Returns:
            An UpgradePlan with per-migration and per-step counts.
        """
        context, errors = await self._upgrade_context(model_id, model_dir)
        if context is None:
            return UpgradePlan(success=False, model_id=model_id, errors=errors)
        installed, _model_dir, manifest, chain, applied = context

        plan = UpgradePlan(
            success=True,
            model_id=model_id,
            from_version=installed.version,
            to_version=manifest.version,
        )

        if manifest.version == installed.version:
            plan.warnings.append(
                f"Model '{model_id}' is already at version {installed.version}."
            )

        compiler = MigrationCompiler(self._client, manifest.prefixes)
        pending_seen = 0
        for spec in chain:
            already = spec.version in applied
            if already:
                plan.migrations.append(
                    PlannedMigration(
                        version=spec.version,
                        description=spec.description,
                        delete_count=0,
                        insert_count=0,
                        already_applied=True,
                    )
                )
                continue

            pending_seen += 1
            try:
                delta = await compiler.compile_migration(spec)
            except MigrationError as e:
                plan.success = False
                plan.errors.append(f"{spec.source}: {e}")
                continue
            except Exception as e:
                plan.success = False
                plan.errors.append(f"{spec.source}: failed to compile: {e}")
                continue

            plan.migrations.append(
                PlannedMigration(
                    version=spec.version,
                    description=spec.description,
                    delete_count=delta.delete_count,
                    insert_count=delta.insert_count,
                    already_applied=False,
                    steps=[
                        {
                            "id": step.step_id,
                            "kind": step.kind,
                            "label": step.label,
                            "deletes": len(step.deletes),
                            "inserts": len(step.inserts),
                            "samples": step.samples(),
                        }
                        for step in delta.steps
                    ],
                )
            )

        if pending_seen > 1:
            plan.warnings.append(
                "This upgrade runs more than one migration. Counts for "
                "migrations after the first are estimates, because they are "
                "compiled against today's data rather than the data their "
                "predecessors will leave behind."
            )
        if plan.success and not chain and manifest.version != installed.version:
            plan.warnings.append(
                f"Version {installed.version} to {manifest.version} ships no "
                "migrations. Schema artifacts will be refreshed and no "
                "instance data will change."
            )
        return plan

    async def upgrade(
        self,
        model_id: str,
        user_id: uuid.UUID | None = None,
        *,
        model_dir: Path | None = None,
        allow_same_version: bool = False,
    ) -> UpgradeResult:
        """Upgrade an installed model in place, migrating its instance data.

        Unlike the old remove-then-reinstall path, this never deletes user
        data and is therefore not blocked when instances of the model's types
        exist. It refreshes the schema artifacts, then applies each pending
        migration as one atomic event, recording each in the applied-migration
        ledger as it lands.

        Migrations run in sequence, each compiled against the state its
        predecessor left behind, because a later migration may depend on an
        earlier one's rewrite. If one fails, the ones before it stay applied
        and stay recorded, so re-running resumes rather than repeating work.

        Args:
            model_id: The model identifier to upgrade.
            user_id: Actor for event provenance and refreshed TBox surfaces.
            model_dir: Archive to upgrade from. Defaults to whatever
                ``resolve_model_dir`` finds; the marketplace passes the
                freshly downloaded archive explicitly.
            allow_same_version: Run even when the disk version equals the
                installed version, for re-applying a corrected archive.

        Returns:
            An UpgradeResult naming what was applied, skipped, and changed.
        """
        context, errors = await self._upgrade_context(model_id, model_dir)
        if context is None:
            return UpgradeResult(success=False, model_id=model_id, errors=errors)
        installed, model_dir, manifest, chain, applied = context

        result = UpgradeResult(
            success=True,
            model_id=model_id,
            from_version=installed.version,
            to_version=manifest.version,
        )

        if manifest.version == installed.version and not allow_same_version:
            result.warnings.append(
                f"Model '{model_id}' is already at version {installed.version}; "
                "nothing to upgrade."
            )
            return result

        # Validate the archive before touching anything, so a broken bundle
        # fails while the installed model is still whole.
        try:
            archive = load_archive(model_dir, manifest)
        except Exception as e:
            result.success = False
            result.errors.append(f"Archive loading error: {e}")
            return result

        report = validate_archive(archive)
        if not report.is_valid:
            result.success = False
            result.errors.extend(
                f"[{issue.file}:{issue.rule}] {issue.message}"
                for issue in report.errors
            )
            return result
        result.warnings.extend(
            f"[{issue.file}:{issue.rule}] {issue.message}"
            for issue in report.warnings
        )

        # Schema first: the migrated data should land against the new shapes.
        refresh = await self.refresh_artifacts(
            model_id, user_id=user_id, model_dir=model_dir
        )
        if not refresh.success:
            result.success = False
            result.errors.extend(refresh.errors)
            return result
        result.graphs_refreshed = refresh.graphs_refreshed

        # The ontology just changed, so every inferred triple is suspect.
        # Entailment settings are deliberately left alone -- this is the same
        # model, not a new one.
        try:
            await clear_inferred_graph(self._client)
        except Exception as e:
            logger.warning(
                "Failed to clear inferred graph during upgrade of '%s': %s",
                model_id,
                e,
            )
            result.warnings.append(
                f"Inferred triples could not be cleared: {e}. Run a full "
                "inference recompute from the admin portal."
            )

        compiler = MigrationCompiler(self._client, manifest.prefixes)
        for spec in chain:
            if spec.version in applied:
                result.migrations_skipped.append(spec.version)
                logger.info(
                    "Migration %s for model '%s' already applied, skipping",
                    spec.version,
                    model_id,
                )
                continue

            try:
                delta = await compiler.compile_migration(spec)
                await self._apply_migration(model_id, spec, delta, user_id)
            except MigrationError as e:
                result.success = False
                result.errors.append(f"Migration {spec.version} failed: {e}")
                return result
            except Exception as e:
                logger.exception(
                    "Migration %s failed for model '%s'", spec.version, model_id
                )
                result.success = False
                result.errors.append(f"Migration {spec.version} failed: {e}")
                return result

            result.migrations_applied.append(spec.version)
            result.triples_deleted += delta.delete_count
            result.triples_inserted += delta.insert_count

        try:
            await set_model_version(self._client, model_id, manifest.version)
        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to update recorded version: {e}")
            return result

        logger.info(
            "Model '%s' upgraded %s -> %s: %d migration(s), -%d/+%d triples",
            model_id,
            installed.version,
            manifest.version,
            len(result.migrations_applied),
            result.triples_deleted,
            result.triples_inserted,
        )
        return result

    async def _apply_migration(
        self,
        model_id: str,
        spec: MigrationSpec,
        delta: MigrationDelta,
        user_id: uuid.UUID | None,
    ) -> None:
        """Journal a migration's delta, commit it, and record it as applied.

        The journal is written before the commit so that a reversal is
        possible even if the process dies mid-upgrade; a journal whose commit
        never landed is harmless, because the next attempt overwrites it.
        """
        graphs = ModelGraphs(model_id)
        deletes = delta.all_deletes()
        inserts = delta.all_inserts()

        await self._write_journal(graphs.migration_removed(spec.version), deletes)
        await self._write_journal(graphs.migration_added(spec.version), inserts)

        model_iri = URIRef(f"urn:sempkm:model:{model_id}")
        subjects = delta.affected_subjects()
        affected = [str(model_iri)] + subjects[:MAX_EVENT_AFFECTED_SUBJECTS]

        data_triples = [
            (model_iri, URIRef(f"{SEMPKM_NS}migratedTo"), Literal(spec.version)),
            (
                model_iri,
                URIRef(f"{SEMPKM_NS}migrationDeleteCount"),
                Literal(len(deletes), datatype=XSD.integer),
            ),
            (
                model_iri,
                URIRef(f"{SEMPKM_NS}migrationInsertCount"),
                Literal(len(inserts), datatype=XSD.integer),
            ),
            (
                model_iri,
                URIRef(f"{SEMPKM_NS}migrationSubjectCount"),
                Literal(len(subjects), datatype=XSD.integer),
            ),
        ]

        step_summary = ", ".join(
            f"{s.step_id} (-{len(s.deletes)}/+{len(s.inserts)})" for s in delta.steps
        )
        operation = Operation(
            operation_type="model.migrate",
            affected_iris=affected,
            description=(
                f"Migrate model '{model_id}' to {spec.version}"
                + (f": {step_summary}" if step_summary else "")
            ),
            data_triples=data_triples,
            materialize_inserts=inserts,
            materialize_delete_data=deletes,
        )
        performed_by = URIRef(f"urn:sempkm:user:{user_id}") if user_id else None
        await self._event_store.commit([operation], performed_by=performed_by)

        await record_applied_migration(self._client, model_id, spec.version)

    async def _write_journal(self, graph_iri: str, triples: list[tuple]) -> None:
        """Replace a migration journal graph with the given triples."""
        await self._client.update(f"CLEAR SILENT GRAPH <{graph_iri}>")
        for start in range(0, len(triples), JOURNAL_CHUNK_SIZE):
            chunk = triples[start : start + JOURNAL_CHUNK_SIZE]
            lines = "\n".join(
                f"    {_rdf_term_to_sparql(s)} {_rdf_term_to_sparql(p)} "
                f"{_rdf_term_to_sparql(o)} ."
                for s, p, o in chunk
            )
            await self._client.update(
                f"INSERT DATA {{\n  GRAPH <{graph_iri}> {{\n{lines}\n  }}\n}}"
            )

    async def rollback_migration(
        self,
        model_id: str,
        version: str,
        user_id: uuid.UUID | None = None,
    ) -> RollbackResult:
        """Reverse one applied migration using its journal.

        This undoes the migration's effect on instance data only. It does not
        restore the previous schema artifacts or the previous recorded
        version, because the archive on disk is still the newer one. To return
        a model fully to an earlier release, roll its migrations back and then
        install the older archive.

        Args:
            model_id: The model identifier.
            version: The migration version to reverse.
            user_id: Actor for event provenance.

        Returns:
            A RollbackResult with the triple counts restored and removed.
        """
        result = RollbackResult(success=True, model_id=model_id, version=version)

        try:
            applied = await get_applied_migrations(self._client, model_id)
        except Exception as e:
            return RollbackResult(
                success=False,
                model_id=model_id,
                version=version,
                errors=[f"Failed to read applied migrations: {e}"],
            )

        if version not in applied:
            return RollbackResult(
                success=False,
                model_id=model_id,
                version=version,
                errors=[
                    f"Migration {version} is not recorded as applied to "
                    f"'{model_id}'."
                ],
            )

        graphs = ModelGraphs(model_id)
        try:
            removed = await self._read_journal(graphs.migration_removed(version))
            added = await self._read_journal(graphs.migration_added(version))
        except Exception as e:
            return RollbackResult(
                success=False,
                model_id=model_id,
                version=version,
                errors=[f"Failed to read migration journal: {e}"],
            )

        if not removed and not added:
            return RollbackResult(
                success=False,
                model_id=model_id,
                version=version,
                errors=[
                    f"No journal found for migration {version}; it cannot be "
                    "rolled back automatically."
                ],
            )

        model_iri = URIRef(f"urn:sempkm:model:{model_id}")
        operation = Operation(
            operation_type="model.migrate.rollback",
            affected_iris=[str(model_iri)],
            description=f"Roll back migration {version} of model '{model_id}'",
            data_triples=[
                (model_iri, URIRef(f"{SEMPKM_NS}rolledBack"), Literal(version))
            ],
            materialize_inserts=removed,
            materialize_delete_data=added,
        )
        performed_by = URIRef(f"urn:sempkm:user:{user_id}") if user_id else None

        try:
            await self._event_store.commit([operation], performed_by=performed_by)
        except Exception as e:
            return RollbackResult(
                success=False,
                model_id=model_id,
                version=version,
                errors=[f"Failed to commit rollback: {e}"],
            )

        # Drop the ledger entry and the journal only after the data is back.
        try:
            await self._client.update(
                f"""DELETE DATA {{
  GRAPH <{MODELS_GRAPH}> {{
    <{model_iri}> <{SEMPKM_NS}appliedMigration> "{version}" .
  }}
}}"""
            )
            for graph_iri in (
                graphs.migration_removed(version),
                graphs.migration_added(version),
            ):
                await self._client.update(f"CLEAR SILENT GRAPH <{graph_iri}>")
        except Exception as e:
            result.errors.append(
                f"Data was restored but the ledger could not be cleaned up: {e}"
            )
            result.success = False

        result.triples_restored = len(removed)
        result.triples_removed = len(added)
        logger.info(
            "Rolled back migration %s of model '%s': +%d/-%d triples",
            version,
            model_id,
            len(removed),
            len(added),
        )
        return result

    async def _read_journal(self, graph_iri: str) -> list[tuple]:
        """Read a migration journal graph back as a list of triples."""
        turtle = await self._client.construct(
            f"CONSTRUCT {{ ?s ?p ?o }} FROM <{graph_iri}> WHERE {{ ?s ?p ?o }}"
        )
        graph = Graph()
        if turtle and turtle.strip():
            graph.parse(data=turtle, format="turtle")
        return list(graph)

    async def remove(
        self, model_id: str, user_id: uuid.UUID | None = None
    ) -> RemoveResult:
        """Remove an installed Mental Model.

        Checks for user data before removing. If instances of model types
        exist in the current state graph, removal is blocked. Deletes any
        model-sourced TBox surfaces (dashboards/workflows) before clearing
        named graphs.

        Args:
            model_id: The model identifier to remove.
            user_id: Not used for authorization on model-sourced deletes,
                but kept for API consistency.

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

        # 3b. Delete model-sourced TBox surfaces (dashboards/workflows)
        dashboards_deleted = 0
        workflows_deleted = 0
        try:
            if self._dashboard_service is not None:
                dashboards_deleted = await self._dashboard_service.delete_by_model(model_id)
                if dashboards_deleted:
                    logger.info(
                        "Deleted %d TBox dashboard(s) for model '%s'",
                        dashboards_deleted,
                        model_id,
                    )
            if self._workflow_service is not None:
                workflows_deleted = await self._workflow_service.delete_by_model(model_id)
                if workflows_deleted:
                    logger.info(
                        "Deleted %d TBox workflow(s) for model '%s'",
                        workflows_deleted,
                        model_id,
                    )
        except Exception as e:
            # TBox deletion failure is a warning, not a removal blocker
            logger.warning(
                "TBox surface deletion failed for model '%s': %s",
                model_id,
                e,
            )

        # 4. Clear all model named graphs, including any migration journals
        try:
            try:
                applied = await get_applied_migrations(self._client, model_id)
            except Exception:
                logger.warning(
                    "Could not read applied migrations for '%s'; migration "
                    "journals may be left behind",
                    model_id,
                    exc_info=True,
                )
                applied = set()
            journals = ModelGraphs(model_id).migration_graphs(sorted(applied))
            await clear_model_graphs(self._client, model_id, extra_graphs=journals)
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
        return RemoveResult(
            success=True,
            model_id=model_id,
            dashboards_deleted=dashboards_deleted,
            workflows_deleted=workflows_deleted,
        )

    async def list_models(self) -> list[InstalledModel]:
        """List all installed Mental Models.

        Returns:
            List of InstalledModel with metadata.
        """
        return await registry_list_models(self._client)

    def get_model_docs(self, model_id: str) -> str | None:
        """Read the Markdown documentation shipped inside a model archive.

        Reads straight from the on-disk archive (bundled or downloaded) so
        that a refreshed archive is reflected immediately -- documentation
        is not stored in the triplestore. Returns None when the archive
        cannot be located or ships no documentation; errors from a broken
        docs declaration are logged and also yield None so the admin page
        still renders.
        """
        from app.config import settings
        from app.models.paths import resolve_model_dir

        model_dir = resolve_model_dir(
            model_id, extra_dirs=[settings.marketplace_models_dir]
        )
        if model_dir is None:
            return None
        try:
            manifest = parse_manifest(model_dir)
            return load_model_docs(model_dir, manifest)
        except Exception:
            logger.warning(
                "Could not load documentation for model '%s'", model_id, exc_info=True
            )
            return None

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

        subclass_edges = await self._query_subclass_edges(graphs.ontology, namespace)

        return {
            "info": model_info,
            "types": types,
            "properties": properties,
            "views": views,
            "shapes": shapes,
            "prefixes": prefixes,
            "subclass_edges": subclass_edges,
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

    async def _query_subclass_edges(self, ontology_graph: str, namespace: str) -> list[dict]:
        """Extract rdfs:subClassOf edges from the ontology graph.

        Returns edges with child/parent local names and labels.  External
        superclasses (outside the model namespace) are included so the
        diagram can show the full TBox hierarchy.
        """
        sparql = f"""SELECT ?child ?childLabel ?parent ?parentLabel WHERE {{
  GRAPH <{ontology_graph}> {{
    ?child <http://www.w3.org/2000/01/rdf-schema#subClassOf> ?parent .
    FILTER(!isBlank(?child) && !isBlank(?parent))
    ?child <http://www.w3.org/2000/01/rdf-schema#label> ?childLabel .
    OPTIONAL {{ ?parent <http://www.w3.org/2000/01/rdf-schema#label> ?parentLabel }}
  }}
}} ORDER BY ?childLabel"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        def _local(iri: str) -> str:
            """Derive a short local name for an IRI."""
            if iri.startswith(namespace):
                return iri[len(namespace):]
            # External IRI — use fragment or last path segment
            if "#" in iri:
                return iri.rsplit("#", 1)[-1]
            return iri.rsplit("/", 1)[-1]

        edges = []
        for b in bindings:
            child_iri = b["child"]["value"]
            parent_iri = b["parent"]["value"]
            parent_label = b.get("parentLabel", {}).get("value", "")
            edges.append({
                "child_iri": child_iri,
                "child_local": _local(child_iri),
                "child_label": b["childLabel"]["value"],
                "parent_iri": parent_iri,
                "parent_local": _local(parent_iri),
                "parent_label": parent_label or _local(parent_iri),
                "parent_external": not parent_iri.startswith(namespace),
            })
        return edges

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
  GRAPH <{CURRENT_GRAPH}> {{
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
  GRAPH <{CURRENT_GRAPH}> {{
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
  GRAPH <{CURRENT_GRAPH}> {{
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
  GRAPH <{CURRENT_GRAPH}> {{
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
        <http://www.w3.org/ns/prov#startedAtTime> ?ts .
    FILTER(CONTAINS(STR(?op), "object"))
  }}
  FILTER(STRSTARTS(STR(?ev), "urn:sempkm:event:"))
  GRAPH <{CURRENT_GRAPH}> {{
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
        <http://www.w3.org/ns/prov#startedAtTime> ?ts .
    FILTER(CONTAINS(STR(?op), "object.create"))
    FILTER(?ts >= "{cutoff_iso}"^^xsd:dateTime)
  }}
  FILTER(STRSTARTS(STR(?ev), "urn:sempkm:event:"))
  GRAPH <{CURRENT_GRAPH}> {{
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
  GRAPH <{CURRENT_GRAPH}> {{
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
    shapes_count = len(shapes_graph)

    # 3. Build CONSTRUCT with FROM clauses for each model's rules graph
    rules_from_clauses = []
    for b in bindings:
        model_id = b["modelId"]["value"]
        rules_iri = f"urn:sempkm:model:{model_id}:rules"
        rules_from_clauses.append(f"FROM <{rules_iri}>")

    rules_from_str = "\n".join(rules_from_clauses)
    rules_construct_sparql = f"""CONSTRUCT {{ ?s ?p ?o }}
{rules_from_str}
WHERE {{ ?s ?p ?o }}"""

    rules_turtle_bytes = await client.construct(rules_construct_sparql)
    rules_graph = Graph()
    if rules_turtle_bytes.strip():
        rules_graph.parse(data=rules_turtle_bytes, format="turtle")
    rules_count = len(rules_graph)

    # 4. Merge rules into shapes graph
    shapes_graph += rules_graph

    logger.info("Loaded %d shapes + %d rules triples from %d model(s)", shapes_count, rules_count, len(bindings))
    # Also print to stdout for Docker log visibility (logger may buffer in async workers)
    import sys
    print(f"model_shapes_loader: Loaded {shapes_count} shapes + {rules_count} rules triples from {len(bindings)} model(s)", flush=True, file=sys.stderr)
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
            # Upgrade in place. The old path cleared the model's graphs and
            # reinstalled, which silently re-seated the schema underneath any
            # objects the user had already created. upgrade() refreshes the
            # artifacts and migrates the data instead.
            logger.info(
                "Starter model upgrade: v%s -> v%s",
                installed.version,
                disk_manifest.version,
            )
            upgrade_result = await model_service.upgrade(installed.model_id)
            if upgrade_result.success:
                logger.info(
                    "Starter model upgraded to v%s (%d migration(s), "
                    "-%d/+%d triples)",
                    disk_manifest.version,
                    len(upgrade_result.migrations_applied),
                    upgrade_result.triples_deleted,
                    upgrade_result.triples_inserted,
                )
                return

            # Leave the working install alone rather than reinstalling over
            # live data. An owner can retry from the admin portal, where the
            # errors are visible.
            logger.error(
                "Starter model upgrade v%s -> v%s failed, leaving v%s "
                "installed: %s",
                installed.version,
                disk_manifest.version,
                installed.version,
                "; ".join(upgrade_result.errors),
            )
            return
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
