"""Comments sub-router — CRUD endpoints for threaded object comments.

Comments are first-class RDF resources stored in urn:sempkm:current
via EventStore operations. Flat SPARQL retrieval + Python tree assembly
for threaded display. Soft-delete replaces body with "[deleted]" and
removes author, preserving thread structure.
"""

import logging
from datetime import datetime, timezone
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from rdflib import Literal, URIRef, Variable
from rdflib.namespace import RDF, XSD
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.models import User
from app.config import settings
from app.db.session import get_db_session
from app.dependencies import get_event_store, get_triplestore_client
from app.events.store import EventStore, Operation
from app.rdf.iri import mint_object_iri
from app.rdf.namespaces import SEMPKM
from app.triplestore.client import TriplestoreClient

from ._helpers import _validate_iri

logger = logging.getLogger(__name__)

comments_router = APIRouter(tags=["comments"])


# ── Helper functions ─────────────────────────────────────────────────


def _relative_time(iso_timestamp: str) -> str:
    """Convert an ISO-8601 timestamp to a human-readable relative string.

    Returns strings like "just now", "2 minutes ago", "3 hours ago",
    "yesterday", "5 days ago", "2 weeks ago", "3 months ago", "1 year ago".
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - dt

        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        if days == 1:
            return "yesterday"
        if days < 14:
            return f"{days} days ago"
        weeks = days // 7
        if weeks < 8:
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        months = days // 30
        if months < 12:
            return f"{months} month{'s' if months != 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    except (ValueError, TypeError):
        return iso_timestamp


def _add_relative_times(comments: list[dict]) -> None:
    """Recursively add 'relative_time' to each comment in the tree."""
    for comment in comments:
        comment["relative_time"] = _relative_time(comment.get("timestamp", ""))
        if comment.get("replies"):
            _add_relative_times(comment["replies"])


def _add_can_delete(comments: list[dict], current_user_uri: str, user_role: str) -> None:
    """Recursively add 'can_delete' flag to each comment in the tree.

    A user can delete a comment if they are the author or have the 'owner' role.
    Deleted comments (body == '[deleted]') cannot be deleted again.
    """
    for comment in comments:
        is_deleted = comment.get("body") == "[deleted]"
        is_author = comment.get("author") == current_user_uri
        is_owner = user_role == "owner"
        comment["can_delete"] = (not is_deleted) and (is_author or is_owner)
        if comment.get("replies"):
            _add_can_delete(comment["replies"], current_user_uri, user_role)


def _build_comment_create_operation(
    comment_iri: str,
    object_iri: str,
    body: str,
    author_uri: URIRef,
    reply_to: str | None = None,
) -> Operation:
    """Build an EventStore Operation for creating a comment.

    Produces triples for rdf:type sempkm:Comment, sempkm:commentOn,
    sempkm:commentBody, sempkm:commentedBy, sempkm:commentedAt,
    and optional sempkm:replyTo.

    Args:
        comment_iri: The minted IRI for the new comment.
        object_iri: The IRI of the object being commented on.
        body: The comment text.
        author_uri: URIRef for the comment author (urn:sempkm:user:{uuid}).
        reply_to: Optional IRI of the parent comment for threading.

    Returns:
        Operation with comment.create type and full triples.
    """
    comment = URIRef(comment_iri)
    now = Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)

    triples: list[tuple] = [
        (comment, RDF.type, SEMPKM.Comment),
        (comment, SEMPKM.commentOn, URIRef(object_iri)),
        (comment, SEMPKM.commentBody, Literal(body)),
        (comment, SEMPKM.commentedBy, author_uri),
        (comment, SEMPKM.commentedAt, now),
    ]

    if reply_to:
        triples.append((comment, SEMPKM.replyTo, URIRef(reply_to)))

    affected = [comment_iri, object_iri]
    if reply_to:
        affected.append(reply_to)

    return Operation(
        operation_type="comment.create",
        affected_iris=affected,
        description=f"Created comment on {object_iri}",
        data_triples=triples,
        materialize_inserts=triples,
        materialize_deletes=[],
    )


def _build_comment_delete_operation(
    comment_iri: str,
    old_body: str,
    old_author: str,
) -> Operation:
    """Build an EventStore Operation for soft-deleting a comment.

    Replaces the comment body with "[deleted]" and removes the author
    triple. Thread structure (replyTo) is preserved.

    Args:
        comment_iri: IRI of the comment to soft-delete.
        old_body: The current body text to be removed.
        old_author: The current author URI string to be removed.

    Returns:
        Operation with comment.delete type, deletes for old body/author,
        insert for "[deleted]" body.
    """
    comment = URIRef(comment_iri)

    return Operation(
        operation_type="comment.delete",
        affected_iris=[comment_iri],
        description=f"Soft-deleted comment {comment_iri}",
        data_triples=[
            (comment, SEMPKM.commentBody, Literal("[deleted]")),
        ],
        materialize_inserts=[
            (comment, SEMPKM.commentBody, Literal("[deleted]")),
        ],
        materialize_deletes=[
            (comment, SEMPKM.commentBody, Literal(old_body)),
            (comment, SEMPKM.commentedBy, URIRef(old_author)),
        ],
    )


def _build_comment_tree(
    flat_comments: list[dict],
) -> list[dict]:
    """Assemble a flat list of comments into a threaded tree.

    Root comments (no reply_to) are top-level. Children are grouped
    under their parent's 'replies' list. Each level is sorted by
    timestamp ascending.

    Args:
        flat_comments: List of dicts with keys: iri, body, author,
            author_name (optional), timestamp, reply_to (None for roots).

    Returns:
        List of root comment dicts, each with a 'replies' list
        (recursively nested).
    """
    if not flat_comments:
        return []

    # Index by IRI for O(1) lookup
    by_iri: dict[str, dict] = {}
    for comment in flat_comments:
        comment["replies"] = []
        by_iri[comment["iri"]] = comment

    roots: list[dict] = []
    for comment in flat_comments:
        parent_iri = comment.get("reply_to")
        if parent_iri and parent_iri in by_iri:
            by_iri[parent_iri]["replies"].append(comment)
        else:
            # Root comment or orphaned reply (parent missing) → treat as root
            roots.append(comment)

    # Sort each level by timestamp ascending
    def _sort_level(comments: list[dict]) -> None:
        comments.sort(key=lambda c: c.get("timestamp", ""))
        for c in comments:
            if c["replies"]:
                _sort_level(c["replies"])

    _sort_level(roots)
    return roots


# ── Endpoints ────────────────────────────────────────────────────────


@comments_router.get("/object/{object_iri:path}/comments")
async def get_comments(
    request: Request,
    object_iri: str,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Retrieve threaded comments for an object as an HTML partial.

    SPARQL-fetches all comments on the object, resolves author display
    names from the SQL users table, assembles the thread tree, and
    renders the comments_section.html partial.
    """
    decoded_iri = unquote(object_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid IRI")

    # Fetch all comments for this object from the current state graph
    sparql = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX sempkm: <{SEMPKM}>

    SELECT ?comment ?body ?author ?timestamp ?replyTo
    FROM <urn:sempkm:current>
    WHERE {{
        ?comment rdf:type sempkm:Comment .
        ?comment sempkm:commentOn <{decoded_iri}> .
        ?comment sempkm:commentBody ?body .
        ?comment sempkm:commentedAt ?timestamp .
        OPTIONAL {{ ?comment sempkm:commentedBy ?author . }}
        OPTIONAL {{ ?comment sempkm:replyTo ?replyTo . }}
    }}
    ORDER BY ?timestamp
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.warning(
            "Failed to query comments for object %s", decoded_iri, exc_info=True
        )
        bindings = []

    # Parse bindings into flat comment dicts
    flat_comments: list[dict] = []
    author_uris: set[str] = set()

    for b in bindings:
        author_val = b.get("author", {}).get("value")
        comment = {
            "iri": b["comment"]["value"],
            "body": b["body"]["value"],
            "author": author_val,
            "timestamp": b["timestamp"]["value"],
            "reply_to": b.get("replyTo", {}).get("value"),
            "author_name": None,
        }
        flat_comments.append(comment)
        if author_val:
            author_uris.add(author_val)

    # Batch-resolve author display names from SQL users table
    if author_uris:
        # Extract UUIDs from urn:sempkm:user:{uuid} URIs
        uuid_to_uri: dict[str, str] = {}
        for uri in author_uris:
            prefix = "urn:sempkm:user:"
            if uri.startswith(prefix):
                user_uuid = uri[len(prefix):]
                uuid_to_uri[user_uuid] = uri

        if uuid_to_uri:
            # Single query to resolve all display names
            placeholders = ", ".join(f":uid_{i}" for i in range(len(uuid_to_uri)))
            query_str = f"SELECT id, display_name FROM users WHERE id IN ({placeholders})"
            params = {
                f"uid_{i}": uid for i, uid in enumerate(uuid_to_uri.keys())
            }
            db_result = await db.execute(text(query_str), params)
            rows = db_result.fetchall()

            # Build URI → display_name map
            uri_to_name: dict[str, str] = {}
            for row in rows:
                user_id_str = str(row[0])
                display_name = row[1]
                uri = uuid_to_uri.get(user_id_str)
                if uri and display_name:
                    uri_to_name[uri] = display_name

            # Apply display names to comments
            for comment in flat_comments:
                if comment["author"] and comment["author"] in uri_to_name:
                    comment["author_name"] = uri_to_name[comment["author"]]
                elif comment["author"]:
                    # Fallback: use the UUID portion of the URI
                    prefix = "urn:sempkm:user:"
                    if comment["author"].startswith(prefix):
                        comment["author_name"] = comment["author"][len(prefix):][:8]

    # Assemble thread tree and enrich with UI-computed fields
    tree = _build_comment_tree(flat_comments)
    _add_relative_times(tree)
    current_user_uri = f"urn:sempkm:user:{user.id}"
    _add_can_delete(tree, current_user_uri, user.role)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "browser/partials/comments_section.html",
        {
            "request": request,
            "comments": tree,
            "comment_count": len(flat_comments),
            "object_iri": decoded_iri,
            "current_user": user,
        },
    )


@comments_router.post("/object/{object_iri:path}/comments")
async def create_comment(
    request: Request,
    object_iri: str,
    body: str = Form(...),
    reply_to: str = Form(default=""),
    user: User = Depends(require_role("owner", "member")),
    event_store: EventStore = Depends(get_event_store),
) -> HTMLResponse:
    """Create a new comment on an object via EventStore.

    Mints a Comment IRI, builds the operation triples, and commits
    atomically. Returns HTML with HX-Trigger for comment list refresh.
    """
    decoded_iri = unquote(object_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid object IRI")

    reply_to_iri: str | None = reply_to if reply_to else None
    if reply_to_iri and not _validate_iri(reply_to_iri):
        raise HTTPException(status_code=400, detail="Invalid reply_to IRI")

    comment_iri = mint_object_iri(settings.base_namespace, "Comment")
    author_uri = URIRef(f"urn:sempkm:user:{user.id}")

    operation = _build_comment_create_operation(
        comment_iri=comment_iri,
        object_iri=decoded_iri,
        body=body,
        author_uri=author_uri,
        reply_to=reply_to_iri,
    )

    await event_store.commit(
        [operation], performed_by=author_uri, performed_by_role=user.role
    )

    logger.debug(
        "Comment created: comment_iri=%s, object_iri=%s, author=%s",
        comment_iri,
        decoded_iri,
        user.id,
    )

    response = HTMLResponse(
        content='<span class="comment-ok">Comment added</span>',
        status_code=200,
    )
    response.headers["HX-Trigger"] = "commentsRefreshed"
    return response


@comments_router.delete("/comments/{comment_iri:path}")
async def delete_comment(
    request: Request,
    comment_iri: str,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    event_store: EventStore = Depends(get_event_store),
) -> HTMLResponse:
    """Soft-delete a comment: replace body with '[deleted]', remove author.

    Fetches the current body and author via SPARQL, verifies the comment
    exists, then commits a soft-delete operation via EventStore.
    """
    decoded_iri = unquote(comment_iri)
    if not _validate_iri(decoded_iri):
        raise HTTPException(status_code=400, detail="Invalid comment IRI")

    # Fetch current comment data to build the delete operation
    sparql = f"""
    PREFIX sempkm: <{SEMPKM}>

    SELECT ?body ?author
    FROM <urn:sempkm:current>
    WHERE {{
        <{decoded_iri}> a sempkm:Comment .
        <{decoded_iri}> sempkm:commentBody ?body .
        OPTIONAL {{ <{decoded_iri}> sempkm:commentedBy ?author . }}
    }}
    """

    try:
        result = await client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
    except Exception:
        logger.error(
            "Failed to query comment %s for deletion", decoded_iri, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to query comment")

    if not bindings:
        raise HTTPException(status_code=404, detail="Comment not found")

    old_body = bindings[0]["body"]["value"]
    old_author = bindings[0].get("author", {}).get("value", "")

    # Don't re-delete already deleted comments
    if old_body == "[deleted]":
        raise HTTPException(status_code=400, detail="Comment already deleted")

    operation = _build_comment_delete_operation(
        comment_iri=decoded_iri,
        old_body=old_body,
        old_author=old_author,
    )

    author_uri = URIRef(f"urn:sempkm:user:{user.id}")
    await event_store.commit(
        [operation], performed_by=author_uri, performed_by_role=user.role
    )

    logger.debug(
        "Comment soft-deleted: comment_iri=%s, deleted_by=%s",
        decoded_iri,
        user.id,
    )

    response = HTMLResponse(
        content='<span class="comment-deleted">Comment deleted</span>',
        status_code=200,
    )
    response.headers["HX-Trigger"] = "commentsRefreshed"
    return response
