"""One-time migration: copy saved queries, shares, promotions, and history
from SQL tables to the RDF triplestore (urn:sempkm:queries graph).

Idempotent — skips queries whose IRI already exists in the graph.
Preserves original UUIDs for URL stability.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.sparql.models import (
    PromotedQueryView,
    SavedSparqlQuery,
    SharedQueryAccess,
    SparqlQueryHistory,
)
from app.sparql.query_service import (
    DCTERMS_CREATED,
    DCTERMS_MODIFIED,
    PRED_EXECUTED_BY,
    PRED_FROM_QUERY,
    PRED_OWNER,
    PRED_QUERY_TEXT,
    PRED_RENDERER_TYPE,
    PRED_SHARED_WITH,
    PROV_STARTED,
    QUERIES_GRAPH,
    RDFS_LABEL,
    TYPE_PROMOTED_VIEW,
    TYPE_QUERY_EXEC,
    TYPE_SAVED_QUERY,
    _dt,
    _esc,
    _lit,
    _query_iri,
    _user_iri,
    _view_iri,
)
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)


async def migrate_queries_to_rdf(
    db: AsyncSession, client: TriplestoreClient
) -> dict[str, int]:
    """Migrate all query-related SQL data to RDF.

    Returns counts: {queries, shares, promotions, history, skipped}.
    """
    counts = {"queries": 0, "shares": 0, "promotions": 0, "history": 0, "skipped": 0}

    # --- Saved queries ---
    result = await db.execute(select(SavedSparqlQuery))
    queries = result.scalars().all()

    for q in queries:
        iri = _query_iri(q.id)

        # Check if already migrated
        check = await client.query(
            f"ASK {{ GRAPH <{QUERIES_GRAPH}> {{ <{iri}> a <{TYPE_SAVED_QUERY}> }} }}"
        )
        if check.get("boolean", False):
            counts["skipped"] += 1
            continue

        user = _user_iri(q.user_id)
        created = q.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if q.created_at else ""
        updated = q.updated_at.strftime("%Y-%m-%dT%H:%M:%SZ") if q.updated_at else ""

        triples = [
            f"<{iri}> a <{TYPE_SAVED_QUERY}> .",
            f"<{iri}> <{PRED_OWNER}> <{user}> .",
            f"<{iri}> <{RDFS_LABEL}> {_lit(q.name)} .",
            f"<{iri}> <{PRED_QUERY_TEXT}> {_lit(q.query_text)} .",
        ]
        if created:
            triples.append(f"<{iri}> <{DCTERMS_CREATED}> {_dt(created)} .")
        if updated:
            triples.append(f"<{iri}> <{DCTERMS_MODIFIED}> {_dt(updated)} .")
        if q.description:
            triples.append(
                f"<{iri}> <http://purl.org/dc/terms/description> {_lit(q.description)} ."
            )

        body = "\n    ".join(triples)
        await client.update(
            f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {body}\n  }}\n}}"
        )
        counts["queries"] += 1

    logger.info("Migrated %d queries (%d skipped)", counts["queries"], counts["skipped"])

    # --- Shares ---
    share_result = await db.execute(select(SharedQueryAccess))
    shares = share_result.scalars().all()

    share_triples = []
    for s in shares:
        q_iri = _query_iri(s.query_id)
        u_iri = _user_iri(s.shared_with_user_id)
        share_triples.append(f"<{q_iri}> <{PRED_SHARED_WITH}> <{u_iri}> .")

    if share_triples:
        body = "\n    ".join(share_triples)
        await client.update(
            f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {body}\n  }}\n}}"
        )
    counts["shares"] = len(share_triples)
    logger.info("Migrated %d shares", counts["shares"])

    # --- Promotions ---
    promo_result = await db.execute(select(PromotedQueryView))
    promos = promo_result.scalars().all()

    for pv in promos:
        view = _view_iri(pv.id)
        q_iri = _query_iri(pv.query_id)
        user = _user_iri(pv.user_id)
        created = pv.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if pv.created_at else ""

        triples = [
            f"<{view}> a <{TYPE_PROMOTED_VIEW}> .",
            f"<{view}> <{PRED_FROM_QUERY}> <{q_iri}> .",
            f"<{view}> <{PRED_OWNER}> <{user}> .",
            f"<{view}> <{RDFS_LABEL}> {_lit(pv.display_label)} .",
            f"<{view}> <{PRED_RENDERER_TYPE}> '{_esc(pv.renderer_type)}' .",
        ]
        if created:
            triples.append(f"<{view}> <{DCTERMS_CREATED}> {_dt(created)} .")

        body = "\n    ".join(triples)
        await client.update(
            f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {body}\n  }}\n}}"
        )
        counts["promotions"] += 1

    logger.info("Migrated %d promotions", counts["promotions"])

    # --- History ---
    hist_result = await db.execute(select(SparqlQueryHistory))
    hist_rows = hist_result.scalars().all()

    batch = []
    for h in hist_rows:
        exec_iri = f"urn:sempkm:query-exec:{h.id}"
        user = _user_iri(h.user_id)
        ts = h.executed_at.strftime("%Y-%m-%dT%H:%M:%SZ") if h.executed_at else ""

        batch.extend([
            f"<{exec_iri}> a <{TYPE_QUERY_EXEC}> .",
            f"<{exec_iri}> <{PRED_EXECUTED_BY}> <{user}> .",
            f"<{exec_iri}> <{PRED_QUERY_TEXT}> {_lit(h.query_text)} .",
        ])
        if ts:
            batch.append(f"<{exec_iri}> <{PROV_STARTED}> {_dt(ts)} .")
        counts["history"] += 1

        # Flush in batches of 50
        if len(batch) > 200:
            body = "\n    ".join(batch)
            await client.update(
                f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {body}\n  }}\n}}"
            )
            batch = []

    if batch:
        body = "\n    ".join(batch)
        await client.update(
            f"INSERT DATA {{\n  GRAPH <{QUERIES_GRAPH}> {{\n    {body}\n  }}\n}}"
        )

    logger.info("Migrated %d history entries", counts["history"])
    logger.info(
        "Migration complete: %d queries, %d shares, %d promotions, %d history (%d skipped)",
        counts["queries"], counts["shares"], counts["promotions"],
        counts["history"], counts["skipped"],
    )
    return counts
