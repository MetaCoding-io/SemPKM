"""CommandClient — execute platform commands via the command API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

logger = logging.getLogger(__name__)

# Which params carry IRIs that must be checked against the app prefix.
# Keys are command types; values are the param names that hold IRIs.
_IRI_PARAMS: dict[str, list[str]] = {
    "object.create": [],  # platform assigns the IRI — nothing to validate
    "object.patch": ["iri"],
    "body.set": ["iri"],
    "body.diff": ["iri"],
    "edge.create": ["source", "target"],
    "edge.patch": ["iri"],
}


class BulkAccumulator:
    """Accumulates commands for a bulk batch submission.

    Created by ``CommandClient.bulk()`` context manager. Not instantiated
    directly — use ``async with client.bulk(...) as batch:``.
    """

    def __init__(self, client: CommandClient, summary: str, source: str) -> None:
        self._client = client
        self._summary = summary
        self._source = source
        self._commands: list[dict] = []

    @property
    def operation_count(self) -> int:
        """Number of commands accumulated so far."""
        return len(self._commands)

    def add(self, command_type: str, params: dict | None = None) -> None:
        """Add a command to the batch.

        Runs the same permission checks as ``CommandClient.execute()``.

        Args:
            command_type: Command type identifier (e.g. ``"object.create"``).
            params: Additional command parameters.

        Raises:
            PermissionError: If command type or IRI params are not permitted.
        """
        # Delegate permission checks to the parent client
        self._client._check_permissions(command_type, params)

        body: dict = {"command": command_type}
        if params:
            body["params"] = params
        self._commands.append(body)

    async def _submit(self) -> dict:
        """Submit the accumulated batch to the bulk endpoint."""
        payload = {
            "commands": self._commands,
            "summary": self._summary,
            "source": self._source,
        }
        logger.debug("submitting bulk batch: %d commands", len(self._commands))
        resp = await self._client._client.post("/api/commands/bulk", json=payload)
        resp.raise_for_status()
        return resp.json()


class CommandClient:
    """Execute commands through the platform's command API.

    Args:
        client: Shared httpx.AsyncClient with platform base_url and auth.
        allowed_commands: Set of permitted command type strings.
            If empty, all commands are blocked.
        iri_prefix: Required IRI prefix for all IRI params
            (e.g. ``"urn:sempkm:app:my-app:"``).
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        allowed_commands: set[str] | None = None,
        iri_prefix: str | None = None,
    ) -> None:
        self._client = client
        self._allowed_commands = allowed_commands if allowed_commands is not None else set()
        self._iri_prefix = iri_prefix or ""

    def _check_iri_prefix(self, value: str) -> bool:
        """Check whether an IRI value is allowed under the namespace policy.

        Enforcement scope (D171): only ``urn:sempkm:app:*`` and
        ``urn:sempkm:data:*`` namespaces are restricted to the app's own
        prefix.  All other namespaces pass through unchecked so that apps
        can freely reference model-defined types, standard vocabularies,
        and user-created types.

        Decision table:

        - ``urn:sempkm:model:*``       → **allowed** (model namespace)
        - ``urn:sempkm:user-types:*``   → **allowed** (user-created types)
        - ``http://`` or ``https://``   → **allowed** (standard vocabularies)
        - ``urn:sempkm:app:{own}:*``    → **allowed** (own app namespace)
        - ``urn:sempkm:app:*`` (other)  → **blocked** (foreign app namespace)
        - ``urn:sempkm:data:*``         → **blocked** (data namespace)
        - other ``urn:*``               → **allowed** (e.g. ``urn:uuid:*``)
        - non-IRI strings               → **allowed** (not subject to checks)

        Returns:
            ``True`` if the value is allowed, ``False`` if it violates the
            namespace policy.
        """
        # Whitelisted namespaces — always allowed
        if value.startswith("urn:sempkm:model:"):
            return True
        if value.startswith("urn:sempkm:user-types:"):
            return True
        if value.startswith(("http://", "https://")):
            return True
        # Own app namespace — allowed
        if self._iri_prefix and value.startswith(self._iri_prefix):
            return True
        # Foreign app or data namespace — blocked
        if value.startswith("urn:sempkm:app:") or value.startswith("urn:sempkm:data:"):
            return False
        # All other URNs and non-IRI strings — allowed
        return True

    def _check_permissions(self, command_type: str, params: dict | None = None) -> None:
        """Validate command type whitelist and IRI prefix constraints.

        Raises:
            PermissionError: If command type is not allowed or IRI
                params violate the prefix restriction.
        """
        if command_type not in self._allowed_commands:
            raise PermissionError(
                f"Command type {command_type!r} is not permitted. "
                f"Allowed: {sorted(self._allowed_commands)}"
            )
        if params and self._iri_prefix:
            iri_fields = _IRI_PARAMS.get(command_type, [])
            for field_name in iri_fields:
                value = params.get(field_name)
                if value and not self._check_iri_prefix(value):
                    raise PermissionError(
                        f"IRI param {field_name!r}={value!r} does not start "
                        f"with required prefix {self._iri_prefix!r}"
                    )

    async def execute(self, command_type: str, params: dict | None = None) -> dict:
        """Execute a single command.

        Args:
            command_type: Command type identifier (e.g. ``"object.create"``).
            params: Additional command parameters merged into the command body.

        Returns:
            Response JSON as a dict.

        Raises:
            PermissionError: If command type is not in the whitelist or
                an IRI param violates the app prefix restriction.
        """
        self._check_permissions(command_type, params)

        body: dict = {"type": command_type}
        if params:
            body.update(params)
        payload = {"commands": [body]}
        logger.debug("executing command %s", command_type)
        resp = await self._client.post("/api/commands", json=payload)
        resp.raise_for_status()
        return resp.json()

    @asynccontextmanager
    async def bulk(
        self,
        summary: str = "",
        source: str = "",
    ) -> AsyncIterator[BulkAccumulator]:
        """Context manager that accumulates commands and sends as a bulk batch.

        On normal exit, POSTs accumulated commands to ``/api/commands/bulk``.
        On exception, discards the batch (no partial commit).

        Usage::

            async with client.bulk(summary="import contacts", source="crm-app") as batch:
                batch.add("object.create", {"type": "Contact", ...})
                batch.add("object.create", {"type": "Contact", ...})
            # batch is submitted here

        Args:
            summary: Human-readable summary for the bulk event metadata.
            source: Identifier of the source (e.g. app ID).

        Yields:
            BulkAccumulator with ``add()`` and ``operation_count``.
        """
        accumulator = BulkAccumulator(self, summary=summary, source=source)
        try:
            yield accumulator
        except Exception:
            # Discard batch on any exception
            logger.debug("bulk batch discarded due to exception")
            raise
        else:
            # Submit on clean exit (only if there are commands)
            if accumulator.operation_count > 0:
                await accumulator._submit()
