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

from app.commands.dispatcher import dispatch
from app.commands.exceptions import CommandError
from app.commands.schemas import (
    Command,
    CommandResponse,
    CommandResult,
)
from app.config import settings
from app.dependencies import get_triplestore_client, get_validation_queue
from app.events.store import EventStore, Operation
from app.triplestore.client import TriplestoreClient
from app.validation.queue import AsyncValidationQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

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
    client: TriplestoreClient = Depends(get_triplestore_client),
    validation_queue: AsyncValidationQueue = Depends(get_validation_queue),
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

        for cmd in commands:
            operation = await dispatch(cmd, settings.base_namespace)
            operations.append(operation)
            # Track the primary IRI for each command's result
            primary_iri = operation.affected_iris[0] if operation.affected_iris else ""
            command_iris.append((primary_iri, cmd.command))

        # Commit all operations atomically
        event_store = EventStore(client)
        event_result = await event_store.commit(operations)

        # Trigger async validation (non-blocking)
        await validation_queue.enqueue(
            event_iri=str(event_result.event_iri),
            timestamp=event_result.timestamp,
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
