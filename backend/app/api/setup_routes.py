"""Setup routes for instance deployment configuration.

Provides the ``POST /api/setup/configure-instance`` endpoint that the
setup wizard calls before account creation to set the deployment mode,
BASE_NAMESPACE, and APP_BASE_URL.
"""

import logging
import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from app.instance_config import (
    DEFAULT_CONFIG_PATH,
    InstanceConfig,
    generate_instance_id,
    load_instance_config,
    save_instance_config,
)

logger = logging.getLogger(__name__)

setup_router = APIRouter(prefix="/api/setup", tags=["setup"])

# Hostname regex: RFC-952/RFC-1123 compliant, no protocol prefix, no path.
# Allows subdomains (e.g. sempkm.example.com) and bare domains (e.g. example.com).
_HOSTNAME_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
)


class ConfigureInstanceRequest(BaseModel):
    """Request body for POST /api/setup/configure-instance."""

    mode: Literal["local", "domain", "later"]
    domain: str | None = None


class ConfigureInstanceResponse(BaseModel):
    """Response after successful instance configuration."""

    base_namespace: str
    app_base_url: str
    instance_id: str


def _validate_domain(domain: str | None, mode: str) -> str:
    """Validate and normalise the domain for 'domain' mode.

    Returns the cleaned domain string.
    Raises HTTPException(400) on validation failure.
    """
    if mode != "domain":
        return ""

    if not domain or not domain.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain is required when mode is 'domain'.",
        )

    domain = domain.strip().lower()

    # Reject protocol prefixes
    if domain.startswith(("http://", "https://", "//")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain must not include a protocol prefix (http:// or https://).",
        )

    # Strip trailing slash/path
    domain = domain.split("/")[0]

    if not _HOSTNAME_RE.match(domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid domain: '{domain}'. Must be a valid hostname (e.g. sempkm.example.com).",
        )

    return domain


async def _check_user_data_exists(request: Request) -> bool:
    """Check if the triplestore has user-created data in urn:sempkm:current.

    Returns True if at least one user-created triple exists (excluding
    vocabulary/ontology triples). A simple ASK against the current graph
    is sufficient — if any object exists, the namespace should not change.
    """
    client = request.app.state.triplestore_client
    sparql = (
        "ASK { GRAPH <urn:sempkm:current> { ?s a ?type } }"
    )
    try:
        result = await client.query(sparql)
        return result.get("boolean", False)
    except Exception:
        logger.warning("Failed to check for user data in triplestore", exc_info=True)
        # Fail open — don't block configuration if triplestore is unreachable.
        # The worst case is reconfiguring an instance with existing data,
        # which the user was warned about in the wizard UI.
        return False


@setup_router.post(
    "/configure-instance",
    response_model=ConfigureInstanceResponse,
    summary="Configure instance deployment mode",
    description=(
        "Sets the deployment mode, BASE_NAMESPACE, and APP_BASE_URL. "
        "Must be called before account creation. Refuses to change "
        "configuration if user data already exists in the triplestore."
    ),
)
async def configure_instance(
    body: ConfigureInstanceRequest,
    request: Request,
) -> ConfigureInstanceResponse:
    """Configure the instance deployment mode and namespace."""

    # Guard: refuse if setup mode is not active (owner already exists)
    if not getattr(request.app.state, "setup_mode", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Instance configuration is only available during initial setup. "
                "Setup mode is not active."
            ),
        )

    # Guard: refuse if user data already exists
    if await _check_user_data_exists(request):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot change deployment configuration: user data already exists "
                "in the triplestore. BASE_NAMESPACE cannot be changed after objects "
                "are created without a data migration."
            ),
        )

    # Validate domain for 'domain' mode
    domain = _validate_domain(body.domain, body.mode)

    # Preserve existing instance_id if config already exists, else generate new
    existing = load_instance_config()
    instance_id = existing.instance_id if existing else generate_instance_id()

    # Compute namespace and base URL per deployment mode
    if body.mode == "local":
        base_namespace = f"urn:sempkm:{instance_id}/"
        app_base_url = "http://localhost:3000"
    elif body.mode == "domain":
        base_namespace = f"https://{domain}/data/"
        app_base_url = f"https://{domain}"
    else:  # "later"
        base_namespace = f"urn:sempkm:{instance_id}/"
        app_base_url = ""

    # Build and persist config
    from datetime import datetime, timezone

    config = InstanceConfig(
        instance_id=instance_id,
        deployment_mode=body.mode,
        base_namespace=base_namespace,
        app_base_url=app_base_url,
        configured_at=datetime.now(timezone.utc).isoformat(),
    )
    save_instance_config(config)

    logger.info(
        "Instance configured: mode=%s, base_namespace=%s, app_base_url=%s",
        body.mode,
        base_namespace,
        app_base_url,
    )

    return ConfigureInstanceResponse(
        base_namespace=base_namespace,
        app_base_url=app_base_url,
        instance_id=instance_id,
    )
