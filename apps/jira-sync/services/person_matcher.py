"""Resolve Jira users to SemPKM Person IRIs.

Uses SPARQL to look up existing Person objects by email (``foaf:mbox``
or ``crm:email``) with fallback to Jira accountId (``bpkm:externalId``).
When no email is available in the call arguments, fetches the user's
email from the Jira API via ``get_user(account_id)``.
Creates new Persons via the platform command API when no match is found.
An in-memory cache avoids duplicate Jira API calls and SPARQL queries
within a single sync run.

Clients are injected — any object with the same ``query`` / ``execute``
/ ``get_user`` signatures works. In tests, use simple async stubs.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("jira_sync.person")

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
    """Resolve Jira users to SemPKM Person IRIs.

    Parameters
    ----------
    graph_client:
        Anything with ``async query(sparql: str) -> dict`` that returns
        SPARQL JSON results (``{"results": {"bindings": [...]}}``.
    command_client:
        Anything with ``async execute(cmd_type: str, params: dict) -> dict``
        that returns a response containing an ``"iri"`` key.
    jira_client:
        Anything with ``async get_user(account_id: str) -> dict`` that
        returns a Jira user dict with ``emailAddress`` and ``displayName``.
        Needed because Jira issue payloads only include accountId, not
        email — an extra API call is required per unique user.
    """

    def __init__(self, graph_client, command_client, jira_client) -> None:
        self._graph = graph_client
        self._commands = command_client
        self._jira = jira_client
        self._cache: dict[str, str] = {}  # account_id → Person IRI

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve(
        self,
        account_id: str | None,
        display_name: str | None = None,
        email: str | None = None,
    ) -> str | None:
        """Find or create a Person for a Jira user.

        Lookup order:
        1. Cache hit by account_id
        2. Email match via SPARQL (foaf:mbox or crm:email)
        3. If no email provided, fetch from Jira API and retry SPARQL
        4. accountId match via SPARQL (bpkm:externalId)
        5. Create new Person on miss

        Args:
            account_id: Jira accountId string. If None, returns None.
            display_name: User's display name (for person creation).
            email: User's email, if already known. Often None in issue
                payloads — requires a ``get_user`` call to retrieve.

        Returns:
            Person IRI string, or None if account_id is None.
        """
        if account_id is None:
            return None

        # 1. Cache hit
        if account_id in self._cache:
            logger.debug("cache hit for account_id=%s", account_id)
            return self._cache[account_id]

        # 2. SPARQL lookup by email (if provided)
        person_iri = None
        if email:
            person_iri = await self._lookup_by_email(email)

        # 3. If no email was provided, try fetching from Jira API
        if person_iri is None and not email:
            try:
                user = await self._jira.get_user(account_id)
                fetched_email = user.get("emailAddress")
                if not display_name:
                    display_name = user.get("displayName")
                if fetched_email:
                    email = fetched_email
                    person_iri = await self._lookup_by_email(email)
            except Exception as exc:
                logger.warning(
                    "Failed to fetch Jira user %s: %s", account_id, exc
                )

        # 4. Fallback: SPARQL lookup by accountId (bpkm:externalId)
        if person_iri is None:
            person_iri = await self._lookup_by_account_id(account_id)

        # 5. Create new Person if no match
        if person_iri is None:
            person_iri = await self._create_person(
                account_id, display_name, email
            )

        self._cache[account_id] = person_iri
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

    async def _lookup_by_account_id(self, account_id: str) -> str | None:
        """Query SPARQL for a Person with matching Jira accountId."""
        sparql = (
            "SELECT ?person WHERE {\n"
            f'  ?person <{_BPKM_EXTERNAL_ID}> "{account_id}" .\n'
            "} LIMIT 1"
        )
        result = await self._graph.query(sparql)
        bindings = result.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0]["person"]["value"]
        return None

    async def _create_person(
        self,
        account_id: str,
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
            slug = _slugify(account_id)
            title = account_id

        properties: dict[str, str] = {
            "dcterms:title": title,
            _BPKM_EXTERNAL_ID: account_id,
        }
        if email:
            properties["foaf:mbox"] = email

        params = {
            "type": _BPKM_PERSON_TYPE,
            "slug": slug,
            "properties": properties,
        }

        logger.debug(
            "creating person slug=%s account_id=%s email=%s",
            slug, account_id, email,
        )
        response = await self._commands.execute("object.create", params)
        return response.get("iri", "")
