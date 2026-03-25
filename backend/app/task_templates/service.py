"""TaskTemplateService — RDF-backed CRUD for reusable task templates.

Templates live in a dedicated named graph (urn:sempkm:task-templates) on
RDF4J.  Each template carries a title, target RDF class, default property
map (JSON), and optional subtask definitions (JSON).  Instantiation
builds a batch command payload using the @slot: convention for cross-
command IRI references.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.sparql.builder import sparql_escape_string
from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

TEMPLATE_GRAPH = "urn:sempkm:task-templates"
TEMPLATE_IRI_PREFIX = "urn:sempkm:task-template:"

# SPARQL prefixes used across all queries
_PREFIXES = """
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX sempkm:  <urn:sempkm:>
PREFIX xsd:     <http://www.w3.org/2001/XMLSchema#>
"""



class TaskTemplateService:
    """CRUD operations for RDF-backed task templates."""

    def __init__(self, triplestore_client: TriplestoreClient) -> None:
        self._client = triplestore_client

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        title: str,
        target_class: str,
        default_properties: dict | None = None,
        subtask_definitions: list[dict] | None = None,
    ) -> dict:
        """Create a new task template and return its representation.

        Args:
            title: Human-readable template name.
            target_class: Full IRI of the RDF type to instantiate.
            default_properties: Key→value map merged into created objects.
            subtask_definitions: List of subtask specs, each with at minimum
                a ``title`` and optional ``type`` and ``properties``.

        Returns:
            Dict with id, title, target_class, default_properties,
            subtask_definitions, and created fields.
        """
        template_id = f"{TEMPLATE_IRI_PREFIX}{uuid.uuid4()}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        props_json = json.dumps(default_properties or {})
        subtasks_json = json.dumps(subtask_definitions or [])

        sparql = f"""{_PREFIXES}
INSERT DATA {{
    GRAPH <{TEMPLATE_GRAPH}> {{
        <{template_id}> dcterms:title "{sparql_escape_string(title)}" ;
            sempkm:targetClass <{target_class}> ;
            sempkm:defaultProperties "{sparql_escape_string(props_json)}" ;
            sempkm:subtaskDefinitions "{sparql_escape_string(subtasks_json)}" ;
            dcterms:created "{now}"^^xsd:dateTime .
    }}
}}"""
        await self._client.update(sparql)
        logger.info("Created task template %s (%s)", template_id, title)

        return {
            "id": template_id,
            "title": title,
            "target_class": target_class,
            "default_properties": default_properties or {},
            "subtask_definitions": subtask_definitions or [],
            "created": now,
        }

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list_all(self) -> list[dict]:
        """Return all task templates (id, title, target_class, created)."""
        sparql = f"""{_PREFIXES}
SELECT ?id ?title ?target_class ?created WHERE {{
    GRAPH <{TEMPLATE_GRAPH}> {{
        ?id dcterms:title ?title ;
            sempkm:targetClass ?target_class ;
            dcterms:created ?created .
    }}
}} ORDER BY ?title"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])

        return [
            {
                "id": b["id"]["value"],
                "title": b["title"]["value"],
                "target_class": b["target_class"]["value"],
                "created": b["created"]["value"],
            }
            for b in bindings
        ]

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    async def get(self, template_id: str) -> dict | None:
        """Fetch a single template by IRI, returning parsed JSON blobs.

        Returns None if the template does not exist.
        """
        sparql = f"""{_PREFIXES}
SELECT ?title ?target_class ?props ?subtasks ?created WHERE {{
    GRAPH <{TEMPLATE_GRAPH}> {{
        <{template_id}> dcterms:title ?title ;
            sempkm:targetClass ?target_class ;
            sempkm:defaultProperties ?props ;
            sempkm:subtaskDefinitions ?subtasks ;
            dcterms:created ?created .
    }}
}}"""

        result = await self._client.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        b = bindings[0]
        return {
            "id": template_id,
            "title": b["title"]["value"],
            "target_class": b["target_class"]["value"],
            "default_properties": _safe_json_loads(b["props"]["value"], {}),
            "subtask_definitions": _safe_json_loads(b["subtasks"]["value"], []),
            "created": b["created"]["value"],
        }

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(self, template_id: str, **updates) -> dict | None:
        """Update selected fields on a template.

        Supported keys: title, target_class, default_properties,
        subtask_definitions.  Returns the updated template dict, or
        None if the template was not found.
        """
        existing = await self.get(template_id)
        if existing is None:
            return None

        field_map: dict[str, tuple[str, str]] = {}
        if "title" in updates:
            field_map["dcterms:title"] = (
                f'"{sparql_escape_string(existing["title"])}"',
                f'"{sparql_escape_string(updates["title"])}"',
            )
            existing["title"] = updates["title"]
        if "target_class" in updates:
            field_map["sempkm:targetClass"] = (
                f'<{existing["target_class"]}>',
                f'<{updates["target_class"]}>',
            )
            existing["target_class"] = updates["target_class"]
        if "default_properties" in updates:
            old_json = json.dumps(existing["default_properties"])
            new_json = json.dumps(updates["default_properties"])
            field_map["sempkm:defaultProperties"] = (
                f'"{sparql_escape_string(old_json)}"',
                f'"{sparql_escape_string(new_json)}"',
            )
            existing["default_properties"] = updates["default_properties"]
        if "subtask_definitions" in updates:
            old_json = json.dumps(existing["subtask_definitions"])
            new_json = json.dumps(updates["subtask_definitions"])
            field_map["sempkm:subtaskDefinitions"] = (
                f'"{sparql_escape_string(old_json)}"',
                f'"{sparql_escape_string(new_json)}"',
            )
            existing["subtask_definitions"] = updates["subtask_definitions"]

        if not field_map:
            return existing  # nothing to change

        delete_lines = "\n".join(
            f"        <{template_id}> {pred} {old} ."
            for pred, (old, _new) in field_map.items()
        )
        insert_lines = "\n".join(
            f"        <{template_id}> {pred} {new} ."
            for pred, (_old, new) in field_map.items()
        )

        sparql = f"""{_PREFIXES}
DELETE DATA {{
    GRAPH <{TEMPLATE_GRAPH}> {{
{delete_lines}
    }}
}};
INSERT DATA {{
    GRAPH <{TEMPLATE_GRAPH}> {{
{insert_lines}
    }}
}}"""
        await self._client.update(sparql)
        logger.info("Updated task template %s (fields: %s)", template_id, list(updates.keys()))
        return existing

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, template_id: str) -> bool:
        """Delete a template by IRI.  Returns True if triples were targeted."""
        # Verify existence first to give a meaningful return value
        existing = await self.get(template_id)
        if existing is None:
            return False

        sparql = f"""{_PREFIXES}
DELETE WHERE {{
    GRAPH <{TEMPLATE_GRAPH}> {{
        <{template_id}> ?p ?o .
    }}
}}"""
        await self._client.update(sparql)
        logger.info("Deleted task template %s", template_id)
        return True

    # ------------------------------------------------------------------
    # Instantiate
    # ------------------------------------------------------------------

    async def instantiate(
        self,
        template_id: str,
        user_overrides: dict | None = None,
    ) -> list[dict]:
        """Build a batch command payload from a template.

        Returns a list of command dicts ready for the ``POST /api/commands``
        batch endpoint.  The main object uses ``slot: "main"`` so that
        subtask edge.create commands can reference it via ``@slot:main``.

        Args:
            template_id: Full IRI of the template to instantiate.
            user_overrides: Optional property overrides merged on top of
                template defaults.

        Returns:
            List of command dicts.

        Raises:
            ValueError: If the template does not exist.
        """
        template = await self.get(template_id)
        if template is None:
            raise ValueError(f"Template not found: {template_id}")

        merged_props = {**(template["default_properties"] or {})}
        if user_overrides:
            merged_props.update(user_overrides)

        # Main object command
        commands: list[dict] = [
            {
                "command": "object.create",
                "params": {
                    "type": template["target_class"],
                    "properties": merged_props,
                },
                "slot": "main",
            }
        ]

        # Subtask commands
        for idx, subtask_def in enumerate(template.get("subtask_definitions") or []):
            subtask_type = subtask_def.get("type", template["target_class"])
            subtask_props = dict(subtask_def.get("properties", {}))
            # Ensure the subtask has a title
            if "dcterms:title" not in subtask_props and "title" in subtask_def:
                subtask_props["dcterms:title"] = subtask_def["title"]

            commands.append({
                "command": "object.create",
                "params": {
                    "type": subtask_type,
                    "properties": subtask_props,
                },
                "slot": f"subtask_{idx}",
            })

            # Link subtask → main via sempkm:subtaskOf
            predicate = subtask_def.get("predicate", "sempkm:subtaskOf")
            commands.append({
                "command": "edge.create",
                "params": {
                    "source": f"@slot:subtask_{idx}",
                    "target": "@slot:main",
                    "predicate": predicate,
                },
            })

        logger.info(
            "Instantiated template %s → %d commands (%d subtasks)",
            template_id,
            len(commands),
            len(template.get("subtask_definitions") or []),
        )
        return commands


def _safe_json_loads(value: str, default):
    """Parse JSON string, returning *default* on failure."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default
