"""Events sub-router — event log, detail, and undo handlers."""

import logging
import re
import uuid as _uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from rdflib import URIRef
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.db.session import get_db_session
from app.dependencies import (
    get_event_store,
    get_label_service,
    get_shapes_service,
    get_triplestore_client,
)
from app.events.store import EventStore
from app.services.labels import LabelService
from app.services.shapes import ShapesService
from app.sparql.builder import sparql_escape_string
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

_USER_IRI_RE = re.compile(r"^urn:sempkm:user:(.+)$")


async def resolve_user_names(
    db: AsyncSession, user_iris: list[str]
) -> dict[str, str]:
    """Batch-resolve user IRIs to display names via a single SQL query.

    Parses ``urn:sempkm:user:{uuid}`` IRIs, skips any that don't match
    or contain invalid UUIDs, and returns ``{iri: display_name_or_email}``.
    """
    if not user_iris:
        return {}

    # Parse valid UUIDs from IRIs, building iri↔uuid mapping
    iri_to_uuid: dict[str, _uuid.UUID] = {}
    for iri in user_iris:
        m = _USER_IRI_RE.match(iri)
        if not m:
            logger.warning("Failed to resolve user IRI %s: no pattern match", iri)
            continue
        try:
            iri_to_uuid[iri] = _uuid.UUID(m.group(1))
        except ValueError:
            logger.warning("Failed to resolve user IRI %s: invalid UUID", iri)

    if not iri_to_uuid:
        return {}

    # Single batched query
    uuid_list = list(iri_to_uuid.values())
    result = await db.execute(sa_select(User).where(User.id.in_(uuid_list)))
    db_users = result.scalars().all()

    # Build reverse lookup: uuid → db_user
    uuid_to_user = {u.id: u for u in db_users}

    user_names: dict[str, str] = {}
    for iri, uid in iri_to_uuid.items():
        db_user = uuid_to_user.get(uid)
        if db_user:
            user_names[iri] = db_user.display_name or db_user.email
    return user_names

events_router = APIRouter(tags=["events"])


@events_router.get("/events")
async def event_log(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    label_service: LabelService = Depends(get_label_service),
    shapes_service: ShapesService = Depends(get_shapes_service),
    db: AsyncSession = Depends(get_db_session),
    cursor: str | None = Query(default=None),
    op: str | None = Query(default=None),
    user_filter: str | None = Query(default=None, alias="user"),
    obj: str | None = Query(default=None),
    pred: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """Render the event log timeline as an htmx partial for the bottom panel."""
    from app.events.query import EventQueryService

    templates = request.app.state.templates
    query_svc = EventQueryService(client)
    events, next_cursor = await query_svc.list_events(
        cursor_timestamp=cursor,
        op_type=op,
        user_iri=user_filter,
        object_iri=obj,
        date_from=date_from,
        date_to=date_to,
        predicate_iri=pred,
    )

    # Resolve labels for all affected IRIs
    all_iris = [iri for e in events for iri in e.affected_iris if iri]
    labels = await label_service.resolve_batch(all_iris) if all_iris else {}

    # Resolve user display names via batched SQL lookup (single WHERE IN query)
    user_iris = list({e.performed_by for e in events if e.performed_by})
    user_names = await resolve_user_names(db, user_iris)

    # Build active filters list for chip rendering
    active_filters = []
    if op:
        active_filters.append({"param": "op", "value": op, "label": f"op: {op}"})
    if obj:
        obj_label = labels.get(obj, obj[:30] + "..." if len(obj) > 30 else obj)
        active_filters.append({"param": "obj", "value": obj, "label": f"object: {obj_label}"})
    if pred:
        # Resolve predicate label from shapes service for human-readable chip
        pred_labels = await shapes_service.get_labels_for_predicates([pred])
        pred_label = pred_labels.get(pred) or ShapesService._local_name(pred)
        active_filters.append({"param": "pred", "value": pred, "label": f"property: {pred_label}"})
    if user_filter:
        active_filters.append({"param": "user", "value": user_filter, "label": f"user: {user_names.get(user_filter, user_filter)}"})
    if date_from:
        active_filters.append({"param": "date_from", "value": date_from, "label": f"from: {date_from}"})
    if date_to:
        active_filters.append({"param": "date_to", "value": date_to, "label": f"to: {date_to}"})

    return templates.TemplateResponse(request, "browser/event_log.html", {
        "request": request,
        "events": events,
        "labels": labels,
        "user_names": user_names,
        "next_cursor": next_cursor,
        "active_filters": active_filters,
        "current_params": dict(request.query_params),
    })


@events_router.get("/events/suggest-types")
async def suggest_types(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Return distinct operation types from event graphs as HTML suggestions."""
    templates = request.app.state.templates
    sparql = """PREFIX sempkm: <urn:sempkm:>
SELECT DISTINCT ?opType WHERE {
  GRAPH ?event {
    ?event sempkm:operationType ?opType .
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
}
ORDER BY ?opType"""
    suggestions: list[dict] = []
    try:
        result = await client.query(sparql)
        for row in result.get("results", {}).get("bindings", []):
            op = row["opType"]["value"]
            suggestions.append({"value": op, "label": op})
    except Exception:
        logger.warning("Failed to query suggestion types from events", exc_info=True)

    return templates.TemplateResponse(request, "browser/_event_suggestions.html", {
        "suggestions": suggestions,
        "filter_param": "op",
    })


@events_router.get("/events/suggest-predicates")
async def suggest_predicates(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    shapes_service: ShapesService = Depends(get_shapes_service),
    q: str = Query(default=""),
):
    """Return distinct predicates from event data triples as HTML suggestions.

    Excludes event metadata predicates. Resolves human-readable labels from
    SHACL shapes and filters by `q` parameter against label or IRI local name.
    """
    templates = request.app.state.templates
    sparql = """PREFIX sempkm: <urn:sempkm:>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?pred WHERE {
  GRAPH ?event {
    ?event a sempkm:Event .
    ?s ?pred ?o .
    FILTER(?s != ?event)
  }
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
}
LIMIT 100"""

    pred_iris: list[str] = []
    try:
        result = await client.query(sparql)
        for row in result.get("results", {}).get("bindings", []):
            pred_iris.append(row["pred"]["value"])
    except Exception:
        logger.warning("Failed to query predicates from events", exc_info=True)

    # Resolve labels from SHACL shapes
    pred_labels = await shapes_service.get_labels_for_predicates(pred_iris) if pred_iris else {}

    # Build suggestions with label + IRI local name
    suggestions: list[dict] = []
    q_lower = q.strip().lower()
    for iri in pred_iris:
        label = pred_labels.get(iri) or ShapesService._local_name(iri)
        local_name = ShapesService._local_name(iri)
        display = f"{label} ({local_name})" if label != local_name else label
        # Filter by q if provided
        if q_lower and q_lower not in label.lower() and q_lower not in local_name.lower() and q_lower not in iri.lower():
            continue
        suggestions.append({"value": iri, "label": display})

    # Limit to 20
    suggestions = suggestions[:20]

    return templates.TemplateResponse(request, "browser/_event_suggestions.html", {
        "suggestions": suggestions,
        "filter_param": "pred",
    })


@events_router.get("/events/suggest-objects")
async def suggest_objects(
    request: Request,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    label_service: LabelService = Depends(get_label_service),
    q: str = Query(default=""),
):
    """Return distinct affected IRIs from events as HTML suggestions.

    Resolves human-readable labels via LabelService and filters by `q`
    parameter against label or IRI.
    """
    templates = request.app.state.templates

    # Build SPARQL with optional text filter in IRI
    q_escaped = sparql_escape_string(q.strip())
    filter_clause = ""
    if q_escaped:
        filter_clause = f'FILTER(CONTAINS(LCASE(STR(?iri)), LCASE("{q_escaped}")))'

    sparql = f"""PREFIX sempkm: <urn:sempkm:>
SELECT DISTINCT ?iri WHERE {{
  GRAPH ?event {{
    ?event sempkm:affectedIRI ?iri .
  }}
  FILTER(STRSTARTS(STR(?event), "urn:sempkm:event:"))
  {filter_clause}
}}
LIMIT 30"""

    obj_iris: list[str] = []
    try:
        result = await client.query(sparql)
        for row in result.get("results", {}).get("bindings", []):
            obj_iris.append(row["iri"]["value"])
    except Exception:
        logger.warning("Failed to query object IRIs from events", exc_info=True)

    # Resolve labels
    labels = await label_service.resolve_batch(obj_iris) if obj_iris else {}

    # Build suggestions; also filter by label if q provided
    suggestions: list[dict] = []
    q_lower = q.strip().lower()
    for iri in obj_iris:
        label = labels.get(iri, iri)
        # If q didn't match IRI (SPARQL filter), also match by label
        if q_lower and q_lower not in label.lower() and q_lower not in iri.lower():
            continue
        # Truncate IRI for display
        iri_short = iri if len(iri) <= 40 else "..." + iri[-37:]
        display = f"{label} ({iri_short})" if label != iri else iri_short
        suggestions.append({"value": iri, "label": display})

    suggestions = suggestions[:20]

    return templates.TemplateResponse(request, "browser/_event_suggestions.html", {
        "suggestions": suggestions,
        "filter_param": "obj",
    })


@events_router.get("/events/{event_iri:path}/detail")
async def event_detail(
    request: Request,
    event_iri: str,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    shapes_service: ShapesService = Depends(get_shapes_service),
    label_service: LabelService = Depends(get_label_service),
):
    """Render an inline diff partial for a single event.

    Returns an HTML fragment (no base template) suitable for insertion
    into a .event-diff-container via htmx.

    Resolves human-readable predicate labels from SHACL shapes (``sh:name``)
    and helptext tooltips (``sempkm:editHelpText`` / ``sh:description``).
    Falls back to local-name extraction when shapes resolution fails.
    """
    from urllib.parse import unquote as _unquote

    from app.events.query import EventQueryService

    templates = request.app.state.templates
    decoded_iri = _unquote(event_iri)
    query_svc = EventQueryService(client)
    detail = await query_svc.get_event_detail(decoded_iri)
    if not detail:
        return HTMLResponse("<div class='event-diff-error'>Event not found.</div>")

    # Collect all predicate IRIs from both diff tables and creation triples
    pred_iris: list[str] = list(detail.new_values.keys())
    pred_iris.extend(
        p for _, p, _ in detail.data_triples if p not in pred_iris
    )

    # Resolve labels and helptext from SHACL shapes
    predicate_labels = await shapes_service.get_labels_for_predicates(pred_iris)
    predicate_helptext = await shapes_service.get_helptext_for_predicates(pred_iris)

    # For predicates not resolved via shapes, try LabelService as fallback
    unresolved = [iri for iri in pred_iris if iri not in predicate_labels]
    if unresolved:
        fallback_labels = await label_service.resolve_batch(unresolved)
        for iri, label in fallback_labels.items():
            if label and label != iri:
                predicate_labels[iri] = label

    return templates.TemplateResponse(request, "browser/event_detail.html", {
        "request": request,
        "detail": detail,
        "predicate_labels": predicate_labels,
        "predicate_helptext": predicate_helptext,
    })


@events_router.post("/events/{event_iri:path}/undo")
async def undo_event(
    request: Request,
    event_iri: str,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
    label_service: LabelService = Depends(get_label_service),
):
    """Create a compensating event that reverses the specified event.

    Builds a compensation Operation via EventQueryService.build_compensation()
    and commits it via EventStore. The original event is not modified.
    """
    from urllib.parse import unquote as _unquote

    from app.events.query import EventQueryService

    decoded_iri = _unquote(event_iri)
    query_svc = EventQueryService(client)
    detail = await query_svc.get_event_detail(decoded_iri)
    if not detail:
        return JSONResponse(status_code=404, content={"error": "Event not found"})
    compensation = await query_svc.build_compensation(decoded_iri, detail)
    if not compensation:
        return JSONResponse(status_code=400, content={"error": "This event cannot be undone"})
    user_iri = URIRef(f"urn:sempkm:user:{user.id}")
    event_result = await event_store.commit([compensation], performed_by=user_iri, performed_by_role=user.role)
    label_service.invalidate(event_result.affected_iris)
    return JSONResponse(content={"status": "ok", "message": "Undo applied successfully"})
