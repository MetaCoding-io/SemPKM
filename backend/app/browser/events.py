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
    get_triplestore_client,
)
from app.events.store import EventStore
from app.services.labels import LabelService
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
    db: AsyncSession = Depends(get_db_session),
    cursor: str | None = Query(default=None),
    op: str | None = Query(default=None),
    user_filter: str | None = Query(default=None, alias="user"),
    obj: str | None = Query(default=None),
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


@events_router.get("/events/{event_iri:path}/detail")
async def event_detail(
    request: Request,
    event_iri: str,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Render an inline diff partial for a single event.

    Returns an HTML fragment (no base template) suitable for insertion
    into a .event-diff-container via htmx.
    """
    from urllib.parse import unquote as _unquote

    from app.events.query import EventQueryService

    templates = request.app.state.templates
    decoded_iri = _unquote(event_iri)
    query_svc = EventQueryService(client)
    detail = await query_svc.get_event_detail(decoded_iri)
    if not detail:
        return HTMLResponse("<div class='event-diff-error'>Event not found.</div>")
    return templates.TemplateResponse(request, "browser/event_detail.html", {
        "request": request,
        "detail": detail,
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
