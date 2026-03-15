"""Operations log service using PROV-O vocabulary.

Records system activities (model installs, inference runs, validation runs)
as prov:Activity instances in the urn:sempkm:ops-log named graph. All data
is stored as raw SPARQL — follows the QueryService pattern exactly.

Resource IRI pattern: urn:sempkm:ops-log:{uuid}
"""

import logging
import uuid
from datetime import datetime, timezone

from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Named graph for all operations log data
OPS_LOG_GRAPH = "urn:sempkm:ops-log"

# ---- Vocabulary IRIs (raw strings, not rdflib objects) ----

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"

# PROV-O Starting Point terms
PROV_ACTIVITY = "http://www.w3.org/ns/prov#Activity"
PROV_STARTED_AT_TIME = "http://www.w3.org/ns/prov#startedAtTime"
PROV_ENDED_AT_TIME = "http://www.w3.org/ns/prov#endedAtTime"
PROV_WAS_ASSOCIATED_WITH = "http://www.w3.org/ns/prov#wasAssociatedWith"
PROV_USED = "http://www.w3.org/ns/prov#used"

# SemPKM extension predicates
SEMPKM_ACTIVITY_TYPE = "urn:sempkm:activityType"
SEMPKM_STATUS = "urn:sempkm:status"
SEMPKM_ERROR_MESSAGE = "urn:sempkm:errorMessage"

# Default system actor
SYSTEM_ACTOR_IRI = "urn:sempkm:system"

# Pagination default
DEFAULT_PAGE_SIZE = 50


def _esc(value: str) -> str:
    """Escape a string for safe SPARQL literal inclusion."""
    return (
        value
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _activity_iri(activity_id: uuid.UUID | str | None = None) -> str:
    """Build an activity IRI from a UUID."""
    return f"urn:sempkm:ops-log:{activity_id or uuid.uuid4()}"


def _dt(val: str) -> str:
    """Build an xsd:dateTime typed literal."""
    return f"'{val}'^^<{XSD_DATETIME}>"


def _lit(val: str) -> str:
    """Build a SPARQL string literal (single-quoted, escaped)."""
    return f"'{_esc(val)}'"


class OperationsLogService:
    """RDF-backed operations log using PROV-O vocabulary.

    All entries are prov:Activity instances stored in the urn:sempkm:ops-log
    named graph. Fire-and-forget logging — callers should wrap in try/except
    so failures never block the primary operation.
    """

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def log_activity(
        self,
        activity_type: str,
        label: str,
        started_at: str | None = None,
        ended_at: str | None = None,
        actor: str | None = None,
        used_iris: list[str] | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ) -> str:
        """Log a system activity as a prov:Activity.

        Args:
            activity_type: Short identifier like 'model.install', 'inference.run'
            label: Human-readable description of the activity
            started_at: ISO 8601 start time (defaults to now)
            ended_at: ISO 8601 end time (defaults to now)
            actor: IRI of the agent performing the activity (defaults to system)
            used_iris: List of resource IRIs that the activity used
            status: 'success' or 'failed' (omitted if None)
            error_message: Error description for failed activities

        Returns:
            The activity IRI string.
        """
        activity_id = uuid.uuid4()
        iri = _activity_iri(activity_id)
        now = _now_iso()
        actor_iri = actor or SYSTEM_ACTOR_IRI

        triples = [
            f"<{iri}> a <{PROV_ACTIVITY}> .",
            f"<{iri}> <{SEMPKM_ACTIVITY_TYPE}> {_lit(activity_type)} .",
            f"<{iri}> <{RDFS_LABEL}> {_lit(label)} .",
            f"<{iri}> <{PROV_STARTED_AT_TIME}> {_dt(started_at or now)} .",
            f"<{iri}> <{PROV_ENDED_AT_TIME}> {_dt(ended_at or now)} .",
            f"<{iri}> <{PROV_WAS_ASSOCIATED_WITH}> <{actor_iri}> .",
        ]

        if used_iris:
            for used_iri in used_iris:
                triples.append(f"<{iri}> <{PROV_USED}> <{used_iri}> .")

        if status:
            triples.append(f"<{iri}> <{SEMPKM_STATUS}> {_lit(status)} .")

        if error_message:
            triples.append(
                f"<{iri}> <{SEMPKM_ERROR_MESSAGE}> {_lit(error_message)} ."
            )

        body = "\n    ".join(triples)
        sparql = (
            f"INSERT DATA {{\n"
            f"  GRAPH <{OPS_LOG_GRAPH}> {{\n"
            f"    {body}\n"
            f"  }}\n"
            f"}}"
        )
        await self._client.update(sparql)
        logger.info("Logged ops activity: %s", activity_type)
        return iri

    async def list_activities(
        self,
        activity_type: str | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[dict], str | None]:
        """List activities in reverse chronological order with cursor pagination.

        Args:
            activity_type: Optional filter by sempkm:activityType value
            cursor: ISO timestamp cursor — return activities started before this
            limit: Page size (default 50)

        Returns:
            (list_of_activity_dicts, next_cursor_or_None)
        """
        filters: list[str] = []

        if cursor:
            filters.append(
                f'FILTER(?startedAt < "{cursor}"^^<{XSD_DATETIME}>)'
            )

        if activity_type:
            filters.append(f"FILTER(STR(?activityType) = {_lit(activity_type)})")

        filter_block = "\n    ".join(filters)

        # Fetch limit+1 to detect next page
        fetch_limit = limit + 1

        sparql = (
            f"SELECT ?activity ?label ?activityType ?startedAt ?endedAt"
            f" ?actor ?status ?errorMessage\n"
            f"WHERE {{\n"
            f"  GRAPH <{OPS_LOG_GRAPH}> {{\n"
            f"    ?activity a <{PROV_ACTIVITY}> .\n"
            f"    ?activity <{RDFS_LABEL}> ?label .\n"
            f"    ?activity <{SEMPKM_ACTIVITY_TYPE}> ?activityType .\n"
            f"    ?activity <{PROV_STARTED_AT_TIME}> ?startedAt .\n"
            f"    ?activity <{PROV_ENDED_AT_TIME}> ?endedAt .\n"
            f"    ?activity <{PROV_WAS_ASSOCIATED_WITH}> ?actor .\n"
            f"    OPTIONAL {{ ?activity <{SEMPKM_STATUS}> ?status }}\n"
            f"    OPTIONAL {{ ?activity <{SEMPKM_ERROR_MESSAGE}> ?errorMessage }}\n"
            f"    {filter_block}\n"
            f"  }}\n"
            f"}}\n"
            f"ORDER BY DESC(?startedAt)\n"
            f"LIMIT {fetch_limit}"
        )

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        activities = []
        for b in bindings[:limit]:
            activities.append(self._binding_to_dict(b))

        # If we got more than limit, there's a next page
        next_cursor: str | None = None
        if len(bindings) > limit:
            # Cursor is the startedAt of the last returned item
            next_cursor = activities[-1]["started_at"] if activities else None

        return activities, next_cursor

    async def get_activity(self, activity_iri: str) -> dict | None:
        """Get a single activity by its IRI.

        Returns a dict with activity details, or None if not found.
        """
        sparql = (
            f"SELECT ?label ?activityType ?startedAt ?endedAt"
            f" ?actor ?status ?errorMessage ?used\n"
            f"WHERE {{\n"
            f"  GRAPH <{OPS_LOG_GRAPH}> {{\n"
            f"    <{activity_iri}> a <{PROV_ACTIVITY}> .\n"
            f"    <{activity_iri}> <{RDFS_LABEL}> ?label .\n"
            f"    <{activity_iri}> <{SEMPKM_ACTIVITY_TYPE}> ?activityType .\n"
            f"    <{activity_iri}> <{PROV_STARTED_AT_TIME}> ?startedAt .\n"
            f"    <{activity_iri}> <{PROV_ENDED_AT_TIME}> ?endedAt .\n"
            f"    <{activity_iri}> <{PROV_WAS_ASSOCIATED_WITH}> ?actor .\n"
            f"    OPTIONAL {{ <{activity_iri}> <{SEMPKM_STATUS}> ?status }}\n"
            f"    OPTIONAL {{ <{activity_iri}> <{SEMPKM_ERROR_MESSAGE}> ?errorMessage }}\n"
            f"    OPTIONAL {{ <{activity_iri}> <{PROV_USED}> ?used }}\n"
            f"  }}\n"
            f"}}"
        )

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        # First binding has scalar fields; collect prov:used from all rows
        first = bindings[0]
        activity = self._binding_to_dict(first, include_iri=False)
        activity["iri"] = activity_iri

        used_iris: list[str] = []
        for b in bindings:
            used_val = b.get("used", {}).get("value")
            if used_val and used_val not in used_iris:
                used_iris.append(used_val)
        activity["used"] = used_iris

        return activity

    async def count_activities(
        self, activity_type: str | None = None
    ) -> int:
        """Count activities, optionally filtered by type.

        Returns the total count as an integer.
        """
        type_filter = ""
        if activity_type:
            type_filter = (
                f"?activity <{SEMPKM_ACTIVITY_TYPE}> ?activityType .\n"
                f"    FILTER(STR(?activityType) = {_lit(activity_type)})\n"
                f"    "
            )

        sparql = (
            f"SELECT (COUNT(?activity) AS ?total)\n"
            f"WHERE {{\n"
            f"  GRAPH <{OPS_LOG_GRAPH}> {{\n"
            f"    ?activity a <{PROV_ACTIVITY}> .\n"
            f"    {type_filter}"
            f"}}\n"
            f"}}"
        )

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return 0
        return int(bindings[0]["total"]["value"])

    # ---- Private helpers ----

    @staticmethod
    def _binding_to_dict(
        b: dict, include_iri: bool = True
    ) -> dict:
        """Convert a SPARQL JSON binding row to a flat dict."""
        d: dict = {}
        if include_iri:
            d["iri"] = b.get("activity", {}).get("value", "")
        d["label"] = b["label"]["value"]
        d["activity_type"] = b["activityType"]["value"]
        d["started_at"] = b["startedAt"]["value"]
        d["ended_at"] = b["endedAt"]["value"]
        d["actor"] = b["actor"]["value"]
        d["status"] = b.get("status", {}).get("value")
        d["error_message"] = b.get("errorMessage", {}).get("value")
        return d
