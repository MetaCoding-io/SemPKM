"""POST /api/commands endpoint for SemPKM writes.

Accepts single command or batch (array) payloads. All commands in a
batch are executed atomically via a single EventStore.commit() call
(all-or-nothing transaction semantics per user decision).
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter
from rdflib import URIRef

from app.auth.dependencies import require_role
from app.auth.models import User
from app.commands.dispatcher import dispatch
from app.commands.exceptions import CommandError
from app.commands.schemas import (
    Command,
    CommandResponse,
    CommandResult,
)
from app.config import settings
from app.dependencies import get_triplestore_client, get_validation_queue, get_webhook_service
from app.events.store import EventStore, Operation
from app.services.webhooks import WebhookService
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Command type to webhook event type mapping
_COMMAND_EVENT_MAP: dict[str, str] = {
    "object.create": "object.changed",
    "object.patch": "object.changed",
    "body.set": "object.changed",
    "edge.create": "edge.changed",
    "edge.patch": "edge.changed",
}


def _command_to_event_type(command_type: str) -> str | None:
    """Map a command type to a webhook event type.

    Returns the event type string, or None if the command type
    does not have a corresponding webhook event.
    """
    return _COMMAND_EVENT_MAP.get(command_type)

# TypeAdapter for parsing both single and batch command payloads
_command_adapter = TypeAdapter(Command)
_batch_adapter = TypeAdapter(list[Command])


def _parse_commands(body: Any) -> list[Command]:
    """Parse a JSON body into a list of Command objects.

    Accepts either a single command dict or a list of command dicts.
    Normalizes both forms to a list.

    Args:
        body: Parsed JSON body (dict or list).

    Returns:
        List of validated Command objects.

    Raises:
        CommandError: If the body is neither a dict nor a list.
    """
    if isinstance(body, list):
        return _batch_adapter.validate_python(body)
    elif isinstance(body, dict):
        return [_command_adapter.validate_python(body)]
    else:
        raise CommandError("Request body must be a JSON object or array")


@router.post("/commands")
async def execute_commands(
    request: Request,
    user: User = Depends(require_role("owner", "member")),
    client: TriplestoreClient = Depends(get_triplestore_client),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
    webhook_service: WebhookService = Depends(get_webhook_service),
) -> CommandResponse:
    """Execute one or more commands atomically.

    Accepts a single command object or an array of commands. All commands
    in a batch share a single event graph and transaction.

    Returns:
        CommandResponse with results for each command and the shared event IRI.
    """
    try:
        body = await request.json()
        commands = _parse_commands(body)
    except CommandError:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid request body: {str(e)}"},
        )

    try:
        # Dispatch all commands to get Operations
        operations: list[Operation] = []
        command_iris: list[tuple[str, str]] = []  # (iri, command_type)

        # Extract optional target_graph from the request body
        # Supports creating objects directly in a shared graph
        target_graph: str | None = None
        if isinstance(body, dict):
            target_graph = body.get("target_graph")
        elif isinstance(body, list) and body:
            # For batch commands, target_graph on the first item applies to all
            target_graph = body[0].get("target_graph") if isinstance(body[0], dict) else None

        for cmd in commands:
            operation = await dispatch(cmd, settings.base_namespace)
            operations.append(operation)
            # Track the primary IRI for each command's result
            primary_iri = operation.affected_iris[0] if operation.affected_iris else ""
            command_iris.append((primary_iri, cmd.command))

        # Commit all operations atomically with user provenance
        event_store = EventStore(client)
        user_iri = URIRef(f"urn:sempkm:user:{user.id}")
        event_result = await event_store.commit(
            operations,
            performed_by=user_iri,
            performed_by_role=user.role,
            target_graph=target_graph,
        )

        # Trigger async validation (non-blocking)
        await validation_queue.enqueue(
            event_iri=str(event_result.event_iri),
            timestamp=event_result.timestamp,
        )

        # Dispatch webhooks (fire-and-forget, after commit)
        # Webhook failures never break command processing
        try:
            for cmd in commands:
                event_type = _command_to_event_type(cmd.command)
                if event_type:
                    await webhook_service.dispatch(event_type, {
                        "event_iri": str(event_result.event_iri),
                        "command": cmd.command,
                        "timestamp": event_result.timestamp,
                    })
        except Exception:
            logger.warning("Webhook dispatch failed", exc_info=True)

        # Federation: send sync-alert to remote members if targeting a shared graph
        if target_graph and target_graph.startswith("urn:sempkm:shared:"):
            try:
                from app.federation.service import FederationService

                fed_service = FederationService(client, event_store)
                await fed_service.notify_remote_members_of_change(
                    shared_graph_iri=target_graph,
                    local_webid=str(user_iri),
                    event_count=len(operations),
                )
            except Exception:
                logger.warning(
                    "Federation sync alert failed for %s", target_graph,
                    exc_info=True,
                )

        # Build response
        results = [
            CommandResult(
                iri=iri,
                event_iri=str(event_result.event_iri),
                command=cmd_type,
            )
            for iri, cmd_type in command_iris
        ]

        return CommandResponse(
            results=results,
            event_iri=str(event_result.event_iri),
            timestamp=event_result.timestamp,
        )

    except CommandError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.message},
        )
    except Exception as e:
        logger.exception("Command execution failed")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal error: {str(e)}"},
        )
