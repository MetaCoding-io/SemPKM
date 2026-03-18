"""SDK runner — CLI entry point that starts a uvicorn server on a UDS.

Reads the app manifest, imports the App entrypoint, builds the ASGI app
with an AppContext, and runs uvicorn on a unix domain socket.

Usage::

    python -m sempkm_app_sdk.runner \\
        --app-dir /path/to/app \\
        --socket /tmp/app.sock \\
        --platform-url http://localhost:8000 \\
        --app-token <jwt>
"""

from __future__ import annotations

import argparse
import importlib
import logging
import signal
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    """Parse CLI args and start the SDK app on a unix domain socket."""
    parser = argparse.ArgumentParser(
        description="SemPKM App SDK Runner",
    )
    parser.add_argument(
        "--app-dir",
        required=True,
        help="Path to the app's root directory",
    )
    parser.add_argument(
        "--socket",
        required=True,
        help="Path to the unix domain socket",
    )
    parser.add_argument(
        "--platform-url",
        required=True,
        help="Base URL of the SemPKM platform API",
    )
    parser.add_argument(
        "--app-token",
        required=True,
        help="JWT token for platform↔app authentication",
    )
    args = parser.parse_args(argv)

    app_dir = Path(args.app_dir).resolve()
    socket_path = Path(args.socket)

    # ── Read manifest to get entrypoint ──

    manifest_path = app_dir / "manifest.yaml"
    if not manifest_path.exists():
        logger.error("manifest.yaml not found in %s", app_dir)
        sys.exit(1)

    import yaml

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    entrypoint = manifest.get("backend", {}).get("entrypoint")
    if not entrypoint or ":" not in entrypoint:
        logger.error(
            "Invalid backend.entrypoint in manifest: %r (expected 'module:attribute')",
            entrypoint,
        )
        sys.exit(1)

    module_name, attr_name = entrypoint.split(":", 1)

    # ── Import the App instance ──

    # Insert app_dir at the front of sys.path so the app's modules are importable
    sys.path.insert(0, str(app_dir))

    try:
        mod = importlib.import_module(module_name)
    except ImportError as exc:
        logger.error(
            "Failed to import app module %r from %s: %s",
            module_name,
            app_dir,
            exc,
        )
        sys.exit(1)

    app_instance = getattr(mod, attr_name, None)
    if app_instance is None:
        logger.error(
            "Module %r has no attribute %r",
            module_name,
            attr_name,
        )
        sys.exit(1)

    from sempkm_app_sdk.app import App

    if not isinstance(app_instance, App):
        logger.error(
            "%s.%s is not an App instance (got %s)",
            module_name,
            attr_name,
            type(app_instance).__name__,
        )
        sys.exit(1)

    # ── Build the ASGI app ──

    from sempkm_app_sdk.context import AppContext

    # ── Extract permissions from manifest ──

    permissions = manifest.get("permissions", {})
    if not isinstance(permissions, dict):
        permissions = {}

    ctx = AppContext(
        app_id=app_instance.app_id,
        app_dir=app_dir,
        platform_url=args.platform_url,
        app_token=args.app_token,
        permissions=permissions,
    )

    asgi_app = app_instance.build_asgi_app(ctx)

    # ── Install SIGTERM handler ──

    def handle_sigterm(signum: int, frame: object) -> None:
        logger.info("SIGTERM received, shutting down %s", app_instance.app_id)
        shutdown_handler = app_instance._lifecycle_handlers.get("shutdown")
        if shutdown_handler:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(shutdown_handler(ctx))
            except RuntimeError:
                # No running loop — run synchronously
                asyncio.run(shutdown_handler(ctx))
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    # ── Start uvicorn ──

    import uvicorn

    logger.info(
        "starting app %s on socket %s",
        app_instance.app_id,
        socket_path,
    )
    uvicorn.run(asgi_app, uds=str(socket_path), log_level="info")


if __name__ == "__main__":
    main()
