"""SSE broadcast manager for real-time lint event push.

Fan-out pattern: multiple SSE clients subscribe via asyncio.Queue.
When a validation run completes, the publisher pushes a summary event
to all connected clients. Clients that fall behind (full queue) are
silently dropped to prevent backpressure.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """A server-sent event with event type and JSON-serializable data."""

    event: str
    data: dict[str, Any]

    def format(self) -> str:
        """Format as SSE wire protocol text."""
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class LintBroadcast:
    """Fan-out SSE broadcast manager for lint events.

    Maintains a set of asyncio.Queue subscribers. Each connected SSE
    client gets its own queue. On publish, the event is pushed to all
    queues. Queues that are full (client not consuming fast enough)
    are silently discarded to prevent backpressure from slow clients.
    """

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[SSEEvent]] = set()

    def subscribe(self) -> asyncio.Queue[SSEEvent]:
        """Create a new subscriber queue and register it.

        Returns:
            An asyncio.Queue that will receive SSEEvent instances.
        """
        q: asyncio.Queue[SSEEvent] = asyncio.Queue(maxsize=16)
        self._clients.add(q)
        logger.debug("SSE client subscribed (total: %d)", len(self._clients))
        return q

    def unsubscribe(self, q: asyncio.Queue[SSEEvent]) -> None:
        """Remove a subscriber queue."""
        self._clients.discard(q)
        logger.debug("SSE client unsubscribed (total: %d)", len(self._clients))

    async def publish(self, event: SSEEvent) -> None:
        """Push an event to all connected subscribers.

        Clients with full queues are silently dropped (removed from
        the subscriber set) to prevent backpressure.
        """
        to_remove: list[asyncio.Queue[SSEEvent]] = []
        for q in self._clients:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("SSE client queue full, dropping subscriber")
                to_remove.append(q)
        for q in to_remove:
            self._clients.discard(q)

    @property
    def client_count(self) -> int:
        """Return the number of connected SSE clients."""
        return len(self._clients)
