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
SAVED_QUERY_ID = f"{NS_SEMPKM}savedQueryId"
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
    saved_query_id: str | None = None
    created_by: str = ""  # user URN (urn:sempkm:user:{uuid})
    visibility: str = "personal"  # "shared" or "personal"
    created_at: str = ""  # ISO datetime string

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "strategy": self.strategy,
            "group_by_property": self.group_by_property,
            "date_property": self.date_property,
            "sparql_scope": self.sparql_scope,
            "saved_query_id": self.saved_query_id,
            "created_by": self.created_by,
            "visibility": self.visibility,
            "created_at": self.created_at,
        }


# ── Validation Helper ───────────────────────────────────────────────

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
                   ?scope ?savedQueryId ?createdBy ?visibility ?createdAt
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
              OPTIONAL {{ ?mount <{SAVED_QUERY_ID}> ?savedQueryId }}
              OPTIONAL {{ ?mount <{CREATED_AT}> ?createdAt }}
              FILTER(
                ?visibility = "shared" ||
                ?createdBy = <{user_iri}>
              )
            }}
            ORDER BY ?name
            """
        )
        return [self._binding_to_mount(b) for b in result["results"]["bindings"]]

    def get_mount_by_id(self, mount_id: str) -> MountDefinition | None:
        """Get a single mount definition by its UUID."""
        mount_iri = f"{NS_MOUNT}{mount_id}"
        result = self._client.query(
            f"""
            SELECT ?name ?path ?strategy ?groupByProp ?dateProp
                   ?scope ?savedQueryId ?createdBy ?visibility ?createdAt
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
              OPTIONAL {{ <{mount_iri}> <{SAVED_QUERY_ID}> ?savedQueryId }}
              OPTIONAL {{ <{mount_iri}> <{CREATED_AT}> ?createdAt }}
            }}
            LIMIT 1
            """
        )
        bindings = result["results"]["bindings"]
        if not bindings:
            return None

        b = bindings[0]
        return MountDefinition(
            id=mount_id,
            name=b["name"]["value"],
            path=b["path"]["value"],
            strategy=b["strategy"]["value"],
            group_by_property=b.get("groupByProp", {}).get("value"),
            date_property=b.get("dateProp", {}).get("value"),
            sparql_scope=b.get("scope", {}).get("value", "all"),
            saved_query_id=b.get("savedQueryId", {}).get("value"),
            created_by=b["createdBy"]["value"],
            visibility=b["visibility"]["value"],
            created_at=b.get("createdAt", {}).get("value", ""),
        )

    def get_mount_by_prefix(self, prefix: str) -> MountDefinition | None:
        """Get a mount definition by its path prefix. Used by provider dispatch."""
        result = self._client.query(
            f"""
            SELECT ?mount ?name ?strategy ?groupByProp ?dateProp
                   ?scope ?savedQueryId ?createdBy ?visibility ?createdAt
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
              OPTIONAL {{ ?mount <{SAVED_QUERY_ID}> ?savedQueryId }}
              OPTIONAL {{ ?mount <{CREATED_AT}> ?createdAt }}
            }}
            LIMIT 1
            """
        )
        bindings = result["results"]["bindings"]
        if not bindings:
            return None

        b = bindings[0]
        mount_iri = b["mount"]["value"]
        mount_id = mount_iri.replace(NS_MOUNT, "") if mount_iri.startswith(NS_MOUNT) else mount_iri
        return MountDefinition(
            id=mount_id,
            name=b["name"]["value"],
            path=prefix,
            strategy=b["strategy"]["value"],
            group_by_property=b.get("groupByProp", {}).get("value"),
            date_property=b.get("dateProp", {}).get("value"),
            sparql_scope=b.get("scope", {}).get("value", "all"),
            saved_query_id=b.get("savedQueryId", {}).get("value"),
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

        # Validate strategy
        if mount.strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{mount.strategy}'. "
                f"Must be one of: {', '.join(sorted(VALID_STRATEGIES))}"
            )

        # Validate path
        _validate_mount_path(mount.path, self._client)

        # Build INSERT DATA
        mount_iri = f"{NS_MOUNT}{mount.id}"
        triples = [
            f'<{mount_iri}> a <{NS_SEMPKM}MountSpec>',
            f'<{mount_iri}> <{MOUNT_NAME}> "{_escape_sparql(mount.name)}"',
            f'<{mount_iri}> <{MOUNT_PATH}> "{_escape_sparql(mount.path)}"',
            f'<{mount_iri}> <{DIRECTORY_STRATEGY}> "{_escape_sparql(mount.strategy)}"',
            f'<{mount_iri}> <{CREATED_BY}> <{mount.created_by}>',
            f'<{mount_iri}> <{VISIBILITY}> "{_escape_sparql(mount.visibility)}"',
            f'<{mount_iri}> <{CREATED_AT}> "{_escape_sparql(mount.created_at)}"^^<http://www.w3.org/2001/XMLSchema#dateTime>',
        ]
        if mount.group_by_property:
            triples.append(
                f'<{mount_iri}> <{GROUP_BY_PROPERTY}> <{mount.group_by_property}>'
            )
        if mount.date_property:
            triples.append(
                f'<{mount_iri}> <{DATE_PROPERTY}> <{mount.date_property}>'
            )
        if mount.sparql_scope and mount.sparql_scope != "all":
            triples.append(
                f'<{mount_iri}> <{SPARQL_SCOPE}> "{_escape_sparql(mount.sparql_scope)}"'
            )
        if mount.saved_query_id:
            triples.append(
                f'<{mount_iri}> <{SAVED_QUERY_ID}> "{_escape_sparql(mount.saved_query_id)}"^^<http://www.w3.org/2001/XMLSchema#string>'
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
        if "saved_query_id" in updates:
            existing.saved_query_id = updates["saved_query_id"]
        if "visibility" in updates:
            existing.visibility = updates["visibility"]

        # Validate strategy if changed
        if existing.strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Invalid strategy '{existing.strategy}'. "
                f"Must be one of: {', '.join(sorted(VALID_STRATEGIES))}"
            )

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
            f'<{mount_iri}> <{MOUNT_NAME}> "{_escape_sparql(existing.name)}"',
            f'<{mount_iri}> <{MOUNT_PATH}> "{_escape_sparql(existing.path)}"',
            f'<{mount_iri}> <{DIRECTORY_STRATEGY}> "{_escape_sparql(existing.strategy)}"',
            f'<{mount_iri}> <{CREATED_BY}> <{existing.created_by}>',
            f'<{mount_iri}> <{VISIBILITY}> "{_escape_sparql(existing.visibility)}"',
            f'<{mount_iri}> <{CREATED_AT}> "{_escape_sparql(existing.created_at)}"^^<http://www.w3.org/2001/XMLSchema#dateTime>',
        ]
        if existing.group_by_property:
            triples.append(
                f'<{mount_iri}> <{GROUP_BY_PROPERTY}> <{existing.group_by_property}>'
            )
        if existing.date_property:
            triples.append(
                f'<{mount_iri}> <{DATE_PROPERTY}> <{existing.date_property}>'
            )
        if existing.sparql_scope and existing.sparql_scope != "all":
            triples.append(
                f'<{mount_iri}> <{SPARQL_SCOPE}> "{_escape_sparql(existing.sparql_scope)}"'
            )
        if existing.saved_query_id:
            triples.append(
                f'<{mount_iri}> <{SAVED_QUERY_ID}> "{_escape_sparql(existing.saved_query_id)}"^^<http://www.w3.org/2001/XMLSchema#string>'
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
            saved_query_id=b.get("savedQueryId", {}).get("value"),
            created_by=b["createdBy"]["value"],
            visibility=b["visibility"]["value"],
            created_at=b.get("createdAt", {}).get("value", ""),
        )


def _escape_sparql(value: str) -> str:
    """Escape special characters for SPARQL string literals."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )
