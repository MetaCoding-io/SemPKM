"""WebDAV write path: body parsing and event store bridge.

Public functions:

  parse_dav_put_body(raw_bytes) -> str
      Strip YAML frontmatter from the PUT body and return the Markdown content.

  write_body_via_event_store(object_iri, body, event_store, user_iri, user_role)
      Bridge the sync wsgidav WSGI thread to the async EventStore.commit()
      for body.set operations.

  write_properties_via_event_store(object_iri, properties, event_store, ...)
      Bridge sync context to async object.patch commit for property changes.

  _frontmatter_to_rdf_properties(new_fm, old_fm, shapes)
      Diff frontmatter dicts and map changed values back to predicate IRIs.

Called from ResourceFile.write_data() and MountedResourceFile.end_write().
"""

from __future__ import annotations

import asyncio
from typing import Any


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


# ── Property write-back (mount frontmatter edits) ────────────────────


async def _commit_property_patch(
    object_iri: str,
    properties: dict[str, Any],
    event_store,
    user_iri_str: str | None,
    user_role: str,
) -> None:
    """Async inner: build object.patch operation and commit via event store."""
    from rdflib import URIRef

    from app.commands.handlers.object_patch import handle_object_patch
    from app.commands.schemas import ObjectPatchParams
    from app.config import settings

    params = ObjectPatchParams(iri=object_iri, properties=properties)
    operation = await handle_object_patch(params, settings.base_namespace)
    user_iri = URIRef(user_iri_str) if user_iri_str else None
    await event_store.commit(
        [operation], performed_by=user_iri, performed_by_role=user_role
    )


def write_properties_via_event_store(
    object_iri: str,
    properties: dict[str, Any],
    event_store,
    user_iri: str | None = None,
    user_role: str = "member",
) -> None:
    """Bridge sync wsgidav context to async object.patch commit.

    Args:
        object_iri: Full IRI string of the RDF object being updated.
        properties: Dict mapping predicate IRI -> new value.
        event_store: AsyncEventStore instance from app.state.
        user_iri: Optional user URN for event provenance.
        user_role: Role string for event provenance.
    """
    asyncio.run(
        _commit_property_patch(
            object_iri, properties, event_store, user_iri, user_role
        )
    )


def _frontmatter_to_rdf_properties(
    new_fm: dict,
    old_fm: dict,
    shapes: list,
) -> dict[str, Any]:
    """Diff new vs old frontmatter and map changed values back to predicate IRIs.

    For each SHACL shape, compares the frontmatter value under its sh:name key.
    Only includes predicates whose values actually changed. Skips system keys
    (object_iri, type_iri) and body predicates.

    Object references ({label, iri} dicts) are converted back to IRI strings.

    Args:
        new_fm: New frontmatter dict from PUT body.
        old_fm: Current frontmatter dict from rendered state.
        shapes: List of PropertyShape instances for the object's type.

    Returns:
        Dict mapping predicate IRI -> new value suitable for ObjectPatchParams.
    """
    from app.vfs.mount_resource import _SYSTEM_KEYS, _BODY_LOCAL_NAMES, _safe_fm_key

    changed: dict[str, Any] = {}

    for shape in shapes:
        pred_local = (
            shape.path.rsplit("/", 1)[-1]
            .rsplit("#", 1)[-1]
            .rsplit(":", 1)[-1]
        )
        if pred_local in _BODY_LOCAL_NAMES:
            continue

        key = _safe_fm_key(shape.name)

        old_val = old_fm.get(key)
        new_val = new_fm.get(key)

        # Normalize None / missing to comparable form
        if old_val is None and new_val is None:
            continue
        if old_val == new_val:
            continue

        # Convert value for ObjectPatchParams
        converted = _convert_fm_value(new_val, shape)
        changed[shape.path] = converted

    return changed


def _convert_fm_value(value: Any, shape) -> Any:
    """Convert a frontmatter value to a form suitable for object.patch.

    - {label, iri} dicts -> IRI string
    - Lists of dicts -> lists of IRI strings
    - None -> empty string (clears the property)
    - Other values -> pass through as-is
    """
    if value is None:
        return ""

    if isinstance(value, dict):
        # Object reference: extract IRI
        if "iri" in value:
            return value["iri"]
        return str(value)

    if isinstance(value, list):
        return [_convert_fm_value(v, shape) for v in value]

    return value
