"""AppManager — subprocess lifecycle engine for SemPKM applications.

Orchestrates install → start → stop → restart → uninstall and provides
crash recovery with exponential backoff, log capture via ring buffers,
and health checking over Unix domain sockets.

The manager is the *only* component that mutates ``app_instances`` rows
and spawns/kills app subprocesses.
"""

from __future__ import annotations

import asyncio
import collections
import hashlib
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from app.apps.manifest import parse_app_manifest
from app.apps.models import AppInstance
from app.apps.registry import AppRegistry
from app.apps.tokens import generate_app_token, get_secret
from app.config import Settings
from app.rdf.namespaces import CURRENT_GRAPH

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)

# Maximum number of automatic restart attempts before marking error.
_MAX_RESTARTS = 3

# Seconds to wait for SIGTERM before sending SIGKILL.
_SIGTERM_TIMEOUT = 5

# Lines retained in the per-app ring buffer.
_LOG_BUFFER_SIZE = 100

# Default health-check timeout in seconds.
_HEALTH_TIMEOUT = 30


class AppManager:
    """Manages the full lifecycle of SemPKM application subprocesses."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        triplestore_client: TriplestoreClient,
        apps_dir: Path,
        data_dir: Path,
        platform_url: str,
    ) -> None:
        self._session_factory = session_factory
        self._triplestore = triplestore_client
        self._apps_dir = apps_dir
        self._data_dir = data_dir
        self._platform_url = platform_url

        # Internal state
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._watchers: dict[str, asyncio.Task[None]] = {}
        self._log_buffers: dict[str, collections.deque[str]] = {}
        self._registry = AppRegistry()
        self._stop_flags: set[str] = set()
        self._install_lock = asyncio.Lock()
        # Track restart counts in memory (reset on manual start/restart)
        self._restart_counts: dict[str, int] = {}
        # JWT tokens for app authentication (generated on start, cleared on stop)
        self._tokens: dict[str, str] = {}

    @property
    def registry(self) -> AppRegistry:
        """Expose the registry for read-only queries."""
        return self._registry

    def get_token(self, app_id: str) -> str | None:
        """Return the current JWT token for *app_id*, or None."""
        return self._tokens.get(app_id)

    # ──────────────────────────────────────────────
    # Install
    # ──────────────────────────────────────────────

    async def install(self, app_dir: Path) -> dict[str, Any]:
        """Install an app from *app_dir* (contains ``manifest.yaml``).

        Creates a venv, installs deps, persists an ``AppInstance`` row,
        registers the manifest, and starts the subprocess.

        Returns a status dict with ``app_id``, ``status``, and ``version``.
        """
        manifest_path = app_dir / "manifest.yaml"
        manifest = parse_app_manifest(str(manifest_path))
        app_id = manifest.appId

        # Platform compatibility check
        settings = Settings()
        platform_spec = SpecifierSet(manifest.dependencies.platform)
        platform_version = Version(settings.app_version)
        if platform_version not in platform_spec:
            raise RuntimeError(
                f"App {app_id} requires platform {manifest.dependencies.platform}, "
                f"but running {settings.app_version}"
            )

        # Manifest hash for change detection
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

        async with self._install_lock:
            # Prepare data directory and venv
            app_data = self._data_dir / app_id
            app_data.mkdir(parents=True, exist_ok=True)
            venv_path = app_data / "venv"

            await self._run_uv(["venv", str(venv_path)])

            # Install Python deps
            req_file = app_dir / manifest.backend.requirements
            await self._run_uv([
                "pip", "install",
                "-r", str(req_file),
                "--python", str(venv_path / "bin" / "python"),
            ])

            # Install the SDK package into the app venv
            await self._run_uv([
                "pip", "install",
                "/app/backend/sdk",
                "--python", str(venv_path / "bin" / "python"),
            ])

            # Copy frontend static assets for nginx serving
            self._copy_static_assets(app_id, app_dir)

            # Persist to DB
            now = datetime.now(timezone.utc)
            async with self._session_factory() as session:
                instance = AppInstance(
                    app_id=app_id,
                    version=manifest.version,
                    status="installing",
                    manifest_hash=manifest_hash,
                    installed_at=now,
                )
                session.add(instance)
                await session.commit()

            # Register manifest in memory
            self._registry.register(app_id, manifest)

            logger.info("Installed app %s v%s", app_id, manifest.version)

            # Start the app subprocess
            await self.start(app_id)

        return {"app_id": app_id, "status": "running", "version": manifest.version}

    # ──────────────────────────────────────────────
    # Start
    # ──────────────────────────────────────────────

    async def start(self, app_id: str) -> None:
        """Start (or restart) the subprocess for *app_id*.

        Cleans up any stale socket, spawns the runner process, attaches
        log capture, launches the watcher, waits for a healthy ``/_health``
        response, and updates the DB row.
        """
        manifest = self._registry.get_manifest(app_id)
        if manifest is None:
            raise ValueError(f"App {app_id} is not registered")

        app_dir = self._apps_dir / app_id
        venv_python = self._data_dir / app_id / "venv" / "bin" / "python"
        socket_path = Path(f"/tmp/sempkm-app-{app_id}.sock")

        # Clean up stale socket
        if socket_path.exists():
            os.unlink(socket_path)

        # Build command
        token = generate_app_token(app_id, {}, get_secret())
        self._tokens[app_id] = token

        cmd = [
            str(venv_python),
            "-m", "sempkm_app_sdk.runner",
            "--app-dir", str(app_dir),
            "--socket", str(socket_path),
            "--platform-url", self._platform_url,
            "--app-token", token,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._processes[app_id] = proc
        self._log_buffers.setdefault(
            app_id, collections.deque(maxlen=_LOG_BUFFER_SIZE)
        )

        # Capture stdout/stderr into ring buffer
        if proc.stdout:
            asyncio.create_task(self._capture_output(app_id, proc.stdout))
        if proc.stderr:
            asyncio.create_task(self._capture_output(app_id, proc.stderr))

        # Watcher for crash recovery
        self._watchers[app_id] = asyncio.create_task(
            self._watch_process(app_id)
        )

        # Wait for health check
        await self._wait_for_health(app_id, socket_path)

        # Reset restart counter on a successful manual/fresh start
        self._restart_counts[app_id] = 0

        # Update DB
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            instance = await session.get(AppInstance, app_id)
            if instance:
                instance.status = "running"
                instance.pid = proc.pid
                instance.socket_path = str(socket_path)
                instance.started_at = now
                instance.restart_count = 0
                instance.error_message = None
                await session.commit()

        logger.info("Started app %s (pid=%s)", app_id, proc.pid)

    # ──────────────────────────────────────────────
    # Stop
    # ──────────────────────────────────────────────

    async def stop(self, app_id: str) -> None:
        """Gracefully stop the subprocess for *app_id*.

        Sends SIGTERM, waits up to 5 s, then SIGKILL if still alive.
        """
        proc = self._processes.get(app_id)
        if proc is None:
            return

        self._stop_flags.add(app_id)

        try:
            proc.terminate()  # SIGTERM
            await asyncio.wait_for(proc.wait(), timeout=_SIGTERM_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(
                "App %s did not stop after SIGTERM; sending SIGKILL", app_id
            )
            proc.kill()  # SIGKILL
            await proc.wait()

        # Clean up internal state
        self._processes.pop(app_id, None)
        watcher = self._watchers.pop(app_id, None)
        if watcher and not watcher.done():
            watcher.cancel()
        self._log_buffers.pop(app_id, None)
        self._restart_counts.pop(app_id, None)
        self._tokens.pop(app_id, None)

        # Update DB
        async with self._session_factory() as session:
            instance = await session.get(AppInstance, app_id)
            if instance:
                instance.status = "stopped"
                instance.pid = None
                instance.restart_count = 0
                await session.commit()

        logger.info("Stopped app %s", app_id)

    # ──────────────────────────────────────────────
    # Restart
    # ──────────────────────────────────────────────

    async def restart(self, app_id: str) -> None:
        """Stop then start *app_id*."""
        await self.stop(app_id)
        await self.start(app_id)

    # ──────────────────────────────────────────────
    # Auto-start / Shutdown-all
    # ──────────────────────────────────────────────

    async def auto_start(self) -> None:
        """Start apps that were running before the last platform shutdown.

        Queries ``app_instances`` for rows with ``status='running'``
        (the shutdown path intentionally preserves this marker).
        Individual failures are logged but do not block boot.
        """
        from sqlalchemy import select

        async with self._session_factory() as session:
            result = await session.execute(
                select(AppInstance.app_id).where(AppInstance.status == "running")
            )
            app_ids = [row[0] for row in result.fetchall()]

        if not app_ids:
            logger.info("auto_start: no previously-running apps to resume")
            return

        for app_id in app_ids:
            # Ensure manifest is registered (it may not be if the platform
            # was restarted without an in-memory registry)
            if self._registry.get_manifest(app_id) is None:
                manifest_path = self._apps_dir / app_id / "manifest.yaml"
                if manifest_path.exists():
                    try:
                        manifest = parse_app_manifest(str(manifest_path))
                        self._registry.register(app_id, manifest)
                    except Exception:
                        logger.warning(
                            "auto_start: failed to load manifest for %s",
                            app_id,
                            exc_info=True,
                        )
                        continue
                else:
                    logger.warning(
                        "auto_start: manifest not found for %s at %s",
                        app_id, manifest_path,
                    )
                    continue
            try:
                await self.start(app_id)
                logger.info("auto_start: started %s", app_id)
            except Exception:
                logger.warning(
                    "auto_start: failed to start %s", app_id, exc_info=True
                )

    async def shutdown_all(self) -> None:
        """Gracefully stop all running app subprocesses.

        Sends SIGTERM to each, waits up to 10 s for exit, then SIGKILL
        for stragglers.  DB status is left as ``'running'`` so
        ``auto_start()`` picks them up on the next boot.
        """
        app_ids = list(self._processes.keys())
        if not app_ids:
            return

        logger.info("shutdown_all: stopping %d app(s)", len(app_ids))

        # Send SIGTERM to all
        for app_id in app_ids:
            proc = self._processes.get(app_id)
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
            # Mark stop flag so watcher doesn't try crash recovery
            self._stop_flags.add(app_id)

        # Wait for each to exit (up to 10 s concurrently)
        async def _wait_one(app_id: str) -> None:
            proc = self._processes.get(app_id)
            if proc is None:
                return
            try:
                await asyncio.wait_for(proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                logger.warning(
                    "shutdown_all: app %s did not exit after SIGTERM; "
                    "sending SIGKILL",
                    app_id,
                )
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass

        await asyncio.gather(*[_wait_one(aid) for aid in app_ids])

        # Cancel watcher tasks and clean up internal state
        for app_id in app_ids:
            watcher = self._watchers.pop(app_id, None)
            if watcher and not watcher.done():
                watcher.cancel()
            self._processes.pop(app_id, None)
            self._log_buffers.pop(app_id, None)
            self._restart_counts.pop(app_id, None)
            self._tokens.pop(app_id, None)
            self._stop_flags.discard(app_id)

        logger.info("shutdown_all: all apps stopped")

    # ──────────────────────────────────────────────
    # Uninstall
    # ──────────────────────────────────────────────

    async def uninstall(self, app_id: str, clean_data: bool = False) -> None:
        """Stop the app, remove its venv, and delete the DB row.

        If *clean_data* is True, also remove all app-prefixed triples from
        the triplestore before deleting the DB row (best-effort).
        """
        await self.stop(app_id)

        # Triplestore cleanup — best-effort, before DB deletion
        if clean_data and self._triplestore:
            logger.info("Cleaning triplestore data for app %s", app_id)
            try:
                # Delete triples where subject has app IRI prefix
                await self._triplestore.update(
                    f'DELETE WHERE {{ GRAPH <{CURRENT_GRAPH}> {{ ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:{app_id}:")) }} }}'
                )
                # Delete triples where object has app IRI prefix
                await self._triplestore.update(
                    f'DELETE WHERE {{ GRAPH <{CURRENT_GRAPH}> {{ ?s ?p ?o . FILTER(STRSTARTS(STR(?o), "urn:sempkm:app:{app_id}:")) }} }}'
                )
                # Clear app state graph
                await self._triplestore.update(
                    f"CLEAR GRAPH <urn:sempkm:app:{app_id}:state>"
                )
                logger.info("Triplestore data cleaned for app %s", app_id)
            except Exception as exc:
                logger.warning(
                    "Failed to clean triplestore data for app %s: %s",
                    app_id,
                    exc,
                )

        # Remove socket if present
        socket_path = Path(f"/tmp/sempkm-app-{app_id}.sock")
        if socket_path.exists():
            os.unlink(socket_path)

        # Remove data directory (includes venv)
        app_data = self._data_dir / app_id
        if app_data.exists():
            shutil.rmtree(app_data)

        # Delete DB row
        async with self._session_factory() as session:
            instance = await session.get(AppInstance, app_id)
            if instance:
                await session.delete(instance)
                await session.commit()

        self._registry.unregister(app_id)
        logger.info("Uninstalled app %s", app_id)

    # ──────────────────────────────────────────────
    # Status / Logs
    # ──────────────────────────────────────────────

    async def get_status(self, app_id: str) -> dict[str, Any]:
        """Return a status dict for *app_id* from the DB."""
        async with self._session_factory() as session:
            instance = await session.get(AppInstance, app_id)
            if instance is None:
                raise ValueError(f"App {app_id} not found")

            uptime: float | None = None
            if instance.started_at and instance.status == "running":
                started = instance.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                uptime = (
                    datetime.now(timezone.utc) - started
                ).total_seconds()

            return {
                "app_id": instance.app_id,
                "status": instance.status,
                "pid": instance.pid,
                "uptime_seconds": uptime,
                "restart_count": instance.restart_count,
                "error_message": instance.error_message,
                "version": instance.version,
            }

    def get_logs(self, app_id: str) -> list[str]:
        """Return the last ≤100 log lines captured from the app process."""
        return list(self._log_buffers.get(app_id, []))

    # ──────────────────────────────────────────────
    # Crash recovery
    # ──────────────────────────────────────────────

    async def _watch_process(self, app_id: str) -> None:
        """Block until the process exits, then handle crash recovery."""
        proc = self._processes.get(app_id)
        if proc is None:
            return

        returncode = await proc.wait()

        # Intentional stop — do nothing
        if app_id in self._stop_flags:
            self._stop_flags.discard(app_id)
            return

        restart_count = self._restart_counts.get(app_id, 0)
        logger.warning(
            "App %s exited unexpectedly (code=%s, restarts=%d/%d)",
            app_id, returncode, restart_count, _MAX_RESTARTS,
        )

        if restart_count < _MAX_RESTARTS:
            # Exponential backoff: 1s, 2s, 4s
            backoff = 2 ** restart_count
            self._restart_counts[app_id] = restart_count + 1

            # Update DB restart_count
            async with self._session_factory() as session:
                instance = await session.get(AppInstance, app_id)
                if instance:
                    instance.restart_count = restart_count + 1
                    await session.commit()

            logger.info(
                "Restarting app %s in %ds (attempt %d/%d)",
                app_id, backoff, restart_count + 1, _MAX_RESTARTS,
            )
            await asyncio.sleep(backoff)
            try:
                await self._start_for_recovery(app_id)
            except Exception:
                logger.exception("Recovery start failed for app %s", app_id)
                await self._mark_error(
                    app_id, restart_count + 1, returncode
                )
        else:
            await self._mark_error(app_id, restart_count + 1, returncode)

    async def _start_for_recovery(self, app_id: str) -> None:
        """Like ``start()`` but preserves the restart counter."""
        saved_count = self._restart_counts.get(app_id, 0)
        await self.start(app_id)
        # Restore count — ``start()`` resets it to 0
        self._restart_counts[app_id] = saved_count

        async with self._session_factory() as session:
            instance = await session.get(AppInstance, app_id)
            if instance:
                instance.restart_count = saved_count
                await session.commit()

    async def _mark_error(
        self, app_id: str, crash_count: int, returncode: int | None
    ) -> None:
        """Mark *app_id* as errored after exhausting restart attempts."""
        msg = (
            f"Crashed {crash_count} times, "
            f"last exit code: {returncode}"
        )
        logger.error("App %s: %s", app_id, msg)

        async with self._session_factory() as session:
            instance = await session.get(AppInstance, app_id)
            if instance:
                instance.status = "error"
                instance.error_message = msg
                instance.restart_count = crash_count
                await session.commit()

    # ──────────────────────────────────────────────
    # Health check
    # ──────────────────────────────────────────────

    async def _wait_for_health(
        self,
        app_id: str,
        socket_path: Path,
        timeout: int = _HEALTH_TIMEOUT,
    ) -> None:
        """Poll ``GET /_health`` on the UDS until 200 or *timeout*."""
        transport = httpx.AsyncHTTPTransport(uds=str(socket_path))
        async with httpx.AsyncClient(transport=transport) as client:
            for _ in range(timeout):
                try:
                    resp = await client.get("http://localhost/_health")
                    if resp.status_code == 200:
                        return
                except (httpx.ConnectError, httpx.RemoteProtocolError):
                    pass  # process still starting
                await asyncio.sleep(1)

        raise RuntimeError(
            f"App {app_id} health check failed after {timeout}s"
        )

    # ──────────────────────────────────────────────
    # Log capture
    # ──────────────────────────────────────────────

    async def _capture_output(
        self,
        app_id: str,
        stream: asyncio.StreamReader,
    ) -> None:
        """Read lines from *stream* and append to the ring buffer."""
        buf = self._log_buffers.get(app_id)
        if buf is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                break
            buf.append(line.decode("utf-8", errors="replace").rstrip("\n"))

    # ──────────────────────────────────────────────
    # Static asset copying
    # ──────────────────────────────────────────────

    def _copy_static_assets(self, app_id: str, app_dir: Path) -> None:
        """Copy frontend static assets to the nginx-served directory.

        If ``{app_dir}/frontend/static/`` exists, copies its contents
        to ``{data_dir}/../apps-static/{app_id}/`` (resolves to
        ``/app/data/apps-static/{app_id}/`` in Docker).  Uses
        ``dirs_exist_ok=True`` so reinstalls overwrite stale assets.
        """
        static_src = app_dir / "frontend" / "static"
        if not static_src.is_dir():
            return

        static_dest = self._data_dir.parent / "apps-static" / app_id
        static_dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(static_src, static_dest, dirs_exist_ok=True)
        logger.info("Copying static assets for app %s", app_id)

    # ──────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────

    async def _run_uv(self, args: list[str]) -> str:
        """Run ``/bin/uv <args>`` and return stdout.  Raises on failure."""
        proc = await asyncio.create_subprocess_exec(
            "/bin/uv", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"uv {' '.join(args)} failed (rc={proc.returncode}): "
                f"{stderr.decode()}"
            )
        return stdout.decode()
