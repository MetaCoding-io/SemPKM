"""AppScheduler — periodic task execution for SemPKM applications.

Fires app tasks at their configured intervals, enforces a concurrency
guard (one invocation per task at a time), retries with exponential
backoff on failure, and records every run in ``app_task_runs``.

Lifecycle: created after AppProxy in lifespan, ``start()`` after
``auto_start()``, ``stop()`` during shutdown before proxy/manager.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.models import AppInstance, AppTaskConfig, AppTaskRun

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.apps.manager import AppManager
    from app.apps.proxy import AppProxy
    from app.apps.registry import AppRegistry

logger = logging.getLogger(__name__)

# ── Interval parsing ──

# Floor/ceiling in seconds
_INTERVAL_FLOOR = 30
_INTERVAL_CEILING = 86400

# Shorthand regex: 30s, 5m, 1h, 1d
_SHORTHAND_RE = re.compile(r"^(\d+)(s|m|h|d)$")

# ISO 8601 duration: PT5M, PT1H30M, PT30S, PT1H30M45S
_ISO_RE = re.compile(
    r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$"
)

_SHORTHAND_MULTIPLIERS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_interval_seconds(interval_str: str) -> int:
    """Parse a shorthand or ISO 8601 duration string to seconds.

    Supported formats:
    - Shorthand: ``30s``, ``5m``, ``1h``, ``1d``
    - ISO 8601: ``PT5M``, ``PT1H30M``, ``PT30S``

    Enforces floor of 30s and ceiling of 86400s (24h).

    Raises:
        ValueError: On unrecognised format or out-of-range value.
    """
    interval_str = interval_str.strip()

    # Try shorthand first
    m = _SHORTHAND_RE.match(interval_str)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        seconds = amount * _SHORTHAND_MULTIPLIERS[unit]
    else:
        # Try ISO 8601
        m = _ISO_RE.match(interval_str)
        if m:
            hours = int(m.group(1) or 0)
            minutes = int(m.group(2) or 0)
            secs = int(m.group(3) or 0)
            seconds = hours * 3600 + minutes * 60 + secs
            if seconds == 0:
                raise ValueError(
                    f"Invalid interval '{interval_str}': ISO 8601 duration "
                    f"must have at least one non-zero component"
                )
        else:
            raise ValueError(
                f"Invalid interval format: '{interval_str}'. "
                f"Use shorthand (30s, 5m, 1h, 1d) or ISO 8601 (PT5M, PT1H30M)."
            )

    if seconds < _INTERVAL_FLOOR:
        raise ValueError(
            f"Interval {seconds}s is below the minimum of {_INTERVAL_FLOOR}s"
        )
    if seconds > _INTERVAL_CEILING:
        raise ValueError(
            f"Interval {seconds}s exceeds the maximum of {_INTERVAL_CEILING}s"
        )

    return seconds


# ── Retry backoff calculation ──


def calculate_backoff(
    attempt: int,
    multiplier: int = 2,
    max_backoff_str: str = "5m",
) -> int:
    """Return backoff delay in seconds for the given retry attempt.

    Uses exponential backoff: ``multiplier ** attempt``, clamped to
    ``max_backoff_str`` (parsed as an interval).
    """
    max_backoff = parse_interval_seconds(max_backoff_str)
    delay = multiplier ** attempt
    return min(delay, max_backoff)


# ── AppScheduler ──


class AppScheduler:
    """Periodic task scheduler for installed applications.

    Ticks every 60 s, checks each running app's manifest tasks against
    the ``app_task_runs`` and ``app_task_config`` tables, and dispatches
    due tasks that aren't already running.
    """

    TICK_INTERVAL = 60  # seconds between scheduler ticks

    def __init__(
        self,
        registry: AppRegistry,
        app_manager: AppManager,
        app_proxy: AppProxy,
        async_sessionmaker: async_sessionmaker[AsyncSession],
    ) -> None:
        self._registry = registry
        self._manager = app_manager
        self._proxy = app_proxy
        self._session_factory = async_sessionmaker

        self._tick_task: asyncio.Task[None] | None = None
        self._running_tasks: set[tuple[str, str]] = set()  # (app_id, task_id)
        self._stopping = False

    async def start(self) -> None:
        """Start the scheduler tick loop."""
        self._stopping = False
        self._tick_task = asyncio.create_task(self._tick_loop())
        logger.info("AppScheduler started")

    async def stop(self) -> None:
        """Cancel the tick loop and wait for in-flight task invocations to drain."""
        self._stopping = True
        if self._tick_task and not self._tick_task.done():
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        self._tick_task = None

        # Wait briefly for running tasks to finish
        for _ in range(10):
            if not self._running_tasks:
                break
            await asyncio.sleep(0.5)

        if self._running_tasks:
            logger.warning(
                "AppScheduler stopped with %d task(s) still running: %s",
                len(self._running_tasks),
                self._running_tasks,
            )
        else:
            logger.info("AppScheduler stopped")

    async def _tick_loop(self) -> None:
        """Run ``_tick()`` every ``TICK_INTERVAL`` seconds."""
        while not self._stopping:
            try:
                await self._tick()
            except Exception:
                logger.exception("Scheduler tick failed")
            try:
                await asyncio.sleep(self.TICK_INTERVAL)
            except asyncio.CancelledError:
                break

    async def _tick(self) -> None:
        """Evaluate all running apps' tasks and dispatch those that are due."""
        now = datetime.now(timezone.utc)

        # Get running app IDs from the manager
        running_app_ids: list[str] = []
        async with self._session_factory() as session:
            result = await session.execute(
                select(AppInstance.app_id).where(
                    AppInstance.status == "running"
                )
            )
            running_app_ids = [row[0] for row in result.fetchall()]

        for app_id in running_app_ids:
            manifest = self._registry.get_manifest(app_id)
            if manifest is None or not manifest.tasks:
                continue

            for task in manifest.tasks:
                await self._evaluate_task(app_id, task.id, task, now)

    async def _evaluate_task(
        self,
        app_id: str,
        task_id: str,
        task: Any,
        now: datetime,
    ) -> None:
        """Check if a task is due and not already running, then dispatch."""
        key = (app_id, task_id)

        # Concurrency guard
        if key in self._running_tasks:
            logger.debug(
                "Skipping %s/%s — still running from previous invocation",
                app_id, task_id,
            )
            return

        # Check config overrides
        config = await self._get_task_config(app_id, task_id)
        if config and config.paused:
            return

        # Determine effective interval
        interval_str = (
            config.interval_override
            if config and config.interval_override
            else task.interval
        )
        try:
            interval_seconds = parse_interval_seconds(interval_str)
        except ValueError:
            logger.warning(
                "Invalid interval '%s' for %s/%s — skipping",
                interval_str, app_id, task_id,
            )
            return

        # Check last run
        last_run = await self._get_last_run(app_id, task_id)
        if last_run and last_run.started_at:
            started = last_run.started_at
            # SQLite stores naive datetimes; normalize to UTC for subtraction
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elapsed = (now - started).total_seconds()
            if elapsed < interval_seconds:
                return

        # Task is due — dispatch in background
        logger.info("Dispatching task %s/%s", app_id, task_id)
        asyncio.create_task(
            self._invoke_task(app_id, task_id, task)
        )

    async def _invoke_task(
        self,
        app_id: str,
        task_id: str,
        task: Any,
    ) -> None:
        """Invoke a task on the app, record the run, and handle retries."""
        key = (app_id, task_id)
        self._running_tasks.add(key)
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        max_retries = task.retryPolicy.maxRetries
        backoff_multiplier = task.retryPolicy.backoffMultiplier
        max_backoff_str = task.retryPolicy.maxBackoff

        status = "error"
        error_message: str | None = None
        duration_ms: int | None = None

        try:
            for attempt in range(max_retries + 1):
                t0 = time.monotonic()
                try:
                    resp_status, resp_body = await self._proxy.invoke_task(
                        app_id, task_id, run_id
                    )
                    duration_ms = int((time.monotonic() - t0) * 1000)

                    if 200 <= resp_status < 300:
                        status = "success"
                        error_message = None
                        logger.info(
                            "Task %s/%s completed (run=%s, %dms)",
                            app_id, task_id, run_id, duration_ms,
                        )
                        break
                    else:
                        error_message = (
                            f"HTTP {resp_status}: {resp_body[:500]}"
                        )
                        logger.warning(
                            "Task %s/%s attempt %d failed: %s",
                            app_id, task_id, attempt + 1, error_message,
                        )
                except Exception as exc:
                    duration_ms = int((time.monotonic() - t0) * 1000)
                    error_message = f"{type(exc).__name__}: {exc}"
                    logger.warning(
                        "Task %s/%s attempt %d exception: %s",
                        app_id, task_id, attempt + 1, error_message,
                    )

                # If we have retries left, backoff and retry
                if attempt < max_retries:
                    backoff = calculate_backoff(
                        attempt, backoff_multiplier, max_backoff_str
                    )
                    logger.info(
                        "Retrying %s/%s in %ds (attempt %d/%d)",
                        app_id, task_id, backoff,
                        attempt + 2, max_retries + 1,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "Task %s/%s exhausted retries (%d attempts, run=%s)",
                        app_id, task_id, max_retries + 1, run_id,
                    )
        finally:
            # Record the task run
            finished_at = datetime.now(timezone.utc)
            if duration_ms is None:
                duration_ms = int(
                    (finished_at - started_at).total_seconds() * 1000
                )

            await self._record_run(
                app_id=app_id,
                task_id=task_id,
                run_id=run_id,
                started_at=started_at,
                finished_at=finished_at,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
            )
            self._running_tasks.discard(key)

    async def _record_run(
        self,
        app_id: str,
        task_id: str,
        run_id: str,
        started_at: datetime,
        finished_at: datetime,
        status: str,
        duration_ms: int,
        error_message: str | None,
    ) -> None:
        """Persist a task run record to the database."""
        try:
            async with self._session_factory() as session:
                run = AppTaskRun(
                    app_id=app_id,
                    task_id=task_id,
                    run_id=run_id,
                    started_at=started_at,
                    finished_at=finished_at,
                    status=status,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )
                session.add(run)
                await session.commit()
        except Exception:
            logger.exception(
                "Failed to record task run %s for %s/%s",
                run_id, app_id, task_id,
            )

    async def _get_task_config(
        self, app_id: str, task_id: str
    ) -> AppTaskConfig | None:
        """Load task config overrides from the database."""
        async with self._session_factory() as session:
            return await session.get(AppTaskConfig, (app_id, task_id))

    async def _get_last_run(
        self, app_id: str, task_id: str
    ) -> AppTaskRun | None:
        """Return the most recent task run, or None."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AppTaskRun)
                .where(
                    AppTaskRun.app_id == app_id,
                    AppTaskRun.task_id == task_id,
                )
                .order_by(AppTaskRun.started_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
