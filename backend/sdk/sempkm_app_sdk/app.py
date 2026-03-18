"""App class — decorator-based handler registration and ASGI app builder.

Apps create an ``App`` instance, register handlers via decorators, and the
SDK runner calls ``build_asgi_app()`` to produce a FastAPI application with
system endpoints (health, lifecycle, tasks) and user routes.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class App:
    """Developer-facing app class with decorator-based handler registration.

    Usage::

        from sempkm_app_sdk import App

        app = App("my-app")

        @app.on_startup
        async def startup(ctx):
            print("App started")

        @app.route("/_fragments/main")
        async def main_fragment(request):
            return HTMLResponse("<h1>Hello</h1>")
    """

    def __init__(self, app_id: str) -> None:
        self.app_id = app_id
        self._lifecycle_handlers: dict[str, Callable] = {}
        self._task_handlers: dict[str, Callable] = {}
        self._routes: list[tuple[list[str], str, Callable]] = []

    # ── Lifecycle decorators ──

    @property
    def on_install(self) -> Callable:
        """Register an install lifecycle handler."""
        def decorator(fn: Callable) -> Callable:
            self._lifecycle_handlers["install"] = fn
            return fn
        return decorator

    @property
    def on_startup(self) -> Callable:
        """Register a startup lifecycle handler."""
        def decorator(fn: Callable) -> Callable:
            self._lifecycle_handlers["startup"] = fn
            return fn
        return decorator

    @property
    def on_shutdown(self) -> Callable:
        """Register a shutdown lifecycle handler."""
        def decorator(fn: Callable) -> Callable:
            self._lifecycle_handlers["shutdown"] = fn
            return fn
        return decorator

    @property
    def on_uninstall(self) -> Callable:
        """Register an uninstall lifecycle handler."""
        def decorator(fn: Callable) -> Callable:
            self._lifecycle_handlers["uninstall"] = fn
            return fn
        return decorator

    # ── Task decorator ──

    def task(self, task_id: str) -> Callable:
        """Register a task handler for the given task_id."""
        def decorator(fn: Callable) -> Callable:
            self._task_handlers[task_id] = fn
            return fn
        return decorator

    # ── Route decorator ──

    def route(self, path: str, methods: list[str] | None = None) -> Callable:
        """Register a user route handler."""
        if methods is None:
            methods = ["GET"]
        def decorator(fn: Callable) -> Callable:
            self._routes.append((methods, path, fn))
            return fn
        return decorator

    # ── ASGI app builder ──

    def build_asgi_app(self, ctx: Any) -> FastAPI:
        """Build and return a FastAPI application with system + user routes.

        Args:
            ctx: An ``AppContext`` instance stored on ``app.state.ctx``.

        Returns:
            Configured FastAPI application.
        """
        from sempkm_app_sdk.context import AppContext

        asgi_app = FastAPI(title=f"SemPKM App: {self.app_id}")
        asgi_app.state.ctx = ctx
        asgi_app.state.sdk_app = self

        # ── System endpoints ──

        @asgi_app.get("/_health")
        async def health() -> dict:
            return {"status": "ok"}

        @asgi_app.post("/_lifecycle/{hook}")
        async def lifecycle(hook: str, request: Request) -> JSONResponse:
            if not _validate_token(request, ctx):
                return JSONResponse(
                    {"detail": "Invalid or missing app token"},
                    status_code=403,
                )
            handler = self._lifecycle_handlers.get(hook)
            if handler is None:
                logger.debug("no handler for lifecycle hook %s", hook)
                return JSONResponse(
                    {"detail": f"No handler for lifecycle hook: {hook}"},
                    status_code=404,
                )
            logger.debug("dispatching lifecycle hook %s for %s", hook, self.app_id)
            result = handler(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            return JSONResponse({"status": "ok", "hook": hook})

        @asgi_app.post("/_tasks/{task_id}")
        async def run_task(task_id: str, request: Request) -> JSONResponse:
            if not _validate_token(request, ctx):
                return JSONResponse(
                    {"detail": "Invalid or missing app token"},
                    status_code=403,
                )
            handler = self._task_handlers.get(task_id)
            if handler is None:
                logger.debug("no handler for task %s", task_id)
                return JSONResponse(
                    {"detail": f"No handler for task: {task_id}"},
                    status_code=404,
                )
            logger.debug("dispatching task %s for %s", task_id, self.app_id)
            result = handler(ctx)
            if asyncio.iscoroutine(result):
                result = await result
            return JSONResponse({"status": "ok", "task_id": task_id})

        # ── User routes ──

        for methods, path, handler in self._routes:
            asgi_app.add_api_route(path, handler, methods=methods)

        return asgi_app


def _validate_token(request: Request, ctx: Any) -> bool:
    """Validate the ``X-SemPKM-App-Token`` header via shared-secret comparison.

    Returns True if the token matches, False otherwise.
    """
    token = request.headers.get("X-SemPKM-App-Token")
    if not token:
        logger.warning("missing X-SemPKM-App-Token header")
        return False
    if token != ctx.app_token:
        logger.warning("invalid app token (mismatch)")
        return False
    logger.debug("app token validated for %s", ctx.app_id)
    return True
