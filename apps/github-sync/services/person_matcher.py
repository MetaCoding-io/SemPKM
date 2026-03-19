"""Resolve GitHub assignees to SemPKM Person IRIs.

Uses SPARQL to look up existing Person objects by email (``foaf:mbox``
or ``crm:email``) with fallback to GitHub login (``bpkm:externalId``).
Creates new Persons via the platform command API when no match is found.
An in-memory cache avoids duplicate queries within a single sync run.

Clients are injected — any object with the same ``query`` / ``execute``
signatures as ``GraphClient`` / ``CommandClient`` works. In tests, use
simple async stubs.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("github_sync.person")

# Full IRIs used in SPARQL queries — no prefix declarations needed.
_FOAF_MBOX = "http://xmlns.com/foaf/0.1/mbox"
_CRM_EMAIL = "urn:sempkm:model:crm:email"
_BPKM = "urn:sempkm:model:basic-pkm:"
_BPKM_PERSON_TYPE = f"{_BPKM}Person"
_BPKM_EXTERNAL_ID = f"{_BPKM}externalId"


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


class PersonMatcher:
    """Resolve GitHub users to SemPKM Person IRIs.

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
        self._cache: dict[str, str] = {}  # cache_key → Person IRI

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def match(self, assignee_info: dict | None) -> str | None:
        """Find or create a Person for a GitHub assignee.

        Lookup order:
        1. Email match (foaf:mbox or crm:email) — preferred
        2. Login match (bpkm:externalId) — fallback when email is null
        3. Create new Person — if no match found

        Args:
            assignee_info: Dict with ``login`` (str) and ``email`` (str|None)
                from ``get_assignee_info()``, or None.

        Returns:
            Person IRI string, or None if assignee_info is None/empty.
        """
        if not assignee_info:
            return None

        login = assignee_info.get("login", "")
        email = assignee_info.get("email")

        if not login and not email:
            return None

        # Cache key: prefer email, fall back to login
        cache_key = (email.lower() if email else f"login:{login.lower()}")

        # 1. Cache hit
        if cache_key in self._cache:
            logger.debug("cache hit for %s", cache_key)
            return self._cache[cache_key]

        # 2. SPARQL lookup by email (if available)
        person_iri = None
        if email:
            person_iri = await self._lookup_by_email(email)

        # 3. SPARQL lookup by login (fallback)
        if person_iri is None and login:
            person_iri = await self._lookup_by_login(login)

        # 4. Create new Person if no match
        if person_iri is None:
            person_iri = await self._create_person(login, email)

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

    async def _lookup_by_login(self, login: str) -> str | None:
        """Query SPARQL for a Person with matching GitHub login as externalId."""
        sparql = (
            "SELECT ?person WHERE {\n"
            f'  ?person <{_BPKM_EXTERNAL_ID}> "{login}" .\n'
            "} LIMIT 1"
        )
        result = await self._graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0]["person"]["value"]
        return None

    async def _create_person(
        self,
        login: str,
        email: str | None,
    ) -> str:
        """Create a new bpkm:Person and return its IRI."""
        slug = _slugify(login) if login else _slugify(email.split("@")[0])
        title = login if login else email.split("@")[0]

        properties: dict[str, str] = {
            "dcterms:title": title,
        }
        if email:
            properties["foaf:mbox"] = email
        if login:
            properties[_BPKM_EXTERNAL_ID] = login

        params = {
            "type": _BPKM_PERSON_TYPE,
            "slug": slug,
            "properties": properties,
        }

        logger.debug("creating person slug=%s login=%s email=%s", slug, login, email)
        response = await self._commands.execute("object.create", params)
        return response.get("iri", "")
