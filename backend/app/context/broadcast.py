"""SSE broadcast manager for real-time context updates.

Fan-out pattern: multiple SSE clients subscribe via asyncio.Queue.
When a context update arrives, the publisher pushes an event to all
connected clients. Clients that fall behind (full queue) are silently
dropped to prevent backpressure.

Reuses ``SSEEvent`` from the lint broadcast module for consistency.
"""

import asyncio
import logging

from app.lint.broadcast import SSEEvent

logger = logging.getLogger(__name__)


class ContextBroadcast:
    """Fan-out SSE broadcast manager for context events.

    Identical pattern to ``LintBroadcast`` — each connected SSE
    client gets its own queue. On publish, the event is pushed to
    all queues. Full queues cause the subscriber to be dropped.
    """

    def __init__(self) -> None:
        self._clients: set[asyncio.Queue[SSEEvent]] = set()

    def subscribe(self) -> asyncio.Queue[SSEEvent]:
        """Create a new subscriber queue and register it."""
        q: asyncio.Queue[SSEEvent] = asyncio.Queue(maxsize=16)
        self._clients.add(q)
        logger.debug("Context SSE client subscribed (total: %d)", len(self._clients))
        return q

    def unsubscribe(self, q: asyncio.Queue[SSEEvent]) -> None:
        """Remove a subscriber queue."""
        self._clients.discard(q)
        logger.debug(
            "Context SSE client unsubscribed (total: %d)", len(self._clients)
        )

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
                logger.warning("Context SSE client queue full, dropping subscriber")
                to_remove.append(q)
        for q in to_remove:
            self._clients.discard(q)

    @property
    def client_count(self) -> int:
        """Return the number of connected SSE clients."""
        return len(self._clients)
