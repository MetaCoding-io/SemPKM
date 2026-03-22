"""Instance configuration model and persistence.

Manages the per-instance deployment configuration that persists in
``data/.instance-config.json``. This file is created by the setup wizard
(or programmatically) and survives container rebuilds via the Docker
volume-mounted ``data/`` directory.

Config loading priority (highest wins):
1. Explicit environment variables (BASE_NAMESPACE=... in .env)
2. Instance config file (data/.instance-config.json)
3. Pydantic defaults in config.py
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("data/.instance-config.json")


class InstanceConfig(BaseModel):
    """Per-instance deployment configuration.

    Written once during the setup wizard's deployment-mode step.
    Read at startup to override Settings defaults for base_namespace
    and app_base_url.
    """

    instance_id: str
    deployment_mode: Literal["local", "domain", "later"]
    base_namespace: str
    app_base_url: str
    configured_at: str  # ISO 8601 datetime string


def generate_instance_id() -> str:
    """Generate a new globally-unique instance identifier (UUID v4)."""
    return str(uuid.uuid4())


def load_instance_config(
    path: Path | None = None,
) -> InstanceConfig | None:
    """Load instance config from disk.

    Returns None if the file is absent, unreadable, or contains
    malformed/invalid JSON. Never raises — callers treat absence
    as "not yet configured".
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH
    try:
        if not path.is_file():
            return None
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return InstanceConfig(**data)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        logger.warning(
            "Failed to load instance config from %s: %s", path, exc
        )
        return None


def save_instance_config(
    config: InstanceConfig,
    path: Path | None = None,
) -> None:
    """Atomically write instance config to disk.

    Writes to a temporary sibling file first, then uses ``os.replace``
    for an atomic rename. This prevents partial writes if the process
    is interrupted mid-write.
    """
    if path is None:
        path = DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    payload = config.model_dump_json(indent=2)
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, path)
    logger.info("Instance config saved to %s (mode=%s)", path, config.deployment_mode)
