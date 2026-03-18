"""SettingsClient — app settings backed by state graph with key prefix.

Delegates to ``StateClient`` using a ``settings:`` key prefix to
namespace settings separately from general app state.
"""

from __future__ import annotations

import logging

from sempkm_app_sdk.clients.state import StateClient

logger = logging.getLogger(__name__)

SETTINGS_PREFIX = "settings:"


class SettingsClient:
    """App settings client that delegates to StateClient with key prefix.

    Args:
        state: A ``StateClient`` instance for the same app.
    """

    def __init__(self, state: StateClient) -> None:
        self._state = state

    async def get(self, key: str) -> str | None:
        """Get a setting value.

        Args:
            key: Setting key (without prefix).

        Returns:
            The setting value, or None if not set.
        """
        prefixed = f"{SETTINGS_PREFIX}{key}"
        logger.debug("settings get key=%s", key)
        return await self._state.get(prefixed)

    async def set(self, key: str, value: str) -> None:
        """Set a setting value.

        Args:
            key: Setting key (without prefix).
            value: Value string to store.
        """
        prefixed = f"{SETTINGS_PREFIX}{key}"
        logger.debug("settings set key=%s", key)
        await self._state.set(prefixed, value)
