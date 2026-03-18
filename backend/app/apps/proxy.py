"""AppProxy — HTTP forwarding to app subprocesses over Unix domain sockets.

Routes platform HTTP requests to the correct app subprocess via httpx
``AsyncHTTPTransport(uds=...)`` with JWT token injection.  Maintains a
connection-pooled client per app_id for efficiency.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from fastapi import Request
from fastapi.responses import Response

if TYPE_CHECKING:
    from app.apps.manager import AppManager

logger = logging.getLogger(__name__)


class AppNotReachableError(Exception):
    """Raised when the app's UDS socket is missing or connection fails."""


class AppProxy:
    """Forward HTTP requests to app subprocesses over UDS."""

    def __init__(self, manager: AppManager) -> None:
        self._manager = manager
        self._clients: dict[str, httpx.AsyncClient] = {}

    async def forward(
        self,
        app_id: str,
        path: str,
        request: Request,
    ) -> Response:
        """Forward an incoming HTTP request to the app subprocess.

        Looks up the UDS socket for *app_id*, injects the current JWT
        as ``X-SemPKM-App-Token``, and returns the upstream response.

        Raises:
            AppNotReachableError: If the socket file doesn't exist or
                the connection fails.
        """
        socket_path = Path(f"/tmp/sempkm-app-{app_id}.sock")

        if not socket_path.exists():
            logger.warning(
                "Socket missing for app %s at %s", app_id, socket_path
            )
            raise AppNotReachableError(
                f"Socket not found for app {app_id}"
            )

        client = self._get_or_create_client(app_id, socket_path)

        # Build target URL (host is ignored for UDS but required by httpx)
        target_url = f"http://localhost/{path}"

        # Copy incoming headers, inject app token
        headers = dict(request.headers)
        # Remove hop-by-hop headers that shouldn't be forwarded
        headers.pop("host", None)
        headers.pop("transfer-encoding", None)

        token = self._manager.get_token(app_id)
        if token:
            headers["x-sempkm-app-token"] = token

        body = await request.body()

        try:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
        except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            logger.warning(
                "Connection failed for app %s: %s", app_id, exc
            )
            raise AppNotReachableError(
                f"Connection failed for app {app_id}: {exc}"
            ) from exc

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=dict(upstream.headers),
        )

    def _get_or_create_client(
        self,
        app_id: str,
        socket_path: Path,
    ) -> httpx.AsyncClient:
        """Return a pooled httpx client for *app_id*, creating if needed."""
        if app_id not in self._clients:
            transport = httpx.AsyncHTTPTransport(uds=str(socket_path))
            self._clients[app_id] = httpx.AsyncClient(transport=transport)
            logger.debug("Created httpx client for app %s", app_id)
        return self._clients[app_id]

    async def invoke_task(
        self,
        app_id: str,
        task_id: str,
        run_id: str,
    ) -> tuple[int, str]:
        """Invoke a scheduled task on an app subprocess via UDS.

        Posts to ``/_tasks/{task_id}`` on the app's socket.
        Returns ``(status_code, response_body)``.

        Raises:
            AppNotReachableError: If the socket is missing or connection fails.
        """
        socket_path = Path(f"/tmp/sempkm-app-{app_id}.sock")

        if not socket_path.exists():
            raise AppNotReachableError(
                f"Socket not found for app {app_id}"
            )

        client = self._get_or_create_client(app_id, socket_path)

        target_url = f"http://localhost/_tasks/{task_id}"

        headers: dict[str, str] = {
            "x-sempkm-task-run": run_id,
        }

        token = self._manager.get_token(app_id)
        if token:
            headers["x-sempkm-app-token"] = token

        try:
            resp = await client.post(
                target_url,
                headers=headers,
                timeout=300.0,  # tasks may be long-running
            )
            return resp.status_code, resp.text
        except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            raise AppNotReachableError(
                f"Connection failed for app {app_id}: {exc}"
            ) from exc

    async def close_client(self, app_id: str) -> None:
        """Close and remove the pooled client for *app_id*."""
        client = self._clients.pop(app_id, None)
        if client:
            await client.aclose()
            logger.debug("Closed httpx client for app %s", app_id)

    async def close_all(self) -> None:
        """Close all pooled clients (platform shutdown)."""
        for app_id in list(self._clients):
            await self.close_client(app_id)
