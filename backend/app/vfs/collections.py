"""WebDAV collection classes for the VFS directory hierarchy.

Three levels of directory nesting:
  /                          -> RootCollection  (lists installed model IDs)
  /{model-id}/               -> ModelCollection (lists type labels in model)
  /{model-id}/{type-label}/  -> TypeCollection  (lists .md files per object)

All collections are read-only -- write operations raise HTTP 403 Forbidden.
"""

import hashlib
import re

from wsgidav.dav_provider import DAVCollection

# Import after dav_provider to avoid circular import in wsgidav
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN

from app.triplestore.sync_client import SyncTriplestoreClient
from app.vfs.cache import cached_get_member_names


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug.

    Lowercase, replace non-alphanumeric with hyphens, deduplicate hyphens,
    strip leading/trailing hyphens.
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


class RootCollection(DAVCollection):
    """Root directory listing installed mental model IDs.

    Path: /
    Children: one directory per installed model (e.g., "basic-pkm")
    """

    def __init__(
        self, path: str, environ: dict, client: SyncTriplestoreClient
    ) -> None:
        super().__init__(path, environ)
        self._client = client

    def get_member_names(self) -> list[str]:
        """Return list of installed model IDs plus mount directory names (cached)."""
        def _load():
            # Model directories
            result = self._client.query(
                """
                SELECT DISTINCT ?modelId FROM <urn:sempkm:models>
                WHERE {
                  ?model a <urn:sempkm:MentalModel> ;
                         <urn:sempkm:modelId> ?modelId .
                }
                """
            )
            names = [
                b["modelId"]["value"] for b in result["results"]["bindings"]
            ]

            # Mount directories
            from app.vfs.mount_service import SyncMountService
            user_iri = self.environ.get("sempkm.user_id", "")
            if user_iri and not user_iri.startswith("urn:"):
                user_iri = f"urn:sempkm:user:{user_iri}"
            mounts = SyncMountService(self._client).list_mounts(user_iri)
            for m in mounts:
                if m.path not in names:
                    names.append(m.path)

            return names

        return cached_get_member_names("root:models", _load)

    def get_member(self, name: str):
        """Return ModelCollection for a model ID, or MountRootCollection for a mount prefix."""
        member_path = f"{self.path.rstrip('/')}/{name}"

        # Check if this is a mount prefix
        from app.vfs.mount_service import SyncMountService
        mount = SyncMountService(self._client).get_mount_by_prefix(name)
        if mount is not None:
            from app.vfs.mount_collections import MountRootCollection
            return MountRootCollection(
                member_path, self.environ, self._client, mount,
            )

        return ModelCollection(member_path, self.environ, self._client, model_id=name)

    # Read-only enforcement
    def create_empty_resource(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def create_collection(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")


class ModelCollection(DAVCollection):
    """Directory listing type labels within a mental model.

    Path: /{model-id}/
    Children: one directory per type (e.g., "Note", "Person", "Project")
    """

    def __init__(
        self,
        path: str,
        environ: dict,
        client: SyncTriplestoreClient,
        model_id: str,
    ) -> None:
        super().__init__(path, environ)
        self._client = client
        self._model_id = model_id

    def get_member_names(self) -> list[str]:
        """Return list of type labels in this model (cached).

        Queries SHACL shapes from the model's shapes graph to find
        sh:targetClass values, extracts the local name as the type label.
        """
        model_id = self._model_id

        def _load():
            result = self._client.query(
                f"""
                PREFIX sh: <http://www.w3.org/ns/shacl#>
                SELECT DISTINCT ?typeLabel
                FROM <urn:sempkm:model:{model_id}:shapes>
                WHERE {{
                  ?shape sh:targetClass ?class .
                  BIND(REPLACE(STR(?class), ".*[/:#]", "") AS ?typeLabel)
                }}
                """
            )
            return [
                b["typeLabel"]["value"] for b in result["results"]["bindings"]
            ]

        return cached_get_member_names(f"model:{model_id}:types", _load)

    def get_member(self, name: str):
        """Return TypeCollection for a type label."""
        member_path = f"{self.path.rstrip('/')}/{name}"
        return TypeCollection(
            member_path,
            self.environ,
            self._client,
            model_id=self._model_id,
            type_label=name,
        )

    # Read-only enforcement
    def create_empty_resource(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def create_collection(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")


class TypeCollection(DAVCollection):
    """Directory listing objects of a specific type as .md files.

    Path: /{model-id}/{type-label}/
    Children: one .md file per object of this type

    Maintains a filename -> object mapping so ResourceFile can look up
    object metadata without re-querying SPARQL.
    """

    def __init__(
        self,
        path: str,
        environ: dict,
        client: SyncTriplestoreClient,
        model_id: str,
        type_label: str,
    ) -> None:
        super().__init__(path, environ)
        self._client = client
        self._model_id = model_id
        self._type_label = type_label
        self._file_map: dict[str, dict] | None = None

    def _resolve_type_iri(self) -> str:
        """Resolve the full type IRI from model namespace and type label.

        Queries the shapes graph to find the sh:targetClass whose local name
        matches the type label.
        """
        result = self._client.query(
            f"""
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT ?class FROM <urn:sempkm:model:{self._model_id}:shapes>
            WHERE {{
              ?shape sh:targetClass ?class .
              FILTER(REPLACE(STR(?class), ".*[/:#]", "") = "{self._type_label}")
            }}
            LIMIT 1
            """
        )
        bindings = result["results"]["bindings"]
        if bindings:
            return bindings[0]["class"]["value"]
        # Fallback: construct from model namespace convention
        return f"urn:sempkm:model:{self._model_id}:{self._type_label}"

    def _build_file_map(self) -> dict[str, dict]:
        """Build mapping of filename -> {iri, label, type_iri}.

        Queries objects of the resolved type from urn:sempkm:current,
        generates slugified filenames, and handles deduplication.
        """
        type_iri = self._resolve_type_iri()

        result = self._client.query(
            f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT ?iri ?label FROM <urn:sempkm:current>
            WHERE {{
              ?iri a <{type_iri}> .
              OPTIONAL {{ ?iri dcterms:title ?t }}
              OPTIONAL {{ ?iri rdfs:label ?r }}
              OPTIONAL {{ ?iri skos:prefLabel ?s }}
              OPTIONAL {{ ?iri foaf:name ?f }}
              BIND(COALESCE(?t, ?r, ?s, ?f, REPLACE(STR(?iri), ".*[/:#]", "")) AS ?label)
            }}
            ORDER BY ?label
            """
        )

        # First pass: generate slugs and detect duplicates
        entries = []
        slug_counts: dict[str, int] = {}
        for b in result["results"]["bindings"]:
            iri = b["iri"]["value"]
            label = b["label"]["value"]
            slug = _slugify(label)
            slug_counts[slug] = slug_counts.get(slug, 0) + 1
            entries.append({"iri": iri, "label": label, "slug": slug, "type_iri": type_iri})

        # Second pass: disambiguate duplicates with IRI hash suffix
        file_map: dict[str, dict] = {}
        seen_slugs: dict[str, int] = {}
        for entry in entries:
            slug = entry["slug"]
            if slug_counts[slug] > 1:
                # Append short hash of IRI for deduplication
                iri_hash = hashlib.sha256(entry["iri"].encode()).hexdigest()[:6]
                filename = f"{slug}--{iri_hash}.md"
            else:
                filename = f"{slug}.md"
            file_map[filename] = {
                "iri": entry["iri"],
                "label": entry["label"],
                "type_iri": entry["type_iri"],
            }

        return file_map

    def _ensure_file_map(self) -> dict[str, dict]:
        """Lazily build and cache the file map."""
        if self._file_map is None:
            self._file_map = self._build_file_map()
        return self._file_map

    def get_member_names(self) -> list[str]:
        """Return list of .md filenames for objects of this type (cached)."""
        cache_key = f"type:{self._model_id}:{self._type_label}"

        def _load():
            return list(self._ensure_file_map().keys())

        return cached_get_member_names(cache_key, _load)

    def get_member(self, name: str):
        """Return ResourceFile for a filename."""
        from app.vfs.resources import ResourceFile

        member_path = f"{self.path.rstrip('/')}/{name}"
        return ResourceFile(
            member_path,
            self.environ,
            self._client,
            model_id=self._model_id,
            type_label=self._type_label,
            filename=name,
        )

    def get_object_by_filename(self, filename: str) -> dict | None:
        """Return {"iri": ..., "label": ..., "type_iri": ...} or None."""
        return self._ensure_file_map().get(filename)

    # Read-only enforcement
    def create_empty_resource(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def create_collection(self, name: str):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_delete(self):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_move(self, dest_path):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")

    def handle_copy(self, dest_path, *, depth_infinity=None):
        raise DAVError(HTTP_FORBIDDEN, "Read-only filesystem")
