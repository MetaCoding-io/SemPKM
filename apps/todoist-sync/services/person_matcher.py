"""Resolve Todoist task assignees to SemPKM Person IRIs.

Uses SPARQL to look up existing Person objects by email (``foaf:mbox``
or ``crm:email``) with fallback to name-based lookup (``bpkm:externalId``).
Creates new Persons via the platform command API when no match is found.
An in-memory cache avoids duplicate queries within a single sync run.

Adapted from github-sync's person_matcher.py — Todoist provides ``name``
and ``email`` fields (from collaborators/assignee data) instead of
GitHub's ``login``.

Clients are injected — any object with the same ``query`` / ``execute``
signatures as ``GraphClient`` / ``CommandClient`` works. In tests, use
simple async stubs.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("todoist.sync.person")

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
    """Resolve Todoist users to SemPKM Person IRIs.

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
        """Find or create a Person for a Todoist assignee.

        Lookup order:
        1. Email match (foaf:mbox or crm:email) — preferred
        2. Name/ID match (bpkm:externalId) — fallback
        3. Create new Person — if no match found

        Args:
            assignee_info: Dict with ``name`` (str) and ``email`` (str|None)
                from Todoist collaborator data, or None.

        Returns:
            Person IRI string, or None if assignee_info is None/empty.
        """
        if not assignee_info:
            return None

        name = assignee_info.get("name", "")
        email = assignee_info.get("email")

        if not name and not email:
            return None

        # Cache key: prefer email, fall back to name
        cache_key = (email.lower() if email else f"name:{name.lower()}")

        # 1. Cache hit
        if cache_key in self._cache:
            logger.debug("cache hit for %s", cache_key)
            return self._cache[cache_key]

        # 2. SPARQL lookup by email (if available)
        person_iri = None
        if email:
            person_iri = await self._lookup_by_email(email)

        # 3. SPARQL lookup by name/externalId (fallback)
        if person_iri is None and name:
            person_iri = await self._lookup_by_external_id(name)

        # 4. Create new Person if no match
        if person_iri is None:
            person_iri = await self._create_person(name, email)

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

    async def _lookup_by_external_id(self, name: str) -> str | None:
        """Query SPARQL for a Person with matching externalId."""
        sparql = (
            "SELECT ?person WHERE {\n"
            f'  ?person <{_BPKM_EXTERNAL_ID}> "{name}" .\n'
            "} LIMIT 1"
        )
        result = await self._graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0]["person"]["value"]
        return None

    async def _create_person(
        self,
        name: str,
        email: str | None,
    ) -> str:
        """Create a new bpkm:Person and return its IRI."""
        slug = _slugify(name) if name else _slugify(email.split("@")[0])
        title = name if name else email.split("@")[0]

        properties: dict[str, str] = {
            "dcterms:title": title,
        }
        if email:
            properties["foaf:mbox"] = email
        if name:
            properties[_BPKM_EXTERNAL_ID] = name

        params = {
            "type": _BPKM_PERSON_TYPE,
            "slug": slug,
            "properties": properties,
        }

        logger.debug("creating person slug=%s name=%s email=%s", slug, name, email)
        response = await self._commands.execute("object.create", params)
        return response.get("iri", "")
