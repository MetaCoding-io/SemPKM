"""Resolve Monday.com users to SemPKM Person IRIs.

Uses SPARQL to look up existing Person objects by email (``foaf:mbox``
or ``crm:email``) with fallback to Monday.com user_id (``bpkm:externalId``).
When no email is available in the call arguments, fetches the user's
email from Monday.com via ``monday_client.get_users([user_id])``.
Creates new Persons via the platform command API when no match is found.
An in-memory cache avoids duplicate Monday.com API calls and SPARQL queries
within a single sync run.

Clients are injected — any object with the same ``query`` / ``execute``
/ ``get_users`` signatures works.  In tests, use simple async stubs.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("monday_sync.person")

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
    """Resolve Monday.com users to SemPKM Person IRIs.

    Parameters
    ----------
    graph_client:
        Anything with ``async query(sparql: str) -> dict`` that returns
        SPARQL JSON results (``{"results": {"bindings": [...]}}``.
    command_client:
        Anything with ``async execute(cmd_type: str, params: dict) -> dict``
        that returns a response containing an ``"iri"`` key.
    monday_client:
        Anything with ``async get_users(user_ids: list[int]) -> list[dict]``
        that returns a list of user dicts with ``id``, ``name``, ``email``.
        Needed because Monday.com item payloads only include numeric user
        IDs — an extra API call is required per unique user.
    """

    def __init__(self, graph_client, command_client, monday_client) -> None:
        self._graph = graph_client
        self._commands = command_client
        self._monday = monday_client
        self._cache: dict[str, str] = {}  # str(user_id) → Person IRI

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve(
        self,
        user_id: int | str | None,
        display_name: str | None = None,
        email: str | None = None,
    ) -> str | None:
        """Find or create a Person for a Monday.com user.

        Lookup order:
        1. Cache hit by user_id (converted to str for cache key)
        2. Email match via SPARQL (foaf:mbox or crm:email)
        3. If no email provided, fetch from Monday.com API and retry SPARQL
        4. user_id match via SPARQL (bpkm:externalId)
        5. Create new Person on miss

        Args:
            user_id: Monday.com numeric user ID.  If None, returns None.
            display_name: User's display name (for person creation).
            email: User's email, if already known.  Often not present
                in item column values — requires a ``get_users`` call.

        Returns:
            Person IRI string, or None if user_id is None.
        """
        if user_id is None:
            return None

        cache_key = str(user_id)

        # 1. Cache hit
        if cache_key in self._cache:
            logger.debug("cache hit for user_id=%s", cache_key)
            return self._cache[cache_key]

        # 2. SPARQL lookup by email (if provided)
        person_iri = None
        if email:
            person_iri = await self._lookup_by_email(email)

        # 3. If no email was provided, try fetching from Monday.com API
        if person_iri is None and not email:
            try:
                users = await self._monday.get_users([int(cache_key)])
                if users:
                    user = users[0]
                    fetched_email = user.get("email")
                    if not display_name:
                        display_name = user.get("name")
                    if fetched_email:
                        email = fetched_email
                        person_iri = await self._lookup_by_email(email)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch Monday.com user %s: %s", cache_key, exc
                )

        # 4. Fallback: SPARQL lookup by user_id (bpkm:externalId)
        if person_iri is None:
            person_iri = await self._lookup_by_user_id(cache_key)

        # 5. Create new Person if no match
        if person_iri is None:
            person_iri = await self._create_person(
                cache_key, display_name, email
            )

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

    async def _lookup_by_user_id(self, user_id: str) -> str | None:
        """Query SPARQL for a Person with matching Monday.com user_id."""
        sparql = (
            "SELECT ?person WHERE {\n"
            f'  ?person <{_BPKM_EXTERNAL_ID}> "{user_id}" .\n'
            "} LIMIT 1"
        )
        result = await self._graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0]["person"]["value"]
        return None

    async def _create_person(
        self,
        user_id: str,
        display_name: str | None,
        email: str | None,
    ) -> str:
        """Create a new bpkm:Person and return its IRI."""
        # Determine slug and title from available info
        if display_name:
            slug = _slugify(display_name)
            title = display_name
        elif email:
            local_part = email.split("@")[0]
            slug = _slugify(local_part)
            title = local_part
        else:
            slug = _slugify(user_id)
            title = user_id

        properties: dict[str, str] = {
            "dcterms:title": title,
            _BPKM_EXTERNAL_ID: user_id,
        }
        if email:
            properties["foaf:mbox"] = email

        params = {
            "type": _BPKM_PERSON_TYPE,
            "slug": slug,
            "properties": properties,
        }

        logger.debug(
            "creating person slug=%s user_id=%s email=%s",
            slug, user_id, email,
        )
        response = await self._commands.execute("object.create", params)
        return response.get("iri", "")
