"""VFS RDF data migrations.

Contains SPARQL UPDATE operations for evolving VFS mount definitions
stored in the urn:sempkm:mounts named graph.
"""

import logging

from app.triplestore.sync_client import SyncTriplestoreClient

logger = logging.getLogger(__name__)


def migrate_saved_query_to_scope_query(client: SyncTriplestoreClient) -> int:
    """Rename sempkm:savedQueryId → sempkm:scopeQuery and wrap values as IRIs.

    Existing mounts store saved query references as:
        <mount> <urn:sempkm:savedQueryId> "uuid-string"^^xsd:string

    This migration converts them to:
        <mount> <urn:sempkm:scopeQuery> <urn:sempkm:query:uuid-string>

    Returns the number of triples migrated (0 if nothing to migrate).
    """
    # First, count how many triples need migration
    count_result = client.query(
        """
        SELECT (COUNT(*) AS ?count) FROM <urn:sempkm:mounts>
        WHERE {
          ?mount <urn:sempkm:savedQueryId> ?oldVal .
        }
        """
    )
    count = int(
        count_result["results"]["bindings"][0]["count"]["value"]
    ) if count_result["results"]["bindings"] else 0

    if count == 0:
        logger.info("migrate_saved_query_to_scope_query: nothing to migrate")
        return 0

    logger.info(
        "migrate_saved_query_to_scope_query: migrating %d triple(s)", count
    )

    # Rename predicate and wrap bare UUID strings as IRIs in one UPDATE
    client.update(
        """
        DELETE {
          GRAPH <urn:sempkm:mounts> {
            ?mount <urn:sempkm:savedQueryId> ?oldVal .
          }
        }
        INSERT {
          GRAPH <urn:sempkm:mounts> {
            ?mount <urn:sempkm:scopeQuery> ?newIri .
          }
        }
        WHERE {
          GRAPH <urn:sempkm:mounts> {
            ?mount <urn:sempkm:savedQueryId> ?oldVal .
            BIND(IRI(CONCAT("urn:sempkm:query:", STR(?oldVal))) AS ?newIri)
          }
        }
        """
    )

    logger.info(
        "migrate_saved_query_to_scope_query: migrated %d triple(s) "
        "(savedQueryId → scopeQuery, string → IRI)",
        count,
    )
    return count
