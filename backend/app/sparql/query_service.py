"""RDF-backed service for saved SPARQL queries, history, sharing, and promoted views.

All data stored in the triplestore under urn:sempkm:queries named graph.
Replaces the previous SQLAlchemy-backed models (SavedSparqlQuery,
SharedQueryAccess, PromotedQueryView, SparqlQueryHistory).

Resource IRI patterns:
  - Saved queries:   urn:sempkm:query:{uuid}
  - Query history:   urn:sempkm:query-exec:{uuid}
  - Promoted views:  urn:sempkm:query-view:{uuid}
  - Model queries:   urn:sempkm:model:{modelId}:query:{slug}
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Named graph for all query data
QUERIES_GRAPH = "urn:sempkm:queries"

# Vocabulary IRIs
VOCAB = "urn:sempkm:vocab:"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
DCTERMS_DESCRIPTION = "http://purl.org/dc/terms/description"
DCTERMS_CREATED = "http://purl.org/dc/terms/created"
DCTERMS_MODIFIED = "http://purl.org/dc/terms/modified"
PROV_STARTED = "http://www.w3.org/ns/prov#startedAtTime"
XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"

TYPE_SAVED_QUERY = VOCAB + "SavedQuery"
TYPE_QUERY_EXEC = VOCAB + "QueryExecution"
TYPE_PROMOTED_VIEW = VOCAB + "PromotedView"

PRED_OWNER = VOCAB + "owner"
PRED_QUERY_TEXT = VOCAB + "queryText"
PRED_SHARED_WITH = VOCAB + "sharedWith"
PRED_FROM_QUERY = VOCAB + "fromQuery"
PRED_RENDERER_TYPE = VOCAB + "rendererType"
PRED_EXECUTED_BY = "http://www.w3.org/ns/prov#wasAssociatedWith"  # was VOCAB + "executedBy"
PRED_SOURCE = VOCAB + "source"

MAX_HISTORY_ENTRIES = 100
VALID_RENDERERS = {"table", "card", "graph"}


def _user_iri(user_id: uuid.UUID) -> str:
    return f"urn:sempkm:user:{user_id}"


def _query_iri(query_id: uuid.UUID | str) -> str:
    return f"urn:sempkm:query:{query_id}"


def _exec_iri() -> str:
    return f"urn:sempkm:query-exec:{uuid.uuid4()}"


def _view_iri(view_id: uuid.UUID | str | None = None) -> str:
    return f"urn:sempkm:query-view:{view_id or uuid.uuid4()}"


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
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dt(val: str) -> str:
    """Build an xsd:dateTime typed literal."""
    return f"'{val}'^^<{XSD_DATETIME}>"


def _lit(val: str) -> str:
    """Build a SPARQL string literal (single-quoted, escaped)."""
    return f"'{_esc(val)}'"


def _graph(body: str) -> str:
    """Wrap triples in a GRAPH clause."""
    return f"GRAPH <{QUERIES_GRAPH}> {{\n{body}\n}}"


@dataclass
class SavedQueryData:
    id: str
    name: str
    description: str | None
    query_text: str
    created_at: str
    updated_at: str
    owner_id: str | None = None
    source: str | None = None
    readonly: bool = False


@dataclass
class SharedQueryData:
    id: str
    name: str
    description: str | None
    query_text: str
    created_at: str
    updated_at: str
    owner_name: str
    is_updated: bool


@dataclass
class QueryHistoryData:
    id: str
    query_text: str
    executed_at: str


@dataclass
class PromotedViewData:
    id: str
    query_id: str
    display_label: str
    renderer_type: str
    query_text: str = ""


class QueryService:
    """RDF-backed service for SPARQL query management."""

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    # ---------- Saved queries CRUD ----------

    async def save_query(
        self,
        user_id: uuid.UUID,
        name: str,
        query_text: str,
        description: str | None = None,
        query_id: uuid.UUID | None = None,
    ) -> SavedQueryData:
        qid = query_id or uuid.uuid4()
        iri = _query_iri(qid)
        user = _user_iri(user_id)
        now = _now_iso()

        triples = [
            f"<{iri}> a <{TYPE_SAVED_QUERY}> .",
            f"<{iri}> <{PRED_OWNER}> <{user}> .",
            f"<{iri}> <{RDFS_LABEL}> {_lit(name)} .",
            f"<{iri}> <{PRED_QUERY_TEXT}> {_lit(query_text)} .",
            f"<{iri}> <{DCTERMS_CREATED}> {_dt(now)} .",
            f"<{iri}> <{DCTERMS_MODIFIED}> {_dt(now)} .",
        ]
        if description:
            triples.append(f"<{iri}> <{DCTERMS_DESCRIPTION}> {_lit(description)} .")

        body = "\n  ".join(triples)
        sparql = f"INSERT DATA {{\n  {_graph(body)}\n}}"
        await self._client.update(sparql)
        logger.info("Saved query %s for user %s", iri, user_id)

        return SavedQueryData(
            id=str(qid), name=name, description=description,
            query_text=query_text, created_at=now, updated_at=now,
            owner_id=str(user_id),
        )

    async def get_query(
        self, query_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> SavedQueryData | None:
        iri = _query_iri(query_id)
        owner_filter = ""
        if user_id:
            owner_filter = f"  <{iri}> <{PRED_OWNER}> <{_user_iri(user_id)}> .\n"

        sparql = (
            "SELECT ?name ?desc ?text ?created ?modified ?owner ?source WHERE {\n"
            f"  {_graph(f'<{iri}> a <{TYPE_SAVED_QUERY}> .' + chr(10) + owner_filter + chr(10).join([
                f'  <{iri}> <{RDFS_LABEL}> ?name .',
                f'  <{iri}> <{PRED_QUERY_TEXT}> ?text .',
                f'  OPTIONAL {{ <{iri}> <{DCTERMS_DESCRIPTION}> ?desc }}',
                f'  OPTIONAL {{ <{iri}> <{DCTERMS_CREATED}> ?created }}',
                f'  OPTIONAL {{ <{iri}> <{DCTERMS_MODIFIED}> ?modified }}',
                f'  OPTIONAL {{ <{iri}> <{PRED_OWNER}> ?owner }}',
                f'  OPTIONAL {{ <{iri}> <{PRED_SOURCE}> ?source }}',
            ]))}\n"
            "}"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        b = bindings[0]
        source = b.get("source", {}).get("value")
        return SavedQueryData(
            id=str(query_id),
            name=b["name"]["value"],
            description=b.get("desc", {}).get("value"),
            query_text=b["text"]["value"],
            created_at=b.get("created", {}).get("value", ""),
            updated_at=b.get("modified", {}).get("value", ""),
            owner_id=_extract_user_uuid(b.get("owner", {}).get("value", "")),
            source=source,
            readonly=source is not None,
        )

    async def list_user_queries(self, user_id: uuid.UUID) -> list[SavedQueryData]:
        user = _user_iri(user_id)
        sparql = (
            "SELECT ?query ?name ?desc ?text ?created ?modified WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?query a <{TYPE_SAVED_QUERY}> .\n"
            f"    ?query <{PRED_OWNER}> <{user}> .\n"
            f"    ?query <{RDFS_LABEL}> ?name .\n"
            f"    ?query <{PRED_QUERY_TEXT}> ?text .\n"
            f"    OPTIONAL {{ ?query <{DCTERMS_DESCRIPTION}> ?desc }}\n"
            f"    OPTIONAL {{ ?query <{DCTERMS_CREATED}> ?created }}\n"
            f"    OPTIONAL {{ ?query <{DCTERMS_MODIFIED}> ?modified }}\n"
            f"    FILTER NOT EXISTS {{ ?query <{PRED_SOURCE}> ?src }}\n"
            "  }\n"
            "}\n"
            "ORDER BY DESC(?created)"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [
            SavedQueryData(
                id=_extract_query_uuid(b["query"]["value"]),
                name=b["name"]["value"],
                description=b.get("desc", {}).get("value"),
                query_text=b["text"]["value"],
                created_at=b.get("created", {}).get("value", ""),
                updated_at=b.get("modified", {}).get("value", ""),
                owner_id=str(user_id),
            )
            for b in bindings
        ]

    async def update_query(
        self,
        query_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        query_text: str | None = None,
    ) -> SavedQueryData | None:
        current = await self.get_query(query_id, user_id)
        if current is None or current.readonly:
            return None

        iri = _query_iri(query_id)
        now = _now_iso()

        # Build per-field DELETE WHERE + INSERT DATA
        # Simplest approach: delete all mutable triples and reinsert
        new_name = name if name is not None else current.name
        new_desc = description if description is not None else current.description
        new_text = query_text if query_text is not None else current.query_text

        # Delete old mutable values
        del_sparql = (
            "DELETE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    <{iri}> <{RDFS_LABEL}> ?n .\n"
            f"    <{iri}> <{DCTERMS_DESCRIPTION}> ?d .\n"
            f"    <{iri}> <{PRED_QUERY_TEXT}> ?t .\n"
            f"    <{iri}> <{DCTERMS_MODIFIED}> ?m .\n"
            "  }\n"
            "} WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    OPTIONAL {{ <{iri}> <{RDFS_LABEL}> ?n }}\n"
            f"    OPTIONAL {{ <{iri}> <{DCTERMS_DESCRIPTION}> ?d }}\n"
            f"    OPTIONAL {{ <{iri}> <{PRED_QUERY_TEXT}> ?t }}\n"
            f"    OPTIONAL {{ <{iri}> <{DCTERMS_MODIFIED}> ?m }}\n"
            "  }\n"
            "}"
        )
        await self._client.update(del_sparql)

        # Insert new values
        ins_triples = [
            f"<{iri}> <{RDFS_LABEL}> {_lit(new_name)} .",
            f"<{iri}> <{PRED_QUERY_TEXT}> {_lit(new_text)} .",
            f"<{iri}> <{DCTERMS_MODIFIED}> {_dt(now)} .",
        ]
        if new_desc:
            ins_triples.append(f"<{iri}> <{DCTERMS_DESCRIPTION}> {_lit(new_desc)} .")

        body = "\n    ".join(ins_triples)
        ins_sparql = f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {body}\n  }}\n}}"
        await self._client.update(ins_sparql)

        return await self.get_query(query_id, user_id)

    async def delete_query(self, query_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        current = await self.get_query(query_id, user_id)
        if current is None or current.readonly:
            return False

        iri = _query_iri(query_id)
        # Delete query + any promoted views referencing it
        sparql = (
            "DELETE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    <{iri}> ?p ?o .\n"
            "    ?view ?vp ?vo .\n"
            "  }\n"
            "} WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    <{iri}> ?p ?o .\n"
            f"    OPTIONAL {{\n"
            f"      ?view a <{TYPE_PROMOTED_VIEW}> .\n"
            f"      ?view <{PRED_FROM_QUERY}> <{iri}> .\n"
            "      ?view ?vp ?vo .\n"
            "    }\n"
            "  }\n"
            "}"
        )
        await self._client.update(sparql)
        logger.info("Deleted query %s for user %s", iri, user_id)
        return True

    # ---------- Sharing ----------

    async def get_shares(self, query_id: uuid.UUID, user_id: uuid.UUID) -> list[str]:
        current = await self.get_query(query_id, user_id)
        if current is None:
            raise ValueError("Query not found")

        iri = _query_iri(query_id)
        sparql = (
            "SELECT ?shared WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    <{iri}> <{PRED_SHARED_WITH}> ?shared .\n"
            "  }\n"
            "}"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [_extract_user_uuid(b["shared"]["value"]) for b in bindings]

    async def update_shares(
        self, query_id: uuid.UUID, user_id: uuid.UUID, target_user_ids: list[uuid.UUID]
    ) -> None:
        current = await self.get_query(query_id, user_id)
        if current is None:
            raise ValueError("Query not found")

        iri = _query_iri(query_id)
        targets = [uid for uid in target_user_ids if uid != user_id]

        # Delete all existing shares
        del_sparql = (
            "DELETE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{ <{iri}> <{PRED_SHARED_WITH}> ?u . }}\n"
            "} WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{ <{iri}> <{PRED_SHARED_WITH}> ?u . }}\n"
            "}"
        )
        await self._client.update(del_sparql)

        if targets:
            share_triples = "\n    ".join(
                f"<{iri}> <{PRED_SHARED_WITH}> <{_user_iri(uid)}> ."
                for uid in targets
            )
            ins_sparql = f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {share_triples}\n  }}\n}}"
            await self._client.update(ins_sparql)

    async def list_shared_with_me(
        self, user_id: uuid.UUID, user_display_names: dict[str, str] | None = None
    ) -> list[SharedQueryData]:
        user = _user_iri(user_id)
        sparql = (
            "SELECT ?query ?name ?desc ?text ?created ?modified ?owner WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?query a <{TYPE_SAVED_QUERY}> .\n"
            f"    ?query <{PRED_SHARED_WITH}> <{user}> .\n"
            f"    ?query <{RDFS_LABEL}> ?name .\n"
            f"    ?query <{PRED_QUERY_TEXT}> ?text .\n"
            f"    ?query <{PRED_OWNER}> ?owner .\n"
            f"    OPTIONAL {{ ?query <{DCTERMS_DESCRIPTION}> ?desc }}\n"
            f"    OPTIONAL {{ ?query <{DCTERMS_CREATED}> ?created }}\n"
            f"    OPTIONAL {{ ?query <{DCTERMS_MODIFIED}> ?modified }}\n"
            "  }\n"
            "}\n"
            "ORDER BY DESC(?modified)"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        names = user_display_names or {}
        queries = []
        for b in bindings:
            owner_uuid = _extract_user_uuid(b.get("owner", {}).get("value", ""))
            queries.append(SharedQueryData(
                id=_extract_query_uuid(b["query"]["value"]),
                name=b["name"]["value"],
                description=b.get("desc", {}).get("value"),
                query_text=b["text"]["value"],
                created_at=b.get("created", {}).get("value", ""),
                updated_at=b.get("modified", {}).get("value", ""),
                owner_name=names.get(owner_uuid, owner_uuid or "Unknown"),
                is_updated=True,  # simplified — always mark as updated for shared
            ))
        return queries

    async def mark_viewed(self, query_id: uuid.UUID, user_id: uuid.UUID) -> None:
        # No-op for now — the is_updated logic was fragile in SQL too.
        # Will revisit with proper RDF reification if needed.
        pass

    async def fork_query(
        self, query_id: uuid.UUID, user_id: uuid.UUID
    ) -> SavedQueryData | None:
        source = await self.get_query(query_id)
        if source is None:
            return None
        return await self.save_query(
            user_id=user_id,
            name=f"Copy of {source.name}",
            query_text=source.query_text,
            description=source.description,
        )

    # ---------- Query history ----------

    async def save_history(self, user_id: uuid.UUID, query_text: str) -> None:
        stripped = query_text.strip()
        user = _user_iri(user_id)

        # Check most recent for dedup
        recent_sparql = (
            "SELECT ?exec ?text ?time WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?exec a <{TYPE_QUERY_EXEC}> .\n"
            f"    ?exec <{PRED_EXECUTED_BY}> <{user}> .\n"
            f"    ?exec <{PRED_QUERY_TEXT}> ?text .\n"
            f"    ?exec <{PROV_STARTED}> ?time .\n"
            "  }\n"
            "}\n"
            "ORDER BY DESC(?time)\n"
            "LIMIT 1"
        )
        result = await self._client.query(recent_sparql)
        bindings = result.get("results", {}).get("bindings", [])

        if bindings and bindings[0]["text"]["value"].strip() == stripped:
            # Update timestamp on existing
            exec_iri = bindings[0]["exec"]["value"]
            old_time = bindings[0]["time"]["value"]
            now = _now_iso()
            upd = (
                "DELETE {\n"
                f"  GRAPH <{QUERIES_GRAPH}> {{ <{exec_iri}> <{PROV_STARTED}> {_dt(old_time)} . }}\n"
                "} INSERT {\n"
                f"  GRAPH <{QUERIES_GRAPH}> {{ <{exec_iri}> <{PROV_STARTED}> {_dt(now)} . }}\n"
                "} WHERE {\n"
                f"  GRAPH <{QUERIES_GRAPH}> {{ <{exec_iri}> <{PROV_STARTED}> {_dt(old_time)} . }}\n"
                "}"
            )
            await self._client.update(upd)
            return

        # Insert new entry
        exec_iri = _exec_iri()
        now = _now_iso()
        triples = "\n    ".join([
            f"<{exec_iri}> a <{TYPE_QUERY_EXEC}> .",
            f"<{exec_iri}> <{PRED_EXECUTED_BY}> <{user}> .",
            f"<{exec_iri}> <{PRED_QUERY_TEXT}> {_lit(stripped)} .",
            f"<{exec_iri}> <{PROV_STARTED}> {_dt(now)} .",
        ])
        ins = f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {triples}\n  }}\n}}"
        await self._client.update(ins)
        await self._prune_history(user_id)

    async def get_history(self, user_id: uuid.UUID, limit: int = 100) -> list[QueryHistoryData]:
        user = _user_iri(user_id)
        sparql = (
            "SELECT ?exec ?text ?time WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?exec a <{TYPE_QUERY_EXEC}> .\n"
            f"    ?exec <{PRED_EXECUTED_BY}> <{user}> .\n"
            f"    ?exec <{PRED_QUERY_TEXT}> ?text .\n"
            f"    ?exec <{PROV_STARTED}> ?time .\n"
            "  }\n"
            "}\n"
            f"ORDER BY DESC(?time)\nLIMIT {limit}"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [
            QueryHistoryData(
                id=_extract_exec_uuid(b["exec"]["value"]),
                query_text=b["text"]["value"],
                executed_at=b["time"]["value"],
            )
            for b in bindings
        ]

    async def clear_history(self, user_id: uuid.UUID) -> None:
        user = _user_iri(user_id)
        sparql = (
            "DELETE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{ ?exec ?p ?o . }}\n"
            "} WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?exec a <{TYPE_QUERY_EXEC}> .\n"
            f"    ?exec <{PRED_EXECUTED_BY}> <{user}> .\n"
            "    ?exec ?p ?o .\n"
            "  }\n"
            "}"
        )
        await self._client.update(sparql)

    async def _prune_history(self, user_id: uuid.UUID) -> None:
        user = _user_iri(user_id)
        count_sparql = (
            "SELECT (COUNT(?exec) AS ?total) WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?exec a <{TYPE_QUERY_EXEC}> .\n"
            f"    ?exec <{PRED_EXECUTED_BY}> <{user}> .\n"
            "  }\n"
            "}"
        )
        result = await self._client.query(count_sparql)
        total = int(result["results"]["bindings"][0]["total"]["value"])
        if total <= MAX_HISTORY_ENTRIES:
            return

        cutoff_sparql = (
            "SELECT ?time WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?exec a <{TYPE_QUERY_EXEC}> .\n"
            f"    ?exec <{PRED_EXECUTED_BY}> <{user}> .\n"
            f"    ?exec <{PROV_STARTED}> ?time .\n"
            "  }\n"
            "}\n"
            f"ORDER BY DESC(?time)\nOFFSET {MAX_HISTORY_ENTRIES}\nLIMIT 1"
        )
        cutoff_result = await self._client.query(cutoff_sparql)
        cutoff_bindings = cutoff_result.get("results", {}).get("bindings", [])
        if not cutoff_bindings:
            return

        cutoff_time = cutoff_bindings[0]["time"]["value"]
        del_sparql = (
            "DELETE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{ ?exec ?p ?o . }}\n"
            "} WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?exec a <{TYPE_QUERY_EXEC}> .\n"
            f"    ?exec <{PRED_EXECUTED_BY}> <{user}> .\n"
            f"    ?exec <{PROV_STARTED}> ?time .\n"
            f"    FILTER(?time <= {_dt(cutoff_time)})\n"
            "    ?exec ?p ?o .\n"
            "  }\n"
            "}"
        )
        await self._client.update(del_sparql)
        logger.info("Pruned query history for user %s (was %d, cap %d)",
                     user_id, total, MAX_HISTORY_ENTRIES)

    # ---------- Promotion ----------

    async def promote_query(
        self,
        query_id: uuid.UUID,
        user_id: uuid.UUID,
        display_label: str,
        renderer_type: str = "table",
    ) -> PromotedViewData:
        if renderer_type not in VALID_RENDERERS:
            raise ValueError(
                f"renderer_type must be one of: {', '.join(sorted(VALID_RENDERERS))}"
            )

        current = await self.get_query(query_id, user_id)
        if current is None:
            raise ValueError("Query not found")

        existing = await self.get_promotion_status(query_id, user_id)
        if existing is not None:
            raise ValueError("Query is already promoted")

        iri = _query_iri(query_id)
        view_id = uuid.uuid4()
        view = _view_iri(view_id)
        user = _user_iri(user_id)
        now = _now_iso()

        triples = "\n    ".join([
            f"<{view}> a <{TYPE_PROMOTED_VIEW}> .",
            f"<{view}> <{PRED_FROM_QUERY}> <{iri}> .",
            f"<{view}> <{PRED_OWNER}> <{user}> .",
            f"<{view}> <{RDFS_LABEL}> {_lit(display_label)} .",
            f"<{view}> <{PRED_RENDERER_TYPE}> '{_esc(renderer_type)}' .",
            f"<{view}> <{DCTERMS_CREATED}> {_dt(now)} .",
        ])
        sparql = f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {triples}\n  }}\n}}"
        await self._client.update(sparql)
        logger.info("Promoted query %s as view %s", iri, view)

        return PromotedViewData(
            id=str(view_id), query_id=str(query_id),
            display_label=display_label, renderer_type=renderer_type,
            query_text=current.query_text,
        )

    async def demote_query(self, query_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        current = await self.get_query(query_id, user_id)
        if current is None:
            return False

        iri = _query_iri(query_id)
        sparql = (
            "DELETE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{ ?view ?p ?o . }}\n"
            "} WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?view a <{TYPE_PROMOTED_VIEW}> .\n"
            f"    ?view <{PRED_FROM_QUERY}> <{iri}> .\n"
            "    ?view ?p ?o .\n"
            "  }\n"
            "}"
        )
        await self._client.update(sparql)
        return True

    async def get_promotion_status(
        self, query_id: uuid.UUID, user_id: uuid.UUID
    ) -> PromotedViewData | None:
        iri = _query_iri(query_id)
        sparql = (
            "SELECT ?view ?label ?renderer WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?view a <{TYPE_PROMOTED_VIEW}> .\n"
            f"    ?view <{PRED_FROM_QUERY}> <{iri}> .\n"
            f"    ?view <{RDFS_LABEL}> ?label .\n"
            f"    ?view <{PRED_RENDERER_TYPE}> ?renderer .\n"
            "  }\n"
            "}"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        b = bindings[0]
        return PromotedViewData(
            id=_extract_view_uuid(b["view"]["value"]),
            query_id=str(query_id),
            display_label=b["label"]["value"],
            renderer_type=b["renderer"]["value"],
        )

    async def list_promoted_views(self, user_id: uuid.UUID) -> list[PromotedViewData]:
        user = _user_iri(user_id)
        sparql = (
            "SELECT ?view ?query ?label ?renderer ?text WHERE {\n"
            f"  GRAPH <{QUERIES_GRAPH}> {{\n"
            f"    ?view a <{TYPE_PROMOTED_VIEW}> .\n"
            f"    ?view <{PRED_OWNER}> <{user}> .\n"
            f"    ?view <{PRED_FROM_QUERY}> ?query .\n"
            f"    ?view <{RDFS_LABEL}> ?label .\n"
            f"    ?view <{PRED_RENDERER_TYPE}> ?renderer .\n"
            f"    ?query <{PRED_QUERY_TEXT}> ?text .\n"
            "  }\n"
            "}"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [
            PromotedViewData(
                id=_extract_view_uuid(b["view"]["value"]),
                query_id=_extract_query_uuid(b["query"]["value"]),
                display_label=b["label"]["value"],
                renderer_type=b["renderer"]["value"],
                query_text=b["text"]["value"],
            )
            for b in bindings
        ]

    # ---------- Model queries ----------

    async def list_model_queries(self) -> list[SavedQueryData]:
        """List named queries from installed Mental Model views graphs."""
        model_sparql = (
            "SELECT ?modelId WHERE {\n"
            "  GRAPH <urn:sempkm:models> {\n"
            "    ?model a <urn:sempkm:MentalModel> .\n"
            "    ?model <urn:sempkm:modelId> ?modelId .\n"
            "  }\n"
            "}"
        )
        model_result = await self._client.query(model_sparql)
        model_bindings = model_result.get("results", {}).get("bindings", [])
        if not model_bindings:
            return []

        from_clauses = " ".join(
            f"FROM <urn:sempkm:model:{b['modelId']['value']}:views>"
            for b in model_bindings
        )
        sparql = (
            f"SELECT ?query ?name ?desc ?text ?source\n{from_clauses}\n"
            "WHERE {\n"
            f"  ?query a <{TYPE_SAVED_QUERY}> .\n"
            f"  ?query <{RDFS_LABEL}> ?name .\n"
            f"  ?query <{PRED_QUERY_TEXT}> ?text .\n"
            f"  ?query <{PRED_SOURCE}> ?source .\n"
            f"  OPTIONAL {{ ?query <{DCTERMS_DESCRIPTION}> ?desc }}\n"
            "}\n"
            "ORDER BY ?name"
        )
        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        return [
            SavedQueryData(
                id=_extract_query_uuid(b["query"]["value"]),
                name=b["name"]["value"],
                description=b.get("desc", {}).get("value"),
                query_text=b["text"]["value"],
                created_at="", updated_at="",
                source=b.get("source", {}).get("value"),
                readonly=True,
            )
            for b in bindings
        ]

    async def list_all_queries(self, user_id: uuid.UUID) -> list[SavedQueryData]:
        """List user queries + model queries (model queries marked readonly)."""
        user_queries = await self.list_user_queries(user_id)
        model_queries = await self.list_model_queries()
        return user_queries + model_queries


# ---------- IRI extraction helpers ----------

def _extract_user_uuid(iri: str) -> str:
    if iri and iri.startswith("urn:sempkm:user:"):
        return iri[len("urn:sempkm:user:"):]
    return iri


def _extract_query_uuid(iri: str) -> str:
    if iri.startswith("urn:sempkm:query:"):
        return iri[len("urn:sempkm:query:"):]
    if ":query:" in iri:
        return iri.rsplit(":query:", 1)[-1]
    return iri


def _extract_exec_uuid(iri: str) -> str:
    if iri.startswith("urn:sempkm:query-exec:"):
        return iri[len("urn:sempkm:query-exec:"):]
    return iri


def _extract_view_uuid(iri: str) -> str:
    if iri.startswith("urn:sempkm:query-view:"):
        return iri[len("urn:sempkm:query-view:"):]
    return iri
