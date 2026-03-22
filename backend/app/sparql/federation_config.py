"""Federation endpoint persistence and merge logic.

Manages the per-instance federation endpoint allowlist that persists in
``data/.federation-endpoints.json``. Admin-added endpoints are stored here
and merged at runtime with env-var-configured endpoints from
``settings.federation_allowed_endpoints``.

The merge rule: env-var entries are authoritative and non-removable.
Admin-added entries can be added or removed via the API.
Deduplication by URL (env wins).
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_FEDERATION_PATH = Path("data/.federation-endpoints.json")


class FederationEndpoints(BaseModel):
    """Persisted admin-added federation endpoints."""

    endpoints: list[str] = []
    updated_at: str = ""  # ISO 8601


def load_federation_endpoints(
    path: Path | None = None,
) -> FederationEndpoints:
    """Load persisted federation endpoints from disk.

    Returns a model with an empty list if the file is absent, unreadable,
    or contains malformed JSON. Never raises.
    """
    if path is None:
        path = DEFAULT_FEDERATION_PATH
    try:
        if not path.is_file():
            return FederationEndpoints()
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return FederationEndpoints(**data)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        logger.warning(
            "Failed to load federation endpoints from %s: %s", path, exc
        )
        return FederationEndpoints()


def save_federation_endpoints(
    config: FederationEndpoints,
    path: Path | None = None,
) -> None:
    """Atomically write federation endpoints to disk.

    Writes to a temporary sibling file first, then uses ``os.replace``
    for an atomic rename to prevent partial writes.
    """
    if path is None:
        path = DEFAULT_FEDERATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    payload = config.model_dump_json(indent=2)
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, path)
    logger.info(
        "Federation endpoints saved to %s (%d endpoints)",
        path,
        len(config.endpoints),
    )


def get_merged_endpoints(path: Path | None = None) -> list[dict]:
    """Merge env-var and persisted endpoints into a unified list.

    Returns list of dicts: ``{"url": str, "source": "env"|"admin", "removable": bool}``.
    Env-var entries are ``removable: False`` and take precedence on duplicates.
    """
    env_endpoints = settings.get_allowed_endpoints()
    persisted = load_federation_endpoints(path)

    # Build result: env entries first (authoritative)
    seen_urls: set[str] = set()
    merged: list[dict] = []

    for url in env_endpoints:
        normalised = url.strip()
        if normalised and normalised not in seen_urls:
            seen_urls.add(normalised)
            merged.append({
                "url": normalised,
                "source": "env",
                "removable": False,
            })

    for url in persisted.endpoints:
        normalised = url.strip()
        if normalised and normalised not in seen_urls:
            seen_urls.add(normalised)
            merged.append({
                "url": normalised,
                "source": "admin",
                "removable": True,
            })

    return merged


def add_endpoint(url: str, path: Path | None = None) -> list[dict]:
    """Add an endpoint to the persisted file and return the merged list.

    Deduplicates against both env and existing persisted entries.
    """
    persisted = load_federation_endpoints(path)
    normalised = url.strip()

    # Check if already in persisted list
    if normalised not in persisted.endpoints:
        persisted.endpoints.append(normalised)
        persisted.updated_at = datetime.now(timezone.utc).isoformat()
        save_federation_endpoints(persisted, path)
        logger.info("Federation endpoint added: %s", normalised)
    else:
        logger.info("Federation endpoint already persisted: %s", normalised)

    return get_merged_endpoints(path)


def remove_endpoint(url: str, path: Path | None = None) -> list[dict]:
    """Remove an admin-added endpoint from the persisted file.

    Returns the updated merged list. Raises ValueError if the endpoint
    is env-sourced (non-removable) or not found.
    """
    normalised = url.strip()

    # Check if it's an env-var endpoint (non-removable)
    env_endpoints = settings.get_allowed_endpoints()
    if normalised in env_endpoints:
        raise ValueError(
            f"Cannot remove env-var endpoint: {normalised}"
        )

    persisted = load_federation_endpoints(path)
    if normalised not in persisted.endpoints:
        raise ValueError(f"Endpoint not found in admin list: {normalised}")

    persisted.endpoints.remove(normalised)
    persisted.updated_at = datetime.now(timezone.utc).isoformat()
    save_federation_endpoints(persisted, path)
    logger.info("Federation endpoint removed: %s", normalised)

    return get_merged_endpoints(path)
