"""Command dispatcher: maps command type strings to handler functions.

The dispatcher is the routing layer between the API endpoint and the
per-command handlers. It looks up the handler by the command's discriminator
value and calls it with the command params and base namespace.
"""

from collections.abc import Callable

from app.commands.exceptions import InvalidCommandError
from app.commands.schemas import Command
from app.events.store import Operation


# Handler type: async function taking (params, base_namespace) -> Operation
HandlerFunc = Callable[..., Operation]

# Registry populated at module load time (after handler imports)
HANDLER_REGISTRY: dict[str, HandlerFunc] = {}


def _register_handlers() -> None:
    """Import and register all command handlers.

    Called once at module load time. Deferred import avoids circular
    dependencies between dispatcher and handler modules.
    """
    from app.commands.handlers.object_create import handle_object_create
    from app.commands.handlers.object_patch import handle_object_patch
    from app.commands.handlers.body_set import handle_body_set
    from app.commands.handlers.edge_create import handle_edge_create
    from app.commands.handlers.edge_patch import handle_edge_patch

    HANDLER_REGISTRY["object.create"] = handle_object_create
    HANDLER_REGISTRY["object.patch"] = handle_object_patch
    HANDLER_REGISTRY["body.set"] = handle_body_set
    HANDLER_REGISTRY["edge.create"] = handle_edge_create
    HANDLER_REGISTRY["edge.patch"] = handle_edge_patch


async def dispatch(command: Command, base_namespace: str) -> Operation:
    """Dispatch a command to its handler and return the resulting Operation.

    Args:
        command: A validated Command model (discriminated union member).
        base_namespace: The configurable base namespace for IRI minting.

    Returns:
        An Operation dataclass ready for EventStore.commit().

    Raises:
        InvalidCommandError: If the command type is not registered.
    """
    if not HANDLER_REGISTRY:
        _register_handlers()

    handler = HANDLER_REGISTRY.get(command.command)
    if handler is None:
        raise InvalidCommandError(f"Unknown command type: {command.command}")

    return await handler(command.params, base_namespace)
