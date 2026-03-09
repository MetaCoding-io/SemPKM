"""Event query service for browsing the immutable event log.

Provides cursor-paginated SPARQL queries over event named graphs
(urn:sempkm:event:*). Supports filtering by operation type, user,
affected object, and date range.
"""

from __future__ import annotations

import difflib
import logging
from collections import OrderedDict
from dataclasses import dataclass, field

from rdflib import URIRef, Literal, Variable

from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Priority-ordered list for determining the primary operation in compound events
_OP_PRIORITY = [
    "object.create",
    "object.patch",
    "body.set",
    "edge.create",
    "edge.patch",
    "edge.create.undo",
]


def get_primary_operation(op_type_str: str) -> tuple[str, list[str]]:
    """Extract the primary operation from a possibly compound operation type.

    Splits on commas and returns (primary_op, secondary_ops) where primary_op
    is the highest-priority operation found, and secondary_ops are the rest.
    If only one operation, returns (op, []).
    """
    parts = [p.strip() for p in op_type_str.split(",") if p.strip()]
    if len(parts) <= 1:
        return (parts[0] if parts else op_type_str, [])
    # Find highest-priority operation
    for candidate in _OP_PRIORITY:
        if candidate in parts:
            remaining = [p for p in parts if p != candidate]
            return (candidate, remaining)
    # Fallback: first part is primary
    return (parts[0], parts[1:])


@dataclass
class EventSummary:
    """Summary of one event for the timeline list view."""

    event_iri: str
    timestamp: str           # ISO datetime string from SPARQL
    operation_type: str
    affected_iris: list[str] = field(default_factory=list)  # CSV-split from GROUP_CONCAT result
    performed_by: str | None = None   # user IRI, None if absent
    description: str | None = None


@dataclass
class EventDetail:
    """Detailed view of a single event for the diff panel."""

    summary: EventSummary
    data_triples: list[tuple[str, str, str]]  # (s, p, o) as strings
    before_values: dict[str, str]             # predicate_iri -> old_value_string
    new_values: dict[str, str]                # predicate_iri -> new_value_string
    body_diff: list[dict] | None              # for body.set: [{type: add|remove|context, text: str}]


class EventQueryService:
    """Query service for browsing and analysing event named graphs.

    All queries are read-only; the event store remains immutable.
    """

    PAGE_SIZE = 50

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def list_events(
        self,
        cursor_timestamp: str | None = None,
        op_type: str | None = None,
        user_iri: str | None = None,
        object_iri: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> tuple[list[EventSummary], str | None]:
        """Return a cursor-paginated page of events in reverse chronological order.

        Returns (events, next_cursor).
        next_cursor is None when there are no more events.
        Uses GROUP_CONCAT to collapse multiple sempkm:affectedIRI rows per event.
        Falls back to Python-side grouping if GROUP_CONCAT is not supported.
        """
        filters: list[str] = []

        if cursor_timestamp:
            filters.append(f'FILTER(?timestamp < "{cursor_timestamp}"^^xsd:dateTime)')
        if op_type:
            filters.append(f'FILTER(STR(?opType) = "{op_type}")')
        if user_iri:
            filters.append(f'FILTER(?performedBy = <{user_iri}>)')
        if object_iri:
            filters.append(f'FILTER(?affectedIRI = <{object_iri}>)')
        if date_from:
            filters.append(f'FILTER(?timestamp >= "{date_from}"^^xsd:dateTime)')
        if date_to:
            filters.append(f'FILTER(?timestamp <= "{date_to}"^^xsd:dateTime)')

        filter_block = "\n  ".join(filters)

        # Primary query: GROUP_CONCAT collapses multiple affectedIRI rows
        group_concat_sparql = f"""PREFIX sempkm: <urn:sempkm:>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?event ?timestamp ?opType (GROUP_CONCAT(STR(?affectedIRI); separator=",") AS ?affected) ?performedBy ?description
WHERE {{
  GRAPH ?event {{
    ?event a sempkm:Event ;
           sempkm:timestamp ?timestamp ;
           sempkm:operationType ?opType ;
           sempkm:affectedIRI ?affectedIRI .
    OPTIONAL {{ ?event sempkm:performedBy ?performedBy }}
    OPTIONAL {{ ?event sempkm:description ?description }}
  }}
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
  {filter_block}
}}
GROUP BY ?event ?timestamp ?opType ?performedBy ?description
ORDER BY DESC(?timestamp)
LIMIT 51
"""

        try:
            result = await self._client.query(group_concat_sparql)
            rows = result.get("results", {}).get("bindings", [])
            events = self._parse_group_concat_rows(rows)
        except Exception:
            # Fallback: plain SELECT + Python-side grouping
            events = await self._list_events_fallback(
                filter_block=filter_block,
            )

        # Cursor: if we got 51 rows, there is a next page
        next_cursor: str | None = None
        if len(events) > self.PAGE_SIZE:
            next_cursor = events[self.PAGE_SIZE - 1].timestamp
            events = events[: self.PAGE_SIZE]

        return events, next_cursor

    async def get_event_detail(self, event_iri: str) -> EventDetail | None:
        """Return detailed diff information for a single event.

        Queries the event named graph for data triples and metadata,
        reconstructs before/after values, and computes body diffs for body.set events.
        Returns None if the event does not exist.
        """
        # Query event metadata
        meta_sparql = f"""PREFIX sempkm: <urn:sempkm:>
SELECT ?timestamp ?opType ?affectedIRI ?performedBy ?description
WHERE {{
  GRAPH <{event_iri}> {{
    <{event_iri}> sempkm:timestamp ?timestamp ;
                  sempkm:operationType ?opType .
    OPTIONAL {{ <{event_iri}> sempkm:affectedIRI ?affectedIRI }}
    OPTIONAL {{ <{event_iri}> sempkm:performedBy ?performedBy }}
    OPTIONAL {{ <{event_iri}> sempkm:description ?description }}
  }}
}}"""

        try:
            meta_result = await self._client.query(meta_sparql)
            meta_rows = meta_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Failed to query metadata for event %s", event_iri, exc_info=True)
            return None

        if not meta_rows:
            return None

        # Build EventSummary from metadata rows
        first_row = meta_rows[0]
        timestamp = first_row["timestamp"]["value"]
        op_type = first_row["opType"]["value"]
        affected_iris: list[str] = []
        for row in meta_rows:
            iri = row.get("affectedIRI", {}).get("value", "")
            if iri and iri not in affected_iris:
                affected_iris.append(iri)
        performed_by = first_row.get("performedBy", {}).get("value") if "performedBy" in first_row else None
        description = first_row.get("description", {}).get("value") if "description" in first_row else None

        summary = EventSummary(
            event_iri=event_iri,
            timestamp=timestamp,
            operation_type=op_type,
            affected_iris=affected_iris,
            performed_by=performed_by,
            description=description,
        )

        # Query data triples (exclude event metadata triples)
        data_sparql = f"""PREFIX sempkm: <urn:sempkm:>
SELECT ?s ?p ?o
WHERE {{
  GRAPH <{event_iri}> {{
    ?s ?p ?o .
    FILTER(
      ?s != <{event_iri}> ||
      ?p NOT IN (
        sempkm:timestamp, sempkm:operationType, sempkm:affectedIRI,
        sempkm:performedBy, sempkm:performedByRole, sempkm:description,
        <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>
      )
    )
  }}
}}"""

        try:
            data_result = await self._client.query(data_sparql)
            data_rows = data_result.get("results", {}).get("bindings", [])
        except Exception:
            logger.warning("Failed to query data triples for event %s", event_iri, exc_info=True)
            data_rows = []

        data_triples: list[tuple[str, str, str]] = []
        for row in data_rows:
            s = row["s"]["value"]
            p = row["p"]["value"]
            o = row["o"]["value"]
            data_triples.append((s, p, o))

        # Build new_values: predicate -> object for the primary affected IRI
        subject_iri = affected_iris[0] if affected_iris else None
        new_values: dict[str, str] = {}
        if subject_iri:
            for s, p, o in data_triples:
                if s == subject_iri:
                    new_values[p] = o

        # For create operations, skip backward query — no before state
        before_values: dict[str, str] = {}
        if "object.create" not in op_type and "edge.create" not in op_type and subject_iri and new_values:
            for pred_iri in new_values:
                old_val = await self._query_before_value(subject_iri, pred_iri, timestamp)
                if old_val is not None:
                    before_values[pred_iri] = old_val

        # Compute body_diff for body.set events
        body_diff: list[dict] | None = None
        if "body.set" in op_type and new_values and before_values:
            # The body predicate is the one in new_values
            body_pred = next(iter(new_values), None)
            if body_pred:
                old_body = before_values.get(body_pred, "")
                new_body = new_values.get(body_pred, "")
                body_diff = self._compute_body_diff(old_body, new_body)

        return EventDetail(
            summary=summary,
            data_triples=data_triples,
            before_values=before_values,
            new_values=new_values,
            body_diff=body_diff,
        )

    async def _query_before_value(
        self, subject_iri: str, predicate_iri: str, this_event_timestamp: str
    ) -> str | None:
        """Find the most recent value for subject+predicate before a given timestamp.

        Searches all event named graphs for the last time this predicate was set
        on this subject before the given event's timestamp.
        Returns the value string, or None if not found.
        """
        sparql = f"""PREFIX sempkm: <urn:sempkm:>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?old_value
WHERE {{
  GRAPH ?prev_event {{
    ?prev_event sempkm:timestamp ?prev_ts .
    <{subject_iri}> <{predicate_iri}> ?old_value .
  }}
  FILTER(STRSTARTS(STR(?prev_event), "urn:sempkm:event:"))
  FILTER(?prev_ts < "{this_event_timestamp}"^^xsd:dateTime)
}}
ORDER BY DESC(?prev_ts)
LIMIT 1"""

        try:
            result = await self._client.query(sparql)
            rows = result.get("results", {}).get("bindings", [])
            if rows:
                return rows[0]["old_value"]["value"]
        except Exception:
            logger.warning(
                "Failed to query before-value for %s %s", subject_iri, predicate_iri, exc_info=True
            )
        return None

    def _compute_body_diff(self, old_body: str, new_body: str) -> list[dict]:
        """Compute a unified diff between two body strings.

        Returns a list of {type: 'add'|'remove'|'context', text: str} dicts
        suitable for rendering in the diff template.
        """
        old_lines = (old_body or "").splitlines(keepends=True)
        new_lines = (new_body or "").splitlines(keepends=True)
        diff_lines: list[dict] = []
        for line in difflib.unified_diff(old_lines, new_lines, lineterm=""):
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            elif line.startswith("+"):
                diff_lines.append({"type": "add", "text": line[1:]})
            elif line.startswith("-"):
                diff_lines.append({"type": "remove", "text": line[1:]})
            else:
                diff_lines.append({"type": "context", "text": line[1:] if line.startswith(" ") else line})
        return diff_lines if diff_lines else [{"type": "context", "text": "(no changes)"}]

    async def build_compensation(
        self, event_iri: str, detail: "EventDetail"
    ) -> "Operation | None":
        """Build a compensation Operation that reverses the given event.

        Returns None if the event type is not reversible or if required
        before-values are missing.
        """
        from app.events.store import Operation

        op_type = detail.summary.operation_type
        subject_iri = detail.summary.affected_iris[0] if detail.summary.affected_iris else None

        if op_type == "object.patch":
            if not detail.before_values or not subject_iri:
                return None
            data_triples: list[tuple] = []
            materialize_inserts: list[tuple] = []
            materialize_deletes: list[tuple] = []
            for pred_iri, old_val in detail.before_values.items():
                if old_val == "(unknown)":
                    continue
                new_val = detail.new_values.get(pred_iri)
                if new_val is not None:
                    materialize_deletes.append(
                        (URIRef(subject_iri), URIRef(pred_iri), Literal(new_val))
                    )
                old_literal = Literal(old_val)
                data_triples.append((URIRef(subject_iri), URIRef(pred_iri), old_literal))
                materialize_inserts.append((URIRef(subject_iri), URIRef(pred_iri), old_literal))
            if not data_triples:
                return None
            return Operation(
                operation_type="object.patch",
                affected_iris=[subject_iri],
                description=f"Undo object.patch: {event_iri}",
                data_triples=data_triples,
                materialize_inserts=materialize_inserts,
                materialize_deletes=materialize_deletes,
            )

        elif op_type == "body.set":
            if not detail.new_values or not subject_iri:
                return None
            body_pred = next(iter(detail.new_values), None)
            if not body_pred:
                return None
            old_body = detail.before_values.get(body_pred)
            new_body = detail.new_values.get(body_pred, "")
            if old_body is None:
                return None
            old_literal = Literal(old_body)
            new_literal = Literal(new_body)
            return Operation(
                operation_type="body.set",
                affected_iris=[subject_iri],
                description=f"Undo body.set: {event_iri}",
                data_triples=[(URIRef(subject_iri), URIRef(body_pred), old_literal)],
                materialize_inserts=[(URIRef(subject_iri), URIRef(body_pred), old_literal)],
                materialize_deletes=[(URIRef(subject_iri), URIRef(body_pred), new_literal)],
            )

        elif op_type == "edge.create":
            if not detail.data_triples:
                return None
            materialize_deletes = []
            for s_str, p_str, o_str in detail.data_triples:
                try:
                    s = URIRef(s_str)
                    p = URIRef(p_str)
                    # Object may be a URI or a literal
                    if o_str.startswith("http") or o_str.startswith("urn"):
                        o = URIRef(o_str)
                    else:
                        o = Literal(o_str)
                    materialize_deletes.append((s, p, o))
                except Exception:
                    pass
            if not materialize_deletes:
                return None
            return Operation(
                operation_type="edge.create.undo",
                affected_iris=detail.summary.affected_iris,
                description=f"Undo edge.create: {event_iri}",
                data_triples=[],
                materialize_inserts=[],
                materialize_deletes=materialize_deletes,
            )

        elif op_type == "edge.patch":
            if not detail.before_values or not subject_iri:
                return None
            data_triples = []
            materialize_inserts = []
            materialize_deletes = []
            for pred_iri, old_val in detail.before_values.items():
                if old_val == "(unknown)":
                    continue
                old_literal = Literal(old_val)
                data_triples.append((URIRef(subject_iri), URIRef(pred_iri), old_literal))
                materialize_inserts.append((URIRef(subject_iri), URIRef(pred_iri), old_literal))
            for pred_iri, new_val in detail.new_values.items():
                materialize_deletes.append(
                    (URIRef(subject_iri), URIRef(pred_iri), Literal(new_val))
                )
            if not data_triples:
                return None
            return Operation(
                operation_type="edge.patch",
                affected_iris=detail.summary.affected_iris,
                description=f"Undo edge.patch: {event_iri}",
                data_triples=data_triples,
                materialize_inserts=materialize_inserts,
                materialize_deletes=materialize_deletes,
            )

        elif "object.create" in op_type:
            # Undo object creation by removing all triples from materialized state
            if not subject_iri or not detail.data_triples:
                return None
            materialize_deletes = []
            for s_str, p_str, o_str in detail.data_triples:
                try:
                    s = URIRef(s_str)
                    p = URIRef(p_str)
                    if o_str.startswith("http") or o_str.startswith("urn"):
                        o = URIRef(o_str)
                    else:
                        o = Literal(o_str)
                    materialize_deletes.append((s, p, o))
                except Exception:
                    pass
            if not materialize_deletes:
                return None
            return Operation(
                operation_type="object.create.undo",
                affected_iris=detail.summary.affected_iris,
                description=f"Undo object.create: {event_iri}",
                data_triples=[],
                materialize_inserts=[],
                materialize_deletes=materialize_deletes,
            )

        return None  # Not reversible

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_group_concat_rows(self, rows: list[dict]) -> list[EventSummary]:
        """Parse SPARQL bindings from the GROUP_CONCAT query."""
        events: list[EventSummary] = []
        for row in rows:
            event_iri = row["event"]["value"]
            timestamp = row["timestamp"]["value"]
            op_type = row["opType"]["value"]
            affected_raw = row.get("affected", {}).get("value", "")
            affected_iris = [iri for iri in affected_raw.split(",") if iri.strip()]
            performed_by = row.get("performedBy", {}).get("value") if "performedBy" in row else None
            description = row.get("description", {}).get("value") if "description" in row else None

            events.append(EventSummary(
                event_iri=event_iri,
                timestamp=timestamp,
                operation_type=op_type,
                affected_iris=affected_iris,
                performed_by=performed_by,
                description=description,
            ))
        return events

    async def _list_events_fallback(
        self,
        filter_block: str,
    ) -> list[EventSummary]:
        """Fallback: plain SELECT (no GROUP_CONCAT) + Python-side grouping.

        Used when GROUP_CONCAT is not supported by the triplestore.
        Groups rows by event IRI, collecting all affectedIRI values.
        """
        plain_sparql = f"""PREFIX sempkm: <urn:sempkm:>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?event ?timestamp ?opType ?affectedIRI ?performedBy ?description
WHERE {{
  GRAPH ?event {{
    ?event a sempkm:Event ;
           sempkm:timestamp ?timestamp ;
           sempkm:operationType ?opType ;
           sempkm:affectedIRI ?affectedIRI .
    OPTIONAL {{ ?event sempkm:performedBy ?performedBy }}
    OPTIONAL {{ ?event sempkm:description ?description }}
  }}
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
  {filter_block}
}}
ORDER BY DESC(?timestamp)
LIMIT 255
"""
        result = await self._client.query(plain_sparql)
        rows = result.get("results", {}).get("bindings", [])

        # Group by event IRI, preserving DESC(?timestamp) order
        grouped: OrderedDict[str, EventSummary] = OrderedDict()
        for row in rows:
            event_iri = row["event"]["value"]
            if event_iri not in grouped:
                grouped[event_iri] = EventSummary(
                    event_iri=event_iri,
                    timestamp=row["timestamp"]["value"],
                    operation_type=row["opType"]["value"],
                    affected_iris=[],
                    performed_by=row.get("performedBy", {}).get("value") if "performedBy" in row else None,
                    description=row.get("description", {}).get("value") if "description" in row else None,
                )
            iri = row.get("affectedIRI", {}).get("value", "")
            if iri and iri not in grouped[event_iri].affected_iris:
                grouped[event_iri].affected_iris.append(iri)

        return list(grouped.values())
