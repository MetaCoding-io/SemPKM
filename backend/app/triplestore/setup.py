"""RDF4J repository auto-creation on startup.

Ensures the SemPKM repository exists in the RDF4J triplestore. If the
repository does not exist, creates it using the Turtle configuration from
config/rdf4j/sempkm-repo.ttl with native store and cspo indexes.

Also ensures the sentinel triple exists in the current state graph to
prevent RDF4J from deleting the empty graph (Pitfall 1 from research).
"""

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


async def ensure_repository(
    client: httpx.AsyncClient, base_url: str, repo_id: str
) -> None:
    """Create the RDF4J repository if it does not exist.

    Args:
        client: An httpx.AsyncClient instance.
        base_url: The RDF4J server base URL (e.g., http://triplestore:8080/rdf4j-server).
        repo_id: The repository identifier (e.g., sempkm).
    """
    base_url = base_url.rstrip("/")
    repo_url = f"{base_url}/repositories/{repo_id}"

    # Check if repository already exists
    resp = await client.get(f"{repo_url}/size")
    if resp.status_code == 200:
        logger.info("Repository '%s' already exists", repo_id)
    else:
        logger.info("Repository '%s' not found, creating...", repo_id)

        # Read the Turtle config file
        config_path = Path("/app/config/rdf4j/sempkm-repo.ttl")
        if not config_path.exists():
            # Fall back to relative path for local development
            config_path = (
                Path(__file__).parent.parent.parent.parent
                / "config"
                / "rdf4j"
                / "sempkm-repo.ttl"
            )

        config_ttl = config_path.read_text()

        # Replace the hardcoded repo ID in the TTL with the actual repo_id.
        # The config file uses "sempkm" but test environments use a different ID.
        config_ttl = config_ttl.replace(
            'config:rep.id "sempkm"', f'config:rep.id "{repo_id}"'
        )

        resp = await client.put(
            repo_url,
            content=config_ttl,
            headers={"Content-Type": "text/turtle"},
        )
        resp.raise_for_status()
        logger.info("Repository '%s' created successfully", repo_id)

    # Ensure sentinel triple exists in current state graph (Pitfall 1)
    # This prevents RDF4J from deleting the empty graph
    sentinel_sparql = (
        "INSERT DATA { "
        "GRAPH <urn:sempkm:current> { "
        "<urn:sempkm:current> a <urn:sempkm:StateGraph> "
        "} }"
    )
    resp = await client.post(
        f"{repo_url}/statements",
        data={"update": sentinel_sparql},
    )
    resp.raise_for_status()
    logger.info("Sentinel triple ensured in current state graph")
