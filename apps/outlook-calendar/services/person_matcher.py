"""Resolve Outlook Calendar attendees to SemPKM Person IRIs.

Uses SPARQL to look up existing Person objects by email (``foaf:mbox``
or ``crm:email``), and creates new ones via the platform command API
when no match is found.  An in-memory cache avoids duplicate queries
within a single sync run.

Clients are injected — any object with the same ``query`` / ``execute``
signatures as ``GraphClient`` / ``CommandClient`` works.  In tests, use
simple async stubs.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("outlook.sync.person_matcher")

# Full IRIs used in SPARQL queries — no prefix declarations needed.
_FOAF_MBOX = "http://xmlns.com/foaf/0.1/mbox"
_CRM_EMAIL = "urn:sempkm:model:crm:email"
_BPKM_PERSON_TYPE = "urn:sempkm:model:basic-pkm:Person"


def _slugify(text: str) -> str:
    """Convert *text* to a URL-safe slug.

    Lowercase, replace whitespace runs with a single hyphen, strip
    anything that isn't alphanumeric or hyphen.
    """
    slug = text.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def _email_local_part(email: str) -> str:
    """Return the local part of an email address (before the ``@``)."""
    return email.split("@")[0]


class PersonMatcher:
    """Resolve Outlook Calendar attendees to SemPKM Person IRIs.

    Parameters
    ----------
    graph_client:
        Anything with ``async query(sparql: str) -> dict`` that returns
        SPARQL JSON results (``{"results": {"bindings": [...]}}``.
    command_client:
        Anything with ``async execute(cmd_type: str, params: dict) -> dict``
        that returns a response containing an ``"iri"`` key.
    """

    def __init__(self, graph_client, command_client) -> None:
        self._graph = graph_client
        self._commands = command_client
        self._cache: dict[str, str] = {}  # lowered-email → Person IRI

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def match_or_create(
        self,
        email: str | None,
        display_name: str | None,
    ) -> str | None:
        """Find or create a Person for *email*.

        Returns the Person IRI, or ``None`` if *email* is ``None``
        or empty.
        """
        if not email:
            return None

        cache_key = email.lower()

        # 1. Cache hit
        if cache_key in self._cache:
            logger.debug("cache hit for %s", cache_key)
            return self._cache[cache_key]

        # 2. SPARQL lookup
        person_iri = await self._lookup_by_email(email)
        if person_iri is not None:
            self._cache[cache_key] = person_iri
            return person_iri

        # 3. Create new Person
        person_iri = await self._create_person(email, display_name)
        self._cache[cache_key] = person_iri
        return person_iri

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _lookup_by_email(self, email: str) -> str | None:
        """Query SPARQL for a Person with matching email (case-insensitive)."""
        sparql = (
            "SELECT ?person WHERE {\n"
            f"  {{ ?person <{_FOAF_MBOX}> ?email }}\n"
            "  UNION\n"
            f"  {{ ?person <{_CRM_EMAIL}> ?email }}\n"
            f'  FILTER(LCASE(STR(?email)) = LCASE("{email}"))\n'
            "} LIMIT 1"
        )
        result = await self._graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0]["person"]["value"]
        return None

    async def _create_person(
        self,
        email: str,
        display_name: str | None,
    ) -> str:
        """Create a new bpkm:Person and return its IRI."""
        slug = (
            _slugify(display_name) if display_name else _slugify(_email_local_part(email))
        )
        title = display_name if display_name else _email_local_part(email)

        params = {
            "type": _BPKM_PERSON_TYPE,
            "slug": slug,
            "properties": {
                "dcterms:title": title,
                "foaf:mbox": email,
            },
        }

        logger.debug("creating person slug=%s email=%s", slug, email)
        response = await self._commands.execute("object.create", params)
        return response.get("iri", "")
