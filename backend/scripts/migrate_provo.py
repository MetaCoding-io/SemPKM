#!/usr/bin/env python3
"""PROV-O retroactive migration — M006/S01.

Renames custom sempkm: provenance predicates to their PROV-O equivalents
across all named graphs in the triplestore. Idempotent — safe to re-run.

Predicates migrated:
  sempkm:timestamp   → prov:startedAtTime
  sempkm:performedBy → prov:wasAssociatedWith
  sempkm:description → rdfs:label
  sempkm:commentedBy → prov:wasAttributedTo
  sempkm:commentedAt → prov:generatedAtTime
  vocab:executedBy   → prov:wasAssociatedWith

Also inserts:
  sempkm:Event rdfs:subClassOf prov:Activity (D104)

Usage:
  python -m scripts.migrate_provo [--dry-run] [--triplestore-url URL]
"""

import argparse
import logging
import sys

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_URL = "http://localhost:7200"
REPOSITORY = "sempkm"

# SPARQL UPDATE statements — each is idempotent (DELETE/INSERT WHERE)
MIGRATION_UPDATES = [
    # 1. Event: sempkm:timestamp → prov:startedAtTime
    """
    DELETE { GRAPH ?g { ?s <urn:sempkm:timestamp> ?o } }
    INSERT { GRAPH ?g { ?s <http://www.w3.org/ns/prov#startedAtTime> ?o } }
    WHERE  { GRAPH ?g { ?s <urn:sempkm:timestamp> ?o } }
    """,
    # 2. Event: sempkm:performedBy → prov:wasAssociatedWith
    """
    DELETE { GRAPH ?g { ?s <urn:sempkm:performedBy> ?o } }
    INSERT { GRAPH ?g { ?s <http://www.w3.org/ns/prov#wasAssociatedWith> ?o } }
    WHERE  { GRAPH ?g { ?s <urn:sempkm:performedBy> ?o } }
    """,
    # 3. Event: sempkm:description → rdfs:label
    """
    DELETE { GRAPH ?g { ?s <urn:sempkm:description> ?o } }
    INSERT { GRAPH ?g { ?s <http://www.w3.org/2000/01/rdf-schema#label> ?o } }
    WHERE  { GRAPH ?g { ?s <urn:sempkm:description> ?o } }
    """,
    # 4. Comment: sempkm:commentedBy → prov:wasAttributedTo
    """
    DELETE { GRAPH ?g { ?s <urn:sempkm:commentedBy> ?o } }
    INSERT { GRAPH ?g { ?s <http://www.w3.org/ns/prov#wasAttributedTo> ?o } }
    WHERE  { GRAPH ?g { ?s <urn:sempkm:commentedBy> ?o } }
    """,
    # 5. Comment: sempkm:commentedAt → prov:generatedAtTime
    """
    DELETE { GRAPH ?g { ?s <urn:sempkm:commentedAt> ?o } }
    INSERT { GRAPH ?g { ?s <http://www.w3.org/ns/prov#generatedAtTime> ?o } }
    WHERE  { GRAPH ?g { ?s <urn:sempkm:commentedAt> ?o } }
    """,
    # 6. Query history: vocab:executedBy → prov:wasAssociatedWith
    """
    DELETE { GRAPH ?g { ?s <urn:sempkm:vocab:executedBy> ?o } }
    INSERT { GRAPH ?g { ?s <http://www.w3.org/ns/prov#wasAssociatedWith> ?o } }
    WHERE  { GRAPH ?g { ?s <urn:sempkm:vocab:executedBy> ?o } }
    """,
    # 7. Declare sempkm:Event rdfs:subClassOf prov:Activity (D104)
    #    Uses INSERT DATA — no-op if triple already exists (RDF set semantics)
    """
    INSERT DATA {
      GRAPH <urn:sempkm:vocab> {
        <urn:sempkm:Event> <http://www.w3.org/2000/01/rdf-schema#subClassOf>
                           <http://www.w3.org/ns/prov#Activity> .
      }
    }
    """,
]

# Verification queries — each should return 0 results after migration
VERIFICATION_QUERIES = [
    ("sempkm:timestamp", "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s <urn:sempkm:timestamp> ?o } }"),
    ("sempkm:performedBy", "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s <urn:sempkm:performedBy> ?o } }"),
    ("sempkm:description", "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s <urn:sempkm:description> ?o } }"),
    ("sempkm:commentedBy", "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s <urn:sempkm:commentedBy> ?o } }"),
    ("sempkm:commentedAt", "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s <urn:sempkm:commentedAt> ?o } }"),
    ("vocab:executedBy", "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s <urn:sempkm:vocab:executedBy> ?o } }"),
]

# Positive verification — these should have results
POSITIVE_QUERIES = [
    ("prov:startedAtTime", "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s <http://www.w3.org/ns/prov#startedAtTime> ?o } }"),
    ("subClassOf declaration", "ASK { GRAPH <urn:sempkm:vocab> { <urn:sempkm:Event> <http://www.w3.org/2000/01/rdf-schema#subClassOf> <http://www.w3.org/ns/prov#Activity> } }"),
]


def sparql_update(base_url: str, update: str, dry_run: bool = False) -> None:
    """Execute a SPARQL UPDATE against the triplestore."""
    if dry_run:
        logger.info("DRY RUN — would execute:\n%s", update.strip())
        return

    url = f"{base_url}/repositories/{REPOSITORY}/statements"
    resp = httpx.post(
        url,
        content=update,
        headers={"Content-Type": "application/sparql-update"},
        timeout=60.0,
    )
    resp.raise_for_status()


def sparql_query(base_url: str, query: str) -> dict:
    """Execute a SPARQL SELECT/ASK query and return JSON results."""
    url = f"{base_url}/repositories/{REPOSITORY}"
    resp = httpx.get(
        url,
        params={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def run_migration(base_url: str, dry_run: bool = False) -> bool:
    """Run all migration updates and verify results.

    Returns True if all verifications pass.
    """
    logger.info("Starting PROV-O migration against %s (dry_run=%s)", base_url, dry_run)

    # Run updates
    for i, update in enumerate(MIGRATION_UPDATES, 1):
        logger.info("Running update %d/%d...", i, len(MIGRATION_UPDATES))
        try:
            sparql_update(base_url, update, dry_run=dry_run)
        except httpx.HTTPStatusError as e:
            logger.error("Update %d failed: %s", i, e)
            return False

    if dry_run:
        logger.info("Dry run complete — no changes made")
        return True

    # Verify: old predicates should have 0 triples
    all_ok = True
    logger.info("Verifying migration...")

    for name, query in VERIFICATION_QUERIES:
        result = sparql_query(base_url, query)
        count = int(result["results"]["bindings"][0]["c"]["value"])
        if count > 0:
            logger.error("FAIL: %d triples still use %s", count, name)
            all_ok = False
        else:
            logger.info("  ✓ %s: 0 remaining", name)

    # Verify: new predicates should exist
    for name, query in POSITIVE_QUERIES:
        result = sparql_query(base_url, query)
        if "boolean" in result:
            # ASK query
            if result["boolean"]:
                logger.info("  ✓ %s: exists", name)
            else:
                logger.error("FAIL: %s not found", name)
                all_ok = False
        else:
            count = int(result["results"]["bindings"][0]["c"]["value"])
            if count > 0:
                logger.info("  ✓ %s: %d triples", name, count)
            else:
                logger.warning("  ⚠ %s: 0 triples (may be empty triplestore)", name)

    if all_ok:
        logger.info("Migration complete — all verifications passed")
    else:
        logger.error("Migration complete with failures — check output above")

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate sempkm: predicates to PROV-O equivalents")
    parser.add_argument("--dry-run", action="store_true", help="Print updates without executing")
    parser.add_argument("--triplestore-url", default=DEFAULT_URL, help=f"Triplestore base URL (default: {DEFAULT_URL})")
    args = parser.parse_args()

    success = run_migration(args.triplestore_url, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
