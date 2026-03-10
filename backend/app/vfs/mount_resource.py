"""WebDAV resource for mounted objects with SHACL-aware frontmatter.

MountedResourceFile renders objects as Markdown files with YAML frontmatter
derived from SHACL property shapes. Unlike the base ResourceFile which uses
a hardcoded predicate-to-key map, this class discovers property names from
the model's SHACL shapes graph dynamically.

Write path:
  Frontmatter property changes are diffed against the original and committed
  via object.patch through the event store. Body changes use the existing
  write_body_via_event_store path.

ETag:
  Derived from object IRI (not content hash) so all paths to the same object
  share the same ETag. This enables cross-path concurrency control for
  multi-folder objects (e.g., same object in two tag folders).
"""

from __future__ import annotations

import hashlib
import io
import logging
import threading

from cachetools import TTLCache
from wsgidav.dav_provider import DAVNonCollection
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN

import frontmatter

from app.services.shapes import PropertyShape
from app.triplestore.sync_client import SyncTriplestoreClient

logger = logging.getLogger(__name__)

# ── SHACL shape cache ────────────────────────────────────────────────

_shape_cache: TTLCache = TTLCache(maxsize=32, ttl=300)
_shape_cache_lock = threading.Lock()

# System keys in frontmatter (not writable)
_SYSTEM_KEYS = {"object_iri", "type_iri"}

# Body predicate local names to extract as body text
_BODY_LOCAL_NAMES = {"body"}


def _get_shapes_for_type(
    type_iri: str, client: SyncTriplestoreClient
) -> list[PropertyShape]:
    """Get SHACL property shapes for a type, with TTL cache.

    Queries all urn:sempkm:model:*:shapes graphs to find the NodeShape
    targeting this type, then extracts its property shapes.
    """
    with _shape_cache_lock:
        if type_iri in _shape_cache:
            return _shape_cache[type_iri]

    # Query property shapes from all model shapes graphs
    sparql = f"""
PREFIX sh: <http://www.w3.org/ns/shacl#>
SELECT ?path ?name ?datatype ?targetClass ?order ?minCount ?maxCount
WHERE {{
  GRAPH ?g {{
    ?shape sh:targetClass <{type_iri}> ;
           sh:property ?propNode .
    ?propNode sh:path ?path .
    OPTIONAL {{ ?propNode sh:name ?name }}
    OPTIONAL {{ ?propNode sh:datatype ?datatype }}
    OPTIONAL {{ ?propNode sh:class ?targetClass }}
    OPTIONAL {{ ?propNode sh:order ?order }}
    OPTIONAL {{ ?propNode sh:minCount ?minCount }}
    OPTIONAL {{ ?propNode sh:maxCount ?maxCount }}
  }}
  FILTER(STRSTARTS(STR(?g), "urn:sempkm:model:") && STRENDS(STR(?g), ":shapes"))
}}
ORDER BY ?order
"""
    result = client.query(sparql)
    shapes: list[PropertyShape] = []
    for b in result["results"]["bindings"]:
        path = b["path"]["value"]
        # Derive name: sh:name or local name from path IRI
        if "name" in b and b["name"].get("value"):
            name = b["name"]["value"]
        else:
            name = path.rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]

        datatype = b.get("datatype", {}).get("value")
        target_class = b.get("targetClass", {}).get("value")

        try:
            order = float(b["order"]["value"]) if "order" in b else 0.0
        except (ValueError, TypeError):
            order = 0.0

        try:
            min_count = int(b["minCount"]["value"]) if "minCount" in b else 0
        except (ValueError, TypeError):
            min_count = 0

        try:
            max_count = int(b["maxCount"]["value"]) if "maxCount" in b else None
        except (ValueError, TypeError):
            max_count = None

        shapes.append(PropertyShape(
            path=path,
            name=name,
            datatype=datatype,
            target_class=target_class,
            order=order,
            min_count=min_count,
            max_count=max_count,
        ))

    # Sort by order
    shapes.sort(key=lambda s: s.order)

    with _shape_cache_lock:
        _shape_cache[type_iri] = shapes

    return shapes


def _safe_fm_key(name: str) -> str:
    """Ensure frontmatter key does not collide with system keys."""
    if name in _SYSTEM_KEYS:
        return f"_{name}"
    return name


def _resolve_labels_for_iris(
    iris: list[str], client: SyncTriplestoreClient
) -> dict[str, str]:
    """Batch-resolve labels for a list of IRIs."""
    if not iris:
        return {}
    values = " ".join(f"<{iri}>" for iri in iris)
    sparql = f"""
SELECT ?iri ?label
FROM <urn:sempkm:current>
WHERE {{
  VALUES ?iri {{ {values} }}
  OPTIONAL {{ ?iri <http://purl.org/dc/terms/title> ?t }}
  OPTIONAL {{ ?iri <http://www.w3.org/2000/01/rdf-schema#label> ?r }}
  OPTIONAL {{ ?iri <http://www.w3.org/2004/02/skos/core#prefLabel> ?s }}
  OPTIONAL {{ ?iri <http://xmlns.com/foaf/0.1/name> ?f }}
  BIND(COALESCE(?t, ?r, ?s, ?f, REPLACE(STR(?iri), ".*[/:#]", "")) AS ?label)
}}
"""
    result = client.query(sparql)
    labels: dict[str, str] = {}
    for b in result["results"]["bindings"]:
        labels[b["iri"]["value"]] = b["label"]["value"]
    return labels


class MountedResourceFile(DAVNonCollection):
    """Renders a mounted RDF object as Markdown with SHACL-aware frontmatter.

    Unlike ResourceFile which uses a hardcoded predicate map, this class
    builds frontmatter keys from SHACL shape metadata (sh:name).

    Object references are rendered as {label, iri} dicts per CONTEXT.md.
    """

    def __init__(
        self,
        path: str,
        environ: dict,
        client: SyncTriplestoreClient,
        object_iri: str,
        object_label: str,
        type_iri: str,
        event_store=None,
    ) -> None:
        super().__init__(path, environ)
        self._client = client
        self._object_iri = object_iri
        self._object_label = object_label
        self._type_iri = type_iri
        self._event_store = event_store
        self._cached_content: bytes | None = None
        self._write_buffer: io.BytesIO | None = None

    def _render_shacl_frontmatter(self) -> tuple[dict, str]:
        """Build frontmatter dict and body text from SHACL shapes.

        Returns:
            (frontmatter_dict, body_text)
        """
        iri = self._object_iri

        # Fetch all triples for this object
        result = self._client.query(
            f"""
            SELECT ?p ?o FROM <urn:sempkm:current>
            WHERE {{ <{iri}> ?p ?o . }}
            """
        )

        # Group values by predicate
        pred_values: dict[str, list[dict]] = {}
        for b in result["results"]["bindings"]:
            pred = b["p"]["value"]
            obj = b["o"]
            pred_values.setdefault(pred, []).append(obj)

        # Get SHACL shapes for this type
        shapes = _get_shapes_for_type(self._type_iri, self._client)

        # System keys
        fm: dict = {
            "object_iri": iri,
            "type_iri": self._type_iri,
        }

        body_text = ""

        # Collect IRIs that need label resolution
        iris_needing_labels: list[str] = []
        for shape in shapes:
            if shape.target_class:
                values = pred_values.get(shape.path, [])
                for v in values:
                    if v.get("type") == "uri":
                        iris_needing_labels.append(v["value"])

        # Batch resolve labels
        label_map = _resolve_labels_for_iris(iris_needing_labels, self._client)

        # Build frontmatter from shapes
        for shape in shapes:
            pred_local = shape.path.rsplit("/", 1)[-1].rsplit("#", 1)[-1].rsplit(":", 1)[-1]

            # Skip body predicates
            if pred_local in _BODY_LOCAL_NAMES:
                values = pred_values.get(shape.path, [])
                if values:
                    body_text = values[0]["value"]
                continue

            values = pred_values.get(shape.path, [])
            if not values:
                continue

            key = _safe_fm_key(shape.name)

            if shape.target_class:
                # Object reference: render as {label, iri} dict
                ref_values = []
                for v in values:
                    v_val = v["value"]
                    if v.get("type") == "uri":
                        label = label_map.get(v_val, v_val.rsplit("/", 1)[-1])
                        ref_values.append({"label": label, "iri": v_val})
                    else:
                        ref_values.append(v_val)

                if shape.max_count == 1 and len(ref_values) == 1:
                    fm[key] = ref_values[0]
                else:
                    fm[key] = ref_values
            else:
                # Literal values
                str_values = [v["value"] for v in values]
                if shape.max_count == 1 and len(str_values) == 1:
                    fm[key] = str_values[0]
                else:
                    fm[key] = str_values

        return fm, body_text

    def _render(self) -> bytes:
        """Render object as Markdown+frontmatter bytes."""
        if self._cached_content is not None:
            return self._cached_content

        fm, body_text = self._render_shacl_frontmatter()
        post = frontmatter.Post(content=body_text, **fm)
        self._cached_content = frontmatter.dumps(post).encode("utf-8")
        return self._cached_content

    def get_content_length(self) -> int:
        return len(self._render())

    def get_content_type(self) -> str:
        return "text/markdown; charset=utf-8"

    def get_content(self) -> io.BytesIO:
        return io.BytesIO(self._render())

    def get_etag(self) -> str:
        """Return ETag derived from object IRI (not content).

        All paths to the same object share the same ETag, enabling
        cross-path concurrency control for multi-folder objects.
        """
        return hashlib.sha256(self._object_iri.encode()).hexdigest()

    def support_etag(self) -> bool:
        return True

    def support_content_length(self) -> bool:
        return True

    # --- Write path ---

    def begin_write(self, *, content_type=None) -> io.BytesIO:
        """Start PUT write cycle."""
        self._write_buffer = io.BytesIO()
        return self._write_buffer

    def end_write(self, *, with_errors: bool) -> None:
        """Commit PUT body: diff frontmatter and write changes.

        Compares old vs new frontmatter to identify changed properties,
        then commits via object.patch for property changes and body.set
        for body changes.
        """
        if with_errors or self._write_buffer is None:
            self._write_buffer = None
            return

        raw_bytes = self._write_buffer.getvalue()
        self._write_buffer = None

        try:
            new_post = frontmatter.loads(raw_bytes.decode("utf-8"))
        except Exception:
            logger.warning(
                "MountedResourceFile.end_write: failed to parse frontmatter for %s",
                self.path,
            )
            return

        new_fm = dict(new_post.metadata)
        new_body = new_post.content

        # Get current state for diffing
        old_fm, old_body = self._render_shacl_frontmatter()
        shapes = _get_shapes_for_type(self._type_iri, self._client)

        # Extract user context
        user_id = self.environ.get("sempkm.user_id")
        user_role = self.environ.get("sempkm.user_role", "member")
        user_iri_str = f"urn:sempkm:user:{user_id}" if user_id else None

        if self._event_store is None:
            logger.error(
                "MountedResourceFile.end_write: event_store not wired for %s",
                self.path,
            )
            return

        # Diff and write properties
        from app.vfs.write import (
            write_body_via_event_store,
            write_properties_via_event_store,
            _frontmatter_to_rdf_properties,
        )

        changed_props = _frontmatter_to_rdf_properties(new_fm, old_fm, shapes)
        if changed_props:
            write_properties_via_event_store(
                object_iri=self._object_iri,
                properties=changed_props,
                event_store=self._event_store,
                user_iri=user_iri_str,
                user_role=user_role,
            )
            logger.info(
                "DAV PUT committed property patch for %s (props=%s, user=%s)",
                self._object_iri,
                list(changed_props.keys()),
                user_id,
            )

        # Diff and write body
        if new_body != old_body:
            write_body_via_event_store(
                object_iri=self._object_iri,
                body=new_body,
                event_store=self._event_store,
                user_iri=user_iri_str,
                user_role=user_role,
            )
            logger.info(
                "DAV PUT committed body.set for %s (user=%s)",
                self._object_iri,
                user_id,
            )

        # Invalidate cached content
        self._cached_content = None

    # --- Blocked operations ---

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Delete not supported via WebDAV")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Move not supported via WebDAV")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Copy not supported via WebDAV")
