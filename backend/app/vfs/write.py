"""WebDAV write path: body parsing and event store bridge.

Two public functions:

  parse_dav_put_body(raw_bytes) -> str
      Strip YAML frontmatter from the PUT body and return the Markdown content.

  write_body_via_event_store(object_iri, body, event_store, user_iri, user_role)
      Bridge the sync wsgidav WSGI thread to the async EventStore.commit().

Called from ResourceFile.write_data() in provider resources.
"""

import asyncio


def parse_dav_put_body(raw_bytes: bytes) -> str:
    """Strip YAML frontmatter from PUT body bytes and return Markdown body.

    Logic:
    1. Decode bytes as UTF-8
    2. If content starts with '---' (with LF or CRLF), scan for closing '---'
    3. Everything after the closing delimiter (one leading newline stripped)
       is the body
    4. If no frontmatter delimiters found: return the entire content unchanged

    Args:
        raw_bytes: Raw bytes from the WebDAV PUT request body.

    Returns:
        Markdown body as a string (frontmatter stripped if present).
    """
    text = raw_bytes.decode("utf-8")

    # Check for frontmatter opening delimiter (--- on its own line)
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        return text

    # Find the closing '---' delimiter on its own line
    # Start searching after the opening delimiter
    search_start = text.index("\n") + 1  # skip past opening '---\n'
    closing_idx = -1

    for delimiter in ("---\r\n", "---\n"):
        idx = text.find("\n" + delimiter, search_start - 1)
        if idx != -1:
            # Position of the '\n' before '---'
            end_of_delimiter = idx + 1 + len(delimiter)
            if closing_idx == -1 or end_of_delimiter < closing_idx:
                closing_idx = end_of_delimiter

    if closing_idx == -1:
        # No closing delimiter found — treat entire content as body
        return text

    # Extract everything after the closing delimiter
    body = text[closing_idx:]

    # Strip exactly one leading newline that YAML frontmatter blocks
    # typically have between '---' and the first body line
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]

    return body


async def _commit_body_set(
    object_iri: str,
    body: str,
    event_store,
    user_iri_str: str | None,
    user_role: str,
) -> None:
    """Async inner: build body.set operation and commit via event store.

    Args:
        object_iri: Full IRI string of the RDF object being updated.
        body: Markdown body content (frontmatter already stripped).
        event_store: AsyncEventStore instance from app.state.
        user_iri_str: Optional URN string for the user (e.g. urn:sempkm:user:uuid).
        user_role: Role string ("owner", "member", or "guest").
    """
    from rdflib import URIRef

    from app.commands.handlers.body_set import handle_body_set
    from app.commands.schemas import BodySetParams
    from app.config import settings

    params = BodySetParams(iri=object_iri, body=body)
    operation = await handle_body_set(params, settings.base_namespace)
    user_iri = URIRef(user_iri_str) if user_iri_str else None
    await event_store.commit([operation], performed_by=user_iri, performed_by_role=user_role)


def write_body_via_event_store(
    object_iri: str,
    body: str,
    event_store,
    user_iri: str | None = None,
    user_role: str = "member",
) -> None:
    """Bridge sync wsgidav context to async EventStore.commit().

    Creates a new event loop in the current thread via asyncio.run() — safe in
    wsgidav WSGI thread pool where no event loop is running. Do NOT use
    asyncio.get_event_loop().run_until_complete() as that raises RuntimeError
    if a loop is already running in the main thread.

    Args:
        object_iri: Full IRI string of the RDF object being updated.
        body: Markdown body content (frontmatter already stripped).
        event_store: AsyncEventStore instance from app.state.
        user_iri: Optional user URN for event provenance (e.g. urn:sempkm:user:uuid).
        user_role: Role string for event provenance ("owner", "member", "guest").
    """
    asyncio.run(
        _commit_body_set(object_iri, body, event_store, user_iri, user_role)
    )
