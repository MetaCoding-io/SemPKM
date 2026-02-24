"""Event query service for browsing the immutable event log.

Provides cursor-paginated SPARQL queries over event named graphs
(urn:sempkm:event:*). Supports filtering by operation type, user,
affected object, and date range.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field

from app.triplestore.client import TriplestoreClient


@dataclass
class EventSummary:
    """Summary of one event for the timeline list view."""

    event_iri: str
    timestamp: str           # ISO datetime string from SPARQL
    operation_type: str
    affected_iris: list[str] = field(default_factory=list)  # CSV-split from GROUP_CONCAT result
    performed_by: str | None = None   # user IRI, None if absent
    description: str | None = None


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
