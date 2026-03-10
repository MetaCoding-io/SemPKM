"""SSE broadcast manager for real-time vault scan progress.

Fan-out pattern: multiple SSE clients subscribe via asyncio.Queue.
When scan progress updates occur, the publisher pushes events to all
connected clients. Thread-safe publish for use from scanner thread.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """A server-sent event with event type and JSON-serializable data."""

    event: str
    data: dict[str, Any]

    def format(self) -> str:
        """Format as SSE wire protocol text."""
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class ScanBroadcast:
    """Fan-out SSE broadcast manager for scan progress events.

    Maintains a set of asyncio.Queue subscribers. Each connected SSE
    client gets its own queue. On publish, the event is pushed to all
    queues. Thread-safe publish via loop.call_soon_threadsafe() since
    the scanner runs in a background thread.
    """

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[SSEEvent]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def subscribe(self) -> asyncio.Queue[SSEEvent]:
        """Create a new subscriber queue and register it."""
        q: asyncio.Queue[SSEEvent] = asyncio.Queue(maxsize=64)
        self._clients.add(q)
        # Capture the event loop for thread-safe publishing
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        logger.debug("Scan SSE client subscribed (total: %d)", len(self._clients))
        return q

    def unsubscribe(self, q: asyncio.Queue[SSEEvent]) -> None:
        """Remove a subscriber queue."""
        self._clients.discard(q)
        logger.debug("Scan SSE client unsubscribed (total: %d)", len(self._clients))

    def publish(self, event: SSEEvent) -> None:
        """Push an event to all connected subscribers.

        Thread-safe: uses call_soon_threadsafe when called from a
        background thread (e.g. the vault scanner thread).
        """
        try:
            loop = self._loop or asyncio.get_running_loop()
        except RuntimeError:
            # No event loop available — log and skip
            logger.warning("No event loop for SSE publish, skipping event: %s", event.event)
            return

        loop.call_soon_threadsafe(self._dispatch, event)

    def _dispatch(self, event: SSEEvent) -> None:
        """Synchronous dispatch called on the event loop thread."""
        to_remove: list[asyncio.Queue[SSEEvent]] = []
        for q in self._clients:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Scan SSE client queue full, dropping subscriber")
                to_remove.append(q)
        for q in to_remove:
            self._clients.discard(q)

    @property
    def client_count(self) -> int:
        """Return the number of connected SSE clients."""
        return len(self._clients)


async def stream_sse(
    queue: asyncio.Queue[SSEEvent],
    terminal_events: set[str] | None = None,
    shutdown_event: asyncio.Event | None = None,
) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE-formatted strings from a subscriber queue.

    Sends a keepalive comment every 30 seconds to prevent proxy timeouts.

    Args:
        queue: The subscriber queue to read events from.
        terminal_events: Set of event names that signal end of stream.
            Defaults to {"scan_complete", "scan_error"} for backward
            compatibility.
        shutdown_event: Optional cooperative shutdown signal.  When set the
            generator exits promptly so uvicorn reload does not hang.
    """
    if terminal_events is None:
        terminal_events = {"scan_complete", "scan_error"}

    while not (shutdown_event and shutdown_event.is_set()):
        try:
            if shutdown_event:
                # Race queue.get() against shutdown signal.
                get_task = asyncio.ensure_future(queue.get())
                shutdown_task = asyncio.ensure_future(shutdown_event.wait())
                done, pending = await asyncio.wait(
                    {get_task, shutdown_task},
                    timeout=30.0,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                if shutdown_task in done:
                    break
                if get_task in done:
                    event = get_task.result()
                    yield event.format()
                    if event.event in terminal_events:
                        break
                else:
                    yield ": keepalive\n\n"
            else:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield event.format()
                if event.event in terminal_events:
                    break
        except asyncio.TimeoutError:
            # Send keepalive comment
            yield ": keepalive\n\n"
        except asyncio.CancelledError:
            break
