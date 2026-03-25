"""MountSpec CRUD service for managing mount definitions stored as RDF.

Mount definitions are RDF resources in the urn:sempkm:mounts named graph.
Each mount specifies a directory strategy (flat, by-type, by-date, by-tag,
by-property) and optional scope filtering via saved SPARQL queries.

Uses SyncTriplestoreClient for WebDAV (WSGI) thread compatibility.
The async mount router uses TriplestoreClient directly with the same
SPARQL query patterns.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.sparql.builder import safe_iri, sparql_escape_string

from app.triplestore.sync_client import SyncTriplestoreClient

# ── RDF Vocabulary Constants ────────────────────────────────────────

NS_SEMPKM = "urn:sempkm:"
NS_MOUNT = "urn:sempkm:mount:"
GRAPH_MOUNTS = "urn:sempkm:mounts"

# Predicate IRIs for MountSpec properties
MOUNT_NAME = f"{NS_SEMPKM}mountName"
MOUNT_PATH = f"{NS_SEMPKM}mountPath"
DIRECTORY_STRATEGY = f"{NS_SEMPKM}directoryStrategy"
GROUP_BY_PROPERTY = f"{NS_SEMPKM}groupByProperty"
DATE_PROPERTY = f"{NS_SEMPKM}dateProperty"
SPARQL_SCOPE = f"{NS_SEMPKM}sparqlScope"
SCOPE_QUERY = f"{NS_SEMPKM}scopeQuery"
TYPE_FILTER = f"{NS_SEMPKM}typeFilter"
FILENAME_TEMPLATE = f"{NS_SEMPKM}filenameTemplate"
CREATED_BY = f"{NS_SEMPKM}createdBy"
VISIBILITY = f"{NS_SEMPKM}visibility"
CREATED_AT = f"{NS_SEMPKM}createdAt"

# Valid strategies
VALID_STRATEGIES = {"flat", "by-type", "by-date", "by-tag", "by-property"}

# Path validation regex: lowercase letters, digits, hyphens; must start with letter or digit
_PATH_REGEX = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Reserved path names that cannot be used as mount prefixes
_RESERVED_PATHS = {"_uncategorized"}


# ── Data Class ──────────────────────────────────────────────────────

@dataclass
class MountDefinition:
    """Represents a single mount definition."""

    id: str  # UUID string
    name: str
    path: str  # URL-safe prefix for the mount directory
    strategy: str  # one of VALID_STRATEGIES
    group_by_property: str | None = None
    date_property: str | None = None
    sparql_scope: str = "all"
    scope_query: str | None = None
    type_filter: list[str] | None = None
    filename_template: str | None = None
    created_by: str = ""  # user URN (urn:sempkm:user:{uuid})
    visibility: str = "personal"  # "shared" or "personal"
    created_at: str = ""  # ISO datetime string

    @property
    def strategy_chain(self) -> list[str]:
        """Parse strategy into ordered list. Single = ['by-tag'], chain = ['by-tag', 'by-date']."""
        return self.strategy.split("|")

    @property
    def is_chain(self) -> bool:
        """True if strategy is a multi-level chain."""
        return "|" in self.strategy

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        result = {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "strategy": self.strategy,
            "group_by_property": self.group_by_property,
            "date_property": self.date_property,
            "sparql_scope": self.sparql_scope,
            "scope_query": self.scope_query,
            "type_filter": self.type_filter,
            "filename_template": self.filename_template,
            "created_by": self.created_by,
            "visibility": self.visibility,
            "created_at": self.created_at,
        }
        chain = self.strategy_chain
        if len(chain) > 1:
            result["strategy_chain"] = chain
        return result


# ── Chain Validation Helper ──────────────────────────────────────────

def _validate_strategy_chain(strategy: str) -> None:
    """Validate a strategy string, including pipe-delimited chains.

    Rules:
    - Each segment must be a valid strategy name
    - Maximum 3 levels in a chain
    - No empty segments

    Raises ValueError with a descriptive message on failure.
    """
    segments = strategy.split("|")
    if len(segments) > 3:
        raise ValueError(
            f"Strategy chain too long ({len(segments)} levels). "
            f"Maximum is 3 levels. Got: '{strategy}'"
        )
    for i, seg in enumerate(segments):
        seg = seg.strip()
        if not seg:
            raise ValueError(
                f"Empty strategy segment at position {i + 1} in chain '{strategy}'."
            )
        if seg not in VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{seg}' at position {i + 1} in chain '{strategy}'. "
                f"Must be one of: {', '.join(sorted(VALID_STRATEGIES))}"
            )


# ── Path Validation Helper ───────────────────────────────────────────

def _validate_mount_path(
    path: str,
    client: SyncTriplestoreClient,
    exclude_id: str | None = None,
) -> None:
    """Validate a mount path prefix.

    Checks:
    1. Regex: must match [a-z0-9][a-z0-9-]*
    2. Reserved names: reject _uncategorized and dot-prefixed names
    3. Model conflict: reject if path matches any installed model ID
    4. Uniqueness: reject if another mount already uses this path

    Raises ValueError with a descriptive message on failure.
    """
    # 1. Regex check
    if not _PATH_REGEX.match(path):
        raise ValueError(
            f"Mount path '{path}' is invalid. "
            "Use only lowercase letters, digits, and hyphens. "
            "Must start with a letter or digit."
        )

    # 2. Reserved names
    if path in _RESERVED_PATHS or path.startswith("."):
        raise ValueError(f"Mount path '{path}' is reserved and cannot be used.")

    # 3. Model conflict check: query installed model IDs
    result = client.query(
        """
        SELECT DISTINCT ?modelId FROM <urn:sempkm:models>
        WHERE {
          ?model a <urn:sempkm:MentalModel> ;
                 <urn:sempkm:modelId> ?modelId .
        }
        """
    )
    model_ids = {b["modelId"]["value"] for b in result["results"]["bindings"]}
    if path in model_ids:
        raise ValueError(
            f"Mount path '{path}' conflicts with installed model '{path}'. "
            "Choose a different path prefix."
        )

    # 4. Uniqueness check: query existing mounts for same path
    exclude_filter = ""
    if exclude_id:
        exclude_filter = f"FILTER(?mount != <{NS_MOUNT}{exclude_id}>)"
    result = client.query(
        f"""
        SELECT ?mount FROM <{GRAPH_MOUNTS}>
        WHERE {{
          ?mount <{MOUNT_PATH}> "{path}" .
          {exclude_filter}
        }}
        LIMIT 1
        """
    )
    if result["results"]["bindings"]:
        raise ValueError(
            f"Mount path '{path}' is already in use by another mount."
        )


# ── Sync Mount Service ──────────────────────────────────────────────

class SyncMountService:
    """Synchronous CRUD operations for mount definitions in the triplestore.

    All methods use SyncTriplestoreClient for WSGI thread compatibility.
    """

    def __init__(self, client: SyncTriplestoreClient) -> None:
        self._client = client

    def list_mounts(self, user_iri: str) -> list[MountDefinition]:
        """List all mounts visible to the given user.

        Returns shared mounts plus personal mounts owned by the user.
        """
        result = self._client.query(
            f"""
            SELECT ?mount ?name ?path ?strategy ?groupByProp ?dateProp
                   ?scope ?scopeQuery ?createdBy ?visibility ?createdAt
                   ?filenameTemplate
            FROM <{GRAPH_MOUNTS}>
            WHERE {{
              ?mount a <{NS_SEMPKM}MountSpec> ;
                     <{MOUNT_NAME}> ?name ;
                     <{MOUNT_PATH}> ?path ;
                     <{DIRECTORY_STRATEGY}> ?strategy ;
                     <{CREATED_BY}> ?createdBy ;
                     <{VISIBILITY}> ?visibility .
              OPTIONAL {{ ?mount <{GROUP_BY_PROPERTY}> ?groupByProp }}
              OPTIONAL {{ ?mount <{DATE_PROPERTY}> ?dateProp }}
              OPTIONAL {{ ?mount <{SPARQL_SCOPE}> ?scope }}
              OPTIONAL {{ ?mount <{SCOPE_QUERY}> ?scopeQuery }}
              OPTIONAL {{ ?mount <{CREATED_AT}> ?createdAt }}
              OPTIONAL {{ ?mount <{FILENAME_TEMPLATE}> ?filenameTemplate }}
              FILTER(
                ?visibility = "shared" ||
                ?createdBy = <{user_iri}>
              )
            }}
            ORDER BY ?name
            """
        )

        # Fetch type_filter triples for all mounts in one query
        tf_result = self._client.query(
            f"""
            SELECT ?mount ?tf
            FROM <{GRAPH_MOUNTS}>
            WHERE {{ ?mount <{TYPE_FILTER}> ?tf }}
            """
        )
        type_filters_map: dict[str, list[str]] = {}
        for tf_b in tf_result["results"]["bindings"]:
            m_iri = tf_b["mount"]["value"]
            type_filters_map.setdefault(m_iri, []).append(tf_b["tf"]["value"])

        mounts = []
        for b in result["results"]["bindings"]:
            mount = self._binding_to_mount(b)
            mount_iri = b["mount"]["value"]
            mount.type_filter = type_filters_map.get(mount_iri) or None
            mounts.append(mount)
        return mounts

    def get_mount_by_id(self, mount_id: str) -> MountDefinition | None:
        """Get a single mount definition by its UUID."""
        mount_iri = f"{NS_MOUNT}{mount_id}"
        result = self._client.query(
            f"""
            SELECT ?name ?path ?strategy ?groupByProp ?dateProp
                   ?scope ?scopeQuery ?createdBy ?visibility ?createdAt
                   ?filenameTemplate
                   (GROUP_CONCAT(DISTINCT ?tf; separator="|") AS ?typeFilters)
            FROM <{GRAPH_MOUNTS}>
            WHERE {{
              <{mount_iri}> a <{NS_SEMPKM}MountSpec> ;
                            <{MOUNT_NAME}> ?name ;
                            <{MOUNT_PATH}> ?path ;
                            <{DIRECTORY_STRATEGY}> ?strategy ;
                            <{CREATED_BY}> ?createdBy ;
                            <{VISIBILITY}> ?visibility .
              OPTIONAL {{ <{mount_iri}> <{GROUP_BY_PROPERTY}> ?groupByProp }}
              OPTIONAL {{ <{mount_iri}> <{DATE_PROPERTY}> ?dateProp }}
              OPTIONAL {{ <{mount_iri}> <{SPARQL_SCOPE}> ?scope }}
              OPTIONAL {{ <{mount_iri}> <{SCOPE_QUERY}> ?scopeQuery }}
              OPTIONAL {{ <{mount_iri}> <{CREATED_AT}> ?createdAt }}
              OPTIONAL {{ <{mount_iri}> <{TYPE_FILTER}> ?tf }}
              OPTIONAL {{ <{mount_iri}> <{FILENAME_TEMPLATE}> ?filenameTemplate }}
            }}
            GROUP BY ?name ?path ?strategy ?groupByProp ?dateProp
                     ?scope ?scopeQuery ?createdBy ?visibility ?createdAt
                     ?filenameTemplate
            LIMIT 1
            """
        )
        bindings = result["results"]["bindings"]
        if not bindings:
            return None

        b = bindings[0]
        tf_raw = b.get("typeFilters", {}).get("value", "")
        type_filter = [s for s in tf_raw.split("|") if s] or None
        return MountDefinition(
            id=mount_id,
            name=b["name"]["value"],
            path=b["path"]["value"],
            strategy=b["strategy"]["value"],
            group_by_property=b.get("groupByProp", {}).get("value"),
            date_property=b.get("dateProp", {}).get("value"),
            sparql_scope=b.get("scope", {}).get("value", "all"),
            scope_query=b.get("scopeQuery", {}).get("value"),
            type_filter=type_filter,
            filename_template=b.get("filenameTemplate", {}).get("value"),
            created_by=b["createdBy"]["value"],
            visibility=b["visibility"]["value"],
            created_at=b.get("createdAt", {}).get("value", ""),
        )

    def get_mount_by_prefix(self, prefix: str) -> MountDefinition | None:
        """Get a mount definition by its path prefix. Used by provider dispatch."""
        result = self._client.query(
            f"""
            SELECT ?mount ?name ?strategy ?groupByProp ?dateProp
                   ?scope ?scopeQuery ?createdBy ?visibility ?createdAt
                   ?filenameTemplate
                   (GROUP_CONCAT(DISTINCT ?tf; separator="|") AS ?typeFilters)
            FROM <{GRAPH_MOUNTS}>
            WHERE {{
              ?mount a <{NS_SEMPKM}MountSpec> ;
                     <{MOUNT_NAME}> ?name ;
                     <{MOUNT_PATH}> "{prefix}" ;
                     <{DIRECTORY_STRATEGY}> ?strategy ;
                     <{CREATED_BY}> ?createdBy ;
                     <{VISIBILITY}> ?visibility .
              OPTIONAL {{ ?mount <{GROUP_BY_PROPERTY}> ?groupByProp }}
              OPTIONAL {{ ?mount <{DATE_PROPERTY}> ?dateProp }}
              OPTIONAL {{ ?mount <{SPARQL_SCOPE}> ?scope }}
              OPTIONAL {{ ?mount <{SCOPE_QUERY}> ?scopeQuery }}
              OPTIONAL {{ ?mount <{CREATED_AT}> ?createdAt }}
              OPTIONAL {{ ?mount <{TYPE_FILTER}> ?tf }}
              OPTIONAL {{ ?mount <{FILENAME_TEMPLATE}> ?filenameTemplate }}
            }}
            GROUP BY ?mount ?name ?strategy ?groupByProp ?dateProp
                     ?scope ?scopeQuery ?createdBy ?visibility ?createdAt
                     ?filenameTemplate
            LIMIT 1
            """
        )
        bindings = result["results"]["bindings"]
        if not bindings:
            return None

        b = bindings[0]
        mount_iri = b["mount"]["value"]
        mount_id = mount_iri.replace(NS_MOUNT, "") if mount_iri.startswith(NS_MOUNT) else mount_iri
        tf_raw = b.get("typeFilters", {}).get("value", "")
        type_filter = [s for s in tf_raw.split("|") if s] or None
        return MountDefinition(
            id=mount_id,
            name=b["name"]["value"],
            path=prefix,
            strategy=b["strategy"]["value"],
            group_by_property=b.get("groupByProp", {}).get("value"),
            date_property=b.get("dateProp", {}).get("value"),
            sparql_scope=b.get("scope", {}).get("value", "all"),
            scope_query=b.get("scopeQuery", {}).get("value"),
            type_filter=type_filter,
            filename_template=b.get("filenameTemplate", {}).get("value"),
            created_by=b["createdBy"]["value"],
            visibility=b["visibility"]["value"],
            created_at=b.get("createdAt", {}).get("value", ""),
        )

    def create_mount(self, mount: MountDefinition) -> MountDefinition:
        """Create a new mount definition.

        Generates UUID and timestamp, validates path, and inserts RDF triples.
        Raises ValueError on validation failure.
        """
        # Generate ID and timestamp
        mount.id = str(uuid.uuid4())
        mount.created_at = datetime.now(UTC).isoformat()

        # Validate strategy (supports pipe-delimited chains)
        _validate_strategy_chain(mount.strategy)

        # Validate path
        _validate_mount_path(mount.path, self._client)

        # Build INSERT DATA
        mount_iri = f"{NS_MOUNT}{mount.id}"
        triples = [
            f'<{mount_iri}> a <{NS_SEMPKM}MountSpec>',
            f'<{mount_iri}> <{MOUNT_NAME}> "{sparql_escape_string(mount.name)}"',
            f'<{mount_iri}> <{MOUNT_PATH}> "{sparql_escape_string(mount.path)}"',
            f'<{mount_iri}> <{DIRECTORY_STRATEGY}> "{sparql_escape_string(mount.strategy)}"',
            f'<{mount_iri}> <{CREATED_BY}> <{mount.created_by}>',
            f'<{mount_iri}> <{VISIBILITY}> "{sparql_escape_string(mount.visibility)}"',
            f'<{mount_iri}> <{CREATED_AT}> "{sparql_escape_string(mount.created_at)}"^^<http://www.w3.org/2001/XMLSchema#dateTime>',
        ]
        if mount.group_by_property:
            triples.append(
                f'<{mount_iri}> <{GROUP_BY_PROPERTY}> {safe_iri(mount.group_by_property)}'
            )
        if mount.date_property:
            triples.append(
                f'<{mount_iri}> <{DATE_PROPERTY}> {safe_iri(mount.date_property)}'
            )
        if mount.sparql_scope and mount.sparql_scope != "all":
            triples.append(
                f'<{mount_iri}> <{SPARQL_SCOPE}> "{sparql_escape_string(mount.sparql_scope)}"'
            )
        if mount.scope_query:
            triples.append(
                f'<{mount_iri}> <{SCOPE_QUERY}> {safe_iri(mount.scope_query)}'
            )
        if mount.type_filter:
            for tf_iri in mount.type_filter:
                triples.append(
                    f'<{mount_iri}> <{TYPE_FILTER}> {safe_iri(tf_iri)}'
                )
        if mount.filename_template:
            triples.append(
                f'<{mount_iri}> <{FILENAME_TEMPLATE}> "{sparql_escape_string(mount.filename_template)}"'
            )

        sparql = f"""
        INSERT DATA {{
          GRAPH <{GRAPH_MOUNTS}> {{
            {' .\n            '.join(triples)} .
          }}
        }}
        """
        self._client.update(sparql)

        # Invalidate cache
        from app.vfs.cache import clear_mount_cache
        clear_mount_cache()

        return mount

    def update_mount(self, mount_id: str, updates: dict) -> MountDefinition:
        """Update a mount definition.

        Deletes all existing triples for the mount and re-inserts with updates applied.
        Returns the updated MountDefinition or raises ValueError.
        """
        existing = self.get_mount_by_id(mount_id)
        if existing is None:
            raise ValueError(f"Mount '{mount_id}' not found.")

        # Apply updates
        if "name" in updates:
            existing.name = updates["name"]
        if "path" in updates:
            existing.path = updates["path"]
        if "strategy" in updates:
            existing.strategy = updates["strategy"]
        if "group_by_property" in updates:
            existing.group_by_property = updates["group_by_property"]
        if "date_property" in updates:
            existing.date_property = updates["date_property"]
        if "sparql_scope" in updates:
            existing.sparql_scope = updates["sparql_scope"]
        if "scope_query" in updates:
            existing.scope_query = updates["scope_query"]
        if "type_filter" in updates:
            existing.type_filter = updates["type_filter"]
        if "filename_template" in updates:
            existing.filename_template = updates["filename_template"]
        if "visibility" in updates:
            existing.visibility = updates["visibility"]

        # Validate strategy if changed (supports pipe-delimited chains)
        _validate_strategy_chain(existing.strategy)

        # Validate path if changed
        if "path" in updates:
            _validate_mount_path(existing.path, self._client, exclude_id=mount_id)

        # Delete old triples then insert new ones
        mount_iri = f"{NS_MOUNT}{mount_id}"
        delete_sparql = f"""
        DELETE WHERE {{
          GRAPH <{GRAPH_MOUNTS}> {{
            <{mount_iri}> ?p ?o .
          }}
        }}
        """
        self._client.update(delete_sparql)

        # Re-insert with updated values
        triples = [
            f'<{mount_iri}> a <{NS_SEMPKM}MountSpec>',
            f'<{mount_iri}> <{MOUNT_NAME}> "{sparql_escape_string(existing.name)}"',
            f'<{mount_iri}> <{MOUNT_PATH}> "{sparql_escape_string(existing.path)}"',
            f'<{mount_iri}> <{DIRECTORY_STRATEGY}> "{sparql_escape_string(existing.strategy)}"',
            f'<{mount_iri}> <{CREATED_BY}> <{existing.created_by}>',
            f'<{mount_iri}> <{VISIBILITY}> "{sparql_escape_string(existing.visibility)}"',
            f'<{mount_iri}> <{CREATED_AT}> "{sparql_escape_string(existing.created_at)}"^^<http://www.w3.org/2001/XMLSchema#dateTime>',
        ]
        if existing.group_by_property:
            triples.append(
                f'<{mount_iri}> <{GROUP_BY_PROPERTY}> {safe_iri(existing.group_by_property)}'
            )
        if existing.date_property:
            triples.append(
                f'<{mount_iri}> <{DATE_PROPERTY}> {safe_iri(existing.date_property)}'
            )
        if existing.sparql_scope and existing.sparql_scope != "all":
            triples.append(
                f'<{mount_iri}> <{SPARQL_SCOPE}> "{sparql_escape_string(existing.sparql_scope)}"'
            )
        if existing.scope_query:
            triples.append(
                f'<{mount_iri}> <{SCOPE_QUERY}> {safe_iri(existing.scope_query)}'
            )
        if existing.type_filter:
            for tf_iri in existing.type_filter:
                triples.append(
                    f'<{mount_iri}> <{TYPE_FILTER}> {safe_iri(tf_iri)}'
                )
        if existing.filename_template:
            triples.append(
                f'<{mount_iri}> <{FILENAME_TEMPLATE}> "{sparql_escape_string(existing.filename_template)}"'
            )

        insert_sparql = f"""
        INSERT DATA {{
          GRAPH <{GRAPH_MOUNTS}> {{
            {' .\n            '.join(triples)} .
          }}
        }}
        """
        self._client.update(insert_sparql)

        # Invalidate cache
        from app.vfs.cache import clear_mount_cache
        clear_mount_cache()

        return existing

    def delete_mount(self, mount_id: str) -> bool:
        """Delete a mount definition. Returns True if deleted, False if not found."""
        existing = self.get_mount_by_id(mount_id)
        if existing is None:
            return False

        mount_iri = f"{NS_MOUNT}{mount_id}"
        sparql = f"""
        DELETE WHERE {{
          GRAPH <{GRAPH_MOUNTS}> {{
            <{mount_iri}> ?p ?o .
          }}
        }}
        """
        self._client.update(sparql)

        # Invalidate cache
        from app.vfs.cache import clear_mount_cache
        clear_mount_cache()

        return True

    # ── Internal helpers ────────────────────────────────────────────

    def _binding_to_mount(self, b: dict) -> MountDefinition:
        """Convert a SPARQL result binding to a MountDefinition."""
        mount_iri = b["mount"]["value"]
        mount_id = (
            mount_iri.replace(NS_MOUNT, "")
            if mount_iri.startswith(NS_MOUNT)
            else mount_iri
        )
        return MountDefinition(
            id=mount_id,
            name=b["name"]["value"],
            path=b["path"]["value"],
            strategy=b["strategy"]["value"],
            group_by_property=b.get("groupByProp", {}).get("value"),
            date_property=b.get("dateProp", {}).get("value"),
            sparql_scope=b.get("scope", {}).get("value", "all"),
            scope_query=b.get("scopeQuery", {}).get("value"),
            filename_template=b.get("filenameTemplate", {}).get("value"),
            created_by=b["createdBy"]["value"],
            visibility=b["visibility"]["value"],
            created_at=b.get("createdAt", {}).get("value", ""),
        )
