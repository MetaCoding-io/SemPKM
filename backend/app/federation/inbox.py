"""LDN (Linked Data Notifications) inbox receiver and notification management.

Implements W3C LDN inbox for receiving JSON-LD notifications from remote
instances. Notifications are stored as RDF named graphs in the triplestore.
Supports notification state management (unread/read/acted/dismissed).
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_triplestore_client
from app.federation.signatures import VerifyHTTPSignature
from app.rdf.namespaces import AS, SEMPKM, XSD
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

inbox_router = APIRouter(tags=["federation-inbox"])

# Allowed notification types per CONTEXT.md
ALLOWED_TYPES = {"Offer", "Announce", "Update", "Note"}


@inbox_router.post("/api/inbox", status_code=202)
async def receive_notification(
    request: Request,
    sender_webid: str = Depends(VerifyHTTPSignature()),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Receive an LDN notification from a remote instance.

    Verifies the HTTP Signature, validates the JSON-LD payload, and stores
    the notification as a named graph in the triplestore with metadata.

    Returns 202 Accepted with a Location header for the notification IRI.
    """
    # Check Content-Type
    content_type = request.headers.get("content-type", "")
    if not any(
        ct in content_type
        for ct in ("application/ld+json", "application/json")
    ):
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/ld+json or application/json",
        )

    # Parse JSON-LD body
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # Validate required fields
    notif_type = body.get("type")
    if notif_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification type: {notif_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_TYPES))}",
        )

    actor = body.get("actor")
    if not actor:
        raise HTTPException(status_code=400, detail="Missing 'actor' field")

    # Verify actor matches the sender's WebID
    if actor != sender_webid:
        raise HTTPException(
            status_code=403,
            detail="Actor does not match sender's WebID",
        )

    # Generate notification graph IRI
    notification_id = str(uuid4())
    notification_iri = f"urn:sempkm:inbox:{notification_id}"
    now = datetime.now(timezone.utc).isoformat()

    # Build SPARQL INSERT for the notification named graph
    # Store the JSON-LD fields as RDF triples using ActivityStreams vocabulary
    sparql_triples = []
    notif_uri = f"<{notification_iri}>"

    # Core metadata
    sparql_triples.append(f"{notif_uri} a <{AS}{notif_type}> .")
    sparql_triples.append(f'{notif_uri} <{AS}actor> <{actor}> .')

    # Summary
    summary = body.get("summary", "")
    if summary:
        escaped_summary = _escape_sparql_string(summary)
        sparql_triples.append(f'{notif_uri} <{AS}summary> "{escaped_summary}" .')

    # Object (nested)
    obj = body.get("object")
    if obj and isinstance(obj, dict):
        obj_id = obj.get("id", f"{notification_iri}:object")
        obj_type = obj.get("type", "Object")
        sparql_triples.append(f'{notif_uri} <{AS}object> <{obj_id}> .')
        sparql_triples.append(f'<{obj_id}> a <{AS}{obj_type}> .')
        obj_name = obj.get("name", "")
        if obj_name:
            escaped_name = _escape_sparql_string(obj_name)
            sparql_triples.append(f'<{obj_id}> <{AS}name> "{escaped_name}" .')
        # Store extra sempkm-prefixed fields
        for key, value in obj.items():
            if key.startswith("sempkm:") and isinstance(value, str):
                prop = key.replace("sempkm:", str(SEMPKM))
                escaped_val = _escape_sparql_string(value)
                sparql_triples.append(f'<{obj_id}> <{prop}> "{escaped_val}" .')
    elif obj and isinstance(obj, str):
        sparql_triples.append(f'{notif_uri} <{AS}object> <{obj}> .')

    # Target
    target = body.get("target")
    if target:
        sparql_triples.append(f'{notif_uri} <{AS}target> <{target}> .')

    # Content (for Note type)
    content = body.get("content", "")
    if content:
        escaped_content = _escape_sparql_string(content)
        media_type = body.get("mediaType", "text/plain")
        sparql_triples.append(f'{notif_uri} <{AS}content> "{escaped_content}" .')
        sparql_triples.append(
            f'{notif_uri} <{AS}mediaType> "{_escape_sparql_string(media_type)}" .'
        )

    # SemPKM metadata
    sparql_triples.append(
        f'{notif_uri} <{SEMPKM}receivedAt> "{now}"^^<{XSD.dateTime}> .'
    )
    sparql_triples.append(
        f'{notif_uri} <{SEMPKM}notificationState> "unread" .'
    )
    sparql_triples.append(f'{notif_uri} <{SEMPKM}senderWebID> <{sender_webid}> .')

    # Execute INSERT DATA into the notification named graph
    sparql = f"""
    INSERT DATA {{
      GRAPH <{notification_iri}> {{
        {chr(10).join(f"        {t}" for t in sparql_triples)}
      }}
    }}
    """

    try:
        await client.update(sparql)
    except Exception as e:
        logger.error("Failed to store notification %s: %s", notification_iri, e)
        raise HTTPException(status_code=500, detail="Failed to store notification")

    logger.info(
        "Received %s notification from %s -> %s",
        notif_type,
        sender_webid,
        notification_iri,
    )

    return Response(
        status_code=202,
        headers={"Location": notification_iri},
    )


@inbox_router.get("/api/inbox")
async def list_notifications(
    request: Request,
    state: str | None = None,
    current_user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """List inbox notifications with optional state filtering.

    Returns a JSON array of notification summaries.
    Query params:
        state: Filter by notification state (unread, read, acted, dismissed)
    """
    state_filter = ""
    if state:
        state_filter = f'FILTER(?state = "{_escape_sparql_string(state)}")'

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
        {state_filter}
      }}
      FILTER(STRSTARTS(STR(?graph), "urn:sempkm:inbox:"))
    }}
    ORDER BY DESC(?receivedAt)
    """

    results = await client.query(sparql)
    bindings = results.get("results", {}).get("bindings", [])

    notifications = []
    for row in bindings:
        graph_iri = row.get("graph", {}).get("value", "")
        notif_id = graph_iri.replace("urn:sempkm:inbox:", "")
        type_val = row.get("type", {}).get("value", "")
        # Extract just the type local name from the AS URI
        type_name = type_val.rsplit("#", 1)[-1] if "#" in type_val else type_val.rsplit("/", 1)[-1]

        notifications.append({
            "id": notif_id,
            "graph_iri": graph_iri,
            "type": type_name,
            "actor": row.get("actor", {}).get("value", ""),
            "summary": row.get("summary", {}).get("value", ""),
            "content": row.get("content", {}).get("value", ""),
            "state": row.get("state", {}).get("value", ""),
            "receivedAt": row.get("receivedAt", {}).get("value", ""),
        })

    return JSONResponse(content=notifications)


@inbox_router.patch("/api/inbox/{notification_id}")
async def update_notification_state(
    notification_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Update a notification's state.

    Valid transitions: unread -> read, read -> acted, read -> dismissed.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    new_state = body.get("state")
    valid_states = {"unread", "read", "acted", "dismissed"}
    if new_state not in valid_states:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state: {new_state}. Valid: {', '.join(sorted(valid_states))}",
        )

    notification_iri = f"urn:sempkm:inbox:{notification_id}"

    # SPARQL UPDATE to change the notification state
    sparql = f"""
    DELETE {{
      GRAPH <{notification_iri}> {{
        ?notif <{SEMPKM}notificationState> ?oldState .
      }}
    }}
    INSERT {{
      GRAPH <{notification_iri}> {{
        ?notif <{SEMPKM}notificationState> "{_escape_sparql_string(new_state)}" .
      }}
    }}
    WHERE {{
      GRAPH <{notification_iri}> {{
        ?notif <{SEMPKM}notificationState> ?oldState .
      }}
    }}
    """

    try:
        await client.update(sparql)
    except Exception as e:
        logger.error("Failed to update notification %s: %s", notification_iri, e)
        raise HTTPException(status_code=500, detail="Failed to update notification state")

    return JSONResponse(
        content={"id": notification_id, "state": new_state},
        status_code=200,
    )


def _escape_sparql_string(value: str) -> str:
    """Escape a string for use in SPARQL string literals."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
