"""RDF import executor — SHACL validation, collision detection, and event-sourced import.

Connects the parser output to the triplestore via EventStore. Builds
Operation dataclasses directly from parsed triples — does NOT use
handle_object_create() — to preserve original IRIs, datatypes, and
language tags from rdflib Literals.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict

from rdflib import Graph
from rdflib.namespace import SH

from app.auth.models import User
from app.events.store import EventStore, Operation
from app.obsidian.broadcast import ScanBroadcast, SSEEvent
from app.rdf_import.models import RdfImportResult, RdfParseResult
from app.services.models import model_shapes_loader
from app.triplestore.client import TriplestoreClient
from app.validation.report import ValidationReport, ValidationResult
from app.rdf.namespaces import CURRENT_GRAPH

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SHACL validation
# ---------------------------------------------------------------------------

async def validate_shacl(
    graph: Graph,
    triplestore_client: TriplestoreClient,
) -> dict[str, list[dict]]:
    """Run SHACL validation against installed model shapes.

    Returns a dict keyed by focus node IRI → list of
    ``{severity, message, path}`` dicts.  When ``allow_warnings=True``,
    ``conforms`` can be True even when warnings exist — so we inspect
    the results graph directly for ``sh:ValidationResult`` triples.
    """
    import pyshacl

    shapes = await model_shapes_loader(triplestore_client)
    if len(shapes) == 0:
        logger.info("No model shapes installed — skipping SHACL validation")
        return {}

    # pyshacl.validate is CPU-bound — run in a thread
    conforms, results_graph, _text = await asyncio.to_thread(
        pyshacl.validate,
        graph,
        shacl_graph=shapes,
        allow_warnings=True,
        allow_infos=True,
        advanced=True,
    )

    # Parse using ValidationReport.from_pyshacl for consistent result extraction
    report = ValidationReport.from_pyshacl(
        event_iri="urn:sempkm:rdf-import:preview",
        results_graph=results_graph,
        conforms=conforms,
        timestamp="",
    )

    # Group results by focus node IRI
    by_focus: dict[str, list[dict]] = defaultdict(list)
    for result in report.results:
        by_focus[result.focus_node].append({
            "severity": result.severity,
            "message": result.message,
            "path": result.path,
        })

    logger.info(
        "SHACL validation: conforms=%s, %d results across %d focus nodes",
        conforms,
        len(report.results),
        len(by_focus),
    )
    return dict(by_focus)


# ---------------------------------------------------------------------------
# IRI collision detection
# ---------------------------------------------------------------------------

async def check_collisions(
    iris: list[str],
    triplestore_client: TriplestoreClient,
) -> set[str]:
    """Check which of the given IRIs already exist in the current state graph.

    Returns the set of IRIs that have at least one triple in
    ``urn:sempkm:current``.
    """
    if not iris:
        return set()

    # Build VALUES clause
    values_entries = " ".join(f"<{iri}>" for iri in iris)
    sparql = f"""SELECT DISTINCT ?s WHERE {{
  GRAPH <{CURRENT_GRAPH}> {{
    ?s ?p ?o .
  }}
  VALUES ?s {{ {values_entries} }}
}}"""

    result = await triplestore_client.query(sparql)
    bindings = result.get("results", {}).get("bindings", [])
    existing = {b["s"]["value"] for b in bindings}

    logger.info(
        "Collision check: %d/%d IRIs already exist",
        len(existing),
        len(iris),
    )
    return existing


# ---------------------------------------------------------------------------
# Import execution
# ---------------------------------------------------------------------------

async def execute_import(
    parse_result: RdfParseResult,
    selected_iris: list[str],
    user: User,
    event_store: EventStore,
    triplestore_client: TriplestoreClient,
    broadcast: ScanBroadcast,
) -> RdfImportResult:
    """Execute the RDF import: build Operations and commit via EventStore.

    For each selected subject, builds an Operation with the subject's
    triples directly — preserving original IRIs, datatypes, and language
    tags.  Uses per-subject commit for ≤10 subjects, bulk commit for >10.

    Broadcasts SSE progress events throughout:
    - ``import_progress``: ``{phase, current, total, current_subject}``
    - ``import_complete``: stats dict on success
    - ``import_error``: ``{message}`` on failure
    """
    start = time.monotonic()
    result = RdfImportResult()

    # Build subject lookup from parse result
    subject_map = {si.iri: si for si in parse_result.subjects}
    selected_subjects = [
        subject_map[iri] for iri in selected_iris if iri in subject_map
    ]

    if not selected_subjects:
        broadcast.publish(SSEEvent(
            event="import_error",
            data={"message": "No valid subjects selected for import"},
        ))
        return result

    total = len(selected_subjects)
    use_bulk = total > 10

    try:
        # Build user IRI for provenance
        from rdflib import URIRef
        user_iri = URIRef(f"urn:sempkm:user:{user.id}")

        if use_bulk:
            # Bulk mode: build all operations, commit in chunks of 500
            all_operations: list[Operation] = []

            for i, si in enumerate(selected_subjects, 1):
                broadcast.publish(SSEEvent(
                    event="import_progress",
                    data={
                        "phase": "building",
                        "current": i,
                        "total": total,
                        "current_subject": si.label or si.iri,
                    },
                ))

                op = _build_operation(si)
                all_operations.append(op)

            # Commit in chunks
            chunk_size = 500
            for chunk_start in range(0, len(all_operations), chunk_size):
                chunk = all_operations[chunk_start:chunk_start + chunk_size]
                chunk_end = min(chunk_start + chunk_size, len(all_operations))

                broadcast.publish(SSEEvent(
                    event="import_progress",
                    data={
                        "phase": "committing",
                        "current": chunk_end,
                        "total": total,
                        "current_subject": f"batch {chunk_start // chunk_size + 1}",
                    },
                ))

                await event_store.commit_bulk(
                    operations=chunk,
                    performed_by=user_iri,
                    summary=f"RDF import: {len(chunk)} subjects",
                    source="rdf-import",
                )
                result.created += len(chunk)

        else:
            # Per-subject mode: commit each subject individually
            for i, si in enumerate(selected_subjects, 1):
                broadcast.publish(SSEEvent(
                    event="import_progress",
                    data={
                        "phase": "importing",
                        "current": i,
                        "total": total,
                        "current_subject": si.label or si.iri,
                    },
                ))

                try:
                    op = _build_operation(si)
                    await event_store.commit(
                        operations=[op],
                        performed_by=user_iri,
                    )
                    result.created += 1
                except Exception as exc:
                    logger.error("Failed to import subject %s: %s", si.iri, exc)
                    result.errors.append({
                        "iri": si.iri,
                        "message": str(exc),
                    })

        result.duration_seconds = round(time.monotonic() - start, 2)
        result.skipped = total - result.created - len(result.errors)

        broadcast.publish(SSEEvent(
            event="import_complete",
            data=result.to_dict(),
        ))

        logger.info(
            "RDF import complete: %d created, %d skipped, %d errors in %.2fs",
            result.created,
            result.skipped,
            len(result.errors),
            result.duration_seconds,
        )

    except Exception as exc:
        result.duration_seconds = round(time.monotonic() - start, 2)
        logger.error("RDF import failed: %s", exc, exc_info=True)
        broadcast.publish(SSEEvent(
            event="import_error",
            data={"message": str(exc)},
        ))

    return result


def _build_operation(si) -> Operation:
    """Build an Operation from a SubjectInfo, preserving original RDF terms.

    The triples stored in SubjectInfo are raw rdflib (s, p, o) tuples
    with URIRef, Literal (including datatype and language), and BNode
    terms.  We pass them through directly — no re-serialization — so
    datatypes and language tags are preserved exactly.
    """
    return Operation(
        operation_type="rdf.import",
        affected_iris=[si.iri],
        description=f"Imported RDF subject {si.iri}",
        data_triples=list(si.triples),
        materialize_inserts=list(si.triples),
        materialize_deletes=[],
    )
