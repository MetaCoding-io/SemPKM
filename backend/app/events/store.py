"""Event store: immutable event graph creation and current state materialization.

Every write to SemPKM flows through EventStore.commit(), which atomically:
1. Creates an immutable event named graph with metadata + data triples
2. Materializes changes into the current state graph (inserts and deletes)

Both operations happen in a single RDF4J transaction -- if either fails,
the entire transaction rolls back (per research Pitfall 2).

All materialization SPARQL uses GRAPH <urn:sempkm:current> clauses to
scope changes to the current state graph (per research Pitfall 3).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from rdflib import URIRef, Literal, BNode, Variable
from rdflib.namespace import RDF, XSD

from app.events.models import (
    EVENT_TYPE,
    EVENT_TIMESTAMP,
    EVENT_OPERATION,
    EVENT_AFFECTED,
    EVENT_DESCRIPTION,
)
from app.rdf.iri import mint_event_iri
from app.rdf.namespaces import CURRENT_GRAPH_IRI
from app.triplestore.client import TriplestoreClient


@dataclass
class Operation:
    """A single operation within an event commit.

    Represents one logical change (e.g., object.create, edge.create) with
    the triples to store in the event graph and the materialization actions
    to apply to the current state graph.
    """

    operation_type: str  # e.g. "object.create"
    affected_iris: list[str]  # IRIs changed by this operation
    description: str  # Human-readable description
    data_triples: list[tuple]  # (s, p, o) triples to add to event graph
    materialize_inserts: list[tuple] = field(
        default_factory=list
    )  # Triples to INSERT into current state
    materialize_deletes: list[tuple] = field(
        default_factory=list
    )  # Triple patterns to DELETE from current state


@dataclass
class EventResult:
    """Result of a successful event commit."""

    event_iri: URIRef
    timestamp: str
    affected_iris: list[str]


class EventStore:
    """Creates immutable event named graphs and materializes current state.

    Uses TriplestoreClient transaction methods to ensure atomicity between
    event graph creation and current state materialization.
    """

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def commit(self, operations: list[Operation]) -> EventResult:
        """Commit one or more operations as a single atomic event.

        Creates an immutable event named graph with metadata and data triples,
        then materializes all inserts/deletes into the current state graph.
        Both happen in a single RDF4J transaction.

        Args:
            operations: List of Operation dataclasses to commit atomically.

        Returns:
            EventResult with the event IRI, timestamp, and all affected IRIs.

        Raises:
            Exception: On any failure, the transaction is rolled back.
        """
        event_iri = mint_event_iri()
        timestamp = datetime.now(timezone.utc).isoformat()

        # Collect all affected IRIs and operation types across operations
        all_affected_iris: list[str] = []
        all_operation_types: set[str] = set()
        for op in operations:
            all_affected_iris.extend(op.affected_iris)
            all_operation_types.add(op.operation_type)

        # Combined description
        descriptions = [op.description for op in operations]
        combined_description = "; ".join(descriptions)

        txn_url = await self._client.begin_transaction()
        try:
            # Step 1: Build and write the event named graph
            event_triples: list[tuple] = []

            # Event metadata
            event_triples.append((event_iri, RDF.type, EVENT_TYPE))
            event_triples.append(
                (event_iri, EVENT_TIMESTAMP, Literal(timestamp, datatype=XSD.dateTime))
            )

            # Combined operation type string
            combined_ops = ",".join(sorted(all_operation_types))
            event_triples.append(
                (event_iri, EVENT_OPERATION, Literal(combined_ops))
            )

            # All affected IRIs
            for iri in all_affected_iris:
                event_triples.append(
                    (event_iri, EVENT_AFFECTED, URIRef(iri))
                )

            # Description
            event_triples.append(
                (event_iri, EVENT_DESCRIPTION, Literal(combined_description))
            )

            # Data triples from all operations
            for op in operations:
                event_triples.extend(op.data_triples)

            # Write event graph
            event_sparql = _build_insert_data_sparql(event_iri, event_triples)
            await self._client.transaction_update(txn_url, event_sparql)

            # Step 2: Materialize deletes from current state graph (before inserts)
            # Deletes must happen first so that Variable patterns like ?old_0
            # only match existing values, not values about to be inserted.
            for op in operations:
                if op.materialize_deletes:
                    delete_sparql = _build_delete_where_sparql(
                        CURRENT_GRAPH_IRI, op.materialize_deletes
                    )
                    await self._client.transaction_update(txn_url, delete_sparql)

            # Step 3: Materialize inserts into current state graph
            all_inserts: list[tuple] = []
            for op in operations:
                all_inserts.extend(op.materialize_inserts)

            if all_inserts:
                insert_sparql = _build_insert_data_sparql(
                    CURRENT_GRAPH_IRI, all_inserts
                )
                await self._client.transaction_update(txn_url, insert_sparql)

            # Commit the transaction (event + materialization are atomic)
            await self._client.commit_transaction(txn_url)

        except Exception:
            # Rollback on any error
            try:
                await self._client.rollback_transaction(txn_url)
            except Exception:
                pass  # Best-effort rollback; original error propagates
            raise

        return EventResult(
            event_iri=event_iri,
            timestamp=timestamp,
            affected_iris=all_affected_iris,
        )


def _serialize_rdf_term(term) -> str:
    """Serialize an rdflib term to its SPARQL representation.

    Handles URIRef (wrapped in <>), Literal (with datatype/language),
    BNode, and Variable (SPARQL ?var).

    Args:
        term: An rdflib URIRef, Literal, BNode, or Variable.

    Returns:
        SPARQL-safe string representation.
    """
    if isinstance(term, Variable):
        return f"?{term}"
    elif isinstance(term, URIRef):
        return f"<{term}>"
    elif isinstance(term, Literal):
        # Escape special characters in the literal value
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
        raise ValueError(f"Unsupported RDF term type: {type(term)}")


def _build_insert_data_sparql(
    graph_iri: URIRef, triples: list[tuple]
) -> str:
    """Build SPARQL INSERT DATA with GRAPH clause.

    Args:
        graph_iri: The named graph to insert into.
        triples: List of (s, p, o) tuples to insert.

    Returns:
        SPARQL INSERT DATA string.
    """
    triple_lines = []
    for s, p, o in triples:
        triple_lines.append(
            f"    {_serialize_rdf_term(s)} {_serialize_rdf_term(p)} {_serialize_rdf_term(o)} ."
        )
    triples_str = "\n".join(triple_lines)

    return f"""INSERT DATA {{
  GRAPH <{graph_iri}> {{
{triples_str}
  }}
}}"""


def _build_delete_where_sparql(
    graph_iri: URIRef, triple_patterns: list[tuple]
) -> str:
    """Build SPARQL DELETE WHERE for removing triples from a named graph.

    Each triple pattern in the list is matched and deleted. Patterns may
    contain rdflib terms (URIRef, Literal) for exact matches.

    Args:
        graph_iri: The named graph to delete from.
        triple_patterns: List of (s, p, o) triple patterns.

    Returns:
        SPARQL DELETE WHERE string.
    """
    pattern_lines = []
    for s, p, o in triple_patterns:
        pattern_lines.append(
            f"    {_serialize_rdf_term(s)} {_serialize_rdf_term(p)} {_serialize_rdf_term(o)} ."
        )
    patterns_str = "\n".join(pattern_lines)

    return f"""DELETE WHERE {{
  GRAPH <{graph_iri}> {{
{patterns_str}
  }}
}}"""


def _build_delete_insert_sparql(
    graph_iri: URIRef,
    deletes: list[tuple],
    inserts: list[tuple],
) -> str:
    """Build SPARQL DELETE/INSERT/WHERE for patch operations.

    Constructs a SPARQL UPDATE that deletes specified patterns and inserts
    new triples within the same operation, scoped to the given named graph.

    Args:
        graph_iri: The named graph to operate on.
        deletes: Triple patterns to delete (may include variables as strings).
        inserts: Triples to insert.

    Returns:
        SPARQL DELETE/INSERT/WHERE string.
    """
    delete_lines = []
    for s, p, o in deletes:
        delete_lines.append(
            f"    {_serialize_rdf_term(s)} {_serialize_rdf_term(p)} {_serialize_rdf_term(o)} ."
        )

    insert_lines = []
    for s, p, o in inserts:
        insert_lines.append(
            f"    {_serialize_rdf_term(s)} {_serialize_rdf_term(p)} {_serialize_rdf_term(o)} ."
        )

    delete_str = "\n".join(delete_lines)
    insert_str = "\n".join(insert_lines)

    return f"""DELETE {{
  GRAPH <{graph_iri}> {{
{delete_str}
  }}
}}
INSERT {{
  GRAPH <{graph_iri}> {{
{insert_str}
  }}
}}
WHERE {{
  GRAPH <{graph_iri}> {{
{delete_str}
  }}
}}"""
