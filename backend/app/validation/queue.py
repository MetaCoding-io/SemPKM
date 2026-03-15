"""Async SHACL validation queue with sequential FIFO processing.

Provides a background worker that processes validation jobs one at a time.
Jobs are enqueued after each EventStore.commit() and processed sequentially.
Implements queue coalescing: when multiple jobs are queued, only the latest
is validated (since full re-validation makes intermediate results obsolete).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from app.services.validation import ValidationService
from app.validation.report import ValidationReportSummary

# Deferred import to avoid circular dependency
if False:  # TYPE_CHECKING
    from app.services.ops_log import OperationsLogService

logger = logging.getLogger(__name__)


@dataclass
class ValidationJob:
    """A validation job representing an event that needs validation."""

    event_iri: str
    timestamp: str
    trigger_source: str = "user_edit"


class AsyncValidationQueue:
    """Sequential async validation queue with coalescing.

    Processes validation jobs one at a time in FIFO order. When multiple
    jobs are queued, drains the queue and processes only the latest job
    (since full re-validation makes intermediate results obsolete).

    The latest_report property provides a cached in-memory summary for
    fast polling without hitting the triplestore.
    """

    def __init__(
        self,
        validation_service: ValidationService,
        on_complete: Optional[
            Callable[[ValidationReportSummary, str, str, str], Awaitable[None]]
        ] = None,
        ops_log_service: Optional["OperationsLogService"] = None,
    ) -> None:
        self._validation_service = validation_service
        self._on_complete = on_complete
        self._ops_log_service = ops_log_service
        self._queue: asyncio.Queue[ValidationJob] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._latest_report: Optional[ValidationReportSummary] = None

    async def start(self) -> None:
        """Start the background worker task.

        Call during app lifespan startup.
        """
        self._task = asyncio.create_task(self._worker())
        logger.info("Validation queue worker started")

    async def stop(self) -> None:
        """Stop the background worker task.

        Call during app lifespan shutdown.
        """
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Validation queue worker stopped")

    async def enqueue(self, event_iri: str, timestamp: str, trigger_source: str = "user_edit") -> None:
        """Enqueue a validation job (non-blocking).

        Args:
            event_iri: The event IRI that triggered validation.
            timestamp: ISO 8601 timestamp for the report.
            trigger_source: What triggered the validation (user_edit, inference, manual).
        """
        await self._queue.put(ValidationJob(event_iri=event_iri, timestamp=timestamp, trigger_source=trigger_source))
        logger.debug("Enqueued validation for %s", event_iri)

    @property
    def latest_report(self) -> Optional[ValidationReportSummary]:
        """Return the most recent validation report summary.

        Cached in memory after each validation run for fast polling
        without hitting the triplestore.
        """
        return self._latest_report

    async def _worker(self) -> None:
        """Process validation jobs sequentially with queue coalescing.

        Infinite loop: get a job, drain any additional queued jobs
        (coalescing), validate only the latest, cache the result.
        Never crashes on exceptions -- logs and continues.
        """
        while True:
            try:
                # Wait for the next job
                job = await self._queue.get()

                # Queue coalescing: drain any additional pending jobs
                # and keep only the latest (full re-validation makes
                # intermediate results obsolete per research Pitfall 4)
                drained_count = 0
                while True:
                    try:
                        newer_job = self._queue.get_nowait()
                        self._queue.task_done()  # Mark the skipped job as done
                        drained_count += 1
                        job = newer_job  # Keep the newest
                    except asyncio.QueueEmpty:
                        break

                if drained_count > 0:
                    logger.info(
                        "Coalesced %d queued jobs, validating latest: %s",
                        drained_count,
                        job.event_iri,
                    )

                # Run validation
                logger.info("Starting validation for event %s", job.event_iri)
                report = await self._validation_service.validate(
                    event_iri=job.event_iri,
                    timestamp=job.timestamp,
                )

                # Cache summary for fast polling
                self._latest_report = report.summary()
                logger.info(
                    "Validation complete for %s: conforms=%s, violations=%d, warnings=%d, infos=%d",
                    job.event_iri,
                    report.conforms,
                    self._latest_report.violation_count,
                    self._latest_report.warning_count,
                    self._latest_report.info_count,
                )

                # Fire completion callback (e.g., webhook dispatch)
                if self._on_complete:
                    try:
                        await self._on_complete(
                            self._latest_report, job.event_iri, job.timestamp, job.trigger_source
                        )
                    except Exception:
                        logger.warning(
                            "Validation completion callback failed",
                            exc_info=True,
                        )

                # Log to ops log (fire-and-forget)
                if self._ops_log_service:
                    try:
                        conforms = self._latest_report.conforms
                        v_count = self._latest_report.violation_count
                        w_count = self._latest_report.warning_count
                        label = (
                            f"Validation run: conforms={conforms}, "
                            f"{v_count} violations, {w_count} warnings"
                        )
                        await self._ops_log_service.log_activity(
                            activity_type="validation.run",
                            label=label,
                            actor="urn:sempkm:system",
                            status="success",
                        )
                    except Exception:
                        logger.warning(
                            "Failed to write ops log for validation run",
                            exc_info=True,
                        )

            except asyncio.CancelledError:
                raise  # Let cancellation propagate for clean shutdown
            except Exception:
                logger.exception("Validation failed for event %s", job.event_iri)
            finally:
                self._queue.task_done()
