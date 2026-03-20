"""LoopGuard — lightweight in-memory TTL cache to prevent push→poll echo loops.

When push sync updates a Monday.com item it calls ``mark_pushed`` to record
the (item_id, column_id) pair with the current timestamp.  When pull sync
later encounters the same item, ``is_echo`` returns True while the mark is
still within the TTL window, and the item is skipped.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger("monday_sync.loop_guard")


class LoopGuard:
    """TTL-based echo guard for push/pull sync loops."""

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._ttl = ttl_seconds
        self._marks: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mark_pushed(self, item_id: str, column_id: str = "*") -> None:
        """Record that *item_id*/*column_id* was just pushed."""
        key = self._key(item_id, column_id)
        now = time.time()
        self._marks[key] = now
        logger.debug("mark_pushed key=%s t=%.3f", key, now)

    def is_echo(self, item_id: str, column_id: str = "*") -> bool:
        """Return ``True`` if the item was pushed within the TTL window."""
        key = self._key(item_id, column_id)
        mark_time = self._marks.get(key)
        if mark_time is None:
            return False
        age = time.time() - mark_time
        hit = age < self._ttl
        if hit:
            logger.debug("is_echo HIT key=%s age=%.3fs ttl=%.1fs", key, age, self._ttl)
        return hit

    def cleanup(self) -> int:
        """Remove expired entries. Return the number removed."""
        now = time.time()
        expired = [k for k, t in self._marks.items() if now - t >= self._ttl]
        for k in expired:
            del self._marks[k]
        if expired:
            logger.debug("cleanup removed %d expired marks", len(expired))
        return len(expired)

    def __len__(self) -> int:
        return len(self._marks)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(item_id: str, column_id: str) -> str:
        return f"{item_id}:{column_id}"
