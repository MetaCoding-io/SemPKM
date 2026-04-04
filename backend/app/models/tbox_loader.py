"""TBox loader — reads dashboard/workflow JSON definitions from model archives.

Used during model install to discover and create model-sourced TBox
surfaces (dashboards, workflows) defined in the manifest's entrypoints.
"""

import json
import logging
from pathlib import Path

from app.models.manifest import ManifestSchema

logger = logging.getLogger(__name__)


def load_tbox_dashboards(
    model_dir: Path, manifest: ManifestSchema
) -> list[dict] | None:
    """Load dashboard definitions from a model archive.

    Args:
        model_dir: Path to the model archive directory.
        manifest: Parsed manifest with resolved entrypoints.

    Returns:
        List of dashboard definition dicts, or None if the manifest
        has no dashboards entrypoint.

    Raises:
        ValueError: If the JSON file is missing, malformed, or contains
            invalid dashboard definitions.
    """
    ep = manifest.entrypoints.dashboards
    if ep is None:
        return None

    json_path = model_dir / ep
    if not json_path.exists():
        raise ValueError(
            f"Dashboards entrypoint '{ep}' not found at {json_path}"
        )

    try:
        with open(json_path) as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Malformed JSON in dashboards file {json_path}: {e}"
        ) from e

    if not isinstance(raw, dict) or "dashboards" not in raw:
        raise ValueError(
            f"Dashboards file must contain a top-level 'dashboards' array: {json_path}"
        )

    dashboards = raw["dashboards"]
    if not isinstance(dashboards, list):
        raise ValueError(
            f"'dashboards' must be an array: {json_path}"
        )

    for i, dash in enumerate(dashboards):
        if not isinstance(dash, dict):
            raise ValueError(
                f"Dashboard entry {i} must be an object: {json_path}"
            )
        if not dash.get("name"):
            raise ValueError(
                f"Dashboard entry {i} missing required 'name' field: {json_path}"
            )

    logger.info(
        "Loaded %d dashboard definition(s) from %s",
        len(dashboards),
        json_path,
    )
    return dashboards


def load_tbox_workflows(
    model_dir: Path, manifest: ManifestSchema
) -> list[dict] | None:
    """Load workflow definitions from a model archive.

    Args:
        model_dir: Path to the model archive directory.
        manifest: Parsed manifest with resolved entrypoints.

    Returns:
        List of workflow definition dicts, or None if the manifest
        has no workflows entrypoint.

    Raises:
        ValueError: If the JSON file is missing, malformed, or contains
            invalid workflow definitions.
    """
    ep = manifest.entrypoints.workflows
    if ep is None:
        return None

    json_path = model_dir / ep
    if not json_path.exists():
        raise ValueError(
            f"Workflows entrypoint '{ep}' not found at {json_path}"
        )

    try:
        with open(json_path) as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Malformed JSON in workflows file {json_path}: {e}"
        ) from e

    if not isinstance(raw, dict) or "workflows" not in raw:
        raise ValueError(
            f"Workflows file must contain a top-level 'workflows' array: {json_path}"
        )

    workflows = raw["workflows"]
    if not isinstance(workflows, list):
        raise ValueError(
            f"'workflows' must be an array: {json_path}"
        )

    for i, wf in enumerate(workflows):
        if not isinstance(wf, dict):
            raise ValueError(
                f"Workflow entry {i} must be an object: {json_path}"
            )
        if not wf.get("name"):
            raise ValueError(
                f"Workflow entry {i} missing required 'name' field: {json_path}"
            )
        if not wf.get("steps"):
            raise ValueError(
                f"Workflow entry {i} missing required 'steps' field: {json_path}"
            )

    logger.info(
        "Loaded %d workflow definition(s) from %s",
        len(workflows),
        json_path,
    )
    return workflows
