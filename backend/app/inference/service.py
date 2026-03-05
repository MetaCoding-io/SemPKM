"""OWL 2 RL inference service for SemPKM.

Orchestrates inference runs: loads data and ontology graphs, runs owlrl
forward-chaining closure expansion, diffs to extract new inferred triples,
classifies by entailment type, filters by enabled types, stores results
in urn:sempkm:inferred, and tracks per-triple state in SQLite.

Uses full recompute strategy on each run (not incremental) for simplicity
and correctness at PKM scale.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import owlrl
import pyshacl
from rdflib import BNode, Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.store import EventStore, Operation
from app.inference.entailments import (
    ENTAILMENT_TYPES,
    MANIFEST_KEY_TO_TYPE,
    classify_entailment,
    filter_by_enabled,
)
from app.inference.models import InferenceTripleState, compute_triple_hash
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Named graph for inferred triples
INFERRED_GRAPH_IRI = "urn:sempkm:inferred"

# Model registry graph
MODELS_GRAPH = "urn:sempkm:models"
SEMPKM_NS = "urn:sempkm:"


@dataclass
class InferenceResult:
    """Result of an inference run."""

    total_inferred: int = 0
    by_entailment_type: dict[str, int] = field(default_factory=dict)
    new_count: int = 0
    preserved_dismissed: int = 0
    preserved_promoted: int = 0
    run_timestamp: str = ""


class InferenceService:
    """Orchestrates OWL 2 RL inference runs and triple management.

    Full recompute strategy: each run drops urn:sempkm:inferred and
    recomputes all inferred triples from scratch. Per-triple dismiss/promote
    state is preserved across runs via SQLite.
    """

    def __init__(
        self,
        client: TriplestoreClient,
        db_session: AsyncSession,
        event_store: EventStore,
    ) -> None:
        self._client = client
        self._db = db_session
        self._event_store = event_store

    async def run_inference(
        self, entailment_config: dict[str, bool]
    ) -> InferenceResult:
        """Run a full inference cycle.

        Steps:
        1. Load all data from urn:sempkm:current via CONSTRUCT
        2. Load ontology graphs from all installed models
        3. Merge data + ontology into rdflib working graph
        4. Run owlrl DeductiveClosure(OWLRL_Semantics).expand()
        5. Diff: new_triples = set(working) - set(data) - set(ontology)
        6. Filter out blank node triples
        7. Filter out triples already in urn:sempkm:current
        8. Classify each triple by entailment type
        9. Filter by enabled entailment types
        10. Clear urn:sempkm:inferred
        11. INSERT DATA inferred triples into urn:sempkm:inferred
        12. Update inference_triple_state table
        13. Log inference run as event
        14. Return InferenceResult

        Args:
            entailment_config: Dict mapping entailment type labels to
                enabled/disabled booleans.

        Returns:
            InferenceResult with counts and details.
        """
        run_timestamp = datetime.now(timezone.utc).isoformat()
        result = InferenceResult(run_timestamp=run_timestamp)

        # 1. Load current data
        data_graph = await self._load_current_data()
        logger.info("Loaded %d data triples from urn:sempkm:current", len(data_graph))

        # 2. Load ontology graphs
        ontology_graph = await self._load_ontology_graphs()
        logger.info("Loaded %d ontology triples", len(ontology_graph))

        if len(ontology_graph) == 0:
            logger.warning("No ontology graphs loaded; inference will produce no results")
            await self._clear_inferred_graph()
            return result

        # 3. Merge into working graph, keep originals for diffing
        original_data_triples = set(data_graph)
        ontology_triples = set(ontology_graph)

        working = Graph()
        for t in data_graph:
            working.add(t)
        for t in ontology_graph:
            working.add(t)

        # 4. Run OWL 2 RL closure
        logger.info("Running OWL 2 RL closure expansion...")
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(working)
        logger.info("Closure expansion complete: %d total triples", len(working))

        # 4b. Run SHACL-AF rules (if enabled)
        rule_new_triples: set[tuple] = set()
        if entailment_config.get("sh:rule", False) or entailment_config.get("shacl_rules", False):
            rules_graph = await self._load_rules_graphs()
            if len(rules_graph) > 0:
                pre_rules = set(working)
                try:
                    expanded = await asyncio.to_thread(
                        pyshacl.shacl_rules,
                        working,
                        shacl_graph=rules_graph,
                        advanced=True,
                        iterate_rules=True,
                    )
                    rule_new = set(expanded) - pre_rules
                    for t in rule_new:
                        working.add(t)
                    logger.info("SHACL rules produced %d new triples", len(rule_new))
                except TypeError:
                    # iterate_rules may not be supported -- fall back to single pass
                    expanded = await asyncio.to_thread(
                        pyshacl.shacl_rules,
                        working,
                        shacl_graph=rules_graph,
                        advanced=True,
                    )
                    rule_new = set(expanded) - pre_rules
                    for t in rule_new:
                        working.add(t)
                    logger.info("SHACL rules (single pass) produced %d new triples", len(rule_new))
                # Track non-BNode rule triples for classification override
                rule_new_triples = {
                    (s, p, o)
                    for s, p, o in rule_new
                    if not isinstance(s, BNode) and not isinstance(o, BNode)
                }

        # 5. Diff to extract new inferred triples
        all_after = set(working)
        new_triples = all_after - original_data_triples - ontology_triples

        # 6. Filter out blank node triples
        new_triples = {
            (s, p, o)
            for s, p, o in new_triples
            if not isinstance(s, BNode) and not isinstance(o, BNode)
        }
        logger.info("New triples after blank node filter: %d", len(new_triples))

        # 7. Filter out triples already in urn:sempkm:current (user takes precedence)
        new_triples = new_triples - original_data_triples
        logger.info("New triples after user-data filter: %d", len(new_triples))

        # 8. Classify each triple by entailment type
        classified: list[tuple[tuple, str]] = []
        for s, p, o in new_triples:
            if (s, p, o) in rule_new_triples:
                classified.append(((s, p, o), "sh:rule"))
            else:
                etype = classify_entailment(s, p, o, ontology_graph)
                if etype is not None:
                    classified.append(((s, p, o), etype))

        logger.info("Classified %d of %d new triples", len(classified), len(new_triples))

        # 9. Filter by enabled entailment types
        enabled_types = {
            etype for etype, enabled in entailment_config.items() if enabled
        }
        filtered = filter_by_enabled(classified, enabled_types)
        logger.info(
            "After entailment filtering (%s enabled): %d triples",
            enabled_types,
            len(filtered),
        )

        # 10. Clear urn:sempkm:inferred
        await self._clear_inferred_graph()

        # 11. INSERT DATA inferred triples into urn:sempkm:inferred
        if filtered:
            await self._store_inferred_triples(
                [(t, etype) for t, etype in filtered]
            )

        # 12. Update inference_triple_state table
        await self._update_triple_states(filtered, run_timestamp, result)

        # 13. Populate result counts
        result.total_inferred = len(filtered)
        type_counts: dict[str, int] = {}
        for _, etype in filtered:
            type_counts[etype] = type_counts.get(etype, 0) + 1
        result.by_entailment_type = type_counts

        # 14. Log inference run as event
        await self._log_inference_event(result)

        logger.info(
            "Inference run complete: %d total inferred, %d new, %d dismissed preserved, %d promoted preserved",
            result.total_inferred,
            result.new_count,
            result.preserved_dismissed,
            result.preserved_promoted,
        )

        return result

    async def get_inferred_triples(
        self, filters: dict | None = None
    ) -> list[dict]:
        """Query urn:sempkm:inferred and join with inference_triple_state.

        Args:
            filters: Optional dict with keys: entailment_type, status,
                object_type, date_from, date_to.

        Returns:
            List of dicts with subject, predicate, object, entailment_type,
            status, inferred_at, triple_hash.
        """
        stmt = select(InferenceTripleState).where(
            InferenceTripleState.status != "promoted"
        )

        if filters:
            if "entailment_type" in filters and filters["entailment_type"]:
                stmt = stmt.where(
                    InferenceTripleState.entailment_type == filters["entailment_type"]
                )
            if "status" in filters and filters["status"]:
                stmt = stmt.where(
                    InferenceTripleState.status == filters["status"]
                )
            if "object_type" in filters and filters["object_type"]:
                type_slug = filters["object_type"]
                stmt = stmt.where(
                    (InferenceTripleState.subject_iri.contains(type_slug))
                    | (InferenceTripleState.object_iri.contains(type_slug))
                )
            if "date_from" in filters and filters["date_from"]:
                stmt = stmt.where(
                    InferenceTripleState.inferred_at >= filters["date_from"]
                )
            if "date_to" in filters and filters["date_to"]:
                # Include the full end day
                stmt = stmt.where(
                    InferenceTripleState.inferred_at <= filters["date_to"] + "T23:59:59"
                )

        stmt = stmt.order_by(InferenceTripleState.inferred_at.desc())

        db_result = await self._db.execute(stmt)
        rows = db_result.scalars().all()

        return [
            {
                "triple_hash": row.triple_hash,
                "subject": row.subject_iri,
                "predicate": row.predicate_iri,
                "object": row.object_iri,
                "entailment_type": row.entailment_type,
                "status": row.status,
                "inferred_at": row.inferred_at,
                "source_model_id": row.source_model_id,
            }
            for row in rows
        ]

    async def dismiss_triple(self, triple_hash: str) -> dict | None:
        """Dismiss an inferred triple.

        Sets status='dismissed' in inference_triple_state and removes
        the triple from urn:sempkm:inferred graph.

        Args:
            triple_hash: The SHA-256 hash identifying the triple.

        Returns:
            Updated triple dict, or None if not found.
        """
        result = await self._db.execute(
            select(InferenceTripleState).where(
                InferenceTripleState.triple_hash == triple_hash
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        now = datetime.now(timezone.utc).isoformat()
        row.status = "dismissed"
        row.dismissed_at = now

        # Remove from inferred graph
        await self._remove_triple_from_inferred(
            row.subject_iri, row.predicate_iri, row.object_iri
        )

        return {
            "triple_hash": row.triple_hash,
            "subject": row.subject_iri,
            "predicate": row.predicate_iri,
            "object": row.object_iri,
            "entailment_type": row.entailment_type,
            "status": row.status,
            "inferred_at": row.inferred_at,
        }

    async def promote_triple(self, triple_hash: str) -> dict | None:
        """Promote an inferred triple to user data.

        Copies the triple to urn:sempkm:current via EventStore.commit(),
        sets status='promoted' in inference_triple_state, and removes
        from urn:sempkm:inferred.

        Args:
            triple_hash: The SHA-256 hash identifying the triple.

        Returns:
            Updated triple dict, or None if not found.
        """
        result = await self._db.execute(
            select(InferenceTripleState).where(
                InferenceTripleState.triple_hash == triple_hash
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        now = datetime.now(timezone.utc).isoformat()

        # Copy to urn:sempkm:current via EventStore
        s = URIRef(row.subject_iri)
        p = URIRef(row.predicate_iri)
        o = URIRef(row.object_iri)

        operation = Operation(
            operation_type="inference.promote",
            affected_iris=[row.subject_iri, row.object_iri],
            description=f"Promoted inferred triple: {row.subject_iri} {row.predicate_iri} {row.object_iri}",
            data_triples=[(s, p, o)],
            materialize_inserts=[(s, p, o)],
            materialize_deletes=[],
        )
        await self._event_store.commit([operation])

        # Update state
        row.status = "promoted"
        row.promoted_at = now

        # Remove from inferred graph
        await self._remove_triple_from_inferred(
            row.subject_iri, row.predicate_iri, row.object_iri
        )

        return {
            "triple_hash": row.triple_hash,
            "subject": row.subject_iri,
            "predicate": row.predicate_iri,
            "object": row.object_iri,
            "entailment_type": row.entailment_type,
            "status": row.status,
            "inferred_at": row.inferred_at,
        }

    async def _load_current_data(self) -> Graph:
        """Load all triples from urn:sempkm:current via CONSTRUCT."""
        sparql = "CONSTRUCT { ?s ?p ?o } FROM <urn:sempkm:current> WHERE { ?s ?p ?o }"
        turtle_bytes = await self._client.construct(sparql)
        graph = Graph()
        if turtle_bytes.strip():
            graph.parse(data=turtle_bytes, format="turtle")
        return graph

    async def _load_ontology_graphs(self) -> Graph:
        """Load ontology graphs from all installed models.

        Same pattern as model_shapes_loader: query model registry for
        installed models, CONSTRUCT from each model's ontology graph.
        """
        sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        if not bindings:
            return Graph()

        from_clauses = []
        for b in bindings:
            model_id = b["modelId"]["value"]
            from_clauses.append(f"FROM <urn:sempkm:model:{model_id}:ontology>")

        construct_sparql = (
            "CONSTRUCT { ?s ?p ?o }\n"
            + "\n".join(from_clauses)
            + "\nWHERE { ?s ?p ?o }"
        )
        turtle_bytes = await self._client.construct(construct_sparql)
        ontology = Graph()
        if turtle_bytes.strip():
            ontology.parse(data=turtle_bytes, format="turtle")
        return ontology

    async def _load_rules_graphs(self) -> Graph:
        """Load rules graphs from all installed models.

        Same pattern as _load_ontology_graphs: query model registry for
        installed models, CONSTRUCT from each model's rules graph.
        """
        sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        if not bindings:
            return Graph()

        from_clauses = []
        for b in bindings:
            model_id = b["modelId"]["value"]
            from_clauses.append(f"FROM <urn:sempkm:model:{model_id}:rules>")

        construct_sparql = (
            "CONSTRUCT { ?s ?p ?o }\n"
            + "\n".join(from_clauses)
            + "\nWHERE { ?s ?p ?o }"
        )
        turtle_bytes = await self._client.construct(construct_sparql)
        rules = Graph()
        if turtle_bytes.strip():
            rules.parse(data=turtle_bytes, format="turtle")
        return rules

    async def _clear_inferred_graph(self) -> None:
        """Clear all triples from urn:sempkm:inferred."""
        sparql = f"CLEAR GRAPH <{INFERRED_GRAPH_IRI}>"
        try:
            await self._client.update(sparql)
        except Exception as e:
            # CLEAR GRAPH on non-existent graph may fail in some triplestores
            logger.debug("Clear inferred graph: %s", e)

    async def _store_inferred_triples(
        self, triples_with_types: list[tuple[tuple, str]]
    ) -> None:
        """Store inferred triples in urn:sempkm:inferred via SPARQL INSERT DATA."""
        if not triples_with_types:
            return

        triple_lines = []
        for (s, p, o), _ in triples_with_types:
            triple_lines.append(f"  <{s}> <{p}> <{o}> .")

        # Batch into chunks to avoid overly large SPARQL statements
        batch_size = 500
        for i in range(0, len(triple_lines), batch_size):
            batch = triple_lines[i : i + batch_size]
            triples_str = "\n".join(batch)
            sparql = f"""INSERT DATA {{
  GRAPH <{INFERRED_GRAPH_IRI}> {{
{triples_str}
  }}
}}"""
            await self._client.update(sparql)

    async def _update_triple_states(
        self,
        filtered: list[tuple[tuple, str]],
        run_timestamp: str,
        result: InferenceResult,
    ) -> None:
        """Update inference_triple_state table for the current run.

        - New triples get 'active' status
        - Previously dismissed triples stay dismissed (not re-added to graph)
        - Previously promoted triples stay promoted
        - Stale triples (in DB but not in current run) are left as-is

        Args:
            filtered: List of ((s, p, o), entailment_type) tuples.
            run_timestamp: ISO timestamp of this run.
            result: InferenceResult to populate with counts.
        """
        new_count = 0

        for (s, p, o), etype in filtered:
            s_str = str(s)
            p_str = str(p)
            o_str = str(o)
            triple_hash = compute_triple_hash(s_str, p_str, o_str)

            # Check existing state
            existing = await self._db.execute(
                select(InferenceTripleState).where(
                    InferenceTripleState.triple_hash == triple_hash
                )
            )
            row = existing.scalar_one_or_none()

            if row is None:
                # New triple
                new_state = InferenceTripleState(
                    triple_hash=triple_hash,
                    status="active",
                    subject_iri=s_str,
                    predicate_iri=p_str,
                    object_iri=o_str,
                    entailment_type=etype,
                    inferred_at=run_timestamp,
                )
                self._db.add(new_state)
                new_count += 1
            else:
                # Update timestamp for existing triple
                row.inferred_at = run_timestamp
                row.entailment_type = etype

                if row.status == "dismissed":
                    result.preserved_dismissed += 1
                    # Remove from inferred graph (was just added in step 11)
                    await self._remove_triple_from_inferred(s_str, p_str, o_str)
                elif row.status == "promoted":
                    result.preserved_promoted += 1
                    # Remove from inferred graph (already in current as user data)
                    await self._remove_triple_from_inferred(s_str, p_str, o_str)

        result.new_count = new_count

    async def _remove_triple_from_inferred(
        self, s: str, p: str, o: str
    ) -> None:
        """Remove a single triple from urn:sempkm:inferred."""
        sparql = f"""DELETE DATA {{
  GRAPH <{INFERRED_GRAPH_IRI}> {{
    <{s}> <{p}> <{o}> .
  }}
}}"""
        try:
            await self._client.update(sparql)
        except Exception as e:
            logger.debug("Remove triple from inferred: %s", e)

    async def _log_inference_event(self, result: InferenceResult) -> None:
        """Log the inference run as an event via EventStore."""
        from rdflib import Literal

        description = (
            f"Inference run: {result.total_inferred} triples inferred "
            f"({result.new_count} new, {result.preserved_dismissed} dismissed, "
            f"{result.preserved_promoted} promoted)"
        )

        operation = Operation(
            operation_type="inference.run",
            affected_iris=[INFERRED_GRAPH_IRI],
            description=description,
            data_triples=[],
            materialize_inserts=[],
            materialize_deletes=[],
        )

        try:
            await self._event_store.commit([operation])
        except Exception as e:
            logger.warning("Failed to log inference event: %s", e)

    async def get_entailment_config(self, user_id=None) -> dict[str, bool]:
        """Get entailment configuration with manifest defaults and user overrides.

        Queries installed models for manifest entailment_defaults, then applies
        any user-specific overrides from SettingsService. If a type is enabled
        for ANY installed model, it is enabled in the merged config.

        Args:
            user_id: Optional user UUID. When provided, SettingsService user
                overrides are applied on top of manifest defaults.

        Returns:
            Dict mapping entailment type labels to enabled booleans.
            Falls back to hardcoded defaults (only owl:inverseOf) if no
            models are installed or user_id is not provided.
        """
        import os

        import yaml

        from app.services.settings import SettingsService

        # Default config: only inverseOf enabled (fallback)
        config = {etype: False for etype in ENTAILMENT_TYPES}
        config["owl:inverseOf"] = True

        # Query installed models from the triplestore
        sparql = f"""SELECT ?modelId WHERE {{
  GRAPH <{MODELS_GRAPH}> {{
    ?model a <{SEMPKM_NS}MentalModel> ;
           <{SEMPKM_NS}modelId> ?modelId .
  }}
}}"""
        try:
            result = await self._client.query(sparql)
            bindings = result.get("results", {}).get("bindings", [])
        except Exception:
            bindings = []

        if not bindings:
            return config

        # Load manifest defaults for each model and merge
        model_ids = [b["modelId"]["value"] for b in bindings]
        merged_config = {etype: False for etype in ENTAILMENT_TYPES}

        for model_id in model_ids:
            manifest_path = os.path.join("/app/models", model_id, "manifest.yaml")
            model_defaults = {key: False for key in MANIFEST_KEY_TO_TYPE}

            try:
                with open(manifest_path) as f:
                    raw = yaml.safe_load(f)
                if raw and "entailment_defaults" in raw:
                    for key, val in raw["entailment_defaults"].items():
                        if key in MANIFEST_KEY_TO_TYPE:
                            model_defaults[key] = bool(val)
            except Exception:
                pass

            # Apply user overrides if user_id provided
            if user_id is not None:
                try:
                    settings_svc = SettingsService()
                    overrides = await settings_svc.get_user_overrides(user_id, self._db)
                    for manifest_key in MANIFEST_KEY_TO_TYPE:
                        settings_key = f"inference.{model_id}.{manifest_key}"
                        if settings_key in overrides:
                            model_defaults[manifest_key] = overrides[settings_key] == "true"
                except Exception:
                    logger.warning("Failed to load user overrides for model %s", model_id)

            # Merge: if enabled for ANY model, enable in merged config
            for manifest_key, etype in MANIFEST_KEY_TO_TYPE.items():
                if model_defaults.get(manifest_key, False):
                    merged_config[etype] = True

        return merged_config
