"""REST API endpoints for VFS mount definition management.

Provides CRUD endpoints for creating, reading, updating, and deleting
mount definitions, plus a preview endpoint for dry-run directory structure
generation and a properties endpoint for populating strategy field dropdowns.

Uses async TriplestoreClient (not sync) since these run in FastAPI routes.
The SPARQL patterns mirror SyncMountService but use async client methods.
"""

import logging
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.dependencies import get_triplestore_client
from app.triplestore.client import TriplestoreClient
from app.vfs.cache import clear_mount_cache
from app.vfs.mount_service import (
    CREATED_AT,
    CREATED_BY,
    DATE_PROPERTY,
    DIRECTORY_STRATEGY,
    GRAPH_MOUNTS,
    GROUP_BY_PROPERTY,
    MOUNT_NAME,
    MOUNT_PATH,
    NS_MOUNT,
    NS_SEMPKM,
    SAVED_QUERY_ID,
    SPARQL_SCOPE,
    VALID_STRATEGIES,
    VISIBILITY,
    MountDefinition,
    _escape_sparql,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vfs", tags=["vfs-mounts"])

# Path validation regex (same as mount_service.py)
_PATH_REGEX = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RESERVED_PATHS = {"_uncategorized"}


# ── Request/Response Models ─────────────────────────────────────────

class MountCreateRequest(BaseModel):
    """Request body for creating a mount."""

    name: str = Field(..., min_length=1, max_length=255)
    path: str = Field(..., min_length=1, max_length=100)
    strategy: str = Field(..., description="One of: flat, by-type, by-date, by-tag, by-property")
    group_by_property: str | None = None
    date_property: str | None = None
    sparql_scope: str | None = "all"
    saved_query_id: str | None = None
    visibility: str | None = "personal"


class MountUpdateRequest(BaseModel):
    """Request body for updating a mount (all fields optional)."""

    name: str | None = None
    path: str | None = None
    strategy: str | None = None
    group_by_property: str | None = None
    date_property: str | None = None
    sparql_scope: str | None = None
    saved_query_id: str | None = None
    visibility: str | None = None


class MountPreviewRequest(BaseModel):
    """Request body for previewing a mount's directory structure."""

    strategy: str = Field(..., description="One of: flat, by-type, by-date, by-tag, by-property")
    group_by_property: str | None = None
    date_property: str | None = None
    sparql_scope: str | None = "all"
    saved_query_id: str | None = None


# ── Async Helpers ───────────────────────────────────────────────────

async def _validate_mount_path_async(
    path: str,
    client: TriplestoreClient,
    exclude_id: str | None = None,
) -> None:
    """Async version of mount path validation."""
    if not _PATH_REGEX.match(path):
        raise HTTPException(
            400,
            f"Mount path '{path}' is invalid. "
            "Use only lowercase letters, digits, and hyphens. "
            "Must start with a letter or digit.",
        )

    if path in _RESERVED_PATHS or path.startswith("."):
        raise HTTPException(400, f"Mount path '{path}' is reserved.")

    # Model conflict check
    result = await client.query(
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
        raise HTTPException(
            400,
            f"Mount path '{path}' conflicts with installed model '{path}'.",
        )

    # Uniqueness check
    exclude_filter = ""
    if exclude_id:
        exclude_filter = f"FILTER(?mount != <{NS_MOUNT}{exclude_id}>)"
    result = await client.query(
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
        raise HTTPException(400, f"Mount path '{path}' is already in use.")


async def _get_mount_by_id_async(
    mount_id: str, client: TriplestoreClient
) -> MountDefinition | None:
    """Async fetch of a single mount by ID."""
    mount_iri = f"{NS_MOUNT}{mount_id}"
    result = await client.query(
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


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/mounts")
async def list_mounts(
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """List all mounts visible to the current user.

    Returns both:
    - Model mounts (read-only, source="model") — auto-generated from
      installed mental models
    - Custom mounts (editable, source="custom") — user-created MountSpecs
    """
    # ── Model mounts (read-only) ─────────────────────────────────────
    models_result = await client.query("""
        SELECT DISTINCT ?modelId FROM <urn:sempkm:models>
        WHERE {
          ?model a <urn:sempkm:MentalModel> ;
                 <urn:sempkm:modelId> ?modelId .
        }
        ORDER BY ?modelId
    """)

    mounts: list[dict] = []
    for b in models_result["results"]["bindings"]:
        model_id = b["modelId"]["value"]
        mounts.append({
            "id": f"model:{model_id}",
            "name": model_id,
            "path": model_id,
            "strategy": "by-type",
            "source": "model",
            "visibility": "shared",
            "created_by": "",
            "created_at": "",
        })

    # ── Custom mounts (editable) ─────────────────────────────────────
    user_iri = f"urn:sempkm:user:{user.id}"
    result = await client.query(
        f"""
        SELECT DISTINCT ?mount ?name ?path ?strategy ?groupByProp ?dateProp
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

    for b in result["results"]["bindings"]:
        mount_iri = b["mount"]["value"]
        mount_id = (
            mount_iri.replace(NS_MOUNT, "")
            if mount_iri.startswith(NS_MOUNT)
            else mount_iri
        )
        d = MountDefinition(
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
        ).to_dict()
        d["source"] = "custom"
        mounts.append(d)

    return JSONResponse(mounts)


@router.post("/mounts", status_code=201)
async def create_mount(
    body: MountCreateRequest,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Create a new mount definition."""
    # Validate strategy
    if body.strategy not in VALID_STRATEGIES:
        raise HTTPException(
            400,
            f"Invalid strategy '{body.strategy}'. "
            f"Must be one of: {', '.join(sorted(VALID_STRATEGIES))}",
        )

    # Only owners can create shared mounts
    visibility = body.visibility or "personal"
    if visibility == "shared" and user.role != "owner":
        raise HTTPException(403, "Only owners can create shared mounts.")

    # Validate path
    await _validate_mount_path_async(body.path, client)

    # Build and insert mount
    mount_id = str(uuid.uuid4())
    user_iri = f"urn:sempkm:user:{user.id}"
    created_at = datetime.now(UTC).isoformat()
    mount_iri = f"{NS_MOUNT}{mount_id}"

    triples = [
        f'<{mount_iri}> a <{NS_SEMPKM}MountSpec>',
        f'<{mount_iri}> <{MOUNT_NAME}> "{_escape_sparql(body.name)}"',
        f'<{mount_iri}> <{MOUNT_PATH}> "{_escape_sparql(body.path)}"',
        f'<{mount_iri}> <{DIRECTORY_STRATEGY}> "{_escape_sparql(body.strategy)}"',
        f'<{mount_iri}> <{CREATED_BY}> <{user_iri}>',
        f'<{mount_iri}> <{VISIBILITY}> "{_escape_sparql(visibility)}"',
        f'<{mount_iri}> <{CREATED_AT}> "{_escape_sparql(created_at)}"^^<http://www.w3.org/2001/XMLSchema#dateTime>',
    ]
    if body.group_by_property:
        triples.append(
            f'<{mount_iri}> <{GROUP_BY_PROPERTY}> <{body.group_by_property}>'
        )
    if body.date_property:
        triples.append(
            f'<{mount_iri}> <{DATE_PROPERTY}> <{body.date_property}>'
        )
    scope = body.sparql_scope or "all"
    if scope != "all":
        triples.append(
            f'<{mount_iri}> <{SPARQL_SCOPE}> "{_escape_sparql(scope)}"'
        )
    if body.saved_query_id:
        triples.append(
            f'<{mount_iri}> <{SAVED_QUERY_ID}> "{_escape_sparql(body.saved_query_id)}"^^<http://www.w3.org/2001/XMLSchema#string>'
        )

    sparql = f"""
    INSERT DATA {{
      GRAPH <{GRAPH_MOUNTS}> {{
        {' .\n        '.join(triples)} .
      }}
    }}
    """
    await client.update(sparql)
    clear_mount_cache()

    mount = MountDefinition(
        id=mount_id,
        name=body.name,
        path=body.path,
        strategy=body.strategy,
        group_by_property=body.group_by_property,
        date_property=body.date_property,
        sparql_scope=scope,
        saved_query_id=body.saved_query_id,
        created_by=user_iri,
        visibility=visibility,
        created_at=created_at,
    )
    return JSONResponse(mount.to_dict(), status_code=201)


@router.put("/mounts/{mount_id}")
async def update_mount(
    mount_id: str,
    body: MountUpdateRequest,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Update a mount definition. Only the creator or owner can update."""
    existing = await _get_mount_by_id_async(mount_id, client)
    if existing is None:
        raise HTTPException(404, f"Mount '{mount_id}' not found.")

    # Authorization: only creator or owner can update
    user_iri = f"urn:sempkm:user:{user.id}"
    if existing.created_by != user_iri and user.role != "owner":
        raise HTTPException(403, "Only the mount creator or an owner can update this mount.")

    # Only owners can set visibility to shared
    if body.visibility == "shared" and user.role != "owner":
        raise HTTPException(403, "Only owners can create shared mounts.")

    # Apply updates
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(existing, key, value)

    # Validate strategy
    if existing.strategy not in VALID_STRATEGIES:
        raise HTTPException(
            400,
            f"Invalid strategy '{existing.strategy}'. "
            f"Must be one of: {', '.join(sorted(VALID_STRATEGIES))}",
        )

    # Validate path if changed
    if "path" in updates:
        await _validate_mount_path_async(existing.path, client, exclude_id=mount_id)

    # Delete old triples
    mount_iri = f"{NS_MOUNT}{mount_id}"
    await client.update(
        f"""
        DELETE WHERE {{
          GRAPH <{GRAPH_MOUNTS}> {{
            <{mount_iri}> ?p ?o .
          }}
        }}
        """
    )

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

    await client.update(
        f"""
        INSERT DATA {{
          GRAPH <{GRAPH_MOUNTS}> {{
            {' .\n            '.join(triples)} .
          }}
        }}
        """
    )
    clear_mount_cache()

    return JSONResponse(existing.to_dict())


@router.delete("/mounts/{mount_id}", status_code=204)
async def delete_mount(
    mount_id: str,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Delete a mount definition. Only the creator or owner can delete."""
    existing = await _get_mount_by_id_async(mount_id, client)
    if existing is None:
        raise HTTPException(404, f"Mount '{mount_id}' not found.")

    # Authorization: only creator or owner can delete
    user_iri = f"urn:sempkm:user:{user.id}"
    if existing.created_by != user_iri and user.role != "owner":
        raise HTTPException(403, "Only the mount creator or an owner can delete this mount.")

    mount_iri = f"{NS_MOUNT}{mount_id}"
    await client.update(
        f"""
        DELETE WHERE {{
          GRAPH <{GRAPH_MOUNTS}> {{
            <{mount_iri}> ?p ?o .
          }}
        }}
        """
    )
    clear_mount_cache()

    return JSONResponse(content=None, status_code=204)


@router.post("/mounts/preview")
async def preview_mount(
    body: MountPreviewRequest,
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """Preview the directory structure a mount config would produce.

    Returns a tree of directories with object counts, without creating
    the mount. Caps at 100 objects per folder.
    """
    if body.strategy not in VALID_STRATEGIES:
        raise HTTPException(
            400,
            f"Invalid strategy '{body.strategy}'. "
            f"Must be one of: {', '.join(sorted(VALID_STRATEGIES))}",
        )

    # Build scope filter (default: all objects in current graph)
    scope_filter = ""
    if body.sparql_scope and body.sparql_scope != "all" and body.saved_query_id:
        # If scope references a saved query, use it as a sub-select
        # For preview, we just use all objects (full scope query execution
        # would require loading the saved query text from SQLite)
        scope_filter = ""

    directories: list[dict] = []

    if body.strategy == "flat":
        # Flat: just count all objects
        result = await client.query(
            f"""
            SELECT (COUNT(DISTINCT ?iri) AS ?count) FROM <urn:sempkm:current>
            WHERE {{
              ?iri a ?type .
              {scope_filter}
            }}
            """
        )
        count = int(result["results"]["bindings"][0]["count"]["value"]) if result["results"]["bindings"] else 0
        directories.append({"name": "(all files)", "file_count": min(count, 100)})

    elif body.strategy == "by-type":
        # Group by rdf:type
        result = await client.query(
            f"""
            SELECT ?typeLabel (COUNT(DISTINCT ?iri) AS ?count) FROM <urn:sempkm:current>
            WHERE {{
              ?iri a ?typeIri .
              {scope_filter}
              BIND(REPLACE(STR(?typeIri), ".*[/:#]", "") AS ?typeLabel)
            }}
            GROUP BY ?typeLabel
            ORDER BY ?typeLabel
            LIMIT 50
            """
        )
        for b in result["results"]["bindings"]:
            directories.append({
                "name": b["typeLabel"]["value"],
                "file_count": min(int(b["count"]["value"]), 100),
            })

    elif body.strategy == "by-tag":
        if not body.group_by_property:
            raise HTTPException(400, "by-tag strategy requires group_by_property.")
        prop = body.group_by_property
        result = await client.query(
            f"""
            SELECT ?tagValue (COUNT(DISTINCT ?iri) AS ?count) FROM <urn:sempkm:current>
            WHERE {{
              ?iri <{prop}> ?tagValue .
              {scope_filter}
            }}
            GROUP BY ?tagValue
            ORDER BY ?tagValue
            LIMIT 50
            """
        )
        for b in result["results"]["bindings"]:
            directories.append({
                "name": str(b["tagValue"]["value"]),
                "file_count": min(int(b["count"]["value"]), 100),
            })
        # Check for uncategorized objects
        uncat_result = await client.query(
            f"""
            SELECT (COUNT(DISTINCT ?iri) AS ?count) FROM <urn:sempkm:current>
            WHERE {{
              ?iri a ?type .
              {scope_filter}
              FILTER NOT EXISTS {{ ?iri <{prop}> ?val }}
            }}
            """
        )
        uncat_count = int(uncat_result["results"]["bindings"][0]["count"]["value"]) if uncat_result["results"]["bindings"] else 0
        if uncat_count > 0:
            directories.append({
                "name": "_uncategorized",
                "file_count": min(uncat_count, 100),
            })

    elif body.strategy == "by-date":
        if not body.date_property:
            raise HTTPException(400, "by-date strategy requires date_property.")
        prop = body.date_property
        result = await client.query(
            f"""
            SELECT ?year ?month (COUNT(DISTINCT ?iri) AS ?count) FROM <urn:sempkm:current>
            WHERE {{
              ?iri <{prop}> ?date .
              {scope_filter}
              BIND(YEAR(xsd:dateTime(?date)) AS ?year)
              BIND(MONTH(xsd:dateTime(?date)) AS ?month)
            }}
            GROUP BY ?year ?month
            ORDER BY DESC(?year) DESC(?month)
            LIMIT 50
            """
        )
        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        for b in result["results"]["bindings"]:
            year = b["year"]["value"]
            month_num = int(b["month"]["value"])
            month_label = month_names[month_num] if 1 <= month_num <= 12 else str(month_num)
            directories.append({
                "name": f"{year}/{month_num:02d}-{month_label}",
                "file_count": min(int(b["count"]["value"]), 100),
            })

    elif body.strategy == "by-property":
        if not body.group_by_property:
            raise HTTPException(400, "by-property strategy requires group_by_property.")
        prop = body.group_by_property
        result = await client.query(
            f"""
            SELECT ?groupValue ?groupLabel (COUNT(DISTINCT ?iri) AS ?count)
            FROM <urn:sempkm:current>
            WHERE {{
              ?iri <{prop}> ?groupValue .
              {scope_filter}
              OPTIONAL {{ ?groupValue <http://purl.org/dc/terms/title> ?t }}
              OPTIONAL {{ ?groupValue <http://www.w3.org/2000/01/rdf-schema#label> ?r }}
              BIND(COALESCE(
                ?t, ?r,
                IF(isIRI(?groupValue),
                   REPLACE(STR(?groupValue), ".*[/:#]", ""),
                   STR(?groupValue))
              ) AS ?groupLabel)
            }}
            GROUP BY ?groupValue ?groupLabel
            ORDER BY ?groupLabel
            LIMIT 50
            """
        )
        for b in result["results"]["bindings"]:
            directories.append({
                "name": b["groupLabel"]["value"],
                "file_count": min(int(b["count"]["value"]), 100),
            })

    return JSONResponse({"directories": directories})


@router.get("/mounts/properties")
async def list_properties(
    user: User = Depends(get_current_user),
    client: TriplestoreClient = Depends(get_triplestore_client),
):
    """List available properties from SHACL shapes for strategy field dropdowns.

    Returns properties extracted from all shapes graphs, with their IRIs,
    human-readable names, and which types they belong to.
    """
    # First get all model IDs to query their shapes graphs
    models_result = await client.query(
        """
        SELECT DISTINCT ?modelId FROM <urn:sempkm:models>
        WHERE {
          ?model a <urn:sempkm:MentalModel> ;
                 <urn:sempkm:modelId> ?modelId .
        }
        """
    )
    model_ids = [b["modelId"]["value"] for b in models_result["results"]["bindings"]]

    properties: dict[str, dict] = {}  # iri -> {iri, name, types: set}

    for model_id in model_ids:
        shapes_graph = f"urn:sempkm:model:{model_id}:shapes"
        result = await client.query(
            f"""
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT ?propIri ?propName ?typeLabel
            FROM <{shapes_graph}>
            WHERE {{
              ?shape sh:property ?propShape .
              ?propShape sh:path ?propIri .
              OPTIONAL {{ ?propShape sh:name ?propName }}
              OPTIONAL {{
                ?shape sh:targetClass ?cls .
                BIND(REPLACE(STR(?cls), ".*[/:#]", "") AS ?typeLabel)
              }}
            }}
            """
        )
        for b in result["results"]["bindings"]:
            prop_iri = b["propIri"]["value"]
            prop_name = b.get("propName", {}).get("value")
            type_label = b.get("typeLabel", {}).get("value")

            if prop_iri not in properties:
                # Use sh:name if available, otherwise derive from IRI
                display_name = prop_name or prop_iri.rsplit("/", 1)[-1].rsplit(":", 1)[-1].rsplit("#", 1)[-1]
                properties[prop_iri] = {
                    "iri": prop_iri,
                    "name": display_name,
                    "types": set(),
                }

            if type_label:
                properties[prop_iri]["types"].add(type_label)

    # Convert sets to sorted lists for JSON serialization
    prop_list = []
    for prop in sorted(properties.values(), key=lambda p: p["name"].lower()):
        prop_list.append({
            "iri": prop["iri"],
            "name": prop["name"],
            "types": sorted(prop["types"]),
        })

    return JSONResponse({"properties": prop_list})
