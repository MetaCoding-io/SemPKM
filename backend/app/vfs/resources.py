"""WebDAV resource rendering a single RDF object as Markdown+frontmatter.

Each object is presented as a .md file with YAML frontmatter containing
metadata (type IRI, object IRI, label, key properties) and a Markdown body
from the object's body predicate.
"""

import hashlib
import io

from wsgidav.dav_provider import DAVNonCollection

# Import after dav_provider to avoid circular import in wsgidav
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN

import frontmatter

from app.triplestore.sync_client import SyncTriplestoreClient


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
    """

    def __init__(
        self,
        path: str,
        environ: dict,
        client: SyncTriplestoreClient,
        model_id: str,
        type_label: str,
        filename: str,
    ) -> None:
        super().__init__(path, environ)
        self._client = client
        self._model_id = model_id
        self._type_label = type_label
        self._filename = filename
        self._cached_content: bytes | None = None

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
        """
        return hashlib.sha256(self._render()).hexdigest()

    def support_etag(self) -> bool:
        return True

    def support_content_length(self) -> bool:
        return True

    # Read-only enforcement
    def begin_write(self, *, content_type=None):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")
