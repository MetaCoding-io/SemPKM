"""WebDAV resource rendering a single RDF object as Markdown+frontmatter.

Each object is presented as a .md file with YAML frontmatter containing
metadata (type IRI, object IRI, label, key properties) and a Markdown body
from the object's body predicate.

Write path (PUT):
  begin_write() returns a BytesIO buffer.
  end_write() reads the buffer, strips frontmatter, and commits body.set via EventStore.
  ETag concurrency (If-Match) is evaluated by wsgidav before begin_write() is called.
  DELETE/MOVE/COPY remain blocked with HTTP 403.
"""

import hashlib
import io
import logging

from wsgidav.dav_provider import DAVNonCollection

# Import after dav_provider to avoid circular import in wsgidav
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN

import frontmatter

from app.triplestore.sync_client import SyncTriplestoreClient

logger = logging.getLogger(__name__)


# Predicates to include in frontmatter with human-readable keys
_PREDICATE_LABELS: dict[str, str] = {
    "http://purl.org/dc/terms/title": "title",
    "http://www.w3.org/2000/01/rdf-schema#label": "rdfs_label",
    "http://www.w3.org/2004/02/skos/core#prefLabel": "pref_label",
    "http://xmlns.com/foaf/0.1/name": "name",
    "http://purl.org/dc/terms/description": "description",
    "https://schema.org/description": "schema_description",
    "http://purl.org/dc/terms/created": "created",
    "http://purl.org/dc/terms/modified": "modified",
    "https://schema.org/jobTitle": "job_title",
    "https://schema.org/worksFor": "works_for",
    "http://xmlns.com/foaf/0.1/mbox": "email",
}

# Predicates to skip in frontmatter (meta or handled separately)
_SKIP_PREDICATES = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
}


class ResourceFile(DAVNonCollection):
    """Renders a single RDF object as a Markdown file with YAML frontmatter.

    The file content is generated on first access and cached for the
    duration of the request (same instance).

    Write path:
    - begin_write() returns a BytesIO buffer for wsgidav to stream PUT body into.
    - end_write() parses the buffer, strips frontmatter, and commits body.set.
    - ETag-based concurrency (If-Match) is handled by wsgidav before begin_write().
    - DELETE/MOVE/COPY still raise HTTP 403 — only PUT body edits are supported.
    """

    def __init__(
        self,
        path: str,
        environ: dict,
        client: SyncTriplestoreClient,
        model_id: str,
        type_label: str,
        filename: str,
        event_store=None,
    ) -> None:
        super().__init__(path, environ)
        self._client = client
        self._model_id = model_id
        self._type_label = type_label
        self._filename = filename
        self._cached_content: bytes | None = None
        self._event_store = event_store
        # Buffer filled by begin_write/end_write cycle for PUT handling
        self._write_buffer: io.BytesIO | None = None

    def _get_object_info(self) -> dict | None:
        """Look up object metadata from the parent TypeCollection.

        Returns {"iri": ..., "label": ..., "type_iri": ...} or None.
        """
        from app.vfs.collections import TypeCollection

        # Reconstruct the parent TypeCollection to get the file map
        parent_path = "/".join(self.path.strip("/").split("/")[:-1])
        parent_path = "/" + parent_path if parent_path else "/"
        tc = TypeCollection(
            parent_path,
            self.environ,
            self._client,
            model_id=self._model_id,
            type_label=self._type_label,
        )
        return tc.get_object_by_filename(self._filename)

    def _render(self) -> bytes:
        """Render the object as Markdown+frontmatter bytes.

        Returns UTF-8 encoded content with YAML frontmatter block
        followed by Markdown body.
        """
        if self._cached_content is not None:
            return self._cached_content

        obj = self._get_object_info()
        if obj is None:
            self._cached_content = b"---\nerror: object not found\n---\n"
            return self._cached_content

        iri = obj["iri"]
        label = obj["label"]
        type_iri = obj["type_iri"]

        # Fetch all properties of the object
        result = self._client.query(
            f"""
            SELECT ?predicate ?object FROM <urn:sempkm:current>
            WHERE {{ <{iri}> ?predicate ?object . }}
            """
        )

        # Build frontmatter dict and extract body
        fm: dict = {
            "type_iri": type_iri,
            "object_iri": iri,
            "label": label,
        }

        body_text = ""
        extra_props: dict[str, str] = {}

        for b in result["results"]["bindings"]:
            pred = b["predicate"]["value"]
            obj_val = b["object"]["value"]

            # Skip rdf:type (already captured as type_iri)
            if pred in _SKIP_PREDICATES:
                continue

            # Check if this is a body predicate (ends with :body or /body)
            pred_local = pred.rsplit("/", 1)[-1].rsplit(":", 1)[-1]
            if pred_local == "body":
                body_text = obj_val
                continue

            # Map known predicates to human-readable keys
            if pred in _PREDICATE_LABELS:
                fm[_PREDICATE_LABELS[pred]] = obj_val
            else:
                # Use local name of predicate as key
                extra_props[pred_local] = obj_val

        # Add extra properties under a properties key to avoid cluttering top-level
        if extra_props:
            fm["properties"] = extra_props

        post = frontmatter.Post(content=body_text, **fm)
        self._cached_content = frontmatter.dumps(post).encode("utf-8")
        return self._cached_content

    def get_content_length(self) -> int:
        """Return byte length of rendered content."""
        return len(self._render())

    def get_content_type(self) -> str:
        """Return MIME type for Markdown files."""
        return "text/markdown; charset=utf-8"

    def get_content(self) -> io.BytesIO:
        """Return rendered content as a BytesIO stream."""
        return io.BytesIO(self._render())

    def get_etag(self) -> str:
        """Return SHA-256 hex of rendered content as ETag.

        wsgidav calls this automatically and includes the value in ETag
        response headers on GET and HEAD requests.

        ETag concurrency: wsgidav evaluates the If-Match header against this
        value before calling begin_write(). Stale ETags result in 412
        Precondition Failed without reaching our write path.
        """
        return hashlib.sha256(self._render()).hexdigest()

    def support_etag(self) -> bool:
        return True

    def support_content_length(self) -> bool:
        return True

    # --- Write path: PUT body edits only ---

    def begin_write(self, *, content_type=None) -> io.BytesIO:
        """Start a PUT write cycle. Returns a BytesIO buffer for wsgidav to fill.

        wsgidav streams the request body into the returned buffer. After streaming
        completes, wsgidav calls end_write() to commit the change.

        ETag concurrency (If-Match) has already been validated by wsgidav
        before this method is called — no manual check needed here.
        """
        self._write_buffer = io.BytesIO()
        return self._write_buffer

    def end_write(self, *, with_errors: bool) -> None:
        """Commit the buffered PUT body via the event store.

        Called by wsgidav after it has finished writing the request body
        into the buffer returned by begin_write().

        Strips YAML frontmatter from the PUT body (silently ignored).
        Only the Markdown body content is committed via body.set.
        """
        if with_errors or self._write_buffer is None:
            # Something went wrong during streaming — abandon the write
            self._write_buffer = None
            return

        from app.vfs.write import parse_dav_put_body, write_body_via_event_store

        raw_bytes = self._write_buffer.getvalue()
        self._write_buffer = None

        # Strip frontmatter; extract Markdown body only
        body = parse_dav_put_body(raw_bytes)

        # Look up the RDF IRI of this resource
        obj = self._get_object_info()
        if obj is None:
            logger.warning("ResourceFile.end_write: object not found for %s", self.path)
            return

        object_iri = obj["iri"]

        # Extract user context from WSGI environ (set by SemPKMWsgiAuthenticator)
        user_id = self.environ.get("sempkm.user_id")
        user_role = self.environ.get("sempkm.user_role", "member")
        # Build user URN for event provenance
        user_iri_str = f"urn:sempkm:user:{user_id}" if user_id else None

        if self._event_store is None:
            logger.error(
                "ResourceFile.end_write: event_store not wired — write to %s dropped",
                self.path,
            )
            return

        write_body_via_event_store(
            object_iri=object_iri,
            body=body,
            event_store=self._event_store,
            user_iri=user_iri_str,
            user_role=user_role,
        )

        # Invalidate cached content so subsequent GETs reflect the new body
        self._cached_content = None

        logger.info(
            "DAV PUT committed body.set for %s (user=%s)", object_iri, user_id
        )

    # --- Blocked operations: DELETE, MOVE, COPY remain read-only ---

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Delete not supported via WebDAV")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Move not supported via WebDAV")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Copy not supported via WebDAV")
