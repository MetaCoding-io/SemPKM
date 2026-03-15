"""Federation API endpoints for shared graphs, sync, invitations, and notifications.

Provides endpoints for:
- Shared graph CRUD (create, list, get, leave)
- Object management in shared graphs (copy, list objects)
- Sync trigger (pull from remote)
- Invitation send/accept/decline
- Notification sending to remote instances
- Contact listing
- Patch export for remote pull (from Plan 01)
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from rdflib import Literal, URIRef

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_event_store, get_triplestore_client
from app.events.store import EventStore, Operation
from app.federation.patch import serialize_patch
from app.federation.schemas import (
    ContactInfo,
    InvitationSend,
    NotificationSend,
    PatchExportResponse,
    SharedGraphCreate,
    SharedGraphResponse,
    SyncResult,
)
from app.federation.service import FederationService
from app.rdf.namespaces import AS, PROV, SEMPKM, XSD
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/federation", tags=["federation"])


# ---------------------------------------------------------------------------
# Dependency: FederationService
# ---------------------------------------------------------------------------


async def get_federation_service(
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
) -> FederationService:
    """FastAPI dependency that provides a FederationService instance."""
    return FederationService(client, event_store)


# ---------------------------------------------------------------------------
# Shared graph CRUD
# ---------------------------------------------------------------------------


@router.post("/shared-graphs", response_model=SharedGraphResponse, status_code=201)
async def create_shared_graph(
    body: SharedGraphCreate,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Create a new shared graph.

    Requires authenticated user with a published WebID.
    The creating user is added as the first member.
    """
    creator_webid = _get_user_webid(current_user)

    graph_iri = await service.create_shared_graph(
        name=body.name,
        description=body.description,
        required_model=body.required_model,
        creator_webid=creator_webid,
    )

    # Return the created graph details
    result = await service.get_shared_graph(graph_iri)
    if result is None:
        raise HTTPException(500, "Failed to retrieve created shared graph")
    return result


@router.get("/shared-graphs", response_model=list[SharedGraphResponse])
async def list_shared_graphs(
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """List the current user's shared graphs."""
    user_webid = _get_user_webid(current_user)
    return await service.list_shared_graphs(user_webid)


@router.get("/shared-graphs/{graph_id}", response_model=SharedGraphResponse)
async def get_shared_graph(
    graph_id: str,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Get details for a single shared graph."""
    graph_iri = f"urn:sempkm:shared:{graph_id}"
    result = await service.get_shared_graph(graph_iri)
    if result is None:
        raise HTTPException(404, "Shared graph not found")
    return result


@router.delete("/shared-graphs/{graph_id}", status_code=204)
async def leave_shared_graph(
    graph_id: str,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Leave a shared graph. Data stays as a frozen snapshot."""
    graph_iri = f"urn:sempkm:shared:{graph_id}"
    user_webid = _get_user_webid(current_user)
    await service.leave_shared_graph(graph_iri, user_webid)


# ---------------------------------------------------------------------------
# Object management in shared graphs
# ---------------------------------------------------------------------------


@router.post("/shared-graphs/{graph_id}/copy")
async def copy_to_shared_graph(
    graph_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Copy an object's triples from the current graph into a shared graph.

    Body: {"object_iri": "..."}

    The copy is committed via EventStore with target_graph set to the
    shared graph. After commit, sync-alert notifications are sent to
    all remote members.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON body")

    object_iri = body.get("object_iri")
    if not object_iri:
        raise HTTPException(400, "Missing object_iri")

    graph_iri = f"urn:sempkm:shared:{graph_id}"
    user_iri = URIRef(f"urn:sempkm:user:{current_user.id}")

    await service.copy_to_shared_graph(
        object_iri=object_iri,
        shared_graph_iri=graph_iri,
        performed_by=user_iri,
        performed_by_role=current_user.role,
    )

    return JSONResponse(
        content={"status": "copied", "object_iri": object_iri, "graph_iri": graph_iri}
    )


@router.get("/shared-graphs/{graph_id}/objects")
async def list_shared_graph_objects(
    graph_id: str,
    current_user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """List objects in a shared graph."""
    graph_iri = f"urn:sempkm:shared:{graph_id}"

    sparql = f"""
    SELECT DISTINCT ?s ?type ?label WHERE {{
      GRAPH <{graph_iri}> {{
        ?s a ?type .
        OPTIONAL {{
          ?s <http://purl.org/dc/terms/title> ?label .
        }}
      }}
    }}
    ORDER BY ?type ?label
    LIMIT 200
    """

    results = await client.query(sparql)
    bindings = results.get("results", {}).get("bindings", [])

    objects = []
    for row in bindings:
        objects.append({
            "iri": row.get("s", {}).get("value", ""),
            "type": row.get("type", {}).get("value", ""),
            "label": row.get("label", {}).get("value", ""),
        })

    return JSONResponse(content=objects)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


@router.post("/shared-graphs/{graph_id}/sync", response_model=SyncResult)
async def sync_shared_graph(
    graph_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Trigger sync for a shared graph (pull from remote instance).

    Body (optional): {"remote_instance_url": "https://..."}
    If not provided, attempts to discover from shared graph members.
    """
    graph_iri = f"urn:sempkm:shared:{graph_id}"
    user_webid = _get_user_webid(current_user)

    # Get remote instance URL from body or discover from members
    try:
        body = await request.json()
    except Exception:
        body = {}

    remote_url = body.get("remote_instance_url", "")
    if not remote_url:
        # Auto-discover from shared graph's remote members
        remote_url = await service.discover_remote_instance_url(
            graph_iri, user_webid
        )
        if not remote_url:
            raise HTTPException(
                400,
                "No remote members found for this shared graph",
            )

    return await service.sync_shared_graph(
        graph_iri=graph_iri,
        remote_instance_url=remote_url,
        local_webid=user_webid,
    )


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post("/invitations", status_code=202)
async def send_invitation(
    body: InvitationSend,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Send a shared graph invitation to a remote user.

    Discovers the recipient via WebFinger, builds an Offer notification,
    and POSTs to their inbox.
    """
    sender_webid = _get_user_webid(current_user)

    await service.send_invitation(
        graph_iri=body.graph_iri,
        recipient_handle=body.recipient_handle,
        sender_webid=sender_webid,
    )

    return JSONResponse(
        status_code=202,
        content={"status": "sent", "recipient": body.recipient_handle},
    )


@router.post("/invitations/{notification_id}/accept")
async def accept_invitation(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Accept a shared graph invitation.

    Creates the shared graph locally and stores the sender as a contact.
    """
    notification_iri = f"urn:sempkm:inbox:{notification_id}"
    user_webid = _get_user_webid(current_user)

    await service.accept_invitation(notification_iri, user_webid)

    return JSONResponse(content={"status": "accepted", "notification_id": notification_id})


@router.post("/invitations/{notification_id}/decline")
async def decline_invitation(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Decline a shared graph invitation (sets notification state to dismissed)."""
    notification_iri = f"urn:sempkm:inbox:{notification_id}"

    sparql = f"""
    DELETE {{
      GRAPH <{notification_iri}> {{
        ?notif <{SEMPKM}notificationState> ?oldState .
      }}
    }}
    INSERT {{
      GRAPH <{notification_iri}> {{
        ?notif <{SEMPKM}notificationState> "dismissed" .
      }}
    }}
    WHERE {{
      GRAPH <{notification_iri}> {{
        ?notif <{SEMPKM}notificationState> ?oldState .
      }}
    }}
    """
    await client.update(sparql)

    return JSONResponse(content={"status": "declined", "notification_id": notification_id})


# ---------------------------------------------------------------------------
# Notifications (outbound)
# ---------------------------------------------------------------------------


@router.post("/notifications/send", status_code=202)
async def send_notification(
    body: NotificationSend,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Send a notification to a remote user.

    Supports recommendation (Announce) and message (Note) types.
    """
    sender_webid = _get_user_webid(current_user)

    await service.send_notification(
        recipient_handle=body.recipient_handle,
        notification_type=body.notification_type,
        sender_webid=sender_webid,
        object_iri=body.object_iri,
        content=body.content,
    )

    return JSONResponse(
        status_code=202,
        content={"status": "sent", "type": body.notification_type},
    )


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@router.get("/contacts", response_model=list[ContactInfo])
async def list_contacts(
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """List known remote contacts derived from shared graph memberships."""
    user_webid = _get_user_webid(current_user)
    return await service.list_contacts(user_webid)


# ---------------------------------------------------------------------------
# Patch export (from Plan 01)
# ---------------------------------------------------------------------------


@router.get("/patches/{graph_id}", response_model=PatchExportResponse)
async def export_patches(
    graph_id: str,
    since: str = Query(..., description="ISO timestamp to fetch events after"),
    requester: str = Query(
        default="",
        description="Requester instance URL for syncSource filtering (loop prevention)",
    ),
    current_user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
) -> PatchExportResponse:
    """Export RDF Patch for events targeting a shared graph since a timestamp.

    Queries event named graphs that:
    1. Have sempkm:graphTarget matching the shared graph IRI
    2. Have timestamp > since
    3. Do NOT have sempkm:syncSource matching the requester (loop prevention)

    Returns the combined patch text, event count, and metadata.
    """
    graph_iri = f"urn:sempkm:shared:{graph_id}"

    # Build SPARQL to find matching events and their data triples.
    # We query event graphs that target the shared graph and extract
    # all non-metadata triples as inserts for the patch.
    requester_filter = ""
    if requester:
        requester_filter = (
            f'FILTER NOT EXISTS {{ ?event <{SEMPKM.syncSource}> <{requester}> }}'
        )

    sparql = f"""
    SELECT ?event ?timestamp ?s ?p ?o
    WHERE {{
      GRAPH ?event {{
        ?event a <{SEMPKM.Event}> ;
               <{PROV.startedAtTime}> ?timestamp ;
               <{SEMPKM.graphTarget}> <{graph_iri}> .
        FILTER(?timestamp > "{since}"^^<{XSD.dateTime}>)
        {requester_filter}
        ?s ?p ?o .
        FILTER(?s != ?event)
      }}
    }}
    ORDER BY ?timestamp ?event
    """

    results = await client.query(sparql)
    bindings = results.get("results", {}).get("bindings", [])

    # Group data triples by event
    events_data: dict[str, list[tuple]] = {}
    for row in bindings:
        event_uri = row["event"]["value"]
        s = _binding_to_term(row["s"])
        p = _binding_to_term(row["p"])
        o = _binding_to_term(row["o"])
        if event_uri not in events_data:
            events_data[event_uri] = []
        events_data[event_uri].append((s, p, o))

    # Create Operations from grouped event data (all triples treated as inserts
    # since the event graph stores the "new state" triples)
    operations: list[Operation] = []
    for event_uri, triples in events_data.items():
        op = Operation(
            operation_type="federation.export",
            affected_iris=[event_uri],
            description=f"Exported from event {event_uri}",
            data_triples=[],
            materialize_inserts=triples,
            materialize_deletes=[],
        )
        operations.append(op)

    # Serialize to RDF Patch format
    if operations:
        patch_text = serialize_patch(operations, graph_iri)
    else:
        patch_text = ""

    return PatchExportResponse(
        patch_text=patch_text,
        event_count=len(events_data),
        since=since,
        graph_iri=graph_iri,
    )


# ---------------------------------------------------------------------------
# HTML partials (htmx endpoints for UI panels)
# ---------------------------------------------------------------------------


@router.get("/inbox-partial")
async def inbox_partial(
    request: Request,
    current_user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Render inbox notification list as HTML partial for htmx swap."""
    templates = request.app.state.templates

    # Query notifications
    sparql = f"""
    SELECT ?graph ?type ?actor ?summary ?state ?receivedAt ?content ?target
    WHERE {{
      GRAPH ?graph {{
        ?notif a ?type .
        ?notif <{SEMPKM}notificationState> ?state .
        ?notif <{SEMPKM}receivedAt> ?receivedAt .
        OPTIONAL {{ ?notif <{AS}actor> ?actor }}
        OPTIONAL {{ ?notif <{AS}summary> ?summary }}
        OPTIONAL {{ ?notif <{AS}content> ?content }}
        OPTIONAL {{ ?notif <{AS}target> ?target }}
      }}
      FILTER(STRSTARTS(STR(?graph), "urn:sempkm:inbox:"))
    }}
    ORDER BY DESC(?receivedAt)
    LIMIT 50
    """

    results = await client.query(sparql)
    bindings = results.get("results", {}).get("bindings", [])

    notifications = []
    unread_count = 0
    for row in bindings:
        graph_iri = row.get("graph", {}).get("value", "")
        notif_id = graph_iri.replace("urn:sempkm:inbox:", "")
        type_val = row.get("type", {}).get("value", "")
        type_name = type_val.rsplit("#", 1)[-1] if "#" in type_val else type_val.rsplit("/", 1)[-1]
        state = row.get("state", {}).get("value", "")
        received = row.get("receivedAt", {}).get("value", "")
        actor_raw = row.get("actor", {}).get("value", "")

        if state == "unread":
            unread_count += 1

        notifications.append({
            "id": notif_id,
            "type": type_name,
            "actor": actor_raw,
            "actor_label": actor_raw.rsplit("/", 1)[-1] if "/" in actor_raw else actor_raw,
            "summary": row.get("summary", {}).get("value", ""),
            "content": row.get("content", {}).get("value", ""),
            "state": state,
            "receivedAt": received,
            "receivedAt_human": _humanize_time(received),
            "target": row.get("target", {}).get("value", ""),
            "object_iri": "",
        })

    return templates.TemplateResponse(request, "browser/partials/inbox_list.html", {
        "notifications": notifications,
        "unread_count": unread_count,
    })


@router.get("/collab-partial")
async def collab_partial(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
):
    """Render collaboration panel content as HTML partial for htmx swap."""
    templates = request.app.state.templates
    user_webid = _get_user_webid(current_user)

    shared_graphs_raw = await service.list_shared_graphs(user_webid)
    contacts_raw = await service.list_contacts(user_webid)

    # Enrich shared graphs with UI fields
    shared_graphs = []
    for g in shared_graphs_raw:
        graph_id = g.graph_iri.replace("urn:sempkm:shared:", "")
        sync_status = _sync_status(g.last_sync)
        shared_graphs.append({
            "graph_iri": g.graph_iri,
            "graph_id": graph_id,
            "name": g.name,
            "description": g.description,
            "members": g.members,
            "last_sync": g.last_sync,
            "last_sync_human": _humanize_time(g.last_sync) if g.last_sync else None,
            "pending_count": g.pending_count,
            "sync_status": sync_status,
        })

    contacts = []
    for c in contacts_raw:
        contacts.append({
            "webid": c.webid,
            "label": c.label,
            "instance_url": c.instance_url,
            "last_seen": c.last_seen,
            "last_seen_human": _humanize_time(c.last_seen) if c.last_seen else None,
        })

    return templates.TemplateResponse(request, "browser/partials/collab_content.html", {
        "shared_graphs": shared_graphs,
        "contacts": contacts,
    })


@router.get("/shared-nav")
async def shared_nav(
    request: Request,
    current_user: User = Depends(get_current_user),
    service: FederationService = Depends(get_federation_service),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Render shared nav section as HTML partial for htmx swap."""
    templates = request.app.state.templates
    user_webid = _get_user_webid(current_user)

    shared_graphs_raw = await service.list_shared_graphs(user_webid)

    shared_graphs = []
    for g in shared_graphs_raw:
        graph_iri = g.graph_iri
        sync_status = _sync_status(g.last_sync)

        # Query objects in this shared graph grouped by type
        sparql = f"""
        SELECT DISTINCT ?s ?type ?label WHERE {{
          GRAPH <{graph_iri}> {{
            ?s a ?type .
            OPTIONAL {{
              ?s <http://purl.org/dc/terms/title> ?t .
            }}
            OPTIONAL {{
              ?s <http://www.w3.org/2000/01/rdf-schema#label> ?l .
            }}
            OPTIONAL {{
              ?s <http://www.w3.org/2004/02/skos/core#prefLabel> ?p .
            }}
            OPTIONAL {{
              ?s <http://xmlns.com/foaf/0.1/name> ?f .
            }}
            BIND(COALESCE(?t, ?l, ?p, ?f, REPLACE(STR(?s), "^.*/", "")) AS ?label)
          }}
        }}
        ORDER BY ?type ?label
        LIMIT 200
        """

        results = await client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        # Group by type
        type_groups: dict[str, list[dict]] = {}
        for row in bindings:
            obj_iri = row.get("s", {}).get("value", "")
            obj_type = row.get("type", {}).get("value", "")
            obj_label = row.get("label", {}).get("value", "")
            type_label = obj_type.rsplit("#", 1)[-1] if "#" in obj_type else obj_type.rsplit("/", 1)[-1]
            if type_label not in type_groups:
                type_groups[type_label] = []
            type_groups[type_label].append({"iri": obj_iri, "label": obj_label})

        objects_by_type = [
            {"label": tl, "objects": objs}
            for tl, objs in sorted(type_groups.items())
        ]

        shared_graphs.append({
            "name": g.name,
            "graph_iri": graph_iri,
            "sync_status": sync_status,
            "objects_by_type": objects_by_type,
        })

    return templates.TemplateResponse(request, "browser/partials/shared_nav_content.html", {
        "shared_graphs": shared_graphs,
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user_webid(user: User) -> str:
    """Extract the user's WebID URI.

    Falls back to a urn:sempkm:user:{id} if no published WebID URL exists.
    """
    if hasattr(user, "webid_url") and user.webid_url:
        return user.webid_url
    return f"urn:sempkm:user:{user.id}"


def _binding_to_term(binding: dict) -> URIRef | Literal:
    """Convert a SPARQL JSON result binding to an rdflib term."""
    term_type = binding["type"]
    value = binding["value"]

    if term_type == "uri":
        return URIRef(value)
    elif term_type == "literal":
        datatype = binding.get("datatype")
        lang = binding.get("xml:lang")
        if lang:
            return Literal(value, lang=lang)
        elif datatype:
            return Literal(value, datatype=URIRef(datatype))
        else:
            return Literal(value)
    elif term_type == "bnode":
        return URIRef(f"urn:skolem:{value}")
    else:
        return URIRef(value)


def _humanize_time(iso_str: str | None) -> str:
    """Convert an ISO timestamp string to a human-friendly relative time."""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            mins = int(seconds // 60)
            return f"{mins}m ago"
        elif seconds < 86400:
            hrs = int(seconds // 3600)
            return f"{hrs}h ago"
        else:
            days = int(seconds // 86400)
            return f"{days}d ago"
    except (ValueError, TypeError):
        return iso_str[:16] if len(iso_str) > 16 else iso_str


def _sync_status(last_sync: str | None) -> str:
    """Return sync status color class based on last_sync timestamp.

    green: synced within 24 hours
    yellow: synced but >24 hours ago
    gray: never synced
    """
    if not last_sync:
        return "gray"
    try:
        dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        if diff.total_seconds() < 86400:
            return "green"
        else:
            return "yellow"
    except (ValueError, TypeError):
        return "gray"
