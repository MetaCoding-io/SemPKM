"""Command-specific exceptions for the SemPKM command API.

Provides a hierarchy of errors that map to HTTP status codes for
proper error responses from the command endpoint.
"""


class CommandError(Exception):
    """Base exception for command processing errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code to return (default 400).
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ObjectNotFoundError(CommandError):
    """Raised when a patch targets a non-existent object or edge."""

    def __init__(self, iri: str) -> None:
        super().__init__(
            message=f"Object not found: {iri}",
            status_code=404,
        )


class InvalidCommandError(CommandError):
    """Raised when a command is malformed or unrecognized."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=400)


class ConflictError(CommandError):
    """Raised when an operation conflicts with existing state (e.g., slug collision)."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=409)
